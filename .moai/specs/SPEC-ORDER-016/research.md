# SPEC-ORDER-016 리서치 — /outbound 매칭 실패 강제 출고 처리

조사일: 2026-08-12
조사 범위: `backend/order/**`, `frontend/src/**`
목적: SPEC-ORDER-015가 구현한 출고 처리 위에 "SKU 불일치 행 강제 출고" 기능을 얹을 때
영향받는 코드·계약·테스트 불변식을 확정한다.
확정 스코프는 `interview.md` 참조.

---

## 1. 주문 LineItem 목록 조달 경로

**결론: 주문 하나의 LineItem 목록을 주는 엔드포인트는 있으나 (a) `Order.name`이 아닌 `pk` 키이고, (b) 배치(다수 주문)를 받는 엔드포인트는 존재하지 않는다.**

### 1-1. 유일한 "한 주문의 LineItem 전체" 경로

- `backend/order/urls.py:60` — `path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail")`
- `backend/order/views.py:31-45` — `OrderDetailView(RetrieveAPIView)`, `select_related("customer","shipping_address")` + `prefetch_related("line_items__notes__author","shipping_lines","refunds")`
- 직렬화: `backend/order/serializers.py:141-171` `OrderDetailSerializer` → `line_items = LineItemDetailSerializer(many=True)` (`serializers.py:146`)

`LineItemDetailSerializer` 필드 (`backend/order/serializers.py:110-123`):

```
id, shopify_line_item_id, title, variant_title, sku,
quantity, price, total_discount, fulfillment_status, vendor, grams,
location, rack_number, notes,
confirmed_price, confirmed_distributor, confirmed_at,
logistics_status, shipped_quantity, shipped_at
```

피커 UI가 요구하는 title / sku / quantity / shipped_quantity는 전부 이미 노출되어 있다.
단 **`purchase_status`는 이 serializer에 없다** (`serializers.py:110-123`) — 6절의 제외 조건을
프론트에서 판정하려면 이 부재가 결정적이다.

프론트 타입: `frontend/src/types/order.ts:112-136` `LineItemDetail` (동일하게 `purchase_status` 없음).

### 1-2. name → id 해석 경로 (기존 선례)

`frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx:37-50`이 유일한 선례:

1. `useOrders({ search })` → `GET /api/orders/?search=` (`features/order/hooks/useOrders.ts:9-28`)
2. 클라이언트에서 `order_number` 일치 또는 `normalizeOrderSearch(name)` 일치로 필터 (`SearchTab.tsx:42-46`)
3. 매칭된 `id`로 `useOrderDetail(matchedOrder.id)` (`SearchTab.tsx:48-50`)

즉 **주문 1건당 최소 2회 HTTP 요청**. `unmatched` 행이 N개면 2N 요청 —
원격 MySQL ~130ms 왕복이라는 알려진 제약(`purchase_order_views.py:2790-2801` @MX:NOTE)에 정면 위배.

백엔드 검색도 `Order.name`을 `icontains`로만 처리하며(`views.py:140`) `name__in` 배치 조회를 노출하지 않는다.

### 1-3. 배치(order name 리스트) 조회 엔드포인트 — 없음

`name__in` 사용처는 전부 내부 함수이며 HTTP로 노출되지 않는다:

- `purchase_order_views.py:234` (`_apply_logistics_transition`)
- `purchase_order_views.py:1498` (Daily Review)
- `purchase_order_views.py:2036` (`_process_warehouse_receipt_rows`)
- `purchase_order_views.py:2922` (`_process_outbound_rows`)

성능 전제는 이미 충족: `Order.name`에 인덱스 존재 — `backend/order/models.py:100-110`
(`models.Index(fields=["name"])`, 코멘트에 "SPEC-ORDER-015 as a single batched `name__in` fetch" 명시).

### 1-4. 재사용 가능한 크로스-오더 LineItem 엔드포인트 후보 (모두 부적합)

| 엔드포인트 | 위치 | 부적합 사유 |
|---|---|---|
| `GET /api/purchase-orders/unordered/` | `purchase_order_views.py:284-347` | `_reorder_candidate_filter`로 `purchase_status in (unordered, damaged_exchange)`만 반환 (`:107-110`, `:308`). 대부분의 강제 대상이 걸러짐 |
| `GET /api/purchase-orders/line-items/rack-number-summary/` | `purchase_order_views.py:2671-2728`, `urls.py:102-106` | 시스템 전체 미출고 LineItem을 rack_number로 그룹핑해 무페이지네이션 반환(@MX:WARN `:2665-2670`). `shipped`/`order_cancelled` 제외 → 후보 집합 불일치. 응답에 `shipped_quantity` 없음 (`:2709-2718`) |

