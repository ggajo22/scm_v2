---
id: SPEC-WAREHOUSE-001
version: 1.0.0
status: implemented
created: 2026-06-21
updated: 2026-06-21
author: ggajo
priority: High
issue_number: ~
---

# 창고 재고 관리 (Warehouse Stock Management)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-21 | ggajo | 최초 작성 — 창고 재고 관리 시스템 회고적(retrospective) SPEC |

---

## 문제 정의

SCM v2는 Shopify 주문 수집(`SPEC-ORDER-001`) 및 발주 관리(`SPEC-PURCHASE-ORDER-001`) 기능을 갖추고 있으나, **물리적 창고에 실제로 보유 중인 재고를 추적하는 수단**이 없었다.

도서 상품은 한국(Korea), 미국 캘리포니아(CA), 미국 뉴저지(NJ) 총 3개 거점 창고에 분산 보관된다. 관리자는 현재:

- 각 창고의 ISBN별 재고 수량을 별도 엑셀로 수동 관리
- 창고 간 재고 현황을 시스템에서 통합 조회할 방법이 없음
- 단건 입력과 대량 입력(일괄 등록)을 모두 수동 처리
- 특정 ISBN의 재고가 어느 창고에 얼마나 있는지 즉시 파악 불가

이로 인해 재고 파악 지연, 과재고·품절 오류, 그리고 물류 의사결정 오류가 반복적으로 발생하였다.

---

## 솔루션 개요

`order` 앱에 **`WarehouseStock` 모델**을 추가하여 창고별 ISBN 재고를 데이터베이스로 관리한다.

1. **재고 목록 조회 (피벗 뷰)** — ISBN 1행에 한국/CA/NJ 수량 컬럼을 한눈에 표시
2. **단건 등록/수정 (Upsert)** — ISBN + 위치 + 수량으로 단건 재고를 생성 또는 갱신
3. **일괄 등록 (Bulk Upsert)** — 텍스트 영역(textarea)에 여러 행을 입력하여 대량 처리
4. **단건 삭제** — 특정 위치의 재고 레코드를 삭제
5. **ISBN 검색 필터** — 조회 목록에서 ISBN으로 빠르게 필터링

---

## 도메인 개념 정의

| 용어 | 정의 |
|------|------|
| ISBN | 국제 표준 도서 번호(International Standard Book Number). 창고 재고의 기본 식별자. |
| 위치(location) | 재고 보관 창고 거점. `korea`(한국), `ca`(미국 캘리포니아), `nj`(미국 뉴저지) 세 곳. |
| 재고(stock) | 특정 ISBN이 특정 위치 창고에 보유된 수량. |
| 피벗 뷰 | ISBN 1행에 korea/ca/nj 수량 컬럼을 나란히 표시하는 비정규화 조회 형태. |
| Upsert | 레코드가 없으면 생성(Create), 있으면 갱신(Update)하는 단일 연산. |
| 일괄 등록 | 여러 재고 항목을 한 번의 요청으로 처리하는 Bulk Upsert. |

---

## 요구사항

### 인증

**REQ-WH-001** (Ubiquitous)
The 창고 재고 관련 모든 API endpoint **shall** JWT 인증(`JWTAuthentication + IsAuthenticated`)을 요구한다.

**REQ-WH-002** (Unwanted Behavior)
**If** 요청에 유효한 JWT 토큰이 없거나 만료된 경우, **then** the API **shall** HTTP 401 Unauthorized를 반환한다.

---

### 재고 목록 조회

**REQ-WH-003** (Ubiquitous)
The 시스템 **shall** `GET /api/warehouse/stock/` 엔드포인트를 제공하며, ISBN별로 피벗된 재고 목록을 반환한다.

**REQ-WH-004** (Ubiquitous)
The 재고 목록 응답 **shall** ISBN 1행당 `isbn`, `korea_qty`, `korea_id`, `ca_qty`, `ca_id`, `nj_qty`, `nj_id` 필드를 포함하며, 각 `*_id`는 해당 위치 `WarehouseStock` 레코드의 기본 키(PK)이다.

**REQ-WH-005** (Ubiquitous)
The 재고 목록 조회 **shall** `isbn` 쿼리 파라미터를 지원하며, 값이 제공된 경우 해당 문자열을 포함하는 ISBN만 필터링하여 반환한다.

**REQ-WH-006** (Unwanted Behavior)
**If** 등록된 재고가 없는 경우, **then** the API **shall** 빈 배열(`[]`)을 반환한다.

---

### 단건 Upsert

