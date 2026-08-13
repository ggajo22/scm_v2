---
id: SPEC-ORDER-018
version: 1.0.3
status: completed
created_at: 2026-08-13
updated: 2026-08-13
author: ggajo
priority: High
issue_number: 0
labels: [order, purchase-status, restore, read-path, frontend]
---

# 보류/제외 품목 복구 — 4개 제외 상태를 발주 대상으로 되돌리는 경로 신설

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-13 | ggajo | 최초 작성 — 사용자 인터뷰 확정 내용(미발주 탭에 "보류/제외 품목" 뷰 추가, 4개 상태 전부 `unordered`로 복구 가능)을 근거로 작성. `purchase_status`가 `on_hold`/`order_cancelled`/`cs_required`/`other_publisher`인 LineItem이 모든 발주 화면에서 보이지 않아 DB 직접 수정 외에는 되돌릴 방법이 없는 문제를 해결한다. 핵심 제약: 공유 필터 `_reorder_candidate_filter`를 **넓히지 않고** 별도 읽기 경로를 신설하며(선례: `OutboundForceCandidateView`), 쓰기는 기존 `purchase_status` 갱신 엔드포인트 2개를 그대로 재사용한다. 모델 변경·마이그레이션·감사 로그 없음. 모든 `file:line` 인용은 `research.md`가 이 세션에서 직접 재검증했다 — SPEC-ORDER-016 v1.0.5가 기록한 허구 인용 사고를 반복하지 않기 위해 선행 SPEC 문서의 인용을 재사용하지 않았다. |
| 1.0.1 | 2026-08-13 | ggajo | 구현 완료. 계획 대비 발산 2건 기록. (1) **T14(AC-RESTORE-014)의 위치** — `acceptance.md` 품질 게이트 표는 `UnorderedItemsTab.test.tsx`를 지정하지만, 그 파일은 `usePurchaseOrderQueries` 모듈 전체를 `vi.mock`으로 대체하므로 검증 대상인 실제 `onSuccess` 콜백이 그 안에서 실행되지 않는다. `plan.md` 리스크 R4가 명시적으로 허용하는 "훅 단위 테스트" 경로를 택해 신규 파일 `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`에 실제 `QueryClientProvider` + `invalidateQueries` spy로 구현했다(선례: `useOutboundQueries.test.tsx`). AC의 Given 문구("두 훅을 실제 QueryClientProvider 안에서 렌더링하고 invalidateQueries를 spy 한다")는 그대로 충족한다. (2) **줄 번호 이동** — 구현 시점의 `purchase_order_views.py`는 동시 진행 중이던 SPEC-ORDER-016 작업으로 `research.md` 인용 대비 약 +33줄 밀려 있었다(`UnorderedItemsView` `:251`→`:284`, `LineItemStatusUpdateView` `:1863`→`:2194`, `LineItemBulkStatusUpdateView` `:1908`→`:2239`). 인용된 코드의 **내용**은 전부 일치했으므로 설계 판단에는 영향이 없다. 신규 뷰는 `UnorderedItemsView` 바로 뒤(`:350`~)에 추가했다. 확정된 엔드포인트 경로는 `GET /api/purchase-orders/excluded-items/`(`plan.md` 권고안 채택). M7 REFACTOR는 리스크 R1의 판단(환불 서브쿼리·행 조립 중복은 **의도적으로 유지**)에 따라 의도적 무변경이다. |
| 1.0.2 | 2026-08-13 | ggajo | 동기화 완료(2026-08-13 커밋 bd5a41c). **새로 발견된 발산 없음** — 단, `plan.md`의 파일 목록 기준으로는 신규 파일 1건(`frontend/src/hooks/usePurchaseOrderQueries.test.tsx`)이 계획 외다. `plan.md`는 이 파일을 언급하지 않는다. 그러나 그 사유(T14/AC-RESTORE-014를 훅 단위 테스트로 옮긴 결정)는 v1.0.1이 이미 발산 2건 중 하나로 기록했으므로, 이번 동기화에서 새로 드러난 발산은 아니다. 나머지 7개 파일(신규 뷰 1 + 신규 백엔드 테스트 1 + 수정 5)은 계획대로다. 테스트 결과: 백엔드 `test_spec_018.py` 12 passed, 프론트엔드 `usePurchaseOrderQueries.test.tsx` 3 passed + `UnorderedItemsTab.test.tsx` 4 passed(기존 2개 회귀 무손실), 백엔드 전체(`order` + `accounts`, `concurrency` 마커 1건 deselect) 979 passed, 프론트엔드 전체 237 passed. 설계 결정 A~H 모두 구현 확인. `_reorder_candidate_filter` 및 4개 호출부, 쓰기 엔드포인트, 모델 필드 전부 무수정 검증. |
| 1.0.3 | 2026-08-13 | ggajo | **plan-audit 1차 후속**(FAIL, 0.68 — 문서 적합성 판정이며 코드 정확성 문제는 아님). 감사관이 mutation testing으로 인수 기준 4건을 검증한 결과 2건이 **판별력 없음**으로 판명됐다(각 기준이 금지한다고 선언한 잘못된 구현을 실제로 주입해도 통과). **D1 수정**: AC-RESTORE-004/T4는 두 응답의 행 순서가 같은지만 봤는데, 이는 정렬이 결정적이지 않아도 성립한다 — `.order_by()`에서 `"pk"` tie-break를 제거해도 통과했다. `CaptureQueriesContext`로 실제 발행된 ORDER BY 절이 두 개의 키를 담는지 단정하는 (e)를 추가했고, 동일 mutation으로 실패함을 확인했다(test_spec_017.py의 쓰기 범위 단정과 같은 기법). **D4 수정**: acceptance.md의 스코프 선언(:17-19)과 DoD 표(:335)가 T14의 테스트 파일을 `UnorderedItemsTab.test.tsx`로 적었으나 실제 위치는 `usePurchaseOrderQueries.test.tsx`다 — v1.0.1이 기록한 발산의 결과인데 문서가 따라가지 않았다. **기능 결함 1건 수정(감사 부수 발견)**: `UnorderedItemsTab.tsx`의 `isError` 가드가 목록 전환 버튼보다 위에서 탭 전체를 early return 해, 미발주 조회가 실패하면 제외 목록 쿼리가 정상이어도 그 화면에 도달할 수 없었다 — "제외되어 보이지 않는 품목을 보이게 한다"는 이 SPEC의 목적이 옆 쿼리의 실패에 막히는 상태였다. 가드를 제외 뷰 분기 아래로 옮기고 전환 버튼을 유지하도록 고쳤으며, 회귀 테스트 T15를 추가해 구 구현에서 실패함을 mutation으로 확인했다. 감사 결과 중 남긴 것: 인용 약 90건이 전부 실제 위치로 해석되나(허구 0건) 구현 반영으로 최대 +439줄 밀려 있다 — 문서 부채로 남긴다. AC-RESTORE-007의 판별력 부재(상수 쿼리 증가가 양쪽 측정에서 상쇄됨)도 후속 과제로 남긴다. 검증: 백엔드 test_spec_018.py 12 passed, 프론트엔드 전체 238 passed(T15 포함). |

