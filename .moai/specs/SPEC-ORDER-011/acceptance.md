# SPEC-ORDER-011 인수 테스트

BDD 형식(Given/When/Then)의 실행 가능한 테스트 시나리오. EARS 형식의 정식 인수 기준은 `spec.md`의 `## ACCEPTANCE CRITERIA` 섹션(AC-LOGI-001~014)을 참조 — 아래 각 시나리오는 그 AC-LOGI-XXX ID를 인용해 상호 추적된다.

## 시나리오 0: 기본값 및 필드 독립성

**Traces**: REQ-LOGI-001, AC-LOGI-001

**Given** 신규 LineItem이 생성된다(Shopify 동기화 등으로)
**When** 별도 조치 없이 조회한다
**Then** `logistics_status`가 `not_shipped`(미입고)이고, `purchase_status`/`fulfillment_status` 값과 무관하게 독립적으로 저장되어 있다

---

## 시나리오 1: 벤더 출고확인 업로드 — 정상 전이

**Traces**: REQ-LOGI-003, AC-LOGI-003

**Given** `purchase_status="in_stock"`(발주 이력 있음), `logistics_status="not_shipped"`인 LineItem(SKU=X)이 존재한다
**When** 벤더 출고확인 파일 업로드에 SKU=X 행이 포함되어 업로드된다
**Then** 해당 LineItem의 `logistics_status`가 `shipment_confirmed`로 전이된다

---

## 시나리오 1b: 업로드 응답 카운트

**Traces**: REQ-LOGI-004, AC-LOGI-004

**Given** 벤더 출고확인 파일에 매칭되는 SKU 3개, 매칭되지 않는 SKU 1개가 포함되어 있다
**When** 업로드가 처리된다
**Then** 응답에 매칭/업데이트 카운트 3, 스킵 카운트 1이 포함되고, 두 값의 합이 파일 내 고유 SKU 수(4)와 일치한다

---

## 시나리오 1c: 벤더 출고확인 업로드 — SKU 중복 행(마지막 값 적용)

**Traces**: REQ-LOGI-003a, AC-LOGI-003a

**Given** 벤더 출고확인 파일에 SKU=X 행이 2번 등장하고, 값이 서로 다르다
**When** 업로드가 처리된다
**Then** SKU=X에는 파일 내 마지막 행의 값만 적용되고 이전 행은 무시된다

---

## 시나리오 1d: 벤더 출고확인 업로드 — 원자성(부분 실패 없음)

**Traces**: REQ-LOGI-003b, AC-LOGI-003b

**Given** 벤더 출고확인 파일 처리 도중 일부 행에서 예외가 발생하는 조건이 존재한다
**When** 업로드가 처리되다가 실패한다
**Then** 어떤 LineItem도 부분적으로 반영되지 않고 트랜잭션 전체가 롤백된다

---

## 시나리오 2: 창고 입고결과 업로드 — 정상 경로(입고예정 → 입고)

**Traces**: REQ-LOGI-005, AC-LOGI-005b

**Given** `logistics_status="shipment_confirmed"`인 LineItem(SKU=Y)이 존재한다
**When** 창고 입고결과 파일 업로드에 SKU=Y 행이 포함되어 업로드된다
**Then** 해당 LineItem의 `logistics_status`가 `received`로 전이된다

---

## 시나리오 2b: 창고 입고결과 업로드 — 직행 경로(미입고 → 입고, 벤더 미회신)

**Traces**: REQ-LOGI-005, AC-LOGI-005a

**Given** `logistics_status="not_shipped"`인 LineItem(SKU=Z, 업로드 1을 거치지 않음)이 존재한다
**When** 창고 입고결과 파일 업로드에 SKU=Z 행이 포함되어 업로드된다
**Then** 해당 LineItem의 `logistics_status`가 `입고예정`을 건너뛰고 곧바로 `received`로 전이된다

---

## 시나리오 2b2: 창고 입고결과 업로드 — dedup/원자성 규칙 동일 적용

**Traces**: REQ-LOGI-005a, AC-LOGI-005c

