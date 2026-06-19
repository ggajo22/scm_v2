"""
Tests for Login endpoint (AC-AUTH-001, 002, 003).
POST /api/auth/login/
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from accounts.tests.factories import AdminUserFactory, InactiveAdminFactory

AdminUser = get_user_model()

LOGIN_URL = "/api/auth/login/"


@pytest.mark.django_db
class TestLoginSuccess:
    """AC-AUTH-001: Valid login returns access + refresh tokens."""

    def test_valid_login_returns_200(self, api_client):
        AdminUserFactory(username="valid_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "valid_user", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_valid_login_returns_access_token(self, api_client):
        AdminUserFactory(username="access_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "access_user", "password": "testpass123"},
            format="json",
        )
        assert "access" in resp.data

    def test_valid_login_returns_refresh_token(self, api_client):
        AdminUserFactory(username="refresh_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "refresh_user", "password": "testpass123"},
            format="json",
        )
        assert "refresh" in resp.data

    def test_response_does_not_contain_password(self, api_client):
        """AC-AUTH-001 + SEC-MUST-002: password must never appear in response."""
        AdminUserFactory(username="no_pass_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "no_pass_user", "password": "testpass123"},
            format="json",
        )
        assert "password" not in resp.data

    def test_response_does_not_contain_role_in_jwt_payload(self, api_client):
        """REQ-AUTH-015: role must NOT be embedded in JWT payload."""
        import base64
        import json

        AdminUserFactory(username="no_role_jwt_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "no_role_jwt_user", "password": "testpass123"},
            format="json",
        )
        access_token = resp.data["access"]
        payload_part = access_token.split(".")[1]
        # Add padding
        padding = 4 - len(payload_part) % 4
        if padding != 4:
            payload_part += "=" * padding
        payload = json.loads(base64.urlsafe_b64decode(payload_part))
        assert "role" not in payload


@pytest.mark.django_db
class TestLoginInvalidCredentials:
    """AC-AUTH-002: Invalid credentials → HTTP 401, generic message."""

    def test_wrong_password_returns_401(self, api_client):
        AdminUserFactory(username="wrong_pass_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "wrong_pass_user", "password": "wrongpassword"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_nonexistent_user_returns_401(self, api_client):
        resp = api_client.post(
            LOGIN_URL,
            {"username": "ghost_user", "password": "anything"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_wrong_password_generic_message(self, api_client):
        """Both wrong password and non-existent user return identical error (anti-enumeration)."""
        AdminUserFactory(username="msg_user")
        resp_wrong_pass = api_client.post(
            LOGIN_URL,
            {"username": "msg_user", "password": "wrongpassword"},
            format="json",
        )
        resp_no_user = api_client.post(
            LOGIN_URL,
            {"username": "nonexistent_user_abc", "password": "anything"},
            format="json",
        )
        assert resp_wrong_pass.data.get("detail") == resp_no_user.data.get("detail")

    def test_empty_username_returns_400(self, api_client):
        """EDGE-007: empty username → HTTP 400."""
        resp = api_client.post(
            LOGIN_URL,
            {"username": "", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_password_returns_400(self, api_client):
        """EDGE-007: empty password → HTTP 400."""
        resp = api_client.post(
            LOGIN_URL,
            {"username": "some_user", "password": ""},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginInactiveUser:
    """AC-AUTH-003 + REQ-AUTH-009: Inactive user login → HTTP 401, no deactivation hint."""

    def test_inactive_user_cannot_login(self, api_client):
        InactiveAdminFactory(username="inactive_user")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "inactive_user", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_response_has_no_tokens(self, api_client):
        InactiveAdminFactory(username="inactive_no_tokens")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "inactive_no_tokens", "password": "testpass123"},
            format="json",
        )
        assert "access" not in resp.data
        assert "refresh" not in resp.data

    def test_inactive_user_error_matches_invalid_credentials_message(self, api_client):
        """AC-AUTH-003: same generic message as wrong credentials — no deactivation hint."""
        InactiveAdminFactory(username="inactive_hint_check")
        AdminUserFactory(username="active_hint_check")

        resp_inactive = api_client.post(
            LOGIN_URL,
            {"username": "inactive_hint_check", "password": "testpass123"},
            format="json",
        )
        resp_wrong_pass = api_client.post(
            LOGIN_URL,
            {"username": "active_hint_check", "password": "wrongpassword"},
            format="json",
        )
        assert resp_inactive.data.get("detail") == resp_wrong_pass.data.get("detail")
