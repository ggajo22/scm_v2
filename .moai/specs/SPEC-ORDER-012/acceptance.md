# SPEC-ORDER-012 인수 테스트

BDD 형식(Given/When/Then)의 실행 가능한 테스트 시나리오. EARS 형식의 정식 인수 기준은 `spec.md`의
`## ACCEPTANCE CRITERIA` 섹션(AC-RTS-001, 002a/002b/002c, 003, 003a, 004, 004a, 005~008)을 참조 — 아래 각 시나리오는 그 AC-RTS-XXX ID를 인용해
상호 추적된다.

## 시나리오 0: 필드 독립성 및 기본값

**Traces**: REQ-RTS-001, AC-RTS-001

**Given** 신규 Order가 생성된다(Shopify 동기화 등으로, `ready_to_ship`에 대해 아무 조치도 하지 않음)
**When** 별도 재계산 없이 조회한다
**Then** `ready_to_ship`은 `null`이며, `Order.status` 값과 무관하게 독립적으로 저장되어 있다

---

## 시나리오 1: 전량 취소 — null

**Traces**: REQ-RTS-002, AC-RTS-002a

**Given** Order(id=200)의 추적 가능 LineItem 전부가 `purchase_status="order_cancelled"`다
**When** 그 Order에 대해 재계산이 트리거된다
**Then** `ready_to_ship`이 `null`로 설정된다

---

## 시나리오 1b: 추적 가능 LineItem 자체가 0개 — null

**Traces**: REQ-RTS-002, AC-RTS-002a

**Given** Order(id=201)에 `sku`가 모두 null인 LineItem만 존재한다(추적 불가)
**When** 그 Order에 대해 재계산이 트리거된다
**Then** `ready_to_ship`이 `null`로 설정된다(`Order.status`가 동일 조건에서 미설정되는 것과 동일한
동작)

---

## 시나리오 2: CS 필요 LineItem이 하드 블록 — False

**Traces**: REQ-RTS-002, AC-RTS-002b

**Given** Order(id=202)에 `purchase_status="cs_required"`인 LineItem 1개와,
`logistics_status="received"`인(다른 조건은 전부 충족하는) LineItem 1개가 함께 존재한다
**When** 그 Order에 대해 재계산이 트리거된다
**Then** 다른 LineItem이 전부 조건을 만족함에도 불구하고 `ready_to_ship`이 `False`로 설정된다

---

## 시나리오 2b: 취소된 아이템은 CS 판정에서도 제외

**Traces**: REQ-RTS-002, AC-RTS-002a, AC-RTS-002c

**Given** Order(id=203)에 `purchase_status="order_cancelled"`인 LineItem 1개(가상으로
`cs_required`였다가 취소됨)와, `purchase_status="in_stock"`인 LineItem 1개만 존재한다
**When** 그 Order에 대해 재계산이 트리거된다
**Then** 취소된 LineItem은 판정에서 완전히 제외되어 `ready_to_ship`이 `True`로 설정된다(취소된
아이템이 있다는 사실 자체는 결과에 영향을 주지 않는다)

---

## 시나리오 3: in_stock만으로 충족 — True

**Traces**: REQ-RTS-002, AC-RTS-002c

**Given** Order(id=204)의 유일한 추적 가능 LineItem이 `purchase_status="in_stock"`이고
`logistics_status="not_shipped"`다(창고 입고 이벤트를 거치지 않음)
**When** 그 Order에 대해 재계산이 트리거된다
**Then** `ready_to_ship`이 `True`로 설정된다(`logistics_status`와 무관하게 `in_stock`만으로 충분)

---

## 시나리오 3b: received만으로 충족 — True

**Traces**: REQ-RTS-002, AC-RTS-002c

**Given** Order(id=205)의 유일한 추적 가능 LineItem이 `purchase_status="other_publisher"`이고
`logistics_status="received"`다
**When** 그 Order에 대해 재계산이 트리거된다
**Then** `ready_to_ship`이 `True`로 설정된다(`other_publisher`/`damaged_exchange`는 일반 규칙에
속하며 별도 특례가 없다)

---

## 시나리오 4: 일부 미충족 — False

**Traces**: REQ-RTS-002, AC-RTS-002c

**Given** Order(id=206)에 `logistics_status="received"`인 LineItem 1개와,
`purchase_status="on_hold"`이면서 `logistics_status="not_shipped"`인 LineItem 1개가 함께 존재한다
**When** 그 Order에 대해 재계산이 트리거된다
**Then** 후자가 received/in_stock 어느 쪽도 만족하지 않으므로 `ready_to_ship`이 `False`로 설정된다

---

## 시나리오 5: 기존 4개 logistics_status write path — 재계산 트리거