**정리:** 피커용으로는 (a) `unmatched` 응답에 후보 동봉, 또는 (b) `{"names": [...]}` /
`{"order_ids": [...]}`를 받는 신규 배치 조회가 필요하다.
`LineItemRackNumberSummaryView`(`:2671`)가 "신규 크로스-오더 읽기 전용 뷰"의 가장 가까운 선례이고,
`_process_outbound_rows`의 `name__in` + 파이썬 그룹핑(`:2919-2945`)이 배치 조회 구현 선례다.

---

## 2. 선택 후 일괄 적용 선례 (백엔드 계약 + 프론트 상태 패턴)

### 2-1. 백엔드 bulk 계약 — 3개 뷰가 동일 형태를 공유

| 뷰 | 라인 | URL |
|---|---|---|
| `LineItemBulkStatusUpdateView` | `purchase_order_views.py:2295-2345` | `urls.py:71` |
| `LineItemLogisticsStatusBulkUpdateView` | `purchase_order_views.py:2397-2452` | `urls.py:74-78` |
| `LineItemBulkRackNumberUpdateView` | `purchase_order_views.py:2511-2548` | `urls.py:85-89` |

공통 계약:

- 메서드: `PATCH`
- 요청: `{"ids": [int, ...], "<field>": <value>}` (`:2310-2311`, `:2411-2412`, `:2523-2524`)
- 빈 ids: `400 {"error": "ids must not be empty"}` (`:2316-2319`, `:2416-2420`, `:2526-2530`)
- 잘못된 값: `400 {"error": "Invalid <field>: ... Valid choices: [...]"}` (`:2421-2431`)
- 응답 200: `{"updated_count": int, "missing_ids": [int]}` (`:2339-2345`, `:2446-2452`, `:2541-2545`)
- `missing_ids` 산출: `existing = LineItem.objects.filter(pk__in=ids)` → set 차집합 (`:2326-2328`, `:2433-2435`)
- 집계 재계산: `.update()` **이전에** `affected_order_ids` 캡처 후 `_recompute_order_aggregates()` 호출 (`:2330-2337`, `:2437-2444`)
- URL 순서 규칙: `bulk-*` 경로는 반드시 `<int:pk>/` 보다 먼저 등록 (`urls.py:70`, `:73`, `:84` 코멘트)

프론트 서비스 계약 (`frontend/src/services/rackNumberApi.ts:13-16, 34-44`):

```ts
export interface BulkRackNumberResponse { updated_count: number; missing_ids: number[] }
bulkUpdateLineItemRackNumber(ids, rackNumber) → api.patch('/api/.../bulk-rack-number/', { ids, rack_number })
```

### 2-2. 3분류 응답 계약 — 2곳

- `_process_outbound_rows` 반환 `purchase_order_views.py:3094-3101`
- `_process_warehouse_receipt_rows` 반환 `purchase_order_views.py:2137-2145` (+ `affected_order_ids`)
- `UploadWarehouseReceiptView` 응답 `purchase_order_views.py:2227-2238` — 기존
  `matched_count/skipped_count`를 유지한 채 상세 리스트를 추가한 선례. 코멘트 `:2220-2226`이
  "OutboundProcessView가 반환하는 것과 같은 3분류 payload라 프론트가 결과 테이블 렌더링을
  재사용할 수 있다"고 명시 → **응답 계약 확장 시 하위 호환 유지 방식의 직접 선례**

### 2-3. 프론트 선택 상태 패턴

**패턴 A — 로컬 `useState<number[]>` (권장, /outbound와 성격 동일)**
`frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx`:

- `const [selectedIds, setSelectedIds] = useState<number[]>([])` (`:28`) — 코멘트 `:20-21`에
  "selection state is local (결정 F), never the global usePurchaseOrderStore" 명시
- `allSelected = lineItems.length > 0 && lineItems.every(li => selectedIds.includes(li.id))` (`:57`)
- `toggleSelect` (`:68-70`), `handleSelectAll` (`:72-74`)
- 일괄 적용: `if (selectedIds.length === 0) return; bulkMutation.mutate({ ids, value }, { onSuccess: () => { setSelectedIds([]); setBulkValue('') } })` (`:76-87`)
- 컨트롤 노출 조건: `{selectedIds.length > 0 && (...)}` (`:155`)
- 헤더 전체선택 체크박스 `aria-label="전체 선택"` (`:177-183`), 행별 `aria-label={`${item.sku ?? item.title} 선택`}` (`:243-249`)
- 새 검색 시 선택 리셋 (`:64`, AC-RACK-010c)

