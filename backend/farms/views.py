import mimetypes

from django.http import FileResponse, Http404
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole, IsFarmer
from . import services
from .models import Farm, KYCApplication
from .serializers import (
    AdminKYCSerializer, FarmOwnerSerializer, FarmPublicSerializer,
    KYCApplicationSerializer, RejectSerializer,
)


# ----------------------------- public ------------------------------------
class FarmListView(generics.ListAPIView):
    """GET /api/v1/farms/ - only KYC-approved farms are public."""
    permission_classes = [permissions.AllowAny]
    serializer_class = FarmPublicSerializer
    search_fields = ['farm_name', 'state', 'district']
    queryset = Farm.objects.filter(kyc_status=Farm.KYCStatus.APPROVED).order_by('farm_name')


class FarmDetailView(generics.RetrieveAPIView):
    """GET /api/v1/farms/<id>/ - public farm page."""
    permission_classes = [permissions.AllowAny]
    serializer_class = FarmPublicSerializer
    queryset = Farm.objects.filter(kyc_status=Farm.KYCStatus.APPROVED)


# ----------------------------- farmer ------------------------------------
class FarmerProfileView(APIView):
    """GET / POST / PATCH /api/v1/farmer/profile/ - the logged-in farmer's own farm only.
    The farm is always looked up from request.user, never from an ID in the request."""
    permission_classes = [IsFarmer]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response({'detail': 'No farm profile yet.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(FarmOwnerSerializer(farm, context={'request': request}).data)

    def post(self, request):
        if getattr(request.user, 'farm', None):
            return Response({'detail': 'Farm profile already exists. Use PATCH to edit it.'}, status=400)
        s = FarmOwnerSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save(user=request.user)
        return Response(s.data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response({'detail': 'No farm profile yet.'}, status=status.HTTP_404_NOT_FOUND)
        s = FarmOwnerSerializer(farm, data=request.data, partial=True, context={'request': request})
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class FarmerKYCView(APIView):
    """GET (history) / POST (submit or resubmit) /api/v1/farmer/kyc/"""
    permission_classes = [IsFarmer]
    parser_classes = [MultiPartParser, FormParser]

    def _farm(self, request):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'Create your farm profile first.'})
        return farm

    def get(self, request):
        farm = getattr(request.user, 'farm', None)
        apps = farm.kyc_applications.all() if farm else []
        return Response({
            'kyc_status': farm.kyc_status if farm else 'not_submitted',
            'applications': KYCApplicationSerializer(apps, many=True).data,
        })

    def post(self, request):
        farm = self._farm(request)
        s = KYCApplicationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        app = services.submit_kyc(farm, id_type=d['id_type'], id_number=d['id_number'], document=d['document'])
        return Response(KYCApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class KYCDocumentView(APIView):
    """
    GET .../kyc/<id>/document/ - streams the private document to its owner or an admin.
    Everyone else gets 404 (not 403) so IDs cannot be probed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            app = KYCApplication.objects.select_related('farm').get(pk=pk)
        except KYCApplication.DoesNotExist:
            raise Http404
        user = request.user
        if not (user.role == 'admin' or app.farm.user_id == user.id):
            raise Http404
        if not app.document:
            raise Http404
        ctype = mimetypes.guess_type(app.document.name)[0] or 'application/octet-stream'
        resp = FileResponse(app.document.open('rb'), content_type=ctype)
        resp['Content-Disposition'] = 'inline'
        resp['X-Content-Type-Options'] = 'nosniff'
        resp['Cache-Control'] = 'private, no-store'
        return resp


# ----------------------------- admin -------------------------------------
class AdminKYCListView(generics.ListAPIView):
    """GET /api/v1/admin/kyc-applications/?status=pending"""
    permission_classes = [IsAdminRole]
    serializer_class = AdminKYCSerializer
    search_fields = ['farm__farm_name', 'farm__user__username']

    def get_queryset(self):
        qs = KYCApplication.objects.select_related('farm', 'farm__user', 'reviewed_by').order_by('-submitted_at')
        st = self.request.query_params.get('status')
        return qs.filter(status=st) if st else qs


class AdminKYCDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = AdminKYCSerializer
    queryset = KYCApplication.objects.select_related('farm', 'farm__user', 'reviewed_by')


class AdminKYCApproveView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        app = services.decide_kyc(pk, request.user, approve=True, reason=request.data.get('reason', ''))
        return Response(AdminKYCSerializer(app).data)


class AdminKYCRejectView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        s = RejectSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        app = services.decide_kyc(pk, request.user, approve=False, reason=s.validated_data['reason'])
        return Response(AdminKYCSerializer(app).data)
