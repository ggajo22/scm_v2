from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.permissions import IsSuperAdmin
from accounts.serializers import (
    AdminUserCreateSerializer,
    AdminUserListSerializer,
    AdminUserUpdateSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetSerializer,
)

AdminUser = get_user_model()

INVALID_CREDENTIALS_MSG = "Invalid credentials."


class LoginView(APIView):
    # @MX:ANCHOR: [AUTO] LoginView is the entry point for all authentication — REQ-AUTH-001
    # @MX:REASON: All auth tests and token-dependent features depend on this endpoint
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            # Return generic 401 for invalid credentials, 400 for missing fields
            errors = serializer.errors
            # Check if it's a credentials error (detail key) → 401
            if "detail" in str(errors) or "non_field_errors" in errors:
                return Response(
                    {"detail": INVALID_CREDENTIALS_MSG},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            # Field validation errors (empty username/password) → 400
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    # @MX:WARN: [AUTO] Token blacklisting — uses DB write on every logout
    # @MX:REASON: REQ-AUTH-006 requires server-side token blacklisting; DB must be reachable
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)


class TokenRefreshView(APIView):
    """Token refresh view — validates and returns new access token."""

    permission_classes = []
    authentication_classes = []

    def post(self, request):
        from rest_framework_simplejwt.serializers import TokenRefreshSerializer

        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response(
                {"detail": str(e) if str(e) else "Token is invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class AdminUserViewSet(ModelViewSet):
    # @MX:ANCHOR: [AUTO] AdminUserViewSet handles all CRUD + reset-password for admin users
    # @MX:REASON: REQ-AUTH-016 through REQ-AUTH-021 all route through this viewset
    queryset = AdminUser.objects.all().order_by("id")
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return AdminUserCreateSerializer
        if self.action in ("update", "partial_update"):
            return AdminUserUpdateSerializer
        if self.action == "reset_password":
            return PasswordResetSerializer
        return AdminUserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            AdminUserListSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        # EDGE-015: Block SUPER_ADMIN from deactivating themselves
        if (
            instance == request.user
            and "is_active" in request.data
            and not request.data["is_active"]
        ):
            return Response(
                {"detail": "SuperAdmin cannot deactivate their own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AdminUserListSerializer(instance).data)

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = False
        return self.partial_update(request, *args, **kwargs)

    def reset_password(self, request, pk=None):
        """POST /api/admin/users/{id}/reset-password/ — REQ-AUTH-018."""
        instance = self.get_object()
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.set_password(serializer.validated_data["password"])
        instance.save()
        return Response({"detail": "Password reset successfully."}, status=status.HTTP_200_OK)
