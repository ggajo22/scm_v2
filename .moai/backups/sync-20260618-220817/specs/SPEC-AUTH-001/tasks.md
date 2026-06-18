## Task Decomposition
SPEC: SPEC-AUTH-001

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | Django 프로젝트 환경 설정 (pyproject.toml, pytest.ini, settings) | REQ-AUTH-001 | - | backend/pyproject.toml, backend/pytest.ini, backend/config/settings/base.py, backend/config/settings/local.py, backend/.env.example | pending |
| T-002 | AdminUser 모델 구현 (AbstractUser 확장, role 필드) | REQ-AUTH-010 | T-001 | backend/accounts/models.py, backend/accounts/tests/test_models.py, backend/accounts/migrations/0001_initial.py | pending |
| T-003 | 로그인/로그아웃/토큰갱신 뷰 구현 | REQ-AUTH-001~009 | T-002 | backend/accounts/views.py, backend/accounts/serializers.py, backend/accounts/urls.py, backend/config/urls.py, backend/accounts/tests/test_login.py, backend/accounts/tests/test_logout.py, backend/accounts/tests/test_token_refresh.py | pending |
| T-004 | RBAC 권한 클래스 구현 (IsSuperAdmin, IsAdminOrSuperAdmin) | REQ-AUTH-010~015 | T-002 | backend/accounts/permissions.py, backend/accounts/tests/test_permissions.py | pending |
| T-005 | 관리자 계정 관리 API 구현 (AdminUserViewSet) | REQ-AUTH-016~021 | T-003, T-004 | backend/accounts/views.py, backend/accounts/serializers.py, backend/accounts/tests/test_admin_user_management.py | pending |
| T-006 | 계정 비활성화 → Refresh Token 무효화 시그널 | REQ-AUTH-022 | T-002, T-003 | backend/accounts/signals.py, backend/accounts/apps.py | pending |
| T-007 | URL 라우팅 통합 | REQ-AUTH-008 | T-003, T-005 | backend/config/urls.py, backend/accounts/urls.py | pending |
| T-008 | 테스트 팩토리 및 커버리지 90% 달성 | All | T-001~T-007 | backend/accounts/tests/factories.py, all test_*.py | pending |
