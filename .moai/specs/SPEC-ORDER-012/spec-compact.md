# SPEC-ORDER-012 Compact

버전 1.0.0 기준(초안, Phase 2 파일 생성 완료 — 상세 구현 참조는 plan.md, 인수 시나리오는
acceptance.md 참조).

## 요구사항

- REQ-RTS-001: `Order.ready_to_ship` 신규 필드, True/False/null 3상태, `Order.status`와 완전 독립
- REQ-RTS-002: 집계 규칙 — `order_cancelled` 제외 → 0개 남으면 null → `cs_required` 있으면 False →
  그 외 전원 `received` 또는 `in_stock`이면 True, 아니면 False
- REQ-RTS-003: 기존 4개 `logistics_status` write path에서 `Order.status`와 같은 패스로
  `ready_to_ship`도 재계산
- REQ-RTS-003a: 신규 4개 `purchase_status` write path(ConfirmOrderView, 단건/일괄 PATCH, Daily
  Review 3분기)에도 동일 재계산 신규 연결 — 지금까지 이 경로들은 Order 재계산을 전혀 하지 않았음
- REQ-RTS-004: 다중 Order 배치 재계산 시 N개 Order 전부의 `ready_to_ship`/`status`를 재계산
- REQ-RTS-004a: 위 재계산의 쿼리 수는 LineItem 개수가 아닌 distinct Order 개수에 비례(비기능 제약,
  004에서 분리)
- REQ-RTS-005: Shopify 동기화가 `ready_to_ship`을 덮어쓰지 않음
- REQ-RTS-006: 기존 Order 백필 마이그레이션
- REQ-RTS-007/008: UI 뱃지 — 3개 뱃지 시각적 구분, null이면 미노출

## 설계 결정 요약

- 필드 타입: `BooleanField(null=True, blank=True)` 3상태(`Order.status`의 null 선례 채택)
- `_recompute_order_status()` → `_recompute_order_aggregates()`로 확장+리네임(같은 SELECT/UPDATE
  재사용, 추가 쿼리 없음) — SPEC-ORDER-011 산출물을 건드리는 cross-SPEC 수정, 사용자 승인 완료
- 마이그레이션 `AddField` + `RunPython` 백필 분리, reverse `noop`
- 계산 전용 필드, 수동 PATCH 엔드포인트 없음

## 인수 기준 요약

- 계산 규칙: 전량취소/무추적→null, cs_required 하드블록→False, in_stock 단독 충족→True,
  received 단독 충족→True, 혼재 미충족→False
- 8개 write path 모두 재계산 트리거(요청당 1회, N+1 없음)
- 다중 Order 배치 쿼리 수 상한 회귀 테스트
- Shopify 재동기화 후 값 무변경
- 백필 마이그레이션 후 기존 Order 전량 재계산
- 프론트엔드 뱃지 3개 시각적 구분 + null 미노출

## 제외

- ready_to_ship 필터 UI/API
- ready_to_ship 수동 PATCH 엔드포인트
- WarehouseStock 증분 연동
- PurchaseOrder.status 연동
- ready_to_ship=True 전이 시 알림/이메일
