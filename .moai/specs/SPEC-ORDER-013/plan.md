# SPEC-ORDER-013 구현 계획

## 기술 접근

브라운필드 변경. 기존 `order` 앱(`backend/order/`)의 모델·뷰·엑셀 유틸리티와 기존
`frontend/src/pages`, `frontend/src/services`, `frontend/src/hooks` 구조를 확장한다. 새
Django 앱이나 신규 최상위 프론트엔드 모듈 디렉터리는 만들지 않는다. 아래 [NEW]/[MODIFY]
마커는 CLAUDE.md 브라운필드 규칙에 따른 표기다. 개발 방법론은 `quality.yaml`의
`development_mode: tdd`(RED-GREEN-REFACTOR) — 신규 필드/신규 엔드포인트/신규 페이지가
중심이므로 기존 write path를 건드리는 SPEC-ORDER-012와 달리 브라운필드 사전 이해 단계
비중은 상대적으로 낮지만, `LineItemDetailSerializer` 등 기존 응답 스키마를 확장하는 지점은
workflow-modes.md "Brownfield Enhancement" 절을 따른다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 데이터 모델 (Priority: High)

- [MODIFY] `backend/order/models.py`
  - `LineItem` 클래스(141-196행)에 `location` 필드(171행) 바로 아래에 `rack_number` 필드
    추가: `models.CharField(max_length=10, blank=True, default="")` — `location`과 완전히
    동일한 시그니처(REQ-RACK-001).
  - 필드 선언 옆에 `logistics_status`(180-185행) 주석 패턴을 미러링해, 계산 전용이 아닌
    수동/업로드 전용 필드이며 `Order` 레벨 집계가 없음(REQ-RACK-002)을 설명하는 주석 추가.
- [NEW] 마이그레이션(계획 시점 기준 `0034`부터 — **Run 단계 착수 직전 최신 마이그레이션
  상태 재검증 필수**, SPEC-ORDER-011/012 모두 계획 시점 번호가 실제 구현 시점에 밀린 선례
  있음):
  - `0034_lineitem_add_rack_number.py` — `AddField` 단독,
    `0010_lineitem_add_location.py` 스타일 그대로 준수(백필 없음, REQ-RACK-001).

### M2 — 백엔드 API: 단건/일괄 PATCH (Priority: High)

참조 구현: `backend/order/purchase_order_views.py:1953-1994`
(`LineItemLogisticsStatusUpdateView`), `:1997-2052`
(`LineItemLogisticsStatusBulkUpdateView`).

- [MODIFY] `backend/order/purchase_order_views.py` — 위 두 클래스 바로 아래(또는 같은
  섹션)에 신규 클래스 2개 추가:
  - `LineItemRackNumberUpdateView(APIView)`: `PATCH
    /api/purchase-orders/line-items/<pk>/rack-number/`. `request.data.get("rack_number")`를
    받아 `len(value) > 10`이면 400(REQ-RACK-003b), LineItem 미존재 시 404(REQ-RACK-003a),
    그 외 `li.rack_number = value; li.save(update_fields=["rack_number"])` 후 `{id,
    rack_number, sku}` 응답(REQ-RACK-003). `JWTAuthentication` + `IsAuthenticated`
    보일러플레이트는 기존 두 클래스와 동일.
  - `LineItemBulkRackNumberUpdateView(APIView)`: `PATCH
    /api/purchase-orders/line-items/bulk-rack-number/`. Body `{"ids": [...], "rack_number":
    str}`. `ids` 빈 리스트면 400(REQ-RACK-004a). `rack_number` 10자 초과면 400
    (REQ-RACK-003b와 동일 검증 재사용). `LineItemBulkStatusUpdateView`(1895-1945행)와 동일
    패턴 — `existing = LineItem.objects.filter(pk__in=ids)`, `missing_ids` 계산,
    `existing.update(rack_number=value)`, `{updated_count, missing_ids}` 응답
    (REQ-RACK-004). **Order 레벨 재계산 호출 없음** — `rack_number`는 집계 필드가 아니므로
    `_recompute_order_aggregates()`를 호출하지 않는다(REQ-RACK-002, SPEC-ORDER-012와의
    핵심 차이).
