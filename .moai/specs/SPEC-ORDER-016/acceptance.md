---
id: SPEC-ORDER-016
document: acceptance
version: 1.0.3
status: draft
updated: 2026-08-12
---

# 인수 기준 — SPEC-ORDER-016 강제 출고 처리

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의
AC-FORCE-XXX / REQ-FORCE-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록과 검증 레이어 표기는 `spec.md` ACCEPTANCE CRITERIA 절의 동일
AC 항목이 선언한 것과 **완전히 일치**한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다.

**검증 레이어 표기**: `[BE]`는 백엔드 pytest(`backend/order/tests/test_spec_016.py`), `[FE]`는
프론트엔드 vitest + React Testing Library(colocate 테스트 파일). 두 레이어가 모두 필요한 시나리오는
`[BE][FE]`로 표시한다.

공통 전제(별도 명시가 없는 한): 인증된 담당자가 `/outbound`에서 출고 처리를 1회 실행해 매칭 실패
항목이 포함된 결과를 보고 있는 상태다.

## 자격과 입력 게이트

### AC-FORCE-001 — 자격 행에만 컨트롤이 렌더된다 `[FE]`

Traces: REQ-FORCE-001, REQ-FORCE-019

- **Given**: 매칭 실패 섹션에 다음 4개 행이 있다 — (1) `line_item_not_found` / 수량 4,
  (2) `line_item_not_found` / 수량 0, (3) `order_not_found` / 수량 3,
  (4) `multiple_line_items` / 수량 3. 수량초과 섹션에도 1건이 있다.
- **When**: 결과 화면을 렌더링하고 전체 선택을 실행한다.
- **Then**: 선택 컨트롤과 대상 지정 컨트롤은 행 (1)에만 존재한다. 행 (2)(3)(4)와 수량초과 행에는
  둘 다 없다. 전체 선택 후 선택된 행은 (1) 하나뿐이다.

### AC-FORCE-002 — 게이트 위반 7종은 요청 전체를 HTTP 400으로 거부한다 `[BE]`

Traces: REQ-FORCE-002

- **Given**: `Order.name="#37349"`(O1)과 `#40000`(O2)이 있다. O1에는 정상 LineItem LA(후보가 이
  하나뿐인 주문 구성), `purchase_status="order_cancelled"`인 LC, `sku=null`인 LN이 있고, O2에는
  정상 LineItem L2가 있다. 모든 케이스에서 요청에는 **정상적으로 지정된 유효한 행 1건**을 함께
  넣는다.
- **When**: 위반 행 1건을 섞은 요청을 7가지로 나누어 제출한다 — (a) 구조가 깨진 행(dict 아님 또는
  필수 키 누락), (b) 대상 식별자 미지정, (c) 존재하지 않는 대상 식별자, (d) 어떤 Order와도 일치하지
  않는 주문 식별자, (e) `#37349` 행에 O2 소속 L2 지정, (f) LC 지정, (g) LN 지정.
- **Then**: 7가지 모두 HTTP 400으로 응답한다. LA, LC, LN, L2 어느 것도 변경되지 않으며, 함께 제출한
  **유효한 행도 반영되지 않는다**. (b)에서 O1의 유일한 후보 LA가 자동 선택되는 일도 없다.

## 후보 목록 조회

### AC-FORCE-003 — 배치 조회와 빈 집합 `[BE][FE]`

Traces: REQ-FORCE-003

- **Given**: 매칭 실패 섹션에 서로 다른 5개 주문에 걸친 강제 자격 행 8건이 있다.
- **When**: (a) 결과 화면이 후보 목록을 조달한다. (b) 별도로, 빈 주문 식별자 목록으로 후보 조회를
  호출한다.
- **Then**: (a) 후보 조회 요청은 정확히 1회 발생하며 응답에 5개 주문 전부의 후보가 담긴다 —
  행마다(8회)나 주문마다(5회) 요청하지 않는다. (b) 오류가 아니라 빈 결과가 반환되며 어떤 Order·
  LineItem도 변경되지 않는다.

### AC-FORCE-004 — 동명 주문 tie-break는 최저 `pk` `[BE]`

Traces: REQ-FORCE-004

- **Given**: `Order.name="#37349"`인 Order가 2건 존재한다. `pk`가 더 작은 O1을 **더 나중에**
  생성해 `pk` 순서와 생성 일시 순서를 어긋나게 만든다. 두 주문은 서로 다른 LineItem 집합을 가진다.
