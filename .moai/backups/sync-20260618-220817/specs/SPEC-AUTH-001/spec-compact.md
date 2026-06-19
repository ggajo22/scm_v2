# SPEC-AUTH-001 Compact Reference
# For use by implementation agents — English only

## Metadata
- ID: SPEC-AUTH-001
- Priority: critical
- Harness: thorough
- Tech: Django 5.0+ / DRF / djangorestframework-simplejwt / MySQL 8.0 / React + TypeScript

---

## Requirements (EARS)

### Module 1: Authentication

| ID | Requirement |
|----|-------------|
| REQ-AUTH-001 | The system shall use JWT authentication with Access Token TTL=15min and Refresh Token TTL=24h. |
| REQ-AUTH-002 | When a valid username+password login request is received, the system shall return both Access Token and Refresh Token. |
| REQ-AUTH-003 | When an invalid username or password is submitted, the system shall return HTTP 401 without revealing which field is incorrect. |
| REQ-AUTH-004 | When a valid Refresh Token is submitted to the refresh endpoint, the system shall issue a new Access Token. |
| REQ-AUTH-005 | When an expired or invalidated Refresh Token is submitted, the system shall return HTTP 401. |
| REQ-AUTH-006 | When a logout request is received, the system shall invalidate the submitted Refresh Token server-side. |
| REQ-AUTH-007 | If a blacklisted Refresh Token is used for token refresh, then the system shall return HTTP 401. |
| REQ-AUTH-008 | While an admin session is active, the system shall validate the Bearer Access Token on every **protected** API request. (Public endpoints such as login and token refresh are excluded.) |
| REQ-AUTH-009 | If a login attempt is made with a deactivated account (is_active=False), then the system shall return HTTP 401. |

### Module 2: RBAC

| ID | Requirement |
|----|-------------|
| REQ-AUTH-010 | The system shall assign each admin account exactly one role: SUPER_ADMIN or ADMIN. |
| REQ-AUTH-011 | While an authenticated SUPER_ADMIN accesses the system, the system shall permit all features including admin account management. |
| REQ-AUTH-012 | While an authenticated ADMIN accesses the system, the system shall permit book listings and order management only. |
| REQ-AUTH-013 | If an ADMIN role user requests access to `/api/admin/users/`, `/api/admin/users/{id}/`, or `/api/admin/users/{id}/reset-password/`, then the system shall return HTTP 403 Forbidden. |
| REQ-AUTH-014 | If an unauthenticated request accesses any protected API endpoint, then the system shall return HTTP 401 Unauthorized. |
| REQ-AUTH-015 | The system shall always determine access based on the server-side current role, regardless of any role claim present in the JWT payload. (The JWT payload role claim is not used for access control decisions.) |

### Module 3: User Management (SuperAdmin only)

| ID | Requirement |
|----|-------------|
| REQ-AUTH-016 | Where a SUPER_ADMIN uses the user management feature, the system shall allow creating new admin accounts with username, initial password, and role. |
| REQ-AUTH-017 | Where a SUPER_ADMIN uses the user management feature, the system shall allow updating username, role, and is_active status of existing admin accounts. |
| REQ-AUTH-018 | Where a SUPER_ADMIN uses the user management feature, the system shall allow directly setting a new password for any admin without email flow. |
| REQ-AUTH-019 | Where a SUPER_ADMIN uses the user management feature, the system shall allow listing all admin accounts. |
| REQ-AUTH-020 | If a duplicate username is used during account creation, then the system shall return HTTP 400 with a duplicate username error message. |
| REQ-AUTH-021 | If a password shorter than 8 characters is set, then the system shall return HTTP 400 with a validation error message. |
| REQ-AUTH-022 | When a SUPER_ADMIN deactivates an admin account (is_active=False), the system shall immediately invalidate that account's existing Refresh Tokens. |

---

## Acceptance Scenarios (Given/When/Then)