- [MODIFY] `backend/order/urls.py`
  - `path("purchase-orders/line-items/bulk-rack-number/",
    LineItemBulkRackNumberUpdateView.as_view(), name="po-line-item-bulk-rack-number")`를
    `path("purchase-orders/line-items/<int:pk>/rack-number/", ...)`보다 **먼저** 등록
    (`bulk-status`/`bulk-logistics-status`가 각각의 `<int:pk>/...`보다 먼저 오는 기존
    관례, 64-77행 참조).
  - import 목록에 두 신규 클래스 추가.

### M3 — 백엔드 API: Excel 업로드 (Priority: High)

참조 구현: `backend/order/excel_utils.py:727-926`(`parse_daily_review_excel`, 이름 기반
다중 컬럼 헤더 탐색 스타일), `:944-983`(`_parse_sku_only_xlsx`, 대소문자 무시 substring
헤더 매칭 스타일 — `"sku" in h or "isbn" in h`), `purchase_order_views.py:1710-1772`
(`UploadVendorShipmentView`, 업로드 뷰/응답 형태).

- [MODIFY] `backend/order/excel_utils.py`
  - `_parse_sku_only_xlsx` 아래(991-1000행 근처)에 신규 함수
    `parse_rack_number_excel(file_bytes: bytes) -> list[dict]` 추가.
  - 헤더 행(`rows[0]`, `_parse_sku_only_xlsx`와 동일하게 첫 행 고정 — Daily Review처럼
    행 스캔이 필요한 다층 헤더가 아니므로 `_parse_sku_only_xlsx`의 단순 방식을 따름)을
    소문자화한 뒤, 아래 3개 컬럼을 각각 대소문자 무시 substring 매칭으로 탐색
    (REQ-RACK-005):
    - 주문번호: 헤더에 `"주문번호"` 또는 `"order"` 포함.
    - SKU: 헤더에 `"sku"` 또는 `"isbn"` 포함(`_parse_sku_only_xlsx`와 동일 별칭).
    - 렉번호: 헤더에 `"렉번호"` 또는 `"rack"` 포함.
  - 셋 중 하나라도 탐색 실패 시 `ValueError`(REQ-RACK-005a, 뷰에서 422로 변환).
  - 데이터 행: `order_number`(정수 파싱 실패/빈 값이면 skip), `sku`(빈 값이면 skip),
    `rack_number`(빈 문자열 허용 — 명시적으로 지우는 값으로 처리, strip만 적용)을 딕셔너리로
    반환.
- [NEW] `backend/order/purchase_order_views.py` — `UploadVendorShipmentView`/
  `UploadWarehouseReceiptView` 섹션 근처(1705-1839행 이후)에 신규 클래스
  `UploadRackNumberView(APIView)` 추가:
  - `POST /api/purchase-orders/upload-rack-number/`. `.xlsx` 확장자 검증(기존 두 업로드
    뷰와 동일).
  - `parse_rack_number_excel()` 호출 → `ValueError` 시 422(REQ-RACK-005a).
  - `(order_number, sku)` 키로 마지막-행-우선 dedup(`UploadVendorShipmentView`의
    `sku_map[row["sku"]] = row` 패턴을 튜플 키로 확장, REQ-RACK-006b).
  - `transaction.atomic()` 블록 안에서, dedup된 각 키에 대해:
    1. `Order.objects.filter(order_number=order_number).first()` — 없으면 skip
       (REQ-RACK-006a).
    2. 있으면 `LineItem.objects.filter(order=order, sku=sku)` — 0건이면 skip
       (REQ-RACK-006a); 1건 이상이면 전부 `rack_number=value`로 업데이트(결정 E,
       REQ-RACK-006).
  - `matched_count`/`skipped_count`는 distinct 키 개수 기준으로 집계(REQ-RACK-007,
    `_apply_logistics_transition`의 "SKU당 1회 집계" 관례를 (order_number, sku) 키로
    확장).
  - 응답: `{"matched_count": ..., "skipped_count": ...}`(기존
    `UploadLogisticsResponse` 형태와 동일).