**Traces**: REQ-RTS-003, AC-RTS-003

**Given** 벤더 출고확인 업로드/창고 입고결과 업로드/단건 PATCH/일괄 PATCH 중 하나가 LineItem의
`logistics_status`를 변경할 조건을 갖춘 Order(id=207)가 존재한다
**When** 해당 write path가 실행된다
**Then** 그 write에 대한 응답이 반환되기 전에 `Order.status`와 함께 `ready_to_ship`도
REQ-RTS-002 규칙에 따라 재계산되어 있다

---

## 시나리오 6: ConfirmOrderView — 신규 연결

**Traces**: REQ-RTS-003a, AC-RTS-003a

**Given** `purchase_status="cs_required"`인 LineItem(SKU=A)이 Order(id=208)에 속해 있다
**When** 다른 SKU에 대한 발주확정 요청(`ConfirmOrderView`)이 처리되어 SKU=A 자체는 요청에 포함되지
않았다
**Then** Order(id=208)의 `ready_to_ship`은 이 요청으로 인해 변경되지 않는다(배치 범위 밖 — 대조군)

**Given** `purchase_status="unordered"`인 LineItem(SKU=B, Order id=209 소속)이 존재하고, 같은
Order의 다른 모든 추적 가능 LineItem은 이미 `received`다
**When** SKU=B를 포함한 발주확정 요청이 처리되어 `purchase_status`가 변경된다(예: 명시적
`purchase_status` override 없이 확정만 진행)
**Then** 이 요청이 끝나기 전에 Order(id=209)의 `ready_to_ship`이 REQ-RTS-002 규칙에 따라
재계산되어 있다 — 이전에는(이 SPEC 적용 전) `ConfirmOrderView`가 어떤 Order 재계산도 트리거하지
않았음을 회귀로 확인

---

## 시나리오 6b: 단건/일괄 purchase_status PATCH — 신규 연결

**Traces**: REQ-RTS-003a, AC-RTS-003a

**Given** Order(id=210)의 유일한 추적 가능 LineItem이 `purchase_status="on_hold"`,
`logistics_status="not_shipped"`다(`ready_to_ship=False`)
**When** 그 LineItem의 `purchase_status`를 `in_stock`으로 변경하는 단건 PATCH 요청이 처리된다
**Then** 응답이 반환되기 전에 Order(id=210)의 `ready_to_ship`이 `True`로 재계산되어 있다

**Given** 서로 다른 Order에 속한 LineItem 여러 개가 일괄 `purchase_status` PATCH 대상이다
**When** 일괄 PATCH 요청이 처리된다
**Then** `.update()` 호출 전에 영향받은 Order id들이 캡처되어, `.update()` 이후 그 Order들의
`ready_to_ship`이 모두 재계산된다(`.update()`가 인스턴스를 반환하지 않는다는 제약을 올바르게
처리했는지 확인)

---

## 시나리오 6c: Daily Review 업로드 3개 분기 — 신규 연결

**Traces**: REQ-RTS-003a, AC-RTS-003a

**Given** Daily Review 업로드 파일에 CS 분기(`선택` 컬럼이 CS성 라벨) 대상 SKU 1개, 창고
`in_stock` 분기 대상 SKU 1개, 비창고(신규 발주) 분기 대상 SKU 1개가 각각 서로 다른 Order에 속해
포함되어 있다
**When** 업로드가 처리된다
**Then** 세 분기가 변경한 LineItem들이 속한 모든 Order의 `ready_to_ship`이 하나의 업로드 요청 안에서
함께 재계산된다(분기별로 따로 재계산되지 않고 한 번에 묶여 처리됨)

---

## 시나리오 7: 다수 Order에 걸친 일괄 변경 — 배치 재계산, N+1 없음

**Traces**: REQ-RTS-004, REQ-RTS-004a, AC-RTS-004, AC-RTS-004a

**Given** 서로 다른 N개 Order에 속한 LineItem 여러 개가 `ConfirmOrderView`/Daily Review 업로드/
일괄 PATCH 중 하나의 대상이다
**When** 해당 요청이 처리된다
**Then** 영향받은 N개 Order의 `ready_to_ship`(및 `status`)이 모두 재계산되고, 재계산에 실행된 쿼리
수가 업데이트된 LineItem 개수에 비례해 선형 증가하지 않는다(`CaptureQueriesContext` 검증, SKU/
LineItem 개수를 늘려도 쿼리 수가 일정함을 확인)

---

## 시나리오 8: Shopify 재동기화 — 무변경

**Traces**: REQ-RTS-005, AC-RTS-005