---

## 문제 정의

`LineItem.purchase_status`가 `on_hold`(주문보류) / `order_cancelled`(주문취소) /
`cs_required`(CS필요) / `other_publisher`(타출판사) 중 하나인 품목은 **발주 관련 모든
화면에서 사라진다.**

원인은 공유 필터 하나다. `_reorder_candidate_filter`
(`backend/order/purchase_order_views.py:93`, 본체 `:107-110`)는 `purchase_status="unordered"`
(단, 어떤 `PurchaseOrder`에도 미연결)와 `purchase_status="damaged_exchange"`만 통과시킨다.
이 필터는 4곳에서 공유된다 — `UnorderedItemsView`(`:275`), `RunComparisonView`(`:567`),
`DailyReviewExcelView`(`:1071`), `UploadDailyReviewView`(`:1410`). 즉 한 번 제외 상태가 되면
미발주 목록에서도, Daily Review 엑셀에서도, Daily Review 업로드 매칭에서도 빠진다.

동시에 **그 상태로 만드는 경로는 여러 개다**:
행별 상태 select가 7개 값을 전부 노출하고(`UnorderedItemsTab.tsx:262`,
`purchaseOrderApi.ts:16-25`), 일괄 변경 select는 오히려 `unordered`만 선택지에서
제거한다(`UnorderedItemsTab.tsx:126`). Daily Review 업로드는 '선택' 열 라벨을 상태로 자동
매핑하면서 `LineItemNote`까지 함께 만든다(`excel_utils.py:614-622`,
`purchase_order_views.py:1442`, `:1453-1466`). 들어가는 문은 넓고 나오는 문은 없다.

담당자의 실제 업무 흐름은 이렇다 — 미출간 도서라 `on_hold`로 잡아 둔다 → 나중에 출판사
재고를 직접 확인하고 주문을 넣는다 → **그 시점에 이 품목을 다시 "발주 대상"(`unordered`)으로
되돌려야 한다.** 오늘 이 마지막 단계는 DB를 직접 수정하는 것 외에 방법이 없다.

품목 노트 페이지는 대안이 되지 못한다 — 노트 중심 화면이라 `purchase_status`를 표시하지도
쓰지도 않는다(`serializers.py:79-97`의 필드 목록에 없고, `LineItemNotesPage.tsx`도 이 값을
참조하지 않는다).

규모와 구체 사례는 운영 DB로 확인했다(2026-08-13 측정, `research.md` §1.6): 4개 상태 합계
**225건**(`other_publisher` 80 / `order_cancelled` 79 / `cs_required` 49 / `on_hold` 17).
대표 사례 — `LineItem` id=15083, 주문 `#37636`, sku `9791199783218`,
`purchase_status='order_cancelled'`, `rack_number='M4'`,
`logistics_status='not_shipped'`, `Refund` 0건. 렉번호 M4를 달고 창고에 물리적으로 있으면서도
`LineItemRackNumberSummaryView`(`:2399`)의 `order_cancelled` 제외 때문에 렉번호 요약에서도
사라진 상태다.

## 솔루션 개요

1. **읽기 — 완전히 별개인 신규 조회 경로.** 4개 제외 상태의 LineItem을 반환하는 읽기 전용
   엔드포인트를 신설한다. 공유 필터를 재사용하지도, 확장하지도 않는다. 이 구조는 이
   저장소에 이미 있는 선례를 그대로 따른다 — `OutboundForceCandidateView`의
   docstring(`purchase_order_views.py:2973-2978`)이 "이 뷰는 완전히 별개 코드라서 기존 두
   출고 엔드포인트에 쿼리를 하나도 추가하지 않는다"고 명시한다.
2. **쓰기 — 신규 엔드포인트 없음.** 복구는 이미 존재하는
   `LineItemStatusUpdateView`(`:1863`, PATCH `/line-items/<pk>/status/`)와
   `LineItemBulkStatusUpdateView`(`:1908`, PATCH `/line-items/bulk-status/`)로 수행한다. 두
   엔드포인트 모두 대상 LineItem의 현재 상태에 아무 제약이 없고(`:1878`은 pk로 직접 조회,
   `:1939`는 `pk__in`), `unordered`는 이미 유효한 선택지다(`:1883`). **백엔드 쓰기 능력은
   전부 존재하며 없는 것은 UI 경로뿐이다.**
3. **UI — 미발주 탭 안의 뷰 전환.** 새 페이지·새 탭을 만들지 않는다.
   `UnorderedItemsTab`(`frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`)에
   "보류/제외 품목" 뷰를 추가하고, 그 뷰에서 기존 행별 select(`:255-267`)와 일괄 변경
   컨트롤(`:118-141`)을 재사용하되 `unordered`를 선택 가능하게 만든다.
4. **선택 상태는 뷰 로컬로 분리한다.** 기존 선택은 전역 zustand 스토어의 SKU 배열
   (`usePurchaseOrderStore.ts:5`)이고 발주 파일 생성이 이를 그대로 서버에 보낸다
   (`UnorderedItemsTab.tsx:90`). 보류/제외 뷰의 선택이 이 배열에 섞이면 제외된 품목의 SKU로
   발주 파일이 생성될 수 있다 — 설계 결정 F 참조.
5. **모델·마이그레이션·감사 로그 없음.** 복구는 `purchase_status` 한 필드만 바꾼다.

요구사항 본문(EARS)은 관측 가능한 동작(WHAT)만 규정한다. "설계 결정" 절은 각 판단의 근거가
된 기존 코드·테스트를 `file:line`으로 인용한다 — 구현 지시가 아니라 결정을 검증 가능하게
만드는 증거다. 구현 순서와 파일별 변경 계획은 `plan.md`를, 조사 전문은 `research.md`를
참조한다.

## 범위 — 델타

