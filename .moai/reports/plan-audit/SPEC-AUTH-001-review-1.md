# SPEC Review Report: SPEC-AUTH-001
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.52

---

## Must-Pass Results

- [FAIL] **MP-1 REQ Number Consistency**: REQ-AUTH-001 through REQ-AUTH-022 are sequential, zero-padded, no gaps, no duplicates. PASS component — but this must-pass criterion passes.
  - Evidence: spec.md:L49, L52, L55, ..., L120 — all 22 REQs present in order.

- [FAIL] **MP-2 EARS Format Compliance**: Every acceptance criterion in acceptance.md uses Given/When/Then (GWT) format. GWT test scenarios mislabeled as acceptance criteria are explicitly disqualifying per MP-2. Not a single AC uses one of the five EARS patterns.
  - Evidence: acceptance.md:L14 ("**Given** username이..."), L30 ("**Given** 데이터베이스에..."), L44 ("**Given** username이..."), L57 ("**Given** 관리자가..."), L71 ("**Given** 관리자의 Access Token이...") — all 12 ACs follow GWT, zero use EARS.
  - The preamble at acceptance.md:L5 explicitly states "각 시나리오는 Given-When-Then 형식으로 작성되며" confirming this is intentional GWT, not EARS.

- [FAIL] **MP-3 YAML Frontmatter Validity**: Two required fields are missing or renamed.
  - `created_at` field: ABSENT. Present as `created` at spec.md:L6. Required field name is `created_at`.
  - `labels` field: ABSENT entirely. spec.md:L1-10 — no `labels` key exists.
  - Present fields: `id` (L2), `version` (L3), `status` (L4), `priority` (L8). Two of six required fields are missing.

- [N/A] **MP-4 Section 22 Language Neutrality**: SPEC is scoped to a single Python/Django project. No multi-language tooling covered. Auto-pass.

**Summary: MP-1 PASS, MP-2 FAIL, MP-3 FAIL. Two must-pass failures = overall FAIL regardless of other scores.**

---

## Category Scores (0.0–1.0, rubric-anchored)

| Dimension    | Score | Rubric Band | Evidence |
|--------------|-------|-------------|----------|
| Clarity      | 0.75  | 0.75        | Most REQs are precise and unambiguous. Two clarity defects identified (D4, D6). |
| Completeness | 0.50  | 0.50        | YAML missing two fields (D1, D2). WHY/WHAT sections present. No HISTORY section header (section exists as table but no explicit heading). Exclusions present and specific (8 entries). |
| Testability  | 0.25  | 0.25        | All 12 ACs are GWT test scenarios, not binary-testable EARS criteria. Several ACs have non-concrete preconditions (D3). REQ-AUTH-015 is explicitly code-review-only, not testable by integration test. |
| Traceability | 0.50  | 0.50        | 18/22 REQs have adequate AC coverage. REQ-AUTH-005 (D5), REQ-AUTH-013 scope mismatch (D7), REQ-AUTH-015 untestable (D8), REQ-AUTH-017 partial coverage. |

---

## Defects Found

**D1. spec.md:L6** — `created` field used instead of required `created_at`. YAML frontmatter field name mismatch. The required field per MP-3 is `created_at`. — Severity: **critical** (MP-3 must-pass failure)

**D2. spec.md:L1-10** — `labels` field entirely absent from YAML frontmatter. Required field per MP-3. — Severity: **critical** (MP-3 must-pass failure)

**D3. acceptance.md:L1-241 (all ACs)** — All 12 acceptance criteria use Given/When/Then format. GWT test scenarios are explicitly excluded from EARS compliance. None of the 12 ACs matches any of the five EARS patterns (Ubiquitous, Event-driven, State-driven, Optional, Unwanted). MP-2 requires every AC to match one EARS pattern. — Severity: **critical** (MP-2 must-pass failure)

