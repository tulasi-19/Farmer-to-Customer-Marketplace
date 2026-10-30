from rest_framework import generics, permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsCustomer
from products.models import Product
from .models import Review
from .serializers import AdminReviewSerializer, ReviewSerializer, eligible_order_item


class ReviewViewSet(viewsets.ModelViewSet):
    """
    list / retrieve : public, only PUBLISHED reviews (?product=<id>)
    create          : customers with a delivered purchase of that product
    update / delete : the review's author only (others get 404)
    """
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [IsCustomer()]

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'product')
        if self.action in ('partial_update', 'update', 'destroy'):
            return qs.filter(user=self.request.user)
        qs = qs.filter(status=Review.Status.PUBLISHED)
        pid = self.request.query_params.get('product')
        if pid:
            if not pid.isdigit():
                raise ValidationError({'product': 'Must be a product id.'})
            qs = qs.filter(product_id=int(pid))
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewEligibilityView(APIView):
    """GET /api/v1/reviews/eligibility/?product=<id> - lets the UI show or hide the review form."""
    permission_classes = [IsCustomer]

    def get(self, request):
        pid = request.query_params.get('product', '')
        if not pid.isdigit():
            raise ValidationError({'product': 'Must be a product id.'})
        product = Product.objects.filter(pk=int(pid)).first()
        if product is None:
            return Response({'can_review': False, 'reason': 'Product not found.'})
        if Review.objects.filter(user=request.user, product=product).exists():
            return Response({'can_review': False, 'reason': 'You have already reviewed this product.'})
        if eligible_order_item(request.user, product) is None:
            return Response({'can_review': False, 'reason': 'You can review this product after it is delivered to you.'})
        return Response({'can_review': True, 'reason': ''})


class AdminReviewListView(generics.ListAPIView):
    """GET /api/v1/admin/reviews/?status=hidden"""
    permission_classes = [IsAdminRole]
    serializer_class = AdminReviewSerializer
    search_fields = ['comment', 'user__username', 'product__name']

    def get_queryset(self):
        qs = Review.objects.select_related('user', 'product').order_by('-created_at')
        st = self.request.query_params.get('status')
        return qs.filter(status=st) if st else qs


class AdminReviewModerateView(generics.UpdateAPIView):
    """PATCH /api/v1/admin/reviews/<id>/ {status: published|hidden}"""
    permission_classes = [IsAdminRole]
    serializer_class = AdminReviewSerializer
    queryset = Review.objects.all()
    http_method_names = ['patch']
