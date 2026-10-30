from django.utils.html import strip_tags
from rest_framework import serializers

from orders.models import OrderItem
from orders import state
from products.models import Product
from .models import Review


def eligible_order_item(user, product):
    """A delivered purchase of this product by this user, or None."""
    return (OrderItem.objects
            .filter(product=product, order__user=user, shipment__status=state.DELIVERED)
            .order_by('-id').first())


class ReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'username', 'rating', 'comment', 'status', 'created_at']
        read_only_fields = ['id', 'username', 'status', 'created_at']

    def validate_comment(self, value):
        # React escapes output, but we also strip markup so stored data is clean for any client.
        return strip_tags(value).strip()

    def validate(self, attrs):
        if self.instance is not None:          # editing: the product can't change
            attrs.pop('product', None)
            return attrs
        user = self.context['request'].user
        product = attrs['product']
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError('You have already reviewed this product.')
        item = eligible_order_item(user, product)
        if item is None:
            raise serializers.ValidationError('You can review a product only after a delivered order that includes it.')
        attrs['order_item'] = item
        return attrs


class AdminReviewSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'product_name', 'username', 'rating', 'comment', 'status', 'created_at']
        read_only_fields = ['id', 'product', 'product_name', 'username', 'rating', 'comment', 'created_at']