**패턴 B — 전역 zustand store** `PurchaseOrders/tabs/UnorderedItemsTab.tsx:45, 49-62, 68-82`
(`selectedSkus/toggleSku/selectAllSkus/clearSelections`). 탭 간 선택 유지가 필요한 경우에만 사용.
`/outbound`는 단일 화면이므로 패턴 A가 관례에 맞다.

**확인 다이얼로그 선례**: 코드베이스 전체에서 `window.confirm` 사용은 1곳뿐 —
`PurchaseOrders/tabs/VendorRulesTab.tsx:40` (규칙 삭제). shadcn `AlertDialog` 사용처 없음.

---

## 3. useOutboundQueries 규약

`frontend/src/hooks/useOutboundQueries.ts` (전체 47줄):

1. **공유 팩토리**: `useOutboundMutation<TVars>(mutationFn, errorMessage)` (`:20-35`) — 두 훅이 이 하나를 감싼다.
2. **무효화 키**: `queryClient.invalidateQueries({ queryKey: ORDER_DETAIL_QUERY_KEY })` (`:28`).
   `ORDER_DETAIL_QUERY_KEY = ['order-detail']`는 `features/order/hooks/useOrderDetail.ts:5`에 정의,
   개별 키는 `[...ORDER_DETAIL_QUERY_KEY, id]` (`useOrderDetail.ts:13`) → prefix 무효화.
   `void` 접두사로 floating promise 회피 (`:28`).
3. **성공 토스트**: `toast.success(buildOutboundSummary(result))`. `buildOutboundSummary`는 export된
   순수 함수 (`:14-16`), 형식: `출고 처리 완료: 성공 N건, 매칭 실패 N건, 수량초과 N건`.
4. **에러 처리**: `onError: () => toast.error(errorMessage)` — 서버 `detail`을 읽지 않고 고정
   한국어 문구만 사용 (`:31-33`). `'출고 처리에 실패했습니다.'` (`:39`),
   `'출고 파일 업로드에 실패했습니다.'` (`:45`).
5. **네이밍**: `use<Verb><Noun>` — `useProcessOutboundManual` (`:38`), `useUploadOutbound` (`:44`).
   각 훅 위에 `// REQ-OUTBOUND-XXX:` 주석.
6. **useQuery 관례** (`useRackNumberQueries.ts:76-81`):
   `useQuery({ queryKey: ['rack-number-summary'], queryFn: getRackNumberSummary })` — 문자열 리터럴
   배열 키, 상수 export 없음. 파라미터가 있으면 `[...KEY, params]` (`useOrders.ts:11`).
7. **부분 실패 토스트 선례**: `useRackNumberQueries.ts:38-45` — `missing_ids.length > 0`이면
   `toast.warning`, 아니면 `toast.success`.
8. **페이지 측 결과 수신**: `mutate(vars, { onSuccess: setResult })` — 훅이 아닌 호출부에서 결과
   state 보관 (`OutboundPage/index.tsx:42`, `:51-57`).

---

## 4. 기존 테스트가 고정한 불변식 / 깨질 위험이 있는 테스트

### 4-1. 백엔드 `backend/order/tests/test_spec_015.py` (1638줄, T1~T8)

**T8 쿼리 카운트 (`:1092-1157`) — 가장 타이트한 제약**

- `_count_queries()`는 `CaptureQueriesContext`로 `_process_outbound_rows` 호출 전체를 감쌈 (`:1118-1121`)
- `test_query_count_is_identical_for_2_and_for_10_groups` (`:1133-1141`): 2그룹 == 10그룹.
  절대값이 아닌 동일성이므로 "그룹 수에 비례하지 않는 쿼리"는 추가해도 통과
- `test_query_count_stays_within_a_small_fixed_bound` (`:1143-1147`): 10그룹 전부 매칭 시 **`<= 6`**.
  현재 = savepoint + Order fetch + LineItem fetch + bulk_update + release ≈ 5. **여유 1쿼리**
- `test_a_batch_that_writes_nothing_issues_no_write_query` (`:1149-1153`): 전부 order_not_found일 때
  **`<= 4`**. 현재 ≈3. **여유 1쿼리**
- `test_an_empty_batch_touches_the_database_at_most_for_the_transaction` (`:1155-1157`): 빈 배치 `<= 2`

→ `_process_outbound_rows` 안에서 후보 LineItem을 함께 조회하면 정확히 +1 쿼리를 소모해
경계에 딱 닿는다. **별도 배치 엔드포인트로 분리하면 T8을 건드리지 않는다.**

**음수 total 불변식 (`:932-1021`, `TestOutboundRejectsNonPositiveTotals`)**

