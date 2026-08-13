---
id: SPEC-ORDER-018
document: plan
version: 1.0.4
status: completed
updated: 2026-08-13
---

# 구현 계획 — SPEC-ORDER-018 보류/제외 품목 발주 대상 복구

`spec.md`의 요구사항(REQ-RESTORE-001~023)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD
사이클, 리스크와 완화책, MX 태그 계획을 정리한다. 근거 자료는 `research.md`(file:line 인용
포함)를 참조한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며,
요구사항을 재진술하지 않고 REQ ID로 참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의
`constitution.development_mode: "tdd"`, `tdd_settings.test_first_required: true`,
`tdd_settings.min_coverage_per_commit: 80`에 따른다. 기존 코드 위에 얹는 브라운필드 변경이므로
각 RED 단계 전에 대상 코드를 먼저 읽는 사전 단계를 거친다
(`.claude/rules/moai/workflow/workflow-modes.md`의 Brownfield Enhancement 절).

---

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 회귀 베이스라인 고정 (RED가 아닌 GREEN 확인)**: 어떤 코드도 쓰기 전에
  `test_purchase_orders.py::TestUnorderedItemsViewPurchaseStatusFilter`(`:2152`)와
  `TestUnorderedItemsViewDamagedExchange`(`:451`)를 실행해 현재 전량 통과함을 기록한다.
  이 두 클래스가 이 SPEC의 회귀 감시선이다. **이 단계에서 실패가 나오면 그것은 이 SPEC과
  무관한 선행 문제이며, 진행 전에 격리해야 한다**(작업 트리 공유로 인한 무관한 실패 가능성 —
  현재 `git status`에 `order/models.py`, `order/shopify_orders.py` 등 미커밋 변경이 있다).

- **M1 (High) — 조회 뷰 테스트 선작성 (RED)**: `backend/order/tests/test_spec_018.py`를
  신규 작성한다. 뷰가 아직 없으므로 URL 역참조/요청 자체가 실패해 자연히 RED다. 작성 범위:
  T1(4개 상태 선별 + 무쓰기, AC-RESTORE-001), T2(null SKU 제외, AC-RESTORE-002),
  T3(환불 넷팅 3분기, AC-RESTORE-003), T4(응답 봉투·필드·결정적 정렬, AC-RESTORE-004),
  T5(미인증 401, AC-RESTORE-005).

- **M2 (High) — 조회 뷰 구현 (GREEN)**: `purchase_order_views.py`에 뷰를 추가하고
  `urls.py`에 정적 경로를 등록한다. 커버 REQ: 001~008. `_reorder_candidate_filter`를
  **호출하지 않는다**.

- **M3 (High) — 회귀·격리 테스트 (RED→GREEN, 코드 변경 없이 GREEN이어야 함)**:
  T6(미발주 목록 + Daily Review 업로드 매칭 불변, AC-RESTORE-006), T7(제외 품목 유무에 따른
  미발주 엔드포인트 쿼리 수 동일, AC-RESTORE-007)을 추가한다. **M2가 올바르면 이 두 테스트는
  코드 수정 없이 즉시 통과해야 한다** — 실패한다면 M2가 공유 필터나 기존 경로를 건드렸다는
  뜻이다(REQ-RESTORE-009/010/011).

- **M4 (High) — 복구 부수효과 테스트 (RED→GREEN, 백엔드 코드 변경 없이 GREEN이어야 함)**:
  T8(`order_cancelled` 복구 → `ready_to_ship` true→false, `Order.status` 불변,
  AC-RESTORE-008), T9(`on_hold` 복구 무변화 + `cs_required` 복구 false→true,
  AC-RESTORE-009), T10(쓰기 필드 범위 + `LineItemNote` 불변, 두 엔드포인트 각각,
  AC-RESTORE-010), T11(PO 연결 품목 복구의 알려진 한계 고정, AC-RESTORE-011)을 추가한다.
  **이 4개는 기존 엔드포인트의 현재 동작을 특성화하는 테스트이므로 백엔드 구현 변경 없이
  통과해야 한다**(REQ-RESTORE-012~015, 022). 통과하지 않으면 `spec.md` 설계 결정 C 또는 E의
  사실 판단이 틀린 것이며, 구현이 아니라 SPEC을 정정해야 한다.

- **M5 (Medium) — 프론트엔드 조회 계층 (RED→GREEN)**: `purchaseOrderApi.ts`에 타입과 fetch
  함수, `usePurchaseOrderQueries.ts`에 쿼리 키·조회 훅·무효화 추가. 커버 REQ: 021의 절반
  (무효화).

