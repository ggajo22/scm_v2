---
id: SPEC-ETOILE-INVEN-ADD-001
type: plan
status: Planned
created: 2026-06-20
updated: 2026-06-20
---

## 구현 계획

### 기술 접근 방식

레거시 `c:/app/scm/main/book/views.py`의 `_process_etoile_inven_skus()` 함수 로직을 DRF `APIView` 패턴으로 이식한다. 기존 `SPEC-INVEN-ADD-001`(`InvenSkuBulkAddView`)과 `SPEC-FAST-LISTING-ADD-001`(`FastListingSkuView`)의 구현 패턴을 일관되게 따른다.

**핵심 기술 결정**:
- 뷰: `APIView` (기존 패턴 일관성)
- 인증: `JWTAuthentication` + `IsAuthenticated` (프로젝트 표준)
- 트랜잭션: `django.db.transaction.atomic()` 데코레이터
- 일괄 처리: `bulk_create(ignore_conflicts=True)` (레거시 검증된 방식)

---

### 마일스톤 (우선순위 순)

#### Priority High — 백엔드 API 구현

**M1. 시리얼라이저 추가**
- `backend/book/serializers.py`에 `EtoileInvenSkuBulkAddSerializer` 추가
- `skus` 필드: `ListField(child=CharField())`, 필수값, 빈 배열 유효성 검사

**M2. 뷰 구현**
- `backend/book/views.py`에 `EtoileInvenSkuBulkAddView` 추가
- 처리 로직:
  1. SKU 정제 (strip, 빈 문자열 제거, 중복 제거, 순서 유지)
  2. `EtoileBookInven` 중복 조회
  3. `Inven` 존재 여부 조회
  4. `transaction.atomic()` 내 일괄 처리
  5. 결과 응답 구성

**M3. URL 등록**
- `backend/book/urls.py`에 `POST /api/book/etoile-inven-skus/` 엔드포인트 등록

#### Priority High — 테스트 작성

**M4. 단위 테스트**
- `backend/book/tests/test_etoile_inven_add.py` 신규 생성
- 10개 테스트 케이스 (spec.md 테스트 전략 참조)
- 목표 커버리지: 신규 코드 90% 이상

---

### 기술 위험 요소

| 위험 | 가능성 | 대응 |
|------|--------|------|
| `bulk_create` 직후 재조회 필요 | 중간 | 레거시 코드와 동일하게 `filter(inven_SKU__in=missing_book_skus)` 재조회로 처리 |
| `ignore_conflicts=True` 시 실제 삽입 건수 확인 불가 | 낮음 | 재조회로 실제 Inven PK 확보 후 EtoileBookInven 생성 (레거시 검증된 패턴) |
| Etoile 중복 조회 시 Inven FK 없는 케이스 | 없음 | `EtoileBookInven`은 항상 Inven FK를 통해 조회하므로 불일치 없음 |

---

### 참조 구현

레거시 함수 `_process_etoile_inven_skus()`는 `c:/app/scm/main/book/views.py`에 있으며 spec.md에 전문 수록됨. 본 구현은 해당 로직을 DRF 패턴으로 이식한 것이므로 비즈니스 로직 변경 없음.
