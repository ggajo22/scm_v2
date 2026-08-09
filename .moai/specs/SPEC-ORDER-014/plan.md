# SPEC-ORDER-014 구현 계획

## 기술 접근

브라운필드 변경. 기존 `order` 앱(`backend/order/`)의 뷰·URL과 기존
`frontend/src/pages/RackNumberPage.tsx`(SPEC-ORDER-013 산출물), `frontend/src/services`,
`frontend/src/hooks` 구조를 확장한다. 신규 모델 필드나 마이그레이션은 없다 — `rack_number`와
`logistics_status`는 이미 SPEC-ORDER-013/011에서 존재하며, 이 SPEC은 순수 읽기 전용 집계
엔드포인트와 프론트엔드 탭 재구성만 추가한다. 개발 방법론은 `quality.yaml`의
`development_mode: tdd`(RED-GREEN-REFACTOR) — 신규 GET 엔드포인트와 신규 탭 컴포넌트가
중심이며, 기존 Tab1 코드는 파일 이동(rename) 수준의 변경만 발생하고 로직 자체는 건드리지
않으므로 회귀 위험이 낮다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 백엔드: 집계 엔드포인트 (Priority: High)

참조 구현: `backend/order/purchase_order_views.py:250-283`(`UnorderedItemsView` — 교차
주문 집계, `select_related("order")`, 페이지네이션 없음, null 수량 처리 관례),
`:2151-2244`(`UploadRackNumberView` — 이 SPEC이 확장하는 SPEC-ORDER-013 rack_number 섹션의
마지막 클래스, 신규 클래스 삽입 위치).

- [MODIFY] `backend/order/purchase_order_views.py`
  - `UploadRackNumberView` 클래스 종료 지점(2244행) 직후, `# M6: Distributor vendor rules`
    섹션 헤더(2247행) 이전에 신규 섹션 헤더 주석과 클래스 1개 추가:
    ```python
    # ---------------------------------------------------------------------------
    # SPEC-ORDER-014: cross-order rack_number summary (read-only aggregate)
    # ---------------------------------------------------------------------------


    class LineItemRackNumberSummaryView(APIView):
        """
        GET /api/purchase-orders/line-items/rack-number-summary/

        REQ-RACKSUM-001~008: cross-order read-only aggregate of every LineItem
        that has not yet shipped (logistics_status != "shipped"), grouped by
        rack_number. LineItems with an empty rack_number are grouped into a
        single unassigned bucket (REQ-RACKSUM-004a) rather than dropped.
        """

        authentication_classes = [JWTAuthentication]
        permission_classes = [IsAuthenticated]

        def get(self, request) -> Response:
            line_items = (
                LineItem.objects.exclude(logistics_status="shipped")
                .select_related("order")
                .order_by("rack_number", "order__order_number")
            )

            groups: dict[str, dict] = {}
            for li in line_items:
                key = li.rack_number  # "" -> unassigned bucket (REQ-RACKSUM-004a)
                group = groups.setdefault(
                    key,
                    {
                        "rack_number": key,
                        "is_unassigned": key == "",
                        "total_quantity": 0,
                        "line_items": [],
                    },
                )
                # REQ-RACKSUM-005: null quantity treated as 0, mirroring
                # UnorderedItemsView's `li.quantity or 0` convention (291행).
                group["total_quantity"] += li.quantity or 0
                group["line_items"].append(
                    {
                        "id": li.id,
                        "order_number": li.order.order_number,
                        "sku": li.sku,
                        "title": li.title,
                        "quantity": li.quantity,
                        "logistics_status": li.logistics_status,
                    }
                )

            # REQ-RACKSUM-004/004a: named groups sorted alphabetically by
            # rack_number, unassigned bucket always last.
            named = sorted(
                (g for k, g in groups.items() if k != ""),
                key=lambda g: g["rack_number"],
            )
            unassigned = [groups[""]] if "" in groups else []

            return Response({"groups": named + unassigned}, status=status.HTTP_200_OK)
    ```
  - **REQ-RACKSUM-008 (페이지네이션 미적용)**: 이 뷰는 `PageNumberPagination`을 사용하지
    않는다 — `UnorderedItemsView`와 동일하게 전체 결과를 단일 payload로 반환한다.
  - **REQ-RACKSUM-002a (필터 우회 파라미터 무시)**: `request.query_params`를 전혀 읽지
    않으므로, 어떤 쿼리 파라미터가 전달되어도 자동으로 무시된다 — 별도 방어 코드 불필요.
  - 별도의 신규 시리얼라이저는 만들지 않는다 — `UnorderedItemsView`(289-307행)와 동일하게
    응답을 plain dict로 직접 구성한다(기존 스타일과 일관).
