---
id: SPEC-ETOILE-INVEN-ADD-001
version: 1.0.0
status: Completed
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

현재 scm_v2에는 Etoile 재고(`EtoileBookInven`) 레코드를 일괄 등록하는 수단이 없다. Etoile은 본관(Gimssine, 즉 `Inven` 테이블)과는 별도의 재고 시스템이며, Etoile에 등록할 때는 반드시 본관에 해당 SKU가 존재해야 한다는 핵심 비즈니스 불변 조건이 있다. 운영자가 Etoile 재고를 추가하려면 다음 두 가지 상황을 수동으로 판단하고 처리해야 한다.

1. SKU가 본관에 없는 경우 → 본관 Inven 레코드를 먼저 생성한 뒤 Etoile 레코드 생성
2. SKU가 본관에 이미 있는 경우 → Etoile 레코드만 생성

이 과정을 수작업으로 반복하는 것은 오류 발생 가능성이 높고 운영 비용이 크다.

## 솔루션 개요

운영자가 ISBN(SKU)을 한 줄에 하나씩 입력하면, 백엔드에서 다음 4단계 로직으로 일괄 처리한다.

1. `EtoileBookInven` 중복 검사 → 이미 존재하면 `etoile_existing_skus`로 분류 (skip)
2. `Inven` 존재 여부 확인
   - 본관에 없는 경우: `Inven` 레코드 신규 생성 후 `EtoileBookInven(status_of_shopify=-1)` 생성
   - 본관에 이미 있는 경우: `EtoileBookInven(status_of_shopify=0)` 생성
3. 입력 SKU 중복 제거 (순서 유지)
4. 모든 DB 쓰기는 단일 원자적 트랜잭션으로 처리

결과를 4가지 범주로 구분하여 반환한다.

---

## 요구사항 (EARS 형식)

### 백엔드 API

**REQ-EIA-001** (Ubiquitous)
The 시스템 shall `POST /api/book/etoile-inven-skus/` 엔드포인트를 제공한다.

**REQ-EIA-002** (Event-Driven)
When `POST /api/book/etoile-inven-skus/` 요청이 수신될 때, the 시스템 shall 요청 헤더의 JWT Bearer 토큰을 검증한다 (`JWTAuthentication` + `IsAuthenticated`).

**REQ-EIA-003** (Unwanted)
If 유효한 JWT 토큰이 없으면, then the 시스템 shall HTTP 401 Unauthorized 응답을 반환한다.

**REQ-EIA-004** (Event-Driven)
When 요청 바디의 `skus` 필드가 누락되었거나 빈 배열인 경우, the 시스템 shall HTTP 400 Bad Request 응답을 반환한다.

**REQ-EIA-005** (Event-Driven)
When 유효한 `skus` 배열이 수신될 때, the 시스템 shall 각 항목에 대해 앞뒤 공백을 제거(strip)하고 빈 문자열을 제외한 뒤, 입력 순서를 유지하며 중복을 제거한다.

**REQ-EIA-006** (Event-Driven)
When 정제된 SKU 목록이 확정될 때, the 시스템 shall 이미 `EtoileBookInven`에 존재하는 SKU를 조회하여 `etoile_existing_skus`로 분류하고, 이후 처리에서 제외한다.

**REQ-EIA-007** (Event-Driven)
When `EtoileBookInven` 중복 검사 이후 처리 대상 SKU가 결정될 때, the 시스템 shall `Inven.inven_SKU__in` 조회를 통해 본관에 존재하는 SKU와 존재하지 않는 SKU를 구분한다.

**REQ-EIA-008** (Event-Driven)
When 본관(`Inven`)에 존재하지 않는 SKU가 1개 이상 확인될 때, the 시스템 shall 단일 트랜잭션 내에서 `Inven.objects.bulk_create()`를 사용하여 해당 SKU의 Inven 레코드를 생성한다. 각 레코드의 고정 값은 `vendor="북센"`, `store="책방"`, `is_prepared=0`, `status_of_shopify=0`, `is_use=1`이다.

**REQ-EIA-009** (Event-Driven)
When REQ-EIA-008에 의해 신규 Inven 레코드가 생성된 직후, the 시스템 shall 생성된 Inven 레코드에 대해 `EtoileBookInven(status_of_shopify=-1)` 레코드를 `bulk_create()`로 생성한다. 이 SKU들은 `etoile_created_new_book_skus`로 분류된다.

**REQ-EIA-010** (Event-Driven)
When 본관(`Inven`)에 이미 존재하고 `EtoileBookInven`에는 없는 SKU가 확인될 때, the 시스템 shall 해당 Inven 레코드에 대해 `EtoileBookInven(status_of_shopify=0)` 레코드를 `bulk_create()`로 생성한다. 이 SKU들은 `etoile_created_existing_book_skus`로 분류된다.

