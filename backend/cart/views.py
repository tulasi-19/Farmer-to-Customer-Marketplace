from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from products.models import Product
from .models import Cart, CartItem
from .serializers import CartItemInputSerializer, CartItemUpdateSerializer, serialize_cart


def _cart_for(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _check_stock(product, qty):
    if not product.is_active or not product.farm.is_verified:
        raise ValidationError({'detail': 'This product is not available.'})
    if qty > product.quantity_available:
        raise ValidationError({'quantity': f'Only {product.quantity_available} {product.unit} available.'})


class CartView(APIView):
    """GET /api/v1/cart/  |  DELETE /api/v1/cart/ (clear). A customer only ever sees their own cart."""
    permission_classes = [IsCustomer]

    def get(self, request):
        return Response(serialize_cart(_cart_for(request.user), request))

    def delete(self, request):
        _cart_for(request.user).items.all().delete()
        return Response(serialize_cart(_cart_for(request.user), request))


class CartItemAddView(APIView):
    """POST /api/v1/cart/items/ {product_id, quantity} - adds, or increases an existing line."""
    permission_classes = [IsCustomer]

    def post(self, request):
        s = CartItemInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        pid, qty = s.validated_data['product_id'], s.validated_data['quantity']
        try:
            product = Product.objects.select_related('farm').get(pk=pid)
        except Product.DoesNotExist:
            raise ValidationError({'product_id': 'Product not found.'})

        cart = _cart_for(request.user)
        with transaction.atomic():
            item = CartItem.objects.select_for_update().filter(cart=cart, product=product).first()
            new_qty = (item.quantity if item else 0) + qty
            _check_stock(product, new_qty)
            if item:
                item.quantity = new_qty
                item.save(update_fields=['quantity'])
            else:
                try:
                    with transaction.atomic():
                        CartItem.objects.create(cart=cart, product=product, quantity=new_qty)
                except IntegrityError:
                    # Two simultaneous "add" clicks: the unique constraint stopped a duplicate line.
                    other = CartItem.objects.get(cart=cart, product=product)
                    other.quantity = other.quantity + qty
                    _check_stock(product, other.quantity)
                    other.save(update_fields=['quantity'])
        return Response(serialize_cart(cart, request), status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    """PATCH {quantity} / DELETE /api/v1/cart/items/<id>/ - lookup is scoped to the caller's cart,
    so changing the ID in the URL can never touch another user's cart (404)."""
    permission_classes = [IsCustomer]

    def _item(self, request, pk):
        try:
            return CartItem.objects.select_related('product', 'product__farm').get(pk=pk, cart__user=request.user)
        except CartItem.DoesNotExist:
            from django.http import Http404
            raise Http404

    def patch(self, request, pk):
        item = self._item(request, pk)
        s = CartItemUpdateSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        _check_stock(item.product, s.validated_data['quantity'])
        item.quantity = s.validated_data['quantity']
        item.save(update_fields=['quantity'])
        return Response(serialize_cart(item.cart, request))

    def delete(self, request, pk):
        item = self._item(request, pk)
        cart = item.cart
        item.delete()
        return Response(serialize_cart(cart, request))