- [MODIFY] `backend/order/urls.py`
  - import 블록(3-24행)의 알파벳 순서에 맞춰 `LineItemRackNumberSummaryView`를
    `LineItemRackNumberUpdateView` **바로 앞**(현재 13행)에 추가("RackNumberS" <
    "RackNumberU" 알파벳 순).
  - 기존 rack-number 관련 경로 블록(81-96행, SPEC-ORDER-013에서 등록) 바로 뒤,
    `purchase-orders/upload-vendor-shipment/`(97-101행) 이전에 신규 경로 추가:
    ```python
    # SPEC-ORDER-014: cross-order read-only rack_number summary (GET only,
    # no <int:pk> conflict possible — path segment is all letters/hyphens)
    path(
        "purchase-orders/line-items/rack-number-summary/",
        LineItemRackNumberSummaryView.as_view(),
        name="po-line-item-rack-number-summary",
    ),
    ```

### M2 — 백엔드: 테스트 (Priority: High)

참조 구현: `backend/order/tests/test_spec_013.py`(파일 명명 관례, 단건/일괄/업로드 정상·예외
경로 테스트 구조).

- [NEW] `backend/order/tests/test_spec_014.py`
  - T1: 필터 정의 — `not_shipped`/`shipment_confirmed`/`received`/`outbound_scheduled`인
    LineItem은 응답에 포함되고 `shipped`인 LineItem은 제외됨(AC-RACKSUM-001/007).
  - T2: 동일 `rack_number`를 가진 서로 다른 Order 소속 LineItem 2건 이상이 같은 그룹으로
    묶이고 각각 자신의 `order_number`를 유지함(AC-RACKSUM-004/004b).
  - T3: 빈 문자열 `rack_number`를 가진 LineItem들이 별도의 미지정 그룹(`rack_number: ""`,
    `is_unassigned: true`)으로 묶임(AC-RACKSUM-004a).
  - T4: 그룹의 `total_quantity`가 멤버 LineItem `quantity` 합과 일치하고, `quantity=None`인
    LineItem은 0으로 취급됨(AC-RACKSUM-005).
  - T5: 그룹 내 각 LineItem 딕셔너리에 `order_number`/`sku`/`title`/`quantity`/
    `logistics_status`가 모두 존재함(AC-RACKSUM-006).
  - T6: 모든 LineItem이 `shipped`인 Order는 응답의 어떤 그룹에도 등장하지 않음
    (AC-RACKSUM-007). 일부만 shipped인 Order는 not-shipped LineItem만 포함됨
    (AC-RACKSUM-007a).
  - T7: 응답 JSON에 `page`/`next`/`previous` 등 페이지네이션 필드가 없음(AC-RACKSUM-008).
  - T8: 임의의 쿼리 파라미터(예: `?include_shipped=true`)를 붙여 요청해도 필터링 결과가
    동일함(AC-RACKSUM-002a).
  - T9: 미출고 LineItem이 시스템 전체에 0건일 때 `{"groups": []}` 반환(AC-RACKSUM-013의
    백엔드 측 전제 조건).
  - T10: JWT 인증 없이 요청 시 401(기존 뷰들과 동일한 인증 보일러플레이트 검증).

### M3 — 프론트엔드: 탭 구조 재구성 (Priority: High, 회귀 위험 최소화)

참조 구현: `frontend/src/pages/PurchaseOrders/index.tsx`(탭 스위처 패턴, 상태 기반 탭
전환, `role="tablist"`/`role="tabpanel"` 접근성 구조), `frontend/src/pages/RackNumberPage.tsx`
(SPEC-ORDER-013 산출물 전체 — Tab1 콘텐츠로 그대로 이동).

