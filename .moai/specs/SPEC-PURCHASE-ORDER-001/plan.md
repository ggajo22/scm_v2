# SPEC-PURCHASE-ORDER-001 구현 계획

## 개요

발주(Purchase Order) 관리 시스템을 기존 `order` Django 앱에 확장하여 구현한다. 프론트엔드는 기존 발주 관리 페이지를 `/purchase-orders` 경로에 신규 추가한다.

---

## 마일스톤

### M1 — 백엔드 모델 및 마이그레이션 (Priority: High)

**목표**: 신규 3개 모델 생성 및 DB 마이그레이션 적용

**작업 범위**:
- `backend/order/models.py`에 `PurchaseOrder`, `VendorComparison`, `DistributorVendorRule` 모델 추가
- `PurchaseOrder.line_items` ManyToManyField 설정
- Django 마이그레이션 파일 생성 (`makemigrations`)
- DB 테이블 접두사 `orders_` 확인 (`Meta.db_table` 지정)

**의존성**: 없음 (SPEC-ORDER-001 LineItem 모델 기반, 변경 없음)

**위험 요소**:
- `PurchaseOrder ↔ LineItem` M2M 관계가 기존 `unique_together` 제약과 충돌 여부 확인 필요
- MySQL `orders_purchaseorder_line_items` 중간 테이블 자동 생성 확인

---

### M2 — 미발주 현황 API (Priority: High)

**목표**: `GET /api/purchase-orders/unordered/` 구현

**작업 범위**:
- `backend/order/views.py` 또는 별도 `purchase_order_views.py`에 `UnorderedItemsView` 추가
- `LineItem.purchase_orders.none()`(M2M 역참조로 연결 없는 LineItem 필터) 쿼리 작성
- SKU별 집계: `values("sku", "title", "vendor").annotate(total_quantity=Sum("quantity"), order_count=Count("order", distinct=True))`
- `DistributorVendorRule` 조회로 `auto_distributor` 결정 로직
- URL 등록: `backend/order/urls.py`
- Serializer 작성

**의존성**: M1 완료

---

### M3 — 발주 파일 생성 API (Priority: High)

**목표**: `POST /api/purchase-orders/generate-order-file/` 구현

**작업 범위**:
- `openpyxl` 라이브러리를 사용한 Excel 파일 생성 (헤더: ISBN, 도서명, 수량)
- `FileResponse` 또는 `HttpResponse`로 Excel 바이너리 반환
- `unknown_skus` 경고 처리 로직
- `pyproject.toml`에 `openpyxl` 의존성 추가 확인

**의존성**: M1 완료

**기술 접근**:
- `openpyxl.Workbook`으로 인메모리 Excel 생성 (`io.BytesIO` 사용)
- 스트리밍 응답으로 파일 크기 무관하게 처리

---

### M4 — 업체 자료 업로드 및 비교 API (Priority: High)

**목표**: `POST /api/purchase-orders/upload-vendor-file/` 및 `GET /api/purchase-orders/comparison/` 구현

**작업 범위**:
- Multipart 파일 업로드 수신 (`request.FILES["file"]`)
- `openpyxl`로 Excel 파싱: ISBN, 재고 여부, 단가 컬럼 추출
- `VendorComparison` upsert (`update_or_create(sku=sku)`)
- 자동 발주처 선택 로직:
  - 재고 있는 업체 우선
  - 양쪽 재고 있으면 단가 낮은 업체 선택
- 파일 형식 유효성 검사 (`.xlsx`, `.xls` 확장자)
- 컬럼 누락 시 HTTP 422 반환

**의존성**: M1 완료

**위험 요소**:
- 업체 Excel 파일의 컬럼명이 북센·교보마다 다를 수 있음
  → 초기 구현에서는 컬럼 위치(순서) 기반 파싱으로 단순화

---

### M5 — 발주 확정 API (Priority: High)

**목표**: `POST /api/purchase-orders/confirm/` 구현

**작업 범위**:
- 요청 데이터 유효성 검사 (Serializer)
- 미발주 `LineItem` 조회 및 존재 여부 확인
- 이중 발주 방지 로직 (이미 연결된 LineItem 확인)
- `PurchaseOrder` 생성 및 `line_items` M2M 연결 (`bulk_create` 또는 반복)
- 트랜잭션 원자성 보장 (`@transaction.atomic`)
- HTTP 201 응답 반환

**의존성**: M1 완료

---

### M6 — 발주처 규칙 CRUD API (Priority: Medium)

**목표**: `GET/POST /api/purchase-orders/vendor-rules/` 및 `DELETE /api/purchase-orders/vendor-rules/{id}/` 구현

