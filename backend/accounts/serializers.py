from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

AdminUser = get_user_model()

INVALID_CREDENTIALS_MSG = "Invalid credentials."


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(required=True, allow_blank=False, write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        user = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )

        if not user:
            raise serializers.ValidationError(
                {"detail": INVALID_CREDENTIALS_MSG},
                code="authorization",
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": INVALID_CREDENTIALS_MSG},
                code="authorization",
            )

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)


class AdminUserListSerializer(serializers.ModelSerializer):
    """Serializer for listing admin users — no password field exposed."""

    class Meta:
        model = AdminUser
        fields = ("id", "username", "role", "is_active", "date_joined")
        read_only_fields = ("id", "date_joined")


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating admin users."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "Password must be at least 8 characters."},
    )

    class Meta:
        model = AdminUser
        fields = ("id", "username", "password", "role")
        read_only_fields = ("id",)

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = AdminUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating admin users (username, role, is_active)."""

    class Meta:
        model = AdminUser
        fields = ("id", "username", "role", "is_active")
        read_only_fields = ("id",)


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for direct password reset (no email flow)."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "Password must be at least 8 characters."},
    )