- **When**: `#37349`의 후보 목록을 조회하고, 그 목록에서 대상을 골라 강제 실행한다.
- **Then**: 후보 목록은 O1(최저 `pk`)의 LineItem으로 구성되고, 강제 실행의 기록도 O1의 LineItem에
  남는다. 생성 일시 순서는 판정에 영향을 주지 않는다.

### AC-FORCE-005 — 후보 제외·속성·용량 표시·정렬 결정성 `[BE]`

Traces: REQ-FORCE-005, REQ-FORCE-006

- **Given**: `Order.name="#37349"`에 다음 5건이 있다 — (1) 정상 LineItem, (2)
  `purchase_status="order_cancelled"`, (3) `sku=null`, (4) `quantity=null`, (5) `quantity=5`,
  `shipped_quantity=5`. (1)과 (5)는 동일한 `sku`와 `title`을 가진다.
- **When**: `#37349`의 후보 목록을 연속 2회 조회한다.
- **Then**: 후보는 (1)(4)(5) 3건이며 (2)(3)은 나타나지 않는다. 각 후보는 안정적 식별자, 도서명,
  `sku`, 주문 수량, 기출고 수량, 물류 상태를 갖고, (4)와 (5)에는 잔여 용량 없음 표시가 붙는다.
  동일 `sku`·`title`인 (1)과 (5)는 식별자로 구분된다. 두 응답의 후보 순서는 동일하다.

## 강제 반영 불변식

### AC-FORCE-006 — 두 경로의 결과 동일성과 0 수량의 유일한 편차 `[BE]`

Traces: REQ-FORCE-007

- **Given**: 초기 상태가 동일한 두 LineItem L1, L2(`quantity=10`, `shipped_quantity=2`)가 있고,
  L1은 정상 경로로 매칭 가능한 SKU를, L2는 매칭되지 않는 SKU를 갖는다. 별도로
  `confirmed_distributor="warehouse_ca"`, `quantity=10`, `shipped_quantity=0`인 L3를 둔다.
- **When**: (a) L1에 정상 경로로 수량 3을 반영하고, L2에 강제 경로로 L2를 지정해 수량 3을 반영한다.
  (b) L3에 정상 경로로 수량 0을 제출하고, 별도로 강제 경로로 L3를 지정해 수량 0을 제출한다.
- **Then**: (a) L1과 L2의 `shipped_quantity`(각각 5)와 `logistics_status`가 동일하다. (b) 정상
  경로는 L3를 완료 처리(`shipped_quantity=10`, `"shipped"`)하지만, 강제 경로에서는 그 0 수량 행이
  그룹화 이전에 제거되어 **L3에 대한 그룹이 아예 형성되지 않는다** — L3는 `shipped_at`을 포함해
  어떤 필드도 변경되지 않고, 응답의 matched·quantity_exceeded 어느 목록에도 나타나지 않는다(그 행
  자체는 `invalid_total`로 보고된다). 두 경로의 편차는 매칭 단계 대체와 이 0 수량 처리 두
  가지뿐이다.

### AC-FORCE-007 — 동일 대상 2행 합산이 한도를 초과하는 경우 `[BE]`

Traces: REQ-FORCE-008, REQ-FORCE-010

- **Given**: `quantity=10`, `shipped_quantity=0`인 대상 L이 있고, 서로 다른 SKU를 가진 매칭 실패 행
  2건(수량 6과 5)이 있다. 각 행은 단독으로는 한도 안에 들어간다.
- **When**: 두 행 모두 대상으로 L을 지정해 **하나의** 요청으로 실행한다.
- **Then**: 수량이 먼저 11로 합산되고 `11 > 10`이므로 L의 어떤 필드도 변경되지 않는다. 응답에는 L에
  대한 수량초과 항목이 **정확히 1건** 포함되며 행별로 2건이 나타나지 않는다. 각 행을 요청 이전 값
  기준으로 따로 판정해 둘 다 통과시키는 동작은 발생하지 않는다.

### AC-FORCE-008 — 동일 대상 2행 합산 성공 시 병합 항목의 필드 `[BE]`

Traces: REQ-FORCE-008, REQ-FORCE-009, REQ-FORCE-016

