import pytest
from django.contrib.auth import get_user_model

AdminUser = get_user_model()


@pytest.mark.django_db
class TestAdminUserModel:
    def test_role_choices_include_super_admin(self):
        """AdminUser has SUPER_ADMIN role choice."""
        choices = [c[0] for c in AdminUser.Role.choices]
        assert "super_admin" in choices

    def test_role_choices_include_admin(self):
        """AdminUser has ADMIN role choice."""
        choices = [c[0] for c in AdminUser.Role.choices]
        assert "admin" in choices

    def test_default_role_is_admin(self):
        """New AdminUser defaults to ADMIN role."""
        user = AdminUser(username="test_default")
        assert user.role == AdminUser.Role.ADMIN

    def test_username_is_primary_login_field(self):
        """USERNAME_FIELD must be 'username'."""
        assert AdminUser.USERNAME_FIELD == "username"

    def test_required_fields_include_role(self):
        """REQUIRED_FIELDS must include 'role'."""
        assert "role" in AdminUser.REQUIRED_FIELDS

    def test_create_admin_user(self):
        """Can create AdminUser with role=ADMIN."""
        user = AdminUser.objects.create_user(
            username="admin_user",
            password="testpass123",
            role=AdminUser.Role.ADMIN,
        )
        assert user.role == AdminUser.Role.ADMIN
        assert user.is_active is True

    def test_create_super_admin_user(self):
        """Can create AdminUser with role=SUPER_ADMIN."""
        user = AdminUser.objects.create_user(
            username="super_admin_user",
            password="testpass123",
            role=AdminUser.Role.SUPER_ADMIN,
        )
        assert user.role == AdminUser.Role.SUPER_ADMIN

    def test_str_representation(self):
        """AdminUser __str__ returns username."""
        user = AdminUser(username="test_str_user", role=AdminUser.Role.ADMIN)
        assert str(user) == "test_str_user"

    def test_email_field_is_optional(self):
        """Email field is optional (blank/null allowed)."""
        user = AdminUser.objects.create_user(
            username="no_email_user",
            password="testpass123",
        )
        assert user.email == "" or user.email is None

    def test_is_active_defaults_to_true(self):
        """New users are active by default."""
        user = AdminUser.objects.create_user(
            username="active_user",
            password="testpass123",
        )
        assert user.is_active is True
