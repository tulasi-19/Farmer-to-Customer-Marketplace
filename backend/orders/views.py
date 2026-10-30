from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsCustomer, IsFarmer
from . import services, state, stats
from .models import Order, Shipment
from .serializers import (
    AdminOrderSerializer, CancelSerializer, CheckoutSerializer, FarmerShipmentSerializer,
    OrderSerializer, ShipmentStatusSerializer,
)

ORDER_PREFETCH = ('shipments__farm', 'shipments__items', 'events')


def _order_qs():
    return Order.objects.select_related('user').prefetch_related(*ORDER_PREFETCH)


def _shipment_qs():
    return (Shipment.objects.select_related('order', 'order__user', 'farm')
            .prefetch_related('items', 'events'))


# ------------------------------ customer ---------------------------------
class CheckoutView(APIView):
    """POST /api/v1/orders/checkout/ - builds a cash-on-delivery order from the SERVER-side cart.
    The request carries only address and phone; never prices, totals or items."""
    permission_classes = [IsCustomer]

    def post(self, request):
        s = CheckoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        order = services.checkout(request.user, **s.validated_data)
        order = _order_qs().get(pk=order.pk)
        return Response(OrderSerializer(order, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrderListView(generics.ListAPIView):
    """GET /api/v1/orders/ - the caller's own orders only."""
    permission_classes = [IsCustomer]
    serializer_class = OrderSerializer

    def get_queryset(self):
        qs = _order_qs().filter(user=self.request.user)
        st = self.request.query_params.get('status')
        return qs.filter(status=st) if st else qs


class OrderDetailView(generics.RetrieveAPIView):
    """GET /api/v1/orders/<id>/ - someone else's order id returns 404."""
    permission_classes = [IsCustomer]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return _order_qs().filter(user=self.request.user)


class OrderCancelView(APIView):
    """POST /api/v1/orders/<id>/cancel/"""
    permission_classes = [IsCustomer]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, user=request.user)
        s = CancelSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.cancel_order(order.pk, actor=request.user, reason=s.validated_data['reason'])
        return Response(OrderSerializer(_order_qs().get(pk=order.pk), context={'request': request}).data)


# ------------------------------ farmer -----------------------------------
class FarmerShipmentListView(generics.ListAPIView):
    """GET /api/v1/farmer/shipments/?status=confirmed - this farmer's shipments only.
    Farmers never see customer emails or other farmers' items."""
    permission_classes = [IsFarmer]
    serializer_class = FarmerShipmentSerializer

    def get_queryset(self):
        qs = _shipment_qs().filter(farm__user=self.request.user).exclude(status=state.PENDING).order_by('-created_at')
        st = self.request.query_params.get('status')
        return qs.filter(status=st) if st else qs


class FarmerShipmentDetailView(generics.RetrieveAPIView):
    permission_classes = [IsFarmer]
    serializer_class = FarmerShipmentSerializer

    def get_queryset(self):
        return _shipment_qs().filter(farm__user=self.request.user).exclude(status=state.PENDING)


class FarmerShipmentStatusView(APIView):
    """POST /api/v1/farmer/shipments/<id>/status/ {status, note, carrier, tracking_number}
    The shipment is looked up WITH the owner filter, so another farmer's id is a 404."""
    permission_classes = [IsFarmer]

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk, farm__user=request.user)
        s = ShipmentStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        services.update_shipment_status(
            shipment.pk, actor=request.user, new_status=d['status'], note=d['note'],
            carrier=d['carrier'], tracking_number=d['tracking_number'])
        fresh = _shipment_qs().get(pk=shipment.pk)
        return Response(FarmerShipmentSerializer(fresh).data)


class FarmerDashboardView(APIView):
    """GET /api/v1/farmer/dashboard/ - live statistics (no hardcoded numbers)."""
    permission_classes = [IsFarmer]

    def get(self, request):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response({'detail': 'Create your farm profile first.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(stats.farmer_dashboard(farm))


# ------------------------------- admin -----------------------------------
class AdminOrderListView(generics.ListAPIView):
    """GET /api/v1/admin/orders/?status=&payment_status=&order_id=&search="""
    permission_classes = [IsAdminRole]
    serializer_class = AdminOrderSerializer
    search_fields = ['user__username', 'user__email']

    def get_queryset(self):
        qs = _order_qs()
        p = self.request.query_params
        if p.get('status'):
            qs = qs.filter(status=p['status'])
        if p.get('payment_status'):
            qs = qs.filter(payment_status=p['payment_status'])
        if p.get('order_id', '').isdigit():
            qs = qs.filter(pk=int(p['order_id']))
        return qs


class AdminOrderDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = AdminOrderSerializer
    queryset = _order_qs()


class AdminShipmentStatusView(APIView):
    """POST /api/v1/admin/shipments/<id>/status/ - same rules as for farmers."""
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        shipment = get_object_or_404(Shipment, pk=pk)
        s = ShipmentStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        services.update_shipment_status(
            shipment.pk, actor=request.user, new_status=d['status'], note=d['note'],
            carrier=d['carrier'], tracking_number=d['tracking_number'])
        return Response(AdminOrderSerializer(_order_qs().get(pk=shipment.order_id)).data)


class AdminMarkCODPaidView(APIView):
    """POST /api/v1/admin/orders/<id>/mark-cod-paid/"""
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        services.mark_cod_collected(order.pk, actor=request.user)
        return Response(AdminOrderSerializer(_order_qs().get(pk=order.pk)).data)
