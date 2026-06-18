# Sprint Contract: SPEC-AUTH-001

**Harness:** thorough  
**Evaluator Profile:** strict  
**Coverage Hard Threshold:** 90%+ for `accounts/` app  
**Date:** 2026-06-18

---

## Done Criteria

### AC-AUTH-001: Valid username+password login
- [ ] `POST /api/auth/login/` with valid credentials returns HTTP 200
- [ ] Response body contains `access` field (JWT string, non-empty)
- [ ] Response body contains `refresh` field (JWT string, non-empty)
- [ ] Response body does NOT contain `password`, `password_hash`, or any password derivative
- [ ] `access` token payload does NOT contain a `role` field (role always from DB per REQ-AUTH-015)
- [ ] Content-Type header is `application/json`

### AC-AUTH-002: Invalid password login
- [ ] `POST /api/auth/login/` with wrong password returns HTTP 401
- [ ] Response body does NOT contain field-specific error (same generic message for wrong-password AND non-existent-user)
- [ ] Response body does NOT contain `access` or `refresh` fields

### AC-AUTH-003: Deactivated account login
- [ ] `POST /api/auth/login/` with `is_active=False` user returns HTTP 401
- [ ] Response body does NOT contain `access` or `refresh` fields
- [ ] Response body does NOT reveal that the account is deactivated (generic 401)

### AC-AUTH-004: Valid Refresh Token → new Access Token
- [ ] `POST /api/auth/token/refresh/` with valid refresh token returns HTTP 200
- [ ] Response body contains new `access` field (non-empty)
- [ ] Rotation behavior is consistent with `ROTATE_REFRESH_TOKENS` setting

### AC-AUTH-005: Expired Access → refresh → new access → access granted
- [ ] Use freezegun to advance time past `ACCESS_TOKEN_LIFETIME`
- [ ] Expired access → protected endpoint → HTTP 401
- [ ] `POST /api/auth/token/refresh/` with valid refresh → HTTP 200, new `access`
- [ ] New access → protected endpoint → HTTP 200
- [ ] Entire flow is a single test method

### AC-AUTH-006: Logout → blacklisted refresh reuse → 401
- [ ] `POST /api/auth/logout/` with valid refresh returns HTTP 200 (or 204)
- [ ] DB assertion: JTI is present in `BlacklistedToken` table
- [ ] Reuse → HTTP 401
- [ ] Second logout with same token → HTTP 401 (idempotency)

### AC-AUTH-007: ADMIN requests /api/admin/users/ → 403
- [ ] ADMIN-role access token → `GET /api/admin/users/` → HTTP 403
- [ ] Response body does NOT leak user list data
- [ ] DB query count assertion: no list query performed before 403 returned

### AC-AUTH-008: SuperAdmin creates admin; duplicate → 400
- [ ] `POST /api/admin/users/` by SUPER_ADMIN → HTTP 201
- [ ] Response contains `id`, `username`, `role`, `is_active`
- [ ] Response does NOT contain `password` or any password hash
- [ ] DB: new user exists with hashed password (not plaintext)
- [ ] Duplicate username → HTTP 400 with `username` field error

### AC-AUTH-009: SuperAdmin resets password; <8 chars → 400
- [ ] Valid password (≥8 chars) → HTTP 200
- [ ] DB: password hash updated
- [ ] Password exactly 8 chars → HTTP 200 (boundary inclusive)
- [ ] Password 7 chars → HTTP 400
- [ ] Empty password → HTTP 400
- [ ] HTTP 400 response identifies `password` field as the error source

### AC-AUTH-010: SuperAdmin deactivates admin → tokens invalidated
- [ ] `PATCH /api/admin/users/{id}/` with `is_active=false` → HTTP 200
- [ ] DB: target user `is_active=False`
- [ ] DB: all `OutstandingToken` records for that user are in `BlacklistedToken`
- [ ] Token invalidation occurs synchronously (same request-response cycle)
- [ ] `POST /api/auth/token/refresh/` with deactivated user's refresh → HTTP 401

