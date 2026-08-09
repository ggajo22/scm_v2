# SPEC-ORDER-014 인수 테스트

BDD 형식(Given/When/Then)의 실행 가능한 테스트 시나리오. EARS 형식의 정식 인수 기준은
`spec.md`의 `## ACCEPTANCE CRITERIA` 섹션(AC-RACKSUM-001, 002, 002a, 003, 004, 004a, 004b,
005, 006, 007, 007a, 008, 009, 009a, 009b, 010, 011, 011a, 012, 013, 014, 015)을 참조 —
아래 각 시나리오는 그 AC-RACKSUM-XXX ID를 인용해 상호 추적된다.

## 시나리오 0: 필터 정의 — 미출고 4개 상태 포함, 출고 상태만 제외

**Traces**: REQ-RACKSUM-001, AC-RACKSUM-001

**Given** `logistics_status`가 각각 `not_shipped`, `shipment_confirmed`, `received`,
`outbound_scheduled`, `shipped`인 LineItem 5건이 서로 다른 Order에 존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** 응답에는 앞의 4건(`shipped`가 아닌 것)만 어떤 그룹에든 포함되어 있고,
`shipped` 상태인 1건은 어떤 그룹에도 나타나지 않는다

---

## 시나리오 0a: 필터 우회 파라미터 무시

**Traces**: REQ-RACKSUM-002, REQ-RACKSUM-002a, AC-RACKSUM-002, AC-RACKSUM-002a