- [NEW] `frontend/src/pages/RackNumberPage/index.tsx`
  - `PurchaseOrdersPage`(`PurchaseOrders/index.tsx` 1-96행)와 동일한 구조로 탭 셸 작성.
  - `TabValue = 'search' | 'summary'`, `TABS = [{value:'search', label:'주문 검색'},
    {value:'summary', label:'렉번호 요약'}]`.
  - `useState<TabValue>('search')`로 기본 활성 탭을 "주문 검색"으로 고정
    (REQ-RACKSUM-009b) — 이는 SPEC-ORDER-013의 기존 15개 프론트엔드 테스트가 별도 탭
    클릭 없이 그대로 통과하기 위한 필수 조건이다.
  - `renderTab()` 스위치: `'search'` → `<SearchTab />`, `'summary'` → `<SummaryTab />`.
  - 라우터의 lazy import 경로(`@/pages/RackNumberPage`)는 `index.tsx`로 자동 해석되므로
    `frontend/src/router/index.tsx`는 **수정 불필요** — 단, Run 단계 착수 시 빌드로 반드시
    재검증할 것(모듈 해석 리스크, 아래 리스크 절 참조).
- [MOVE] `frontend/src/pages/RackNumberPage.tsx` → `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx`
  - 파일 내용은 그대로 이동하되, export하는 컴포넌트명만 `RackNumberPage` →
    `SearchTab`으로 변경(REQ-RACKSUM-009a — 동작 100% 동일, 로직 변경 없음).
  - 내부 `RackNumberRow` 서브컴포넌트, 모든 상태(`searchInput`, `submittedSearch`,
    `selectedIds`, `bulkValue`, `fileInputRef`)와 핸들러는 무변경.
- [NEW] `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx`
  - `useRackNumberSummary()` 훅(M4)으로 데이터 조회 — 탭이 마운트되는 시점에 자동 요청
    (결정 F, REQ-RACKSUM-010). 별도 `enabled` 플래그 불필요(스위치 렌더링으로 이미 탭
    활성화 시에만 마운트됨, `PurchaseOrdersPage`의 `renderTab()` 패턴과 동일).
  - 그룹 목록을 순서대로 렌더링(백엔드가 이미 정렬해서 반환, 결정 D). 각 그룹:
    - 헤더: `rack_number` 값(빈 문자열이면 "미지정" 라벨, `is_unassigned` 플래그로 판정,
      REQ-RACKSUM-011/011a) + `총 {total_quantity}권` 형태의 총 수량 표시.
    - 그룹 내 LineItem 테이블/목록: 주문번호(`order_number`, null이면 "-" 표시) / SKU /
      도서명 / 수량 / 물류상태 라벨(REQ-RACKSUM-012).
  - 물류상태 라벨은 `frontend/src/services/purchaseOrderApi.ts:32-38`의
    `LOGISTICS_STATUS_OPTIONS`를 import해 로컬 `Record<string, string>` 맵으로 변환 —
    `OrderDetailPage.tsx:52-55`의 `LOGISTICS_STATUS_LABELS` 구성 패턴과 동일(해당 파일은
    수정하지 않고 패턴만 재사용).
  - `groups.length === 0`일 때 빈 상태 메시지 렌더링, 빈 테이블 구조를 렌더링하지 않음
    (REQ-RACKSUM-013).
  - 체크박스, 입력창, 버튼 등 편집 관련 엘리먼트를 일체 렌더링하지 않는다(REQ-RACKSUM-014).
  - 로딩 상태: `isPending` 동안 `UnorderedItemsTab`/`PurchaseOrderHistoryTab` 등 기존
    탭들의 `role="status"` 스켈레톤 패턴을 재사용.

### M4 — 프론트엔드: API 서비스 및 TanStack Query 훅 (Priority: Medium)

참조 구현: `frontend/src/services/rackNumberApi.ts`(SPEC-ORDER-013 산출물 — 타입/함수 작성
스타일), `frontend/src/hooks/useRackNumberQueries.ts`(기존 mutation 훅 스타일, 이 SPEC은
읽기 전용 query 훅을 동일 파일에 추가).

- [MODIFY] `frontend/src/services/rackNumberApi.ts`
  - 신규 타입 추가:
    ```typescript
    export interface RackNumberSummaryLineItem {
      id: number
      order_number: number | null
      sku: string | null
      title: string | null
      quantity: number | null
      logistics_status: string
    }

    export interface RackNumberSummaryGroup {
      rack_number: string
      is_unassigned: boolean
      total_quantity: number
      line_items: RackNumberSummaryLineItem[]
    }

    export interface RackNumberSummaryResponse {
      groups: RackNumberSummaryGroup[]
    }
    ```
  - 신규 함수 추가:
    ```typescript
    // REQ-RACKSUM-001~008: cross-order read-only rack_number summary.
    export async function getRackNumberSummary(): Promise<RackNumberSummaryResponse> {
      const res = await api.get('/api/purchase-orders/line-items/rack-number-summary/')
      return res.data
    }
    ```