- **M6 (Medium) — 보류/제외 뷰 UI (RED→GREEN)**: `UnorderedItemsTab.test.tsx`에
  T12(뷰 전환 + 상태 라벨 + `unordered` 옵션 노출, AC-RESTORE-012), T13(선택 격리,
  AC-RESTORE-013), T14(복구 성공 시 두 쿼리 무효화, AC-RESTORE-014)을 먼저 작성한 뒤
  `UnorderedItemsTab.tsx`를 구현한다. 커버 REQ: 016~021.
  **[HARD] 신규 훅을 `vi.mock` 팩토리(`UnorderedItemsTab.test.tsx:13-22`)와
  `beforeEach`(`:31-57`)에 반드시 추가한다** — 누락하면 기존 2개 테스트(`:60`, `:73`)가
  `undefined is not a function`으로 깨진다.

- **M7 (Low) — REFACTOR + 문서 동기화**: 백엔드 뷰와 `UnorderedItemsView`의 중복(환불
  서브쿼리, 필드 조립)을 리스크 R1의 판단 기준에 따라 정리하고, `spec.md`/`plan.md`/
  `acceptance.md`/`spec-compact.md`의 상태를 갱신한다.

의존 관계: M0 → M1 → M2 → M3. M2 → M5 → M6. M0 → M4 (M2와 독립, 병렬 가능).
M7은 M1~M6 완료 후.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| NEW (뷰, 같은 파일 안) | `backend/order/purchase_order_views.py` | 제외 상태 조회 `APIView` 1개. `LineItemRackNumberSummaryView`(`:2365`)와 `OutboundForceCandidateView`(`:2963`) 옆, 또는 `UnorderedItemsView`(`:251`) 바로 뒤에 배치(구현자 재량). 인증 관례는 `:2380-2381`/`:2981-2982`와 동일한 `authentication_classes = [JWTAuthentication]` + `permission_classes = [IsAuthenticated]`. **`_reorder_candidate_filter`(`:93`)를 호출하지 않는다** — `LineItem.objects.filter(purchase_status__in=[...])`로 직접 시작한다. 환불 서브쿼리는 `UnorderedItemsView:263-272` / `LineItemRackNumberSummaryView:2387-2395`와 동일 형태. 넷팅 가드는 **`LineItemRackNumberSummaryView:2415`의 `if li.refunded_qty and net_qty == 0:` 형태**를 쓴다(`spec.md` 설계 결정 D — `UnorderedItemsView:293-294`의 무조건 스킵이 아니다). 정렬은 `-order__shopify_created_at` + `pk`(설계 결정 H). 응답은 `Response({"count": len(results), "results": results})` (`:314`와 동일 봉투, 설계 결정 G). 주문명 폴백은 `:296`의 `order.name or (f"#{order.order_number}" if order.order_number else None)`를 그대로. |
| MODIFY | `backend/order/urls.py` | 정적 경로 1개 추가. 권고 경로: `purchase-orders/excluded-items/`. 위치는 `:66`(`purchase-orders/unordered/`) 인근이며, **`:150`의 일반 목록 `path("purchase-orders/", ...)`보다 반드시 앞**이어야 한다(`:63` 주석 "more specific paths must come before the generic list"). `purchase-orders/` 아래에 `<int:pk>` 패턴이 없으므로 정적 세그먼트 충돌은 발생하지 않는다(`:102-103`, `:123-127`의 동일 취지 주석 참조). 임포트 목록에도 신규 뷰 추가. |
| NEW | `backend/order/tests/test_spec_018.py` | 모듈 docstring에 `Coverage targets:` T1~T11과 REQ/AC 매핑(`test_spec_015.py:1-24` 관례, `test_spec_016.py:1-40`도 동일). URL 상수는 `test_purchase_orders.py:50-59` 관례를 따라 파일 상단에 정의. 픽스처(`user`/`auth_client`/`anon_client`)는 `test_purchase_orders.py:72`/`:77`/`:85` 또는 `test_spec_015.py:611`/`:617`/`:625` 형태를 그대로 복제(공용 `backend/conftest.py`는 `api_client` 하나만 제공하므로 스위트마다 자체 정의가 관례다). 헬퍼는 `test_purchase_orders.py:89`(`_make_order`)/`:97`(`_make_line_item`) 형태. 쿼리 수 측정(T7)은 `from django.test.utils import CaptureQueriesContext`(`test_spec_015.py:34`) 사용. |
| MODIFY | `frontend/src/services/purchaseOrderApi.ts` | (a) 제외 품목 행 타입. `UnorderedItem`(`:5-14`)과 필드가 거의 같으므로 재사용 또는 확장을 검토하되, **`purchase_status`는 이 뷰에서 필수 표시 값**이므로 optional로 두지 않는다. (b) fetch 함수 — `getUnorderedItems`(`:90-93`)와 동일한 형태, 반환 타입 `{ count: number; results: ... }` (`PaginatedResponse<T>`(`:61-66`)를 쓰지 **않는다** — 서버가 `next`/`previous`를 반환하지 않는다). **`PURCHASE_STATUS_OPTIONS`(`:16-25`)는 수정하지 않는다.** |
| MODIFY | `frontend/src/hooks/usePurchaseOrderQueries.ts` | (a) `QUERY_KEYS`(`:26-31`)에 신규 키 추가 — 기존 `unordered: ['purchase-orders', 'unordered']`와 접두사를 공유하되 다른 키여야 한다. (b) 조회 훅 추가(`useUnorderedItems`(`:33-38`) 형태). (c) **`useUpdateLineItemStatus`의 `onSuccess`(`:109`)와 `useBulkUpdateLineItemStatus`의 `onSuccess`(`:125`)에 신규 키 무효화를 추가**(REQ-RESTORE-021) — 누락하면 복구 후 제외 목록에 항목이 남는다. 그 외 두 훅의 동작(toast, `missing_ids` 경고 `:126-130`)은 변경하지 않는다. |
| MODIFY | `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` | (a) 뷰 전환 state + 컨트롤(REQ-016, 기본값은 미발주). (b) 제외 목록 조회 훅 호출. (c) **LineItem id 집합을 `useState`로 관리하는 뷰 로컬 선택**(REQ-019, 설계 결정 F) — `usePurchaseOrderStore`(`:45`)의 `selectedSkus`/`toggleSku`를 이 뷰에서 **읽지도 쓰지도 않는다**. (d) 일괄 select의 옵션 필터를 뷰에 따라 분기 — 미발주 뷰는 기존 `:126`의 `filter(o => o.value !== 'unordered')` 유지, 제외 뷰는 전체 목록(REQ-018). (e) 행별 select는 `:262`의 전체 목록을 그대로 재사용(이미 `unordered` 포함). (f) 상태 라벨 열(REQ-017) — `PURCHASE_STATUS_OPTIONS`에서 `value → label` 조회. (g) 발주 파일 생성 버튼(`:143-174`)은 제외 뷰에서 비활성/미표시(REQ-020). (h) 일괄 복구는 기존 `bulkStatusMutation`(`:44`, `:74-81`)을 재사용하되 `ids`를 로컬 선택에서 직접 만든다 — `:69-72`의 SKU→id 재매핑 경로를 타지 않는다. |
| MODIFY | `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx` | **[HARD]** `vi.mock('@/hooks/usePurchaseOrderQueries', ...)` 팩토리(`:13-22`)에 신규 훅 이름 추가 + `beforeEach`(`:31-57`)에 `vi.mocked(신규훅).mockReturnValue(...)` 추가. 그 다음 T12~T14 시나리오 추가. |
| EXISTING (무수정, 회귀 확인만) | `backend/order/tests/test_purchase_orders.py` | `TestUnorderedItemsViewPurchaseStatusFilter`(`:2152`) 5개와 `TestUnorderedItemsViewDamagedExchange`(`:451`) 전량 무수정 통과가 M3의 완료 조건. |
| EXISTING (변경 없음) | `backend/order/purchase_order_views.py`의 `_reorder_candidate_filter`(`:93-110`), 호출부 `:275`/`:567`/`:1071`/`:1410`, `LineItemStatusUpdateView`(`:1863-1900`), `LineItemBulkStatusUpdateView`(`:1908-1958`), `_recompute_order_aggregates`(`:123-195`) | `spec.md` Exclusions. |
| EXISTING (변경 없음) | `backend/order/models.py`, `backend/order/excel_utils.py`, `backend/order/serializers.py`, `backend/order/views.py` | 신규 필드·마이그레이션·상태값·노트 로직 없음. |
| EXISTING (변경 없음) | `frontend/src/stores/usePurchaseOrderStore.ts`, `frontend/src/pages/PurchaseOrders/index.tsx` | 설계 결정 F / Exclusions("신규 탭 없음"). |