**D4. spec.md:L71-72** — REQ-AUTH-008: "the 시스템 **shall** 모든 API 요청에서 Authorization 헤더의 Bearer Access Token을 검증한다." The phrase "모든 API 요청" (all API requests) is contradicted by the login endpoint itself, which must be accessible without a token. The requirement should scope to "모든 보호된 API 요청" (all *protected* API requests). As written, it contradicts the login flow implicitly permitted by REQ-AUTH-002. — Severity: **major**

**D5. acceptance.md:L69-83** — AC-AUTH-005 is listed as covering REQ-AUTH-005 ("When expired or invalidated Refresh Token → HTTP 401") but the AC never actually sends an expired Refresh Token. The second When/Then block sends a *valid* Refresh Token and expects success (HTTP 200). REQ-AUTH-005's core scenario — sending an expired Refresh Token and receiving 401 — has no dedicated AC. It is only indirectly implied in AC-AUTH-006's precondition setup. — Severity: **major**

**D6. spec.md:L96** — REQ-AUTH-015: "역할 검증은 항상 데이터베이스에서 조회한 최신 역할 정보를 기준으로 수행한다" specifies the implementation mechanism (database query) rather than a behavioral outcome. This is HOW, not WHAT. The requirement should specify the behavioral invariant: "role checks shall always reflect the current role at time of request" without prescribing the database-query implementation. The plan.md (TASK-AUTH-004) is the appropriate place for the implementation approach. — Severity: **major**

**D7. spec.md:L89-90** — REQ-AUTH-013 restricts ADMIN access only to `/api/admin/users/` (the collection endpoint). However, plan.md:L86-90 defines four sub-resource paths under `/api/admin/users/` (including `{id}/`, `{id}/reset-password/`). AC-AUTH-007 (acceptance.md:L116-119) tests that ADMIN receives 403 on `PUT /api/admin/users/{id}/` and `POST /api/admin/users/{id}/reset-password/` — but these paths are not named in REQ-AUTH-013. The requirement is under-specified: it names only one path but acceptance criteria test four paths. An ADMIN might be granted access to sub-resource paths if only the collection path is enforced. — Severity: **major**

**D8. acceptance.md:L222-224** — REQ-AUTH-015 is verified by "코드 리뷰로 확인" (code review confirmation) in the quality gate, not by an automated test. This makes REQ-AUTH-015 untestable through any automated acceptance test. A requirement that can only be verified by code review should either be documented as a non-automated gate explicitly in spec.md, or reformulated with a behavioral test (e.g., verify via an integration test that uses a tampered JWT with a role claim that differs from the DB). — Severity: **major**

**D9. spec.md:L121 / plan.md:L189-192** — REQ-AUTH-022 invalidates Refresh Tokens when an account is deactivated. However, plan.md:L189-192 acknowledges that a valid Access Token (up to 15 minutes remaining) continues to work after deactivation — this is accepted as a known risk. This risk acceptance is documented only in plan.md, not in spec.md's exclusions or non-goals. The spec.md exclusion at L133 covers "로그인 실패 횟수 기반 계정 잠금" but does not explicitly exclude "immediate Access Token revocation upon deactivation." A future implementer reading spec.md alone would not know this behavior is intentionally out of scope. The risk acceptance should be documented in spec.md's 비목표 (Non-goals) section. — Severity: **minor**

**D10. acceptance.md:L44-50** — AC-AUTH-003: "올바른 username과 password를 전송한다" — the test specifies `username = inactive_admin` but the password is never stated. The AC is not self-contained: a tester cannot reproduce the scenario without knowing the password. Concrete test credentials should be stated (e.g., `password = "correct_password123"`). — Severity: **minor**

**D11. spec.md:L65** — REQ-AUTH-006 / REQ-AUTH-007 together: logout invalidates the specific Refresh Token presented. There is no requirement addressing multiple concurrent sessions (one user logged in on multiple devices simultaneously). After logout from device A, device B's Refresh Token remains valid. Whether this is intentional or an oversight is not addressed. Given that REQ-AUTH-022 goes to the trouble of invalidating all tokens on deactivation, the per-device logout behavior for multi-session users should be explicitly addressed (as a non-goal if not supported, or as a requirement if it is). — Severity: **minor**

