"""
Tests for Logout endpoint (AC-AUTH-006).
POST /api/auth/logout/
"""

import pytest
from rest_framework import status

from accounts.tests.factories import AdminUserFactory

LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"


def get_tokens(api_client, username, password="testpass123"):
    resp = api_client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
    )
    return resp.data


@pytest.mark.django_db
class TestLogout:
    """AC-AUTH-006: Logout blacklists refresh token server-side."""

    def test_logout_returns_200(self, api_client):
        AdminUserFactory(username="logout_user")
        tokens = get_tokens(api_client, "logout_user")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = api_client.post(
            LOGOUT_URL,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_logout_blacklists_refresh_token_in_db(self, api_client):
        """SEC-MUST-003: DB-level assertion that JTI is in BlacklistedToken."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        AdminUserFactory(username="blacklist_user")
        tokens = get_tokens(api_client, "blacklist_user")
        refresh_token = tokens["refresh"]

        # Get JTI before blacklisting
        decoded = RefreshToken(refresh_token)
        jti = decoded["jti"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        api_client.post(
            LOGOUT_URL,
            {"refresh": refresh_token},
            format="json",
        )

        assert BlacklistedToken.objects.filter(token__jti=jti).exists()

    def test_blacklisted_token_reuse_returns_401(self, api_client):
        """AC-AUTH-006 + REQ-AUTH-007: reusing blacklisted refresh token → 401."""
        from rest_framework import status as drf_status

        AdminUserFactory(username="reuse_token_user")
        tokens = get_tokens(api_client, "reuse_token_user")
        refresh_token = tokens["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        # First logout — blacklist the token
        api_client.post(
            LOGOUT_URL,
            {"refresh": refresh_token},
            format="json",
        )

        # Try to use the blacklisted refresh token
        api_client.credentials()
        resp = api_client.post(
            "/api/auth/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )
        assert resp.status_code == drf_status.HTTP_401_UNAUTHORIZED

    def test_logout_without_auth_returns_401(self, api_client):
        """REQ-AUTH-014: unauthenticated logout → 401."""
        resp = api_client.post(
            LOGOUT_URL,
            {"refresh": "some.fake.token"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_without_refresh_token_returns_400(self, api_client):
        """Missing refresh token body → 400."""
        AdminUserFactory(username="no_refresh_user")
        tokens = get_tokens(api_client, "no_refresh_user")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = api_client.post(LOGOUT_URL, {}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_with_invalid_token_string_returns_400(self, api_client):
        """Logout with malformed refresh token → 400 (TokenError path)."""
        AdminUserFactory(username="invalid_token_user")
        tokens = get_tokens(api_client, "invalid_token_user")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = api_client.post(
            LOGOUT_URL,
            {"refresh": "not.a.valid.token.string"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
