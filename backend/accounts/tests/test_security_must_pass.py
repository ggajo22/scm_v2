"""
Security must-pass tests (SEC-MUST-001 through SEC-MUST-005).
ALL tests in this file are HARD requirements — any failure = OVERALL FAIL.
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status

from accounts.tests.factories import AdminUserFactory, SuperAdminFactory

AdminUser = get_user_model()

LOGIN_URL = "/api/auth/login/"
USERS_URL = "/api/admin/users/"
LOGOUT_URL = "/api/auth/logout/"
REFRESH_URL = "/api/auth/token/refresh/"


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
class TestSecMust001RoleFromDB:
    """
    SEC-MUST-001: IsSuperAdmin reads role from DB (request.user.role), NOT from JWT payload.

    Scenario: JWT was issued when user had SUPER_ADMIN role.
    After DB role is demoted to ADMIN, the same JWT must be rejected.
    """

    def test_jwt_super_admin_claim_rejected_when_db_says_admin(self, api_client):
        """Core SEC-MUST-001 test: JWT payload ≠ DB role → DB wins."""
        super_user = SuperAdminFactory(username="sec001_sa")
        auth = get_auth_header(api_client, "sec001_sa")

        # Demote in DB after JWT was issued
        super_user.role = AdminUser.Role.ADMIN
        super_user.save()

        api_client.credentials(HTTP_AUTHORIZATION=auth)
        resp = api_client.get(USERS_URL)

        # DB says ADMIN → 403 even with a SUPER_ADMIN-era JWT
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_isa_permission_uses_request_user_not_token(self):
        """Unit test: IsSuperAdmin accesses request.user.role (from DB), not token claims."""
        from unittest.mock import MagicMock

        from accounts.permissions import IsSuperAdmin

        perm = IsSuperAdmin()

        # Simulate: user object has ADMIN role (DB state)
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.role = AdminUser.Role.ADMIN

        mock_request = MagicMock()
        mock_request.user = mock_user

        result = perm.has_permission(mock_request, None)
        assert result is False, "ADMIN role must not pass IsSuperAdmin check"

    def test_super_admin_permission_unit(self):
        """Unit test: IsSuperAdmin grants access when DB role = SUPER_ADMIN."""
        from unittest.mock import MagicMock

        from accounts.permissions import IsSuperAdmin

        perm = IsSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.role = AdminUser.Role.SUPER_ADMIN

        mock_request = MagicMock()
        mock_request.user = mock_user

        result = perm.has_permission(mock_request, None)
        assert result is True

    def test_is_super_admin_rejects_inactive_user(self):
        """IsSuperAdmin.has_permission returns False when user.is_active is False."""
        from unittest.mock import MagicMock

        from accounts.permissions import IsSuperAdmin

        perm = IsSuperAdmin()
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = False  # inactive
        mock_user.role = AdminUser.Role.SUPER_ADMIN

        mock_request = MagicMock()
        mock_request.user = mock_user

        assert perm.has_permission(mock_request, None) is False


@pytest.mark.django_db
class TestSecMust002PasswordNeverExposed:
    """SEC-MUST-002: Password must never appear in any API response."""

    def test_login_response_no_password(self, api_client):
        AdminUserFactory(username="sec002_login")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "sec002_login", "password": "testpass123"},
            format="json",
        )
        assert "password" not in resp.data

    def test_user_list_no_password(self, api_client):
        SuperAdminFactory(username="sec002_sa")
        AdminUserFactory(username="sec002_admin")
        auth = get_auth_header(api_client, "sec002_sa")
        api_client.credentials(HTTP_AUTHORIZATION=auth)
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_200_OK
        # Check no password field in any item
        for user_data in resp.data:
            assert "password" not in user_data

    def test_user_create_response_no_password(self, api_client):
        SuperAdminFactory(username="sec002_creator")
        auth = get_auth_header(api_client, "sec002_creator")
        api_client.credentials(HTTP_AUTHORIZATION=auth)
        resp = api_client.post(
            USERS_URL,
            {"username": "sec002_new", "password": "securepass1", "role": "admin"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert "password" not in resp.data

    def test_400_error_no_password_leakage(self, api_client):
        """400 error response must not echo back password value."""
        SuperAdminFactory(username="sec002_400sa")
        auth = get_auth_header(api_client, "sec002_400sa")
        api_client.credentials(HTTP_AUTHORIZATION=auth)
        # Short password → 400
        resp = api_client.post(
            USERS_URL,
            {"username": "sec002_err", "password": "short", "role": "admin"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        # SEC-MUST-002: submitted password value must NOT be echoed in the error body
        assert "short" not in str(resp.data)

    def test_serializer_fields_no_password(self):
        """Verify serializer fields list does not expose password."""
        from accounts.serializers import AdminUserListSerializer

        serializer = AdminUserListSerializer()
        field_names = list(serializer.fields.keys())
        assert "password" not in field_names


@pytest.mark.django_db
class TestSecMust003TokenBlacklistEnforcement:
    """SEC-MUST-003: Token blacklist is enforced after logout with DB-level assertion."""

    def test_logout_creates_db_record(self, api_client):
        """DB-level assertion: BlacklistedToken row exists after logout."""
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from rest_framework_simplejwt.tokens import RefreshToken

        AdminUserFactory(username="sec003_user")
        tokens = get_tokens(api_client, "sec003_user")
        jti = RefreshToken(tokens["refresh"])["jti"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = api_client.post(
            LOGOUT_URL,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        assert BlacklistedToken.objects.filter(token__jti=jti).exists(), (
            f"JTI {jti} must be in BlacklistedToken after logout"
        )

    def test_blacklisted_token_reuse_rejected(self, api_client):
        AdminUserFactory(username="sec003_reuse")
        tokens = get_tokens(api_client, "sec003_reuse")
        refresh = tokens["refresh"]

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        api_client.post(LOGOUT_URL, {"refresh": refresh}, format="json")

        api_client.credentials()
        resp = api_client.post(REFRESH_URL, {"refresh": refresh}, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSecMust004AlgNoneAndHs384Rejected:
    """
    SEC-MUST-004: alg:none and HS384-signed tokens must be rejected.
    Only HS256 is accepted (ALGORITHMS=["HS256"]).
    """

    def test_algorithms_list_excludes_none(self):
        """Verify SIMPLE_JWT settings explicitly exclude 'none'."""
        algorithms = settings.SIMPLE_JWT.get("ALGORITHMS", [])
        assert "none" not in algorithms, "Algorithm 'none' must never be in ALGORITHMS"
        assert "None" not in algorithms

    def test_algorithm_is_hs256_not_none(self):
        assert settings.SIMPLE_JWT["ALGORITHM"] == "HS256"

    @pytest.mark.django_db
    def test_alg_none_token_rejected(self, api_client):
        """EDGE-002: A JWT with alg:none → HTTP 401."""
        import base64
        import json

        # Craft a JWT with algorithm=none (unsigned)
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()

        payload = base64.urlsafe_b64encode(
            json.dumps({"user_id": 1, "token_type": "access"}).encode()
        ).rstrip(b"=").decode()

        # alg:none token has empty signature
        fake_token = f"{header}.{payload}."

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {fake_token}")
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.django_db
    def test_hs384_token_rejected(self, api_client):
        """EDGE-002b: A JWT signed with HS384 must be rejected (only HS256 accepted)."""
        import jwt as pyjwt
        from django.conf import settings as django_settings

        # Sign a token with HS384 — wrong algorithm
        hs384_token = pyjwt.encode(
            {"user_id": 99999, "token_type": "access"},
            django_settings.SECRET_KEY,
            algorithm="HS384",
        )

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {hs384_token}")
        resp = api_client.get(USERS_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSecMust005InactiveAccountBlocked:
    """
    SEC-MUST-005: is_active=False accounts cannot obtain tokens,
    and their pre-existing access tokens are rejected by JWTAuthentication.
    """

    def test_inactive_user_cannot_login(self, api_client):
        from accounts.tests.factories import InactiveAdminFactory

        InactiveAdminFactory(username="sec005_inactive")
        resp = api_client.post(
            LOGIN_URL,
            {"username": "sec005_inactive", "password": "testpass123"},
            format="json",
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert "access" not in resp.data

    def test_deactivated_user_access_token_rejected(self, api_client):
        """After deactivation, JWTAuthentication rejects existing access token → 401."""
        user = AdminUserFactory(username="sec005_deactivate_after")
        tokens = get_tokens(api_client, "sec005_deactivate_after")

        # Deactivate user directly (bypasses signal intentionally — testing JWTAuth behavior)
        user.is_active = False
        user.save()

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        resp = api_client.get(USERS_URL)
        # JWTAuthentication.get_user() checks is_active → authentication fails → 401
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