- `test_negative_total_cannot_decrement_shipped_quantity` (`:934-944`)
- `test_non_positive_totals_are_all_rejected` — `[0, -1, -5, -100]` 파라미터화 (`:946-958`)
- `test_rejected_row_leaves_timestamp_and_status_untouched` (`:960-974`)
- `test_negative_row_cannot_offset_a_positive_row_for_the_same_key` (`:976-992`) — 합산 이전 per-row 거부
- 엔드포인트 레벨: `:994-1007` (manual), `:1009-1021` (excel)
- 파생 불변식 `TestZeroTotalRequiresAGenuineParsedZero` (`:1524-1637`): `_parse_total`의 `parsed_ok`가
  없으면 blank 셀이 미국창고 완료 신호로 오인됨

→ **강제 경로도 `total < 0` 및 `total_ok == False`를 동일하게 거부해야 하며 `shipped_quantity`는 감소 불가.**

**응답 계약 테스트**

- `test_response_exposes_three_categories_each_with_count_and_items` (`:692-714`): 각 카테고리
  `len == *_count`. 필드 추가로는 안 깨짐
- `test_both_endpoints_return_identical_results_for_equivalent_input` (`:716-747`):
  `assert manual.data[category] == excel.data[category]` — **딕셔너리 전체 동등성** (`:746`).
  새 필드가 비결정적(타임스탬프, DB 순서 의존 id 리스트)이면 깨진다. 결정적 값이면 통과
- `unmatched` 관련 assert는 전부 `["reason"]`/`["name"]`/`["sku"]` 개별 키 접근
  (`:263-265, 278-279, 815, 824, 920, 944, 992, 1226, 1361, 1413, 1425, 1449, 1470, 1555, 1567, 1607, 1624`)
  또는 `== []` (`:218, 1199, 1321, 1499, 1586`). **필드 추가로 깨지는 백엔드 테스트는 없다.**

**기타 고정된 불변식**

- `test_order_number_is_never_referenced_in_the_matching_source` (`:241`) — `inspect`로 소스 문자열 검사
- `test_result_lists_keep_their_original_first_seen_row_ordering` (`:1228-1245`)
- `test_a_sku_belonging_to_another_order_is_not_borrowed_across_groups` (`:1201-1226`)
- `test_below_threshold_match_does_not_advance_logistics_status_via_batch_write` (`:1247-1277`)
- `test_processing_is_atomic_so_a_mid_run_failure_rolls_everything_back` (`:452`)
- `test_any_logistics_status_is_eligible_for_outbound` (`:307`) — 출고에 상태 게이트 없음
- 인증: `:652-654` (manual), `:1057` (upload) — `status_code in (401, 403)`

### 4-2. 프론트엔드 — 깨질 위험 있는 테스트 2건

**(1) `frontend/src/pages/OutboundPage/index.test.tsx:218-223`**

```ts
it('renders no raw snake_case reason code anywhere in the unmatched section', () => {
  const section = screen.getByTestId('outbound-unmatched')
  expect(section.textContent).not.toMatch(/[a-z]+_[a-z_]+/)
})
```

매칭 실패 섹션의 textContent 전체에 snake_case가 없어야 한다. 새 컬럼에 `logistics_status`
("not_shipped"), `purchase_status`("order_cancelled"), 또는 언더스코어 포함 SKU/타이틀을 그대로
렌더하면 즉시 실패. (체크박스 `aria-label`은 textContent에 미포함이라 안전.)
→ `OrderDetailPage.tsx:52` / `RackNumberPage/tabs/SummaryTab.tsx:12`의 `LOGISTICS_STATUS_LABELS`
방식으로 한국어 라벨링 필요. [v1.0.5 정정: 이전 판은 `InboundPage/index.tsx:30-32`를 인용했으나
그 파일은 저장소에 존재하지 않는다.]

**(2) TS 컴파일 실패 위험 (테스트 fixture)**

`OutboundUnmatchedItem`에 **필수 필드**를 추가하면 아래 객체 리터럴이 `tsc`에서 실패:

- `frontend/src/pages/OutboundPage/index.test.tsx:31-38` (unmatched 5건 리터럴)
- `frontend/src/services/outboundApi.test.ts:33-36` (unmatched 1건 리터럴)

→ **optional(`?`)로 추가하면 무해.**

**깨지지 않는 것들**

- `index.test.tsx:12-18` 및 `OutboundPage/index.tsx:12-18`의 `Record<OutboundUnmatchedReason, string>` —
  reason union이 늘면 컴파일 에러로 강제 (`Partial` 아님, 의도된 설계). 본 SPEC은 reason 추가 계획 없음