---

## 기술적 접근

### 조회 뷰 (M1 RED → M2 GREEN)

1. **선별 조건**: `LineItem.objects.filter(purchase_status__in=("on_hold",
   "order_cancelled", "cs_required", "other_publisher"))`로 시작한다. 4개 코드는
   `models.py:156-167`의 `PURCHASE_STATUS_CHOICES`에 정의된 값이다.
   `_reorder_candidate_filter`를 호출하지 않는 것이 REQ-RESTORE-011의 구현이다.
   상수 목록을 모듈 레벨에 두면 뷰와 테스트가 같은 정의를 공유할 수 있다.
2. **SKU 가드**(REQ-004): `.exclude(sku__isnull=True)` — `OutboundForceCandidateView:3010`과
   동일 형태. (`UnorderedItemsView:275`는 `filter(sku__isnull=False)`를 쓰는데, 이는
   `_reorder_candidate_filter`에 넘기기 전에 적용해야 하는 구조 때문이다. 이 뷰는 어느 쪽을
   써도 무방하다.)
3. **환불 서브쿼리**: `UnorderedItemsView:263-272`를 그대로 복제한다 —
   `Refund.objects.filter(order_id=OuterRef("order_id"),
   line_item_id=OuterRef("shopify_line_item_id")).values("order_id", "line_item_id")
   .annotate(total=Sum("quantity")).values("total")[:1]`. 두 키가 모두 필요한 이유는
   `:2384-2386`의 주석에 있다(Refund 행은 로컬 pk가 아니라 Shopify의 `line_item_id`를 든다).
   `Coalesce(Subquery(...), 0)`로 `refunded_qty` annotate.