**REQ-EIA-011** (State-Driven)
While REQ-EIA-008 ~ REQ-EIA-010의 모든 DB 쓰기 작업은, the 시스템 shall 단일 원자적 트랜잭션(`transaction.atomic()`) 내에서 실행되어야 한다.

**REQ-EIA-012** (Unwanted)
If 트랜잭션 내 데이터베이스 오류가 발생하면, then the 시스템 shall 모든 변경 사항을 롤백하고 HTTP 500 Internal Server Error 응답을 반환한다.

**REQ-EIA-013** (Event-Driven)
When 처리가 완료될 때, the 시스템 shall 다음 구조의 HTTP 200 응답을 반환한다:
```json
{
  "book_created_skus": ["SKU_A"],
  "etoile_created_new_book_skus": ["SKU_A"],
  "etoile_created_existing_book_skus": ["SKU_B"],
  "etoile_existing_skus": ["SKU_C"],
  "book_created_count": 1,
  "etoile_created_new_book_count": 1,
  "etoile_created_existing_book_count": 1,
  "etoile_existing_count": 1
}
```

**REQ-EIA-014** (State-Driven)
While 모든 입력 SKU가 이미 `EtoileBookInven`에 존재하는 경우, the 시스템 shall `book_created_skus`, `etoile_created_new_book_skus`, `etoile_created_existing_book_skus`가 모두 빈 배열이고 `etoile_existing_skus`에 모든 SKU가 포함된 HTTP 200 응답을 반환한다.

---

### 핵심 비즈니스 불변 조건 (Core Invariant)

**REQ-EIA-015** (Ubiquitous)
The 시스템 shall Etoile(`EtoileBookInven`) 등록 시 항상 해당 SKU의 본관(`Inven`) 레코드가 존재함을 보장한다. 본관에 없는 SKU는 Etoile 등록 전에 반드시 본관에 먼저 생성되어야 한다.

---

## 응답 필드 정의

| 필드 | 설명 |
|------|------|
| `book_created_skus` | 본관(`Inven`)에 신규 생성된 SKU 목록 |
| `etoile_created_new_book_skus` | 본관 신규 생성과 함께 Etoile에 등록된 SKU 목록 (`status_of_shopify=-1`) |
| `etoile_created_existing_book_skus` | 본관에 이미 존재하여 Etoile에 등록된 SKU 목록 (`status_of_shopify=0`) |
| `etoile_existing_skus` | 이미 `EtoileBookInven`에 존재하여 건너뛴 SKU 목록 |
| `book_created_count` | `book_created_skus` 개수 |
| `etoile_created_new_book_count` | `etoile_created_new_book_skus` 개수 |
| `etoile_created_existing_book_count` | `etoile_created_existing_book_skus` 개수 |
| `etoile_existing_count` | `etoile_existing_skus` 개수 |

---

## 데이터 모델 참조

> 스키마 마이그레이션 불필요 — 모든 모델이 이미 존재함.

### Inven (본관 재고)
- 테이블: `book_inven`
- 주요 필드: `inven_SKU` (PK), `vendor`, `store`, `is_prepared`, `status_of_shopify`, `is_use`
- 신규 생성 고정값: `vendor="북센"`, `store="책방"`, `is_prepared=0`, `status_of_shopify=0`, `is_use=1`

### EtoileBookInven (Etoile 재고)
- 테이블: `etoile_book_inven`
- 주요 필드: `inven` (OneToOne FK → Inven), `status_of_shopify`
- Etoile `status_of_shopify` 값 의미:
  - `-1`: Gimssine 등록 대기 (신규 본관 생성과 함께 Etoile 등록된 경우)
  - `0`: 리스팅 준비

---

## API 명세

### POST /api/book/etoile-inven-skus/

**인증**: JWT Bearer 토큰 필수

**요청 바디**:
```json
{
  "skus": ["9791234567890", "9790000000001", "9790000000002"]
}
```

**성공 응답** (HTTP 200):
```json
{
  "book_created_skus": ["9790000000001"],
  "etoile_created_new_book_skus": ["9790000000001"],
  "etoile_created_existing_book_skus": ["9791234567890"],
  "etoile_existing_skus": ["9790000000002"],
  "book_created_count": 1,
  "etoile_created_new_book_count": 1,
  "etoile_created_existing_book_count": 1,
  "etoile_existing_count": 1
}
```

**오류 응답**:
- `400 Bad Request`: `skus` 필드 누락 또는 빈 배열
- `401 Unauthorized`: JWT 토큰 없거나 유효하지 않음
- `500 Internal Server Error`: DB 오류 발생 (트랜잭션 롤백)