- **Given**: `sku="ISBN-TARGET"`, `quantity=10`, `shipped_quantity=0`인 대상 L이 있고, 매칭 실패
  행 2건이 각각 `sku="ISBN-X"` 수량 4, `sku="ISBN-Y"` 수량 6으로 존재한다.
- **When**: 두 행 모두 대상으로 L을 지정해 하나의 요청으로 실행한다.
- **Then**: L의 `shipped_quantity`가 10으로 **한 번만** 증가하고 `logistics_status`가 `"shipped"`로
  전이된다. 응답의 matched 리스트에는 항목이 **1건**만 있으며, 그 `line_item_id`는 L,
  `sku`는 요청 행의 `ISBN-X`/`ISBN-Y`가 아니라 **L 자신의 `ISBN-TARGET`**, `total`은 10이다.

### AC-FORCE-009 — 임계 미달 단일 행 반영 `[BE]`

Traces: REQ-FORCE-009

- **Given**: 대상 LineItem이 `quantity=10`, `shipped_quantity=3`,
  `logistics_status="received"`이다.
- **When**: 그 대상에 수량 2로 강제 실행한다.
- **Then**: `shipped_quantity=5`가 되고 `shipped_at`이 처리 시각으로 갱신되며 `logistics_status`는
  `"received"` 그대로다.

### AC-FORCE-010 — `quantity=null` 대상에 대한 양수 요청 `[BE]`

Traces: REQ-FORCE-010

- **Given**: 대상 LineItem이 `quantity=null`, `shipped_quantity=0`이다(용량 0으로 취급).
- **When**: 수량 1로 강제 실행한다.
- **Then**: 어떤 필드도 변경되지 않고 해당 대상이 `quantity_exceeded`로 보고된다.

### AC-FORCE-011 — 음수 / 0 / 판독불가 거부, 그룹 미형성, 합산 제외 `[BE]`

Traces: REQ-FORCE-008, REQ-FORCE-011

- **Given**: `quantity=10`, `shipped_quantity=8`인 대상 LA와,
  `confirmed_distributor="warehouse_ca"`, `quantity=10`, `shipped_quantity=0`인 대상 LB가 있다.
  추가로 **`quantity=null`, `shipped_quantity=0`인 대상 LD**(용량 0)와 **`quantity=5`,
  `shipped_quantity=5`로 이미 완전 출고된 대상 LE**를 둔다. 별도로 `quantity=10`,
  `shipped_quantity=0`인 대상 LC를 두고, LC를 지정하는 정상 행(수량 3)과 음수 행(수량 `-5`)을 함께
  준비한다. 실행 전 LA·LB·LD·LE의 `shipped_at`과 `logistics_status`를 기록해 둔다.
- **When**: 한 요청에 (a) LA에 수량 `-5`, (b) LA에 수량 `0`, (c) LA에 숫자로 읽을 수 없는 값,
  (d) LB에 수량 `0`, (e) **LD에 수량 `0`**, (f) **LE에 수량 `0`**, (g) LC에 수량 3과 수량 `-5` 두
  행을 담아 제출한다.
- **Then**: (a)~(f) 여섯 행 모두 `invalid_total`로 보고된다. LA·LB·LD·LE는 `shipped_quantity`뿐
  아니라 **`shipped_at`과 `logistics_status`도 실행 전 값 그대로**이며, 네 대상 모두 응답의
  matched·quantity_exceeded 어느 목록에도 나타나지 않는다 — 살아남은 행이 없어 그룹이 형성되지
  않았기 때문이다. 특히 (d)는 정상 경로라면 적용될 미국창고 완료 신호가 적용되지 않고, (e)와 (f)는
  용량이 0이거나 이미 채워져 있어 `0 >= 0`이 성립함에도 `"shipped"`로 전이되지 않는다. (g)에서
  음수 행은 LC의 합산에서 제외되어 LC의 `shipped_quantity`는 `3`이 되며, 음수가 상쇄나 감소를
  일으키지 않는다.

### AC-FORCE-012 — `shipped_quantity` 불감소 `[BE]`

Traces: REQ-FORCE-012

- **Given**: 대상 LineItem이 `shipped_quantity=6`이다.
- **When**: 성공·수량초과·`invalid_total` 결과가 섞인 강제 요청을 순서를 바꿔가며 연속 수행한다.
- **Then**: 어떤 시점에도 `shipped_quantity`가 6보다 작아지지 않는다.

### AC-FORCE-013 — 쓰기 대상 제한 (필드 단위 diff) `[BE]`