4. **정렬**(REQ-007, 설계 결정 H): `.order_by("-order__shopify_created_at", "pk")`.
   `.select_related("order")`로 주문명 접근의 N+1을 막는다(`:282` 관례).
5. **넷팅 루프**(REQ-005, 설계 결정 D): `net_qty = max((li.quantity or 0) -
   li.refunded_qty, 0)` 후 **`if li.refunded_qty and net_qty == 0: continue`**.
   `UnorderedItemsView:293-294`의 무조건 `if net_qty == 0: continue`를 복사하면
   AC-RESTORE-003의 세 번째 분기(미환불 null 수량)가 깨진다.
6. **행 조립**(REQ-003): `UnorderedItemsView:297-308`의 필드 집합에서 `auto_distributor`를
   뺀 형태 — `id`, `order_name`(`:296`의 폴백 포함), `sku`, `title`, `vendor`,
   `quantity`(순수량), `purchase_status`. `auto_distributor`는 발주처 자동 추천값이며
   제외 품목 목록의 목적(복구)과 무관하므로 제외한다. `DistributorVendorRule` 조회
   (`:286-288`)도 따라서 불필요하다.
7. **응답**(REQ-006): `Response({"count": len(results), "results": results})` —
   페이지네이션 클래스를 붙이지 않는다.
8. **인증**(REQ-008): 클래스 속성 2줄. 별도 코드 없이 401이 나온다.

### URL 등록 (M2)

`urls.py`의 `:66` 인근에 정적 경로를 추가한다. 검증 완료 사실:
`purchase-orders/` 하위에 `<int:pk>` 세그먼트를 갖는 패턴이 존재하지 않으므로
(`:64-150` 전수 확인) `<int:pk>` 그림자 문제는 이 경로에 발생하지 않는다 —
`:102-103`(rack-number-summary)과 `:123-127`(outbound-force-candidates)의 주석이 같은 취지의
판단을 이미 기록해 두었다. 유일한 순서 제약은 `:150`의 일반 목록보다 앞이어야 한다는 것이다.

### 회귀 격리 검증 (M3)

- **T6**: 하나의 픽스처에서 `unordered` 1건(SKU A) + 4개 제외 상태 4건(SKU B/C/D/E)을
  만든 뒤, (a) `UNORDERED_URL` GET이 A만 반환하는지, (b) B~E를 지목한 Daily Review 업로드가
  전부 skip으로 처리되고 네 품목의 `purchase_status`가 그대로인지 확인한다. Daily Review
  업로드 테스트 기법은 `test_daily_review_upload.py`의 기존 시나리오를 참조한다
  (예: `:694` `test_warehouse_skipped_if_no_unordered_line_items`).
