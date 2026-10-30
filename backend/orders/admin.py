from django.contrib import admin

from .models import Order, OrderEvent, OrderItem, Shipment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'product_name', 'unit', 'unit_price', 'quantity', 'line_total', 'shipment']
    can_delete = False


class ShipmentInline(admin.TabularInline):
    model = Shipment
    extra = 0
    readonly_fields = ['farm', 'status', 'subtotal', 'carrier', 'tracking_number']
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_amount', 'status', 'payment_status', 'payment_method', 'created_at']
    list_filter = ['status', 'payment_status', 'payment_method']
    # Read-only on purpose: status/payment changes must go through the API so the
    # state machine, stock restoration and audit events are never bypassed.
    readonly_fields = [f.name for f in Order._meta.fields]
    inlines = [ShipmentInline, OrderItemInline]

    def has_add_permission(self, request):
        return False


@admin.register(OrderEvent)
class OrderEventAdmin(admin.ModelAdmin):
    list_display = ['order', 'shipment', 'status', 'note', 'actor', 'created_at']
    readonly_fields = [f.name for f in OrderEvent._meta.fields]