Traces: REQ-FORCE-013

- **Given**: `Order.name="#37349"`에 LineItem 3건이 있고, 실행 전 모든 LineItem의 전체 필드와
  `Order.status`, `Order.ready_to_ship`을 기록해 둔다. 주문 집계 재계산 루틴에 spy를 건다
  (`test_spec_013.py`의 `assert_not_called()` 선례와 동일한 방식).
- **When**: 그중 한 LineItem을 대상으로 `"shipped"` 전이가 일어나는 강제 실행을 수행한다.
- **Then**: 변경된 필드는 그 대상의 `shipped_quantity`, `shipped_at`, `logistics_status` 3개뿐이다.
  주문의 LineItem 개수는 3건 그대로이고 모든 LineItem의 `sku`/`title`/`quantity`가 동일하며,
  `Order.status`와 `Order.ready_to_ship`도 실행 전 값 그대로다. spy는 호출되지 않는다.

### AC-FORCE-014 — 원자성 (고장 주입) `[BE]`

Traces: REQ-FORCE-014

- **Given**: 서로 다른 대상 3건을 반영하는 강제 요청을 준비하고 각 대상의 실행 전 상태를 기록한다.
- **When**: 일괄 쓰기 단계가 배치 중간에 예외를 던지도록 패치한 뒤 요청을 제출한다(기존 출고
  원자성 테스트가 사용하는 고장 주입 방식과 동일).
- **Then**: 3건 모두 변경되지 않은 상태로 롤백된다. 부분 반영은 남지 않는다.

## 실행 단위 · 응답 계약 · 기존 계약 보존

### AC-FORCE-015 — 일괄 실행 요청 1회, 전송 대상은 지정된 행만 `[FE]`

Traces: REQ-FORCE-015, REQ-FORCE-023

- **Given**: 서로 다른 3개 주문에 걸친 자격 행 6건을 선택했고, 그중 4건에만 대상을 지정했다.
- **When**: "강제 출고 처리 실행"을 1회 클릭한다.
- **Then**: 강제 처리 요청은 정확히 1회 발생하며 payload에는 대상이 지정된 4건만 담겨 있다. 행별
  6회나 주문별 3회로 분할되지 않고, 대상 없는 2건도 실리지 않는다.

### AC-FORCE-016 — 기존 3분류 응답 계약 전체 재사용 `[BE]`

Traces: REQ-FORCE-016

- **Given**: 성공 1건, 수량초과 1건, `invalid_total` 거부 1건이 섞이도록 구성한 강제 요청을
  준비한다(대상 지정은 모두 유효해 게이트를 통과한다).
- **When**: 응답을 확인한다.
- **Then**: 응답은 기존 출고 처리 응답과 동일한 계약을 만족한다 — 3개 카테고리 리스트와 각각의
  count가 존재하고 리스트 길이가 count와 일치하며, matched 항목에는 `name`, `sku`, `total`,
  `line_item_id`, `shipped_quantity`, `quantity`, `logistics_status`가 모두 존재하고,
  quantity_exceeded 항목에는 `logistics_status` 자리에 `reason`이 있으며, unmatched 항목에는
  `name`, `sku`, `total`, `reason`이 있다. 필드를 좁히거나 넓히지 않아 기존 클라이언트 결과 렌더링
  경로가 수정 없이 이 응답을 소비한다.

### AC-FORCE-017 — 인증 관례 동일, 추가 권한 게이트 없음 `[BE]`

Traces: REQ-FORCE-017

- **Given**: 인증 토큰이 없는 클라이언트와, 일반 관리자 권한의 인증된 클라이언트가 있다.
- **When**: 후보 조회와 강제 처리를 각각 호출한다.
- **Then**: 미인증 요청은 두 경우 모두 거부된다(401 또는 403). 인증된 요청은 추가 역할 검사 없이
  정상 처리된다.

### AC-FORCE-018 — 기존 출고 처리 계약·쿼리 수 무변경 회귀 `[BE]`

Traces: REQ-FORCE-018

- **Given**: SPEC-ORDER-015 기준의 출고 처리 입력을 준비한다.
- **When**: 기존 수동 입력 엔드포인트와 Excel 업로드 엔드포인트에 각각 제출한다.
- **Then**: 두 응답의 payload 형태가 이 SPEC 적용 전과 동일하고 `unmatched` 항목에 후보 목록이
  동봉되어 있지 않다. 출고 처리 1회당 쿼리 수도 이전과 동일해, 기존 쿼리 카운트 상한
  테스트(10그룹 매칭 `<=6`, 전부 매칭 실패 `<=4`)와 두 엔드포인트 응답 동등성 테스트가 수정 없이
  통과한다.

