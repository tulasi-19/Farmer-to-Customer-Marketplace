from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsFarmer
from products.models import Product
from . import predictor, services
from .models import AIPrediction
from .serializers import AIPredictionSerializer, DemandRequestSerializer, PriceRequestSerializer


class _FarmerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role in ('farmer', 'admin'))


def _own_product(request, product_id):
    """Farmers can only analyse their own products (others -> 404); admins can analyse any."""
    qs = Product.objects.select_related('farm')
    if request.user.role != 'admin':
        qs = qs.filter(farm__user=request.user)
    return get_object_or_404(qs, pk=product_id)


class DemandPredictionView(APIView):
    """POST /api/v1/ai/demand-prediction/ {product_id, [crop], [month], [supply_index], [avg_weekly_units]}"""
    permission_classes = [_FarmerOrAdmin]
    throttle_scope = 'predictions'

    def post(self, request):
        s = DemandRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        product = _own_product(request, d.pop('product_id'))
        return Response(services.demand_forecast(product, request.user, **d))


class PriceRecommendationView(APIView):
    """POST /api/v1/ai/price-recommendation/ {product_id, [grade], [market_price_per_kg], ...}
    Returns an estimate only. It never edits the product's price."""
    permission_classes = [_FarmerOrAdmin]
    throttle_scope = 'predictions'

    def post(self, request):
        s = PriceRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = dict(s.validated_data)
        product = _own_product(request, d.pop('product_id'))
        return Response(services.price_recommendation(product, request.user, **d))


class ModelInfoView(APIView):
    """GET /api/v1/ai/model-info/ - metrics from the real training run, supported crops/regions."""
    permission_classes = [_FarmerOrAdmin]

    def get(self, request):
        return Response({'demand': predictor.model_info('demand'), 'price': predictor.model_info('price')})


class PredictionHistoryView(generics.ListAPIView):
    """GET /api/v1/ai/history/?product=<id>&kind=demand - the caller's own past predictions."""
    permission_classes = [IsFarmer]
    serializer_class = AIPredictionSerializer

    def get_queryset(self):
        qs = AIPrediction.objects.filter(product__farm__user=self.request.user)
        p = self.request.query_params
        if p.get('product', '').isdigit():
            qs = qs.filter(product_id=int(p['product']))
        if p.get('kind') in ('demand', 'price'):
            qs = qs.filter(kind=p['kind'])
        return qs