---

## Chain-of-Verification Pass

Second-look findings: Three new defects discovered in second pass (D9, D10, D11) not identified in first pass.

Re-read sections verified:
- YAML frontmatter (spec.md:L1-10): confirmed both `created_at` and `labels` missing
- All 22 REQ entries: confirmed sequential numbering end-to-end, no skips
- All 12 AC entries: confirmed all use GWT, verified against each of five EARS patterns — zero EARS matches
- Exclusions section (spec.md:L125-136): 8 specific entries, each with rationale — adequate specificity
- Traceability: verified every REQ against AC coverage list individually — REQ-AUTH-005 and REQ-AUTH-017 partial coverage confirmed
- Contradictions: REQ-AUTH-008 vs. login endpoint contradiction confirmed (D4)
- plan.md risk section: D9 found — deactivation risk acceptance not reflected in spec.md exclusions

---

## Regression Check

Not applicable — this is iteration 1.

---

## Recommendation

The following fixes are required before this SPEC can pass audit:

**Fix 1 (critical — MP-3):** spec.md:L6 — rename `created` to `created_at`. Change `created: "2026-06-18"` to `created_at: "2026-06-18"`.

**Fix 2 (critical — MP-3):** spec.md frontmatter (after L9, before closing `---`) — add `labels` field. Example: `labels: ["authentication", "rbac", "security"]`. Any non-empty array or comma-separated string satisfies the requirement.

**Fix 3 (critical — MP-2):** acceptance.md — convert all 12 ACs from Given/When/Then format to EARS format. Each AC must match one of the five EARS patterns. The underlying test logic (concrete values, endpoint paths, HTTP status codes) is sound and can be preserved, but the framing must change. Example transformation for AC-AUTH-001:
  - Current: "Given X, When POST /api/auth/login/, Then HTTP 200..."
  - EARS: "When a valid username and password are submitted to POST /api/auth/login/, the system shall return HTTP 200 with access and refresh tokens, where access token lifetime equals 15 minutes and refresh token lifetime equals 24 hours."

**Fix 4 (major):** spec.md:L71-72 — change "모든 API 요청에서" to "모든 보호된 API 요청에서" to eliminate the contradiction with the unauthenticated login endpoint.

**Fix 5 (major):** spec.md — add a new REQ covering all ADMIN-restricted sub-resource paths, or expand REQ-AUTH-013 to enumerate: "If an ADMIN-role administrator requests access to any endpoint under `/api/admin/users/` (including `{id}/`, `{id}/reset-password/`)..." so that AC-AUTH-007's multi-path test has a traceable requirement.

**Fix 6 (major):** spec.md — add REQ for the direct REQ-AUTH-005 scenario: "When an expired Refresh Token is submitted to POST /api/auth/token/refresh/, the system shall return HTTP 401." Ensure a corresponding AC isolates this scenario rather than bundling it ambiguously into AC-AUTH-005.

**Fix 7 (major):** spec.md:L96 — rephrase REQ-AUTH-015 to express the behavioral invariant without prescribing the mechanism. Suggested: "While processing any authenticated request, the system shall enforce the role assigned to the administrator at the time of the request, not the role encoded in the Access Token at issuance."

**Fix 8 (minor):** spec.md:L34-42 (비목표 section) — add an explicit non-goal entry: "즉각적인 Access Token 무효화 (Immediate Access Token Revocation) — 계정 비활성화 시 발급된 Access Token은 만료(최대 15분)될 때까지 유효하게 작동한다. 즉각적 무효화는 v1 범위 외이다."

**Fix 9 (minor):** acceptance.md:L44-50 (AC-AUTH-003) — specify a concrete password value for the `inactive_admin` test account so the scenario is fully self-contained without external lookup.