- [MODIFY] `frontend/src/hooks/useRackNumberQueries.ts`
  - `useQuery`를 새로 import(현재 파일은 `useMutation`/`useQueryClient`만 import).
  - 신규 조회 훅 추가:
    ```typescript
    // REQ-RACKSUM-010: fetched once when the "렉번호 요약" tab mounts.
    export function useRackNumberSummary() {
      return useQuery({
        queryKey: ['rack-number-summary'],
        queryFn: getRackNumberSummary,
      })
    }
    ```
  - 뮤테이션 훅(`useUpdateLineItemRackNumber` 등)은 무변경 — `queryKey: ['rack-number-summary']`
    무효화는 이번 SPEC 범위에서는 하지 않는다(Tab1 편집이 Tab2 요약에 실시간 반영되지 않아도
    되며, 사용자가 Tab2를 재방문하면 자동으로 최신 데이터를 다시 조회하므로 무효화 연결은
    불필요한 복잡도로 판단 — Enforce Simplicity 원칙).

### M5 — 프론트엔드: 테스트 (Priority: Medium)

참조 구현: `frontend/src/pages/RackNumberPage.test.tsx`(SPEC-ORDER-013 산출물, 이동 대상).

- [MOVE] `frontend/src/pages/RackNumberPage.test.tsx` → `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`
  - `import { RackNumberPage } from './RackNumberPage'` → `import { SearchTab } from './SearchTab'`로
    변경, `render(<RackNumberPage />)` 호출부를 `render(<SearchTab />)`로 치환하는 것 외에는
    기존 15개 테스트의 단언(assertion)을 일체 변경하지 않는다(REQ-RACKSUM-009a 회귀 방지의
    핵심 증거).
- [NEW] `frontend/src/pages/RackNumberPage/index.test.tsx`
  - 기본 진입 시 "주문 검색" 탭 콘텐츠가 즉시 보임(탭 클릭 없이, AC-RACKSUM-009b).
  - "렉번호 요약" 탭 클릭 시 해당 탭 패널로 전환됨(AC-RACKSUM-009/010).
  - 두 탭 컨트롤이 정확히 2개만 렌더링됨(AC-RACKSUM-009).
- [NEW] `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx`
  - `useRackNumberSummary`를 목(mock)하여: 그룹 여러 개(멀티 오더 포함) 렌더링 시 각 그룹
    헤더에 `rack_number`/총 수량이 보임(AC-RACKSUM-011/004b).
  - `is_unassigned: true`인 그룹이 "미지정" 라벨로 렌더링됨(AC-RACKSUM-011a).
  - 그룹 내 LineItem 행에 주문번호/SKU/도서명/수량/물류상태 라벨이 보임(AC-RACKSUM-012).
  - `groups: []`일 때 빈 상태 메시지가 보이고 테이블이 렌더링되지 않음(AC-RACKSUM-013).
  - 체크박스(`role="checkbox"`), 텍스트 입력(`role="textbox"`), 적용 버튼이 하나도
    쿼리되지 않음(AC-RACKSUM-014/015).

## 리스크

- **모듈 해석 리스크**: `RackNumberPage.tsx`(파일) → `RackNumberPage/index.tsx`(폴더) 전환
  시 Vite/TypeScript의 `@/pages/RackNumberPage` 별칭 해석이 동일하게 동작하는지 Run 단계
  착수 직후 최우선으로 빌드 검증 필요 — `PurchaseOrders.tsx`가 이미 동일한 폴더+index.tsx
  구조로 존재하므로(`frontend/src/pages/PurchaseOrders/index.tsx`) 선례상 문제는 없을
  것으로 예상되나, 라우터 lazy import(`router/index.tsx`)가 실제로 깨지지 않는지 반드시
  `npm run build`로 재검증할 것.
- **기존 15개 SPEC-ORDER-013 테스트 회귀**: `SearchTab.tsx`/`SearchTab.test.tsx`로의 이동은
  파일 경로와 export 이름만 바꾸는 것이어야 하며, 로직/마크업/테스트 단언을 일체 수정하지
  않아야 한다 — 코드 리뷰 시 diff가 "이동 + 이름 변경"만으로 구성되어 있는지 확인
  (REQ-RACKSUM-009a 준수 검증).
