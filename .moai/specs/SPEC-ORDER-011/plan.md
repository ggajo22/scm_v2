# SPEC-ORDER-011 구현 계획

## 기술 접근

브라운필드 변경. 기존 `order` 앱(`backend/order/`)의 모델·뷰·동기화 로직에 필드/엔드포인트를 추가한다. 새 앱/모듈은 만들지 않는다. 아래 [NEW]/[MODIFY] 마커는 CLAUDE.md 브라운필드 규칙에 따른 표기다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 데이터 모델 (Priority: High)

- [MODIFY] `backend/order/models.py`
  - `LineItem`에 `logistics_status` 필드 추가: `CharField(max_length=20, choices=LOGISTICS_STATUS_CHOICES, default="not_shipped")`, 5개 choices(REQ-LOGI-001).
  - `Order.status`에 `choices=ORDER_STATUS_CHOICES` 부여(6개 값: 5개 LineItem 코드 재사용 + `partial`). `max_length=50`은 변경 없음 — 컬럼 변경 없는 상태값 재정의(AlterField, DB 무영향).
- [NEW] 마이그레이션 (다음 번호부터 순차 부여, 계획 시점 기준 `0029`부터):
  - `0029_lineitem_add_logistics_status.py` — AddField, `0011_lineitem_add_purchase_status.py` 스타일 준수.
  - `0030_order_add_status_choices.py` — AlterField(choices만 추가, no-op SQL 예상).
  - `0031_backfill_order_status.py` — RunPython, `0026_backfill_bundle_lineitems.py` 관례(historical model, `noop` reverse, 상단 주석으로 알고리즘 설명) 준수. REQ-LOGI-012.
  - 실제 구현 시점에 SPEC-PURCHASE-ORDER-010과 번호가 겹치지 않도록 먼저 구현되는 SPEC이 `0029`를 선점하고, 다른 SPEC은 그 다음 번호로 조정.

### M2 — Shopify 동기화 제외 처리 (Priority: High)

- [MODIFY] `backend/order/shopify_orders.py`
  - `_sync_single_order()`의 `Order.objects.update_or_create()` defaults에서 `"status": order_data.get("financial_status")`(138번째 줄) 제거. REQ-LOGI-011.
  - LineItem `common_defaults`(203번째 줄 부근)에 `logistics_status` 미포함 상태 유지(신규 필드이므로 애초에 추가하지 않으면 됨) — REQ-LOGI-002.

### M3 — 업로드 엔드포인트 2개 (Priority: High)

참조 구현: `backend/order/purchase_order_views.py:998-1451` (`UploadDailyReviewView`) — parse → SKU dedupe → 단일 `transaction.atomic()` → `filter(sku__in=...).select_for_update()` → `bulk_update`/`bulk_create`.

- [NEW] `backend/order/excel_utils.py`: `parse_vendor_shipment_excel()`, `parse_warehouse_receipt_excel()` — `parse_daily_review_excel`(724번째 줄) 옆에 추가.
- [NEW] `backend/order/purchase_order_views.py`:
  - 벤더 출고확인 업로드 뷰 — REQ-LOGI-003, REQ-LOGI-004. 대상: `purchase_status != "unordered"` AND `logistics_status = "not_shipped"`.
  - 창고 입고결과 업로드 뷰 — REQ-LOGI-005, REQ-LOGI-006. 대상: `logistics_status IN ("not_shipped", "shipment_confirmed")`(Decision C 최종본, 미입고→입고 직행 경로 포함).
  - 두 뷰 모두 REQ-LOGI-009/010에 따라 영향받은 Order를 배치로 재계산.
- [MODIFY] `backend/order/urls.py`: 두 신규 업로드 엔드포인트 URL 등록(정확한 경로명은 Run 단계에서 기존 명명 규칙 — `purchase-orders/upload-*` — 참고해 확정).

### M4 — 수기 상태 변경 PATCH (Priority: High)

- [NEW] `backend/order/purchase_order_views.py`: `logistics_status` 단건/일괄 PATCH 뷰 — `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`(1463-1544번째 줄) 패턴 재사용. REQ-LOGI-007.
- 두 PATCH 모두 REQ-LOGI-009/010에 따라 Order 재계산 트리거.

### M5 — Order.status 집계 재계산 로직 (Priority: High)

- [NEW] 재계산 헬퍼 함수(예: `_recompute_order_status(order_ids: Iterable[int])`) — REQ-LOGI-008 규칙 구현, Order별 그룹화 배치 처리.
- M3/M4의 모든 write 경로에서 이 헬퍼를 호출.
- 쿼리 수 상한 회귀 테스트 추가 권장(SPEC-PURCHASE-ORDER-009의 `CaptureQueriesContext` 선례 참고).

### M6 — 프론트엔드 (Priority: Medium)

- [MODIFY] `frontend/src/services/purchaseOrderApi.ts`: `LOGISTICS_STATUS_OPTIONS` 신규 상수(`PURCHASE_STATUS_OPTIONS` 패턴 미러링), 단건/일괄 PATCH 래퍼, 업로드 API 래퍼 2개.
- [MODIFY] 관련 탭/페이지: `logistics_status` 컬럼/뱃지 추가 — REQ-LOGI-013에 따라 기존 `fulfillment_status` 컬럼과 시각적으로 구분되는 헤더/스타일.
- [MODIFY] `OrderDetailPage.tsx` 등: `Order.status` 집계값 표시(필터 UI는 제외 범위).

## 리스크

- **Excel 컬럼 레이아웃 미정** (spec.md "확인이 필요한 가정" 참조) — Run 단계 착수 전 실제 템플릿/컬럼 스펙 확보 필요. 확보 전 착수 시 파싱 함수 재작업 위험.
- **마이그레이션 번호 충돌**: SPEC-ORDER-011과 SPEC-PURCHASE-ORDER-010이 병렬로 구현될 경우 `0029`를 먼저 커밋하는 쪽이 선점 — Run 단계 시작 시 최신 마이그레이션 상태 재확인 필요.
- **N+1 회귀**: Order 재계산을 LineItem 단위로 잘못 구현하면 SPEC-PURCHASE-ORDER-009에서 해결한 것과 동일한 성능 문제가 재발할 수 있음 — M5에서 배치 그룹화를 반드시 검증.

## 참조 구현

- 배칭 패턴: `backend/order/purchase_order_views.py:998-1451` (`UploadDailyReviewView`)
- PATCH 패턴: `backend/order/purchase_order_views.py:1463-1544` (`LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`)
- 마이그레이션: `0011_lineitem_add_purchase_status.py`, `0026_backfill_bundle_lineitems.py`
- N+1 방지 선례: SPEC-PURCHASE-ORDER-009 전체
