---
id: SPEC-PURCHASE-ORDER-011
version: 1.3.1
status: draft
created_at: 2026-08-14
updated: 2026-08-14
author: ggajo
priority: High
issue_number: 29
labels: [purchase-order, damaged-exchange, reorder-queue, frontend]
---

# 파손 교환 신청 페이지

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-14 | ggajo | 최초 작성 — 3라운드 사용자 인터뷰로 확정된 요구사항(R1~R5)을 EARS 형식으로 formalize. 코드베이스 직접 확인(`backend/order/models.py`, `backend/order/purchase_order_views.py`, `backend/order/urls.py`, `backend/order/excel_utils.py`, `frontend/src/services/purchaseOrderApi.ts`, `frontend/src/components/Sidebar.tsx`, `frontend/src/router/index.tsx`) 완료. |
| 1.1.0 | 2026-08-14 | ggajo | 사용자가 초안 완료 요약의 열린 질문 중 결정 B("전체 출고 수량" 합산 범위)를 확정 — 취소·미추적 행을 제외하고 합산하도록 정정, `_recompute_order_aggregates`가 이미 사용하는 "추적 가능(trackable)" 관례와 정합시킴. REQ-DEX-006 갱신 + REQ-DEX-006b 신설, AC-DEX-005/AC-DEX-005b 갱신·신설. 결정 A(환불 차감 적용)와 결정 D(`author=request.user`)는 그대로 확정. |
| 1.2.0 | 2026-08-14 | ggajo | plan-auditor 리뷰(iteration 1, FAIL, 0.52) 반영. **D1(critical, 사용자 결정으로 요구사항 자체를 변경)**: `logistics_status`를 건드리지 않으므로 파손 접수 후에도 `ready_to_ship`이 `True`로 남는 실제 결함을 확인(`purchase_order_views.py:182-185`) — 사용자가 테스트가 아니라 `_recompute_order_aggregates`의 집계 규칙을 고치기로 결정. 신규 REQ-DEX-009c([MODIFY], `damaged_exchange`를 기존 `cs_required`와 동일하게 단락 처리해 `ready_to_ship=False`)·REQ-DEX-009d(`Order.status`는 불변) 추가, 신규 결정 E(공유 함수 fan-in 8→9 확장, 다운스트림 소비자 전수 명시, 특성화 테스트 요구)를 설계 결정에 추가. AC-DEX-009 재작성(잘못된 근거 서술 삭제, 올바른 이유로 교체) + 신규 AC-DEX-009c(집계 규칙 자체의 단위 수준 검증) 추가 — `_recompute_order_aggregates` 미호출과 미수정 양쪽 모두를 잡아내는 판별력 확보. **D3(major)**: `plan.md`/`spec.md`가 5개 조회 지점이 모두 동일한 `quantity - refunded_qty` 패턴을 쓴다고 주장한 것이 사실과 다름을 직접 재확인(`UploadDailyReviewView`는 환불 항을 아예 갖지 않고, `ConfirmOrderView`는 `LineItem.quantity`를 전혀 읽지 않고 요청 바디값을 사용) — REQ-DEX-012b를 정확한 5개 지점(`RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView`)으로 재작성하고, `ConfirmOrderView`는 구조적으로 다른 이유(quantity 자체를 안 읽음)로 별도의 신규 REQ-DEX-012c로 분리. **D11(minor, D3와 동일 조사에서 발견)**: `VendorComparisonView`(L744-757)가 원래 열거에서 누락되었던 6번째 재발주 후보 조회 지점임을 확인, REQ-DEX-012b/Exclusions에 추가하고 AC-DEX-012d(5개 중 2개만 커버)를 4개 전량 커버로 확장 + 신규 AC-DEX-012e(VendorComparisonView) 추가. **D4(major)**: AC-DEX-012b/시나리오 12c에 `quantity` 값이 명시되지 않아 무수정 구현과 구분되지 않던 결함을 `quantity=10`(vs `damaged_quantity=1`) 명시로 수정, 시나리오 6/12/12b/12c에 `sku` not null 명시 추가. **D5(major)**: 이미 `damaged_exchange`인 행에 대한 재접수 시맨틱 미정의 — 사용자가 덮어쓰기(overwrite)로 확정, 신규 REQ-DEX-009b + AC-DEX-009b 추가. **D6(major)**: 결정 D(`author=request.user`)에 대응하는 REQ/AC가 없던 결함 — REQ-DEX-010에 `author` 절 추가, AC-DEX-010 갱신. **MP-2(EARS 형식 위반)**: `(Unwanted)` 라벨을 달았으나 If-트리거가 없거나 주어가 "the system"이 아니었던 4건(REQ-DEX-006a/011/012a/012b)을 순수 If/then·시스템 주어 형태로 재작성. spec.md ACCEPTANCE CRITERIA 섹션 전 항목에서 "Given...when...the system shall" 하이브리드 구문을 제거하고 순수 트리거-응답 EARS 산문으로 재작성(SPEC-PURCHASE-ORDER-010 v1.2.0에서 확립된 동일 수정 관례를 따름). **MP-3**: frontmatter `created:` → `created_at:`로 리네임(프로젝트 전역 관례 정합). **D7/D8/D9/D10/D12(minor)**: "전체 출고 수량" 라벨이 `LineItem.shipped_quantity`와 무관함을 REQ-DEX-006에 명시, AC-DEX-002를 SPEC-ORDER-015 선례 수준의 검증 가능한 문구로 축소, AC-DEX-006의 존재하지 않는 "REQ-DEX-006a's rule" 참조를 `_recompute_order_aggregates`/SPEC-ORDER-012 REQ-RTS-002로 정정, AC-DEX-005a의 자기모순 전제("추적 가능한 LineItem이 하나도 없는 상태") 삭제, DoD에 결정 D 확인 항목 추가. 부가로 AC-DEX-008의 "client-side 또는 server-side" 문구를 server-side 필수로 강화하고, null-quantity→0 처리에 대한 AC-DEX-005c를 신설. 모듈 수는 "파손 신고 제출" 섹션에 Order 집계 영향(REQ-DEX-009b~009d)을 편입해 5개 이하를 유지. REQ: 기본 계열 001~012(12개, 결번 없음, 불변) + 접미사 10개(005a/006a/006b/009a/009b/009c/009d/012a/012b/012c) = 총 18개 항목 → 22개 항목으로 증가(신규 009b/009c/009d/012c 4건). AC: 20개 → 25개 항목으로 증가(신규 005c/009b/009c/012e/012f 5건). `issue_number: 0`은 원 지시(발급 전 플레이스홀더)에 따라 변경하지 않음. |
| 1.3.0 | 2026-08-14 | ggajo | plan-auditor 리뷰(iteration 2, FAIL, 0.69) 반영 — 이전 12개 결함은 전량 재확인 해결(RESOLVED), 이번 실패는 v1.2.0이 새로 확장한 범위에서 발생. **D13(blocking, major)**: `ready_to_ship` 규칙을 바꾸면서도 기존 Order를 백필하는 요구사항이 없어, REQ-DEX-006a가 새 페이지의 재계산을 금지하는 것과 결합하면 이 SPEC이 없애려는 바로 그 증상(파손 접수 후에도 `ready_to_ship=True` 잔존)이 기존 파손 Order에는 영구히 남는 결함을 확인 — `backend/order/migrations/0033_backfill_order_ready_to_ship.py`(SPEC-ORDER-012 REQ-RTS-006)를 선례로 직접 읽고 확인. 신규 REQ-DEX-013([NEW], 1회성 백필 마이그레이션) + REQ-DEX-013a(다른 Order 불변) + AC-DEX-013/013a + 결정 F 추가. **D14(blocking, major)**: AC-DEX-009c 픽스처가 `damaged_exchange` 행의 `logistics_status`를 고정하지 않아(acceptance.md는 `"not_shipped"`로 고정) 신규 단락 없이도 `all(...)`이 이미 `False`가 되어 판별력이 0임을 확인 — `damaged_exchange` 행을 `logistics_status="received"`로 고정해 무수정 규칙은 `True`, 수정된 규칙은 `False`가 되도록 양쪽 문서 모두 재작성. **D20(blocking, major)**: AC-DEX-005c 픽스처(null 1건 + 9 1건)가 SQL `SUM`이 NULL을 무시해 `Coalesce` 없는 구현에서도 `9`를 반환함을 확인(판별력 없음) — 추적 가능·비취소 LineItem 전원이 `quantity=null`인 픽스처로 교체, 기대값 `0`(무수정 시 `null`/`None`). 판별력 없는 mixed-null 보조 주장은 제거. **D21(blocking, major)**: `VendorComparisonView`(L744-750)가 `damaged_exchange` 링크 예외를 갖지 않고, `purchase_order_views.py:373-381`이 "파손 품목은 현실적으로 원 PurchaseOrder에 연결된 채로 남는다"를 기록하고 있음을 확인 — AC-DEX-012e/시나리오 12f가 PO 링크 여부를 고정하지 않아 정상 구현도 실패할 수 있었던 결함을, `purchase_orders__isnull=True`(미연결) 픽스처로 명시 고정하고 PO-연결 사례는 Exclusions에 별도 기록. **D15(major)**: `OrderResyncView`(`backend/order/views.py:188`, `urls.py:58`, `views.py:229`에서 `OrderDetailSerializer` 재사용)가 다운스트림 소비자 열거에서 누락되었음을 확인, 결정 E와 acceptance.md 회귀 목록에 추가. **D16(major)**: `_recompute_order_aggregates`가 `status`/`ready_to_ship` 두 컬럼을 하나의 UPDATE로 함께 쓴다는 사실(L188-195)을 확인 — REQ-DEX-009d의 "shall NOT modify `status`"가 런타임 사실과 다름을 인정하고 "규칙은 불변, 컬럼은 같은 UPDATE로 계속 쓰임"으로 정정. **D17(minor)**: `test_daily_review_upload.py`(damaged_exchange 25건, `UploadDailyReviewView` 경유)가 회귀 목록에서 누락되었음을 확인, acceptance.md에 추가. **D18(minor)**: REQ-DEX-009c/012b/012c가 spec.md 자신이 선언한 "REQUIREMENTS는 WHAT만" 규칙(L42)을 어기고 file:line을 REQUIREMENTS 안에 담고 있었음을 확인 — 해당 인용을 plan.md로 이관하고 REQ 문구를 행위적으로 재서술. **D19(minor)**: REQ-DEX-006b의 `then`절 주어가 "the system"이 아니라 "that LineItem's quantity"였음을 확인 — 시스템 주어로 수정. **D22(minor)**: 특성화 테스트 요구가 세 번째 기존 분기(`if not non_cancelled → None`)를 누락하고, `test_spec_012.py:168-285`의 `TestRecomputeOrderAggregatesReadyToShip`(9개 테스트)가 이미 그 특성화 스위트임을 인지하지 못해 신규 작성을 요구하는 것처럼 읽혔음을 확인 — 기존 스위트를 명시하고 "신규 작성이 아니라 회귀 확인 + damaged_exchange 신규 테스트 추가"로 정정. 모듈 수는 REQ-DEX-013/013a를 "파손 신고 제출 및 Order 집계 영향" 섹션에 편입해 5개 이하 유지. REQ: 기본 계열 001~013(13개, 신규 013 추가) + 접미사 11개(005a/006a/006b/009a/009b/009c/009d/012a/012b/012c/013a) = 22개 항목 → 24개 항목. AC: 25개 → 27개 항목(신규 013/013a). |
| 1.3.1 | 2026-08-14 | ggajo | plan-auditor 리뷰(iteration 3, FAIL, 0.78)의 잔여 blocking 결함 2건 반영. iteration 2의 blocking 4건(D13/D14/D20/D21)과 major 6건(D15~D19, D22)은 전량 RESOLVED로 재확인되었고, 이번 2건은 v1.3.0이 그 수정 과정에서 새로 만든 것이다. **D24(blocking)**: AC-DEX-013/시나리오 13이 `damaged_exchange` 행의 `logistics_status`를 고정하지 않아, `not_shipped` 픽스처에서는 기존 `all(...)` 규칙만으로도 `False`가 나오므로 `0033_backfill_order_ready_to_ship.py`를 그대로 베껴 `damaged_exchange` 단락을 누락한 마이그레이션(plan.md가 0033을 선례로 따르라고 지시하므로 가장 발생 확률이 높은 구현 오류)도 통과할 수 있었음 — `logistics_status="received"` 고정으로 판별력 확보. 이는 D13(이번 개정 전체가 그것을 위해 만들어진 blocking 결함)을 지탱하는 유일한 기준이므로 필수. 함께 AC-DEX-013a/시나리오 13a의 두 번째 Order에 `sku` not null 고정 추가 — 백필 스코프가 "추적 가능 LineItem 1건 이상인 Order"이므로 `sku`가 null이면 그 Order는 애초에 대상 밖이 되어 기준이 공허해짐. **D23(blocking)**: AC-DEX-012e/시나리오 12f가 "the system shall report a quantity"라고 단언했으나 `VendorComparisonView`의 응답 행(`purchase_order_views.py:808-833`)에는 수량 필드가 존재하지 않고, 해당 픽스처(창고 재고 전부 0)에서 수량에 의존하는 유일한 출력인 `selected_distributor`/`candidate_basis`는 `10`이든 `3`이든 동일해 실행 불가·판별 불가였음 — 뷰 내부 SKU→수량 맵 `qty_by_sku`(`purchase_order_views.py:744-750`)에 대한 화이트박스 단언으로 재작성하고, 화이트박스를 택한 이유를 기준 본문에 명시. iteration 3이 잔여로 분류한 D25~D32(테스트 개수 9 vs 10, `spec.md:41/:50`의 D16 이전 문구 잔존, 자기참조 문구, 감사 이력이 규범 텍스트에 섞인 점 등)는 전부 문서 정확성 항목이고 구현 리스크가 없다고 판단해, 감사 리포트(`.moai/reports/plan-audit/SPEC-PURCHASE-ORDER-011-review-3.md`)에 기록된 채로 이월한다. REQ/AC 개수 변동 없음(24/27). |

