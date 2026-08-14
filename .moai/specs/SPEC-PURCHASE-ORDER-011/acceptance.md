---
id: SPEC-PURCHASE-ORDER-011
document: acceptance
version: 1.4.0
status: draft
updated: 2026-08-14
---

# 인수 기준 — SPEC-PURCHASE-ORDER-011 파손 교환 신청 페이지

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의 AC-DEX-XXX/REQ-DEX-XXX ID를 인용해 상호 추적된다. 모든 시나리오는 "구현이 조용히 잘못 동작해도 이 기준이 통과하는가?"를 기준으로 판별력을 갖도록 작성되었다 — 특히 `damaged_quantity` vs 전체 `quantity` 구분(REQ-DEX-012), "전체 출고 수량" 합산 범위(REQ-DEX-006), `logistics_status` 무변경(REQ-DEX-011), `ready_to_ship` 재계산(REQ-DEX-009c)에 집중한다.

**v1.2.0 변경 요지** (plan-auditor iteration 1 FAIL 대응): 시나리오 9를 D1(critical) 대응으로 전면 교체. 시나리오 9a(재접수 덮어쓰기)·9c(집계 단락 단위 검증) 추가. 시나리오 6/12/12b/12c에 `sku` not null 및(12c에) `quantity=10` 명시. 시나리오 12e를 4개 지점으로 확장하고 시나리오 12f(`VendorComparisonView`)·12g(`ConfirmOrderView`) 신규 추가. 시나리오 10에 `author` 검증 추가.

**v1.3.0 변경 요지** (plan-auditor iteration 2 FAIL 대응): **D14(blocking)** 시나리오 9c의 `damaged_exchange` 행 `logistics_status`를 `"not_shipped"`(무판별력)에서 `"received"`(판별력 확보)로 수정. **D20(blocking)** 시나리오 5c를 mixed-null(무판별력, SQL `SUM`이 NULL 무시)에서 all-null 픽스처(기대값 `0`)로 교체. **D21(blocking)** 시나리오 12f에 `purchase_orders__isnull=True`(PO 미연결) 명시 고정 — 그렇지 않으면 정상 구현도 실패. **D13(blocking)** 신규 시나리오 13/13a(`ready_to_ship` 백필 마이그레이션) 추가. **D15/D17(minor)** 회귀 스위트 목록에 `test_order_resync.py`/`test_spec_012.py:609`, `test_daily_review_upload.py` 추가. **D16** 시나리오 9c의 `status` 관련 서술을 "컬럼이 안 쓰인다"가 아니라 "규칙이 안 바뀐다"로 정정.

**v1.3.1 변경 요지** (plan-auditor iteration 3 FAIL의 잔여 blocking 2건 대응): **D24(blocking)** 시나리오 13의 `damaged_exchange` 행을 `logistics_status="received"`로 고정 — 미고정 시 `0033_backfill_order_ready_to_ship.py`를 그대로 베껴 `damaged_exchange` 단락을 누락한 마이그레이션도 통과했다(이 기준이 D13을 지탱하는 유일한 가드이므로 필수). 시나리오 13a의 두 번째 Order에 `sku` not null 고정 추가 — 백필 스코프가 "추적 가능 LineItem 1건 이상"이라 미고정 시 기준이 공허. **D23(blocking)** 시나리오 12f를 화이트박스 단언으로 재작성 — `VendorComparisonView`는 응답에 수량 필드를 내보내지 않고(`purchase_order_views.py:808-833`), 이 픽스처에서 수량 의존 출력이 `10`/`3` 모두 동일해 블랙박스로는 실행도 판별도 불가능했다.

**v1.4.0 변경 요지** (Run 단계에서 발견된 결함, plan-audit 3라운드 모두 놓침, 결정 G 반영 — 코드는 이미 구현·커밋되어 있고 이 문서만 그에 맞춘다): REQ-DEX-012의 무조건 `quantity→damaged_quantity` 치환이 안전하려면 `damaged_exchange`이면서 `damaged_quantity=0`인 행이 존재할 수 없어야 하는데, 그런 행을 만들 수 있는 레거시 쓰기 경로 3곳(`LineItemStatusUpdateView`, `LineItemBulkStatusUpdateView`, `UploadDailyReviewView`의 `선택="파손/교환"` 매핑)이 남아 있었다 — `TestUnorderedItemsViewDamagedExchange`의 기존 테스트 3건이 이 결함으로 실패했었다. 사용자는 그 3곳을 전면 차단하는 쪽을 선택했다(대안: `net_qty` 계산에 0-폴백을 추가하는 것 — 기각). 신규 시나리오 14/14a/14b(단건·일괄 상태 변경 API 차단, 다른 값은 정상 동작), 15/15a(Daily Review 엑셀 `선택="파손/교환"` 거부·보고, PurchaseOrder 미생성), 16/16a(프론트엔드 드롭다운에서 제외, 이미 그 상태인 행은 비활성 옵션으로 표시) 추가 — 전부 실제 커밋된 테스트(`test_spec_purchase_order_011.py::TestDamagedExchangeLegacyWritePathsBlocked`, `test_purchase_orders.py::TestLineItemStatusUpdateView`, `test_daily_review_upload.py::TestParseDailyReviewDamagedExchangeBlocked`/`TestUploadDamagedExchangeSelectionRejected`)의 실제 단언과 대조해 작성했다.