- `outboundApi.test.ts:57-77` — `ALL_UNMATCHED_REASONS`가 정확히 5개임을 assert (`:67`)
- `useOutboundQueries.test.tsx:22-34` `buildResponse`는 빈 배열이라 필드 추가에 무영향
- `useOutboundQueries.test.tsx:99-120` — HTTP 400이 실패 토스트로 표면화, 메시지에 `'출고 처리'` 포함
- `useOutboundQueries.test.tsx:122-132` — 400 시 `data === undefined`
- `parseManualRows.ts:11-30` / `.test.ts` — 순수 함수, 무영향

### 4-3. 테스트 파일 명명/구조 관례

**백엔드**: `backend/order/tests/test_spec_0NN.py`. SPEC-ORDER-016 → `test_spec_016.py`.

- 모듈 docstring에 `"""SPEC-ORDER-0NN: <제목> (TDD)."""` + `Coverage targets:` T1~Tn과 각 T의
  `REQ-XXX / AC-XXX` 매핑 (`test_spec_015.py:1-24`, `test_spec_014.py:1-8`)
- 모듈 상단 팩토리 헬퍼 `_make_order()` / `_make_line_item()` (`test_spec_015.py:46-57`)
- 섹션 구분: `# ---` 배너 + `# T6 — endpoints (REQ-..., AC-...)` (`:597-599`)
- URL 상수를 모듈 레벨에 (`:601-602`)
- fixture: `user` / `auth_client`(SimpleJWT `RefreshToken.for_user`) / `anon_client` (`:611-626`),
  username은 `spec015_user` 식 SPEC별 접두
- 클래스: `@pytest.mark.django_db` + `class TestXxx:` + docstring에 AC 참조
- 테스트명은 서술형 문장
- "호출하지 않음"을 pin하는 선례: `patch("order.purchase_order_views._recompute_order_aggregates")` +
  `spy.assert_not_called()` (`test_spec_013.py:383-399`, `:842-851`)

**프론트엔드**: 소스와 동일 디렉터리 colocate.

- `describe('<모듈명> — SPEC-ORDER-0NN', ...)` 최상위, 내부에 `describe('AC-XXX-NNN: <한국어 시나리오>', ...)`
  (`index.test.tsx:76, 81, 154, 268, 317`)
- 훅은 `vi.mock('@/hooks/...')`, 서비스는 `vi.mock('@/lib/axios')`, 토스트는 `vi.mock('sonner')`
- `buildResponse(overrides: Partial<T> = {}): T` 팩토리 관례 (`index.test.tsx:15-54`)
- 훅 테스트는 `renderHook` + 로컬 `QueryClientProvider` wrapper, `retry: false`
  (`useOutboundQueries.test.tsx:36-41`)

---

## 5. `_recompute_order_aggregates` 연동 여부

### 5-1. 함수 사양 (`backend/order/purchase_order_views.py:123-195`)

- 대상 집합: `LineItem.objects.filter(order_id__in=..., sku__isnull=False)` — **"trackable" = sku가 NULL이 아닌 LineItem** (`:155-157`)
- `Order.status`: trackable LineItem의 `logistics_status`가 균일하면 그 값, 2종 이상이면 `"partial"`,
  trackable이 없으면 `None` (`:167-173`)
- `Order.ready_to_ship`: `purchase_status="order_cancelled"` 제외 후, 남은 게 없으면 `None`,
  하나라도 `cs_required`면 `False`, 아니면 모두 `logistics_status=="received" or purchase_status=="in_stock"`일 때 `True` (`:175-186`)
- 쿼리 수: 정확히 2 (SELECT + Case/When UPDATE), `order_ids`가 비면 0 (`:138-152`, `:188-195`)
- 팬인 8 (`:113-122` @MX:NOTE)

### 5-2. 호출하는 곳 / 안 하는 곳

**호출함** (모두 `logistics_status` 또는 `purchase_status`를 쓴 뒤):
`:1047`, `:1778`, `:1943`(`UploadVendorShipmentView`), `:2212`(`UploadWarehouseReceiptView`),
`:2279`(`LineItemStatusUpdateView`), `:2337`(`LineItemBulkStatusUpdateView`),
`:2386`(`LineItemLogisticsStatusUpdateView`), `:2444`(`LineItemLogisticsStatusBulkUpdateView`)

**의도적으로 호출 안 함** (rack_number는 Order 집계가 없음 — @MX:NOTE + 테스트로 pin):
`LineItemRackNumberUpdateView` `:2470-2479`, `LineItemBulkRackNumberUpdateView` `:2507-2510`
("Do not add that call here"), 테스트 `test_spec_013.py:383-399`, `:842-851`