---

## 문제 정의

배송된 도서가 파손되었거나 교환이 필요한 경우, 현재는 이를 접수할 전용 화면이 없다. `LineItem.purchase_status`에 `damaged_exchange`(파손/교환) 값 자체는 SPEC-PURCHASE-ORDER-010에서 이미 도입되어 재발주 큐에 재진입하도록 구현되어 있으나, 그 값을 실제로 "설정하는" 진입점은 기존 발주 관리 화면의 범용 상태 변경 기능뿐이다. 창고/CS 담당자가 ISBN 하나로 미출고 품목을 즉시 검색하고, 파손 수량을 입력해 한 번의 클릭으로 접수할 수 있는 전용 화면이 필요하다.

또한 SPEC-PURCHASE-ORDER-010이 재발주 큐 노출(읽기측 필터)만 다루었을 뿐, 재발주 "수량" 자체는 다루지 않았다. 현재 재발주 큐(`UnorderedItemsView`)는 `damaged_exchange` 품목에 대해서도 원래 주문 수량(`quantity`) 전체를 재발주 수량으로 제시한다 — 예를 들어 10권 중 2권만 파손되었어도 10권 전체를 다시 발주하라고 안내하는 결함이 있다. 파손 수량만 별도로 기록하고, 재발주 큐가 그 파손 수량만큼만 반영하도록 정정해야 한다.