## 데이터 모델 시나리오

### 시나리오 1 — Traces: AC-DEX-001

**Given** 마이그레이션 적용 전 `quantity=10`, `purchase_status="unordered"`인 기존 LineItem 레코드가 존재한다.
**When** `damaged_quantity` 마이그레이션이 적용된다.
**Then** 그 LineItem을 다시 조회하면 `damaged_quantity=0`이며, `quantity`/`purchase_status` 등 기존 필드 값은 하나도 변경되지 않는다.

## 프론트엔드 진입점 시나리오

### 시나리오 2 — Traces: AC-DEX-002

**Given** 로그인한 관리자가 사이드바를 조회한다.
**When** "파손 교환" 메뉴 항목을 클릭한다.
**Then** `/damaged-exchange` 독립 페이지로 이동하며, 해당 페이지 모듈은 `OutboundPage`/`RackNumberPage` 컴포넌트와 `outboundApi`/`rackNumberApi`/`useOutboundQueries`/`useRackNumberQueries` 모듈 중 무엇도 import하지 않는다(별도 `damagedExchangeApi.ts`/`useDamagedExchangeQueries.ts` 사용을 코드 리뷰로 확인 — `ui/button`, `lib/axios` 같은 공용 프리미티브 공유는 이 기준의 대상이 아니다).

## ISBN 검색 시나리오

### 시나리오 3 — Traces: AC-DEX-003 (정확 일치만 허용)

**Given** `sku="9788956609959"`인 LineItem이 미출고 상태로 존재한다.
**When** ISBN 검색창에 마지막 자리가 빠진 `"978895660995"`(부분 문자열)을 입력해 검색한다.
**Then** 검색 결과가 비어 있다 — `icontains`/부분 일치였다면 매칭되었을 값이 정확 일치 구현에서는 매칭되지 않음을 확인한다.

### 시나리오 4 — Traces: AC-DEX-004 (미출고 정의 재사용)

**Given** 동일 SKU(`sku` not null)를 가진 LineItem 3건이 존재한다: (A) `logistics_status="not_shipped"`, `purchase_status="unordered"`; (B) `logistics_status="shipped"`, `purchase_status="unordered"`; (C) `logistics_status="not_shipped"`, `purchase_status="order_cancelled"`.
**When** 해당 SKU로 검색한다.
**Then** 결과에는 A 한 건만 포함되고 B(출고 완료)와 C(주문취소)는 제외된다.

### 시나리오 4b — Traces: AC-DEX-004a (이미 접수된 행 포함 + 배지)

**Given** 동일 SKU를 가진 LineItem 중 `purchase_status="damaged_exchange"`, `logistics_status="not_shipped"`인 행이 존재한다.
**When** 해당 SKU로 검색한다.
**Then** 그 행이 결과에 포함되며, 응답/화면에서 다른 행과 구분되는 배지(또는 동등한 플래그)로 표시된다.

### 시나리오 5 — Traces: AC-DEX-005 ("전체 출고 수량" = 추적 가능·비취소 LineItem만 합산, 결정 B 확정 반영)

**Given** 하나의 Order에 LineItem 4건이 속해 있다: (1) 검색 대상 SKU, `quantity=4`, `sku` not null, `purchase_status="unordered"`; (2) 다른 SKU, `quantity=9`, `sku` not null, `purchase_status="unordered"`; (3) 다른 SKU, `quantity=100`, `purchase_status="order_cancelled"`; (4) `sku=null`, `quantity=50`.
**When** 검색 대상 SKU((1))로 검색한다.
**Then** 결과 행의 "주문 수량"은 `4`(그 행 자신의 quantity)이고, "전체 출고 수량"은 `13`(4+9, 추적 가능·비취소 행만 합산)이다 — `163`(모든 행 합산), `4`(행 자신), `2`(행 개수) 어느 것도 아니다.

### 시나리오 5a — Traces: AC-DEX-005a (ready_to_ship 3-state, null 보존)

**Given** 부모 Order의 `ready_to_ship`이 `null`이다 — 이는 검색 매칭 행의 존재(적어도 하나의 추적 가능 LineItem이 있다는 증거)와 모순되지 않도록, 재계산이 아직 반영되지 않은 stale 상태(예: 마이그레이션/수기 갱신으로 직접 `null`을 설정한 상태)로 구성한다.
**When** 그 Order에 속한 LineItem이 검색 결과에 포함된다.
**Then** "오늘 출고 가능 여부"는 `null`로 표시된다 — `false`로 강제 변환되지 않는다.

### 시나리오 5b — Traces: AC-DEX-005b (취소·미추적 행은 "전체 출고 수량"에서 제외)

**Given** 시나리오 5와 동일한 4건짜리 픽스처(취소 행 `quantity=100`, `sku=null` 행 `quantity=50` 포함)가 있다.
**When** 검색 대상 SKU로 검색한다.
**Then** "전체 출고 수량" 응답값에 `100`도 `50`도 반영되지 않는다 — 모든 행을 단순 합산하는 구현이었다면 나왔을 `163`과 대조해 이 기준이 그런 구현을 잡아낸다.