이 SPEC은 기존 화면 위에 얹는 브라운필드 기능 추가다.

| 마커 | 대상 | 내용 |
|---|---|---|
| [EXISTING] | `_reorder_candidate_filter`(`:93-110`)와 4개 호출부(`:275`, `:567`, `:1071`, `:1410`) | **한 글자도 바꾸지 않는다.** 회귀 확인만 한다(REQ-RESTORE-008/009/010). |
| [EXISTING] | `LineItemStatusUpdateView`(`:1863-1900`), `LineItemBulkStatusUpdateView`(`:1908-1958`) | 코드 변경 없이 그대로 재사용한다(REQ-RESTORE-011). |
| [EXISTING] | `_recompute_order_aggregates`(`:123-195`) | 변경 없음. 두 쓰기 엔드포인트가 이미 호출한다(`:1892`, `:1950`). |
| [EXISTING] | `LineItem` / `LineItemNote` / `Order` 모델 | 신규 필드·마이그레이션 없음. |
| [NEW] | 제외 상태 조회 뷰 (BE) | 4개 상태 LineItem의 읽기 전용 목록. 기존 필터와 쿼리셋을 공유하지 않는다(REQ-RESTORE-001~007). |
| [NEW] | 조회 API 클라이언트 + 쿼리 훅 (FE) | `purchaseOrderApi.ts`에 fetch 함수, `usePurchaseOrderQueries.ts`에 쿼리 키와 훅. |
| [MODIFY] | `UnorderedItemsTab.tsx` | 뷰 전환 컨트롤, 보류/제외 테이블, LineItem id 기반 로컬 선택, `unordered` 포함 일괄 select(REQ-RESTORE-015~020). |
| [MODIFY] | `usePurchaseOrderQueries.ts`의 `useUpdateLineItemStatus`(`:103-115`) / `useBulkUpdateLineItemStatus`(`:119-135`) | 성공 시 신규 쿼리 키도 무효화하도록 `invalidateQueries` 추가(`:109`, `:125` 옆). 그 외 동작 변경 없음. |
| [MODIFY] | `UnorderedItemsTab.test.tsx`(`:13-22`, `:31-57`) | 신규 훅을 `vi.mock` 팩토리와 `beforeEach`에 추가. 누락 시 기존 2개 테스트가 깨진다. |
| [NEW] | `backend/order/tests/test_spec_018.py` | 조회 경로·회귀·집계 재계산·부수효과 테스트. |
| [NEW] | 프론트엔드 테스트 | `UnorderedItemsTab.test.tsx`에 뷰 전환·선택 격리·옵션 노출 시나리오 추가. |

## 설계 결정

### 결정 A — 공유 필터를 넓히지 않고 별도 읽기 경로를 만든다 (핵심 제약)

`_reorder_candidate_filter`(`purchase_order_views.py:93-110`)에 4개 상태를 추가하면
호출부 4곳(`:275`, `:567`, `:1071`, `:1410`)의 동작이 **전부** 바뀐다. 특히 `:1410`은
`UploadDailyReviewView`의 SKU 배치 매칭이라, 필터가 넓어지면 이미 취소된 품목이 Daily Review
업로드로 다시 발주 처리되는 심각한 회귀가 된다.

같은 문제를 이미 이 방식으로 푼 선례가 같은 파일에 있다. `OutboundForceCandidateView`
(`:2963`)의 docstring `:2973-2978`은 "이 뷰는 완전히 별개 코드라서 기존 두 출고
엔드포인트에 쿼리를 하나도 추가하지 않는다(REQ-FORCE-018, 설계 결정 A)"고 명시한다. 이
SPEC은 그 구조를 그대로 따른다.

기각한 대안 — `UnorderedItemsView`에 쿼리 파라미터를 추가해 분기시키는 방식. 필터 자체는
안 넓히지만 `:275`의 호출부에 분기가 들어가 4개 호출부 중 하나의 코드 경로가 바뀌고,
비교적 넓은 회귀 표면(`test_purchase_orders.py:2152-2234`의 5개 테스트)에 위험을 만든다.
별개 뷰는 그 표면을 0으로 만든다.

### 결정 B — 4개 상태는 재발주 큐 밖에 그대로 남는다

이 SPEC은 4개 상태를 **보이게** 만들 뿐 **자격을 주지 않는다**. 배제는 의도된 계약이며
`test_all_non_unordered_statuses_excluded`
(`backend/order/tests/test_purchase_orders.py:2217-2234`)가 5개 상태를 한 번에 고정하고 있다.
복구는 상태를 `unordered`로 바꾼 **결과로** 자격을 얻는 것이지, 제외 상태에 자격을 부여하는
것이 아니다.

### 결정 C — `Order.status`는 불변, `Order.ready_to_ship`은 2개 상태에서만 변한다

복구 시 `_recompute_order_aggregates`가 호출된다(단일 `:1892`, 일괄 `:1950`). 두 집계의
계산 규칙은 다음과 같다.

**`Order.status`(`:167-173`)**: 집합에 넣는 값이 `logistics_status`뿐이다.
`purchase_status`를 무엇으로 바꾸든 결과가 바뀌지 않는다 — **복구는 `Order.status`를 절대
변경하지 않는다.**

**`Order.ready_to_ship`(`:176-185`)**: `order_cancelled`인 LineItem을 집계에서 제외한 뒤
(`:176`), 남은 것이 없으면 `None`(`:177-178`), 하나라도 `cs_required`면 `False`(`:179-180`),
그 외에는 모든 항목이 `logistics_status="received"` 또는 `purchase_status="in_stock"`일
때만 `True`(`:181-185`)다. docstring `:130-136`이 SPEC-ORDER-012 REQ-RTS-002/003/003a/004로
같은 규칙을 명시한다.

| 복구 방향 | `Order.ready_to_ship` |
|---|---|
| `order_cancelled` → `unordered` | **바뀔 수 있다.** 그 품목이 `:176`의 제외에서 빠져나와 집계에 재진입한다. 복구된 품목은 보통 `logistics_status="not_shipped"`(모델 기본값, `models.py:204-208`)이고 `in_stock`도 아니므로 `:182-185`의 `all(...)`이 거짓이 된다 — **`True`였던 Order가 `False`로 뒤집힐 수 있다.** 그 품목이 Order의 유일한 추적 대상이었다면 `None` → `False`. |
| `cs_required` → `unordered` | **바뀔 수 있다.** `:179-180`의 강제 `False` 조건이 사라져 `False` → `True`로 올라갈 수 있다. |
| `on_hold` → `unordered` | **바뀌지 않는다.** 두 규칙 어디에도 등장하지 않는 값이다. |
| `other_publisher` → `unordered` | **바뀌지 않는다.** 위와 동일. |

