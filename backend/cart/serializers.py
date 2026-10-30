from decimal import Decimal

from rest_framework import serializers

from products.models import Product


class CartItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))


def serialize_cart(cart, request=None):
    """Builds the cart payload with CURRENT prices and server-side totals."""
    items, subtotal = [], Decimal('0.00')
    qs = cart.items.select_related('product', 'product__farm')
    for it in qs:
        p = it.product
        line = (p.price * it.quantity).quantize(Decimal('0.01'))
        orderable = p.is_active and p.farm.is_verified
        issue = None
        if not orderable:
            issue = 'This product is no longer available.'
        elif it.quantity > p.quantity_available:
            issue = f'Only {p.quantity_available} {p.unit} left in stock.'
        if orderable:
            subtotal += line
        image = None
        if p.image:
            image = request.build_absolute_uri(p.image.url) if request else p.image.url
        items.append({
            'id': it.id, 'product_id': p.id, 'product_name': p.name, 'unit': p.unit,
            'image': image, 'farm_name': p.farm.farm_name,
            'unit_price': str(p.price), 'quantity': str(it.quantity), 'line_total': str(line),
            'stock_available': str(p.quantity_available), 'issue': issue,
        })
    return {
        'id': cart.id, 'items': items, 'item_count': len(items),
        'subtotal': str(subtotal.quantize(Decimal('0.01'))),
        'has_issues': any(i['issue'] for i in items),
    }