### 시나리오 5c — Traces: AC-DEX-005c (null quantity → 0 취급, v1.3.0 D20 재작성)

**Given** 부모 Order의 추적 가능·비취소 LineItem이 두 건이며, **둘 다** `quantity=null`이다(`9`처럼 non-null 값을 가진 형제 행이 전혀 없음).
**When** 검색 대상 SKU(둘 중 하나)로 검색한다.
**Then** "전체 출고 수량"은 `0`으로 보고된다 — `null`/`None`이 아니다. (v1.3.0 D20 정정 — v1.2.0은 null 1건 + `quantity=9` 1건 픽스처를 썼는데, SQL `SUM`은 NULL을 무시하므로 `Coalesce` 유무와 무관하게 `9`가 반환되어 이 기준이 아무것도 검증하지 못했다. 추적 가능·비취소 LineItem 전원이 null일 때만 `Coalesce(Sum("quantity"), 0)`의 유무가 관찰 가능한 차이 — `0` vs `null` — 를 만든다.)

### 시나리오 6 — Traces: AC-DEX-006 (ready_to_ship 읽기 전용, 재계산 금지)

**Given** Order의 `ready_to_ship`이 DB에 `True`로 저장되어 있으나, 그 이후 동일 Order에 `sku` not null, `purchase_status="cs_required"`인 LineItem이 추가되어 있어 "만약 지금 재계산한다면" `False`가 나올 상황이다(`sku` not null 명시 — 그렇지 않으면 미추적 행이 되어 재계산해도 여전히 `True`가 나와 이 기준이 판별력을 잃는다).
**When** 그 Order에 속한 LineItem이 검색 결과에 포함된다.
**Then** 화면에는 저장된 값 그대로 `True`가 표시된다 — 검색 요청 처리 과정에서 `_recompute_order_aggregates`(SPEC-ORDER-012 REQ-RTS-002, REQ-DEX-009c로 확장됨)를 호출하는 재계산 로직이 실행되지 않는다(회귀: `Order.ready_to_ship` 레코드 자체도 이 요청 전후로 변경되지 않는다).

### 시나리오 7 — Traces: AC-DEX-007 (매칭 없음 → 빈 결과)

**Given** 존재하지 않는 ISBN `"0000000000000"`이다.
**When** 해당 값으로 검색한다.
**Then** HTTP 성공 응답과 함께 빈 결과 목록을 받는다 — 404/500 오류가 아니다.

## 파손 신고 제출 시나리오

### 시나리오 8 — Traces: AC-DEX-008 (기본값 1, 서버측 범위 검증)

**Given** 검색 결과 행이 화면에 렌더링되어 있다.
**When** 파손 수량 입력 컨트롤을 확인하고, `LineItem.quantity`를 초과하는 값으로 제출을 시도한다.
**Then** 입력값은 `1`로 미리 채워져 있고, 제출은 최소한 서버 측에서 거부된다(클라이언트 측 검증이 우회되거나 비활성화된 요청을 서버에 직접 보내도 동일하게 거부되어야 한다).

### 시나리오 9 — Traces: AC-DEX-009 (정상 접수 → damaged_quantity ≠ quantity, ready_to_ship 재계산은 신규 단락 때문)

**Given** `quantity=8`, `purchase_status="unordered"`, `logistics_status="received"`인 LineItem 하나만 속한 Order가 있다 — 이 LineItem이 유일한 추적 가능 행이므로 기존 `logistics_status=="received"` disjunct에 의해 Order의 `ready_to_ship=True`로 이미 계산되어 있다.
**When** 파손 수량 `3`으로 접수 요청을 제출한다.
**Then** 해당 LineItem은 `purchase_status="damaged_exchange"`, `damaged_quantity=3`(`8`이 아님)으로 갱신되고, 부모 Order의 `ready_to_ship`은 재계산되어 `False`로 바뀐다. **이 전환은 `logistics_status`가 바뀌어서가 아니다** — REQ-DEX-011에 의해 `logistics_status`는 여전히 `"received"`로 남는다. 전환의 원인은 REQ-DEX-009c가 추가하는 `damaged_exchange` 단락(기존 `cs_required` 단락과 동일한 방식)이 `all(received/in_stock)` 판정보다 먼저 적용되기 때문이다. 이 시나리오는 `_recompute_order_aggregates([li.order_id])` 호출을 아예 생략한 구현과, 호출은 하되 REQ-DEX-009c 단락을 구현하지 않은 구현 양쪽 모두에서 `ready_to_ship`이 `True`로 정체되므로 실패한다.

### 시나리오 9a — Traces: AC-DEX-009a (범위 밖 거부, quantity=null 거부)

**Given** `quantity=5`인 LineItem이 있다.
**When** 파손 수량 `6`으로 접수를 시도한다.
**Then** 요청이 거부되고, `purchase_status`/`damaged_quantity`/부모 Order 집계 모두 접수 이전 값 그대로 유지된다. 동일하게 `quantity=null`인 LineItem에 어떤 양수 값을 제출해도 거부된다(범위가 공집합이므로).

### 시나리오 9b — Traces: AC-DEX-009b (재접수는 덮어쓰기)