- [MODIFY] `backend/order/urls.py`
  - `path("purchase-orders/upload-rack-number/", UploadRackNumberView.as_view(),
    name="po-upload-rack-number")` 추가(다른 업로드 경로들과 같은 블록).

### M4 — API 노출: 시리얼라이저 (Priority: Medium)

- [MODIFY] `backend/order/serializers.py`
  - `LineItemDetailSerializer.Meta.fields`(110-118행)에 `"location"`(113행) 옆에
    `"rack_number"` 추가(REQ 요구사항 8, `OrderDetailSerializer`를 통해 신규 페이지가
    이 필드를 재사용). `OrderDetailPage`는 이 필드를 UI에서 소비하지 않을 뿐(REQ-RACK-012)
    시리얼라이저 자체는 공용이므로 변경 대상.

### M5 — 프론트엔드: 신규 페이지, 라우팅, 메뉴 (Priority: High)

참조 구현: `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`(체크박스 컬럼 +
전체선택 + 일괄값 선택 + 적용 버튼 UX), `frontend/src/router/index.tsx`(lazy 라우트
등록 관례), `frontend/src/components/Sidebar.tsx`(`flatNavItems` 배열).

- [NEW] `frontend/src/pages/RackNumberPage.tsx`
  - 주문번호 검색 입력 + 검색 버튼(REQ-RACK-009/009a).
  - 검색 성공 시 LineItem 테이블 렌더링: 체크박스 컬럼(+ 헤더 전체선택,
    `UnorderedItemsTab.tsx` 194-202/226-235행 패턴 재사용) + SKU/도서명/현재 `rack_number`
    컬럼(REQ-RACK-010).
  - `rack_number` 컬럼 셀은 인라인 편집 가능한 텍스트 입력(값 변경 후 blur 또는 Enter로
    확정 시 단건 PATCH 호출, REQ-RACK-011) — `maxLength={10}` 속성으로 REQ-RACK-003b를
    프론트엔드에서도 사전 방어.
  - 체크박스 선택 상태는 로컬 `useState<number[]>`(LineItem id 배열, 결정 F) — 전역
    `usePurchaseOrderStore` 미사용.
  - 하단/상단에 일괄 적용 컨트롤: 텍스트 입력(렉번호 값) + "일괄 적용" 버튼, 체크된 행이
    1개 이상일 때만 활성화(REQ-RACK-010a).
  - 상단에 Excel 업로드 버튼(파일 선택 + 업로드 트리거, `uploadVendorShipment` 등 기존
    업로드 버튼 UX 패턴 재사용).
- [MODIFY] `frontend/src/router/index.tsx`
  - `/purchase-orders` 라우트(101-107행) 근처에 신규 lazy 라우트 추가:
    ```
    {
      path: '/rack-number',
      lazy: async () => {
        const { RackNumberPage } = await import('@/pages/RackNumberPage')
        return { Component: RackNumberPage }
      },
    },
    ```
- [MODIFY] `frontend/src/components/Sidebar.tsx`
  - `flatNavItems`(37-75행) 배열에 신규 항목 추가(REQ-RACK-008):
    `{ label: '렉번호 관리', href: '/rack-number', icon: MapPin }` — `lucide-react`에서
    `MapPin` import 추가(1-6행 import 블록에 `Package`, `Warehouse` 등과 함께).

### M6 — 프론트엔드: API 서비스 및 TanStack Query 훅 (Priority: Medium)

참조 구현: `frontend/src/services/purchaseOrderApi.ts:138-256`(단건/일괄/업로드 함수 +
타입 정의 스타일), `frontend/src/hooks/usePurchaseOrderQueries.ts:103-237`(대응 mutation
훅 + `onSuccess`/`onError` toast 패턴).

