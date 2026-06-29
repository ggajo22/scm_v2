---
id: SPEC-SHOPIFY-SKU-SET-001
version: "1.0"
status: Implemented
created: 2026-06-29
updated: 2026-06-29
author: ggajo
priority: High
issue_number: ~
---

# HISTORY

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| 1.0 | 2026-06-29 | 최초 작성 |

---

# SPEC-SHOPIFY-SKU-SET-001: Shopify SKU 세트/번들 매핑 관리

## 개요

Shopify 일부 상품은 "세트" 상품으로, 하나의 SKU가 여러 개별 ISBN을 묶어 판매한다.  
예: `"GITANMATH-F SET"` → ISBN 5종 (`9788926025451`, `9788926025468`, `9788926025475`, `9788926025482`, `9788926025499`)

현재 세트 SKU가 주문에 포함되어도 어떤 개별 ISBN이 필요한지 알 수 없어, 발주 생성이 불가능하다.  
본 SPEC은 세트 SKU와 구성 ISBN 간 매핑을 관리하는 기능을 정의한다.

---

## 범위 (Scope)

- **대상**: Django 백엔드(DRF) + React 프론트엔드 관리자 앱
- **핵심 동작**: 세트 SKU 매핑 CRUD, 발주 생성 시 세트 SKU 자동 전개(expansion)
- **확정된 결정 사항**:
  - 전개 시점: 발주 생성 시 (`UnorderedItemsView` 응답)
  - 수량 동작: 구성 ISBN 각각에 번들 수량을 그대로 적용
  - 관리 UI: `/settings/sku-sets` 별도 설정 페이지

---

## 요구사항 (EARS Format)

### REQ-SKU-SET-001: ShopifySkuSetMapping 모델

**The system shall** `ShopifySkuSetMapping` Django 모델을 `order` 앱에 추가한다.

- 필드 명세:
  - `id`: AutoField (PK)
  - `bundle_sku`: CharField(max_length=200, db_index=True) — Shopify 세트 SKU 값 (예: "GITANMATH-F SET")
  - `member_isbn`: CharField(max_length=20) — 구성 개별 ISBN
  - `sort_order`: IntegerField(default=0) — 정렬 순서
  - `created_at`: DateTimeField(auto_now_add=True)
  - `updated_at`: DateTimeField(auto_now=True)
- 하나의 `bundle_sku`에 여러 `member_isbn` 행이 존재한다 (1:N 관계)
- `Meta.db_table = "order_shopify_sku_set_mapping"`
- `Meta.ordering = ["bundle_sku", "sort_order"]`
- `Meta.indexes`에 `bundle_sku` 단일 인덱스 포함

**When** 동일한 `bundle_sku`와 `member_isbn` 조합이 저장될 때, **the system shall** `unique_together = [("bundle_sku", "member_isbn")]` 제약으로 중복 저장을 방지한다.

### REQ-SKU-SET-002: 번들 매핑 관리 REST API

**The system shall** 아래 엔드포인트를 제공한다. 모든 엔드포인트는 JWT 인증(`IsAuthenticated`)을 요구한다.

| Method | URL | 설명 |
|--------|-----|------|
| GET | `/api/shopify-sku-sets/` | 전체 번들 SKU 목록 및 구성 ISBN 조회 |
| POST | `/api/shopify-sku-sets/` | 번들 매핑 신규 생성 |
| GET | `/api/shopify-sku-sets/{bundle_sku}/` | 특정 번들의 구성 ISBN 조회 |
| PUT | `/api/shopify-sku-sets/{bundle_sku}/` | 특정 번들의 구성 ISBN 전체 교체 (atomic) |
| DELETE | `/api/shopify-sku-sets/{bundle_sku}/` | 특정 번들 매핑 전체 삭제 |

**When** `GET /api/shopify-sku-sets/`를 호출할 때, **the system shall** `bundle_sku` 기준으로 그룹화하여 아래 구조로 응답한다. 각 `member_isbn`에는 `book.Info.name`에서 조회한 책 제목(`book_title`)을 포함하며, 해당 ISBN이 `Inven`에 존재하지 않으면 `null`로 반환한다:

```json
[
  {
    "bundle_sku": "GITANMATH-F SET",
    "member_isbns": [
      {"isbn": "9788926025451", "sort_order": 0, "book_title": "기탄수학 F1"},
      {"isbn": "9788926025468", "sort_order": 1, "book_title": null}
    ]
  }
]
```

**The system shall** `book_title` 조회 시 `Inven.inven_SKU = member_isbn` 조건으로 `book_inven` → `book_info` 테이블을 `select_related`로 조인하여 N+1 쿼리를 방지한다.

