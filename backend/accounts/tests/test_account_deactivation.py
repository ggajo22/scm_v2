"""
Tests for account deactivation → token invalidation (AC-AUTH-010, REQ-AUTH-022).
"""

import pytest
from rest_framework import status

from accounts.tests.factories import AdminUserFactory, SuperAdminFactory

LOGIN_URL = "/api/auth/login/"
REFRESH_URL = "/api/auth/token/refresh/"
USERS_URL = "/api/admin/users/"


def get_tokens(api_client, username, password="testpass123"):
    resp = api_client.post(
        LOGIN_URL,
        {"username": username, "password": password},
        format="json",
    )
    return resp.data


def get_auth_header(api_client, username, password="testpass123"):
    tokens = get_tokens(api_client, username, password)
    return f"Bearer {tokens['access']}"


@pytest.mark.django_db
class TestDeactivationTokenInvalidation:
    """
    AC-AUTH-010 + REQ-AUTH-022 [CRITICAL]:
    Deactivating an account immediately invalidates all existing refresh tokens.
    """

    def test_deactivation_blacklists_all_refresh_tokens(self, api_client):
        """DB-level assertion: BlacklistedToken exists after deactivation."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        target = AdminUserFactory(username="deactivate_target")
        SuperAdminFactory(username="sa_deactivator")

        # Target user gets refresh token
        tokens = get_tokens(api_client, "deactivate_target")
        jti = RefreshToken(tokens["refresh"])["jti"]

        # SA deactivates target
        sa_auth = get_auth_header(api_client, "sa_deactivator")
        api_client.credentials(HTTP_AUTHORIZATION=sa_auth)
        resp = api_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

        # DB assertion: token must be blacklisted
        assert BlacklistedToken.objects.filter(token__jti=jti).exists(), (
            "Refresh token JTI must be in BlacklistedToken after account deactivation"
        )

    def test_refresh_token_rejected_after_deactivation(self, api_client):
        """After deactivation, the pre-existing refresh token → 401."""
        target = AdminUserFactory(username="refresh_after_deactivate")
        SuperAdminFactory(username="sa_deactivator2")

        # Target gets tokens
        tokens = get_tokens(api_client, "refresh_after_deactivate")
        refresh_token = tokens["refresh"]

        # SA deactivates target
        sa_auth = get_auth_header(api_client, "sa_deactivator2")
        api_client.credentials(HTTP_AUTHORIZATION=sa_auth)
        api_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )

        # Try to use the pre-existing refresh token → must fail
        api_client.credentials()
        resp = api_client.post(
            REFRESH_URL,
            {"refresh": refresh_token},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_multiple_refresh_tokens_all_blacklisted(self, api_client):
        """If user has multiple outstanding tokens, all are invalidated on deactivation."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        target = AdminUserFactory(username="multi_token_target")
        SuperAdminFactory(username="sa_multi_deactivator")

        # Get multiple refresh tokens for target (login twice)
        tokens1 = get_tokens(api_client, "multi_token_target")
        tokens2 = get_tokens(api_client, "multi_token_target")

        jti1 = RefreshToken(tokens1["refresh"])["jti"]
        jti2 = RefreshToken(tokens2["refresh"])["jti"]

        # SA deactivates target
        sa_auth = get_auth_header(api_client, "sa_multi_deactivator")
        api_client.credentials(HTTP_AUTHORIZATION=sa_auth)
        api_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )

        # Both tokens should be blacklisted
        assert BlacklistedToken.objects.filter(token__jti=jti1).exists()
        assert BlacklistedToken.objects.filter(token__jti=jti2).exists()

    def test_newly_created_user_signal_does_nothing(self):
        """Signal with created=True should return early without attempting blacklisting."""
        from unittest.mock import MagicMock

        from accounts.signals import invalidate_tokens_on_deactivation

        mock_user = MagicMock()
        mock_user.is_active = False  # Even if inactive, created=True means skip

        # Should not raise any exceptions
        invalidate_tokens_on_deactivation(
            sender=None,
            instance=mock_user,
            created=True,
        )

    def test_signal_handles_blacklist_exception_gracefully(self):
        """Signal exception handler prevents save from breaking."""
        from unittest.mock import MagicMock, patch

        from accounts.signals import invalidate_tokens_on_deactivation

        mock_user = MagicMock()
        mock_user.is_active = False
        mock_user.pk = 999

        # Patch the import inside the function by making the import fail
        with patch.dict(
            "sys.modules",
            {"rest_framework_simplejwt.token_blacklist.models": None},
        ):
            # Should not raise — exception is caught and logged
            invalidate_tokens_on_deactivation(
                sender=None,
                instance=mock_user,
                created=False,
            )

    def test_activation_does_not_unblacklist_tokens(self, api_client):
        """Re-activating an account does NOT unblacklist previously invalidated tokens."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        target = AdminUserFactory(username="reactivate_target")
        SuperAdminFactory(username="sa_reactivator")

        tokens = get_tokens(api_client, "reactivate_target")
        jti = RefreshToken(tokens["refresh"])["jti"]

        sa_auth = get_auth_header(api_client, "sa_reactivator")
        api_client.credentials(HTTP_AUTHORIZATION=sa_auth)

        # Deactivate
        api_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": False},
            format="json",
        )

        # Re-activate
        api_client.patch(
            f"{USERS_URL}{target.id}/",
            {"is_active": True},
            format="json",
        )

        # Old token must still be blacklisted
        assert BlacklistedToken.objects.filter(token__jti=jti).exists()