- [NEW] `frontend/src/services/rackNumberApi.ts`
  - 타입: `RackNumberResponse { id: number; rack_number: string; sku: string | null }`,
    `BulkRackNumberResponse { updated_count: number; missing_ids: number[] }`,
    `UploadRackNumberResponse { matched_count: number; skipped_count: number }`.
  - 함수: `updateLineItemRackNumber(id, rackNumber)` → `PATCH
    /api/purchase-orders/line-items/${id}/rack-number/`; `bulkUpdateLineItemRackNumber(ids,
    rackNumber)` → `PATCH /api/purchase-orders/line-items/bulk-rack-number/`;
    `uploadRackNumber(formData)` → `POST /api/purchase-orders/upload-rack-number/`
    (multipart, 기존 `uploadVendorShipment` 243-248행과 동일 헤더 패턴).
  - 주문 검색/조회는 신규 함수를 만들지 않고 기존 `frontend/src/services`의 주문 목록/상세
    함수(주문 검색 `search` 파라미터, 주문 상세 조회)를 그대로 import해 재사용(결정 C) —
    정확한 기존 함수명은 Run 단계 착수 시 `frontend/src/services/` 내 orders 관련 파일을
    재확인.
- [NEW] `frontend/src/hooks/useRackNumberQueries.ts`
  - `useUpdateLineItemRackNumber()` — 단건 PATCH mutation, 성공 시 해당 Order 상세 쿼리
    무효화(현재 페이지가 보고 있는 Order의 재조회 트리거).
  - `useBulkUpdateLineItemRackNumber()` — 일괄 PATCH mutation, `missing_ids` 존재 시
    warning toast(기존 `useBulkUpdateLineItemLogisticsStatus` 190-209행 패턴 재사용).
  - `useUploadRackNumber()` — 업로드 mutation, 성공 시 `matched_count`/`skipped_count`
    toast(기존 `useUploadVendorShipment` 211-223행 패턴 재사용).

## 리스크

- **마이그레이션 번호 충돌**: 계획 시점(`0034`) 이후 다른 SPEC이 병렬로 구현되며 번호를
  선점할 수 있음 — Run 단계 착수 시 최신 마이그레이션 상태 재확인 필수(SPEC-ORDER-011/012
  모두 실제로 겪은 문제).
- **검색 오탐**: `GET /api/orders/?search=`의 검색 로직(`views.py:137-149`)은
  `order_number` 정확 일치와 `name__icontains` 부분 일치를 OR로 묶는다 — 숫자로만 이루어진
  검색어라도 어떤 주문의 `name`에 그 숫자가 부분 문자열로 포함되면 여러 결과가 반환될 수
  있음. 프론트엔드는 반드시 응답 중 `order_number`가 정확히 일치하는 항목만 선택해야
  하며(결정 C), 이 필터링 로직 누락 시 잘못된 주문의 LineItem이 노출되는 회귀가 발생한다 —
  Run 단계에서 반드시 테스트로 검증.
- **중복 (주문번호, SKU) 매칭**: 결정 E에 따라 여러 LineItem이 매칭될 경우 전부 업데이트하는
  기본 동작이 실제 운영 시나리오와 다를 수 있음 — 구현 후 실사용 데이터로 재검증 권장(후속
  SPEC 필요 시 별도 처리).
- **Order 재계산 호출 누락 방지 재검증**: `rack_number` 관련 write path 어디에도
  `_recompute_order_aggregates()`를 호출하지 않는 것이 REQ-RACK-002의 핵심 — 코드 리뷰
  시 실수로 호출이 추가되지 않았는지 반드시 확인(SPEC-ORDER-012 패턴과의 의도된 차이점).

## 참조 구현

- `location` 필드 선례: `backend/order/models.py:171`(`LineItem.location`),
  `backend/order/migrations/0010_lineitem_add_location.py`.
- 단건/일괄 PATCH 선례: `backend/order/purchase_order_views.py:1953-2052`
  (`LineItemLogisticsStatusUpdateView`/`LineItemLogisticsStatusBulkUpdateView`),
  `:1850-1945`(`LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`).
- Excel 업로드 선례: `backend/order/excel_utils.py:727-926`(이름 기반 다중 컬럼 헤더
  탐색), `:944-991`(대소문자 무시 substring 헤더 매칭 + SKU-only 파서),
  `purchase_order_views.py:1710-1838`(`UploadVendorShipmentView`/
  `UploadWarehouseReceiptView`).