- **T7**: `CaptureQueriesContext`로 `UNORDERED_URL` GET을 감싸 (a) 제외 품목이 DB에 없는
  상태와 (b) 제외 품목 4건이 있는 상태에서 쿼리 수가 **동일**한지 확인한다. 절대값이 아니라
  동등성을 주장하므로 인증 쿼리 유무와 무관하게 성립한다 — `UnorderedItemsView`는 뷰밖에
  없으므로 함수 직접 호출 스코프를 만들 수 없고, 동등성 비교가 그 제약을 우회하는 방법이다.

### 복구 부수효과 특성화 (M4)

이 마일스톤의 테스트는 **기존 엔드포인트의 현재 동작을 고정**하는 것이지 새 동작을 요구하는
것이 아니다. 따라서 백엔드 코드 변경 없이 통과해야 한다.

- **T8**(AC-RESTORE-008): Order 1개에 LineItem 2건 —
  li1(`logistics_status="received"`, `purchase_status="unordered"`),
  li2(`purchase_status="order_cancelled"`, `logistics_status="not_shipped"`).
  `_recompute_order_aggregates([order.id])`를 먼저 호출해 `ready_to_ship`이 `True`가 되게
  한다(`:176`이 li2를 제외 → 남은 li1이 `received` → `:182-185`의 `all(...)`이 참).
  `Order.status`도 함께 기록한다(li1/li2의 `logistics_status`가 서로 달라 `"partial"`이
  된다, `:171-172`). 그 다음 li2를 `LINE_ITEM_STATUS_URL`로 `unordered`로 복구하고 Order를
  refresh — `ready_to_ship`이 `False`(li2가 집계에 재진입하고 `not_shipped`+비-`in_stock`),
  `Order.status`는 `"partial"` 그대로임을 확인한다.
- **T9**(AC-RESTORE-009): 두 Order를 쓴다. Order1 — `received` + `on_hold` LineItem 1건.
  복구 전후 `ready_to_ship`/`status` 모두 동일(`on_hold`는 `:176-185` 어디에도 등장하지
  않는다). Order2 — `received` + `cs_required` 1건과 `received` + `unordered` 1건. 복구 전
  `ready_to_ship`은 `:179-180`에 의해 `False`, 복구 후 `True`.
- **T10**(AC-RESTORE-010): `on_hold` LineItem에 `rack_number="A-01"`,
  `confirmed_distributor="booxen"`, `logistics_status="received"`, 미해결 `LineItemNote`
  1건을 세팅한다. 복구 전 전 필드 스냅샷을 뜨고, `LINE_ITEM_STATUS_URL`(단일)과
  `BULK_STATUS_URL`(일괄) **각각**에 대해 복구 → `purchase_status`만 달라지고 나머지가
  동일한지, `li.notes.count()`와 그 노트의 `is_resolved`가 불변인지 확인한다. 단일 경로는
  `:1891`의 `update_fields=["purchase_status"]`, 일괄 경로는 `:1948`의
  `existing.update(purchase_status=...)`가 근거다.
- **T11**(AC-RESTORE-011): `order_cancelled` LineItem을 `PurchaseOrder`에 `add()`로 연결한 뒤
  `unordered`로 복구 → `UNORDERED_URL`에도 신규 제외 목록 URL에도 나타나지 않음을 확인한다.
  전자의 근거는 `_reorder_candidate_filter:109`의 `.exclude(purchase_status="unordered",
  purchase_orders__isnull=False)`이고, `test_po_linked_unordered_item_excluded`
  (`test_purchase_orders.py:2197-2215`)가 같은 규칙을 이미 고정한다. 후자는 복구로
  `purchase_status`가 4개 상태를 벗어났기 때문이다.

### 프론트엔드 (M5 → M6)

1. **쿼리 키**: `QUERY_KEYS`(`:26-31`)에 추가. 기존 `unordered`와 접두사를 공유하되
   구분되는 키여야 `invalidateQueries`가 정확히 동작한다.
2. **무효화**(REQ-021): `:109`와 `:125` 두 지점 각각에 신규 키 무효화를 추가한다. 두 훅은
   미발주 뷰도 쓰므로 양방향으로 필요하다 — 미발주 뷰에서 항목을 `on_hold`로 바꾸면 제외
   목록에 나타나야 하고, 제외 뷰에서 복구하면 미발주 목록에 나타나야 한다.
