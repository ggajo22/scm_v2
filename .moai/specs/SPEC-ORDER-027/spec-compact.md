# SPEC-ORDER-027 — Compact Summary

> v0.2.0 — plan-auditor 1차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-027-review-1.md`, **FAIL, 0.50**) 반영. **입고 정의가 교체되었다**: `logistics_status`(상태) 기반 → `LineItem.received_quantity`(필드) 기반. 이제 백엔드 변경을 포함한다(v0.1.0은 프런트엔드 전용이었음).
> v0.2.1 — plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-027-review-2.md`, **PASS, 0.75**) 반영. 구조·요구사항 신설 없이 5건 정정 + 1건 정리만 적용했다: 그룹 격리 미검증 공백 해소(N9, AC-012 신설), M1 단독 판별 오표기 정정(N1), AC-010의 M5 공동 판별 누락 정정(N2), 클램프 원인의 두 번째 독립 경로 추가(N4, Shopify 재동기화로 `quantity` 자체가 바뀔 수 있음), NULL 경로를 방어적/도달 불가 케이스로 정직화(N6), REQ-RACKRECV-006을 가정 A1로 통합·폐기(N7).

## 왜 정의가 바뀌었는가 (D1, critical)

`LineItem.received_quantity`(`backend/order/models.py:228`, `IntegerField(default=0)`)는 이미 존재하는 필드다. `_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`)가 입고 업로드마다 이 값을 누적하고, `received_quantity >= quantity`가 될 때만 `logistics_status`를 `"received"`로 전환한다(`:2549-2550`). 즉 **부분 입고는 상태를 바꾸지 않는다** — v0.1.0의 "`received` 상태인 행만 카운트" 정의는 `quantity=5, received_quantity=3, logistics_status="shipment_confirmed"`인 행을 `입고 0`으로 표시하는 결함이었다.

## 새 정의 (사용자 재확정)

`group.received_quantity = Σ min(li.received_quantity, net_qty)`, 그룹에 기여하는 모든 라인아이템에 대해(`logistics_status`와 무관). `net_qty`는 기존 환불 순액화 값(`purchase_order_views.py:3446`, `max((li.quantity or 0) - li.refunded_qty, 0)`)을 그대로 재사용한다.

**클램프가 필요한 이유**: `received_quantity`는 환불이 기록되어도 소급 감산되지 않는다(이 세션에서 `grep -r received_quantity backend/`로 유일한 쓰기 경로가 `:2542` 한 곳뿐임을 확인). 전량 입고 후 부분 환불된 품목은 `received_quantity`(예: 5)가 그 시점의 `net_qty`(예: 3)보다 커질 수 있다 — 클램프 없이는 "입고 5 / 총 3"처럼 입고가 총을 초과하는 표시가 나온다. **[v0.2.1 추가, 감사 N4]** 원인은 환불만이 아니다 — `LineItem.quantity` 자체가 Shopify 재동기화마다 덮어써지므로(`shopify_orders.py:236`, `update_or_create`의 `defaults`로 쓰이는 지점 `:265`/`:281`), 환불이 전혀 없어도 재동기화로 `quantity`가 하향 정정되면 같은 괴리가 생긴다. REQ-RACKRECV-003의 조건은 원인 무관(cause-agnostic)이라 이미 두 경로 모두 커버한다.

## 왜 더 이상 프런트엔드 전용이 아닌가

`received_quantity`는 그룹 요약 API 응답에 없다 — 프런트엔드가 소유하지 않은 백엔드 필드다. 클라이언트에서 파생할 방법이 없으므로, 백엔드가 그룹 레벨로 신규 집계해 응답에 추가해야 한다. 행 레벨(`RackNumberSummaryLineItem`)에는 노출하지 않는다 — 그룹 헤더 집계 목적에만 필요하다.

## 표기 형식 (v0.1.0에서 유지)

`입고 {group.received_quantity} / 총 {group.total_quantity}권`. 두 값 모두 API 응답에서 그대로 읽으며, 클라이언트는 어떤 산술도 하지 않는다 — 이 설계가 v0.1.0의 D2(`?? 0` 가드 판별 불가) 결함을 부수적으로 해소한다.

## 핵심 결정

