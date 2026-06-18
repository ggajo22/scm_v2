"""
Tests for AdminUserViewSet (AC-AUTH-008, 009, 012, EDGE-015).
GET/POST/PUT/PATCH /api/admin/users/
POST /api/admin/users/{id}/reset-password/
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from accounts.tests.factories import AdminUserFactory, SuperAdminFactory

AdminUser = get_user_model()

LOGIN_URL = "/api/auth/login/"
USERS_URL = "/api/admin/users/"


def get_auth_header(api_client, username, password="testpass123"):
    resp = api_client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
    )
    return f"Bearer {resp.data['access']}"


@pytest.fixture
def super_admin(db):
    return SuperAdminFactory(username="sa_manager")


@pytest.fixture
def sa_client(api_client, super_admin):
    api_client.credentials(HTTP_AUTHORIZATION=get_auth_header(api_client, "sa_manager"))
    return api_client


@pytest.mark.django_db
class TestCreateAdminUser:
    """AC-AUTH-008: Create admin account + duplicate username → 400."""

    def test_create_admin_user_returns_201(self, sa_client):
        resp = sa_client.post(
            USERS_URL,
            {"username": "new_admin", "password": "securepass1", "role": "admin"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_create_admin_user_response_has_no_password(self, sa_client):
        """SEC-MUST-002: password must never appear in API response."""
        resp = sa_client.post(
            USERS_URL,
            {"username": "no_pass_in_resp", "password": "securepass1", "role": "admin"},
            format="json",
        )
        assert "password" not in resp.data

    def test_duplicate_username_returns_400(self, sa_client):
        """AC-AUTH-008 + REQ-AUTH-020: duplicate username → HTTP 400."""
        AdminUserFactory(username="existing_admin")
        resp = sa_client.post(
            USERS_URL,
            {"username": "existing_admin", "password": "securepass1", "role": "admin"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_sets_correct_role(self, sa_client):
        resp = sa_client.post(
            USERS_URL,
            {
                "username": "super_new",
                "password": "securepass1",
                "role": "super_admin",
            },
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        created_user = AdminUser.objects.get(username="super_new")
        assert created_user.role == AdminUser.Role.SUPER_ADMIN


@pytest.mark.django_db
class TestPasswordReset:
    """AC-AUTH-009: Password reset endpoint."""

    def test_password_reset_returns_200_with_valid_password(self, sa_client):
        """EDGE-010: password exactly 8 chars → HTTP 200 (boundary inclusive)."""
        target = AdminUserFactory(username="reset_target")
        resp = sa_client.post(
            f"/api/admin/users/{target.id}/reset-password/",
            {"password": "exact8ch"},  # exactly 8 characters
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_password_reset_7_chars_returns_400(self, sa_client):
        """EDGE-011: password exactly 7 chars → HTTP 400."""
        target = AdminUserFactory(username="reset_7chars")
        resp = sa_client.post(
            f"/api/admin/users/{target.id}/reset-password/",
            {"password": "seven77"},  # 7 characters
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_empty_returns_400(self, sa_client):
        """AC-AUTH-009: empty password → HTTP 400."""
        target = AdminUserFactory(username="reset_empty")
        resp = sa_client.post(
            f"/api/admin/users/{target.id}/reset-password/",
            {"password": ""},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_actually_changes_password(self, sa_client, api_client):
        """After reset, user can login with new password."""
        target = AdminUserFactory(username="reset_verify")
        new_password = "newpassword123"

        sa_client.post(
            f"/api/admin/users/{target.id}/reset-password/",
            {"password": new_password},
            format="json",
        )

        # Try login with new password
        resp = api_client.post(
            LOGIN_URL,
            {"username": "reset_verify", "password": new_password},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_password_reset_does_not_invalidate_existing_tokens(self, sa_client, api_client):
        """REQ-AUTH-018 / EDGE-013: password reset must NOT invalidate target's refresh tokens."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken as RT

        # Create target user and obtain THEIR OWN refresh token
        target = SuperAdminFactory(username="reset_no_blacklist_target")
        target_token_resp = api_client.post(
            LOGIN_URL,
            {"username": "reset_no_blacklist_target", "password": "testpass123"},
            format="json",
        )
        assert target_token_resp.status_code == 200
        target_refresh_token = target_token_resp.data["refresh"]
        target_jti = RT(target_refresh_token)["jti"]

        # Reset the target user's password via SUPER_ADMIN
        sa_client.post(
            f"/api/admin/users/{target.id}/reset-password/",
            {"password": "newpass999"},
            format="json",
        )

        # EDGE-013: target's own refresh token must NOT be blacklisted after password reset
        assert not BlacklistedToken.objects.filter(token__jti=target_jti).exists(), (
            "Password reset must NOT invalidate existing refresh tokens (EDGE-013)"
        )


@pytest.mark.django_db
class TestListAdminUsers:
    """AC-AUTH-012: List all admin accounts."""

    def test_list_returns_200(self, sa_client):
        resp = sa_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_list_response_has_no_password_field(self, sa_client):
        """SEC-MUST-002: no password key anywhere in list response."""
        AdminUserFactory(username="listed_user")
        resp = sa_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK
        response_body = str(resp.data)
        assert "password" not in response_body

    def test_list_returns_all_users(self, sa_client, super_admin):
        # super_admin fixture already created 1 user
        AdminUserFactory(username="extra_user1")
        AdminUserFactory(username="extra_user2")
        resp = sa_client.get(USERS_URL)
        assert len(resp.data) >= 3


@pytest.mark.django_db
class TestUpdateAdminUser:
    """REQ-AUTH-017: Update username, role, is_active."""

    def test_patch_update_role(self, sa_client):
        target = AdminUserFactory(username="update_role_user", role=AdminUser.Role.ADMIN)
        resp = sa_client.patch(
            f"{USERS_URL}{target.id}/",
            {"role": "super_admin"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.role == AdminUser.Role.SUPER_ADMIN

    def test_patch_update_is_active(self, sa_client):
        target = AdminUserFactory(username="deactivate_me")
        resp = sa_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False

    def test_put_update_username(self, sa_client):
        """PUT (full update) changes username."""
        target = AdminUserFactory(username="put_target_user", role=AdminUser.Role.ADMIN)
        resp = sa_client.put(
            f"{USERS_URL}{target.id}/",
            {"username": "put_updated_user", "role": "admin", "is_active": True},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.username == "put_updated_user"


@pytest.mark.django_db
class TestSuperAdminSelfDeactivation:
    """EDGE-015: SUPER_ADMIN self-deactivation → HTTP 400."""

    def test_super_admin_cannot_deactivate_self(self, api_client):
        sa = SuperAdminFactory(username="sa_self_deactivate")
        auth = get_auth_header(api_client, "sa_self_deactivate")
        api_client.credentials(HTTP_AUTHORIZATION=auth)

        resp = api_client.patch(
            f"{USERS_URL}{sa.id}/",
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_super_admin_can_deactivate_other_user(self, sa_client):
        target = AdminUserFactory(username="deactivate_other")
        resp = sa_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