**Given** 창고 입고결과 파일에 SKU=Y 행이 2번 등장하고, 값이 서로 다르다
**When** 업로드가 처리된다
**Then** SKU=Y에는 마지막 행의 값만 적용되며, 업로드 처리는 벤더 출고확인 업로드와 동일하게 단일 트랜잭션으로 전체 커밋되거나 전체 롤백된다

---

## 시나리오 2c: 벤더 출고확인 업로드 — 회귀(발주 자체가 안 된 SKU는 매칭되지 않음)

**Traces**: REQ-LOGI-003, AC-LOGI-003

**Given** `purchase_status="unordered"`인 LineItem(아직 발주 자체가 안 됨, SKU=W)이 존재한다
**When** 벤더 출고확인 파일 업로드에 SKU=W 행이 포함되어 업로드된다
**Then** SKU=W는 매칭되지 않고 skipped 카운트에 포함된다

---

## 시나리오 2d: WarehouseStock 무변경

**Traces**: REQ-LOGI-006, AC-LOGI-006

**Given** ISBN=X의 `WarehouseStock` 행(quantity=10)이 존재하고, 해당 ISBN의 LineItem이 `received`로 전이될 예정이다
**When** 창고 입고결과 업로드 또는 수기 변경으로 `logistics_status`가 `received`가 된다
**Then** `WarehouseStock(isbn=X)`의 `quantity`는 여전히 10이다(전이로 인한 변화 없음)

---

## 시나리오 2e: 수기 상태 변경 — 유효 값 수용

**Traces**: REQ-LOGI-007, AC-LOGI-007a


**Given** `logistics_status="not_shipped"`인 LineItem이 존재한다
**When** 수기 변경 요청으로 유효한 값(`shipment_confirmed`)을 지정한다
**Then** 전이가 적용된다

---

## 시나리오 2e2: 수기 상태 변경 — 무효 값 거부

**Traces**: REQ-LOGI-007a, AC-LOGI-007b

**Given** `logistics_status="shipment_confirmed"`인 LineItem이 존재한다
**When** 수기 변경 요청으로 5개 값에 속하지 않는 값을 지정한다
**Then** 요청이 거부되고, LineItem의 `logistics_status`는 변경되지 않으며, 어떤 값이 유효하지 않은지 응답에 포함된다

---

## 시나리오 3: Order.status 집계 — 단일 상태

**Traces**: REQ-LOGI-008, REQ-LOGI-009, AC-LOGI-008, AC-LOGI-009

**Given** Order(id=100)의 모든 trackable LineItem이 `logistics_status="received"`다
**When** 마지막 LineItem의 `logistics_status`가 write된다
**Then** 그 write에 대한 응답이 반환되기 전에 `Order.status`가 `received`로 재계산되어 있다

---

## 시나리오 4: Order.status 집계 — 혼재 상태

**Traces**: REQ-LOGI-008, AC-LOGI-008

**Given** Order(id=101)의 LineItem 중 일부는 `not_shipped`, 일부는 `received`다
**When** 마지막 LineItem의 `logistics_status`가 write된다
**Then** `Order.status`가 `partial`(부분입고)로 재계산된다

---

## 시나리오 5: 다수 Order에 걸친 일괄 변경 — 배치 재계산

**Traces**: REQ-LOGI-010, AC-LOGI-010

**Given** 서로 다른 N개 Order에 속한 LineItem 여러 개가 일괄 변경 대상이다
**When** 일괄 변경 요청이 처리된다
**Then** 영향받은 N개 Order의 `status`가 모두 재계산되고, 재계산에 실행된 쿼리 수가 업데이트된 LineItem 개수에 비례해 선형 증가하지 않는다(`CaptureQueriesContext` 검증)

---

## 시나리오 6: Shopify 재동기화 — logistics_status/Order.status 무변경

**Traces**: REQ-LOGI-002, REQ-LOGI-011, AC-LOGI-002, AC-LOGI-011

**Given** 기존 LineItem에 `logistics_status`가 설정되어 있고, Order에 집계된 `status`가 설정되어 있다
**When** 해당 Order/LineItem이 Shopify와 재동기화된다
**Then** `logistics_status`와 `Order.status` 값이 재동기화 전후로 동일하다