- **상태 무관, 필드 기반.** `logistics_status` 비교를 완전히 제거한다 — 부분 입고(상태 미전환)도 그대로 반영된다.
- **클램프는 필수, 두 경로 모두 테스트한다.** 환불로 인한 축소(AC-002)와 NULL quantity로 인한 축소(AC-003) — 하나만 테스트하면 다른 경로의 클램프 누락을 놓친다.
- **행 레벨 노출 없음.** 그룹 딕셔너리에만 추가한다 — 개별 라인아이템 필드, 행별 "수량" 컬럼은 무변경.
- **클라이언트 산술 없음.** API가 준 정수 두 개를 문자열에 끼워 넣을 뿐이다 — 재계산·가드·재클램프 전부 금지.
- **헤더는 단일 텍스트 노드.** 기존 `SummaryTab.test.tsx:103`의 `getByText('입고')`(물류상태 `received` 라벨과 동일 리터럴)와 충돌하지 않도록, 헤더를 별도 `<span>`으로 쪼개지 않는다(D5).
- **DB 마이그레이션 불필요.** `received_quantity`는 이미 존재하는 컬럼이다.
- **쓰기 경로 무변경.** `_process_warehouse_receipt_rows`는 건드리지 않는다 — 이 SPEC은 읽기 전용 집계 추가다.

## 요구사항 (EARS, REQ-RACKRECV-001~018, 006은 v0.2.1에서 폐기·결번)

| 모듈 | REQ | 내용 |
|---|---|---|
| 1 | 001~005 | 백엔드 그룹 집계: 필드 추가, 클램프 정의(Unwanted), 상태 무관 적용, NULL 처리 (**REQ-006 폐기** — 모델 사실 서술이라 가정 A1로 통합, 감사 N7) |
| 2 | 007 | API 타입: 그룹 레벨만 추가, 행 레벨 무변경 |
| 3 | 008~012 | 프런트엔드 렌더링: API 값 그대로, 0건 표기, 미지정 그룹, 접힘/펼침 무관, 단일 텍스트 노드(D5) |
| 4 | 013~018 | 비목표 불변식: SearchTab/read-only/행별 컬럼/정렬/쓰기 경로/마이그레이션 무변경 |

## 인수 기준 12개(백엔드 7 + 프런트엔드 5) — 판별력 매핑

잡아야 하는 변이 **8개**: M1(BE, 상태 게이트 잔존) — AC-001+AC-004 **공동**(v0.2.1 N1 정정, 이전 버전은 AC-001을 단독이라 잘못 표기) · M2(BE, 클램프 누락) — AC-002+AC-003 공동 필수 · M3(BE, 필드 미추가) — 전체 안전망, AC-005 대표 · **M4(BE, 미지정 특수케이스) — AC-006 단독** · **M8(BE, 그룹 간 격리 미비, v0.2.1 N9 신규) — AC-012 단독** · M5(FE, 필드 뒤바뀜) — AC-007/008/009/010 4중 공동(v0.2.1 N2에서 AC-010 추가) · **M6(FE, 0건 숨김) — AC-008 단독** · **M7(FE, 헤더 노드 분리, D5) — AC-011 단독**.

**단독 판별자 4건은 삭제·약화 금지**: M4=AC-006, M6=AC-008, M7=AC-011, M8=AC-012. AC-001은 M1의 공동 판별자(단독 아님, v0.2.1 N1)이지만 계속 유지한다 — 가장 단순한 단일 품목 증명. AC-010(접힘/펼침)은 M5를 공동으로 잡으면서 그 외에는 회귀 확인 목적이다(v0.2.1 N2 정정).

> **감사 재발 방지**: 모든 "단독" 표시는 변이 코드를 픽스처에 직접 대입해 결과값이 실제로 달라지는지 확인한 결과다(감사 D2/D4/N1/N2 재발 방지). 공동 판별(M1, M2, M5)은 정직하게 "공동"으로 표기했다.

## 영향 파일 (5개)

`[MODIFY]` `backend/order/purchase_order_views.py`(`:3442-3479` + 신규 `@MX:NOTE`) · `[NEW]` `backend/order/tests/test_spec_027.py` · `[MODIFY]` `frontend/src/services/rackNumberApi.ts`(`:68-73`) · `[MODIFY]` `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx`(`:96`) · `[MODIFY]` `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx`
`[EXISTING]` 무변경: `SearchTab.tsx`, `_process_warehouse_receipt_rows`(`:2392-2579`), `RackNumberSummaryLineItem` 타입, 정렬 블록(`:3481-3489`)

## MX 태그

`purchase_order_views.py`에 신규 `@MX:NOTE` 1건 추가(클램프가 필요한 이유 — 환불과 입고 누적의 비동기화). `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE`(read-only 불변식)는 그대로 유지.

## 문서

- 코드베이스 근거·검증 내역, EARS 요구사항·Exclusions·알려진 제약: `spec.md`
- 마일스톤·위험·MX 계획: `plan.md`
- Given-When-Then + 변이별 판별력 대조표: `acceptance.md`
- 이 재설계의 근거가 된 1차 감사 보고서(FAIL, 0.50): `.moai/reports/plan-audit/SPEC-ORDER-027-review-1.md`
- v0.2.1 정정의 근거가 된 2차 감사 보고서(PASS, 0.75): `.moai/reports/plan-audit/SPEC-ORDER-027-review-2.md`