- URL 등록 순서 선례: `backend/order/urls.py:64-77`(bulk 경로가 `<int:pk>` 경로보다
  먼저 등록되는 관례).
- 시리얼라이저 확장 선례: `backend/order/serializers.py:100-118`
  (`LineItemDetailSerializer`), `:148-166`(`OrderDetailSerializer`, `ready_to_ship`을
  이미 동일한 방식으로 노출).
- 프론트엔드 체크박스/일괄 적용 UX 선례:
  `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`(전체) — 특히 40-82행
  (로컬/전역 상태 조합), 194-269행(체크박스 컬럼 및 인라인 select 컬럼 마크업).
  본 SPEC은 전역 스토어 부분만 로컬 상태로 대체.
  - 렉번호 텍스트 인라인 편집은 `UnorderedItemsTab.tsx`의 `select` 인라인 편집(254-268행)
    구조를 텍스트 입력으로 치환한 것과 동일한 패턴.
- 라우팅/메뉴 선례: `frontend/src/router/index.tsx:101-107`(`/purchase-orders` lazy
  라우트), `frontend/src/components/Sidebar.tsx:37-75`(`flatNavItems`).
- 서비스/훅 선례: `frontend/src/services/purchaseOrderApi.ts:138-256`,
  `frontend/src/hooks/usePurchaseOrderQueries.ts:103-237`.
- 주문 검색 재사용 대상: `backend/order/views.py:88-151`(`OrderListView.get_queryset`,
  `order_number` 정확 매칭 검색 로직), `:31-45`(`OrderDetailView`).
- 테스트 파일 명명: `test_spec_011.py`/`test_spec_012.py` 선례를 따라
  `backend/order/tests/test_spec_013.py` 신설 권장(단건/일괄/업로드 각각의 정상·예외
  경로, `(order_number, sku)` 중복 매칭·미매칭 케이스 포함).

## MX 태그 계획

Full scan 대상(기존 코드 수정 + 신규 공개 API 다수 포함).

- **@MX:NOTE 대상**:
  - `LineItem.rack_number` 필드 선언(`models.py`, M1) — `location`과의 관계 및 "계산/집계
    없음, 수동·업로드 전용" 불변조건을 설명하는 주석(REQ-RACK-002 근거).
  - `LineItemBulkRackNumberUpdateView`(M2) — `_recompute_order_aggregates()`를 의도적으로
    호출하지 않는다는 사실을 코드 근처에 명시(리스크 절 "Order 재계산 호출 누락 방지
    재검증" 참조 — 실수로 추가되는 것을 막기 위한 의도 설명).
  - `parse_rack_number_excel`(M3) — 컬럼 별칭 목록(`"주문번호"/"order"`,
    `"sku"/"isbn"`, `"렉번호"/"rack"`)이 왜 이 문자열들인지(기존 업로드 파서 관례와의
    일관성) 설명.
- **@MX:WARN 대상**:
  - `UploadRackNumberView`의 `transaction.atomic()` 블록(M3) — 결정 E(중복 매칭 시 전체
    적용)로 인해 한 행이 여러 LineItem에 동시 반영될 수 있음을 경고 주석으로 명시,
    `@MX:REASON`으로 결정 E 요약 링크.
- **@MX:ANCHOR 대상**: 없음 — 이번 SPEC에서 신설되는 함수/뷰는 모두 신규 엔드포인트로
  fan_in(호출자 수) 3 이상에 해당하는 기존 고위험 함수가 아님. 기존 `LineItemDetailSerializer`
  등 확장 지점은 이미 SPEC-ORDER-011/012에서 anchor 처리된 것으로 간주하고 재태깅하지 않음.
  - `Order.objects.filter(order_number=...)` 등은 Django ORM 표준 호출이라 별도 앵커 불필요.
- **@MX:TODO 대상**: Run 단계 RED 단계에서 `backend/order/tests/test_spec_013.py` 및
  프론트엔드 테스트가 작성되기 전까지, 신규 뷰/함수 상단에 임시 `@MX:TODO`(테스트 대기)를
  붙였다가 GREEN 완료 시 제거(workflow-modes.md TDD Mode MX Tags 규칙).