마지막으로(v1.2.0, plan-auditor D1 재검토 결과), 파손 접수만으로는 부모 Order의 `ready_to_ship`(오늘 출고 가능 여부) 집계가 갱신되지 않는 실제 결함이 확인되었다 — 아래 REQ-DEX-009c/결정 E 참조.

## 솔루션 개요

1. `LineItem`에 `damaged_quantity`(파손 접수 수량, 기본값 0) 필드를 신규 추가한다.
2. `/outbound`, `/rack-number`와 완전히 독립된 신규 프론트엔드 페이지(`/damaged-exchange`)와 사이드바 메뉴 항목을 추가한다.
3. ISBN 정확 일치 검색으로 미출고 품목(기존 `LineItemRackNumberSummaryView`가 사용하는 것과 동일한 정의)을 조회하고, 이미 `damaged_exchange` 상태인 품목도 배지로 구분해 함께 노출한다.
4. 행(row) 단위로 파손 수량을 입력해 접수하면 `purchase_status`를 `damaged_exchange`로 전환하고, 신규 필드 `damaged_quantity`에 접수 수량을 기록하며(재접수 시 덮어쓰기), 해당 품목에 대한 메모(`LineItemNote`, `note_type="파손/교환"`, `assignee="발주"`, `author`=접수자)를 자동 생성하고, 부모 Order 집계를 기존 관례대로 재계산한다. `logistics_status`/`shipped_quantity`는 이 접수로 변경되지 않는다.
5. 기존 재발주 큐 조회(`UnorderedItemsView`)의 수량 계산을, `damaged_exchange` 품목에 한해 `quantity` 대신 `damaged_quantity`를 기준으로 사용하도록 정정한다. 환불 차감·0이면 제외 규칙은 그대로 유지한다.
6. **(v1.2.0 신규, 범위 확장)** 공유 집계 함수 `_recompute_order_aggregates`를 수정해, `damaged_exchange` LineItem이 있는 Order는 기존 `cs_required` 단락과 동일하게 `ready_to_ship=False`로 강제한다 — `Order.status`(물류 집계)는 건드리지 않는다. 결정 E 참조.

구체적인 코드 위치, 함수/클래스명, 엔드포인트 경로는 `plan.md`에 있다 — 이 문서는 관찰 가능한 동작(WHAT)만 규정한다. DELTA 마커: 이 SPEC의 항목 대부분은 신규([NEW])이나, REQ-DEX-009c/009d는 예외적으로 기존 공유 함수 `_recompute_order_aggregates`를 고치는 `[MODIFY]`다.

## 범위 — 포함

- `LineItem.damaged_quantity` 필드 신규 추가 + 마이그레이션(데이터 백필 불필요).
- 신규 백엔드 엔드포인트 2개 — ISBN 정확 일치 검색(미출고 품목 조회), 행 단위 파손 접수(상태 전환 + 메모 생성 + 집계 재계산, 재접수 시 덮어쓰기).
- 기존 `UnorderedItemsView`의 재발주 수량 계산 로직 수정(`damaged_exchange` 품목 한정).
- **[MODIFY]** 기존 공유 함수 `_recompute_order_aggregates`의 `ready_to_ship` 계산 규칙에 `damaged_exchange` 단락 분기 추가(결정 E) — `Order.status`는 무변경.
- 신규 독립 프론트엔드 페이지(`/damaged-exchange`) + 사이드바 메뉴 항목.

## 가정 (Confirmed Assumptions)

1. ISBN 검색은 `LineItem.sku`에 대한 정확 일치(exact match)이며, 부분/포함(icontains) 검색은 지원하지 않는다.
2. 이미 `damaged_exchange` 상태인 품목도 검색 결과에 포함하고, 상태 배지로 다른 행과 구분한다.
3. `damaged_quantity`는 기본값 0이며, `purchase_status != "damaged_exchange"`인 행에서는 그 값이 의미를 가지지 않는다(표시·재발주 수량 계산 어디에도 사용되지 않는다).
4. 인증은 기존 모든 형제 엔드포인트와 동일하게 `JWTAuthentication` + `IsAuthenticated`를 그대로 사용하며, 이번 SPEC에서 인증/권한 방식을 변경하지 않는다.

## 설계 결정

SPEC 작성 과정에서 확정 요구사항이 명시적으로 다루지 않은 실제 엣지 케이스에 대해 SPEC 작성자가 판단을 내린 뒤 사용자가 확인·확정했다. 결정 A/B/D/E는 2026-08-14에 사용자 확인을 거쳤다. 결정 C는 확정이 필요 없는 명명 규칙이다.

### 결정 A — 재발주 수량 계산에서 환불 차감은 `damaged_quantity`에도 동일하게 적용 (사용자 확정, 2026-08-14)

`UnorderedItemsView`는 현재 모든 행에 대해 `net_qty = max((quantity or 0) - refunded_qty, 0)`를 계산한다. `damaged_exchange` 품목의 기준값을 `quantity`에서 `damaged_quantity`로 바꾸되, 환불 차감 자체는 계속 적용한다 — 즉 `net_qty = max((damaged_quantity or 0) - refunded_qty, 0)`. 환불은 Shopify에서 발생하는 별도 신호이며, 파손 접수 여부와 무관하게 "이미 환불된 수량은 재발주할 필요가 없다"는 원칙이 그대로 성립하기 때문에, 새 필드를 도입하되 기존 차감 패턴은 유지하는 것이 최소 변경 원칙에 부합한다. 0이면 제외하는 규칙(`if net_qty == 0: continue`)도 동일하게 적용된다.

### 결정 B — "전체 출고 수량" 합산은 취소·미추적 행을 제외한 부모 Order LineItem에 한정 (사용자 확정, 2026-08-14 — 초안에서 내용 수정)

**최종 확정 규칙**: "전체 출고 수량"은 부모 Order에 속한 LineItem 중 `sku IS NOT NULL` AND `purchase_status != "order_cancelled"`인 행에 한해 `quantity`를 합산한다 — `_recompute_order_aggregates`가 이미 사용하는 "추적 가능(trackable)" 범위와 정합시킨 것이다. 사용자가 밝힌 근거: "표시되는 숫자는 실제로 출고될 물량과 일치해야 한다 — 취소된 행을 포함하면 값이 과장된다." null `quantity`는 기존 SPEC-ORDER-014 REQ-RACKSUM-005 선례를 따라 0으로 취급한다(AC-DEX-005c).

### 결정 C — ISBN 검색 파라미터는 모델 필드명을 따라 `sku`로 명명

이 코드베이스에서 "ISBN"은 업무 용어일 뿐, 실제 필드는 `LineItem.sku` 하나뿐이다(별도 `isbn` 필드 없음). 따라서 검색 API 파라미터명은 `sku`로 하고, 화면 라벨만 "ISBN 검색"으로 표기한다.

### 결정 D — 파손 접수로 생성되는 `LineItemNote.author`는 접수를 수행한 로그인 사용자로 기록 (사용자 확정, 2026-08-14)

기존 자동 생성 노트(Daily Review 업로드, 발주확정 화면의 note 필드)는 배치/파일 기반 흐름이라 `author=None`으로 기록되어 왔다. 그러나 이 기능은 한 명의 로그인한 운영자가 한 건씩 직접 클릭해 접수하는 단건 대화형 액션이므로, TRUST 5의 Trackable 원칙에 따라 `author`를 요청을 수행한 인증된 사용자로 기록한다. 기존 `author=None` 선례에서 의도적으로 벗어난 결정임을 명시한다. (REQ-DEX-010, AC-DEX-010)

