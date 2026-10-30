"""
All order business rules live here (views stay thin). Every function that
changes more than one row runs inside transaction.atomic() so it either fully
succeeds or fully rolls back.
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from cart.models import Cart
from products.models import Product
from . import state
from .models import Order, OrderEvent, OrderItem, Shipment

logger = logging.getLogger('orders')
TWO_PLACES = Decimal('0.01')

DEFAULT_NOTES = {
    state.PROCESSING: 'Farmer is preparing your items.',
    state.SHIPPED: 'Your items have been shipped.',
    state.OUT_FOR_DELIVERY: 'Your items are out for delivery.',
    state.DELIVERED: 'Delivered.',
}


class Conflict(APIException):
    status_code = 409
    default_detail = 'This action conflicts with the current state of the resource.'
    default_code = 'conflict'


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _log(order, status, note='', shipment=None, actor=None):
    return OrderEvent.objects.create(
        order=order, shipment=shipment, status=status, note=note[:255],
        actor=actor if (actor is not None and getattr(actor, 'pk', None)) else None,
    )


def _restore_stock(items):
    """Give reserved stock back. F() makes the +quantity happen inside the database."""
    for item in items:
        Product.objects.filter(pk=item.product_id).update(
            quantity_available=F('quantity_available') + item.quantity)


def _cancel_shipment(shipment, order, actor, note):
    _restore_stock(shipment.items.all())
    shipment.status = state.CANCELLED
    shipment.save(update_fields=['status', 'updated_at'])
    _log(order, state.CANCELLED, note, shipment, actor)


def _refresh_order(order, actor=None):
    """Re-derive the order status from its shipments and save."""
    statuses = list(order.shipments.values_list('status', flat=True))
    new = state.derive_order_status(statuses)
    changed = new != order.status
    order.status = new
    order.save(update_fields=['status', 'updated_at'])
    if changed and new in (state.DELIVERED, state.CANCELLED):
        _log(order, new, 'Order delivered.' if new == state.DELIVERED else 'Order cancelled.', None, actor)
    return order


# --------------------------------------------------------------------------
# checkout
# --------------------------------------------------------------------------
@transaction.atomic
def checkout(user, *, shipping_address, shipping_phone):
    """
    Turn the customer's server-side cart into an Order.
      * prices come from the DB at this moment (snapshotted into OrderItem)
      * product rows are LOCKED (SELECT ... FOR UPDATE) so two buyers of the
        last 5 kg are serialised: one succeeds, the other gets a clear error
      * stock is reserved (decremented) in the same transaction
      * one Shipment per farmer
    """
    cart = Cart.objects.filter(user=user).first()
    lines = list(cart.items.all()) if cart else []
    if not lines:
        raise ValidationError({'detail': 'Your cart is empty.'})

    # Lock in a consistent order (by id) so two concurrent checkouts can't deadlock each other.
    ids = sorted({l.product_id for l in lines})
    products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=ids).order_by('id')}

    problems = []
    for l in lines:
        p = products.get(l.product_id)
        if p is None or not p.is_active or not p.farm.is_verified:
            problems.append(f"{l.product.name}: no longer available")
        elif l.quantity > p.quantity_available:
            problems.append(f"{p.name}: only {p.quantity_available} {p.unit} left (you asked for {l.quantity})")
    if problems:
        raise ValidationError({'detail': 'Some items in your cart cannot be ordered.', 'items': problems})

    initial = state.CONFIRMED   # cash on delivery: confirmed straight away, no payment step

    totals, by_farm = Decimal('0.00'), {}
    for l in lines:
        p = products[l.product_id]
        line_total = (p.price * l.quantity).quantize(TWO_PLACES)
        totals += line_total
        by_farm.setdefault(p.farm_id, []).append((p, l.quantity, line_total))

    order = Order.objects.create(
        user=user, status=initial, payment_method=Order.PaymentMethod.COD,
        payment_status=Order.PaymentStatus.COD_PENDING, total_amount=totals, shipping_address=shipping_address, shipping_phone=shipping_phone,
    )
    for farm_id, entries in by_farm.items():
        shipment = Shipment.objects.create(
            order=order, farm_id=farm_id, status=initial,
            subtotal=sum((e[2] for e in entries), Decimal('0.00')),
        )
        for p, qty, line_total in entries:
            OrderItem.objects.create(
                order=order, shipment=shipment, product=p, product_name=p.name, unit=p.unit,
                unit_price=p.price, quantity=qty, line_total=line_total,
            )
            p.quantity_available = p.quantity_available - qty
            p.save(update_fields=['quantity_available', 'updated_at'])

    _log(order, initial, 'Order placed. Cash on delivery.', None, user)
    cart.items.all().delete()
    logger.info('order %s created user=%s total=%s', order.pk, user.pk, totals)
    return order


# --------------------------------------------------------------------------
# tracking updates
# --------------------------------------------------------------------------
@transaction.atomic
def update_shipment_status(shipment_id, *, actor, new_status, note='', carrier='', tracking_number=''):
    """Move ONE shipment forward. The caller (view) has already made sure a farmer
    can only reach their own shipments. Rules come from orders/state.py."""
    if getattr(actor, 'role', None) not in ('farmer', 'admin'):
        raise PermissionDenied('Only the farmer or an admin can update delivery status.')

    shipment = Shipment.objects.select_for_update().get(pk=shipment_id)
    order = Order.objects.select_for_update().get(pk=shipment.order_id)

    if new_status not in state.STAFF_SETTABLE:
        raise ValidationError({'status': 'You cannot set this status manually.'})
    if not state.can_transition(shipment.status, new_status):
        raise ValidationError({'status': f"Cannot move a '{shipment.status}' shipment to '{new_status}'."})

    if new_status == state.CANCELLED:
        if not note.strip():
            raise ValidationError({'note': 'Please give a reason for cancelling.'})
        _cancel_shipment(shipment, order, actor, note.strip())
    else:
        now = timezone.now()
        shipment.status = new_status
        if carrier:
            shipment.carrier = carrier
        if tracking_number:
            shipment.tracking_number = tracking_number
        if new_status == state.SHIPPED:
            shipment.shipped_at = now
        if new_status == state.DELIVERED:
            shipment.delivered_at = now
            shipment.shipped_at = shipment.shipped_at or now
        shipment.save()
        _log(order, new_status, note.strip() or DEFAULT_NOTES.get(new_status, ''), shipment, actor)

    _refresh_order(order, actor)
    return shipment


@transaction.atomic
def cancel_order(order_id, *, actor, reason=''):
    """Customer (or admin) cancels the whole order, allowed only while nothing is processing/shipped."""
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.user_id != actor.id and getattr(actor, 'role', None) != 'admin':
        raise PermissionDenied('You cannot cancel this order.')
    shipments = list(order.shipments.select_for_update())
    active = [s for s in shipments if s.status != state.CANCELLED]
    if not active:
        raise ValidationError({'detail': 'This order is already cancelled.'})
    if any(s.status not in state.CUSTOMER_CANCELLABLE for s in active):
        raise ValidationError({'detail': 'Some items are already being prepared or shipped, so the whole '
                                         'order can no longer be cancelled. Please contact the farmer.'})
    for s in active:
        _cancel_shipment(s, order, actor, (reason or 'Cancelled by customer').strip())
    _refresh_order(order, actor)
    return order


@transaction.atomic
def mark_cod_collected(order_id, *, actor):
    """Admin confirms the cash for a delivered COD order was collected.
    Farmers cannot do this - nobody on the selling side can mark an order paid."""
    if getattr(actor, 'role', None) != 'admin':
        raise PermissionDenied('Only an admin can confirm cash collection.')
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.payment_status != Order.PaymentStatus.COD_PENDING:
        raise ValidationError({'detail': 'Cash for this order has already been recorded.'})
    if order.status != state.DELIVERED:
        raise ValidationError({'detail': 'The order must be delivered first.'})
    order.payment_status = Order.PaymentStatus.COD_PAID
    order.save(update_fields=['payment_status', 'updated_at'])
    _log(order, order.status, 'Cash on delivery collected.', None, actor)
    return order
