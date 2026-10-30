"""Admin-only endpoints: marketplace statistics and user management."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsAdminRole
from .serializers import AdminUserSerializer

User = get_user_model()


class AdminStatsView(APIView):
    """GET /api/v1/admin/stats/ - real counts straight from the database."""
    permission_classes = [IsAdminRole]

    def get(self, request):
        from farms.models import KYCApplication
        from orders.models import Order
        from products.models import Product
        from reviews.models import Review

        collected = Order.objects.filter(payment_status=Order.PaymentStatus.COD_PAID).aggregate(t=Sum('total_amount'))['t']
        return Response({
            'users': {row['role']: row['n'] for row in User.objects.values('role').annotate(n=Count('id'))},
            'products': {
                'total': Product.objects.count(),
                'active': Product.objects.filter(is_active=True).count(),
            },
            'orders': {
                'total': Order.objects.count(),
                'by_status': {r['status']: r['n'] for r in Order.objects.values('status').annotate(n=Count('id'))},
            },
            'cash_collected': str(collected or Decimal('0.00')),
            'kyc_pending': KYCApplication.objects.filter(status=KYCApplication.Status.PENDING).count(),
            'reviews': {
                'total': Review.objects.count(),
                'hidden': Review.objects.filter(status=Review.Status.HIDDEN).count(),
            },
        })


class AdminUserListView(generics.ListAPIView):
    """GET /api/v1/admin/users/?role=farmer&search=ram"""
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    search_fields = ['username', 'email']
    ordering_fields = ['created_at', 'username']

    def get_queryset(self):
        qs = User.objects.all().order_by('-created_at')
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """PATCH /api/v1/admin/users/<id>/ {is_active} - suspend / re-activate."""
    permission_classes = [IsAdminRole]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()
    http_method_names = ['get', 'patch', 'head', 'options']

    def patch(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response({'detail': 'You cannot deactivate your own account.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().patch(request, *args, **kwargs)
