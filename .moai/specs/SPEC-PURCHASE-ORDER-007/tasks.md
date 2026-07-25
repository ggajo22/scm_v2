## Task Decomposition
SPEC: SPEC-PURCHASE-ORDER-007

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | generate_order_excel() yes24 분기 + 단위 테스트 | REQ-PO7-001, REQ-PO7-005 | - | backend/order/excel_utils.py, backend/order/tests/test_purchase_orders.py | done |
| T-002 | VALID_DISTRIBUTORS + GenerateOrderFileView 통합 테스트 | REQ-PO7-002, REQ-PO7-006 | T-001 | backend/order/purchase_order_views.py, backend/order/tests/test_purchase_orders.py | done |
| T-003 | 프론트엔드 distributorLabel + YES24 버튼 | REQ-PO7-003, REQ-PO7-004 | T-002 | frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx | done |
| T-004 | 프론트엔드 신규 테스트 (버튼 렌더링 + 클릭 시 API 호출) | REQ-PO7-007 | T-003 | frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx (신규) | done |
| T-005 | 회귀 검증: booxen/kyobo/test_auto_dist.py/SPEC-006 yes24 업로드 테스트 무변경 통과 | REQ-PO7-008 | T-001~T-004 | backend/order/tests/test_auto_dist.py, backend/order/tests/test_purchase_orders.py (읽기 전용) | done |

Planned files column is used by the Drift Guard to detect scope drift.