3. **뷰 로컬 선택**(REQ-019, 설계 결정 F): `useState<Set<number>>` 또는 `number[]`.
   `usePurchaseOrderStore`(`:45`)에서 가져오는 4개 중 어느 것도 제외 뷰 경로에서 호출하지
   않는다. 뷰 전환 시 로컬 선택을 초기화하고, 전역 `clearSelections()`는 **호출하지
   않는다**(미발주 뷰의 선택을 지워버리면 REQ-019의 "이월하지 않는다"를 넘어 기존 동작을
   손상한다).
4. **일괄 복구 호출**: 기존 `bulkStatusMutation.mutate({ ids, purchaseStatus })`
   (`:74-81`)를 그대로 쓰되 `ids`를 로컬 선택에서 직접 만든다. 성공 콜백은 로컬 선택
   초기화로 바꾼다(`:77-79`의 `clearSelections()`를 제외 뷰 경로에서 호출하지 않는다).
5. **옵션 필터 분기**(REQ-018): `:126`의 `filter((o) => o.value !== 'unordered')`를 뷰
   조건부로 만든다. 미발주 뷰에서의 동작은 그대로여야 한다(AC-RESTORE-012의 마지막 절).
6. **발주 파일 버튼**(REQ-020): 제외 뷰에서는 렌더링하지 않는 편이 `selectedSkus`에 대한
   의존을 구조적으로 끊어 가장 안전하다. 비활성화만 하면 뷰 전환 순간의 상태 조합에 따라
   활성화될 여지가 남는다.