**Given** 이미 `purchase_status="damaged_exchange"`, `damaged_quantity=3`인 LineItem이 있다(`quantity=8`).
**When** 같은 LineItem에 파손 수량 `2`로 재접수 요청을 제출한다.
**Then** `damaged_quantity=2`가 된다 — `5`(3+2 누적)가 아니다.

### 시나리오 9c — Traces: AC-DEX-009c (집계 단락 자체의 단위 수준 검증, v1.3.0 D14 재작성)

**Given** 하나의 Order에 추적 가능·비취소 LineItem 두 건이 있다: (a) `purchase_status="damaged_exchange"`, **`logistics_status="received"`**; (b) `purchase_status="unordered"`, `logistics_status="received"`. 두 행 모두 개별적으로 기존 `received`/`in_stock` disjunct를 만족하므로, **REQ-DEX-009c 단락이 없다면** `all(...)` 판정은 두 행 모두에 대해 참이 되어 `ready_to_ship=True`가 산출된다. (v1.3.0 D14 정정 — v1.2.0은 (a)의 `logistics_status`를 `"not_shipped"`로 고정했는데, 그 경우 (a) 행이 신규 단락 없이도 `all(...)`을 이미 `False`로 만들어 이 기준이 무엇도 검증하지 못했다. `"received"`로 고정해야 무수정 규칙=`True`, 수정된 규칙=`False`로 갈라진다.)
**When** 이 Order에 대해 `_recompute_order_aggregates`가 직접 호출된다(엔드포인트를 거치지 않고 함수 자체를 단위 테스트).
**Then** `ready_to_ship=False`로 계산된다(damaged_exchange 단락이 `all(...)` 판정보다 먼저 적용되어 가로챔 — 무수정 코드라면 `True`가 나왔을 것과 대조). 같은 호출로 `status`(물류 집계) 필드도 계산되지만, 그 값은 이 Order의 `logistics_status` 데이터에 대해 기존 규칙 그대로 산출된다 — `damaged_exchange` 단락의 영향을 받지 않는다(REQ-DEX-009d; `status`와 `ready_to_ship`이 같은 UPDATE로 함께 쓰인다는 사실 자체는 이 기준의 대상이 아니다 — "규칙이 바뀌지 않는다"만 검증한다).

### 시나리오 10 — Traces: AC-DEX-010 (메모 자동 생성, 수량·작성자 정보 포함)

**Given** 노트가 0건인 LineItem이 있고, 인증된 사용자(`request.user`)가 요청을 제출한다.
**When** 파손 수량 `3`으로 접수가 성공한다.
**Then** 그 LineItem에 신규 `LineItemNote`가 정확히 1건 생성되며, `note_type="파손/교환"`, `assignee="발주"`, `author`가 그 인증된 사용자와 동일(`null`이 아님)이고 `content`에 `"3"`이 포함되어 있다 — 노트가 0건이거나 2건 생성되지 않으며, `note_type`이 빈 값이나 다른 유형("CS필요" 등)으로 잘못 저장되지 않으며, `author=None`으로 저장하는 구현(기존 배치 흐름의 관례를 그대로 답습한 구현)은 이 기준에서 실패한다.

### 시나리오 11 — Traces: AC-DEX-011 (logistics_status/shipped_quantity 무변경)

**Given** `logistics_status="not_shipped"`, `shipped_quantity=0`인 LineItem이 있다.
**When** 파손 수량 `4`로 접수가 성공한다.
**Then** 접수 이후에도 `logistics_status="not_shipped"`, `shipped_quantity=0` 그대로다 — 접수 수량만큼 `shipped_quantity`가 증가하거나 `logistics_status`가 변경되지 않는다.

## Order.ready_to_ship 백필 마이그레이션 시나리오 (v1.3.0 신규, D13)

### 시나리오 13 — Traces: AC-DEX-013 (기존 파손 Order의 stale True가 False로 갱신됨)

**Given** 백필 마이그레이션 적용 전, `damaged_exchange` LineItem(추적 가능, 비취소, **`logistics_status="received"`**)을 가진 Order가 있고 그 Order의 저장된 `ready_to_ship`이 (구 규칙으로 계산된) `True`다. — `logistics_status="received"` 고정은 판별력의 핵심이다(v1.3.1 D24): `not_shipped`로 두면 기존 `all(...)` 규칙만으로도 이미 `False`가 나오므로, `0033_backfill_order_ready_to_ship.py`를 그대로 베껴 `damaged_exchange` 단락 분기를 빠뜨린 마이그레이션(plan.md가 0033을 따르라고 지시하므로 가장 발생 확률이 높은 구현 오류)도 이 기준을 통과해 버린다.
**When** 백필 마이그레이션이 적용된다.
**Then** 그 Order의 `ready_to_ship`이 `False`로 갱신된다 — 이 SPEC이 배포되기 전부터 존재하던 파손 Order도 새 페이지에서 더 이상 stale `True`로 표시되지 않는다.

### 시나리오 13a — Traces: AC-DEX-013a (무관한 다른 Order는 영향받지 않음)

