from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    ChangePasswordSerializer, ForgotPasswordSerializer, FarmBridgeTokenObtainPairSerializer,
    LogoutSerializer, RegisterSerializer, ResetPasswordSerializer, UserSerializer,
)

User = get_user_model()
token_generator = PasswordResetTokenGenerator()


class RegisterView(generics.CreateAPIView):
    """POST /api/v1/auth/register/ - open to anyone; role limited to farmer/customer."""
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'


class LoginView(TokenObtainPairView):
    """POST /api/v1/auth/login/ - returns access + refresh JWT."""
    serializer_class = FarmBridgeTokenObtainPairSerializer
    throttle_scope = 'auth'


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ {refresh} - blacklists the refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = LogoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            RefreshToken(s.validated_data['refresh']).blacklist()
        except TokenError:
            pass  # already invalid/expired - the goal (logged out) is met
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET/PATCH /api/v1/auth/me/ - current user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        s = UserSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'auth'

    def post(self, request):
        s = ChangePasswordSerializer(data=request.data, context={'request': request})
        s.is_valid(raise_exception=True)
        request.user.set_password(s.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        return Response({'detail': 'Password changed successfully.'})


class ForgotPasswordView(APIView):
    """Always answers with the same message so it cannot be used to discover
    which usernames/emails are registered."""
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        s = ForgotPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        ident = s.validated_data['username_or_email']
        user = User.objects.filter(Q(username__iexact=ident) | Q(email__iexact=ident), is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = token_generator.make_token(user)
            link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject='FarmBridge AI - Password Reset',
                message=f"Hi {user.username},\n\nReset your password here:\n{link}\n\n"
                        "If you did not request this, ignore this email.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True,
            )
        return Response({'detail': 'If an account exists, a reset link has been sent. '
                                   '(Dev mode: the email is printed in the Django terminal.)'})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = 'auth'

    def post(self, request):
        s = ResetPasswordSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(d['uid'])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({'detail': 'Invalid or expired reset link.'}, status=400)
        if not token_generator.check_token(user, d['token']):
            return Response({'detail': 'Invalid or expired reset link.'}, status=400)
        try:
            validate_password(d['new_password'], user=user)
        except DjangoValidationError as exc:
            return Response({'new_password': exc.messages}, status=400)
        user.set_password(d['new_password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Password has been reset. You can now log in.'})