**Given** `logistics_status="shipped"`인 LineItem과 `logistics_status="not_shipped"`인
LineItem이 각각 존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/?include_shipped=true`
처럼 필터를 끄려는 의도의 쿼리 파라미터를 붙여 호출한다
**Then** 응답은 파라미터가 없을 때와 동일하며, `shipped` LineItem은 여전히 어떤 그룹에도
포함되지 않는다

---

## 시나리오 1: 전체 주문 교차 조회 — 특정 주문에 국한되지 않음

**Traces**: REQ-RACKSUM-003, AC-RACKSUM-003

**Given** 서로 다른 Order(order_number=7001, 7002, 7003) 각각에 미출고 LineItem이 1건씩
존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** 세 주문 모두의 LineItem이 응답의 그룹들에 함께 포함되어 있다(단일 주문으로 제한된
결과가 아니다)

---

## 시나리오 2: 렉번호별 그룹핑 — 같은 렉에 서로 다른 주문의 LineItem이 섞임

**Traces**: REQ-RACKSUM-004, REQ-RACKSUM-006, AC-RACKSUM-004, AC-RACKSUM-004b

**Given** Order(order_number=7010)의 미출고 LineItem(sku="A")과 Order(order_number=7011)의
미출고 LineItem(sku="B")이 둘 다 `rack_number="C-01"`로 기록되어 있다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** `rack_number="C-01"` 그룹 하나에 두 LineItem이 모두 포함되고, 각 LineItem 항목은
자신의 `order_number`(각각 7010, 7011)를 정확히 유지하고 있다

---

## 시나리오 3: 미지정 버킷 — 빈 `rack_number`는 드롭되지 않고 별도 그룹으로 묶임

**Traces**: REQ-RACKSUM-004a, AC-RACKSUM-004a

**Given** `rack_number=""`인 미출고 LineItem 2건이 서로 다른 Order에 존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** 응답에는 `rack_number=""`, `is_unassigned=true`인 그룹이 정확히 하나 존재하며, 그
그룹의 `line_items`에는 두 LineItem이 모두 포함되어 있다(어느 쪽도 응답에서 누락되지 않는다)

---

## 시나리오 4: 총 수량 계산 — null 수량은 0으로 취급

**Traces**: REQ-RACKSUM-005, AC-RACKSUM-005

**Given** `rack_number="D-01"`인 미출고 LineItem 3건이 존재하며 `quantity` 값이 각각
2, 3, `null`이다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** `rack_number="D-01"` 그룹의 `total_quantity`는 5다(2 + 3 + 0)

---

## 시나리오 5: LineItem 상세 필드 — 최소 5개 필드 노출

**Traces**: REQ-RACKSUM-006, AC-RACKSUM-006

**Given** Order(order_number=7020)의 미출고 LineItem(sku="9788900000010",
title="샘플 도서", quantity=4, logistics_status="received", rack_number="E-01")이 존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** `rack_number="E-01"` 그룹의 해당 LineItem 항목에 `order_number=7020`,
`sku="9788900000010"`, `title="샘플 도서"`, `quantity=4`, `logistics_status="received"`가
모두 정확히 포함되어 있다

---

## 시나리오 6: 전 품목 출고 완료 주문 — 응답에서 완전히 제외

**Traces**: REQ-RACKSUM-007, AC-RACKSUM-007

**Given** Order(order_number=7030)에 속한 LineItem 전부(2건)가 `logistics_status="shipped"`다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** Order(7030) 소속 LineItem은 응답의 어떤 그룹에도 등장하지 않는다

---

## 시나리오 6a: 부분 출고 주문 — 미출고분만 포함

**Traces**: REQ-RACKSUM-007, AC-RACKSUM-007a

**Given** Order(order_number=7031)에 LineItem 2건이 속해 있으며, 하나는
`logistics_status="shipped"`, 다른 하나는 `logistics_status="received"`다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** `received` 상태인 LineItem만 응답의 그룹에 포함되고, `shipped` 상태인 LineItem은
어떤 그룹에도 포함되지 않는다

---

## 시나리오 7: 페이지네이션 미적용

**Traces**: REQ-RACKSUM-008, AC-RACKSUM-008

**Given** 미출고 LineItem이 다수(예: 50건 이상) 존재한다
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** 응답은 `page`/`next`/`previous` 등 페이지네이션 관련 필드를 포함하지 않으며,
`groups` 배열에 조건에 맞는 모든 그룹이 한 번에 담겨 있다

---

## 시나리오 8: 시스템 전체 미출고 LineItem 0건 — 빈 응답

**Traces**: REQ-RACKSUM-013(백엔드 전제 조건), AC-RACKSUM-013

**Given** 시스템에 존재하는 모든 LineItem의 `logistics_status`가 `"shipped"`다(미출고
LineItem이 0건)
**When** `GET /api/purchase-orders/line-items/rack-number-summary/`를 호출한다
**Then** 응답은 `{"groups": []}`다
**When** "렉번호 요약" 탭이 이 응답으로 렌더링된다
**Then** 빈 상태 메시지가 표시되고, 빈 테이블/그룹 목록 구조는 렌더링되지 않는다

---

## 시나리오 9: 탭 구조 — 2개 탭, 기본 활성 탭은 "주문 검색"

**Traces**: REQ-RACKSUM-009, REQ-RACKSUM-009b, AC-RACKSUM-009, AC-RACKSUM-009b

**Given** 사용자가 `/rack-number` 페이지에 처음 진입한다
**When** 페이지가 렌더링된다
**Then** "주문 검색"과 "렉번호 요약" 라벨을 가진 탭 컨트롤이 정확히 2개 보이며, 아무 탭도
클릭하지 않은 상태에서 "주문 검색" 탭의 콘텐츠(검색 입력창)가 이미 화면에 보인다

---

## 시나리오 9a: Tab1 기존 동작 무변경 — SPEC-ORDER-013 흐름 회귀 없음

**Traces**: REQ-RACKSUM-009a, AC-RACKSUM-009a

**Given** "주문 검색" 탭이 활성화되어 있고, Order(order_number=8001)에 LineItem 3건이
속해 있다
**When** "8001"을 검색하고, 그중 2건을 체크박스로 선택해 렉번호 값을 일괄 적용한 뒤, 나머지
1건을 인라인으로 직접 편집한다
**Then** SPEC-ORDER-013에서 검증된 것과 동일하게 검색 → 체크박스 다중 선택 → 일괄 PATCH →
인라인 단건 PATCH 흐름이 전부 동일하게 동작한다(요청 URL, 페이로드, 성공 후 UI 반영 방식
모두 무변경)

---

## 시나리오 10: Tab2 활성화 시 자동 조회

**Traces**: REQ-RACKSUM-010, AC-RACKSUM-010

**Given** "주문 검색" 탭이 활성화된 상태로 페이지가 열려 있다
**When** "렉번호 요약" 탭을 클릭한다
**Then** 별도의 검색어 입력이나 버튼 클릭 없이 자동으로 렉번호 요약 데이터 요청이
전송되고, 응답 도착 후 그룹 목록이 렌더링된다

---

## 시나리오 11: 그룹 헤더 표시 — 렉번호와 총 수량

**Traces**: REQ-RACKSUM-011, AC-RACKSUM-011

**Given** `rack_number="F-01"` 그룹에 LineItem 2건(수량 3, 5)이 속해 있다
**When** "렉번호 요약" 탭이 렌더링된다
**Then** 해당 그룹의 헤더에 "F-01"과 총 수량 8이 함께 표시된다

---

## 시나리오 11a: 미지정 그룹 라벨

**Traces**: REQ-RACKSUM-011a, AC-RACKSUM-011a

**Given** 요약 응답에 `is_unassigned=true`인 그룹이 포함되어 있다
**When** "렉번호 요약" 탭이 렌더링된다
**Then** 그 그룹은 다른 이름 있는 렉번호 그룹과 시각적으로 구분되는 "미지정" 라벨로
표시된다

---

## 시나리오 12: LineItem 행 상세 표시

**Traces**: REQ-RACKSUM-012, AC-RACKSUM-012

**Given** 한 그룹에 order_number=8010, sku="9788900000020", title="샘플2",
quantity=2, logistics_status="outbound_scheduled"인 LineItem이 포함되어 있다
**When** "렉번호 요약" 탭이 렌더링된다
**Then** 해당 LineItem의 행에 주문번호 8010, SKU, 도서명, 수량 2, 물류상태 라벨("출고예정")이
모두 표시된다

---

## 시나리오 13: 읽기 전용 강제 — 편집 UI 부재

**Traces**: REQ-RACKSUM-014, REQ-RACKSUM-015, AC-RACKSUM-014, AC-RACKSUM-015

**Given** "렉번호 요약" 탭이 하나 이상의 그룹과 함께 렌더링되어 있다
**When** 탭 내부의 DOM을 검사한다
**Then** 체크박스 엘리먼트, 렉번호 텍스트 입력창, "일괄 적용" 버튼이 하나도 존재하지 않으며,
탭 내 어떤 클릭 상호작용도 PATCH/업로드 네트워크 요청을 발생시키지 않는다

---

## 엣지 케이스

- 동일 (렉번호) 값이 3개 이상의 서로 다른 Order에 걸쳐 나타나는 경우 — 시나리오 2의 2-주문
  케이스와 동일한 방식으로 전부 한 그룹에 포함되며, 이는 그룹핑 기준이 `rack_number` 단독
  값이지 `(rack_number, order)` 조합이 아니기 때문에 자연히 성립한다(REQ-RACKSUM-004).
- 동일 Order 안에서 서로 다른 두 LineItem이 각각 다른 `rack_number`를 갖는 경우 — 이
  LineItem들은 서로 다른 그룹에 각각 분산되어 나타나며, 이는 그룹핑이 LineItem 단위로
  이루어지고 Order 단위로 묶이지 않기 때문에 자연히 성립한다(REQ-RACKSUM-004의 정의상 결과).
- `order_number`가 null인 Order에 속한 미출고 LineItem — 백엔드는 `order_number: null`을
  그대로 반환하고, 프론트엔드는 "-"로 방어적으로 표시한다(plan.md 리스크 절 참조,
  REQ-RACKSUM-006의 필드 존재 요구사항은 값이 null이어도 필드 자체는 포함되어야 함을 의미한다).
- 그룹 내 LineItem 개수가 매우 많은 렉(예: 100건 이상) — REQ-RACKSUM-008(페이지네이션
  미적용) 결정에 따라 그룹 내부적으로도 별도 페이지네이션 없이 전부 반환된다.
- SPEC-ORDER-013 Tab1에서 방금 렉번호를 수정한 직후 Tab2로 전환하는 경우 — 이 SPEC은 실시간
  캐시 무효화 연결을 구현하지 않으므로(plan.md M4, Enforce Simplicity), Tab2를 새로
  마운트(탭 재진입)하면 최신 값이 반영된 새 요청이 전송된다. 같은 탭 인스턴스가 유지된 채
  Tab1에서의 변경이 자동으로 Tab2에 실시간 반영되는 것은 이 SPEC의 범위가 아니다.

## 품질 게이트

- 신규/변경 코드 커버리지 85%+ (TRUST 5 Tested 기준)
- `LineItemRackNumberSummaryView`가 `PageNumberPagination`을 사용하지 않고 단일 payload로
  응답함을 코드 리뷰로 확인(REQ-RACKSUM-008 위반 방지)
- `SearchTab.tsx`(이동된 Tab1 콘텐츠)와 `SearchTab.test.tsx`(이동된 기존 테스트)의 diff가
  파일 경로/export 이름 변경만으로 구성되어 있고 로직·마크업·단언이 무변경임을 확인
  (REQ-RACKSUM-009a 회귀 방지 핵심 검증)
- 기존 SPEC-ORDER-013 프론트엔드 테스트 15개가 이동 후에도 전부 그대로 통과
- 기존 SPEC-ORDER-011/012/013 백엔드 테스트 스위트(`test_spec_011.py`, `test_spec_012.py`,
  `test_spec_013.py`) 무변경 통과
- ruff/black, ESLint/Prettier 통과
- `npm run build` 성공(모듈 해석 리스크 검증, plan.md 리스크 절 참조)

## Definition of Done

- [ ] REQ-RACKSUM-001~015(및 하위 접미사 전체) 및 AC-RACKSUM-001~015(및 하위 접미사 전체)
      구현 및 테스트 통과
- [ ] 신규 백엔드 GET 엔드포인트(`LineItemRackNumberSummaryView`) 구현 및 urls.py 등록 완료
- [ ] `RackNumberPage`가 탭 2개 구조(`index.tsx` + `tabs/SearchTab.tsx` +
      `tabs/SummaryTab.tsx`)로 재구성 완료, 기본 활성 탭은 "주문 검색"
- [ ] 신규 서비스 함수(`getRackNumberSummary`) + 조회 훅(`useRackNumberSummary`) 추가 완료
- [ ] Exclusions 항목(Tab2 편집 기능 없음, 필터 토글 없음, 페이지네이션 없음, 추가 검색/정렬
      UI 없음, Excel 내보내기 없음, Tab1 변경 없음)이 실제로 구현되지 않았음을 코드 리뷰로
      확인
- [ ] SPEC-ORDER-013 기존 테스트(백엔드 51개, 프론트엔드 15개) 전부 무변경 통과 확인