**Given** 기존 Order에 `ready_to_ship=True`가 계산되어 있다
**When** 해당 Order/LineItem이 Shopify와 재동기화된다
**Then** `ready_to_ship` 값이 재동기화 전후로 동일하다(financial_status 등 Shopify 소스 필드로
덮어써지지 않음)

---

## 시나리오 9: 백필 마이그레이션

**Traces**: REQ-RTS-006, AC-RTS-006

**Given** `ready_to_ship` 필드 마이그레이션 적용 직후, 기존 Order 전부가 `null`이다
**When** 백필 마이그레이션이 실행된다
**Then** 기존 Order 전체의 `ready_to_ship`이 REQ-RTS-002 규칙에 따라 재계산된다(추적 가능
LineItem이 있는 Order는 각자의 현재 `purchase_status`/`logistics_status` 조합에 따라 True/False/
null로 정확히 나뉨)

---

## 시나리오 10: 프론트엔드 — 뱃지 3개 구분 및 null 미노출

**Traces**: REQ-RTS-007, REQ-RTS-008, AC-RTS-007, AC-RTS-008

**Given** Order 상세 화면이 렌더링되고, `fulfillment_status`/`status`/`ready_to_ship`이 모두
non-null 값을 갖는다
**When** 세 뱃지가 함께 표시된다
**Then** 세 뱃지의 헤더 텍스트가 서로 단어를 공유하지 않고, 배경색도 서로 다르다

**Given** 같은 화면에서 `ready_to_ship`이 `null`인 Order를 조회한다
**When** 상세 화면이 렌더링된다
**Then** 출고가능 뱃지가 렌더링되지 않는다(`fulfillment_status`/`status` 뱃지는 각자의 null 여부에
따라 독립적으로 노출/미노출된다)

---

## 엣지 케이스

- 추적 가능 LineItem 1개가 `damaged_exchange`이고 아직 재발주되지 않은 경우(`logistics_status`가
  여전히 `not_shipped`) — 일반 규칙에 속하므로 다른 미충족 아이템과 동일하게 `False`에 기여한다.
- `ConfirmOrderView`의 damaged_exchange 자동 리셋(요청 처리 중 `purchase_status`가
  `damaged_exchange`→`unordered`로 바뀜)이 재계산 시점 이전에 완전히 반영되어야 한다 — 재계산이
  `bulk_update` 이후에 위치하는지 검증.
- 같은 업로드/요청 안에서 동일 SKU가 여러 LineItem으로 확장된 번들 SKU(SPEC-SHOPIFY-SKU-SET-002)인
  경우 — 모든 멤버 LineItem이 각각 판정에 포함되어야 하며, 하나만 누락되어도 결과가 달라질 수 있음.
- `_recompute_order_aggregates`가 0개의 `order_ids`로 호출되는 경우(예: 업로드 파일의 모든 SKU가
  스킵됨) — 기존 `_recompute_order_status`의 no-op 동작(빈 리스트면 즉시 반환)을 그대로 유지.

## 품질 게이트

- 신규/변경 코드 커버리지 85%+ (TRUST 5 Tested 기준)
- 8개 write path 모두 재계산 호출이 "요청당 1회" 원칙을 준수(코드 리뷰 체크, 참조 구현은 plan.md)
- 쿼리 수 상한 회귀 테스트 포함(시나리오 7)
- `_recompute_order_status` → `_recompute_order_aggregates` 리네임이 기존 참조(테스트 포함) 전체에
  누락 없이 반영됨을 `grep` 재확인
- ruff/black 통과, 기존 SPEC-PURCHASE-ORDER-005~010/SPEC-ORDER-011 관련 테스트 스위트 무변경 통과
  (특히 `test_spec_011.py`, `test_daily_review_upload.py`, `test_purchase_orders.py`)

## Definition of Done

- [ ] REQ-RTS-001, 002, 003, 003a, 004, 004a, 005~008 및 AC-RTS-001, 002a/002b/002c, 003, 003a, 004, 004a, 005~008 전체 구현 및 테스트 통과
- [ ] 마이그레이션 2개(`AddField` + 백필) 적용, reverse `noop` 사유 문서화(plan.md 참조)
- [ ] 8개 write path 전부에 재계산 연결 완료(기존 4개 함수명 교체 + 신규 4개 신규 연결)
- [ ] 프론트엔드 뱃지 연결 및 `OrderDetailSerializer`/`types/order.ts` 갱신
- [ ] Exclusions 항목이 실제로 구현되지 않았음을 코드 리뷰로 확인
- [ ] SPEC-ORDER-011/SPEC-PURCHASE-ORDER-010과의 의도된 cross-cutting 결합이 정확히 설계대로만
      이루어졌는지(다른 write path에 부작용 없음) 코드 리뷰로 재확인
