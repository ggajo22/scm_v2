---
id: SPEC-BOOK-EDIT-001
version: "0.1.0"
status: completed
created: "2026-06-20"
updated: "2026-06-20"
author: ggajo
priority: high
issue_number: 0
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-06-20 | ggajo | 최초 작성 — 도서 정보 수정 화면 SPEC |

---

## 개요

### 문제 정의

도서 검색(SPEC-BOOK-SEARCH-001)으로 도서 목록을 조회한 후, 특정 도서를 선택하여 상세 정보를 확인하고 수정할 방법이 없다. 관리자는 도서 기본 정보 편집, 메모(노트) 관리, Shopify 상태 변경, Etoile(Etoile) 정보 관리를 모두 개별 DB 쿼리 또는 레거시 시스템에서 수행해야 한다.

### 목표

1. 도서 검색 결과에서 도서를 클릭하면 해당 도서의 전체 정보를 조회·수정할 수 있는 화면을 제공한다.
2. 도서 기본 정보(Info 모델 필드), 노트, Shopify 상태, Etoile 정보를 단일 화면에서 통합 관리할 수 있도록 한다.
3. 레거시 `UpdateBookInfoView`와 동등한 기능을 REST API + React SPA 방식으로 제공한다.

### 비목표 (Non-Goals)

- 이 SPEC은 도서 **생성** 또는 **삭제** 기능을 다루지 않는다.
- Shopify 상품 상세 페이지 직접 편집(메타필드, 옵션 등)은 다루지 않는다.
- Etoile 영문 설명(`desc_en`) 및 영문 제목(`name_en`) 직접 편집은 이 SPEC 범위 밖이다 (조회만 제공).
- 이미지 업로드(cover_image_url 외부 URL 입력은 가능하나 파일 업로드는 제외)는 다루지 않는다.
- 교보 카테고리, 부클 카테고리 코드 목록 관리는 이 SPEC에 포함하지 않는다.

---

## 시스템 컨텍스트

### 액터

| 액터 | 설명 |
|------|------|
| 관리자 (Admin) | JWT 로그인 완료된 내부 운영자. 도서 정보 수정 권한 보유 |
| Shopify API | 본관/Etoile Shopify 스토어의 외부 REST API |

### 관련 시스템 및 의존성

| 시스템 | 역할 |
|--------|------|
| SPEC-AUTH-001 | JWT 발급·갱신·검증 — 모든 API 요청의 인증 전제 |
| SPEC-BOOK-SEARCH-001 | 도서 목록 검색 — 이 화면의 진입점(도서 클릭 → 수정 화면) |
| Shopify REST API | 상품 상태(active/draft) 변경 외부 호출 |
| MySQL (AWS RDS) | Inven, Info, BookNote, EtoileBookInven, EtoileBookInfo, Shopify_product 모델 저장소 |

---

## 요구사항 (EARS 형식)

### 1. 데이터 조회 (GET)

**REQ-BKEDIT-001**: `WHEN` 관리자가 `GET /api/book/{id}/`를 요청하면, 시스템은 해당 `Inven` 레코드 및 연관된 `Info`, `BookNote`(미해결 + 최근 해결 10건), `Shopify_product`, `EtoileBookInven`, `EtoileBookInfo`, `EtoileShopifyProduct` 데이터를 단일 응답으로 반환하여야 한다.

**REQ-BKEDIT-002**: `IF` 요청한 `{id}`에 해당하는 `Inven` 레코드가 존재하지 않으면, 시스템은 HTTP 404 Not Found를 반환하여야 한다.

**REQ-BKEDIT-003**: `WHERE` `EtoileBookInven` 연관 레코드가 존재하는 경우, 시스템은 Etoile 섹션 데이터(`etoile_inven`, `etoile_info`, `etoile_shopify_product`)를 응답에 포함하여야 한다. 존재하지 않으면 해당 필드를 `null`로 반환하여야 한다.

**REQ-BKEDIT-004**: 시스템은 `GET /api/book/{id}/` 엔드포인트에 대해 유효한 JWT 인증을 요구하여야 한다.

