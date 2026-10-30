import re
from decimal import Decimal

from rest_framework import serializers

from . import state
from .models import Order, OrderEvent, OrderItem, Shipment

PHONE_RE = re.compile(r'^\+?\d{10,14}$')


class CheckoutSerializer(serializers.Serializer):
    shipping_address = serializers.CharField(min_length=10, max_length=500)
    shipping_phone = serializers.CharField(max_length=15)

    def validate_shipping_phone(self, v):
        v = v.strip().replace(' ', '').replace('-', '')
        if not PHONE_RE.match(v):
            raise serializers.ValidationError('Enter a valid phone number (10-14 digits).')
        return v

    def validate_shipping_address(self, v):
        return v.strip()


class ShipmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=state.ALL_STATUSES)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    carrier = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')
    tracking_number = serializers.CharField(max_length=80, required=False, allow_blank=True, default='')


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'unit', 'unit_price', 'quantity', 'line_total']


class OrderEventSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderEvent
        fields = ['id', 'shipment', 'status', 'status_label', 'note', 'created_at']


class ShipmentSerializer(serializers.ModelSerializer):
    """What the CUSTOMER sees for each farmer's part of the order."""
    farm_id = serializers.IntegerField(source='farm.id', read_only=True)
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = ['id', 'farm_id', 'farm_name', 'status', 'status_label', 'subtotal', 'carrier',
                  'tracking_number', 'shipped_at', 'delivered_at', 'updated_at', 'items']


class OrderSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_label = serializers.CharField(source='get_payment_status_display', read_only=True)
    shipments = ShipmentSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'status', 'status_label', 'payment_method', 'payment_status', 'payment_status_label',
                  'total_amount', 'shipping_address', 'shipping_phone', 'created_at',
                  'updated_at', 'can_cancel', 'shipments', 'events']
        read_only_fields = fields

    def get_can_cancel(self, o):
        active = [s.status for s in o.shipments.all() if s.status != state.CANCELLED]
        return bool(active) and all(s in state.CUSTOMER_CANCELLABLE for s in active)


class AdminOrderSerializer(OrderSerializer):
    customer_username = serializers.CharField(source='user.username', read_only=True)
    customer_email = serializers.CharField(source='user.email', read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['customer_username', 'customer_email']
        read_only_fields = fields


class FarmerShipmentSerializer(serializers.ModelSerializer):
    """What a FARMER sees: only their own items, plus the delivery details needed to
    fulfil them. No customer email, no other farmers' items, no payment secrets."""
    order_id = serializers.IntegerField(source='order.id', read_only=True)
    customer_name = serializers.CharField(source='order.user.username', read_only=True)
    shipping_address = serializers.CharField(source='order.shipping_address', read_only=True)
    shipping_phone = serializers.CharField(source='order.shipping_phone', read_only=True)
    payment_method = serializers.CharField(source='order.payment_method', read_only=True)
    payment_status = serializers.CharField(source='order.payment_status', read_only=True)
    ordered_at = serializers.DateTimeField(source='order.created_at', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    events = OrderEventSerializer(many=True, read_only=True)
    allowed_next = serializers.SerializerMethodField()

    class Meta:
        model = Shipment
        fields = ['id', 'order_id', 'status', 'status_label', 'allowed_next', 'subtotal', 'carrier',
                  'tracking_number', 'customer_name', 'shipping_address', 'shipping_phone',
                  'payment_method', 'payment_status', 'ordered_at', 'shipped_at', 'delivered_at',
                  'items', 'events']
        read_only_fields = fields

    def get_allowed_next(self, s):
        return state.allowed_next_for_staff(s.status)