**When** `POST /api/shopify-sku-sets/`를 호출할 때, **the system shall** 요청 본문 `{"bundle_sku": "...", "member_isbns": ["...", "..."]}` 을 파싱하여 각 ISBN을 `ShopifySkuSetMapping` 행으로 저장한다.

**When** `PUT /api/shopify-sku-sets/{bundle_sku}/`를 호출할 때, **the system shall** 해당 `bundle_sku`의 기존 매핑 전체를 삭제하고 새 `member_isbns` 목록으로 원자적으로(atomic) 교체한다.

**When** `DELETE /api/shopify-sku-sets/{bundle_sku}/`를 호출할 때, **the system shall** 해당 `bundle_sku`에 속한 모든 `ShopifySkuSetMapping` 행을 삭제한다.

**If** 존재하지 않는 `bundle_sku`로 GET/PUT/DELETE를 요청하면, **then the system shall** HTTP 404를 반환한다.

**If** POST/PUT 요청에서 `bundle_sku`가 빈 문자열이거나 `member_isbns`가 빈 배열이면, **then the system shall** HTTP 400을 반환하고 오류 메시지를 포함한다.

### REQ-SKU-SET-003: 발주 생성 시 세트 SKU 전개

**When** `GET /api/purchase-orders/unordered/`를 호출할 때, **the system shall** 각 `LineItem.sku`가 `ShopifySkuSetMapping.bundle_sku`와 일치하는지 확인한다.

**When** `LineItem.sku`가 `bundle_sku`에 매핑되어 있을 때, **the system shall** 해당 `LineItem`을 원본 응답 대신 구성 ISBN 수만큼의 행으로 전개하여 반환한다. 각 전개 행은:

- `sku`: `member_isbn` 값
- `quantity`: 원본 `LineItem.quantity` (수량 동일 적용)
- `is_bundle_member`: `true`
- `bundle_sku`: 원본 `LineItem.sku` 값

를 포함한다.

**While** 세트 SKU 매핑이 존재하지 않을 때, **the system shall** 기존 동작을 그대로 유지한다(원본 SKU 반환, `is_bundle_member` 필드 없음 또는 `false`).

**The system shall** 세트 전개 시 성능을 위해 `ShopifySkuSetMapping` 전체를 한 번의 쿼리로 로드하여 메모리 내 딕셔너리로 매핑한다.

### REQ-SKU-SET-004: 프론트엔드 설정 페이지

**The system shall** `/settings/sku-sets` 경로에 번들 매핑 관리 페이지를 제공한다.

**The system shall** 다음 기능을 포함한다:
- 전체 번들 SKU 목록 테이블 표시: 열 구성 — bundle_sku, 구성 ISBN 목록 (ISBN + 책 제목 함께 표시), 액션 버튼
- 책 제목은 API 응답의 `book_title` 필드를 표시하며, `null`인 경우 "—" 또는 "(등록 안됨)"으로 표시
- 신규 번들 추가 폼 (bundle_sku 입력, ISBN 목록 입력)
- 기존 번들 편집 (구성 ISBN 수정)
- 번들 삭제 확인 후 제거

**Where** 기존 설정 페이지 UI 스타일이 존재할 때, **the system shall** 동일한 React 컴포넌트 라이브러리(shadcn/ui, Tailwind CSS)를 사용한다.

**When** API 호출이 성공할 때, **the system shall** 목록을 자동으로 갱신(refetch)한다.

**If** API 호출이 실패할 때, **then the system shall** 사용자에게 오류 메시지를 표시한다.

---

## 비기능 요구사항

**The system shall** `UnorderedItemsView` 세트 전개 로직이 기존 응답 시간 대비 추가 쿼리를 최소화한다 (최대 1회 추가 쿼리 허용).

**The system shall** `ShopifySkuSetMapping` 테이블의 Django 마이그레이션 파일을 생성하여 스키마 변경을 추적한다.

---

## Exclusions (What NOT to Build)

- **Shopify 싱크 변경 없음**: `LineItem.sku`는 Shopify 원본 값 그대로 저장. 싱크 로직 수정 범위 외.
- **데일리 리뷰 업로드 전개 없음**: 일일 CS 검토 업로드 흐름에는 세트 SKU 전개를 적용하지 않는다.
- **기존 PurchaseOrder 소급 전개 없음**: 이미 생성된 발주 레코드는 변경하지 않는다.
- **자동 Shopify SKU 감지 없음**: 세트 여부는 수동으로 매핑 테이블에 등록하며, Shopify API에서 자동 판별하지 않는다.
- **역방향 조회 없음**: ISBN → bundle_sku 역방향 검색 기능은 제공하지 않는다.
- **권한 세분화 없음**: 별도 권한 역할(Role)을 추가하지 않으며, 기존 `IsAuthenticated` JWT 인증만 적용한다.