| ID | Scenario | Result |
|----|----------|--------|
| AC-AUTH-001 | Valid username+password login | HTTP 200, access + refresh tokens returned |
| AC-AUTH-002 | Invalid password login | HTTP 401, no token, no field-specific error hint |
| AC-AUTH-003 | Deactivated account login | HTTP 401, no token |
| AC-AUTH-004 | Valid Refresh Token → new Access Token | HTTP 200, new access token |
| AC-AUTH-005 | Expired Access Token → 401 → refresh with valid Refresh Token → new Access Token → access granted | Full flow passes |
| AC-AUTH-013 | Expired Refresh Token submitted to refresh endpoint | HTTP 401, no new token issued |
| AC-AUTH-006 | Logout → blacklisted Refresh Token reuse → 401 | HTTP 401 on reuse |
| AC-AUTH-007 | ADMIN role requests `/api/admin/users/` | HTTP 403 Forbidden |
| AC-AUTH-008 | SuperAdmin creates new admin account | HTTP 201, account created; duplicate → HTTP 400 |
| AC-AUTH-009 | SuperAdmin resets admin password directly | HTTP 200; old password invalid, new password valid; <8 chars → HTTP 400 |
| AC-AUTH-010 | SuperAdmin deactivates admin → existing token invalidated | HTTP 401 on token refresh attempt |
| AC-AUTH-011 | Unauthenticated request to protected endpoint | HTTP 401 |
| AC-AUTH-012 | SuperAdmin lists all admin accounts | HTTP 200, list returned, no password field |

---

## API Endpoints

| Method | Path | Permission |
|--------|------|------------|
| POST | `/api/auth/login/` | Anonymous |
| POST | `/api/auth/logout/` | Authenticated |
| POST | `/api/auth/token/refresh/` | Authenticated (valid Refresh Token) |
| GET | `/api/admin/users/` | SuperAdmin only |
| POST | `/api/admin/users/` | SuperAdmin only |
| GET | `/api/admin/users/{id}/` | SuperAdmin only |
| PUT | `/api/admin/users/{id}/` | SuperAdmin only |
| PATCH | `/api/admin/users/{id}/` | SuperAdmin only |
| POST | `/api/admin/users/{id}/reset-password/` | SuperAdmin only |

---

## Files to Create

### Backend (Django)
```
accounts/
  models.py               # AdminUser(AbstractUser) with role field
  views.py                # AdminLoginView, AdminLogoutView, AdminTokenRefreshView, AdminUserViewSet
  serializers.py          # Login, AdminUserList, AdminUserCreate, AdminUserUpdate, PasswordReset
  permissions.py          # IsSuperAdmin, IsAdminOrSuperAdmin
  urls.py                 # Auth and admin user routes
  tests/
    test_login.py
    test_logout.py
    test_token_refresh.py
    test_permissions.py
    test_admin_user_management.py
```

### Frontend (React + TypeScript)
```
src/
  pages/
    LoginPage.tsx
    AdminUsersPage.tsx    # SuperAdmin only
  services/
    auth.ts               # login, logout, refreshToken API calls
  store/
    authStore.ts          # Zustand: access token, role, user info
  hooks/
    useAuth.ts
  types/
    models.ts             # AdminUser type, Role enum
```

### Configuration
```
config/settings/base.py   # SIMPLE_JWT settings, INSTALLED_APPS += token_blacklist
.env.example              # SECRET_KEY, SIMPLE_JWT signing key
```

---

## Exclusions (What NOT to Build)

1. Social login (Google, GitHub, OAuth)
2. Multi-factor authentication (MFA/TOTP)
3. Email-based password reset flow
4. Audit log
5. Login attempt lockout (account lockout after N failures)
6. Public/customer user account system
7. Fine-grained per-resource permissions
8. Refresh Token auto-rotation strategy
9. Immediate invalidation of existing Access Tokens on account deactivation — existing Access Tokens remain valid until expiry (v1); only Refresh Tokens are immediately invalidated (REQ-AUTH-022)

---

## Key Constraints for Implementation

- **Login identifier**: `username` only — NOT email
- **Role validation**: ALWAYS query database — NEVER use JWT payload role claim (REQ-AUTH-015)
- **Password minimum**: 8 characters (no complexity rules beyond length)
- **Token storage (frontend)**: Prefer httpOnly cookie or in-memory; avoid localStorage (XSS risk)
- **Blacklist cleanup**: Expired tokens in `outstanding_token` table should be periodically pruned
- **RBAC enforcement**: DRF `permission_classes` per view — not middleware-level
