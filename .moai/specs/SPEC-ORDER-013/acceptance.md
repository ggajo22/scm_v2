# SPEC-ORDER-013 인수 테스트

BDD 형식(Given/When/Then)의 실행 가능한 테스트 시나리오. EARS 형식의 정식 인수 기준은
`spec.md`의 `## ACCEPTANCE CRITERIA` 섹션(AC-RACK-001, 002, 003, 003a, 003b, 004, 004a,
005, 005a, 006, 006a, 006b, 006c, 007, 008, 009, 009a, 010, 010a, 010b, 010c, 011, 012,
013)을 참조 — 아래 각 시나리오는 그 AC-RACK-XXX ID를 인용해 상호 추적된다.

## 시나리오 0: 필드 기본값 및 독립성

**Traces**: REQ-RACK-001, REQ-RACK-002, AC-RACK-001, AC-RACK-002

**Given** 신규 LineItem이 생성된다(별도 조치 없이)
**When** 그 LineItem을 조회한다
**Then** `rack_number`는 빈 문자열("")이며, `location`/`logistics_status`/
`purchase_status` 값과 무관하게 독립적으로 저장되어 있다
**And** `Order` 모델에는 `rack_number` 관련 필드나 계산 프로퍼티가 존재하지 않는다

---

## 시나리오 1: 단건 PATCH — 정상 갱신

**Traces**: REQ-RACK-003, AC-RACK-003

**Given** `rack_number=""`인 LineItem(id=300)이 존재한다
**When** `PATCH /api/purchase-orders/line-items/300/rack-number/`에
`{"rack_number": "A-12"}`를 전송한다
**Then** 응답은 200이며 `{"id": 300, "rack_number": "A-12", "sku": ...}`를 포함하고,
DB의 LineItem(id=300).rack_number는 "A-12"로 갱신되어 있다

---

## 시나리오 1a: 단건 PATCH — 존재하지 않는 LineItem

**Traces**: REQ-RACK-003a, AC-RACK-003a

**Given** id=999999인 LineItem이 존재하지 않는다
**When** `PATCH /api/purchase-orders/line-items/999999/rack-number/`에
`{"rack_number": "A-12"}`를 전송한다
**Then** 응답은 404이며, 어떤 LineItem의 `rack_number`도 변경되지 않는다

---

## 시나리오 1b: 단건 PATCH — 10자 초과 값 거부

**Traces**: REQ-RACK-003b, AC-RACK-003b

**Given** `rack_number="OLD"`인 LineItem(id=301)이 존재한다
**When** `PATCH /api/purchase-orders/line-items/301/rack-number/`에
`{"rack_number": "12345678901"}`(11자)를 전송한다
**Then** 응답은 400이며, LineItem(id=301).rack_number는 여전히 "OLD"다(변경 없음)

---

## 시나리오 2: 일괄 PATCH — 존재/미존재 id 혼합

**Traces**: REQ-RACK-004, AC-RACK-004

**Given** LineItem id=[302, 303]이 존재하고 id=9999는 존재하지 않는다
**When** `PATCH /api/purchase-orders/line-items/bulk-rack-number/`에
`{"ids": [302, 303, 9999], "rack_number": "B-07"}`를 전송한다
**Then** 응답은 200이며 `updated_count=2`, `missing_ids=[9999]`를 포함하고, id=302/303의
`rack_number`가 모두 "B-07"로 갱신되어 있다

---

## 시나리오 2a: 일괄 PATCH — 빈 id 목록 거부

**Traces**: REQ-RACK-004a, AC-RACK-004a

**Given** 임의의 LineItem들이 존재한다
**When** `PATCH /api/purchase-orders/line-items/bulk-rack-number/`에
`{"ids": [], "rack_number": "B-07"}`를 전송한다
**Then** 응답은 400이며, 어떤 LineItem도 변경되지 않는다

---

## 시나리오 3: Excel 업로드 — 헤더 대소문자/컬럼 순서 무관 탐색

**Traces**: REQ-RACK-005, AC-RACK-005

**Given** 업로드 파일의 헤더 행이 `["렉번호", "Lineitem SKU", "주문번호"]` 순서(요구
순서와 다름, "SKU"가 대문자 포함)로 구성되어 있다
**When** 이 파일이 업로드된다
**Then** 세 컬럼이 모두 올바르게 탐색되어 데이터 행 파싱이 정상적으로 진행된다(422가
발생하지 않는다)

---

## 시나리오 3a: Excel 업로드 — 필수 컬럼 누락

**Traces**: REQ-RACK-005a, AC-RACK-005a

**Given** 업로드 파일의 헤더 행에 "렉번호"에 해당하는 컬럼이 없다(주문번호/SKU만 존재)
**When** 이 파일이 업로드된다
**Then** 응답은 422이며, 어떤 LineItem도 변경되지 않는다