## 프론트엔드

### AC-FORCE-019 — 대상 선택 피커 표시 내용 `[FE]`

Traces: REQ-FORCE-020

- **Given**: 자격 행 1건이 있고 그 주문에 후보 3건이 있으며, 그중 1건은 이미 완전 출고되었다.
- **When**: 그 행의 대상 지정 컨트롤을 연다.
- **Then**: 후보 3건이 각각 도서명, SKU, 주문 수량, 기출고 수량, 물류 상태와 함께 표시되고, 완전
  출고된 후보에는 잔여 용량 없음 표시가 붙어 있다.

### AC-FORCE-020 — 상태·사유 코드값 미노출, 데이터 값은 원본 유지 `[FE]`

Traces: REQ-FORCE-021

- **Given**: 피커가 열려 후보의 물류 상태가 표시되고 있고, 행의 매칭 실패 사유도 표시되고 있다.
  후보 중 하나의 `sku`에는 언더스코어가 포함되어 있다.
- **When**: 매칭 실패 섹션 전체의 렌더링된 텍스트를 검사한다.
- **Then**: `not_shipped`나 `line_item_not_found` 같은 상태·사유 코드값이 텍스트로 나타나지 않고
  모두 한국어 라벨로 표시된다. `sku`와 도서명은 저장된 값 그대로 렌더링되며 변환되지 않는다.

### AC-FORCE-021 — 대상 미지정 시 실행 컨트롤 비활성 `[FE]`

Traces: REQ-FORCE-022

- **Given**: 자격 행 2건을 선택했으나 아직 어느 행에도 대상을 지정하지 않았다.
- **When**: 일괄 실행 컨트롤을 확인하고, 이어서 1건에만 대상을 지정한다.
- **Then**: 지정 전에는 실행 컨트롤을 사용할 수 없고, 1건을 지정한 직후 사용할 수 있게 된다.

### AC-FORCE-022 — 실행 성공 시 결과 병합, 미선택 행 잔존, 재제출 불가 `[FE]`

Traces: REQ-FORCE-024

- **Given**: 매칭 실패 섹션에 자격 행 R1·R2·R3가 표시되어 있고, 그중 **R1과 R2만** 선택해 대상을
  지정했다. R3는 선택하지 않았다. 강제 응답은 R1을 matched 1건으로, R2를 quantity_exceeded 1건으로
  반환한다.
- **When**: 일괄 실행을 수행하고 성공 응답을 받는다.
- **Then**: 네 가지가 모두 성립한다 — (1) 제출한 R1과 R2는 매칭 실패 섹션에서 사라져 다시 선택·
  반영할 수 없다. (2) **선택하지 않은 R3는 매칭 실패 섹션에 그대로 남아 있고 선택 컨트롤과 대상
  지정 컨트롤도 그대로 사용할 수 있다.** (3) R1은 성공 섹션에, R2는 수량초과 섹션에 표시된다 —
  한도를 넘겨 반려된 건이 화면에서 사라지지 않는다. (4) 세 섹션의 건수는 각각 화면에 표시된 목록
  길이와 일치한다(매칭 실패 1건, 성공 +1건, 수량초과 +1건). 선택 상태는 비어 있고, 페이지
  새로고침 없이 새 처리를 이어서 수행할 수 있다.

## 품질 게이트 (Quality Gate)

품질 게이트는 **레이어별로 분리**한다. 프론트엔드 요구사항(React 렌더링, 선택 상태, 결과 대체)은
Django pytest로 검증할 수 없으므로 백엔드 커버리지 게이트가 이를 요구하지 않는다.

### 백엔드 (`backend/order/tests/test_spec_016.py`, pytest)

- 커버 대상 REQ: 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 016, 017, 018
  — 각 항목에 최소 1개 테스트 매핑.
- 커버 대상 AC: 002, 003, 004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 014, 016, 017, 018.
- REQ-FORCE-003은 백엔드에서 "한 요청으로 N개 주문 후보를 반환하고 빈 집합에는 빈 결과를 준다"를,
  프론트엔드에서 "요청이 1회만 발생한다"를 각각 검증한다 — 두 레이어 모두에 배정된 유일한 항목이다.