### 5-3. `_process_outbound_rows`는 호출하지 않는다 — 선행 불일치 확정

- `_process_outbound_rows` 본문 전체(`:2810-3101`)에 `_recompute_order_aggregates` 호출 없음
- `OutboundProcessView.post` `:3117-3148`, `UploadOutboundView.post` `:3166-3191` 모두
  결과를 바로 `Response`로 반환
- 그런데 이 함수는 `logistics_status = "shipped"`를 실제로 쓴다: `:3022-3023`(0-total 미국창고 완료),
  `:3067-3068`(임계 도달), `:3089-3091` `bulk_update([..., "logistics_status"])`

**대조 증거 — 거의 동일한 자매 함수는 호출한다:**
`_process_warehouse_receipt_rows`는 `affected_order_ids`를 수집(`:1997`, `:2119`)해 반환(`:2144`)하고
docstring `:1987-1992`가 "for the caller to pass to `_recompute_order_aggregates()`"라고 명시.
호출부 `UploadWarehouseReceiptView` `:2209-2212`가 같은 `transaction.atomic()` 안에서 호출.

**결론:** LineItem의 `logistics_status`를 `"shipped"`로 바꿔도 `Order.status` / `Order.ready_to_ship`이
갱신되지 않는 선행 불일치가 존재한다. `test_spec_015.py`에는 `recompute` / `ready_to_ship` /
`order.status`를 언급하는 테스트가 하나도 없어 현재 동작이 어느 방향으로도 pin되어 있지 않다.
SPEC-ORDER-016은 "기존 동작 답습" 또는 "함께 수정" 중 하나를 **명시적으로 결정**해야 하며,
어느 쪽이든 기존 테스트를 깨지 않는다. 수정 시 `affected_order_ids` 수집(파이썬 패스, 0 쿼리) +
2쿼리 추가이므로 T8의 `<=6`/`<=4` 경계를 넘는다(각각 7, 5) → T8 상수 조정이 동반된다.

---

## 6. 강제 대상에서 제외해야 할 LineItem 조건

### 6-1. 모델 필드 전량 (`backend/order/models.py:152-235`)

| 필드 | 라인 | 비고 |
|---|---|---|
| `order` (FK) | `:169` | `related_name="line_items"` |
| `shopify_line_item_id` | `:170` | |
| `title` | `:173` | nullable |
| `variant_title` | `:174` | nullable |
| `sku` | `:175` | **nullable** |
| `quantity` | `:176` | **nullable** — NULL == 용량 0 (설계 결정 B) |
| `price`, `total_discount` | `:177-178` | |
| `fulfillment_status` | `:179` | Shopify 동기화값, 출고와 무관 |
| `vendor`, `grams`, `location` | `:180-182` | |
| `rack_number` | `:189` | `CharField(max_length=10, default="")` |
| `purchase_status` | `:190-194` | 7종 choices `:156-167` |
| `confirmed_price/distributor/at` | `:195-197` | `confirmed_distributor`가 `_US_WAREHOUSE_DISTRIBUTORS` 판정에 사용 (`:3000`) |
| `logistics_status` | `:204-208` | default `"not_shipped"` |
| `shipped_quantity` | `:221` | `IntegerField(default=0)` |
| `shipped_at` | `:222` | nullable |
| `received_quantity` / `received_at` | `:228-229` | 입고측 대응 필드 |
| Meta `unique_together` | `:235` | `(order, shopify_line_item_id, sku)` — **한 주문에 동일 SKU 복수 행 가능** |

**별도의 `excluded` / `cancelled` boolean 필드는 없다.** "취소"는 `purchase_status="order_cancelled"`
(`:159`), "발주제외"는 `LineItemNote.note_type` 값일 뿐 LineItem 플래그가 아니다 (`:256`).

### 6-2. 다른 뷰들이 적용하는 필터

| 필터 | 적용 위치 | 의미 |
|---|---|---|
| `sku__isnull=False` | `_recompute_order_aggregates` `:155-157` (docstring `:126` "trackable"), `UnorderedItemsView` `:308` | trackable 정의. sku NULL 행은 집계에서 제외 |
| `.exclude(purchase_status="order_cancelled")` | `LineItemRackNumberSummaryView` `:2689`, `_recompute_order_aggregates` `:176` | 취소 품목은 물류 대상 아님 |
| `.exclude(logistics_status="shipped")` | `LineItemRackNumberSummaryView` `:2688` | 이미 출고 완료 |
| eligibility Q (`logistics_status IN (...)`) | `_apply_logistics_transition` `:243-247`, `_process_warehouse_receipt_rows` `:1980-1985` | 입고 경로는 상태 게이트 있음 |
| **필터 없음 (의도적)** | `_process_outbound_rows` `:2934-2935` — "REQ-OUTBOUND-006: no logistics_status filter here on purpose" | **출고는 상태 게이트가 없음** |
| 환불 차감 | `UnorderedItemsView` `:296-305, 325-327` | 출고 경로에는 환불 반영 없음 (선행 격차) |