**REQ-WH-007** (Event-Driven)
**When** 관리자가 `POST /api/warehouse/stock/upsert/`를 호출하면, the 시스템 **shall** 요청된 `isbn`과 `location`의 조합으로 `WarehouseStock` 레코드를 생성하거나 `quantity`를 갱신한다.

**REQ-WH-008** (Ubiquitous)
The `upsert` 요청 **shall** `isbn`, `location`(`korea`, `ca`, `nj` 중 하나), `quantity`(0 이상의 정수) 필드를 필수로 포함한다.

**REQ-WH-009** (Unwanted Behavior)
**If** `location`이 `korea`, `ca`, `nj` 이외의 값인 경우, **then** the API **shall** HTTP 400 Bad Request를 반환한다.

---

### 일괄 등록 (Bulk Upsert)

**REQ-WH-010** (Event-Driven)
**When** 관리자가 `POST /api/warehouse/stock/bulk/`를 호출하면, the 시스템 **shall** 요청 배열의 각 항목(`isbn`, `location`, `quantity`)을 순서대로 Upsert 처리한다.

**REQ-WH-011** (Ubiquitous)
The `bulk` 요청 **shall** 하나 이상의 `{isbn, location, quantity}` 객체로 구성된 JSON 배열을 요청 바디로 받는다.

**REQ-WH-012** (Unwanted Behavior)
**If** `bulk` 요청 배열이 비어 있는 경우, **then** the API **shall** HTTP 400 Bad Request를 반환한다.

---

### 단건 삭제

**REQ-WH-013** (Event-Driven)
**When** 관리자가 `DELETE /api/warehouse/stock/<pk>/`를 호출하면, the 시스템 **shall** 해당 PK의 `WarehouseStock` 레코드를 삭제한다.

**REQ-WH-014** (Unwanted Behavior)
**If** 요청된 PK의 `WarehouseStock` 레코드가 존재하지 않는 경우, **then** the API **shall** HTTP 404 Not Found를 반환한다.

---

### 프론트엔드 — 창고 재고 페이지

**REQ-WH-015** (Ubiquitous)
The 프론트엔드 **shall** `/warehouse` 경로에 창고 재고 관리 페이지를 제공하며, 사이드바 네비게이션에 "창고 재고" 항목을 Warehouse 아이콘과 함께 추가한다.

**REQ-WH-016** (Ubiquitous)
The 창고 재고 페이지 **shall** ISBN, 한국, CA, NJ 컬럼으로 구성된 피벗 테이블을 표시하며, 각 수량 셀에는 해당 위치 레코드를 삭제할 수 있는 휴지통 아이콘을 제공한다.

**REQ-WH-017** (Ubiquitous)
The 창고 재고 페이지 **shall** ISBN 검색 입력 필드를 제공하며, 입력 값이 변경될 때 테이블을 즉시 필터링한다.

**REQ-WH-018** (Event-Driven)
**When** 관리자가 "재고 추가" 버튼을 클릭하면, the 시스템 **shall** ISBN 입력, 위치 선택 드롭다운(한국/CA/NJ), 수량 입력으로 구성된 모달을 표시한다.

**REQ-WH-019** (Event-Driven)
**When** 관리자가 "일괄 등록" 버튼을 클릭하면, the 시스템 **shall** textarea 모달을 표시하며, 각 행에 `ISBN 위치 수량` 형식으로 입력할 수 있도록 안내한다.

**REQ-WH-020** (Event-Driven)
**When** 셀의 휴지통 아이콘을 클릭하면, the 시스템 **shall** `DELETE /api/warehouse/stock/<pk>/`를 호출하고, 성공 시 테이블을 자동으로 새로고침한다.

**REQ-WH-021** (State-Driven)
**While** 데이터를 로딩 중인 경우, the 테이블 **shall** 로딩 스켈레톤 또는 스피너를 표시한다.

**REQ-WH-022** (Unwanted Behavior)
**If** API 호출 중 오류가 발생하면, **then** the 시스템 **shall** 오류 내용을 토스트 메시지로 사용자에게 표시한다.

---

### 도서명 표시

**REQ-WH-023** (Ubiquitous)
The 재고 목록 응답 **shall** 각 ISBN에 대해 `book_info` 테이블(`Inven.inven_SKU` → `Info.name`)에서 조회한 도서명 `title` 필드를 포함하며, 매핑되지 않는 ISBN의 경우 빈 문자열을 반환한다.

**REQ-WH-024** (Ubiquitous)
The 창고 재고 페이지 **shall** 피벗 테이블의 ISBN 컬럼 옆에 도서명 컬럼을 표시하며, `book_info`에 없는 ISBN은 `—`으로 표시한다.

---

### 재고 합계 요약