- **무제한 응답 크기**: 결정 B에 따라 페이지네이션을 적용하지 않으므로, 미출고 LineItem
  수가 실제 운영에서 예상보다 커질 경우 응답 지연이 발생할 수 있음 — 발생 시 후속 SPEC에서
  페이지네이션 또는 커서 기반 조회 도입을 재검토.
- **`order_number`가 null인 LineItem**: `Order.order_number`는
  `models.IntegerField(null=True, blank=True)`로 선언되어 있어(models.py:36) 이론상 null일
  수 있다 — 프론트엔드는 `item.order_number ?? '-'`로 방어적으로 렌더링해야 하며, 백엔드는
  null 값을 그대로 전달한다(임의로 0이나 빈 문자열로 치환하지 않음, 데이터 정확성 우선).

## 참조 구현

- 교차 주문 집계 + 페이지네이션 미적용 선례: `backend/order/purchase_order_views.py:250-283`
  (`UnorderedItemsView`).
- null 수량 0 처리 관례: `backend/order/purchase_order_views.py:291`
  (`net_qty = max((li.quantity or 0) - li.refunded_qty, 0)`).
- rack_number PATCH 뷰 3종 선례(삽입 위치 기준점): `backend/order/purchase_order_views.py:2071-2244`
  (`LineItemRackNumberUpdateView`/`LineItemBulkRackNumberUpdateView`/`UploadRackNumberView`).
- URL 등록 선례: `backend/order/urls.py:81-96`(SPEC-ORDER-013 rack-number 경로 블록).
- 탭 스위처 패턴 선례: `frontend/src/pages/PurchaseOrders/index.tsx:1-96`(`PurchaseOrdersPage`).
- 물류상태 라벨 맵 구성 패턴: `frontend/src/pages/OrderDetailPage.tsx:49-55`
  (`LOGISTICS_STATUS_LABELS`), `frontend/src/services/purchaseOrderApi.ts:32-38`
  (`LOGISTICS_STATUS_OPTIONS`).
- Tab1 원본(이동 대상): `frontend/src/pages/RackNumberPage.tsx`(전체, SPEC-ORDER-013),
  `frontend/src/pages/RackNumberPage.test.tsx`(전체, 이동 대상).
- 서비스/훅 원본(확장 대상): `frontend/src/services/rackNumberApi.ts`(전체),
  `frontend/src/hooks/useRackNumberQueries.ts`(전체).
- 테스트 파일 명명 관례: `test_spec_013.py` 선례를 따라 `backend/order/tests/test_spec_014.py`
  신설.

## MX 태그 계획

- **@MX:NOTE 대상**:
  - `LineItemRackNumberSummaryView`(M1) — 페이지네이션 미적용 이유(결정 B, `UnorderedItemsView`
    선례 참조)와 미지정 버킷을 드롭하지 않는 이유(결정 A)를 설명하는 주석.
  - `frontend/src/pages/RackNumberPage/index.tsx`(M3) — 기본 활성 탭이 반드시 "search"여야
    하는 이유(SPEC-ORDER-013 기존 테스트 회귀 방지)를 설명하는 주석.
- **@MX:WARN 대상**:
  - `LineItemRackNumberSummaryView`(M1) — 페이지네이션 없이 전체 미출고 LineItem을 단일
    응답으로 반환하므로, 데이터 규모가 커지면 응답 지연이 발생할 수 있음을 경고 주석으로
    명시, `@MX:REASON`으로 결정 B 요약 링크.
- **@MX:ANCHOR 대상**: 없음 — 이번 SPEC에서 신설되는 뷰/컴포넌트는 모두 신규 엔드포인트/
  신규 탭으로 fan_in(호출자 수) 3 이상에 해당하는 기존 고위험 함수가 아니다.
- **@MX:TODO 대상**: Run 단계 RED 단계에서 `backend/order/tests/test_spec_014.py` 및
  `SummaryTab.test.tsx`/`index.test.tsx`가 작성되기 전까지, 신규 뷰/컴포넌트 상단에 임시
  `@MX:TODO`(테스트 대기)를 붙였다가 GREEN 완료 시 제거.