이는 이 SPEC이 새로 만드는 동작이 아니라 기존 쓰기 엔드포인트가 이미 하는 동작이다. 다만
"보이지 않던 품목을 되살린다"는 성격상 `True` → `False` 뒤집힘은 담당자에게 놀라운
결과이므로 REQ-RESTORE-013과 AC-RESTORE-008/009로 명시적으로 고정한다.

### 결정 D — 환불 넷팅은 렉번호 요약의 가드된 관례를 따른다

두 관례가 공존한다.

- `UnorderedItemsView:293-294` — `net_qty == 0`이면 **무조건** 스킵. 환불이 0건이고
  `quantity`가 NULL/0인 품목도 사라진다.
- `LineItemRackNumberSummaryView:2415` — `if li.refunded_qty and net_qty == 0:`일 때만
  스킵. `:2416-2421`의 주석이 근거를 남긴다: "`refunded_qty`에 가드를 걸어 환불이 없는데
  `quantity`가 NULL/0인 LineItem은 기존 동작(목록에 표시, 0으로 집계)을 유지하게 했다 — 그
  경우는 취소가 아니라 **데이터 결손**이다."

이 SPEC은 **후자(가드된 관례)를 채택한다.** 근거: 이 화면의 존재 이유가 "안 보이는 품목을
보이게 하는 것"인데, 무조건 스킵을 쓰면 `quantity`가 NULL인 데이터 결손 품목이 여기서도
사라져 정확히 같은 문제를 재생산한다. 전량 환불된 품목은 실제로 되살릴 이유가 없으므로 그
경우만 제외한다.

트레이드오프: 전량 환불된 `order_cancelled` 품목은 이 목록에 나타나지 않으므로 UI로 복구할
수 없다. 의도된 것이다 — 환불이 완료된 판매를 재발주 큐에 넣는 것은 오동작이다.

### 결정 E — 복구는 `LineItemNote`를 건드리지 않는다 (트레이드오프 있음)

**권고: 자동 해결하지 않는다.**

근거:

1. **역방향 결합이 코드베이스에 존재하지 않는다.** 상태 → 노트 방향은 있다 —
   `UploadDailyReviewView`(`:1453-1466`)가 상태 변경과 `LineItemNote` 생성을 한
   트랜잭션에서 수행한다. 그러나 `LineItemStatusUpdateView`(`:1876-1900`)와
   `LineItemBulkStatusUpdateView`(`:1922-1958`) 어느 쪽도 `LineItemNote`를 조회·생성·수정하지
   않는다.
2. **범위 침범이 된다.** 그 두 엔드포인트는 기존 미발주 탭 흐름
   (`UnorderedItemsTab.tsx:64-66`, `:132-139`)이 공유한다. 노트 자동 해결을 넣으면 이
   SPEC과 무관한 기존 상태 변경까지 노트를 건드리게 된다.
3. **전용 경로가 이미 있다.** `LineItemNoteResolveView`(`backend/order/views.py:285`, PATCH
   `/api/orders/line-item-notes/{pk}/resolve/`, `urls.py:154`)와 품목 노트 화면이 담당한다.
4. **선례가 일관된다.** `damaged_exchange` → `unordered` 자동 리셋
   (`ConfirmOrderView:975-984`, `UploadDailyReviewView:1568-1569`)도 `purchase_status` 한
   필드만 바꾸고 노트를 건드리지 않는다.

**트레이드오프(명시)**: `research.md` §2.3이 보여주듯 4개 상태 품목 상당수는 Daily Review
업로드가 만든 미해결 `LineItemNote`를 동반한다. 복구해도 그 노트는 미해결로 남아 미해결
노트 목록(`views.py:269`)과 타출판사 엑셀 내보내기(`views.py:313-317`)에 계속 나타난다.
담당자가 노트를 따로 해결해야 하는 이중 작업이 남는다. 이를 인지한 채로 범위 밖에 두며
"후속 과제 1"로 등록한다.

### 결정 F — 보류/제외 뷰의 선택은 LineItem id 기반 뷰 로컬 state다

기존 선택 상태는 전역 zustand 스토어의 **SKU 문자열 배열**이다
(`usePurchaseOrderStore.ts:5`, 주석 `:4`가 "SKUs selected (checked) in UnorderedItemsTab"로
용도를 못박는다). `@MX:ANCHOR`/`@MX:REASON`(`:12-13`)은 `UnorderedItemsTab`과
`VendorFileUploadTab`이 이 스토어를 공유한다고 기록한다.

두 가지 문제가 있다.

1. **선택 키가 SKU다.** `UnorderedItemsTab.tsx:224`/`:230`이 `toggleSku(item.sku)`를
   호출하고 `:69-72`가 선택된 SKU를 LineItem id로 되매핑한다. 미발주 목록에서는 같은 SKU가
   전부 `unordered`이므로 무해하지만, 보류/제외 목록에서는 같은 SKU가 서로 다른 주문에 서로
   다른 상태로 존재할 수 있어(225건 규모에서 충분히 가능) SKU 하나를 체크하면 의도치 않은
   행까지 함께 복구된다.
2. **스토어가 전역이다.** `:90`의 발주 파일 생성이 `selectedSkus`를 **그대로** 서버에
   보낸다(`generateOrderFile({ distributor, skus: selectedSkus })`). 보류 품목을 선택한 채
   뷰를 전환하면 제외된 품목의 SKU로 발주 파일이 만들어질 수 있다.

따라서 보류/제외 뷰는 **LineItem id 집합을 뷰 로컬 state로** 관리하며 전역 스토어를
건드리지 않는다(REQ-RESTORE-018). 기존 일괄 엔드포인트가 이미 `{"ids": [...]}`를
받으므로(`:1923`) 백엔드 변경은 필요 없다.

### 결정 G — 페이지네이션하지 않는다

`UnorderedItemsView`의 응답은 `:314`의
`Response({"count": len(results), "results": results})`다 — DRF 페이지네이션을 거치지 않고
봉투를 직접 만들며 `next`/`previous` 키가 없다. 파일 안에서 `PageNumberPagination`을 상속하는
클래스는 `PurchaseOrderPagination`(`:3428-3429`, `page_size = 50`) 하나뿐이고 그것은
`PurchaseOrderListView`(`:3503`)의 PurchaseOrder 목록 전용이다. 프론트엔드에서도
`PaginatedResponse<T>`(`purchaseOrderApi.ts:61-66`)는 `getPurchaseOrders`(`:158-170`)에만
쓰이며 `getUnorderedItems`(`:90-93`)의 반환 타입은 `{ count, results }`다.