**REQ-WH-025** (Ubiquitous)
The 창고 재고 페이지 **shall** 테이블 상단에 한국·CA·NJ 위치별 재고 합계와 전체 총 합계를 카드 형태로 표시한다.

---

### 일괄 등록 파싱 개선

**REQ-WH-026** (Ubiquitous)
The 일괄 등록 텍스트 파서 **shall** 위치 값으로 `korea`·`ca`·`nj` 외에 `한국`·`kor`·`kr` 별칭을 대소문자 구분 없이 허용한다.

**REQ-WH-027** (Unwanted Behavior)
**If** 일괄 등록 텍스트 입력에서 유효한 항목이 하나도 파싱되지 않은 경우, **then** the 시스템 **shall** "유효한 항목이 없습니다" 에러 토스트를 표시하고 API 호출을 생략한다.

---

## 인수 조건

### AC-WH-001 — 피벗 재고 목록 조회

- Given: `WarehouseStock` 테이블에 ISBN `9788901234567`에 대해 korea 수량 10, ca 수량 5가 등록되어 있음
- When: `GET /api/warehouse/stock/` 요청
- Then: 응답 배열에 `{ isbn: "9788901234567", korea_qty: 10, ca_qty: 5, nj_qty: null }` 형태의 항목이 포함됨

### AC-WH-002 — ISBN 필터

- Given: 여러 ISBN의 재고가 등록된 상태
- When: `GET /api/warehouse/stock/?isbn=9788901` 요청
- Then: `9788901`을 포함하는 ISBN의 항목만 반환됨

### AC-WH-003 — 단건 Upsert (신규 생성)

- Given: ISBN `9780000000001`, 위치 `nj`에 해당하는 레코드가 없음
- When: `POST /api/warehouse/stock/upsert/` `{ isbn: "9780000000001", location: "nj", quantity: 3 }` 요청
- Then: HTTP 200 또는 201 반환, DB에 해당 레코드가 생성됨

### AC-WH-004 — 단건 Upsert (수량 갱신)

- Given: ISBN `9780000000001`, 위치 `nj`, 수량 3인 레코드가 존재
- When: `POST /api/warehouse/stock/upsert/` `{ isbn: "9780000000001", location: "nj", quantity: 7 }` 요청
- Then: 기존 레코드의 수량이 7로 갱신됨 (신규 레코드 생성 없음)

### AC-WH-005 — 일괄 등록

- Given: 빈 `WarehouseStock` 테이블
- When: `POST /api/warehouse/stock/bulk/` `[{ isbn: "A", location: "korea", quantity: 1 }, { isbn: "B", location: "ca", quantity: 2 }]` 요청
- Then: 2개의 레코드가 생성되고, HTTP 200 반환

### AC-WH-006 — 단건 삭제

- Given: PK=5인 `WarehouseStock` 레코드가 존재
- When: `DELETE /api/warehouse/stock/5/` 요청
- Then: HTTP 204 No Content 반환, 해당 레코드가 DB에서 삭제됨

### AC-WH-007 — 유효하지 않은 위치값 거부

- Given: 유효한 JWT 토큰
- When: `POST /api/warehouse/stock/upsert/` `{ isbn: "X", location: "tokyo", quantity: 1 }` 요청
- Then: HTTP 400 Bad Request 반환

### AC-WH-008 — 인증 없는 접근 거부

- Given: Authorization 헤더 없음
- When: `GET /api/warehouse/stock/` 요청
- Then: HTTP 401 Unauthorized 반환

---

## 데이터 모델

### WarehouseStock

```python
class WarehouseStock(models.Model):
    LOCATION_CHOICES = [
        ("korea", "한국"),
        ("ca", "CA"),
        ("nj", "NJ"),
    ]
    isbn = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)
    location = models.CharField(max_length=10, choices=LOCATION_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_warehousestock"
        unique_together = [("isbn", "location")]
        indexes = [models.Index(fields=["isbn"])]
```

**설계 결정 사항:**

- `unique_together = [("isbn", "location")]` — 동일 ISBN + 위치 조합의 중복 레코드를 DB 수준에서 방지하고 Upsert 로직을 단순화한다.
- `isbn` 컬럼 인덱스 — ISBN 검색 필터 성능 확보를 위해 추가.
- `updated_at` auto-update — 마지막 재고 갱신 시각 추적.
- 별도 테이블(`orders_warehousestock`) 사용 — 주문/발주 모델과 직접적인 FK 관계 없이 독립적으로 관리.

---

## API 명세

### GET /api/warehouse/stock/

**요청**
```
GET /api/warehouse/stock/
GET /api/warehouse/stock/?isbn=9788901
Authorization: Bearer <access_token>
```

