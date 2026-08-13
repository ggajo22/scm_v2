---
id: SPEC-ORDER-018
document: spec-compact
version: 1.0.5
status: completed
updated: 2026-08-13
---

# SPEC-ORDER-018 압축 요약 — 보류/제외 품목 발주 대상 복구

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(TDD 구현 계획), `acceptance.md`
(Given/When/Then), `research.md`(코드베이스 조사 근거, file:line 인용 전량 — 이 세션에서
직접 재검증).

## 문제

`purchase_status`가 `on_hold`/`order_cancelled`/`cs_required`/`other_publisher`인 LineItem은
발주 관련 **모든** 화면에서 사라진다. 원인은 공유 필터
`_reorder_candidate_filter`(`backend/order/purchase_order_views.py:93`, 본체 `:107-110`)가
`unordered`(PurchaseOrder 미연결)와 `damaged_exchange`만 통과시키기 때문이며, 이 필터는 4곳
(`:275` 미발주 목록, `:567` 발주처 비교, `:1071` Daily Review 엑셀, `:1410` Daily Review 업로드
매칭)이 공유한다.

들어가는 문은 여럿이다 — 행별 select가 7개 값을 전부 노출하고
(`UnorderedItemsTab.tsx:486`), 일괄 select는 `unordered`만 제거하며(`:126`), Daily Review
업로드는 '선택' 열 라벨을 상태로 자동 매핑한다(`excel_utils.py:614-622`). 나오는 문은 없다.

실제 업무: 미출간이라 `on_hold` → 나중에 출판사 재고 확인 후 주문 → **그 시점에 `unordered`로
복구 필요**. 오늘은 DB 직접 수정뿐이다.

운영 DB 실측(2026-08-13): 4개 상태 합계 **225건**(`other_publisher` 80 / `order_cancelled` 79 /
`cs_required` 49 / `on_hold` 17). 대표 사례 — LineItem id=15083, 주문 `#37636`, sku
`9791199783218`, `order_cancelled`, `rack_number='M4'`, `Refund` 0건.

## 솔루션

| 층 | 접근 |
|---|---|
| 읽기 | **신규 읽기 전용 엔드포인트** — 공유 필터를 재사용도 확장도 하지 않는 완전 별개 코드. 선례: `OutboundForceCandidateView` docstring(`:2973-2978`) "완전히 별개 코드라서 기존 두 엔드포인트에 쿼리를 하나도 추가하지 않는다". |
| 쓰기 | **신규 엔드포인트 없음** — 기존 `LineItemStatusUpdateView`(`:1863`)와 `LineItemBulkStatusUpdateView`(`:1908`)를 그대로 재사용. 두 엔드포인트 모두 대상의 현재 상태에 제약이 없고 `unordered`는 이미 유효한 선택지(`:1883`). |
| UI | **미발주 탭 안의 뷰 전환** — 새 페이지·새 탭 없음. `UnorderedItemsTab.tsx`의 행별 select(`:255-267`)와 일괄 컨트롤(`:342-365`) 재사용, 단 `unordered`를 선택 가능하게. |
| 선택 상태 | **LineItem id 기반 뷰 로컬 state** — 전역 SKU 배열(`usePurchaseOrderStore.ts:5`)에 섞이면 발주 파일 생성(`UnorderedItemsTab.tsx:144`)이 제외 품목 SKU를 서버로 보낸다. |

모델 변경·마이그레이션·감사 로그 없음.

## 설계 결정 요약

| 결정 | 내용 |
|---|---|
| A | 공유 필터를 넓히지 않고 별도 읽기 경로 신설 (선례 `:2963`, `:2973-2978`). `UnorderedItemsView`에 쿼리 파라미터를 추가하는 대안은 기각 — 회귀 표면이 `test_purchase_orders.py:2152-2234`까지 넓어진다. |
| B | 4개 상태는 재발주 큐 **밖에 그대로** 남는다. 보이게만 만들고 자격은 주지 않는다. |
| C | `Order.status`는 **불변**(`:167-173`은 `logistics_status`만 집계). `Order.ready_to_ship`은 `order_cancelled`(재진입, `True`→`False` 뒤집힘 가능)와 `cs_required`(`False`→`True` 가능)에서만 변한다. `on_hold`/`other_publisher`는 무변화. 근거 `:176-185`. |
| D | 환불 넷팅은 **가드된 관례** 채택 — `LineItemRackNumberSummaryView:2415`의 `if li.refunded_qty and net_qty == 0:`. `UnorderedItemsView:293-294`의 무조건 스킵은 `quantity`가 NULL인 데이터 결손 품목을 다시 숨겨 같은 문제를 재생산한다. |
| E | 복구는 `LineItemNote`를 **건드리지 않는다**. 역방향 결합이 코드베이스에 없고(`:1876-1900`, `:1922-1958` 모두 노트 미접근), 두 엔드포인트는 기존 흐름과 공유되며, 전용 해결 경로가 있다(`views.py:285`). **트레이드오프**: 미해결 노트가 남아 이중 작업 → 후속 과제 1. |
| F | 선택은 **LineItem id 기반 뷰 로컬 state**. 전역 스토어는 SKU 키(`usePurchaseOrderStore.ts:4-5`)이며 발주 파일 생성이 그대로 서버에 보낸다(`:90`). |
| G | **페이지네이션 없음**. `UnorderedItemsView:314`가 `{count, results}` 봉투를 직접 만들고 `PageNumberPagination`은 `PurchaseOrderListView` 전용(`:3428-3429`, `:3503`). 실측 225건. |
| H | 정렬은 `-order__shopify_created_at` + `pk` tie-break. 근거: `OutboundForceCandidateView:3011`의 결정적 정렬 관례(주석 `:3003-3006`). |
| I | 서버측 상태 필터 파라미터 **없음**. 응답에 `purchase_status`가 있으므로 클라이언트가 필터링한다. |

