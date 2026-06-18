"""
Tests for Token Refresh endpoint (AC-AUTH-004, 005, 013).
POST /api/auth/token/refresh/
"""

import pytest
from django.conf import settings
from freezegun import freeze_time
from rest_framework import status

from accounts.tests.factories import AdminUserFactory

LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/token/refresh/"


def get_tokens(api_client, username, password="testpass123"):
    resp = api_client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
    )
    return resp.data


@pytest.mark.django_db
class TestTokenRefresh:
    """AC-AUTH-004: Valid refresh token → new access token."""

    def test_valid_refresh_returns_200(self, api_client):
        AdminUserFactory(username="refresh_ok_user")
        tokens = get_tokens(api_client, "refresh_ok_user")
        resp = api_client.post(
            REFRESH_URL,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

    def test_valid_refresh_returns_new_access_token(self, api_client):
        AdminUserFactory(username="new_access_user")
        tokens = get_tokens(api_client, "new_access_user")
        resp = api_client.post(
            REFRESH_URL,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        assert "access" in resp.data


@pytest.mark.django_db
class TestExpiredRefreshToken:
    """AC-AUTH-013: Expired refresh token → HTTP 401."""

    def test_expired_refresh_token_returns_401(self, api_client):
        """AC-AUTH-013: freezegun test — refresh token expired after TTL."""

        AdminUserFactory(username="expired_refresh_user")

        # Login to get tokens
        with freeze_time("2026-01-01 00:00:00"):
            tokens = get_tokens(api_client, "expired_refresh_user")

        # Move 25 hours ahead (refresh TTL is 24h)
        with freeze_time("2026-01-02 01:00:00"):
            resp = api_client.post(
                REFRESH_URL,
                {"refresh": tokens["refresh"]},
                format="json",
            )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestExpiredAccessToken:
    """AC-AUTH-005: Expired access token rejected; refresh flow restores access."""

    def test_expired_access_token_rejected(self, api_client):
        """AC-AUTH-005 part 1: freezegun — access token expired after 15min."""
        AdminUserFactory(username="expired_access_user")

        with freeze_time("2026-01-01 00:00:00"):
            tokens = get_tokens(api_client, "expired_access_user")

        # Move 20 minutes ahead (access TTL is 15min)
        with freeze_time("2026-01-01 00:20:00"):
            api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
            # Try to access a protected endpoint
            resp = api_client.get("/api/admin/users/")

        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_access_then_refresh_then_protected_endpoint_succeeds(self, api_client):
        """AC-AUTH-005 part 2: full flow — expired access → refresh → new access → 200."""
        from accounts.tests.factories import SuperAdminFactory

        SuperAdminFactory(username="full_flow_sa")

        with freeze_time("2026-01-01 00:00:00"):
            tokens = get_tokens(api_client, "full_flow_sa")

        # Step 1: access token expires after 20 minutes
        with freeze_time("2026-01-01 00:20:00"):
            # Step 2: use refresh token to obtain a new access token
            refresh_resp = api_client.post(
                REFRESH_URL,
                {"refresh": tokens["refresh"]},
                format="json",
            )
            assert refresh_resp.status_code == status.HTTP_200_OK
            new_access = refresh_resp.data["access"]

            # Step 3: new access token successfully accesses protected endpoint
            api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access}")
            resp = api_client.get("/api/admin/users/")
            assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestJWTSettings:
    """Cycle 2: Assert SIMPLE_JWT configuration is correct."""

    def test_access_token_lifetime_is_15_minutes(self):
        from datetime import timedelta

        assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"] == timedelta(minutes=15)

    def test_refresh_token_lifetime_is_24_hours(self):
        from datetime import timedelta

        assert settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"] == timedelta(hours=24)

    def test_algorithms_does_not_include_none(self):
        """SEC-MUST-005: 'none' algorithm must not be in ALGORITHMS list."""
        assert "none" not in settings.SIMPLE_JWT["ALGORITHMS"]
        assert "None" not in settings.SIMPLE_JWT["ALGORITHMS"]

    def test_algorithm_is_hs256(self):
        assert settings.SIMPLE_JWT["ALGORITHM"] == "HS256"

    def test_role_not_in_jwt_claims(self):
        """REQ-AUTH-015: role should not be added to JWT claims."""
        # Ensure no custom claim serializer adds 'role' to the token
        # Default TOKEN_OBTAIN_SERIALIZER means no role injection
        assert "role" not in str(settings.SIMPLE_JWT)