### 6-3. 강제 대상 후보 제외 판단이 필요한 항목

1. **`sku is NULL`** — 강력한 제외 근거: `_recompute_order_aggregates`가 이런 행을 집계에서
   배제하므로(`:155-157`) 여기에 `logistics_status="shipped"`를 쓰면 Order 집계에 절대 반영되지
   않는 "유령 출고"가 된다. 동시에 정상 경로에서는 SKU 매칭 자체가 불가능한 행이라
   강제 처리만이 도달할 수 있는 유일한 경로이기도 하다.
2. **`purchase_status="order_cancelled"`** — `:2689`와 `:176`이 일관되게 제외. 취소 품목에
   출고 수량 기록은 모순.
3. **`quantity is NULL`** — 제외할 필요는 없으나 용량이 0으로 취급되어(`:2984-2985`) 모든 양수 요청이
   `quantity_exceeded`가 된다. 피커에 표시해 사용자가 헛수고하지 않게 해야 한다.
4. **`shipped_quantity >= quantity`** (이미 출고 완료) — 하드 제외 대신 표시가 적절. 정상 경로도
   이를 막지 않고 `quantity_exceeded`로 보고한다 (`:3039-3051`).
5. **`purchase_status="in_stock"` / `"cs_required"`** — 제외 선례 없음. `ready_to_ship` 계산에만 쓰임 (`:179-185`).
6. **`purchase_status`는 `LineItemDetailSerializer`에 없음** (`serializers.py:110-123`) →
   2·6번 조건을 프론트 피커에서 판정하려면 필드 추가 또는 백엔드 필터링이 필요하다.

---

## 7. 라우팅 / 사이드바 현황

**라우터** `frontend/src/router/index.tsx:129-135`

```
{ path: '/outbound', lazy: async () => { const { OutboundPage } = await import('@/pages/OutboundPage'); return { Component: OutboundPage } } }
```

- `ProtectedRoute`(`:19`) → `AppLayout`(`:22`) 하위. 역할 제한 없음 (`SuperAdminRoute`는 `/admin-users`에만, `:144-153`)
- 지연 로딩이 named export 구조분해에 의존 → `@MX:ANCHOR` (`OutboundPage/index.tsx:24-28`):
  export 이름과 folder+index.tsx 모듈 해석을 `router/index.tsx` 수정 없이 바꾸지 말 것.
  **컴포넌트 분할 시 `export function OutboundPage` 유지 필수.**

**사이드바** `frontend/src/components/Sidebar.tsx:76-82` —
`{ label: '출고 처리', href: '/outbound', icon: Truck }`, `/inbound`(`:70-75`) 바로 다음.
테스트 pin `Sidebar.test.tsx:173-194`.

→ 본 SPEC은 라우팅/사이드바 변경 불필요.

---

## 8. 인증·권한 관례

**모든 order 앱 엔드포인트가 동일**: `authentication_classes = [JWTAuthentication]`,
`permission_classes = [IsAuthenticated]`

- 출고: `OutboundProcessView` `:3112-3113`, `UploadOutboundView` `:3163-3164`
- bulk 계열: `:2306-2307`, `:2407-2408`, `:2519-2520`
- 읽기 계열: `views.py:34-35`, `:89-90`, `purchase_order_views.py:2683-2684`
- `backend/order/**` 전체가 예외 없이 `IsAuthenticated`

**"위험/오버라이드" 액션에 대한 추가 권한 게이트 — 선례 없음.**

- 코드베이스 전체에서 `IsAuthenticated`가 아닌 권한 클래스는 `IsSuperAdmin` 하나뿐
  (`backend/accounts/permissions.py:6`), 적용처는 `backend/accounts/views.py:104`(관리자 계정 관리)뿐
- 프론트 게이트도 `SuperAdminRoute`가 `/admin-users`에만 (`router/index.tsx:144-153`)
- 백엔드에 확인/2단계 승인 패턴 없음. 프론트 확인 다이얼로그도 `VendorRulesTab.tsx:40` 1건
- `ConfirmOrderView`(대량 발주 확정), `LineItemNoteExportView`(`views.py:343` — 다운로드하며
  `qs.update(is_resolved=True)` 부수효과) 같은 되돌리기 어려운 동작도 전부 `IsAuthenticated`