**Given** 시나리오 13과 같은 마이그레이션 실행 범위 안에, `damaged_exchange` LineItem이 전혀 없는 두 번째 Order가 있다 — 예: `sku`가 null이 아닌 `in_stock` LineItem 1건만 있고 저장된 `ready_to_ship=True`(기존 규칙으로도 이미 정확한 값). `sku` not null 고정이 필요하다(v1.3.1 D24): 백필 범위가 "추적 가능 LineItem 1건 이상"인 Order이므로, `sku`가 null이면 이 Order는 애초에 마이그레이션 대상 밖이라 기준이 공허해진다.
**When** 백필 마이그레이션이 적용된다(시나리오 13과 동일한 실행).
**Then** 이 두 번째 Order의 `ready_to_ship`은 `True`로 그대로 유지된다 — 시나리오 13의 Order를 처리하는 과정이 이 무관한 Order를 건드리지 않는다.

## 파손 접수 경로 배타성 시나리오 (v1.4.0 신규, 결정 G — Run 단계에서 발견된 결함)

### 시나리오 14 — Traces: AC-DEX-014 (단건 상태 변경 API 차단)

**Given** `purchase_status="unordered"`인 LineItem이 있다.
**When** 단건 상태 변경 엔드포인트(`PATCH .../line-items/<pk>/status/`)로 `purchase_status="damaged_exchange"`를 요청한다.
**Then** HTTP 400이 반환되고, 그 LineItem의 `purchase_status="unordered"`, `damaged_quantity=0`이 그대로 유지된다.

### 시나리오 14a — Traces: AC-DEX-014a (일괄 상태 변경 API 차단, 전체 배치 거부)

**Given** `purchase_status="unordered"`인 LineItem 2건이 있다.
**When** 일괄 상태 변경 엔드포인트(`PATCH .../line-items/bulk-status/`)로 두 LineItem의 id를 포함해 `purchase_status="damaged_exchange"`를 요청한다.
**Then** HTTP 400이 반환되고, **두 LineItem 모두** `purchase_status`가 요청 이전 값 그대로 유지된다 — 일부만 반영되는 부분 업데이트는 없다.

### 시나리오 14b — Traces: AC-DEX-014b (다른 값은 정상 동작, 회귀 방지)

**Given** 시나리오 14와 동일한 LineItem(여전히 `purchase_status="unordered"`)이 있다.
**When** 같은 단건 상태 변경 엔드포인트로 `purchase_status="cs_required"`(damaged_exchange가 아닌 값)를 요청한다.
**Then** HTTP 200이 반환되고 `purchase_status="cs_required"`로 정상 갱신된다 — REQ-DEX-014의 거부는 `damaged_exchange` 값 하나에만 적용되며, 엔드포인트 전체를 막는 것이 아니다.

### 시나리오 15 — Traces: AC-DEX-015 (Daily Review 엑셀 파손/교환 선택 거부·보고)

**Given** `purchase_status="unordered"`인 LineItem이 있고, Daily Review 엑셀 업로드 파일의 해당 행 `선택` 컬럼 값이 `"파손/교환"`이다.
**When** 이 파일을 업로드한다.
**Then** HTTP 201과 함께 `skipped_count == 1`, `errors == [{"name": <주문명>, "sku": <sku>, "reason": "damaged_exchange_requires_dedicated_page"}]`가 반환된다. 그 LineItem의 `purchase_status`는 `"unordered"`로 그대로이고 `damaged_quantity=0`이며, 새로 생성된 `LineItemNote`는 0건이다 — SPEC-PURCHASE-ORDER-010이 원래 기대했던 "CS 분기가 자동으로 damaged_exchange를 설정한다"는 동작(REQ-DMG-003)이 뒤집힌 것을 확인하는 시나리오다.

### 시나리오 15a — Traces: AC-DEX-015a (거부된 선택은 PurchaseOrder를 만들지 않음)

**Given** 시나리오 15와 동일한 업로드 파일(행이 이것 하나뿐)이 있다.
**When** 업로드를 처리한다.
**Then** 새로 생성된 `PurchaseOrder`가 0건이다 — 거부된 선택이 우회 경로로 발주를 만들지 않는다.

### 시나리오 16 — Traces: AC-DEX-016 (프론트엔드 드롭다운에서 제외, 라벨은 유지)

**Given** `frontend/src/services/purchaseOrderApi.ts`의 export를 조회한다.
**When** `PURCHASE_STATUS_OPTIONS`(수동 선택 가능 목록)와 `PURCHASE_STATUS_LABELS`(전체 라벨 조회 맵)를 각각 확인한다.
**Then** `PURCHASE_STATUS_OPTIONS`에는 `value: 'damaged_exchange'`인 항목이 없고, `PURCHASE_STATUS_LABELS.damaged_exchange === '파손/교환'`이다 — 두 맵을 모두 지우거나, `PURCHASE_STATUS_OPTIONS`를 `PURCHASE_STATUS_LABELS`에서 필터링해 파생시키다가 필터를 빠뜨리는 구현은 이 기준에서 실패한다.

### 시나리오 16a — Traces: AC-DEX-016a (이미 파손/교환인 행은 비활성 옵션으로 표시)