**쿼리 파라미터**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `isbn` | string | 선택 | 포함 검색. 해당 문자열을 포함하는 ISBN만 반환. |

**성공 응답 (HTTP 200)**
```json
[
  {
    "isbn": "9788901234567",
    "korea_qty": 10,
    "korea_id": 1,
    "ca_qty": 5,
    "ca_id": 2,
    "nj_qty": null,
    "nj_id": null
  },
  {
    "isbn": "9788901234568",
    "korea_qty": null,
    "korea_id": null,
    "ca_qty": null,
    "ca_id": null,
    "nj_qty": 3,
    "nj_id": 7
  }
]
```

> 위치에 재고가 없는 경우 해당 `*_qty` 및 `*_id`는 `null`로 반환한다.

---

### POST /api/warehouse/stock/upsert/

**요청**
```
POST /api/warehouse/stock/upsert/
Authorization: Bearer <access_token>
Content-Type: application/json
```
```json
{
  "isbn": "9788901234567",
  "location": "korea",
  "quantity": 10
}
```

**성공 응답 (HTTP 200)**
```json
{
  "id": 1,
  "isbn": "9788901234567",
  "location": "korea",
  "quantity": 10,
  "updated_at": "2026-06-21T10:00:00+09:00"
}
```

**오류 응답 (HTTP 400 — 잘못된 위치값)**
```json
{
  "location": ["\"tokyo\" is not a valid choice."]
}
```

---

### POST /api/warehouse/stock/bulk/

**요청**
```
POST /api/warehouse/stock/bulk/
Authorization: Bearer <access_token>
Content-Type: application/json
```
```json
[
  { "isbn": "9788901234567", "location": "korea", "quantity": 10 },
  { "isbn": "9788901234567", "location": "ca", "quantity": 5 },
  { "isbn": "9788901234568", "location": "nj", "quantity": 3 }
]
```

**성공 응답 (HTTP 200)**
```json
{
  "upserted": 3
}
```

**오류 응답 (HTTP 400 — 빈 배열)**
```json
{
  "detail": "배열이 비어 있습니다."
}
```

---

### DELETE /api/warehouse/stock/\<pk\>/

**요청**
```
DELETE /api/warehouse/stock/1/
Authorization: Bearer <access_token>
```

**성공 응답 (HTTP 204)** — 응답 바디 없음

**오류 응답 (HTTP 404)**
```json
{
  "detail": "Not found."
}
```

---

## 비기능 요구사항

### 보안

- 모든 엔드포인트는 JWT 인증 필수(`JWTAuthentication + IsAuthenticated`).
- 인증되지 않은 요청은 HTTP 401로 즉시 거부.

### 데이터 무결성

- `unique_together = [("isbn", "location")]` 제약으로 동일 ISBN+위치의 중복 레코드를 DB 수준에서 방지.
- `quantity`는 정수(`IntegerField`)이며 음수 방어는 뷰 레이어에서 처리.

### 성능

- `isbn` 컬럼 인덱스로 검색 필터 쿼리 성능 확보.
- 피벗 응답은 서버사이드에서 집계하여 클라이언트 측 추가 가공 없이 직접 렌더링 가능.

### 프론트엔드

- TanStack Query v5 훅으로 서버 상태를 관리하여 낙관적 UI 업데이트 및 자동 무효화(invalidate) 지원.
- 페이지는 React lazy-loading으로 처리하여 초기 번들 크기 최소화.

---

## 제외 사항 (What NOT to Build)

- **위치별 재고 이동 이력**: 창고 간 재고 이동(transfer) 내역 추적 기능은 이 SPEC의 범위가 아니다.
- **재고 임계값 알림**: 재고가 특정 수량 이하로 떨어질 때 이메일·슬랙 알림을 발송하는 기능은 구현하지 않는다.
- **주문과의 자동 재고 차감 연동**: Shopify 주문 생성 시 해당 ISBN의 창고 재고를 자동으로 차감하는 기능은 별도 SPEC으로 처리한다.
- **바코드/QR 스캔 입력**: 창고 현장에서 스캐너 장비로 재고를 입력하는 기능은 구현하지 않는다.
- **창고 위치 동적 추가**: `korea`, `ca`, `nj` 외 새로운 창고 위치를 관리자가 UI에서 추가하는 기능은 구현하지 않는다. 위치 목록은 코드에 고정(hardcoded)된다.
- **재고 수량 음수 보호 규칙**: 재고가 0 미만이 되는 경우를 시스템이 자동으로 차단하는 도메인 규칙은 현재 SPEC에 포함하지 않는다.