### AC-AUTH-011: Unauthenticated request → 401
- [ ] No Authorization header → HTTP 401
- [ ] `Authorization: Bearer invalid_string` → HTTP 401
- [ ] `Authorization: Token abc123` (wrong scheme) → HTTP 401
- [ ] Response does NOT leak endpoint data

### AC-AUTH-012: SuperAdmin lists admins, no password field
- [ ] `GET /api/admin/users/` by SUPER_ADMIN → HTTP 200
- [ ] Response is a list of user objects
- [ ] No user object contains `password`, `password_hash`, `passwd`, or `pwd` key
- [ ] Each user object contains: `id`, `username`, `role`, `is_active`

### AC-AUTH-013: Expired Refresh Token → 401
- [ ] Use freezegun to advance time past `REFRESH_TOKEN_LIFETIME`
- [ ] `POST /api/auth/token/refresh/` with expired refresh → HTTP 401
- [ ] Response does NOT contain new `access` token

---

## Edge Cases

- EDGE-001: JWT with forged role claim → IsSuperAdmin must use DB-sourced role (mock test)
- EDGE-002: `alg: none` JWT → HTTP 401 (simplejwt config must exclude `none`)
- EDGE-003: Malformed Authorization header variants → HTTP 401
- EDGE-004: Expired access token replay after refresh → HTTP 401
- EDGE-005: Refresh token cross-user attempt → validate user ownership
- EDGE-006: Concurrent deactivation + token refresh → deactivation wins
- EDGE-007: Empty username/password fields → HTTP 400
- EDGE-008: SQL injection in username field → HTTP 401 or 400, ORM protects
- EDGE-009: Extremely long input (10K chars) → HTTP 400, no bcrypt DoS
- EDGE-010: Password exactly 8 chars → HTTP 200 (boundary inclusive)
- EDGE-011: Password exactly 7 chars → HTTP 400
- EDGE-012: Logout with access token (not refresh) → HTTP 400 or 401
- EDGE-013: Token refresh after password reset → [PENDING SPEC CLARIFICATION]
- EDGE-014: Re-login after re-activation → HTTP 200, old tokens still blacklisted
- EDGE-015: SUPER_ADMIN self-deactivation → [PENDING SPEC CLARIFICATION]
- EDGE-016: ADMIN attempting to reset another ADMIN's password → HTTP 403
- EDGE-017: JWT `nbf` in the future → HTTP 401

---

## Hard Thresholds

| Threshold | Value | Consequence |
|-----------|-------|-------------|
| Coverage — `accounts/` app | >= 90% | Craft FAIL → Overall FAIL |
| Security findings | 0 (zero) | Security FAIL → Overall FAIL |
| Dimension minimum score | 0.80 each | Overall FAIL |

---

## Security Must-Pass Criteria

- **SEC-MUST-001**: JWT role claim injection — IsSuperAdmin reads DB role, not JWT payload
- **SEC-MUST-002**: Password never exposed via any API endpoint
- **SEC-MUST-003**: Token blacklist enforcement after logout (DB-level assertion)
- **SEC-MUST-004**: is_active=False accounts cannot obtain tokens
- **SEC-MUST-005**: alg:none rejection — ALGORITHMS setting excludes `none`

---

## Additional Test Files Required

Beyond the original plan, these files MUST be created:
- `accounts/tests/test_security_must_pass.py` — SEC-MUST-001 through SEC-MUST-005
- `accounts/tests/test_account_deactivation.py` — AC-AUTH-010 + EDGE-006, 013, 014

---

## Resolved Clarifications

1. **EDGE-013**: Password reset does NOT invalidate existing Refresh Tokens. REQ-AUTH-022 applies only to `is_active=False`. (User confirmed 2026-06-18)
2. **EDGE-015**: SUPER_ADMIN self-deactivation is BLOCKED → HTTP 400. System must always have at least one active SUPER_ADMIN. (User confirmed 2026-06-18)
