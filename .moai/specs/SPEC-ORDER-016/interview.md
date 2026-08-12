# Interview: /outbound 매칭 실패 강제 출고 처리

원본 요청: `/outbound 페이지에서 출고 처리 매칭 실패 시 강제 출고 처리 버튼`

인터뷰 진행일: 2026-08-12
대상 SPEC: SPEC-ORDER-016 (SPEC-ORDER-015 확장)

## 사전 조사 요약 (질문 설계 근거)

`/outbound` 결과는 `matched` / `unmatched` / `quantity_exceeded` 3분류이며,
`unmatched`의 `reason` 코드는 5종이다
(`backend/order/purchase_order_views.py` `_process_outbound_rows`,
`frontend/src/services/outboundApi.ts` `OutboundUnmatchedReason`).

| reason | 의미 | 강제 처리 가능성 |
|---|---|---|
| `order_not_found` | 해당 `Order.name` 없음 | 기록 대상 LineItem 부재 — 물리적으로 불가 |
| `line_item_not_found` | 주문은 있으나 그 SKU의 LineItem 없음 | 대상 지정이 필요 |
| `multiple_line_items` | 동일 SKU LineItem 2건 이상 | 대상 지정이 필요 |
| `invalid_total` | 수량이 음수/판독불가/0(비-미국창고) | 수량 재입력이 필요 |
| `invalid_row` | 행 형식 오류 | 기록 대상 부재 — 불가 |

## Round 1: 범위 (Scope)

**Q1. 강제 출고 처리 버튼을 어느 결과 분류에 노출할까요?**
- 답변: **매칭 실패 섹션만**
- 함의: `quantity_exceeded` 섹션은 기존 동작 유지. 수량초과 건은 강제 대상이 아니다.

**Q2. 매칭 실패 사유 중 어디까지 강제 처리를 허용할까요?**
- 답변: **SKU 불일치만** (`line_item_not_found`)
- 함의: `multiple_line_items`, `invalid_total`, `order_not_found`, `invalid_row`는
  강제 대상에서 제외한다. 강제 컨트롤은 `reason === "line_item_not_found"` 행에만 노출된다.

**Q3. 강제 처리 실행은 어떤 단위로 할까요?**
- 답변: **행별 체크박스 + 일괄 실행**
- 함의: 선택된 행 전체를 하나의 요청으로 전송한다. 원격 DB 왕복 비용(~130ms/쿼리)을
  고려해 배치 쿼리 설계가 필수다.

**Q4. 강제 처리된 건을 별도로 추적해야 할까요?**
- 답변: **별도 이력 없이 기존 필드만 갱신**
- 함의: `LineItem`에 신규 컬럼/마이그레이션 없음. 감사 로그 테이블 없음.
  `shipped_quantity` / `shipped_at` / `logistics_status`만 갱신한다.

## Round 2: 강제 처리 동작 정의 (Behavior)

**Q5. SKU 불일치 행을 강제 처리할 때 출고 수량을 어느 LineItem에 기록할까요?**
- 답변: **주문 내 품목 목록에서 사용자가 직접 선택**
- 함의:
  - 자동 추론(빈 SKU 자동 반영 / 미출고 순차 분배) 없음
  - 신규 LineItem 생성 없음 — 주문 원본 구성은 불변
  - 대상 주문의 LineItem 목록(제목/SKU/주문수량/기출고 수량)을 프론트에 제공해야 함
  - 강제 요청 payload는 대상 `line_item_id`를 명시적으로 실어야 함

**Q6. 강제 반영 시 주문 수량(잔여 용량) 초과도 허용할까요?**
- 답변: **초과 불가**
- 함의:
  - 강제가 우회하는 것은 **SKU 매칭 규칙뿐**이며, 수량 한도는 그대로 유지된다
  - `shipped_quantity + total > quantity`인 강제 요청은 반영하지 않고
    `quantity_exceeded`로 다시 보고한다
  - SPEC-ORDER-015의 "NULL quantity == 0 capacity"(설계 결정 B),
    "shipped_quantity는 감소 불가" 불변식이 강제 경로에서도 그대로 성립한다

## 확정된 스코프 요약

강제 출고 처리는 **`line_item_not_found` 행에 한해, 사용자가 명시적으로 지정한
LineItem에, 수량 한도를 지킨 채 출고 수량을 누적하는** 기능이다.
정상 경로와의 유일한 차이는 `(order, sku)` 매칭 단계를 사용자 지정으로 대체하는 것이다.

## Clarity Score

- Initial: 5/10 (대상/동작/사유 범위 모두 미정)
- Final: 9/10 (반영 대상, 수량 규칙, 실행 단위, 이력 정책 확정)
- Rounds completed: 2

## 남은 설계 판단 (SPEC 단계에서 결정)

인터뷰로 확정할 필요가 없는, 구현 접근 수준의 열린 항목:

1. 주문 내 LineItem 목록 조달 방식 — (a) 기존 `unmatched` 응답에 후보 목록을 동봉,
   (b) 여러 주문분을 한 번에 조회하는 신규 배치 엔드포인트. 둘 다 요청 1회 이내로
   해결 가능하며, 응답 계약 변경 범위가 판단 기준이다.
2. 강제 처리 엔드포인트를 신설할지, 기존 `outbound-process/`에 대상 지정 필드를
   추가할지.
3. 강제 실행 결과를 기존 3분류 응답으로 그대로 반환할지 여부.