### 결정 E — REQ-DEX-009c/009d는 공유 함수 `_recompute_order_aggregates`(fan-in 8)로의 범위 확장이며, 이번 페이지와 무관한 기존 소비자에도 `ready_to_ship` 시맨틱 변화가 미친다 (사용자 확정, 2026-08-14, plan-auditor D1 반영)

plan-auditor D1 재검토 결과, 파손 접수 후에도 `logistics_status`를 건드리지 않으면(REQ-DEX-011) `ready_to_ship`이 그대로 `True`로 남는 실제 결함이 확인되었다 — `purchase_order_views.py:182-185`의 판정은 다음과 같다:

```python
ready_to_ship = all(
    logistics_status == "received" or purchase_status == "in_stock"
    for logistics_status, purchase_status in non_cancelled
)
```

이 `all(...)` 판정은 `damaged_exchange`를 전혀 인식하지 않으므로, `logistics_status="received"`인 품목이 `damaged_exchange`로 바뀌어도 첫 번째 disjunct가 여전히 참이라 `True`로 남는다. 사용자는 테스트 픽스처를 고치는 대신 이 집계 규칙 자체를 고치기로 결정했다 — `damaged_exchange`를 기존 `cs_required` 단락(`purchase_order_views.py:179-180`)과 동일한 자리에서 동일한 방식으로 단락(short-circuit) 처리해 무조건 `False`로 만든다(REQ-DEX-009c).

**이것은 이번 SPEC의 원래 범위(신규 페이지 + `UnorderedItemsView` 수정)를 넘어, fan-in 8인 공유 함수 `_recompute_order_aggregates`(`purchase_order_views.py:113-195`) 자체를 수정하는 확장이다.** 아래 호출자 전원이 산출하는 `ready_to_ship` 값이 이 SPEC 적용 이후 (해당 Order에 `damaged_exchange` LineItem이 있는 경우) 달라질 수 있다 — 이번 신규 페이지와 무관한 기존 화면·플로우도 영향권에 든다.

**기존 호출자 8곳** (`purchase_order_views.py:113-118` 주석에서 확인):
1. `UploadVendorShipmentView`
2. `UploadWarehouseReceiptView`
3. `LineItemLogisticsStatusUpdateView`
4. `LineItemLogisticsStatusBulkUpdateView`
5. `ConfirmOrderView`
6. `LineItemStatusUpdateView`
7. `LineItemBulkStatusUpdateView`
8. `UploadDailyReviewView`

**이번 SPEC이 추가하는 9번째 호출자**: 신규 파손 접수 엔드포인트(REQ-DEX-009) — fan-in이 8에서 9로 증가한다.

**`Order.ready_to_ship`의 다운스트림 소비자** (`backend/`·`frontend/` 전체 grep으로 확인, v1.3.0에서 재검증 및 D15 보강):
- 백엔드: `OrderDetailSerializer`(`backend/order/serializers.py:141-171`, 필드 노출은 L170) → `OrderDetailView`(`GET /api/orders/<pk>/`).
- 백엔드(v1.3.0 신규, D15): `OrderResyncView`(`backend/order/views.py:188`, `POST /api/orders/<pk>/sync/`, 라우트는 `urls.py:58`) — Shopify 재동기화 후 `OrderDetailSerializer(order).data`를 그대로 반환한다(`views.py:229`), `OrderDetailView`와 동일한 직렬화기를 공유하는 두 번째 소비 엔드포인트.
- 프론트엔드: `frontend/src/pages/OrderDetailPage.tsx:240-260` — 주문 상세 화면의 3-state 배지("출고가능"/"출고불가"/미표시, SPEC-ORDER-012 결정 F).
- 이번 SPEC 자신의 신규 검색 화면(REQ-DEX-006)도 동일 값을 읽기 전용으로 소비한다.
- 확인 결과 `OrderListSerializer`(`backend/order/serializers.py:14-36`, `/orders` 목록 화면)는 `ready_to_ship`을 노출하지 않으므로 영향이 없다.
- `backend/order/migrations/0033_backfill_order_ready_to_ship.py:55-63`은 REQ-RTS-002 규칙의 **별도 재구현**(과거 시점 스냅샷 — Django 마이그레이션 관례상 `purchase_order_views`를 import할 수 없어 규칙을 다시 구현해 둔 코드)이다. 이 SPEC 적용 이후 0033의 재구현과 런타임 `_recompute_order_aggregates`는 `damaged_exchange` 단락 유무로 의도적으로 갈라진다 — 0033은 과거 특정 시점(SPEC-ORDER-012 배포 시점)의 규칙을 동결한 것이므로 소급 수정 대상이 아니다. 신규 REQ-DEX-013이 그 간극을 메운다.

**`Order.status`(물류 상태 집계, `logistics_status` 기반)를 도출하는 규칙 자체는 이 변경으로 전혀 수정되지 않는다** — 여전히 기존 `logistics_status` 집계 규칙만을 따른다(REQ-DEX-009d). 다만 `_recompute_order_aggregates`는 `status`와 `ready_to_ship` 두 컬럼을 항상 하나의 UPDATE 문으로 함께 쓰므로(v1.3.0 D16 정정 — plan-auditor가 `purchase_order_views.py:188-195`에서 직접 확인), 신규 9번째 호출자(파손 접수 엔드포인트)도 매번 `status` 컬럼을 다시 쓴다 — 다만 그 값은 새 단락과 무관하게 항상 기존 규칙대로만 계산된다. "무변경"은 컬럼 write 여부가 아니라 **규칙**에 대한 진술이다.

**브라운필드 관례에 따른 요구사항 (v1.3.0 정정, D22)**: `_recompute_order_aggregates`의 기존 `ready_to_ship` 동작에 대한 특성화 테스트는 이미 존재한다 — `backend/order/tests/test_spec_012.py`의 `TestRecomputeOrderAggregatesReadyToShip` 클래스(9개 테스트)가 세 가지 기존 분기를 전부 고정하고 있다: (1) 추적 가능 LineItem이 0건이면 `None`, (2) `cs_required` 단락, (3) `all(received/in_stock)` 판정. 이 SPEC은 이 기존 스위트를 새로 작성하지 않는다 — `damaged_exchange` 단락 추가 전후로 이 9개 테스트가 그대로 통과하는지만 확인하고(회귀 없음 — 이 파일에 `damaged_exchange` 문자열이 전혀 등장하지 않음을 확인함), 그 위에 `damaged_exchange` 단락 자체를 검증하는 신규 테스트(AC-DEX-009c)만 추가한다.

### 결정 F — 규칙 변경만으로는 기존 데이터가 갱신되지 않으므로, 1회성 백필 마이그레이션을 신규 추가 (사용자 확정, 2026-08-14, plan-auditor iteration 2 D13 반영)

REQ-DEX-009c는 `ready_to_ship`을 "계산하는 규칙"만 바꾼다 — 이미 저장되어 있는 값은 다시 쓰이는 이벤트(`_recompute_order_aggregates`의 9개 호출자 중 하나가 그 Order에 대해 실행되는 것)가 일어나기 전까지는 그대로 남는다. REQ-DEX-006a는 신규 검색 페이지가 조회 시점에 재계산하는 것을 명시적으로 금지하므로, 이미 `damaged_exchange`로 접수되어 있던 기존 Order는 이 SPEC이 배포된 뒤에도 무관한 다른 쓰기가 우연히 발생하기 전까지 `ready_to_ship=True`인 채로 새 페이지에 그대로 표시된다 — 이 SPEC이 없애려는 바로 그 증상이 과거 데이터에는 그대로 남는 것이다.

