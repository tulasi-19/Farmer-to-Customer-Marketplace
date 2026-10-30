from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from farms.models import Farm
from products.models import Product
from . import state


class Order(models.Model):
    """
    One checkout by one customer (cash on delivery). Payment is tracked in `payment_status`
    and delivery in `status` - two separate concerns, two separate fields.
    `status` is DERIVED from the order's shipments (one per farmer).
    """

    class Status(models.TextChoices):
        PENDING = state.PENDING, 'Pending payment'
        CONFIRMED = state.CONFIRMED, 'Confirmed'
        PROCESSING = state.PROCESSING, 'Processing'
        SHIPPED = state.SHIPPED, 'Shipped'
        OUT_FOR_DELIVERY = state.OUT_FOR_DELIVERY, 'Out for delivery'
        DELIVERED = state.DELIVERED, 'Delivered'
        CANCELLED = state.CANCELLED, 'Cancelled'

    class PaymentMethod(models.TextChoices):
        COD = 'cod', 'Cash on delivery'

    class PaymentStatus(models.TextChoices):
        COD_PENDING = 'cod_pending', 'Cash on delivery - to collect'
        COD_PAID = 'cod_paid', 'Cash collected'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CONFIRMED, db_index=True)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.COD)
    payment_status = models.CharField(max_length=15, choices=PaymentStatus.choices,
                                      default=PaymentStatus.COD_PENDING, db_index=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    shipping_phone = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', '-created_at'])]
        constraints = [models.CheckConstraint(check=Q(total_amount__gte=0), name='order_total_non_negative')]

    def __str__(self):
        return f"Order #{self.pk} ({self.status}/{self.payment_status})"


class Shipment(models.Model):
    """One farmer's portion of an order. This is what a farmer fulfils and what
    the customer tracks. Splitting by farmer means each farmer sees and updates
    ONLY their own items, and delivery tracking is honest for multi-farm carts."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='shipments')
    farm = models.ForeignKey(Farm, on_delete=models.PROTECT, related_name='shipments')
    status = models.CharField(max_length=20, choices=Order.Status.choices, default=Order.Status.PENDING, db_index=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    carrier = models.CharField(max_length=80, blank=True)
    tracking_number = models.CharField(max_length=80, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['order', 'farm'], name='one_shipment_per_farm_per_order')]

    def __str__(self):
        return f"Shipment #{self.pk} of order #{self.order_id} [{self.status}]"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    # Snapshots: later edits to the product must never rewrite order history.
    product_name = models.CharField(max_length=150)
    unit = models.CharField(max_length=10)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(check=Q(quantity__gt=0), name='orderitem_quantity_positive')]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"


class OrderEvent(models.Model):
    """Append-only tracking timeline. Replaces the old single-status history:
    each event records which shipment (if any) changed, to what, when and by whom."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='events')
    shipment = models.ForeignKey(Shipment, null=True, blank=True, on_delete=models.CASCADE, related_name='events')
    status = models.CharField(max_length=20, choices=Order.Status.choices)
    note = models.CharField(max_length=255, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['order', 'created_at'])]

    def __str__(self):
        return f"{self.status} @ order #{self.order_id}"