---

## 시나리오 4: Excel 업로드 — 정상 매칭 및 적용

**Traces**: REQ-RACK-006, AC-RACK-006

**Given** Order(order_number=5001)에 속한 LineItem(sku="9788900000001")이 존재한다
**When** 헤더가 올바르고, 데이터 행이 `주문번호=5001, SKU=9788900000001, 렉번호=C-03`인
파일이 업로드된다
**Then** 해당 LineItem의 `rack_number`가 "C-03"으로 갱신된다

---

## 시나리오 4a: Excel 업로드 — 동일 SKU가 서로 다른 주문에 존재(주문번호로 명확히 구분)

**Traces**: REQ-RACK-006, AC-RACK-006

**Given** 동일 SKU="9788900000002"를 가진 LineItem이 Order(order_number=5002)와
Order(order_number=5003) 양쪽에 각각 존재한다(같은 책이 서로 다른 주문에 포함)
**When** 업로드 파일에 두 행 — `(5002, 9788900000002, D-01)`과
`(5003, 9788900000002, D-02)` — 이 포함되어 처리된다
**Then** Order(5002) 소속 LineItem의 `rack_number`는 "D-01"로, Order(5003) 소속
LineItem의 `rack_number`는 "D-02"로 각각 독립적으로 갱신된다(서로의 값이 뒤섞이지 않는다)

---

## 시나리오 4a2: Excel 업로드 — 교차 주문 격리(다른 주문 소속 LineItem 미변경)

**Traces**: REQ-RACK-006, AC-RACK-006c

**Given** 동일 SKU="9788900000002"를 가진 LineItem이 Order(order_number=5002,
rack_number="")와 Order(order_number=5003, rack_number="OLD-B")에 각각 존재한다(같은
책이 서로 다른 주문에 포함)
**When** 업로드 파일에 Order(5003)에 대한 행은 포함하지 않고, `(5002, 9788900000002,
D-01)` 행 하나만 포함되어 처리된다
**Then** Order(5002) 소속 LineItem의 `rack_number`는 "D-01"로 갱신되지만, Order(5003)
소속 LineItem의 `rack_number`는 "OLD-B" 그대로 유지된다(같은 SKU를 가졌다는 이유만으로
다른 주문 소속 LineItem이 변경되지 않는다)

---

## 시나리오 4b: Excel 업로드 — 주문번호 불일치

**Traces**: REQ-RACK-006a, AC-RACK-006a

**Given** Order(order_number=5004)에 속한 LineItem(sku="9788900000003")이 존재하지만,
order_number=9999인 Order는 존재하지 않는다
**When** 업로드 파일에 `주문번호=9999, SKU=9788900000003, 렉번호=E-01` 행이 포함되어
처리된다
**Then** 이 행은 skipped로 카운트되고, Order(5004) 소속 LineItem의 `rack_number`는
변경되지 않는다

---

## 시나리오 4c: Excel 업로드 — 주문은 존재하나 해당 SKU의 LineItem 없음

**Traces**: REQ-RACK-006a, AC-RACK-006a

**Given** Order(order_number=5005)가 존재하지만 sku="9788900000099"인 LineItem은 그
Order에 속해 있지 않다
**When** 업로드 파일에 `주문번호=5005, SKU=9788900000099, 렉번호=F-01` 행이 포함되어
처리된다
**Then** 이 행은 skipped로 카운트되고, 어떤 LineItem도 변경되지 않는다

---

## 시나리오 5: Excel 업로드 — 동일 (주문번호, SKU) 중복 행, 빈 렉번호 값

**Traces**: REQ-RACK-006b, AC-RACK-006b

**Given** Order(order_number=5006)에 속한 LineItem(sku="9788900000004",
rack_number="OLD")이 존재한다
**When** 업로드 파일에 같은 (5006, 9788900000004) 조합의 행이 두 개 순서대로 포함된다 —
1번째 행: 렉번호="G-01", 2번째(더 아래) 행: 렉번호=""(빈 문자열)
**Then** 마지막 행이 우선 적용되어 해당 LineItem의 `rack_number`는 최종적으로 ""(빈
문자열, 명시적 지우기)가 된다 — "OLD"도 "G-01"도 아니다

---

## 시나리오 6: Excel 업로드 — matched_count/skipped_count 합산 검증

**Traces**: REQ-RACK-007, AC-RACK-007