→ 강제 출고에 추가 권한을 두면 코드베이스 최초 사례가 되며, 기존 인증 테스트 관례
(`test_spec_015.py:652-654`, `:1057-1062`의 `status_code in (401, 403)`)와 별개의 새 테스트 축이 생긴다.

---

## 9. 위험 요소 및 구현 시 주의점

1. **T8 쿼리 예산에 여유가 거의 없음** — `<=6`(10그룹 매칭, 현재 ≈5) / `<=4`(전부 unmatched, 현재 ≈3)
   (`test_spec_015.py:1143-1153`). `_process_outbound_rows` 내부에 후보 조회를 추가하면 경계에 닿는다.
   배치 조회를 **별도 엔드포인트로 분리하면 T8을 전혀 건드리지 않는다.**
2. **`_recompute_order_aggregates` 미호출은 선행 불일치이며 어떤 테스트로도 pin되어 있지 않다**
   (`:2810-3101` vs 자매 함수 `:2137-2145`+`:2212`). 답습/수정 중 SPEC이 명시 결정해야 하며,
   수정 시 T8 상수 조정이 동반된다.
3. **`index.test.tsx:218-223`의 snake_case 금지 정규식**이 매칭 실패 섹션 textContent 전체에 적용된다.
   피커 UI에 `logistics_status`/`purchase_status` 원값을 렌더하면 즉시 실패 —
   `OrderDetailPage.tsx:52` / `RackNumberPage/tabs/SummaryTab.tsx:12` 방식의 한국어 라벨 매핑 필요.
   [v1.0.5 정정: 이전 판이 인용한 `InboundPage/index.tsx:30-32`는 존재하지 않는 파일이다.]
4. **`OutboundUnmatchedItem`에 필수 필드를 추가하면 두 테스트 fixture가 컴파일 실패**
   (`index.test.tsx:31-38`, `outboundApi.test.ts:33-36`). optional로 추가하면 무해.
5. **`test_both_endpoints_return_identical_results_for_equivalent_input`(`:746`)이 딕셔너리 전체
   동등성을 검사** — 새 필드가 비결정적이면 깨진다. 후보 리스트 동봉 시 결정적 정렬(`order_by("pk")`) 필수.
6. **`purchase_status`가 `LineItemDetailSerializer`에 없다** (`serializers.py:110-123`) —
   취소 품목 제외를 프론트에서 판정할 수 없다.
7. **`Order.name`은 유일하지 않다** (`unique_together`는 `(shopify_order_id, store_type)`).
   정상 경로는 `.order_by("pk")` + `setdefault`로 oldest-wins를 재현한다 (`:2912-2925`, 테스트 `:1166-1199`).
   강제 경로의 후보 조회도 **동일한 tie-break**를 써야 피커가 보여준 주문과 실제 기록 대상이 어긋나지 않는다.
8. **동시성 락 없음** — @MX:WARN `:2802-2809`. 강제 경로는 사용자가 대상을 직접 고르는 만큼
   피커 조회 시점의 `shipped_quantity`가 실행 시점에 낡을 수 있어 창이 더 넓어진다.
   참고로 `_apply_logistics_transition:247`은 `select_for_update()`를 쓴다 — 같은 파일에 두 관례 공존.
9. **한 주문에 동일 SKU LineItem이 복수 존재 가능** (`models.py:235`) — 피커 목록에서 title/sku만으로는
   구분되지 않을 수 있으므로 `line_item_id`가 표시 키가 되어야 한다.
10. **`unmatched` 행은 `line_item_id`를 갖지 않는다** (`:2954-2980`) — `matched`/`quantity_exceeded`만
    보유(`:3031`, `:3045`). 프론트 `ResultSection` row key도 `${name}-${sku}-${index}`
    (`OutboundPage/index.tsx:154`). 체크박스 선택 상태 키 결정이 필요하다
    (`line_item_not_found` 행은 그룹 루프에서 나오므로 `(name, sku)`가 유일하다).
11. **음수/판독불가 total 불변식이 두껍게 pin됨** (`:932-1021`, `:1524-1637`). 강제 엔드포인트가
    `_process_outbound_rows`를 우회해 별도 경로를 만들면 이 검증을 중복 구현해야 하며,
    누락 시 "출고 취소/되돌리기" 제외 스코프가 뒷문으로 뚫린다.
12. **`OutboundPage`의 named export 이름과 `index.tsx` 모듈 해석은 라우터가 의존**
    (`OutboundPage/index.tsx:24-28` @MX:ANCHOR).