## REQ 목록 (요약, REQ-RESTORE-001~023)

**모듈 1 — 제외 상태 조회 경로 (신규, 읽기 전용)**

- 001 — 4개 상태 LineItem 반환, 쓰기 절대 없음
- 002 — `unordered`/`in_stock`/`damaged_exchange`는 절대 미포함
- 003 — LineItem id + 주문명 + sku + title + vendor + 순수량 + `purchase_status`
- 004 — SKU 없는 LineItem 제외
- 005 — 환불 넷팅(가드된 관례): 전량 환불만 제외, 미환불 0수량은 표시
- 006 — 비페이지네이션 `{count, results}` 봉투
- 007 — 결정적·반복 가능한 정렬
- 008 — 미인증 401

**모듈 2 — 기존 재발주 경로 불변**

- 009 — 공유 자격 규칙 무변경(미발주 목록·Daily Review 엑셀·발주처 비교)
- 010 — Daily Review 업로드가 4개 상태를 계속 매칭하지 않음
- 011 — 신규 읽기 경로는 별개 코드 — 기존 엔드포인트의 쿼리 수·응답 무변화

**모듈 3 — 복구 쓰기 경로 (기존 엔드포인트 재사용)**

- 012 — 신규 쓰기 엔드포인트 없음
- 013 — 쓰기 필드는 `purchase_status` 하나뿐
- 014 — 집계 재계산: `Order.status` 불변 / `ready_to_ship`은 `order_cancelled`·`cs_required`에서만 변함
- 015 — `LineItemNote` 생성·수정·해결·삭제 없음

**모듈 4 — 미발주 탭의 보류/제외 뷰**

- 016 — 탭 내 뷰 전환, 기본은 미발주 목록
- 017 — 각 행의 현재 상태 라벨 표시
- 018 — 행별·일괄 select 둘 다 `unordered` 선택 가능(`:126` 필터 비적용)
- 019 — LineItem id 기반 뷰 로컬 선택, 전역 SKU 선택과 격리, 전환 시 미이월
- 020 — 발주 파일 생성이 제외 뷰 선택을 사용하지 않음
- 021 — 복구 성공 시 두 목록 모두 갱신

**모듈 5 — 알려진 한계·비범위 불변식**

- 022 — PurchaseOrder 연결 품목은 복구해도 재발주 큐 밖(우회 추가 금지)
- 023 — 신규 모델 필드·마이그레이션·감사 로그 테이블 없음

## Acceptance Criteria (요약)

14개 인수 기준이 22개 요구사항을 커버한다(REQ-023은 DoD 게이트로 검증).

| AC | 레이어 | 요지 |
|---|---|---|
| AC-RESTORE-001 | `[BE]` | 7개 상태 각 1건 → 정확히 4건만 반환 + 요청 전후 스냅샷 동일(무쓰기) |
| AC-RESTORE-002 | `[BE]` | null SKU `on_hold` 제외, SKU 있는 형제는 반환 |
| AC-RESTORE-003 | `[BE]` | 부분 환불 5-2=3 표시 / 전량 환불 3-3 제외 / **미환불 null 수량은 표시** |
| AC-RESTORE-004 | `[BE]` | count 일치 + 페이지 커서 키 부재 + 7개 필드 + 동일 타임스탬프 2건 포함 재현 가능 정렬 |
| AC-RESTORE-005 | `[BE]` | 미인증 401 + 본문에 품목 데이터 없음 |
| AC-RESTORE-006 | `[BE]` | **재발주 큐 회귀** — 미발주 목록이 B~E 미포함 + Daily Review 업로드가 B~E 전량 skip·상태 무변경 |
| AC-RESTORE-007 | `[BE]` | 제외 품목 유무와 무관하게 미발주 엔드포인트 쿼리 수 동일 |
| AC-RESTORE-008 | `[BE]` | **`ready_to_ship` 재계산** — `order_cancelled` 복구로 true → false, `Order.status`는 불변 |
| AC-RESTORE-009 | `[BE]` | `on_hold` 복구는 두 집계 모두 불변 / `cs_required` 복구는 false → true |
| AC-RESTORE-010 | `[BE]` | 두 엔드포인트 각각에 대해 `purchase_status`만 변경 + 노트 개수·해결 플래그 불변 |
| AC-RESTORE-011 | `[BE]` | PO 연결 품목 복구 → 두 목록 어디에도 안 나타남(한계 고정) |
| AC-RESTORE-012 | `[FE]` | 초기 미발주 뷰 → 전환 후 상태 라벨 + 행별/일괄 select에 `unordered` 존재, 미발주 뷰 일괄에는 여전히 부재 |
| AC-RESTORE-013 | `[FE]` | 동일 SKU·다른 주문 2행 선택 → 정확히 2개 id로 요청, 전역 SKU 선택 무변경, 복귀 후 발주 파일 생성 영향 없음 |
| AC-RESTORE-014 | `[FE]` | 복구 성공 시 제외 목록 쿼리 + 미발주 쿼리 둘 다 무효화 |