**Given** 업로드 파일에 distinct (주문번호, SKU) 행이 총 5개 있고, 그중 3개는 매칭에
성공하고 2개는 매칭에 실패하는 조건으로 구성되어 있다
**When** 이 파일이 업로드된다
**Then** 응답의 `matched_count=3`, `skipped_count=2`이며 `matched_count + skipped_count`는
5(distinct 행 개수)와 같다 — 매칭된 LineItem이 여러 건이어도(시나리오 4a처럼) 행 단위로만
카운트된다

---

## 시나리오 7: 신규 페이지 라우팅 및 메뉴

**Traces**: REQ-RACK-008, AC-RACK-008

**Given** 인증된 관리자가 로그인되어 있다
**When** 사이드바에서 "렉번호 관리" 메뉴 항목을 클릭한다
**Then** `/rack-number` 경로로 이동하며, `/purchase-orders`(발주 관리) 페이지나 그 하위
탭이 아닌 독립된 페이지가 렌더링된다

---

## 시나리오 8: 주문번호 검색 — 성공

**Traces**: REQ-RACK-009, AC-RACK-009

**Given** Order(order_number=6001)에 LineItem 3건이 속해 있다
**When** 렉번호 관리 페이지에서 "6001"을 검색한다
**Then** 그 3건의 LineItem이 테이블에 표시되며, 각 행에 SKU/도서명/현재 `rack_number`가
보인다

---

## 시나리오 8a: 주문번호 검색 — 실패(존재하지 않는 주문번호)

**Traces**: REQ-RACK-009a, AC-RACK-009a

**Given** order_number=9999999인 Order가 존재하지 않는다
**When** 렉번호 관리 페이지에서 "9999999"를 검색한다
**Then** "주문을 찾을 수 없습니다" 류의 미발견 상태가 표시되고, LineItem 테이블은
렌더링되지 않는다

---

## 시나리오 8b: 주문번호 검색 — 이름 부분일치 오탐 방지

**Traces**: REQ-RACK-009, AC-RACK-009

**Given** Order A는 `order_number=1234`이고, Order B는 `name`에 "1234"라는 문자열이 부분
포함되어 있지만 `order_number`는 5678이다(오탐 유발 조건)
**When** "1234"를 검색한다
**Then** 화면에는 Order A의 LineItem만 표시되며, Order B의 LineItem은 표시되지 않는다

---

## 시나리오 9: 체크박스 다중 선택 및 일괄 적용

**Traces**: REQ-RACK-010, REQ-RACK-010a, AC-RACK-010, AC-RACK-010a

**Given** 주문 검색 결과로 LineItem 4건이 테이블에 표시되어 있다
**When** 그중 2건의 체크박스를 선택하고, 렉번호 입력란에 "H-05"를 입력한 뒤 "일괄 적용"을
클릭한다
**Then** 체크된 2건에 대해서만 단일 bulk-PATCH 요청이 전송되고, 성공 응답 후 체크박스
선택 상태가 모두 해제되며 테이블에는 갱신된 "H-05" 값이 반영된다(나머지 2건은 변경되지
않는다)

---

## 시나리오 9a: 전체선택 체크박스

**Traces**: REQ-RACK-010, AC-RACK-010b

**Given** LineItem 4건이 테이블에 표시되어 있고 아무것도 선택되지 않은 상태다
**When** 헤더의 "전체선택" 체크박스를 클릭한다
**Then** 4건의 행 체크박스가 모두 선택 상태로 바뀐다
**When** 다시 한 번 클릭한다
**Then** 4건의 행 체크박스가 모두 선택 해제된다

---

## 시나리오 9b: 페이지 이탈 후 재검색 시 선택 상태 초기화

**Traces**: REQ-RACK-010, AC-RACK-010c

**Given** 한 주문의 LineItem 중 일부가 체크되어 있다
**When** 다른 주문번호로 재검색한다
**Then** 새로 표시되는 LineItem 테이블은 체크박스 선택이 전부 해제된 상태로 시작한다
(이전 검색의 선택 상태가 남아있지 않다)

---

## 시나리오 10: 개별 인라인 편집

**Traces**: REQ-RACK-011, AC-RACK-011

**Given** 주문 검색 결과 테이블에 LineItem(id=310, rack_number="")이 표시되어 있고, 이
행은 체크박스로 선택되어 있지 않다
**When** 이 행의 `rack_number` 입력 칸에 "I-09"를 입력하고 확정(blur 또는 Enter)한다
**Then** 그 LineItem 하나에 대해서만 단건 PATCH 요청이 전송되고, 성공 시 테이블 셀에
"I-09"가 반영되며 페이지 전체가 새로고침되지 않는다(다른 행의 값이나 선택 상태에는 영향이
없다)

---

## 시나리오 11: OrderDetailPage 미노출

**Traces**: REQ-RACK-012, AC-RACK-012