즉 **LineItem 목록 계열 읽기 엔드포인트의 이 저장소 관례는 비페이지네이션이다.** 신규 뷰는
그 관례를 그대로 따른다. 규모 근거: 2026-08-13 운영 DB 실측 4개 상태 합계 225건
(`research.md` §1.6)으로, 미발주 목록이 이미 감당하는 규모와 같은 자릿수다. 이 SPEC은
페이지네이션 관례를 새로 발명하지 않는다.

### 결정 H — 정렬은 미발주 목록의 정렬 키에 결정적 tie-break를 더한다

`UnorderedItemsView:283`은 `.order_by("-order__shopify_created_at")` 단일 키라 동률 시 순서가
비결정적이다. 같은 파일의 더 신중한 관례는 명시적 tie-break를 둔다 —
`OutboundForceCandidateView:3011`의 `.order_by("order_id", "pk")`에는 `:3003-3006`의 근거
주석이 붙어 있다("결정적이고 반복 가능한 순서를 주며 MySQL의 무정렬 스캔 반환 순서에
의존하지 않는다"). `LineItemRackNumberSummaryView:2407`도 2개 키로 정렬한다.

신규 뷰는 `-order__shopify_created_at`(담당자에게 익숙한 최신순)에 `pk` tie-break를 더한다.

### 결정 I — 서버측 상태 필터 파라미터를 두지 않는다

4개 상태를 항상 전부 반환한다. 근거: (a) 응답에 `purchase_status`가 이미 들어 있어
클라이언트가 필터링할 수 있고, (b) 실측 225건 규모에서 서버 왕복을 늘릴 이유가 없으며,
(c) 파라미터를 추가하면 조합별 인수 기준이 늘어나 이 SPEC의 핵심(복구 경로 신설)을 희석한다.

---

## 요구사항 (EARS)

요구사항은 5개 모듈, REQ-RESTORE-001부터 REQ-RESTORE-022까지 연속 번호로 구성된다.

### 모듈 1 — 제외 상태 조회 경로 (신규, 읽기 전용)

**REQ-RESTORE-001** (Ubiquitous): The system shall provide a read-only endpoint that returns
the LineItems whose `purchase_status` is one of `on_hold`, `order_cancelled`, `cs_required`,
or `other_publisher`. The endpoint shall perform no write of any kind — no LineItem, Order,
PurchaseOrder, or LineItemNote row shall be created, modified, or deleted as a result of
calling it.

**REQ-RESTORE-002** (Ubiquitous): The system shall exclude from that endpoint's response any
LineItem whose `purchase_status` is not one of the four listed states — in particular
`unordered`, `in_stock`, and `damaged_exchange` items shall never appear in it.

**REQ-RESTORE-003** (Ubiquitous): For each returned item the system shall include at minimum
the LineItem identifier, the parent order's display name, the SKU, the title, the vendor, the
remaining quantity, and the item's current `purchase_status`, so that the existing purchase
table UI can render the row and the existing bulk status endpoint can be addressed by
identifier without a further lookup.

**REQ-RESTORE-004** (Unwanted): If a LineItem has no SKU, then the system shall not include it
in the response.

**REQ-RESTORE-005** (State-Driven): While refunds are recorded against a returned LineItem,
the system shall report its remaining quantity net of those refunds rather than the ordered
quantity, and shall omit the item entirely when refunds have reduced that remaining quantity
to zero. A LineItem with no refunds shall be listed regardless of its ordered quantity,
including when that quantity is absent or zero.

**REQ-RESTORE-006** (Ubiquitous): The system shall return the entire matching set in one
unpaginated response carrying a total count and a results array, with no page cursor of any
kind, matching the response envelope the existing unordered-items endpoint returns.

**REQ-RESTORE-007** (Ubiquitous): The system shall return the results in a deterministic,
repeatable order that does not depend on the database's unordered-scan return order.

**REQ-RESTORE-008** (Unwanted): If the request to that endpoint is unauthenticated, then the
system shall reject it with HTTP 401 and shall return no item data.

### 모듈 2 — 기존 재발주 경로 불변 (회귀 방지)

**REQ-RESTORE-009** (Ubiquitous): The system shall leave the shared reorder-candidate
eligibility rule unchanged — LineItems in the four excluded states shall continue to be absent
from the reorder queue, from the daily-review export, and from the vendor-comparison run.

**REQ-RESTORE-010** (Unwanted): If an uploaded daily-review row names a SKU whose only
LineItems are in one of the four excluded states, then the system shall continue not to match
that row, exactly as it does today.

**REQ-RESTORE-011** (Ubiquitous): The system shall implement the new read path as code that is
separate from every existing endpoint, so that no existing endpoint issues a different number
of database queries or returns a different response as a result of this SPEC.

### 모듈 3 — 복구 쓰기 경로 (기존 엔드포인트 재사용)

**REQ-RESTORE-012** (Ubiquitous): The system shall perform every restore through the
already-existing single-item and bulk `purchase_status` update endpoints, and shall introduce
no additional write endpoint for this purpose.

**REQ-RESTORE-013** (Event-Driven): When an operator restores a LineItem from any of the four
excluded states to `unordered`, the system shall persist only that LineItem's
`purchase_status` field — no other LineItem field shall change.

**REQ-RESTORE-014** (Event-Driven): When a restore is persisted, the system shall recompute the
parent Order's aggregate status and ready-to-ship flag within the same request. The aggregate
status shall be unchanged by the restore, because it is derived solely from logistics state.
The ready-to-ship flag shall be recomputed to reflect the restored item's re-entry into the
aggregate when the item was previously `order_cancelled`, and to reflect the removal of the
CS-blocked condition when the item was previously `cs_required`; a restore from `on_hold` or
`other_publisher` shall leave the ready-to-ship flag's value unchanged.

**REQ-RESTORE-015** (Unwanted): If a restore is performed, then the system shall not create,
modify, resolve, or delete any LineItemNote attached to the restored LineItem.

### 모듈 4 — 미발주 탭의 보류/제외 뷰

**REQ-RESTORE-016** (Ubiquitous): The purchase-management unordered tab shall offer a control
that switches between the existing unordered list and a excluded-items list, without navigating
away from the tab. The unordered list shall remain the view shown when the tab is first
opened.

**REQ-RESTORE-017** (State-Driven): While the excluded-items view is displayed, the interface
shall show each item's current purchase-status label, so the operator can tell why the item is
excluded before acting on it.

**REQ-RESTORE-018** (State-Driven): While the excluded-items view is displayed, the interface
shall offer `unordered` as a selectable target in both the per-row status control and the bulk
status control. The bulk control's existing removal of `unordered` from its options shall not
apply in this view.

**REQ-RESTORE-019** (Ubiquitous): The excluded-items view shall track its row selection by
LineItem identifier in state local to that view, and shall not read from or write to the shared
SKU-keyed selection that the unordered view uses for order-file generation. Switching between
the two views shall not carry a selection from one into the other.

**REQ-RESTORE-020** (Unwanted): If the excluded-items view is displayed, then the order-file
generation controls shall not act on the items selected in it.

**REQ-RESTORE-021** (Event-Driven): When a restore performed from the excluded-items view
succeeds, the interface shall refresh both the excluded-items list and the unordered list, so
that the restored item leaves the former without a manual page reload.

### 모듈 5 — 알려진 한계와 비범위 불변식

**REQ-RESTORE-022** (Unwanted): If a restored LineItem is linked to at least one PurchaseOrder,
then it shall remain outside the reorder queue after the restore — this SPEC shall add no
bypass, no alternative status value, and no filter change for that case.

**REQ-RESTORE-023** (Unwanted): If this SPEC is implemented, then no new model field, database
migration, or audit-log table shall be introduced.

---

## ACCEPTANCE CRITERIA

각 인수 기준은 대응 요구사항이 이미 말한 내용을 되풀이하지 않고 구체적 픽스처·경계값으로
관측 가능한 결과를 제시한다. 실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있으며
동일한 `Traces:` 목록을 인용한다.

**AC-RESTORE-001** (Event-Driven) — Traces: REQ-RESTORE-001, REQ-RESTORE-002. When one LineItem
exists in each of the seven `purchase_status` values under a single Order and an authenticated
operator requests the excluded-items list, the system shall return exactly the four items whose
status is `on_hold`, `order_cancelled`, `cs_required`, or `other_publisher`, and shall return
neither the `unordered`, the `in_stock`, nor the `damaged_exchange` item. A snapshot of every
LineItem row taken before and after the request shall be identical.

**AC-RESTORE-002** (Unwanted) — Traces: REQ-RESTORE-004. If an `on_hold` LineItem has a null
SKU, then the system shall omit it from the excluded-items list while still returning a
sibling `on_hold` LineItem that has a SKU.

**AC-RESTORE-003** (State-Driven) — Traces: REQ-RESTORE-005. While three `order_cancelled`
LineItems exist under one Order — the first with quantity 5 and refunds totalling 2, the second
with quantity 3 and refunds totalling 3, the third with a null quantity and no refunds — the
system shall return the first with a remaining quantity of 3, shall omit the second entirely,
and shall still return the third.

**AC-RESTORE-004** (Ubiquitous) — Traces: REQ-RESTORE-003, REQ-RESTORE-006, REQ-RESTORE-007.
Given 12 excluded LineItems spread across Orders with distinct creation timestamps, the
response body shall carry a count equal to the number of returned rows and no page-cursor key
of any kind; every returned row shall carry the LineItem identifier, order display name, SKU,
title, vendor, remaining quantity, and `purchase_status`; and two consecutive identical
requests shall return the rows in the identical order, including for two items whose Orders
share the same creation timestamp.

**AC-RESTORE-005** (Unwanted) — Traces: REQ-RESTORE-008. If an unauthenticated client requests
the excluded-items list while excluded items exist, then the system shall respond 401 and the
response body shall contain no SKU, title, or identifier of any LineItem.

**AC-RESTORE-006** (Ubiquitous) — Traces: REQ-RESTORE-009, REQ-RESTORE-010. Given one
`unordered` LineItem for SKU A and one LineItem in each of the four excluded states for SKUs
B/C/D/E, the unordered-items endpoint shall return SKU A and none of B/C/D/E, and a daily-review
upload naming SKUs B through E shall report every one of them as skipped and shall leave their
`purchase_status` values untouched.

**AC-RESTORE-007** (Ubiquitous) — Traces: REQ-RESTORE-011. With the same fixture in place, the
number of database queries the unordered-items endpoint issues shall be identical whether or
not excluded LineItems exist in the database, and the new read view shall not appear in the
call graph of any pre-existing endpoint.

**AC-RESTORE-008** (Event-Driven) — Traces: REQ-RESTORE-014. When an Order holds two LineItems
— one with `logistics_status="received"` and `purchase_status="unordered"`, one with
`purchase_status="order_cancelled"` and `logistics_status="not_shipped"` — so that its
ready-to-ship flag currently reads true, and the second item is restored to `unordered` through
the single-item status endpoint, the system shall recompute the Order's ready-to-ship flag to
false and shall leave the Order's aggregate status at the value it held before the restore.

**AC-RESTORE-009** (Event-Driven) — Traces: REQ-RESTORE-014. When an Order holds one
`logistics_status="received"` LineItem in `on_hold` and that item is restored to `unordered`,
the Order's ready-to-ship flag and aggregate status shall both hold the same values after the
restore as before it; and when a second Order holds one `received` LineItem in `cs_required`
alongside one `received` `unordered` LineItem, restoring the `cs_required` item to `unordered`
shall move that Order's ready-to-ship flag from false to true.

**AC-RESTORE-010** (Ubiquitous) — Traces: REQ-RESTORE-012, REQ-RESTORE-013, REQ-RESTORE-015.
Given an `on_hold` LineItem carrying a non-empty `rack_number`, a non-null
`confirmed_distributor`, a `logistics_status` other than the default, and one unresolved
LineItemNote, restoring it to `unordered` through each of the two existing status endpoints in
turn shall change only its `purchase_status`; every other LineItem field shall hold its
pre-restore value, the LineItemNote count for that item shall be unchanged, and that note's
resolved flag shall still read false.

**AC-RESTORE-011** (Unwanted) — Traces: REQ-RESTORE-022. If an `order_cancelled` LineItem is
linked to an existing PurchaseOrder and is then restored to `unordered`, then it shall appear
in neither the unordered-items list nor the excluded-items list afterwards, and no code path
introduced by this SPEC shall alter that outcome.

**AC-RESTORE-012** (State-Driven) `[FE]` — Traces: REQ-RESTORE-016, REQ-RESTORE-017,
REQ-RESTORE-018. While the tab is first rendered the unordered list shall be shown; after the
operator activates the excluded-items view, each rendered row shall display its purchase-status
label, the per-row status control shall contain an `unordered` option, and the bulk status
control shall contain an `unordered` option — whereas in the unordered view the bulk control
shall continue not to offer `unordered`.

**AC-RESTORE-013** (State-Driven) `[FE]` — Traces: REQ-RESTORE-019, REQ-RESTORE-020. While the
excluded-items view is displayed and the operator selects two rows that share one SKU but
belong to different Orders, the bulk restore shall address exactly those two LineItem
identifiers; the shared SKU-keyed selection shall remain untouched throughout; and after
switching back to the unordered view the order-file generation control shall behave as if no
excluded row had ever been selected.

**AC-RESTORE-014** (Event-Driven) `[FE]` — Traces: REQ-RESTORE-021. When a restore initiated
from the excluded-items view resolves successfully, both the excluded-items query and the
unordered query shall be invalidated, so that a stale excluded-items list cannot keep showing
the restored row.

### Traceability 검증표

| REQ | 커버하는 AC | 레이어 |
|---|---|---|
| REQ-RESTORE-001 | AC-RESTORE-001 | `[BE]` |
| REQ-RESTORE-002 | AC-RESTORE-001 | `[BE]` |
| REQ-RESTORE-003 | AC-RESTORE-004 | `[BE]` |
| REQ-RESTORE-004 | AC-RESTORE-002 | `[BE]` |
| REQ-RESTORE-005 | AC-RESTORE-003 | `[BE]` |
| REQ-RESTORE-006 | AC-RESTORE-004 | `[BE]` |
| REQ-RESTORE-007 | AC-RESTORE-004 | `[BE]` |
| REQ-RESTORE-008 | AC-RESTORE-005 | `[BE]` |
| REQ-RESTORE-009 | AC-RESTORE-006 | `[BE]` |
| REQ-RESTORE-010 | AC-RESTORE-006 | `[BE]` |
| REQ-RESTORE-011 | AC-RESTORE-007 | `[BE]` |
| REQ-RESTORE-012 | AC-RESTORE-010 | `[BE]` |
| REQ-RESTORE-013 | AC-RESTORE-010 | `[BE]` |
| REQ-RESTORE-014 | AC-RESTORE-008, AC-RESTORE-009 | `[BE]` |
| REQ-RESTORE-015 | AC-RESTORE-010 | `[BE]` |
| REQ-RESTORE-016 | AC-RESTORE-012 | `[FE]` |
| REQ-RESTORE-017 | AC-RESTORE-012 | `[FE]` |
| REQ-RESTORE-018 | AC-RESTORE-012 | `[FE]` |
| REQ-RESTORE-019 | AC-RESTORE-013 | `[FE]` |
| REQ-RESTORE-020 | AC-RESTORE-013 | `[FE]` |
| REQ-RESTORE-021 | AC-RESTORE-014 | `[FE]` |
| REQ-RESTORE-022 | AC-RESTORE-011 | `[BE]` |
| REQ-RESTORE-023 | (DoD 게이트로 검증 — `plan.md` 완료 조건의 마이그레이션 부재 확인) | `[BE]` |

23개 요구사항이 14개 인수 기준으로 커버된다. REQ-RESTORE-023은 부재를 요구하는 메타
요구사항이라 시나리오가 아니라 완료 조건 게이트로 검증한다.

---

## Implementation Notes

### 주요 구현 선택사항

1. **신규 뷰의 위치** — 백엔드 새 `ExcludedItemsView`는 `purchase_order_views.py` 중 `UnorderedItemsView` 바로 뒤인 line 350 이후에 배치됨. 이 위치는 같은 클래스 내 뷰들의 논리적 연관성을 반영한 것으로, 두 뷰 모두 읽기 전용 교차 주문 조회이기 때문.

2. **프론트엔드 훅 테스트 분리** — AC-RESTORE-014(invalidateQueries 검증)의 테스트는 원래 계획(plan.md M6)과 달리 `UnorderedItemsTab.test.tsx`가 아니라 신규 파일 `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`에 작성됨. 이유는 `UnorderedItemsTab.test.tsx`의 `vi.mock('@/hooks/usePurchaseOrderQueries')`가 훅 모듈 전체를 목업하므로, 실제 `QueryClientProvider` + `invalidateQueries` spy 검증이 그 파일 내에서 불가능하기 때문. 대신 훅 전용 통합 테스트를 별도 파일에서 수행함으로써 AC의 "두 훅을 실제 QueryClientProvider 안에서 렌더링" 요구사항을 정확히 충족함. 선례는 같은 조회 훅 테스트 구조(useOutboundQueries.test.tsx).

3. **동시성 작업 트리 오염** — 구현 시점에 `purchase_order_views.py`가 선행 SPEC-ORDER-016의 영향으로 약 33줄 이동되어 있었음. research.md의 line 인용과 구현 코드의 실제 위치가 불일치했으나, **코드 내용 자체는 전부 일치**했으므로 설계 판단에 영향 없음. 후속 문서 동기화 시 절대 좌표가 아닌 기능 영역으로 참조하는 방식 권장.

4. **환불 넷팅 가드 선택** — 신규 뷰의 환불 처리는 `LineItemRackNumberSummaryView`의 가드된 형태(`if li.refunded_qty and net_qty == 0: continue`)를 따름. 이는 `UnorderedItemsView`의 무조건 스킵(`if net_qty == 0: continue`)과 달라, 미환불 null/0 수량 행을 유지하는 설계 결정 D를 구현함.

5. **선택 상태 격리 구현** — 제외 뷰의 LineItem 선택은 `React.useState<Set<number>>`로 로컬 관리되며, 전역 SKU 배열(`usePurchaseOrderStore`)과 완전히 분리됨. 이는 설계 결정 F(SKU 기반 선택의 모호함 회피)를 정확히 구현한 것으로, 제외 뷰와 미발주 뷰의 선택이 독립적으로 작동함을 보장.

### 알려진 한계 및 후속 과제

1. **복구와 미해결 노트의 연결** (설계 결정 E) — 복구 후에도 관련 `LineItemNote`가 자동 해결되지 않음. 미해결 노트가 계속 노트 페이지와 타출판사 엑셀에 나타나므로, 담당자의 작업 흐름상 별도 해결 단계가 필요한 상태 유지.

2. **PurchaseOrder 연결 품목의 처리** (REQ-RESTORE-022의 한계) — 발주 확정 후 취소된 품목은 `unordered`로 복구해도 미발주 목록에 나타나지 않음. `_reorder_candidate_filter`의 `.exclude(purchase_orders__isnull=False)` 때문이며, 이는 이 SPEC의 의도적 제외 대상(설계 결정 A).

3. **렉번호 요약의 `order_cancelled` 제외** (후속 과제 3) — 문제 정의의 대표 사례(LineItem id=15083)처럼 물리적으로 창고에 있는데 렉번호 요약에서 사라지는 품목이 존재. 창고 관점과 발주 관점의 제외 규칙 통일 필요.

---

## Exclusions (What NOT to Build)

- **`_reorder_candidate_filter`(`purchase_order_views.py:93-110`) 수정 없음.** 4개 상태에
  재발주 자격을 부여하지 않는다. 4개 호출부(`:275`, `:567`, `:1071`, `:1410`)도 무수정.
- **신규 쓰기 엔드포인트 없음.** 기존 `LineItemStatusUpdateView`(`:1863`)와
  `LineItemBulkStatusUpdateView`(`:1908`)만 사용한다.
- **모델 변경·마이그레이션 없음.** 신규 `purchase_status` 값도 추가하지 않는다
  (`models.py:156-167`의 7개 값 유지).
- **감사 로그 테이블·이력 필드 없음.** 누가 언제 무엇을 복구했는지 기록하지 않는다.
- **`LineItemNote` 자동 생성·자동 해결 없음** (설계 결정 E).
- **신규 페이지·신규 탭 없음.** `PurchaseOrders/index.tsx:23-31`의 `TABS` 배열은
  수정하지 않는다.
- **서버측 상태 필터 쿼리 파라미터 없음** (설계 결정 I).
- **페이지네이션 없음** (설계 결정 G).
- **`PURCHASE_STATUS_OPTIONS`(`purchaseOrderApi.ts:16-25`) 수정 없음.** 옵션 목록의 내용이
  아니라 그것을 어떻게 필터링해 렌더링하는지만 바뀐다.
- **`usePurchaseOrderStore`(`usePurchaseOrderStore.ts:1-28`) 수정 없음** (설계 결정 F).
- **`LineItemRackNumberSummaryView`(`:2365`)의 `order_cancelled` 제외(`:2399`) 수정 없음.**
  렉번호 요약에 취소 품목을 되살리는 것은 별개 문제다(후속 과제 3).
- **`ConfirmOrderTab` / `LineItemNotesPage` / `OutboundPage` 변경 없음.**
- **일괄 복구의 부분 실패 UX 개선 없음.** 기존 `missing_ids` toast 처리
  (`usePurchaseOrderQueries.ts:126-130`)를 그대로 쓴다.
- **엑셀 업로드 기반 일괄 복구 없음.** 화면 조작만 지원한다.

## 후속 과제

1. **복구와 `LineItemNote` 해결의 연결** (설계 결정 E의 트레이드오프). 복구 후에도 미해결
   노트가 남아 미해결 노트 목록(`views.py:269`)과 타출판사 엑셀(`views.py:313-317`)에 계속
   나타난다. 복구 UI에서 관련 노트를 함께 해결할지, 별도 화면에서 처리할지 결정이 필요하다.
2. **PurchaseOrder에 연결된 품목의 복구** (REQ-RESTORE-022의 한계). 발주 확정 후 취소된
   품목은 `unordered`로 복구해도 미발주 목록에 나타나지 않는다
   (`test_purchase_orders.py:2197-2215`가 고정하는 동작). `damaged_exchange`가 쓴 우회
   (`models.py:163-166`, `purchase_order_views.py:108`)가 참고 선례지만 의미가 다르므로 별도
   설계가 필요하다.
3. **렉번호 요약의 `order_cancelled` 제외 재검토.** 문제 정의의 대표 사례(id=15083,
   `rack_number='M4'`)처럼 물리적으로 창고에 있는데 요약에서 사라지는 품목이 있다
   (`purchase_order_views.py:2399`). 창고 관점과 발주 관점의 제외 규칙이 같아야 하는지
   재검토가 필요하다.
4. **복구 이력 추적.** 감사 로그가 없어 누가 언제 어떤 근거로 복구했는지 남지 않는다. 필요해지면
   `LineItemNote`를 이력 매체로 쓸지, 전용 테이블을 둘지 결정한다.
5. **`UnorderedItemsView` 선택 모델의 SKU → LineItem id 통일.** 설계 결정 F가 지적한 SKU
   기반 선택의 애매함은 미발주 목록에도 잠재적으로 존재한다(같은 SKU가 여러 주문에 걸칠 때
   수량 합산은 맞지만 행 단위 의도는 흐려진다). 이 SPEC은 신규 뷰만 id 기반으로 만들고 기존
   뷰는 건드리지 않는다.

## 관련 SPEC

- **SPEC-PURCHASE-ORDER-010** — `damaged_exchange` 상태 도입. "제외 상태를 재발주 큐로
  되돌리는" 문제를 신규 상태값 + 필터 확장으로 푼 선례(`models.py:163-166`,
  `purchase_order_views.py:108`). 이 SPEC은 그 접근을 의도적으로 채택하지 않는다(설계 결정 A/B).
- **SPEC-ORDER-012** — `Order.ready_to_ship` 집계 규칙. 설계 결정 C의 계산 근거
  (`purchase_order_views.py:130-136`, `:176-185`).
- **SPEC-ORDER-014** — `LineItemRackNumberSummaryView`. 교차 주문 읽기 전용 뷰의 구조적
  선례이자 가드된 환불 넷팅 관례의 출처(`:2415-2421`, 설계 결정 D).
- **SPEC-ORDER-016** — `OutboundForceCandidateView`. "기존 경로를 넓히지 않고 완전히 별개인
  읽기 경로를 신설한다"는 아키텍처 선례(`:2963`, docstring `:2973-2978`, 설계 결정 A).
  또한 그 SPEC의 v1.0.5 HISTORY가 기록한 허구 인용 사고가 이 SPEC의 인용 전량 재검증 방침의
  직접적 계기다.
- **SPEC-PURCHASE-ORDER-004** — `LineItemBulkStatusUpdateView` 도입(`urls.py:72` 주석의
  경로 순서 제약 포함).
- **SPEC-ORDER-010** — `LineItemNote` 도입 및 해결 경로(`backend/order/views.py:251-296`).