**REQ-BKEDIT-005**: `WHEN` 인증되지 않은 요청이 도서 상세 엔드포인트에 도달하면, 시스템은 HTTP 401 Unauthorized를 반환하여야 한다.

---

### 2. 도서 기본 정보 수정 (PATCH)

**REQ-BKEDIT-006**: `WHEN` 관리자가 `PATCH /api/book/{id}/info/`를 요청하면, 시스템은 요청 바디에 포함된 `Info` 모델 필드만 선택적으로 업데이트하여야 한다 (partial update).

**REQ-BKEDIT-007**: `WHEN` `Info` 수정 요청이 성공하면, 시스템은 업데이트된 전체 `Info` 필드를 HTTP 200 OK와 함께 반환하여야 한다.

**REQ-BKEDIT-008**: `IF` 수정 요청 바디에 유효하지 않은 필드 값이 포함된 경우 (예: `price`에 문자열, `status`에 허용되지 않는 값), 시스템은 HTTP 400 Bad Request와 필드별 오류 메시지를 반환하여야 한다.

**REQ-BKEDIT-009**: `WHEN` 관리자가 `Info` 수정 요청을 전송하면, 시스템은 `Info.updated_at`을 현재 시각으로 갱신하여야 한다.

**REQ-BKEDIT-010**: 시스템은 수정 가능한 `Info` 필드 그룹을 다음과 같이 정의하여야 한다:
- **기본 필드**: `name`, `cover_image_url`, `manual_weight`, `price`, `kyobo_supply_price`, `status`, `price_sale`, `useruse1`, `useruse2`, `opndate`, `dim1`, `dim2`, `dim3`, `page`, `qty`, `image_detail`
- **부클 필드**: `booxen_cate_cd1`, `booxen_cate_cd2`, `booxen_cate_cd3`
- **교보 필드**: `kyobo_category1`, `kyobo_category2`, `kyobo_category3`, `kyobo_category4`, `kyobo_category5`, `kyobo_weight`
- **중량 필드**: `weight`, `yes24_weight`, `aladin_weight`
- **장문 텍스트 필드**: `desc_desc`, `desc_table`, `desc_pub`, `desc_author`

---

### 3. 노트 관리

**REQ-BKEDIT-011**: `WHEN` 관리자가 `POST /api/book/{id}/notes/`를 요청하면, 시스템은 `note_type`(GENERAL 또는 SHIPPING)과 `content`를 받아 `BookNote`를 생성하고, 생성된 노트를 HTTP 201 Created와 함께 반환하여야 한다.

**REQ-BKEDIT-012**: `IF` 노트 생성 요청에 `note_type` 또는 `content`가 누락되거나 유효하지 않으면, 시스템은 HTTP 400 Bad Request와 오류 메시지를 반환하여야 한다.

**REQ-BKEDIT-013**: `WHEN` 관리자가 `PATCH /api/book/notes/{note_id}/resolve/`를 요청하면, 시스템은 해당 `BookNote`의 `is_resolved`를 `True`로, `resolved_at`을 현재 시각으로 설정하고 업데이트된 노트를 반환하여야 한다.

**REQ-BKEDIT-014**: `IF` 해결 요청 대상 노트가 `note_type: SHIPPING`이면, 시스템은 HTTP 400 Bad Request를 반환하여야 한다 (SHIPPING 노트는 해결 처리 불가).

**REQ-BKEDIT-015**: `IF` 해결 요청 대상 노트가 이미 `is_resolved: True`이면, 시스템은 HTTP 400 Bad Request를 반환하여야 한다.

**REQ-BKEDIT-016**: `WHEN` 도서 상세 정보가 조회되면, 시스템은 미해결(`is_resolved: False`) 노트 전체와 최근 해결된 노트 10건을 함께 반환하여야 한다.

---

### 4. Shopify 상태 변경

**REQ-BKEDIT-017**: `WHEN` 관리자가 `PATCH /api/book/{id}/shopify-status/`를 `action: active` 또는 `action: draft`로 요청하면, 시스템은 외부 Shopify API를 호출하여 해당 상품 상태를 변경하고 성공 시 `Inven.status_of_shopify`를 갱신하여야 한다.