**Given** 발주 관리 화면(미발주 품목 테이블)에 `purchase_status="damaged_exchange"`인 행이 렌더링된다.
**When** 그 행의 상태 변경 `<select>`를 확인한다.
**Then** `<option value="damaged_exchange" disabled>파손/교환</option>`이 다른 선택 가능 옵션들과 함께 렌더링되어 현재 선택값으로 표시된다 — 이 옵션이 없으면 브라우저가 목록의 첫 옵션("미발주")을 선택된 것처럼 표시해 실제 상태를 오도한다.

## 재발주 큐 수량 보정 시나리오

### 시나리오 12 — Traces: AC-DEX-012 (damaged_quantity 기준, 환불 없음)

**Given** `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, `sku` not null인 LineItem이 있고 관련 Refund 레코드가 없다.
**When** 재발주 큐 조회(`UnorderedItemsView`)를 요청한다.
**Then** 그 행의 재발주 수량이 `3`으로 보고된다 — `10`(원래 quantity)이 아니다.

### 시나리오 12b — Traces: AC-DEX-012a (환불 차감이 damaged_quantity에도 적용)

**Given** 시나리오 12와 동일한 LineItem에 수량 `1`의 Refund 레코드가 존재한다.
**When** 재발주 큐 조회를 요청한다.
**Then** 재발주 수량이 `2`(`max(3-1,0)`)로 보고된다 — `9`(`max(10-1,0)`, quantity 기준 계산)가 아니다.

### 시나리오 12c — Traces: AC-DEX-012b (0이면 제외 규칙, damaged_quantity 기준 적용)

**Given** `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=1`, `sku` not null인 LineItem에 수량 `1`의 Refund 레코드가 존재한다(순감 0).
**When** 재발주 큐 조회를 요청한다.
**Then** 그 LineItem은 결과에서 완전히 제외된다(`max(1-1,0)=0`) — `quantity=10`을 명시했으므로, `quantity` 기준(무수정 코드)으로 계산했다면 `max(10-1,0)=9`가 되어 여전히 결과에 포함되었을 상황과 대조된다.

### 시나리오 12d — Traces: AC-DEX-012c (unordered 행은 영향 없음 — 회귀 방지)

**Given** `purchase_status="unordered"`, `quantity=10`, `damaged_quantity=0`(건드리지 않은 기본값)인 LineItem이 있다.
**When** 재발주 큐 조회를 요청한다.
**Then** 재발주 수량이 `10`으로 그대로 보고된다 — 이번 SPEC 적용 전과 동일(회귀 없음).

### 시나리오 12e — Traces: AC-DEX-012d (다른 4개 조회 지점은 quantity 기준 유지)

**Given** `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, `sku` not null인 LineItem이 있다.
**When** 업체 자료 비교 뷰(`RunComparisonView`), Daily Review 다운로드 뷰(`DailyReviewExcelView`), Daily Review 업로드 확정 뷰(`UploadDailyReviewView`), 발주 파일 생성 뷰(`GenerateOrderFileView`)를 각각 같은 SKU로 조회한다.
**Then** 네 뷰 모두 여전히 `quantity`(10) 기준으로 계산된 수량을 반환한다 — `damaged_quantity`(3)로 대체되지 않는다. REQ-DEX-012b가 열거하는 5곳 중 4곳을 커버한다(다섯 번째는 시나리오 12f).

### 시나리오 12f — Traces: AC-DEX-012e (VendorComparisonView, v1.3.0 D21 재작성 — PO 미연결 고정)

**Given** 시나리오 12e와 동일한 LineItem(`damaged_exchange`, `quantity=10`, `damaged_quantity=3`, `sku` not null)이되, **어떤 PurchaseOrder에도 연결되어 있지 않다**(`purchase_orders__isnull=True`) — 그리고 해당 SKU에 대한 `VendorComparison` 레코드가 존재한다(그렇지 않으면 이 SKU가 응답의 `results`에 아예 나타나지 않는다).
**When** 업체 비교 목록 뷰(`VendorComparisonView`)를 같은 SKU로 조회한다.
**Then** 뷰 내부의 SKU→수량 맵 `qty_by_sku`(`backend/order/purchase_order_views.py:744-750`의 `Sum("quantity")` 어노테이션으로 생성)가 해당 SKU에 대해 `10`을 담는다 — `3`이 아니다. 이 기준은 의도적으로 화이트박스 단언이다(v1.3.1 D23 정정): 이 뷰가 실제로 내보내는 응답 행(`purchase_order_views.py:808-833`)에는 수량 필드 자체가 없고, 이 픽스처에서 수량에 의존하는 유일한 출력인 `selected_distributor`/`candidate_basis`는 `10`이든 `3`이든 동일하므로 블랙박스 단언으로는 판별이 불가능하다. v1.3.0은 "수량이 보고된다"고 썼으나 그런 관측값은 존재하지 않았다. (v1.3.0 D21 정정 — v1.2.0은 PurchaseOrder 연결 여부를 고정하지 않았다. `VendorComparisonView`는 `purchase_orders__isnull=True`인 LineItem만 집계하며 `damaged_exchange`에 대한 링크 예외가 없으므로, 이 SKU가 PO에 연결되어 있으면 — 파손/교환 품목은 현실적으로 이미 원래 PO에 연결되어 있는 경우가 흔하다 — 이 뷰는 `0`을 보고하고 "정상 구현"조차 이 기준을 만족시킬 수 없었다. PO-연결 케이스는 `spec.md` Exclusions에 알려진 미검증 공백으로 남아 있다.)