이 코드베이스에는 정확히 들어맞는 선례가 있다: SPEC-ORDER-012가 `ready_to_ship` 필드 자체를 도입했을 때, `backend/order/migrations/0033_backfill_order_ready_to_ship.py`(REQ-RTS-006)라는 1회성 백필 마이그레이션을 함께 배포했다. 이번에도 동일한 형태로 신규 마이그레이션을 추가한다(REQ-DEX-013) — 사용자가 결정했다: "규칙만 바꾸고 데이터를 방치하면 이 SPEC의 존재 이유가 무색해진다."

## 요구사항 (EARS)

**번호 규칙 참고**: 기본 번호 계열(REQ-DEX-001~013)에는 결번이 없다. 알파벳 접미사(`005a`, `006a`, `006b`, `009a`, `009b`, `009c`, `009d`, `012a`, `012b`, `012c`, `013a`)는 기본 항목에서 파생된 서로 다른 트리거 또는 성격(정상 경로 vs 예외/회귀 방지 vs 범위 확장)을 분리 표현하기 위한 것이며, SPEC-ORDER-015/SPEC-PURCHASE-ORDER-010에서 확립된 프로젝트 관례를 따른다. `006b`는 v1.1.0에서, `009b`/`009c`/`009d`/`012c`는 v1.2.0에서, `013`/`013a`는 v1.3.0에서 신규 추가되었다. `(Unwanted)` 항목은 전량 "If [조건], then the system shall NOT/shall [응답]" 형태로 시스템을 주어로 삼는다(v1.2.0, MP-2 대응; v1.3.0에서 REQ-DEX-006b를 이 규칙에 맞춰 재정정 — D19). REQUIREMENTS는 관찰 가능한 동작(WHAT)만 규정하며 파일:라인 인용을 담지 않는다 — 그런 세부는 `plan.md`에 있다(v1.3.0에서 REQ-DEX-009c/012b/012c의 file:line 문단을 이관 — D18).

### 데이터 모델

**REQ-DEX-001** (Ubiquitous): The system shall persist, for every LineItem, a `damaged_quantity` integer field defaulting to `0`, representing the quantity reported as damaged/exchange-requested for that LineItem.

### 프론트엔드 진입점

**REQ-DEX-002** (Ubiquitous): The system shall provide a new standalone frontend page for damaged-exchange requests, at a route independent of the existing `/outbound` and `/rack-number` pages.

**REQ-DEX-003** (Ubiquitous): The system shall provide a new sidebar menu entry linking to the page defined in REQ-DEX-002.

### ISBN 검색 및 결과 표시

**REQ-DEX-004** (Event-Driven): When an operator submits a single ISBN search, the system shall match it against `LineItem.sku` using exact string equality only, with no partial or substring (icontains) matching.

**REQ-DEX-005** (Ubiquitous): The system shall restrict search results to LineItems where `logistics_status != "shipped"` AND `purchase_status != "order_cancelled"` — the same 미출고(unshipped) definition already used by the existing cross-order rack-number summary endpoint.

**REQ-DEX-005a** (Ubiquitous): The system shall include, within the search results defined by REQ-DEX-005, LineItems whose `purchase_status` is already `"damaged_exchange"`, visually distinguished from other rows by a status badge.

**REQ-DEX-006** (Ubiquitous): The system shall display, for each search result row: the parent Order's `name` (주문번호), the LineItem's own `quantity` (주문 수량), the parent Order's `ready_to_ship` value exactly as stored (오늘 출고 가능 여부, three-state: true/false/null), and the sum of `quantity` across every LineItem belonging to that same parent Order where `sku IS NOT NULL` AND `purchase_status != "order_cancelled"` (전체 출고 수량, per 결정 B — the "trackable" scope already used by the existing Order aggregate recomputation). This label intentionally names the sum of order `quantity`, not `LineItem.shipped_quantity` (SPEC-ORDER-015's unrelated outbound-tracking field, `models.py:221`) — the two counters are never conflated and this SPEC does not read or display `shipped_quantity` anywhere.

**REQ-DEX-006a** (Unwanted): If the system serves a search result row per REQ-DEX-006, then the system shall NOT recompute, override, or redefine `Order.ready_to_ship` before displaying it — it shall be read and shown exactly as currently stored.

**REQ-DEX-006b** (Unwanted): If a LineItem belonging to the parent Order has `sku IS NULL` or `purchase_status == "order_cancelled"`, then the system shall NOT include that LineItem's `quantity` in the 전체 출고 수량 sum defined in REQ-DEX-006 (v1.3.0 D19 — subject corrected to "the system").

**REQ-DEX-007** (Unwanted): If a searched ISBN does not exactly match any LineItem within the REQ-DEX-005 scope, then the system shall return an empty result set rather than an error response.

### 파손 신고 제출 및 Order 집계 영향

**REQ-DEX-008** (Ubiquitous): The system shall provide, for each search result row, a damage-submission control accepting a damage quantity input that defaults to `1` and accepts integer values in the range `1` to that row's `LineItem.quantity` inclusive.

**REQ-DEX-009** (Event-Driven): When an operator submits a valid damage quantity for a LineItem, the system shall set that LineItem's `purchase_status` to `"damaged_exchange"`, store the submitted quantity in `damaged_quantity`, and recompute the parent Order's aggregate fields, following the same recomputation convention already applied to every other `purchase_status` write.

**REQ-DEX-009a** (Unwanted): If the submitted damage quantity is outside the range `1` to `LineItem.quantity` inclusive (including the case where `LineItem.quantity` is null or zero, making that range empty), then the system shall reject the submission and shall NOT modify `purchase_status`, `damaged_quantity`, or any Order aggregate field.

**REQ-DEX-009b** (Event-Driven): When an operator submits a valid damage quantity for a LineItem whose `purchase_status` is already `"damaged_exchange"`, the system shall overwrite the existing `damaged_quantity` with the newly submitted value rather than accumulate it, so a mis-reported quantity can be corrected by resubmission.

**REQ-DEX-009c** (State-Driven) `[MODIFY]`: While an Order's non-cancelled trackable LineItem set (the same set already evaluated per SPEC-ORDER-012 REQ-RTS-002) contains at least one LineItem with `purchase_status == "damaged_exchange"`, the system shall set that Order's `ready_to_ship` to `False` regardless of any LineItem's `logistics_status` or `purchase_status == "in_stock"` value — evaluated with the same precedence as the existing `cs_required` condition (결정 E; exact code location in `plan.md`).

**REQ-DEX-009d** (Unwanted): If the REQ-DEX-009c short-circuit evaluates for an Order, then the system shall continue to compute that Order's `status` field using the existing, unmodified `logistics_status` aggregate rule — the short-circuit changes only the `ready_to_ship` output value; it does not alter how `status` is derived (v1.3.0 D16 — "the system shall not modify `status`" is not literally true, since `status` and `ready_to_ship` are always persisted together by the same underlying write; what does not change is the *rule*, see 결정 E).

**REQ-DEX-010** (Event-Driven): When a damage submission (REQ-DEX-009) succeeds, the system shall also create exactly one `LineItemNote` for that LineItem with `note_type="파손/교환"`, `assignee="발주"`, `author` set to the authenticated user who submitted the request (결정 D — a deliberate departure from the `author=None` convention used by batch-driven note creation elsewhere), and `content` that includes the submitted damage quantity value.

**REQ-DEX-011** (Unwanted): If a damage submission (REQ-DEX-009) is processed for a LineItem, then the system shall NOT modify that LineItem's `logistics_status` or `shipped_quantity`.