**작업 범위**:
- `DistributorVendorRule`에 대한 DRF `ModelViewSet` 또는 개별 뷰 작성
- 중복 `publisher_name` 처리 (HTTP 409)
- 삭제 시 `LineItem.vendor` 기반 자동 발주처 추천에 영향 없음 확인

**의존성**: M1 완료

---

### M7 — 발주 목록 조회 API (Priority: Medium)

**목표**: `GET /api/purchase-orders/` 구현

**작업 범위**:
- `PurchaseOrder` 목록 DRF 뷰 작성
- `django-filter`를 사용한 `distributor`, `status`, `date_from`, `date_to` 필터
- DRF 표준 PageNumberPagination (50건/페이지)
- Serializer 작성 (연결된 `line_items` 수 포함)

**의존성**: M1 완료

---

### M8 — 프론트엔드 발주 관리 페이지 (Priority: High)

**목표**: `/purchase-orders` 경로에 6탭 발주 관리 페이지 구현

**작업 범위**:
- `frontend/src/pages/PurchaseOrders/` 디렉토리 생성
- `PurchaseOrderPage.tsx` (탭 레이아웃)
- 탭별 컴포넌트:
  - `UnorderedItemsTab.tsx` — 미발주 현황 테이블 + 파일 생성 트리거
  - `GenerateOrderFileTab.tsx` — 파일 생성 UI
  - `VendorFileUploadTab.tsx` — 파일 업로드 + 비교 테이블
  - `ConfirmOrderTab.tsx` — 발주 확정
  - `PurchaseOrderHistoryTab.tsx` — 발주 이력
  - `VendorRulesTab.tsx` — 규칙 설정
- TanStack Query hooks: `usePurchaseOrderQueries.ts`
- Zustand store: `usePurchaseOrderStore.ts` (탭 선택 상태, 체크박스 선택)
- `frontend/src/services/purchaseOrderApi.ts` API 통신 레이어
- React Router에 `/purchase-orders` 경로 추가
- 사이드바에 "발주 관리" 메뉴 항목 추가

**의존성**: M2~M7 백엔드 API 완료

---

## 기술적 접근

### 백엔드 구조

기존 `order` 앱 내에 발주 관련 뷰를 추가한다. 별도 앱 분리는 하지 않는다 (기존 패턴 유지).

```
backend/order/
├── models.py          # PurchaseOrder, VendorComparison, DistributorVendorRule 추가
├── serializers.py     # 발주 관련 Serializer 추가
├── views.py           # 발주 관련 View 추가 (또는 purchase_order_views.py 분리)
├── urls.py            # /api/purchase-orders/* URL 등록
└── filters.py         # PurchaseOrder 필터셋 추가
```

### 프론트엔드 구조

```
frontend/src/
├── pages/
│   └── PurchaseOrders/
│       ├── index.tsx
│       ├── tabs/
│       │   ├── UnorderedItemsTab.tsx
│       │   ├── VendorFileUploadTab.tsx
│       │   ├── ConfirmOrderTab.tsx
│       │   ├── PurchaseOrderHistoryTab.tsx
│       │   └── VendorRulesTab.tsx
│       └── components/
│           ├── ComparisonTable.tsx
│           └── UnorderedItemsTable.tsx
├── services/
│   └── purchaseOrderApi.ts
├── hooks/
│   └── usePurchaseOrderQueries.ts
└── stores/
    └── usePurchaseOrderStore.ts
```

### Excel 처리

- **생성**: `openpyxl`로 서버사이드 Excel 생성, `io.BytesIO` 인메모리 처리
- **파싱**: `openpyxl` 또는 `pandas`로 업로드 파일 파싱 (컬럼 순서 기반)
- **다운로드**: 프론트엔드에서 `axios` 응답을 Blob으로 받아 `URL.createObjectURL`로 다운로드

---

## 위험 요소 및 대응

| 위험 | 영향도 | 대응 방안 |
|------|--------|-----------|
| 업체 Excel 컬럼 형식 불일치 | High | 초기 구현에서 컬럼 순서 기반 파싱; 추후 매핑 UI 별도 SPEC |
| LineItem M2M 쿼리 성능 | Medium | `prefetch_related("purchase_orders")` 최적화, 인덱스 확인 |
| 대용량 Excel 파일 파싱 | Low | 현재 도서 발주 수량은 소규모로 예상; 문제 발생 시 스트리밍 파싱 도입 |
| 이중 발주 경쟁 조건 | Medium | `@transaction.atomic` + `select_for_update()` 적용 |
| openpyxl 의존성 추가 | Low | pyproject.toml에 이미 포함 여부 확인 후 추가 |

---

## 우선순위 순서 (구현 순서)

1. **Priority High**: M1 → M2 → M3 → M4 → M5 → M8
2. **Priority Medium**: M6 → M7
3. 백엔드 M1~M7 완료 후 프론트엔드 M8 착수