**Given** `rack_number="J-01"`인 LineItem을 포함한 Order의 상세 페이지
(`/orders/:id`)를 연다
**When** 페이지가 렌더링된다
**Then** 화면 어디에도 `rack_number` 값, 라벨, 입력란, 뱃지가 나타나지 않으며, 이 페이지의
어떤 상호작용도 `rack_number`를 변경할 수 없다(API 응답 JSON 자체에는 필드가 포함될 수
있으나 UI 소비는 없음)

---

## 엣지 케이스

- 동일 (주문번호, SKU) 조합이 한 주문 안에서 2개 이상의 LineItem과 매칭되는 경우(결정 E,
  unique_together가 `sku`가 아닌 `shopify_line_item_id`를 포함하므로 이론상 가능) — 매칭된
  LineItem 전부에 같은 값을 적용하며, 이는 시나리오 6에서 "매칭 행 1개가 LineItem 여러 건에
  영향"으로 간접 검증된다.
- 엑셀 업로드 파일이 아예 읽을 수 없는 형식(손상된 파일, `.xlsx` 확장자이지만 실제로는
  텍스트 파일 등)인 경우 — `openpyxl.load_workbook`이 예외를 던지고, 기존 업로드 뷰들과
  동일하게 422로 응답하며 어떤 LineItem도 변경되지 않는다(REQ-RACK-005a 확장 케이스).
- 주문번호 컬럼 값이 숫자가 아닌 텍스트(예: 공백, "N/A")인 행 — 정수 파싱 실패로 해당 행은
  skipped 처리된다(REQ-RACK-006a와 동일 취급).
- 일괄 PATCH에 10자를 초과하는 `rack_number` 값이 전달되는 경우 — 단건 PATCH와 동일하게
  400으로 거부되고 어떤 LineItem도 변경되지 않는다(REQ-RACK-003b와 동일 검증이 일괄
  엔드포인트에도 적용됨).
- 검색 입력값이 숫자가 아닌 문자열인 경우(예: 사용자가 실수로 주문 이름을 입력) — 기존
  `OrderListView` 검색 로직상 숫자 파싱이 되지 않으므로 `order_number` 정확 매칭 조건은
  적용되지 않고 `name__icontains`만 적용되며, 정확히 일치하는 `order_number`가 없으므로
  프론트엔드는 결정 C의 필터링 규칙에 따라 결과를 찾지 못한 것으로 처리한다
  (AC-RACK-009a와 동일 취급).

## 품질 게이트

- 신규/변경 코드 커버리지 85%+ (TRUST 5 Tested 기준)
- 단건/일괄 PATCH 어디에도 `_recompute_order_aggregates()` 호출이 없음을 코드 리뷰로 확인
  (REQ-RACK-002 위반 방지)
- `bulk-rack-number` 경로가 `<int:pk>/rack-number/` 경로보다 urls.py에서 먼저 등록되어
  있는지 확인(URL 충돌 회귀 방지, 기존 `bulk-status`/`bulk-logistics-status` 관례)
- Excel 업로드 헤더 탐색이 컬럼 순서/대소문자와 무관하게 동작함을 최소 2가지 헤더 배열
  조합으로 테스트
- ruff/black 통과, 기존 SPEC-ORDER-011/012/SPEC-PURCHASE-ORDER-004 관련 테스트 스위트
  무변경 통과(특히 `test_spec_011.py`, `test_spec_012.py`, `test_purchase_orders.py`)
- `OrderDetailPage.test.tsx`(존재 시) 등 기존 프론트엔드 테스트에 `rack_number` 관련
  단언이 추가되지 않았음을 확인(REQ-RACK-012 회귀 방지)

## Definition of Done

- [ ] REQ-RACK-001~013(및 하위 접미사 전체) 및 AC-RACK-001~013(및 하위 접미사 전체)
      구현 및 테스트 통과
- [ ] 마이그레이션(`AddField` 단독) 적용, 백필 불필요 사유 문서화(plan.md 참조)
- [ ] 3개 백엔드 엔드포인트(단건 PATCH/일괄 PATCH/Excel 업로드) 전부 구현 및 urls.py 등록
      순서 검증 완료
- [ ] `LineItemDetailSerializer`에 `rack_number` 노출 완료
- [ ] 신규 페이지(`RackNumberPage`) + 라우팅 + 사이드바 메뉴 항목 추가 완료
- [ ] 신규 서비스(`rackNumberApi.ts`) + 훅(`useRackNumberQueries.ts`) 추가 완료
- [ ] Exclusions 항목(OrderDetailPage 미노출, Order 집계 없음, capacity/uniqueness 없음,
      변경 이력 없음, 역방향 검색 없음, WarehouseStock 연동 없음)이 실제로 구현되지
      않았음을 코드 리뷰로 확인