---

## 처리 로직 흐름

```
입력 SKUs
  ↓ strip + 빈 문자열 제거 + 중복 제거 (순서 유지)
  ↓ EtoileBookInven 존재 여부 조회
  → 이미 존재: etoile_existing_skus (종료)
  → 미존재: 처리 대상
       ↓ Inven 존재 여부 조회
       → 본관 없음: Inven bulk_create → EtoileBookInven(status=-1) bulk_create
                    → book_created_skus, etoile_created_new_book_skus
       → 본관 있음: EtoileBookInven(status=0) bulk_create
                    → etoile_created_existing_book_skus
  ↓ 전체 DB 쓰기 단일 atomic 트랜잭션
  ↓ HTTP 200 응답 반환
```

---

## 제외 범위 (What NOT to Build)

- **프론트엔드 UI 없음**: 이 SPEC은 백엔드 API만 정의한다. 프론트엔드 페이지 및 UI 컴포넌트는 별도 SPEC에서 다룬다.
- **Info 레코드 생성 없음**: `book_info` 테이블 레코드 생성은 포함하지 않는다. Inven 레코드 생성에만 해당한다.
- **Shopify API 직접 연동 없음**: `status_of_shopify` 값은 내부 상태 플래그이며, 실제 Shopify API 호출은 별도 배치/동기화 작업이 담당한다.
- **ISBN 형식 유효성 검사 없음**: ISBN-10/ISBN-13 형식 검증을 수행하지 않는다. SKU는 임의의 문자열로 허용한다.
- **기존 Etoile 레코드 업데이트 없음**: 이미 `EtoileBookInven`에 존재하는 SKU는 상태값 변경 없이 건너뛴다.
- **기존 본관 레코드 업데이트 없음**: 이미 `Inven`에 존재하는 SKU의 필드를 수정하지 않는다.
- **스키마 마이그레이션 없음**: `Inven`, `EtoileBookInven` 모델 변경 없이 기존 모델을 그대로 사용한다.

---

## 테스트 전략

### 단위 테스트 (`backend/book/tests/test_etoile_inven_add.py`)

| 테스트 케이스 | 검증 항목 |
|--------------|-----------|
| 인증 없이 요청 | HTTP 401 반환 |
| `skus` 필드 누락 | HTTP 400 반환 |
| `skus` 빈 배열 | HTTP 400 반환 |
| 모든 SKU가 Etoile에 이미 존재 | `etoile_existing_skus`에 모두 포함, 신규 레코드 없음 |
| 모든 SKU가 본관에도 Etoile에도 없음 | Inven + EtoileBookInven 신규 생성, `status_of_shopify=-1` |
| 모든 SKU가 본관에 있고 Etoile에 없음 | EtoileBookInven만 생성, `status_of_shopify=0` |
| 혼합 케이스 (3가지 상황 동시) | 각 범주 분류 정확성 |
| 중복 SKU 입력 | 중복 제거 후 1회만 처리 |
| 공백 포함 SKU 입력 | strip 후 정상 처리 |
| DB 오류 발생 시 | 트랜잭션 롤백, HTTP 500 반환 |

### 수용 테스트 (Acceptance)

상세 수용 기준은 `acceptance.md` 참조.

---

## 변경 파일 목록 (예상)

### 백엔드
- `backend/book/views.py` — `EtoileInvenSkuBulkAddView` (APIView) 추가
- `backend/book/urls.py` — `POST /api/book/etoile-inven-skus/` 엔드포인트 등록
- `backend/book/serializers.py` — `EtoileInvenSkuBulkAddSerializer` 추가
- `backend/book/tests/test_etoile_inven_add.py` — 신규 테스트 파일 생성

---

## 관련 SPEC

- **SPEC-INVEN-ADD-001**: 본관 ISBN 일괄 추가 (완료) — Etoile 없이 Inven만 생성
- **SPEC-FAST-LISTING-ADD-001**: 빠른 리스팅 일괄 추가 (완료) — Inven status 변경
- **SPEC-ETOILE-DASHBOARD-001**: Etoile 재고 현황 대시보드 (완료) — `EtoileBookInven` 조회

---

## 구현 완료 노트 (2026-06-20)

구현이 완료되었습니다. 다음 파일에 REQ-EIA-001 ~ REQ-EIA-015 모두 반영되었습니다.

- `backend/book/views.py` — `EtoileInvenSkuBulkAddView`, `_process_etoile_inven_skus()`
- `backend/book/serializers.py` — `EtoileInvenSkuBulkAddSerializer`
- `backend/book/urls.py` — `POST /api/book/etoile-inven-skus/`
- `backend/book/tests/test_etoile_inven_add.py` — 10/10 테스트 통과