## 파일 변경 대상

| 구분 | 파일 |
|---|---|
| NEW (뷰) | `backend/order/purchase_order_views.py` — 제외 상태 조회 뷰 |
| MODIFY | `backend/order/urls.py` — 정적 경로 1개 등록(`:66` 인근, `:150` 일반 목록보다 앞) |
| NEW | `backend/order/tests/test_spec_018.py` |
| MODIFY | `frontend/src/services/purchaseOrderApi.ts` — 조회 함수 + 타입 |
| MODIFY | `frontend/src/hooks/usePurchaseOrderQueries.ts` — 쿼리 키·훅 + 무효화 2곳(`:109`, `:125`) |
| MODIFY | `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` |
| MODIFY | `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx` — mock 팩토리(`:13-22`)·`beforeEach`(`:31-57`)에 신규 훅 추가 필수 |
| EXISTING (무수정) | `_reorder_candidate_filter`(`:93-110`)와 4개 호출부, 쓰기 엔드포인트 2개, `models.py`, `excel_utils.py`, `usePurchaseOrderStore.ts`, `PurchaseOrders/index.tsx` |

## Exclusions (요약)

공유 필터 수정 없음 · 신규 쓰기 엔드포인트 없음 · 모델 변경·마이그레이션 없음 · 신규
`purchase_status` 값 없음 · 감사 로그 없음 · `LineItemNote` 자동 해결 없음 · 신규 페이지·탭
없음 · 서버측 필터 파라미터 없음 · 페이지네이션 없음 · `PURCHASE_STATUS_OPTIONS` 수정 없음 ·
`usePurchaseOrderStore` 수정 없음 · 렉번호 요약의 `order_cancelled` 제외(`:2399`) 수정 없음 ·
엑셀 기반 일괄 복구 없음

## 후속 과제 (요약)

1. 복구와 `LineItemNote` 해결의 연결 (설계 결정 E 트레이드오프)
2. PurchaseOrder 연결 품목의 복구 (REQ-022 한계)
3. 렉번호 요약의 `order_cancelled` 제외 재검토 (id=15083 사례)
4. 복구 이력 추적
5. `UnorderedItemsView` 선택 모델의 SKU → id 통일

## 참조 구현

- 별도 읽기 경로 아키텍처 원본: `backend/order/purchase_order_views.py:3402`
  (`OutboundForceCandidateView`, docstring `:2973-2978`, 빈 입력 무쿼리 `:2991-2996`,
  가드 `:3002`, 결정적 정렬 `:3011` + 주석 `:3003-3006`)
- 교차 주문 읽기 전용 뷰 + 가드된 환불 넷팅: `:2365`
  (`LineItemRackNumberSummaryView`, 넷팅 `:2415` + 주석 `:2416-2421`)
- 응답 봉투·필드 구성 원본: `:251`(`UnorderedItemsView`, 서브쿼리 `:263-272`,
  쿼리셋 `:274-284`, 넷팅 `:291-294`, 주문명 폴백 `:296`, 필드 `:297-308`, 봉투 `:314`)
- 재사용할 쓰기 경로: `:1863-1900`(단일), `:1908-1958`(일괄)
- 집계 재계산 규칙: `:123`(`_recompute_order_aggregates`), `:167-173`(status),
  `:176-185`(ready_to_ship), docstring `:130-136`
- 절대 넓히지 **않을** 지점: `:93-110`(`_reorder_candidate_filter`)와 호출부
  `:275`/`:567`/`:1071`/`:1410`
- 회귀 고정 테스트: `backend/order/tests/test_purchase_orders.py:2217-2234`
  (`test_all_non_unordered_statuses_excluded`), `:2197-2215`(PO 연결 품목 제외)
- 테스트 스위트 관례: `test_spec_015.py:1-24`(모듈 docstring), `:34`
  (`CaptureQueriesContext`), `:46`/`:69`(헬퍼); `test_purchase_orders.py:50`(URL 상수),
  `:72`/`:96`/`:85`(픽스처), `:89`/`:97`(헬퍼)
- 프론트엔드 mock 관례: `UnorderedItemsTab.test.tsx:17-27`, `:31-57`