### 프론트엔드 (colocate 테스트, vitest + React Testing Library)

- 대상 파일: `frontend/src/pages/OutboundPage/index.test.tsx`, 신규 매칭 실패 섹션 컴포넌트의
  colocate 테스트, `frontend/src/services/outboundApi.test.ts`,
  `frontend/src/hooks/useOutboundQueries.test.tsx`.
- 커버 대상 REQ: 001, 003(요청 횟수), 015, 019, 020, 021, 022, 023, 024 — 각 항목에 최소 1개 테스트
  매핑.
- 커버 대상 AC: 001, 003, 015, 019, 020, 021, 022.

### 회귀

- `backend/order/tests/test_spec_015.py` 전량 **무수정** 통과 — 특히 T8 쿼리 카운트 4건, 두
  엔드포인트 응답 동등성, 음수/판독불가 total 불변식 계열, 미국창고 완료 신호 계열.
- 프론트엔드 기존 테스트: `OutboundPage/index.test.tsx`(snake_case 금지 테스트 포함),
  `outboundApi.test.ts`(사유 코드 5개 assert 포함), `useOutboundQueries.test.tsx`.
- 공유 결과 섹션 컴포넌트의 외부 호출부 회귀: `frontend/src/pages/InboundPage/index.tsx`(3개
  호출부)와 `frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx`(1개 호출부) 및 그 테스트
  전량 통과 — 이 컴포넌트를 수정하지 않았으므로 무변경이 기대값이다.

### 기타

- 마이그레이션: 신규 마이그레이션 파일이 생성되지 않아야 한다(`makemigrations --check` 무변경).
- Exclusions 위반 없음: 신규 모델 컬럼, 감사 로그 모델, 신규 권한 클래스, 라우팅/사이드바 변경,
  `_recompute_order_aggregates` 및 그 호출부 변경, 신규 매칭 실패 사유 코드, 공유 결과 섹션
  컴포넌트 시그니처 변경, 부분 반영 경로가 diff에 존재하지 않아야 한다.
- LSP 게이트: `tsc` / eslint / ruff 0 에러.

## Definition of Done

- [ ] 후보 배치 조회 구현 완료 — 1요청 배치, 빈 집합 빈 결과, 최저 `pk` tie-break, 취소·NULL SKU
      제외, 잔여 용량 표시, 결정적 정렬
- [ ] 강제 반영 구현 완료 — 사전 게이트(7종 위반 → HTTP 400), 음수·0·판독불가 행을 **그룹화
      이전에** 제거(살아남은 행이 없는 대상은 그룹 미형성 → 판정·쓰기·보고 없음), 대상별 합산,
      수량 한도, 불감소, 임계 전이, 쓰기 대상 3필드 제한, 원자성
- [ ] 강제 응답이 기존 3분류 응답 계약을 필드까지 그대로 만족하고, 병합 항목이 대상 단위로
      보고되며 `sku`가 대상 LineItem 자신의 값임을 확인
- [ ] REQ-FORCE-001~024 전량이 위 레이어별 게이트에 따라 테스트 통과, AC-FORCE-001~022 전량 검증
- [ ] 매칭 실패 섹션 전용 컴포넌트 구현 완료 — 기존 섹션의 시각적 처리 재현, 공유 컴포넌트 무변경
- [ ] 강제 실행 성공 시 결과 병합 규칙 동작 확인 — 제출한 행만 매칭 실패 목록에서 제거되고
      재제출 불가, 미선택 행은 잔존·선택 가능, 강제 응답의 성공·수량초과 항목이 각 섹션에 추가,
      세 건수 재계산
- [ ] SPEC-ORDER-015 기존 테스트 스위트 무수정 전량 통과
- [ ] 공유 결과 섹션 컴포넌트의 4개 외부 호출부 및 그 테스트 무변경 통과
- [ ] `product.md` 기능 목록에 SPEC-ORDER-016 항목 추가(sync 단계)
- [ ] `spec.md` `status: draft → completed` 전이 및 HISTORY 갱신
- [ ] 후속 과제 1(주문 집계 미갱신), 2(동시성 + 배치 전체 400 실패 모드), 4(완료 신호 대상 지정
      확장)가 문서에 남아 있고 이번 범위에서 손대지 않았음을 확인