---

## 시나리오 6b: logistics_status write가 PurchaseOrder.status에 영향 없음

**Traces**: REQ-LOGI-014, AC-LOGI-014a

**Given** LineItem이 기존 `PurchaseOrder`에 연결되어 있고, 그 `PurchaseOrder.status`는 `pending`이다
**When** 해당 LineItem의 `logistics_status`가 임의의 값으로 변경된다(수기 또는 업로드)
**Then** 연결된 `PurchaseOrder.status`는 여전히 `pending`이며 변경되지 않는다

---

## 시나리오 6c: logistics_status는 PurchaseOrder.status로부터 계산되지 않음

**Traces**: REQ-LOGI-014, AC-LOGI-014b

**Given** 동일 SKU에 연결된 `PurchaseOrder.status`가 `pending`에서 `confirmed`로 변경된다(가상 시나리오 — 현재 코드베이스에서 이 전이가 실제로 발생하지 않더라도 불변식 검증 목적)
**When** 그 `PurchaseOrder.status` 변경 이후 LineItem의 `logistics_status`를 조회한다
**Then** `logistics_status` 값은 `PurchaseOrder.status` 변경 전과 동일하며, `PurchaseOrder.status`를 참조해 계산된 흔적이 없다(코드 검토: `logistics_status`를 쓰는 모든 경로가 `PurchaseOrder.status`를 입력으로 사용하지 않음을 확인)

---

## 시나리오 7: 프론트엔드 — 컬럼 구분

**Traces**: REQ-LOGI-013, AC-LOGI-013

**Given** LineItem 목록 화면이 렌더링된다
**When** `logistics_status` 컬럼과 `fulfillment_status`(배송 상태) 컬럼이 함께 표시된다
**Then** 두 컬럼의 헤더 텍스트와 뱃지 스타일이 시각적으로 구분된다

---

## 시나리오 8: 백필 마이그레이션

**Traces**: REQ-LOGI-012, AC-LOGI-012

**Given** `logistics_status` 필드 마이그레이션 적용 직후, 기존 LineItem 전부가 기본값 `not_shipped`를 갖는다
**When** 백필 마이그레이션이 실행된다
**Then** 기존 Order 전체의 `status`가 새 집계 규칙에 따라 재계산된다(신규 필드가 전부 기본값이므로 trackable LineItem이 있는 Order는 전량 `not_shipped`로 수렴 예상)

---

## 엣지 케이스

- SKU가 여러 LineItem에 걸쳐 있는 경우(번들 확장, SPEC-SHOPIFY-SKU-SET-002) — 업로드 매칭이 SKU 단위이므로 동일 SKU의 모든 LineItem 행이 함께 전이되어야 한다.
- 업로드 파일에 존재하지 않는 SKU가 포함된 경우 — skipped 카운트 증가, 예외 없이 나머지 행 처리 계속.
- trackable LineItem이 하나도 없는 Order(sku 전부 null) — `Order.status` 미설정(null) 유지, 예외 발생 없음.

## 품질 게이트

- 신규 코드 커버리지 85%+ (TRUST 5 Tested 기준)
- 업로드 2개 엔드포인트 모두 단일 트랜잭션·배칭 처리를 준수 (코드 리뷰 체크, 구체적 참조 구현은 plan.md)
- 쿼리 수 상한 회귀 테스트 포함(시나리오 5)
- ruff/black 통과, 기존 SPEC-PURCHASE-ORDER-005~009 관련 테스트 스위트 무변경 통과

## Definition of Done

- [ ] REQ-LOGI-001~014 및 AC-LOGI-001~014 전체 구현 및 테스트 통과
- [ ] 마이그레이션 적용 및 롤백 불가 사유 문서화(plan.md 참조)
- [ ] 프론트엔드 컬럼/PATCH/업로드 UI 연결
- [ ] Exclusions 항목이 실제로 구현되지 않았음을 코드 리뷰로 확인
- [ ] research.md의 "확인이 필요한 가정"(Excel 컬럼 레이아웃)이 Run 단계 시작 전 해소됨
