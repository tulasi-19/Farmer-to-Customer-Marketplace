import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()
PHONE_RE = re.compile(r'^\+?\d{10,14}$')


def _clean_phone(value):
    value = (value or '').strip().replace(' ', '').replace('-', '')
    if value and not PHONE_RE.match(value):
        raise serializers.ValidationError('Enter a valid phone number (10-14 digits).')
    return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    # Only these two roles can self-register. 'admin' is rejected by validation.
    role = serializers.ChoiceField(choices=['farmer', 'customer'], default='customer')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'role', 'phone', 'address']
        read_only_fields = ['id']
        extra_kwargs = {'email': {'required': True}}

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is taken.')
        return value

    def validate_phone(self, value):
        return _clean_phone(value)

    def validate(self, attrs):
        probe = User(username=attrs.get('username', ''), email=attrs.get('email', ''))
        try:
            validate_password(attrs['password'], user=probe)
        except Exception as exc:  # DjangoValidationError -> DRF error
            raise serializers.ValidationError({'password': list(getattr(exc, 'messages', [str(exc)]))})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)  # hashes the password


class UserSerializer(serializers.ModelSerializer):
    """Profile shown to / edited by the logged-in user.
    role, username and is_verified are READ-ONLY: users cannot promote themselves."""

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'address', 'is_verified', 'created_at']
        read_only_fields = ['id', 'username', 'role', 'is_verified', 'created_at']

    def validate_phone(self, value):
        return _clean_phone(value)

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'phone', 'is_active', 'is_verified', 'created_at']
        read_only_fields = ['id', 'username', 'email', 'role', 'phone', 'is_verified', 'created_at']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate_new_password(self, value):
        validate_password(value, user=self.context['request'].user)
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class FarmBridgeTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds role/username to the JWT so the UI can pick the right dashboard.
    The backend never trusts this claim for authorization - it re-reads the DB."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        return token