**REQ-BKEDIT-018**: `WHEN` 관리자가 `PATCH /api/book/{id}/etoile-shopify-status/`를 `action: active` 또는 `action: draft`로 요청하면, 시스템은 Etoile Shopify API를 호출하여 해당 상품 상태를 변경하고 성공 시 `EtoileBookInven.status_of_shopify`를 갱신하여야 한다.

**REQ-BKEDIT-019**: `IF` Shopify API 호출이 실패하면 (네트워크 오류, 4xx/5xx 응답), 시스템은 DB 상태를 변경하지 않고 HTTP 502 Bad Gateway와 오류 원인을 반환하여야 한다.

**REQ-BKEDIT-020**: `IF` Etoile Shopify 상태 변경 요청 시 `EtoileBookInven` 레코드가 존재하지 않으면, 시스템은 HTTP 404 Not Found를 반환하여야 한다.

---

### 5. Etoile 태그 관리

**REQ-BKEDIT-021**: `WHEN` 관리자가 `PATCH /api/book/{id}/etoile-tags/`를 요청하면, 시스템은 `tags` 필드(문자열 배열)를 `EtoileBookInfo.tags` JSONField에 저장하고, Shopify API를 통해 Etoile 상품 태그를 동기화하여야 한다.

**REQ-BKEDIT-022**: `IF` Etoile 태그 저장 후 Shopify API 동기화가 실패하면, 시스템은 DB 저장은 유지하되 HTTP 207 Multi-Status로 부분 성공을 반환하여야 한다.

**REQ-BKEDIT-023**: `IF` Etoile 태그 변경 요청 시 `EtoileBookInfo` 레코드가 존재하지 않으면, 시스템은 HTTP 404 Not Found를 반환하여야 한다.

---

### 6. 프론트엔드 UX

**REQ-BKEDIT-024**: `WHEN` 관리자가 도서 검색 결과 테이블에서 특정 도서 행을 클릭하면, 시스템은 `/book/{id}/edit` 경로로 이동하여 해당 도서의 수정 화면(`BookDetailPage`)을 표시하여야 한다.

**REQ-BKEDIT-025**: `WHEN` `BookDetailPage`가 로드되면, 시스템은 `GET /api/book/{id}/` API를 호출하여 도서 정보를 가져오고 로딩 중에는 스켈레톤 또는 로딩 인디케이터를 표시하여야 한다.

**REQ-BKEDIT-026**: `WHILE` 도서 수정 폼이 표시된 상태에서, 시스템은 필드 그룹별로 탭 또는 섹션을 구분하여 표시하여야 한다 (기본 정보, 부클, 교보, 중량, 장문 텍스트, 노트, Shopify 상태, Etoile).

**REQ-BKEDIT-027**: `WHEN` 관리자가 기본 정보 저장 버튼을 클릭하면, 시스템은 변경된 필드만 포함한 PATCH 요청을 전송하고, 성공 시 인라인 성공 피드백(토스트 또는 배너)을 표시하여야 한다.

**REQ-BKEDIT-028**: `IF` API 저장 요청이 실패하면, 시스템은 오류 메시지를 화면에 표시하고 폼 상태를 저장 이전 값으로 유지하여야 한다.

**REQ-BKEDIT-029**: `WHERE` Etoile 연관 데이터가 존재하는 경우, 시스템은 Etoile 섹션(태그, Shopify 상태)을 화면에 표시하여야 한다. 존재하지 않는 경우 Etoile 섹션을 숨기거나 비활성 상태로 표시하여야 한다.

**REQ-BKEDIT-030**: `WHEN` 관리자가 도서 수정 화면에서 뒤로가기 또는 검색 링크를 클릭하면, 시스템은 도서 검색 화면(`/book`)으로 이동하여야 한다.

---

### 7. 보안

**REQ-BKEDIT-031**: 시스템은 도서 수정 관련 모든 API 엔드포인트(`GET /api/book/{id}/`, `PATCH /api/book/{id}/info/`, `POST /api/book/{id}/notes/`, `PATCH /api/book/notes/{note_id}/resolve/`, `PATCH /api/book/{id}/shopify-status/`, `PATCH /api/book/{id}/etoile-shopify-status/`, `PATCH /api/book/{id}/etoile-tags/`)에 대해 `IsAuthenticated` 권한 클래스를 적용하여야 한다.

