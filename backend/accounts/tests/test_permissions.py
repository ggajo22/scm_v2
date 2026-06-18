"""
Tests for RBAC permission classes (AC-AUTH-007, 011, SEC-MUST-001).
"""
from unittest.mock import MagicMock

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


@pytest.mark.django_db
class TestSuperAdminAccess:
    """REQ-AUTH-011: SUPER_ADMIN has access to all features."""

    def test_super_admin_can_access_users_list(self, api_client):
        SuperAdminFactory(username="sa_list_user")
        api_client.credentials(HTTP_AUTHORIZATION=get_auth_header(api_client, "sa_list_user"))
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAdminAccess:
    """AC-AUTH-007 + REQ-AUTH-013: ADMIN cannot access /api/admin/users/."""

    def test_admin_cannot_access_users_list(self, api_client):
        AdminUserFactory(username="regular_admin")
        api_client.credentials(HTTP_AUTHORIZATION=get_auth_header(api_client, "regular_admin"))
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_403_response_has_no_data_leak(self, api_client):
        """AC-AUTH-007: 403 response must not leak user data."""
        AdminUserFactory(username="admin_no_leak")
        SuperAdminFactory(username="super_in_db")  # exists in DB — must not appear in 403

        api_client.credentials(HTTP_AUTHORIZATION=get_auth_header(api_client, "admin_no_leak"))
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # Response body should not contain sensitive user data
        body_str = str(resp.data)
        assert "super_in_db" not in body_str
        assert "password" not in body_str


@pytest.mark.django_db
class TestUnauthenticatedAccess:
    """AC-AUTH-011 + REQ-AUTH-014: Unauthenticated → HTTP 401."""

    def test_no_token_returns_401_on_users_list(self, api_client):
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_token_returns_401_on_user_create(self, api_client):
        resp = api_client.post(USERS_URL, {}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_token_returns_401_on_protected_endpoint(self, api_client):
        resp = api_client.get("/api/admin/users/1/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestIsAdminOrSuperAdminPermission:
    """Unit tests for IsAdminOrSuperAdmin permission class."""

    def test_admin_user_granted(self):
        from accounts.permissions import IsAdminOrSuperAdmin

        perm = IsAdminOrSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.role = AdminUser.Role.ADMIN

        mock_request = MagicMock()
        mock_request.user = mock_user

        assert perm.has_permission(mock_request, None) is True

    def test_super_admin_granted(self):
        from accounts.permissions import IsAdminOrSuperAdmin

        perm = IsAdminOrSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.role = AdminUser.Role.SUPER_ADMIN

        mock_request = MagicMock()
        mock_request.user = mock_user

        assert perm.has_permission(mock_request, None) is True

    def test_unauthenticated_denied(self):
        from accounts.permissions import IsAdminOrSuperAdmin

        perm = IsAdminOrSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = False

        mock_request = MagicMock()
        mock_request.user = mock_user

        assert perm.has_permission(mock_request, None) is False

    def test_inactive_user_denied(self):
        from accounts.permissions import IsAdminOrSuperAdmin

        perm = IsAdminOrSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = False

        mock_request = MagicMock()
        mock_request.user = mock_user

        assert perm.has_permission(mock_request, None) is False


@pytest.mark.django_db
class TestSecMust001RoleFromDB:
    """
    SEC-MUST-001: IsSuperAdmin reads role from DB (request.user.role),
    NOT from JWT payload.
    """

    def test_role_from_db_not_jwt_payload(self, api_client):
        """
        Scenario: JWT payload claims SUPER_ADMIN but DB says ADMIN.
        Expected: HTTP 403 (DB role wins).
        """
        # Create a user as SUPER_ADMIN to get a valid JWT
        super_user = SuperAdminFactory(username="sa_then_demoted")
        auth = get_auth_header(api_client, "sa_then_demoted")

        # Demote the user in the DB to ADMIN after JWT was issued
        super_user.role = AdminUser.Role.ADMIN
        super_user.save()

        # Use the old JWT (which was issued when user was SUPER_ADMIN)
        api_client.credentials(HTTP_AUTHORIZATION=auth)
        resp = api_client.get(USERS_URL)

        # DB says ADMIN → must be 403 even though JWT was issued as SUPER_ADMIN
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_inactive_super_admin_cannot_access(self, api_client):
        """REQ-AUTH-008 + SEC-MUST-004: inactive account cannot access protected endpoints."""
        super_user = SuperAdminFactory(username="sa_then_deactivated")
        auth = get_auth_header(api_client, "sa_then_deactivated")

        # Deactivate after obtaining token
        super_user.is_active = False
        super_user.save()

        api_client.credentials(HTTP_AUTHORIZATION=auth)
        resp = api_client.get(USERS_URL)
        # JWTAuthentication validates the token, then IsAuthenticated checks is_active
        assert resp.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )
