from django.urls import reverse
from rest_framework import serializers

from .models import Farm, KYCApplication


class FarmPublicSerializer(serializers.ModelSerializer):
    """Safe for anonymous visitors: no KYC data, no owner contact details."""
    is_verified = serializers.BooleanField(read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = ['id', 'farm_name', 'description', 'state', 'district', 'village',
                  'farm_image', 'is_verified', 'product_count', 'created_at']

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()


class KYCApplicationSerializer(serializers.ModelSerializer):
    """Farmer's view of their own applications (read) and submission (write)."""
    id_number = serializers.CharField(write_only=True, min_length=4, max_length=20)
    document = serializers.FileField(write_only=True)
    has_document = serializers.SerializerMethodField()

    class Meta:
        model = KYCApplication
        fields = ['id', 'id_type', 'id_number', 'id_number_last4', 'document', 'has_document',
                  'status', 'decision_reason', 'submitted_at', 'reviewed_at']
        read_only_fields = ['id', 'id_number_last4', 'status', 'decision_reason',
                            'submitted_at', 'reviewed_at']

    def get_has_document(self, obj):
        return bool(obj.document)

    def validate_document(self, f):
        from common.validators import validate_kyc_document
        from django.core.exceptions import ValidationError as DjangoVE
        try:
            validate_kyc_document(f)
        except DjangoVE as exc:
            raise serializers.ValidationError(exc.messages)
        return f


class FarmOwnerSerializer(serializers.ModelSerializer):
    """The farmer's own profile, including KYC status and the latest decision."""
    is_verified = serializers.BooleanField(read_only=True)
    latest_kyc = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = ['id', 'farm_name', 'description', 'state', 'district', 'village', 'pincode',
                  'area_in_acres', 'farm_image', 'kyc_status', 'is_verified', 'latest_kyc',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'kyc_status', 'created_at', 'updated_at']

    def get_latest_kyc(self, obj):
        app = obj.kyc_applications.first()
        return KYCApplicationSerializer(app).data if app else None

    def validate_area_in_acres(self, v):
        if v < 0:
            raise serializers.ValidationError('Area cannot be negative.')
        return v


class AdminKYCSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.farm_name', read_only=True)
    farm_location = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source='farm.user.username', read_only=True)
    owner_email = serializers.CharField(source='farm.user.email', read_only=True)
    owner_phone = serializers.CharField(source='farm.user.phone', read_only=True)
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True, default=None)
    document_url = serializers.SerializerMethodField()

    class Meta:
        model = KYCApplication
        fields = ['id', 'farm', 'farm_name', 'farm_location', 'owner_username', 'owner_email',
                  'owner_phone', 'id_type', 'id_number_last4', 'status', 'decision_reason',
                  'reviewed_by_username', 'submitted_at', 'reviewed_at', 'document_url']
        read_only_fields = fields

    def get_farm_location(self, obj):
        return f"{obj.farm.district}, {obj.farm.state}"

    def get_document_url(self, obj):
        # An API path (needs the admin's JWT), NOT a public media URL.
        return reverse('admin-kyc-document', args=[obj.pk])


class RejectSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