7. **테스트 mock**(M6 [HARD]): `UnorderedItemsTab.test.tsx:13-22`의 `vi.mock` 팩토리는
   모듈 전체를 대체하므로 팩토리에 없는 export를 컴포넌트가 호출하면 `undefined`가 된다.
   신규 훅 추가 시 팩토리와 `beforeEach`(`:31-57`) 양쪽을 갱신해야 기존 2개
   테스트(`:60`, `:73`)가 유지된다.

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | 신규 뷰가 `UnorderedItemsView`와 환불 서브쿼리·행 조립을 중복해 두 곳을 따로 고쳐야 하는 부채가 생긴다 | **의도적으로 중복을 허용한다.** 공유 헬퍼로 추출하면 `UnorderedItemsView`(4개 호출부 중 하나)를 수정하게 되어 설계 결정 A의 "회귀 표면 0"이 무너진다. 같은 파일에 이미 이 중복이 3벌 존재한다(`:263-272`, `:2387-2395`, `:1060-1068`) — 이 저장소가 이미 받아들인 트레이드오프다. M7 REFACTOR에서도 이 중복은 **정리 대상이 아니다**. |
| R2 | M2 구현자가 `UnorderedItemsView:293-294`를 그대로 복사해 무조건 넷팅 스킵을 쓴다 | T3(AC-RESTORE-003)의 세 번째 분기(미환불 null 수량)가 이를 정확히 판별한다. M1에서 T3을 먼저 작성하므로 RED 단계에서 걸린다. |
| R3 | 프론트엔드에서 실수로 `toggleSku`를 제외 뷰에 연결해 전역 SKU 선택이 오염된다 | T13(AC-RESTORE-013)이 "전역 SKU 선택이 내내 무변경"을 assertion으로 확인한다. mock된 스토어의 `toggleSku`/`selectAllSkus`에 대해 `expect(...).not.toHaveBeenCalled()`로 검증할 수 있다. |
| R4 | 무효화 누락으로 복구 후 제외 목록에 항목이 남는다 | T14(AC-RESTORE-014)가 `invalidateQueries` 호출을 직접 확인한다. `useQueryClient`를 mock하거나 훅 단위 테스트로 검증한다. |
| R5 | 설계 결정 C의 `ready_to_ship` 분석이 틀렸다 | M4를 M2와 **독립적으로, 백엔드 구현 전에** 실행할 수 있게 배치했다. T8/T9가 실패하면 구현이 아니라 `spec.md` 설계 결정 C를 정정하고 AC-RESTORE-008/009를 다시 쓴다. |
| R6 | 원격 MySQL 테스트 DB를 공유하는 다른 세션과 pytest가 동시에 돌아 무관한 실패가 섞인다 | 프로젝트 기존 관례 — pytest를 동시 실행하지 않는다. M0의 베이스라인 기록이 "이 SPEC 이전부터 실패하던 것"과 "이 SPEC이 깬 것"을 구분하는 기준이 된다. 현재 작업 트리에 미커밋 변경(`order/models.py`, `order/shopify_orders.py`, `order/tests/test_shopify_orders.py` 등)이 있어 무관한 실패 가능성이 실재한다. |
| R7 | 신규 URL이 `:150`의 일반 목록보다 뒤에 등록되어 404가 난다 | `urls.py:63`의 기존 주석이 이미 규칙을 명시한다. T1이 URL 역참조/요청으로 즉시 검출한다. |
| R8 | 제외 목록에 나타난 품목을 복구했는데 PO 연결 때문에 미발주 목록에 안 나타나 담당자가 혼란을 겪는다 | 이 SPEC에서 해결하지 않는다(REQ-RESTORE-022). T11이 이 동작을 고정해 이후 누군가 "고치려고" 공유 필터를 넓히는 것을 막는다. 후속 과제 2로 등록. |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | 신규 조회 뷰의 클래스 위 | 이 뷰가 `_reorder_candidate_filter`(`:93`)를 **의도적으로 호출하지 않는다**는 사실과 그 이유(공유 필터의 4개 호출부에 회귀를 만들지 않기 위해, `spec.md` 설계 결정 A). `OutboundForceCandidateView`의 `:2973-2978` docstring과 같은 성격의 기록이다. 이 태그가 없으면 이후 누군가 "중복 제거"를 명목으로 공유 필터를 재사용하려 할 수 있다. |
| `@MX:NOTE` (신규) | 신규 조회 뷰의 넷팅 루프 안 | 넷팅 가드가 `UnorderedItemsView:293-294`가 아니라 `LineItemRackNumberSummaryView:2415`의 가드된 형태를 따른다는 사실과 근거(`spec.md` 설계 결정 D). `:2416-2421`의 기존 주석과 같은 취지. |
| `@MX:NOTE` (신규) | `UnorderedItemsTab.tsx`의 뷰 로컬 선택 state 선언부 | 제외 뷰의 선택이 전역 `usePurchaseOrderStore`(`:5`)와 분리된 이유 — SKU 키 모호성과 발주 파일 생성(`:90`)으로의 누출(`spec.md` 설계 결정 F). |
| 검토 후 무변경 | `purchase_order_views.py:86-92`의 `@MX:NOTE` | `_reorder_candidate_filter`의 "Fan-in == 4" 서술은 이 SPEC이 호출부를 늘리지 않으므로 **갱신 불필요**하다. 신규 뷰가 이 헬퍼를 호출하면 이 태그를 고쳐야 한다는 사실 자체가 설계 위반의 신호다. |
| 검토 후 무변경 | `purchase_order_views.py:113-122`의 `@MX:NOTE` | `_recompute_order_aggregates`의 "Fan-in == 8"도 신규 호출부가 없으므로 무변경. |
| 검토 후 무변경 | `usePurchaseOrderStore.ts:12-13`의 `@MX:ANCHOR`/`@MX:REASON` | 설계 결정 F에 따라 제외 뷰가 이 스토어를 쓰지 않으므로 fan-in 서술("UnorderedItemsTab and VendorFileUploadTab") 무변경. |
| 검토 후 무변경 | `usePurchaseOrderQueries.ts:117-118`의 `@MX:WARN`/`@MX:REASON` | 일괄 상태 변경의 부분 성공 경고는 그대로 유효하다. 제외 뷰의 일괄 복구도 같은 훅을 쓰므로 오히려 적용 범위가 넓어진다 — 문구 수정 없이 유지. |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문은
영어로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 베이스라인 기록 — `test_purchase_orders.py::TestUnorderedItemsViewPurchaseStatusFilter`
      5개와 `TestUnorderedItemsViewDamagedExchange` 전량의 현재 통과 여부가 기록되어 있다
- [ ] `spec.md`의 설계 결정 A~I가 검토되었다
- [ ] 신규 URL 경로명이 확정되었다

**Done (백엔드)**

- [ ] `test_spec_018.py` T1~T11 전량 통과
- [ ] `test_purchase_orders.py`의 두 회귀 클래스 **무수정** 전량 통과 (REQ-009/010)
- [ ] `test_daily_review_upload.py` 전량 통과 (REQ-010)
- [ ] `test_spec_011.py`/`test_spec_012.py` 전량 통과 (`ready_to_ship`/`status` 집계 회귀)
- [ ] `git diff`에 `_reorder_candidate_filter`(`:93-110`)와 그 4개 호출부의 변경이 **없다**
      (REQ-011)
- [ ] `git diff`에 `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`의 변경이
      **없다** (REQ-012)