### 시나리오 12g — Traces: AC-DEX-012f (ConfirmOrderView, quantity를 요청 바디에서 받으므로 구조적으로 무관)

**Given** `damaged_exchange` LineItem 하나가 있고, 수기 발주확정 요청 바디의 해당 항목에 `quantity=7`이 명시되어 있다(LineItem 자신의 `quantity`/`damaged_quantity` 값과 무관하게 임의의 값).
**When** 수기 발주확정 뷰(`ConfirmOrderView`)로 이 요청을 확정한다.
**Then** 확정 결과는 요청 바디의 `7`을 그대로 사용한다 — 이 뷰는 `LineItem.quantity`도 `LineItem.damaged_quantity`도 조회하지 않으므로, LineItem의 두 필드 값을 어떻게 바꿔도 이 뷰의 동작에는 영향이 없다(구조적 무관성 확인).

## 품질 게이트 (Quality Gate)

- 백엔드 pytest: REQ-DEX-001~016(하위 항목 005a/006a/006b/009a/009b/009c/009d/012a/012b/012c/013a/014a/016a 포함) 전 항목에 대해 최소 1개 이상의 테스트 매핑(AC-DEX-001~016, 하위 004a/005a/005b/005c/009a/009b/009c/012a~012f/013a/014a/014b/015a 전량 포함).
- **파손 접수 경로 배타성 테스트(v1.4.0 신규, 결정 G)**: `backend/order/tests/test_spec_purchase_order_011.py::TestDamagedExchangeLegacyWritePathsBlocked`(3개), `test_purchase_orders.py::TestLineItemStatusUpdateView::test_patch_damaged_exchange_rejected`, `test_daily_review_upload.py::TestParseDailyReviewDamagedExchangeBlocked`/`TestUploadDamagedExchangeSelectionRejected`가 REQ-DEX-014/014a/015를 커버한다. `TestUnorderedItemsViewDamagedExchange`의 픽스처가 `damaged_quantity`를 명시적으로 채우도록 갱신되어 있어야 한다(그렇지 않던 3개 테스트가 원래 이 결함으로 실패했음).
- pytest 실행은 **순차 실행**만 허용 — 원격 공유 MySQL 테스트 DB 특성상 동시 실행 시 무관한 테스트가 가짜로 실패할 수 있다.
- **기존 특성화 테스트 확인(신규 작성 아님)**: `_recompute_order_aggregates`의 `damaged_exchange` 단락(REQ-DEX-009c) 추가 전, `backend/order/tests/test_spec_012.py`의 `TestRecomputeOrderAggregatesReadyToShip` 클래스(9개 테스트 — `cs_required` 단락, `all(received/in_stock)` 판정, 추적 가능 LineItem 0건→`None` 세 분기 전부 커버)가 그대로 통과하는지 확인한다(plan.md M1.5). 이 9개는 새로 작성하는 것이 아니라 기존에 이미 존재하는 스위트다.
- 검색 엔드포인트 쿼리 수 테스트: 결과 행 수(예: 2건 vs 10건 매칭)와 무관하게 고정된 쿼리 수임을 `django.test.utils.CaptureQueriesContext` 또는 동등한 방법으로 증명하는 테스트 최소 1건 포함(N+1 회귀 방지, plan.md "기술적 접근" 참조).
- **백필 마이그레이션 쿼리 수 테스트(v1.3.0 신규, D13)**: `0033_backfill_order_ready_to_ship.py` 선례와 동일하게, Order 수와 무관하게 고정된 쿼리 수(1 SELECT + 1 `bulk_update`)임을 증명하는 테스트 최소 1건 포함.
- 프론트엔드 테스트: ISBN 검색 폼 제출, 결과 테이블 렌더링(배지 포함), 행별 파손 수량 입력(기본값/서버측 범위 검증), 접수 성공/실패 처리에 대한 테스트 포함.
- 회귀 테스트: 발주 관리 페이지(`/purchase-orders`, `UnorderedItemsView` 소비 화면), SPEC-PURCHASE-ORDER-010 기존 테스트 스위트(`test_purchase_order_models.py`, `test_purchase_orders.py`), SPEC-ORDER-012 기존 테스트 스위트(`test_spec_012.py`, `test_backfill_order_ready_to_ship_migration.py`)와 `OrderDetailPage.test.tsx`(REQ-DEX-009c가 `ready_to_ship`의 기존 소비자에도 영향을 주므로, "회귀 없음"이 아니라 "의도된 변경 반영"을 확인하는 목적), **`test_order_resync.py`/`test_spec_012.py:609`(`test_resync_does_not_change_ready_to_ship`, v1.3.0 신규 — D15가 추가한 `OrderResyncView` 소비 경로 확인)**, **`test_daily_review_upload.py`(v1.3.0 신규 — D17, `damaged_exchange` 행이 `_recompute_order_aggregates`를 실제로 경유하는 유일한 기존 스위트, 25건의 `damaged_exchange` 픽스처를 포함하나 `ready_to_ship` 단언은 없음을 사전 확인함)** 전량 통과.
- 마이그레이션: `damaged_quantity` 필드 마이그레이션과 `ready_to_ship` 백필 마이그레이션 적용 후 기존 데이터 손실/오류 없이 `python manage.py migrate` 성공.
- Exclusions 위반 없음: `book.Info.qty`, `order.WarehouseStock`, `LineItem.fulfillment_status`, `Order.status`를 도출하는 규칙(REQ-DEX-009d — 컬럼 자체는 매 호출마다 다시 쓰이므로 "컬럼 write 없음"이 아니라 "규칙 불변"이 검증 대상), `RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView`/`ConfirmOrderView`의 수량 계산에 대한 변경이 diff에 존재하지 않아야 한다. `Order.ready_to_ship`은 Exclusion이 아니다 — REQ-DEX-009c가 그 계산 규칙을 의도적으로 수정하고 REQ-DEX-013이 기존 데이터를 백필한다. `damaged_exchange ⇒ damaged_quantity >= 1` 불변식의 모델 레벨 강제(`clean()`/`save()` 오버라이드, DB 제약)는 diff에 존재하지 않아야 한다 — REQ-DEX-014/015가 강제하는 엔드포인트 레벨 검사만 범위 안이다(v1.4.0 신규, 결정 G, 알려진 한계).
- **운영 커뮤니케이션(v1.4.0 신규, 결정 G)**: Daily Review 엑셀 `선택` 컬럼에 "파손/교환"을 사용해 오던 팀에게 신규 `/damaged-exchange` 페이지로 전환하라는 공지가 전달되었는지 확인 — 이는 자동화된 테스트로 검증할 수 없는 운영 변경사항이므로 배포 체크리스트에서 별도 확인한다.

