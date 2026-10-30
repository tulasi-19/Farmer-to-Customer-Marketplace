from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, Q
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from accounts.permissions import IsAdminRole, IsApprovedFarmer, IsFarmer
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


def _with_ratings(qs):
    """Average rating counts only reviews that moderators have not hidden."""
    pub = Q(reviews__status='published')
    return qs.annotate(avg_rating=Avg('reviews__rating', filter=pub),
                       n_reviews=Count('reviews', filter=pub, distinct=True))


def _decimal_param(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ''):
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        raise ValidationError({name: 'Must be a number.'})


class CategoryListView(generics.ListAPIView):
    """GET /api/v1/categories/"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    pagination_class = None


class ProductViewSet(viewsets.ModelViewSet):
    """
    Public:   list / retrieve (only active products of KYC-approved farms)
    Farmer:   create / update / delete - ONLY own products, ONLY if KYC approved
    Query:    ?search= &category=<slug|id> &min_price= &max_price= &available=true &farm=<id> &ordering=
    """
    serializer_class = ProductSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ['name', 'description', 'category__name', 'farm__farm_name', 'farm__district']
    ordering_fields = ['price', 'created_at', 'quantity_available', 'name', 'avg_rating']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        if self.action == 'mine':
            return [IsFarmer()]
        return [IsApprovedFarmer()]

    def _public_qs(self):
        return Product.objects.select_related('farm', 'category').filter(
            is_active=True, farm__kyc_status='approved')

    def get_queryset(self):
        user = self.request.user
        if self.action in ('update', 'partial_update', 'destroy'):
            # Ownership enforced by the queryset: someone else's product => 404.
            qs = Product.objects.select_related('farm', 'category').filter(farm__user=user)
        elif self.action == 'mine':
            qs = Product.objects.select_related('farm', 'category').filter(farm__user=user)
        elif self.action == 'retrieve' and user.is_authenticated:
            base = Product.objects.select_related('farm', 'category')
            qs = base.filter(Q(is_active=True, farm__kyc_status='approved') | Q(farm__user=user))
        else:
            qs = self._public_qs()

        p = self.request.query_params
        if p.get('category'):
            c = p['category']
            qs = qs.filter(category_id=int(c)) if c.isdigit() else qs.filter(category__slug=c)
        if p.get('farm', '').isdigit():
            qs = qs.filter(farm_id=int(p['farm']))
        lo, hi = _decimal_param(self.request, 'min_price'), _decimal_param(self.request, 'max_price')
        if lo is not None:
            qs = qs.filter(price__gte=lo)
        if hi is not None:
            qs = qs.filter(price__lte=hi)
        if p.get('available', '').lower() in ('1', 'true', 'yes'):
            qs = qs.filter(quantity_available__gt=0)
        return _with_ratings(qs)

    def perform_create(self, serializer):
        serializer.save(farm=self.request.user.farm)  # farm comes from the session, never the request body

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.order_items.exists():
            # Past orders reference this product: archive instead of deleting history.
            product.is_active = False
            product.save(update_fields=['is_active', 'updated_at'])
            return Response({'detail': 'Product has order history, so it was archived instead of deleted.',
                             'archived': True})
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='mine')
    def mine(self, request):
        """GET /api/v1/products/mine/ - all of the farmer's own products, including archived."""
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        ser = self.get_serializer(page if page is not None else qs, many=True)
        return self.get_paginated_response(ser.data) if page is not None else Response(ser.data)


# ------------------------------ admin ------------------------------------
class AdminProductListView(generics.ListAPIView):
    """GET /api/v1/admin/products/"""
    permission_classes = [IsAdminRole]
    serializer_class = ProductSerializer
    search_fields = ['name', 'farm__farm_name']

    def get_queryset(self):
        return _with_ratings(Product.objects.select_related('farm', 'category').order_by('-created_at'))


class AdminProductToggleView(generics.GenericAPIView):
    """PATCH /api/v1/admin/products/<id>/ {is_active} - hide/unhide a listing."""
    permission_classes = [IsAdminRole]
    serializer_class = ProductSerializer
    queryset = Product.objects.all()

    def patch(self, request, pk):
        product = self.get_object()
        if 'is_active' not in request.data:
            raise ValidationError({'is_active': 'This field is required.'})
        val = request.data['is_active']
        product.is_active = val if isinstance(val, bool) else str(val).lower() in ('1', 'true', 'yes')
        product.save(update_fields=['is_active', 'updated_at'])
        return Response(ProductSerializer(product).data)