**REQ-DEX-013** (Event-Driven) `[NEW]`: When the backfill migration is applied, the system shall recompute `ready_to_ship` (applying the REQ-DEX-009c rule, including the `damaged_exchange` short-circuit) for every existing Order that has at least one trackable LineItem — so that Orders damaged before this SPEC ships no longer display a stale `ready_to_ship` value (결정 F; exact algorithm and precedent in `plan.md`).

**REQ-DEX-013a** (Unwanted): If an Order in the backfill's scope does not contain any `damaged_exchange` LineItem, then the backfill shall leave that Order's `ready_to_ship` value exactly as already computed by the pre-existing REQ-RTS-002 rule — unaffected by this SPEC's migration.

### 재발주 큐 수량 보정

**REQ-DEX-012** (Event-Driven): When the existing unordered-items reorder-queue view computes the reorder quantity for a LineItem whose `purchase_status == "damaged_exchange"`, the system shall use that LineItem's `damaged_quantity` as the base quantity — in place of `quantity` — before applying the existing refund subtraction (`max(base - refunded_qty, 0)`, 결정 A) and the existing zero-quantity skip rule, both otherwise unchanged.

**REQ-DEX-012a** (Unwanted): If the reorder-queue view (REQ-DEX-012) computes the reorder quantity for a LineItem whose `purchase_status != "damaged_exchange"`, then the system shall use `quantity` as the base — unchanged from current behavior — and shall NOT apply the `damaged_quantity` substitution.

**REQ-DEX-012b** (Unwanted): If a LineItem with `purchase_status == "damaged_exchange"` is evaluated by the 업체 자료 비교 뷰(`RunComparisonView`), Daily Review 다운로드 뷰(`DailyReviewExcelView`), Daily Review 업로드 확정 뷰(`UploadDailyReviewView`), 발주 파일 생성 뷰(`GenerateOrderFileView`), or 업체 비교 목록 뷰(`VendorComparisonView`), then the system shall continue to read/report that LineItem's `quantity` unchanged — the `damaged_quantity` substitution defined in REQ-DEX-012 applies only to the reorder-queue view (`UnorderedItemsView`). These five sites do not share one uniform computation — see `plan.md` for each site's exact formula and citation; what they share is only that none of them read `damaged_quantity`. The 업체 비교 목록 뷰's coverage under this requirement is additionally limited to `damaged_exchange` LineItems not linked to any PurchaseOrder — see Exclusions for the PO-linked case, which this requirement does not cover (v1.3.0 D21).

**REQ-DEX-012c** (Unwanted): If the 수기 발주확정 뷰(`ConfirmOrderView`) processes a request item, then the system shall continue to take that item's quantity from the request body as submitted by the client — it shall NOT read `LineItem.quantity` or `LineItem.damaged_quantity` for that purpose. `ConfirmOrderView` is unaffected by REQ-DEX-012 for a structurally different reason than the five sites in REQ-DEX-012b: it never reads a LineItem-sourced quantity to begin with, so no regression test against `LineItem.quantity`/`damaged_quantity` is meaningful for this view (exact code location in `plan.md`).

---

## Exclusions (What NOT to Build)

- `book.Info.qty`, `order.WarehouseStock` — 변경 없음, 이 SPEC은 `order.LineItem`/`Order` 레벨 상태·수량 필드만 다룬다.
- `LineItem.fulfillment_status`(Shopify 동기화 전용 필드) — 변경 없음.
- Shopify 동기화 경로 — 변경 없음.
- 기존 `/outbound`(SPEC-ORDER-015) 및 `/rack-number`(SPEC-ORDER-013/014) 페이지 동작 — 변경 없음, 완전히 독립된 신규 페이지로 구현한다.
- 신규 `logistics_status`/`purchase_status` enum 값 추가 없음 — `damaged_exchange`는 SPEC-PURCHASE-ORDER-010에서 이미 도입된 기존 값을 재사용한다.
- 파손 접수를 위한 대량/Excel 업로드 경로 없음 — 이번 SPEC은 행 단위 단건 접수만 다룬다.
- `Order.status`(물류 상태 집계, `logistics_status` 기반)를 **도출하는 규칙**은 변경 없음(REQ-DEX-009d) — `_recompute_order_aggregates`의 `ready_to_ship` 출력만 새 규칙이 적용되고(REQ-DEX-009c, 더 이상 Exclusion이 아님), `status` 값은 여전히 기존 `logistics_status` 규칙만으로 계산된다. 다만 두 컬럼이 같은 UPDATE 문으로 함께 쓰이므로(v1.3.0 D16), "컬럼이 쓰이지 않는다"는 의미는 아니다 — "규칙이 바뀌지 않는다"는 의미다.
- REQ-DEX-012b에 열거된 5개 재발주 후보 조회 지점(업체 자료 비교 뷰, Daily Review 다운로드 뷰, Daily Review 업로드 확정 뷰, 발주 파일 생성 뷰, 업체 비교 목록 뷰)의 수량 계산 — 변경 없음. `damaged_quantity` 보정은 `UnorderedItemsView` 한 곳에만 적용된다. **알려진 의도적 공백(known, deliberate gap)**: 이 5곳도 논리적으로는 `UnorderedItemsView`와 동일한 결함(`damaged_exchange` 행에 대해 `damaged_quantity`가 아닌 전체 `quantity`를 계속 사용)을 잠재적으로 가지고 있다. 사용자가 이번 SPEC의 범위를 `UnorderedItemsView` 한 곳으로 명시적으로 확정했으므로(2026-08-14) 이번 SPEC에서는 손대지 않으며, 후속 SPEC 후보로 기록해 둔다. 수기 발주확정 뷰(`ConfirmOrderView`)는 이 5곳과 다른 구조적 이유(REQ-DEX-012c)로 별도 취급한다 — quantity 자체를 요청 바디에서 받으므로 애초에 이 공백에 해당하지 않는다.
- **(v1.3.0 신규, D21) 업체 비교 목록 뷰(`VendorComparisonView`)의 PO-연결된 `damaged_exchange` 행** — 이 뷰의 수량 집계는 `purchase_orders__isnull=True`(PurchaseOrder에 전혀 연결되지 않은 LineItem)만 대상으로 하며, `damaged_exchange`에 대한 링크 예외가 없다(`GenerateOrderFileView`의 `_reorder_candidate_filter`류 예외와 다름). 이 코드베이스의 기존 주석(`purchase_order_views.py:372-381`, SPEC-PURCHASE-ORDER-010 REQ-DMG-008 수정 이력)은 "파손/교환 품목은 현실적으로 원래 PurchaseOrder에 이미 연결되어 있다"고 기록하고 있다 — 즉 실무에서 자주 발생할 PO-연결된 `damaged_exchange` 행은 이 뷰에서 아예 `0`으로 보고되며(수량 `10`도 `damaged_quantity` `3`도 아님), 이 SPEC은 이 경우를 다루지 않는다. AC-DEX-012e는 PO-미연결 경우만 검증한다 — PO-연결 경우는 알려진 미검증 공백으로 남긴다.
- `LineItemDetailSerializer` 등 기존 상세 화면에 `damaged_quantity` 노출 — 요청되지 않았으므로 이번 SPEC 범위에 포함하지 않는다.

## 관련 SPEC