**REQ-BKEDIT-032**: `WHEN` 노트를 생성하면, 시스템은 현재 인증된 사용자의 식별자를 `BookNote.created_by`에 기록하여야 한다.

---

### 8. 오류 처리

**REQ-BKEDIT-033**: `IF` 도서 상세 조회 중 데이터베이스 오류가 발생하면, 시스템은 HTTP 500 Internal Server Error를 반환하고 오류를 로그에 기록하여야 한다.

**REQ-BKEDIT-034**: `WHEN` 프론트엔드에서 API 요청 중 네트워크 오류 또는 서버 오류(5xx)가 발생하면, 시스템은 사용자에게 오류 알림을 표시하고 재시도 방법을 안내하여야 한다.

---

## 데이터 계약 (Data Contracts)

### GET /api/book/{id}/

**응답 (200 OK)**

```json
{
  "id": 1,
  "inven_SKU": "9791190090001",
  "vendor": "vendor_name",
  "store": "store_name",
  "is_prepared": 0,
  "status_of_shopify": 1,
  "info": {
    "id": 1,
    "status": "active",
    "price_sale": "15000.00",
    "name": "도서 제목",
    "useruse1": "",
    "useruse2": "",
    "price": "18000.00",
    "opndate": "2024-01-01",
    "qty": 100,
    "page": 320,
    "weight": 350,
    "kyobo_weight": 350,
    "kyobo_supply_price": "12000.00",
    "yes24_weight": 350,
    "aladin_weight": 350,
    "manual_weight": null,
    "dim1": null,
    "dim2": null,
    "dim3": null,
    "image_detail": "",
    "cover_image_url": "https://example.com/cover.jpg",
    "cover_image_url2": null,
    "booxen_cate_cd1": "",
    "booxen_cate_cd2": "",
    "booxen_cate_cd3": "",
    "kyobo_category1": "",
    "kyobo_category2": "",
    "kyobo_category3": "",
    "kyobo_category4": "",
    "kyobo_category5": "",
    "desc_desc": "",
    "desc_table": "",
    "desc_pub": "",
    "desc_author": "",
    "updated_at": "2026-06-20T12:00:00Z"
  },
  "notes": [
    {
      "id": 1,
      "note_type": "GENERAL",
      "content": "재고 확인 필요",
      "is_resolved": false,
      "resolved_at": null,
      "created_by": "admin",
      "created_at": "2026-06-20T10:00:00Z"
    }
  ],
  "shopify_products": [
    {
      "id": 1,
      "product_id": "123456789",
      "variant_id": "987654321",
      "shopify_price": "18000.00",
      "is_new_arrival": false,
      "image_url": ""
    }
  ],
  "etoile": {
    "inven": {
      "id": 1,
      "status_of_shopify": 1,
      "updated_at": "2026-06-20T12:00:00Z"
    },
    "info": {
      "id": 1,
      "name_en": "Book Title",
      "desc_en": "",
      "preview_urls": [],
      "tags": ["tag1", "tag2"],
      "updated_at": "2026-06-20T12:00:00Z"
    },
    "shopify_products": [
      {
        "id": 1,
        "product_id": "111222333",
        "variant_id": "444555666",
        "shopify_price": "20000.00",
        "is_new_arrival": false
      }
    ]
  }
}
```

> `etoile` 필드: `EtoileBookInven`이 없으면 `null` 반환.

---

### PATCH /api/book/{id}/info/

**요청 바디** (모든 필드 선택적 - partial update)

```json
{
  "name": "수정된 제목",
  "price": "19000.00",
  "manual_weight": 400
}
```

**응답 (200 OK)**: 업데이트된 `Info` 전체 필드

---

### POST /api/book/{id}/notes/

**요청 바디**

```json
{
  "note_type": "GENERAL",
  "content": "포장 주의 필요"
}
```

**응답 (201 Created)**

