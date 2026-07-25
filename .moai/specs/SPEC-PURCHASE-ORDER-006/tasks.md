## Task Decomposition
SPEC: SPEC-PURCHASE-ORDER-006

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | Yes24Data 모델 추가 + 마이그레이션 생성 | REQ-PO6-001 | - | backend/order/models.py, backend/order/migrations/0024_yes24data.py | done |
| T-002 | _parse_yes24_xlsx 파서 + dispatch 분기 | REQ-PO6-002, REQ-PO6-003 | - | backend/order/excel_utils.py | done |
| T-003 | 파서 단위 테스트 (헤더 매핑/1행스킵/유통상태6종/잘못된ISBN/빈파일) | REQ-PO6-008 | T-002 | backend/order/tests/test_purchase_orders.py | done |
| T-004 | VENDOR_FILE_DISTRIBUTORS + UploadVendorFileView 3번째 분기 | REQ-PO6-004, REQ-PO6-005 | T-001, T-002 | backend/order/purchase_order_views.py | done |
| T-005 | 업로드 API 통합 테스트 (생성/upsert/잘못된distributor/빈파일422) | REQ-PO6-009 | T-004 | backend/order/tests/test_purchase_orders.py | done |
| T-006 | 프론트엔드 YES24 옵션 + 안내 문구 | REQ-PO6-006, REQ-PO6-007 | - | frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx | done |
| T-007 | 프론트엔드 신규 테스트 (YES24 옵션 표시/선택, distributor=yes24 API 호출) | REQ-PO6-006 (AC-008) | T-006 | frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.test.tsx (신규) | done |
| T-008 | 회귀 검증: test_auto_dist.py 및 발주서 생성 관련 테스트 무변경 통과 확인 | REQ-PO6-010 | T-001~T-007 | backend/order/tests/test_auto_dist.py (읽기 전용) | done |

Planned files column is used by the Drift Guard to detect scope drift.