- SPEC-PURCHASE-ORDER-010: `LineItem.purchase_status`에 `damaged_exchange` 값 도입 및 재발주 큐 읽기측/쓰기측 재진입 로직의 근원 SPEC. 이번 SPEC은 그 값을 "설정하는" 전용 UI와, 재발주 "수량" 정확도를 다룬다 — 완전히 보완적이며 SPEC-PURCHASE-ORDER-010의 로직을 변경하지 않는다. `purchase_order_views.py:372-381`(REQ-DMG-008 수정 이력)의 "damaged_exchange는 현실적으로 PO에 이미 연결되어 있다"는 기록이 이번 SPEC의 D21 대응(VendorComparisonView PO-연결 공백) 근거다.
- SPEC-ORDER-012: `Order.ready_to_ship` 3-state 집계 도입 SPEC — 이번 SPEC(v1.2.0)은 그 계산 규칙에 `damaged_exchange` 단락 분기를 신규 추가한다(REQ-DEX-009c, `[MODIFY]`). SPEC-ORDER-012가 확립한 나머지 규칙(`cs_required` 단락, `received`/`in_stock` 판정, 추적 가능 LineItem이 없으면 `None`)은 그대로 유지된다. SPEC-ORDER-012가 REQ-RTS-006으로 배포한 `0033_backfill_order_ready_to_ship` 백필 마이그레이션이 이번 SPEC(v1.3.0)의 REQ-DEX-013의 직접적 선례다 — 0033은 과거 시점의 규칙을 동결한 재구현이며, 이 SPEC 적용 이후 런타임 규칙과 의도적으로 갈라진다(결정 F).
- SPEC-ORDER-014: 미출고(unshipped) 정의(`logistics_status != "shipped"` AND `purchase_status != "order_cancelled"`)와 null 수량을 0으로 취급하는 관례의 선례.
- SPEC-ORDER-015: `/outbound` 독립 페이지 + 사이드바 신규 메뉴 항목 패턴의 직접적 선례.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-DEX-XXX 하나 이상에 1:1 이상으로 추적된다. 실행 가능한 Given/When/Then 테스트 시나리오는 `acceptance.md`에 별도로 있으며, 각 시나리오는 아래 AC-DEX-XXX ID를 인용해 상호 추적된다. (v1.2.0: MP-2 대응으로 아래 항목 전량에서 "Given...when...the system shall" 하이브리드 구문을 제거하고 순수 트리거-응답 EARS 산문으로 재작성했다.)

**AC-DEX-001** (Ubiquitous) — Traces: REQ-DEX-001. The system shall expose `damaged_quantity` on every LineItem defaulting to `0`, and applying the migration shall NOT alter any existing LineItem record's stored values.

**AC-DEX-002** (Ubiquitous) — Traces: REQ-DEX-002, REQ-DEX-003. The system shall present a standalone damaged-exchange page reachable from a dedicated sidebar entry; the page's frontend module shall import no `OutboundPage`/`RackNumberPage` component and no `outboundApi`/`rackNumberApi`/`useOutboundQueries`/`useRackNumberQueries` module (shared primitives such as `ui/button` and `lib/axios` are expected and excluded from this check — D8 correction, matches the SPEC-ORDER-015 independence precedent).

**AC-DEX-003** (Unwanted) — Traces: REQ-DEX-004. If a search ISBN is a strict substring or prefix of an existing LineItem's `sku` (but not exactly equal to it), then the system shall NOT include that LineItem in the results.

**AC-DEX-004** (Event-Driven) — Traces: REQ-DEX-005. When the search endpoint is queried for a SKU shared by three LineItems whose (`logistics_status`, `purchase_status`) pairs are (`not_shipped`,`unordered`), (`shipped`,`unordered`), and (`not_shipped`,`order_cancelled`) respectively, the system shall return only the first LineItem in the results.

**AC-DEX-004a** (Event-Driven) — Traces: REQ-DEX-005a. When the search endpoint returns a LineItem within REQ-DEX-005's scope whose `purchase_status` is already `"damaged_exchange"`, the system shall include it in the results and mark it as distinct from non-damaged rows in the response.

**AC-DEX-005** (Event-Driven) — Traces: REQ-DEX-006. When a search matches only LineItem (1) of a parent Order containing four LineItems — (1) the searched SKU, `quantity=4`, `sku` not null, `purchase_status="unordered"`; (2) a different SKU, `quantity=9`, `sku` not null, `purchase_status="unordered"`; (3) a different SKU, `quantity=100`, `purchase_status="order_cancelled"`; (4) `sku=null`, `quantity=50` — the system shall report that row's 주문 수량 as `4` and its 전체 출고 수량 as `13` (`4+9`, trackable non-cancelled rows only) — not `163` (summing every row), not `4` (the row's own quantity alone), and not the row count.

**AC-DEX-005a** (State-Driven) — Traces: REQ-DEX-006. While a parent Order's stored `ready_to_ship` is `null` due to a state the recomputation has not (yet) overwritten — not because the Order lacks trackable LineItems, since a matched search result row is itself proof that at least one trackable LineItem exists (D10 correction) — the system shall display/return `null` for 오늘 출고 가능 여부 rather than coercing it to `false`.

**AC-DEX-005b** (Unwanted) — Traces: REQ-DEX-006b. If the four-LineItem fixture from AC-DEX-005 is searched, then the system shall NOT include either the cancelled LineItem's `100` or the `sku=null` LineItem's `50` in the 전체 출고 수량 total — an implementation that naively sums every LineItem on the Order (producing `163`) fails this criterion.

**AC-DEX-005c** (Ubiquitous) — Traces: REQ-DEX-006. The system shall treat a `null` `quantity` as `0` when computing 전체 출고 수량 — for a parent Order whose trackable non-cancelled LineItems are **all** `quantity=null` (no non-null quantity present among them), the system shall report the sum as `0`, not `null`/`None` (v1.3.0 D20 correction — the v1.2.0 fixture mixed one null row with a `quantity=9` row, and SQL `SUM` ignores NULL inputs, so it returned `9` regardless of whether the implementation used `Coalesce`; this criterion did not discriminate. The all-null fixture is the only one where the presence or absence of `Coalesce(Sum("quantity"), 0)` is observable).

**AC-DEX-006** (Unwanted) — Traces: REQ-DEX-006a. If a parent Order's stored `ready_to_ship` value would differ from what a fresh recomputation via `_recompute_order_aggregates` (SPEC-ORDER-012 REQ-RTS-002, extended by REQ-DEX-009c) would currently produce, then the system shall display the stored value unchanged and shall NOT trigger a recomputation as part of serving the search request (D9 correction — previously referenced a non-existent "REQ-DEX-006a's rule").

**AC-DEX-007** (Unwanted) — Traces: REQ-DEX-007. If no LineItem exactly matches the searched ISBN within scope, then the system shall respond with an empty result list and an HTTP success status, not an error status.

**AC-DEX-008** (Ubiquitous) — Traces: REQ-DEX-008. The system shall render each result row's damage-quantity input pre-filled with `1`, and shall reject, at minimum on the server side, any value outside `1..LineItem.quantity` (client-side validation may additionally reject early, but server-side rejection is mandatory on its own — uncounted Recommendation #11 correction).

**AC-DEX-009** (Event-Driven) — Traces: REQ-DEX-009, REQ-DEX-009c. When a damage submission of `3` is made for a LineItem with `quantity=8`, `purchase_status="unordered"`, `logistics_status="received"` (the sole trackable LineItem of its parent Order, so `ready_to_ship=True` beforehand via the pre-existing `logistics_status=="received"` disjunct), the system shall set `purchase_status="damaged_exchange"` and `damaged_quantity=3` (not `8`), and shall recompute the parent Order's `ready_to_ship` to `False` via the REQ-DEX-009c short-circuit — NOT because `logistics_status` changes (REQ-DEX-011 keeps it `"received"`) but because the row is now `damaged_exchange` (D1 correction — the v1.1.0 rationale was factually wrong even though the expected outcome was right). An implementation that omits the `_recompute_order_aggregates([li.order_id])` call, or that calls it without implementing the REQ-DEX-009c short-circuit, leaves `ready_to_ship` stale at `True` and fails this criterion either way — closing the zero-coverage gap the auditor identified (D2).

