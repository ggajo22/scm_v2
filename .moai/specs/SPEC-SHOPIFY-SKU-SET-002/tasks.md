## Task Decomposition
SPEC: SPEC-SHOPIFY-SKU-SET-002

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | LineItem unique_together 스키마 변경 + 마이그레이션 | REQ-SKUSET2-001, REQ-SKUSET2-002 | - | backend/order/models.py, backend/order/migrations/0025_*.py | done |
| T-002 | _sync_single_order() 번들-인식형 전개 구현 | REQ-SKUSET2-003, REQ-SKUSET2-004, REQ-SKUSET2-005 | T-001 | backend/order/shopify_orders.py | done |
| T-003 | UnorderedItemsView/GenerateOrderFileView 정리 (되돌리기) | REQ-SKUSET2-007, REQ-SKUSET2-008, REQ-SKUSET2-009 | T-002 | backend/order/purchase_order_views.py | done |
| T-004 | 데이터 백필 마이그레이션 (기존 미발주 번들 LineItem 전개) | REQ-SKUSET2-011, REQ-SKUSET2-012 | T-001 | backend/order/migrations/0026_*.py, backend/order/tests/test_backfill_bundle_lineitems_migration.py | done |
| T-005 | 싱크 파이프라인 신규 테스트 | REQ-SKUSET2-014 | T-002 | backend/order/tests/test_shopify_orders.py | done |
| T-006 | 기존 테스트 재작성 (화면 시점 전개 테스트 제거/전환) | REQ-SKUSET2-013 | T-002, T-003 | backend/order/tests/test_shopify_sku_set.py, backend/order/tests/test_purchase_orders.py, backend/order/tests/test_purchase_order_models.py | done |
| T-007 | 재동기화 엣지 케이스 회귀 테스트 (권장) | REQ-SKUSET2-015, REQ-SKUSET2-010 | T-002 | backend/order/tests/test_order_resync.py | done |
| T-008 | 전체 회귀 검증 (test_auto_dist.py 등 무변경 통과 확인) | REQ-SKUSET2-013 | T-001~T-007 | backend/order/tests/ (읽기 전용) | done |

Planned files column is used by the Drift Guard to detect scope drift.