```json
{
  "id": 2,
  "note_type": "GENERAL",
  "content": "포장 주의 필요",
  "is_resolved": false,
  "resolved_at": null,
  "created_by": "admin",
  "created_at": "2026-06-20T13:00:00Z"
}
```

---

### PATCH /api/book/notes/{note_id}/resolve/

**요청 바디**: 없음 (빈 바디 허용)

**응답 (200 OK)**

```json
{
  "id": 1,
  "is_resolved": true,
  "resolved_at": "2026-06-20T14:00:00Z"
}
```

---

### PATCH /api/book/{id}/shopify-status/

**요청 바디**

```json
{
  "action": "active"
}
```

> `action` 허용값: `"active"`, `"draft"`

**응답 (200 OK)**

```json
{
  "status_of_shopify": 1,
  "action": "active"
}
```

---

### PATCH /api/book/{id}/etoile-shopify-status/

**요청 바디**

```json
{
  "action": "draft"
}
```

**응답 (200 OK)**

```json
{
  "status_of_shopify": 0,
  "action": "draft"
}
```

---

### PATCH /api/book/{id}/etoile-tags/

**요청 바디**

```json
{
  "tags": ["신간", "추천", "소설"]
}
```

**응답 (200 OK)**

```json
{
  "tags": ["신간", "추천", "소설"],
  "shopify_sync": "success"
}
```

> Shopify 동기화 실패 시: HTTP 207 응답, `"shopify_sync": "failed"`

---

## 수락 기준 요약

| 요구사항 ID | 검증 방법 |
|-------------|-----------|
| REQ-BKEDIT-001 | `GET /api/book/1/` 응답이 Info, Notes, Shopify, Etoile 필드를 모두 포함하는지 단위 테스트 |
| REQ-BKEDIT-002 | 존재하지 않는 ID로 요청 시 HTTP 404 반환 확인 |
| REQ-BKEDIT-003 | Etoile 없는 도서 조회 시 `etoile: null` 반환 확인 |
| REQ-BKEDIT-006~009 | PATCH 요청 후 DB 필드 값 변경 및 `updated_at` 갱신 확인 |
| REQ-BKEDIT-011~015 | 노트 CRUD 각 경우에 대한 HTTP 상태 코드 및 응답 바디 확인 |
| REQ-BKEDIT-017~020 | Shopify API mock 사용하여 성공/실패 시나리오 확인 |
| REQ-BKEDIT-024~030 | E2E: 검색 결과 클릭 → 수정 화면 진입 → 저장 → 피드백 표시 흐름 |
| REQ-BKEDIT-031~032 | 미인증 요청 시 401 반환, 노트 생성 시 created_by 기록 확인 |

---

## 제외 항목 (What NOT to Build)

- **도서 생성**: `POST /api/book/` 신규 등록 기능은 이 SPEC에 포함하지 않는다.
- **도서 삭제**: `DELETE /api/book/{id}/` 삭제 기능은 이 SPEC에 포함하지 않는다.
- **이미지 파일 업로드**: `cover_image_url`은 외부 URL 문자열 입력만 허용하며, 파일 업로드 기능은 포함하지 않는다.
- **Etoile 영문 정보 편집**: `EtoileBookInfo.name_en`, `desc_en`, `preview_urls` 수정 기능은 포함하지 않는다 (조회만 가능).
- **카테고리 코드 목록 API**: 부클/교보 카테고리 코드 선택용 드롭다운 목록 API는 이 SPEC에 포함하지 않는다 (직접 입력).
- **Shopify 웹훅 수신**: 외부 Shopify 이벤트에 의한 자동 상태 동기화는 포함하지 않는다.
- **권한 역할 분리**: 관리자 역할 내 세부 권한 분리(읽기 전용 vs 편집)는 포함하지 않는다.

---

## 의존성

| SPEC ID | 의존 이유 |
|---------|----------|
| SPEC-AUTH-001 | JWT 인증 체계 — 모든 API 엔드포인트의 `IsAuthenticated` 권한 클래스 전제 |
| SPEC-BOOK-SEARCH-001 | 도서 검색 결과 테이블 — 이 SPEC의 진입점(도서 행 클릭 → `/book/{id}/edit` 이동) |
