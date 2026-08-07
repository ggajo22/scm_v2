# SPEC-ORDER-011 Compact

버전 1.1.0 기준(Phase 2.3 리뷰 반영: REQ 본문에서 구현 세부사항 제거, spec.md에 EARS 형식 ACCEPTANCE CRITERIA 섹션 신설 — AC-LOGI-001~014, 상세 구현 참조는 plan.md 참조).

## 요구사항

- REQ-LOGI-001: `LineItem.logistics_status` 신규 필드, 5값(미입고/입고예정/입고/출고예정/출고), 기본값 미입고, purchase_status/fulfillment_status와 독립
- REQ-LOGI-002: Shopify 동기화가 `logistics_status`를 덮어쓰지 않음
- REQ-LOGI-003: 벤더 출고확인 업로드 — `purchase_status != unordered` AND `logistics_status = not_shipped` 매칭 → `shipment_confirmed`
- REQ-LOGI-004: 업로드 응답에 매칭/스킵 카운트 포함
- REQ-LOGI-005: 창고 입고결과 업로드 — `logistics_status IN (not_shipped, shipment_confirmed)` 매칭 → `received` (미입고→입고 직행 경로 포함, Revision 1)
- REQ-LOGI-006: `received` 전이 시 `WarehouseStock.quantity` 미변경
- REQ-LOGI-007: `logistics_status` 단건/일괄 PATCH 엔드포인트(기존 purchase_status PATCH 패턴 재사용)
- REQ-LOGI-008: `Order.status` = trackable LineItem 집계(동일값 그대로, 혼재 시 `partial`)
- REQ-LOGI-009/010: LineItem write마다 부모 Order 재계산, 다중 Order는 배치 처리
- REQ-LOGI-011: Shopify sync가 `Order.status`를 financial_status로 덮어쓰지 않음(`shopify_orders.py:138` 제거)
- REQ-LOGI-012: 기존 Order 백필 마이그레이션
- REQ-LOGI-013: UI에서 fulfillment_status 컬럼과 시각적으로 구분
- REQ-LOGI-014: `PurchaseOrder.status`와 완전 독립

## 인수 기준 요약

- 업로드 1: 정상 전이 + 미발주 SKU 스킵 회귀
- 업로드 2: 정상 경로(입고예정→입고) + 직행 경로(미입고→입고 skip) 둘 다 통과
- Order 집계: 단일값/혼재값 케이스, 다중 Order 배치 재계산 쿼리 수 검증
- Shopify 재동기화 후 값 무변경
- 프론트엔드 컬럼 시각적 구분
- 백필 마이그레이션 후 기존 Order 전량 재계산

## 제외

- Order.status 필터 UI/API
- partial 세분화(부분입고 vs 부분출고)
- WarehouseStock 증분 연동
- PurchaseOrder.status 연동
- Excel 컬럼 레이아웃 확정(Run 단계 전 별도 확인 필요)