- [ ] `backend/order/migrations/`에 신규 파일이 **없다**, `models.py` diff가 **없다**
      (REQ-023)
- [ ] `python manage.py makemigrations --check --dry-run`이 변경 없음을 보고한다 (REQ-023)
- [ ] `ruff check` 신규 에러 0 (기존 베이스라인 대비 — SPEC-ORDER-016 v1.0.5가 기록했듯 이
      저장소에는 이 SPEC과 무관한 기존 에러가 있어 절대 0은 달성 불가능하다)

**Done (프론트엔드)**

- [ ] `UnorderedItemsTab.test.tsx` T12~T14 + **기존 2개 테스트(`:60`, `:73`)** 전량 통과
- [ ] `tsc --noEmit` 신규 에러 0
- [ ] `eslint` 신규 에러 0
- [ ] `git diff`에 `usePurchaseOrderStore.ts`와 `PurchaseOrders/index.tsx`의 변경이 **없다**
- [ ] `git diff`에 `PURCHASE_STATUS_OPTIONS`(`purchaseOrderApi.ts:16-25`)의 변경이 **없다**

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`/`spec-compact.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001, 002 | T1 |
| 003, 006, 007 | T4 |
| 004 | T2 |
| 005 | T3 |
| 008 | T5 |
| 009, 010 | T6 + 기존 회귀 스위트 |
| 011 | T7 + diff 게이트 |
| 012 | diff 게이트 (쓰기 뷰 무변경) |
| 013, 015 | T10 |
| 014 | T8, T9 |
| 016, 017, 018 | T12 |
| 019, 020 | T13 |
| 021 | T14 + 무효화 코드 리뷰 |
| 022 | T11 |
| 023 | `makemigrations --check` + `models.py` diff 게이트 |

---

## 관련 참조 구현

- 별도 읽기 경로 아키텍처: `backend/order/purchase_order_views.py:2963`
  (`OutboundForceCandidateView`) — 근거 docstring `:2973-2978`, 인증 `:2981-2982`,
  빈 입력 무쿼리 `:2991-2996`, 가드 `:3002`, SKU 제외 `:3010`,
  결정적 정렬 `:3011`(주석 `:3003-3006`)
- 교차 주문 읽기 전용 뷰 + 가드된 환불 넷팅: `:2365`
  (`LineItemRackNumberSummaryView`) — 서브쿼리 `:2387-2395`(주석 `:2384-2386`),
  쿼리셋 `:2397-2408`, 넷팅 가드 `:2415`(주석 `:2416-2421`)
- 응답 봉투·필드 구성 원본: `:251`(`UnorderedItemsView`) — 서브쿼리 `:263-272`,
  쿼리셋 `:274-284`, 넷팅 `:291-294`, 주문명 폴백 `:296`, 필드 `:297-308`, 봉투 `:314`
- 재사용할 쓰기 경로: `:1863-1900`(단일, `update_fields` `:1891`, 재계산 `:1892`),
  `:1908-1958`(일괄, `ids` 계약 `:1923`, UPDATE `:1948`, 재계산 `:1950`)
- 집계 규칙: `:123`, `:167-173`(status), `:176-185`(ready_to_ship), docstring `:130-136`
- 절대 넓히지 **않을** 지점: `:93-110` + 호출부 `:275`/`:567`/`:1071`/`:1410`
- URL 등록 순서 규칙: `backend/order/urls.py:63`(주석), `:66`, `:150`;
  정적 세그먼트 안전성 선례 `:102-103`, `:123-127`
- 회귀 고정 테스트: `backend/order/tests/test_purchase_orders.py:2152`(클래스),
  `:2217-2234`(5개 상태 제외), `:2197-2215`(PO 연결 제외), `:451`(damaged_exchange 계열)
- 테스트 스위트 관례: `test_spec_015.py:1-24`(docstring), `:34`(`CaptureQueriesContext`),
  `:46`/`:50`(헬퍼), `:611`/`:617`/`:625`(픽스처); `test_spec_016.py:1-40`(docstring);
  `test_purchase_orders.py:50-59`(URL 상수), `:72`/`:77`/`:85`(픽스처), `:89`/`:97`(헬퍼)
- 프론트엔드 mock 관례: `UnorderedItemsTab.test.tsx:13-22`(`vi.mock` 팩토리),
  `:31-57`(`beforeEach`), `:60`/`:73`(깨지면 안 되는 기존 테스트)