**AC-DEX-009a** (Unwanted) — Traces: REQ-DEX-009a. If a submitted damage quantity is outside `1..LineItem.quantity` (e.g. `6` or `0` against `quantity=5`, or any positive value against `quantity=null`), then the system shall reject the submission and leave `purchase_status`, `damaged_quantity`, and the parent Order's aggregate fields unchanged.

**AC-DEX-009b** (Event-Driven) — Traces: REQ-DEX-009b. When a LineItem already at `purchase_status="damaged_exchange"` with `damaged_quantity=3` receives a second valid submission of `2`, the system shall set `damaged_quantity=2` — not `5` — confirming overwrite rather than accumulation.

**AC-DEX-009c** (State-Driven) — Traces: REQ-DEX-009c, REQ-DEX-009d. While an Order's non-cancelled trackable LineItem set contains a LineItem with `purchase_status="damaged_exchange"`, `logistics_status="received"` and another LineItem with `purchase_status="unordered"`, `logistics_status="received"` — so that, absent the REQ-DEX-009c short-circuit, **both** rows individually satisfy the pre-existing `received`/`in_stock` disjunct and the unmodified rule computes `ready_to_ship=True` — the system shall compute `ready_to_ship=False` for that Order when `_recompute_order_aggregates` runs, and that Order's `status` field shall be computed using the same unmodified `logistics_status` rule as before (unaffected by the `damaged_exchange` short-circuit, even though `status` is written by the same underlying UPDATE that persists `ready_to_ship` — D16). (v1.3.0 D14 correction — the v1.2.0 fixture left the `damaged_exchange` row's `logistics_status` unpinned; acceptance.md pinned it to `"not_shipped"`, under which the unmodified `all(...)` already evaluates `False` on its own, so the criterion verified nothing. Pinning it to `"received"` makes the unmodified rule yield `True` and the modified rule yield `False`.)

**AC-DEX-010** (Event-Driven) — Traces: REQ-DEX-010. When a damage submission of `3` succeeds for a LineItem with zero existing notes, submitted by an authenticated user, the system shall create exactly one new `LineItemNote` with `note_type="파손/교환"`, `assignee="발주"`, `author` equal to that authenticated user (not `null` — D6 correction), and `content` that includes `"3"`.

**AC-DEX-011** (Unwanted) — Traces: REQ-DEX-011. If a damage submission succeeds for a LineItem whose pre-submission `logistics_status="not_shipped"` and `shipped_quantity=0`, then the system shall leave both fields at those exact pre-submission values.

**AC-DEX-012** (Event-Driven) — Traces: REQ-DEX-012. When the reorder-queue view is queried for a LineItem with `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, `sku` not null, and no Refund records, the system shall report that row's quantity as `3`, not `10`.

**AC-DEX-012a** (Event-Driven) — Traces: REQ-DEX-012 (결정 A). When the reorder-queue view is queried for the same LineItem as AC-DEX-012 but with a Refund totaling `1` against it, the system shall report that row's quantity as `2` (`max(3-1,0)`), not `9` (`max(10-1,0)`).

**AC-DEX-012b** (Unwanted) — Traces: REQ-DEX-012. If the reorder-queue view is queried for a LineItem with `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=1`, `sku` not null, and a Refund totaling `1` against it, then the system shall exclude that LineItem from the results entirely (`max(1-1,0)=0`, zero-quantity skip rule applied to the substituted base) — an unmodified implementation using `quantity` as the base would compute `max(10-1,0)=9` and wrongly include the row (D4 correction — `quantity` is now pinned explicitly so the criterion discriminates).

**AC-DEX-012c** (Unwanted) — Traces: REQ-DEX-012a. If the reorder-queue view is queried for a LineItem with `purchase_status="unordered"`, `quantity=10`, and `damaged_quantity=0` (untouched default), then the system shall report that row's quantity as `10`, unaffected by the REQ-DEX-012 substitution.

**AC-DEX-012d** (Unwanted) — Traces: REQ-DEX-012b. If a LineItem with `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, `sku` not null is queried via the 업체 자료 비교 뷰(`RunComparisonView`), Daily Review 다운로드 뷰(`DailyReviewExcelView`), Daily Review 업로드 확정 뷰(`UploadDailyReviewView`), or 발주 파일 생성 뷰(`GenerateOrderFileView`) for the same SKU, then the system shall report/aggregate a quantity based on `quantity` (`10`), not `damaged_quantity` (`3`), at every one of these four sites (D11 correction — v1.1.0 covered only 2 of 5 sites; this now covers 4 of the 5 in REQ-DEX-012b).

**AC-DEX-012e** (Unwanted) — Traces: REQ-DEX-012b. If a LineItem with `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, `sku` not null, and **not linked to any PurchaseOrder** (`purchase_orders__isnull=True`) is queried via the 업체 비교 목록 뷰(`VendorComparisonView`) for the same SKU — with a `VendorComparison` record present for that SKU so it appears in the response — then the view's internal SKU→수량 맵(`qty_by_sku`, built from the `Sum("quantity")` annotation at `backend/order/purchase_order_views.py:744-750`) shall hold `10` for that SKU, not `3`. This is deliberately a white-box assertion on `qty_by_sku`: the response rows the view emits (`purchase_order_views.py:808-833`) contain no quantity field at all, and with this fixture the only quantity-dependent outputs (`selected_distributor` / `candidate_basis`) are identical for `10` and `3`, so no black-box assertion on this view can discriminate (v1.3.1 D23 correction — v1.3.0 asserted "the system shall report a quantity", an observable this view does not produce). This criterion is scoped to unlinked `damaged_exchange` rows only (v1.3.0 D21 correction — `VendorComparisonView` has no linkage exception, unlike `GenerateOrderFileView`; an unpinned or PO-linked fixture makes the view report `0` and fails this criterion even against a correct implementation. See Exclusions for the PO-linked case this criterion does not cover).

**AC-DEX-012f** (Unwanted) — Traces: REQ-DEX-012c. If the 수기 발주확정 뷰(`ConfirmOrderView`) processes a request item for a `damaged_exchange` LineItem, then the system shall use the request body's `quantity` value exactly as submitted by the client — the system shall NOT read that LineItem's `quantity` or `damaged_quantity` field for this purpose (D3 correction — `ConfirmOrderView` is structurally different from the five sites in AC-DEX-012d/012e, not merely an unmodified sixth instance of the same pattern).

**AC-DEX-013** (Event-Driven) — Traces: REQ-DEX-013. When the backfill migration is applied to a fixture Order with a `damaged_exchange` LineItem (trackable, non-cancelled, **`logistics_status="received"`**) whose stored `ready_to_ship=True` was computed under the pre-migration rule, the system shall update that Order's `ready_to_ship` to `False` (v1.3.0 D13, new). The `logistics_status="received"` pin is load-bearing (v1.3.1 D24): under a `not_shipped` fixture the pre-existing `all(...)` rule already yields `False`, so a migration that copies `0033_backfill_order_ready_to_ship.py` verbatim — omitting the `damaged_exchange` short-circuit, the single most likely implementation error given plan.md instructs the implementer to follow 0033 — would pass this criterion. With `received` pinned, only a migration carrying the new short-circuit produces `False`.

**AC-DEX-013a** (Unwanted) — Traces: REQ-DEX-013a. If a second Order in the same migration run has no `damaged_exchange` LineItem (e.g. a single `in_stock` LineItem with **`sku` not null** and stored `ready_to_ship=True`, already correct under the existing rule), then the backfill shall NOT change that Order's `ready_to_ship` value — the migration processing one Order shall not disturb another (v1.3.0 D13, new).

---

## 구현 노트 (Implementation Notes)

**상태**: 미구현 (draft) — Run 단계 진행 후 이 섹션을 갱신한다.
