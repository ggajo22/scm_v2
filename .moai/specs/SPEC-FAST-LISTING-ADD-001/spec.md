---
id: SPEC-FAST-LISTING-ADD-001
version: 1.0.0
status: Planned
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-06-20 | 1.0.0 | 최초 작성 |

---

## 문제 정의

현재 scm_v2에는 재고(Inven) 레코드를 Shopify 빠른 리스팅 대상(`status_of_shopify=1`)으로 일괄 지정하는 수단이 없다. 운영자는 Shopify에 신속히 등록해야 할 도서 SKU를 대량으로 처리할 때 수작업으로 하나씩 상태를 변경해야 한다.

기존 시스템(레거시 scm)의 `fast_add_inven_skus()` 함수는 상태 80/81/82(이미 Shopify에 활성화된 도서)를 구별 없이 덮어쓰는 문제가 있었다. 본 SPEC은 해당 로직을 개선하여 활성 도서를 보호하는 안전 장치를 포함한다.

## 솔루션 개요

운영자가 ISBN을 한 줄에 하나씩 텍스트 영역에 입력하면, 백엔드에서 다음 로직으로 처리한다:

1. 신규 SKU: `status_of_shopify=1` 로 Inven 레코드 신규 생성
2. 기존 SKU (status NOT IN 80, 81, 82): `status_of_shopify=1` 로 업데이트
3. 기존 SKU (status IN 80, 81, 82): 변경 없이 건너뜀 (활성 도서 보호)

결과를 `created` / `updated` / `skipped` 3가지 범주로 구분하여 반환한다.

---

## 요구사항 (EARS 형식)

### 백엔드 API

**REQ-FLA-001** (Ubiquitous)
The system shall expose a `POST /api/book/fast-listing-skus/` endpoint.

**REQ-FLA-002** (Event-Driven)
When a `POST /api/book/fast-listing-skus/` request is received, the system shall require JWT Bearer token authentication via `JWTAuthentication` + `IsAuthenticated`.

**REQ-FLA-003** (Unwanted)
If no valid JWT token is present in the request, then the system shall return HTTP 401 Unauthorized.

**REQ-FLA-004** (Event-Driven)
When the request body `skus` field is missing, null, or an empty array, the system shall return HTTP 400 Bad Request.

**REQ-FLA-005** (Event-Driven)
When a valid `skus` array is received, the system shall strip leading/trailing whitespace from each item, exclude empty strings, and deduplicate while preserving original order.

**REQ-FLA-006** (Event-Driven)
When new SKUs (not present in the `Inven` table) are identified after deduplication, the system shall bulk-create `Inven` records within a single database transaction with fixed field values: `vendor="북센"`, `store="책방"`, `is_prepared=0`, `status_of_shopify=1`, `is_use=1`.

**REQ-FLA-007** (Event-Driven)
When existing SKUs with `status_of_shopify NOT IN (80, 81, 82)` are identified, the system shall update those records to `status_of_shopify=1` within the same transaction.

**REQ-FLA-008** (State-Driven)
While an existing `Inven` record has `status_of_shopify IN (80, 81, 82)`, the system shall skip that record without modification and include it in the `skipped` response list.

**REQ-FLA-009** (Event-Driven)
When processing completes successfully, the system shall return HTTP 200 with the following structure:
```json
{
  "created": ["SKU1"],
  "updated": ["SKU2"],
  "skipped": ["SKU3"],
  "created_count": 1,
  "updated_count": 1,
  "skipped_count": 1
}
```

**REQ-FLA-010** (Unwanted)
If a database error occurs during the transaction, then the system shall roll back all changes and return HTTP 500 Internal Server Error.

### 프론트엔드 UI

**REQ-FLA-011** (Ubiquitous)
The system shall register a `/books/fast-listing` route accessible to authenticated users.

**REQ-FLA-012** (Ubiquitous)
The system shall display a "빠른 리스팅" sub-item in the "도서관리" sidebar group, positioned alongside "대시보드" and "ISBN 추가".

**REQ-FLA-013** (Ubiquitous)
The system shall render a `<textarea>` on the `/books/fast-listing` page with placeholder text "ISBN을 한 줄에 하나씩 입력하세요".

**REQ-FLA-014** (State-Driven)
While an API call is in progress, the system shall disable the submit button to prevent duplicate submissions.

**REQ-FLA-015** (Event-Driven)
When the user submits the form, the system shall split the textarea content by newline, strip whitespace, filter empty lines, and send the resulting array as `skus` to `POST /api/book/fast-listing-skus/`.

**REQ-FLA-016** (Event-Driven)
When the API response is received successfully, the system shall display three result sections:
- 생성됨 (green): SKUs in `created` array
- 업데이트됨 (blue): SKUs in `updated` array
- 건너뜀 (muted/gray): SKUs in `skipped` array

**REQ-FLA-017** (Unwanted)
If the API call returns an error response, then the system shall display an error message to the user.

**REQ-FLA-018** (Ubiquitous)
The system shall provide a link navigating back to `/books` on the fast-listing page.

---

## 제약 사항

- `status_of_shopify` 값 80, 81, 82는 Shopify 활성 상태를 나타내며, 이 값을 가진 기존 레코드는 절대 덮어쓰지 않는다.
- 신규 생성 레코드의 `vendor`와 `store` 고정값은 "북센", "책방"이며 사용자 입력으로 변경 불가하다.
- 인증은 반드시 JWT Bearer 토큰 방식이어야 한다 (기존 DRF 설정 준수).
- 프론트엔드 UI 패턴은 기존 `AddIsbnPage.tsx` 와 동일한 구조를 따른다.

---

## 제외 사항 (What NOT to Build)

- **EtoileBookInven 레코드 생성 없음**: 에투알 연동 테이블은 본 기능의 범위 밖이다.
- **Info 레코드 생성 없음**: 도서 메타정보(Info) 테이블 삽입은 포함하지 않는다.
- **Shopify API 직접 연동 없음**: `status_of_shopify=1`은 내부 상태 플래그일 뿐이며, 실제 Shopify API 호출은 별도 배치/동기화 작업이 담당한다.
- **ISBN 형식 유효성 검사 없음**: 입력값의 ISBN-10/13 형식 검증은 수행하지 않는다.
- **기존 SPEC-INVEN-ADD-001 변경 없음**: `POST /api/book/inven-skus/` 엔드포인트(status=0 삽입)는 그대로 유지된다.
- **개별 SKU 단건 조회/수정 UI 없음**: 본 기능은 일괄 처리 전용이다.