## Definition of Done

- [ ] `LineItem.damaged_quantity` 필드 + 마이그레이션 적용 완료
- [ ] ISBN 검색 엔드포인트 + 파손 접수 엔드포인트(재접수 덮어쓰기 포함) 구현 완료(배치 쿼리 설계 확인)
- [ ] `UnorderedItemsView`의 재발주 수량 계산 보정 완료(`damaged_exchange` 행 한정)
- [ ] `_recompute_order_aggregates`의 `damaged_exchange` 단락 추가 완료 — 선행 기존 특성화 테스트(`test_spec_012.py` T2) 통과 확인 후 구현(REQ-DEX-009c/009d)
- [ ] `ready_to_ship` 백필 마이그레이션 구현 완료 — 배치 쿼리 설계 확인(REQ-DEX-013/013a, v1.3.0 신규)
- [x] 파손 접수 레거시 경로 3곳(단건/일괄 상태 변경 API, Daily Review 엑셀 `선택` 매핑) 차단 구현 완료 — 이미 커밋됨(REQ-DEX-014/014a/015, v1.4.0 신규, 결정 G)
- [x] 프론트엔드 `PURCHASE_STATUS_OPTIONS`에서 `damaged_exchange` 제외 + `PURCHASE_STATUS_LABELS` 신설 + 비활성 옵션 렌더링 구현 완료 — 이미 커밋됨(REQ-DEX-016/016a, v1.4.0 신규, 결정 G)
- [ ] REQ-DEX-001~016(하위 항목 포함, 총 29개 항목) 및 AC-DEX-001~016(하위 항목 포함, 총 34개 항목) 테스트 전량 통과
- [ ] 신규 `/damaged-exchange` 프론트엔드 페이지 + 사이드바 메뉴 항목 구현 완료
- [ ] SPEC-PURCHASE-ORDER-010, 발주 관리 페이지, SPEC-ORDER-012(`ready_to_ship`, `OrderResyncView` 포함), `test_daily_review_upload.py` 기존 테스트 스위트(백엔드+프론트엔드) 확인 완료 — SPEC-ORDER-012 관련 스위트는 "회귀 없음"이 아니라 "의도된 변경 반영" 기준
- [x] 결정 A(환불 차감 적용 범위)와 결정 B("전체 출고 수량" 합산 범위 — 취소·미추적 행 제외)에 대한 사용자 확인 완료(2026-08-14, `spec.md` 설계 결정 섹션 참조)
- [x] 결정 D(`LineItemNote.author=request.user`)에 대한 사용자 확인 완료(2026-08-14)
- [x] 결정 E(공유 함수 `_recompute_order_aggregates` 범위 확장, fan-in 8→9, 다운스트림 소비자 전수 명시)에 대한 사용자 확인 완료(2026-08-14)
- [x] 결정 F(`ready_to_ship` 1회성 백필 마이그레이션 신규 추가)에 대한 사용자 확인 완료(2026-08-14, v1.3.0 신규 — D13)
- [x] 결정 G(파손 접수 레거시 경로 3곳 차단, `damaged_quantity==0` 폴백 대안 기각, 모델 레벨 불변식 미강제를 알려진 한계로 기록)에 대한 사용자 확인 완료(2026-08-14, v1.4.0 신규 — Run 단계에서 발견)
- [ ] `product.md` 기능 목록에 SPEC-PURCHASE-ORDER-011 항목 추가(sync 단계)
- [ ] `spec.md` `status: draft → completed` 전이 및 HISTORY 갱신
