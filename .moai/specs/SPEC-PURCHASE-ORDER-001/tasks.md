# Task Decomposition
SPEC: SPEC-PURCHASE-ORDER-001

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| M1-T1 | openpyxl>=3.1 의존성 추가 | REQ-PO-020 | - | backend/pyproject.toml | pending |
| M1-T2 | PurchaseOrder 모델 작성 | REQ-PO-040~044 | - | backend/order/models.py | pending |
| M1-T3 | VendorComparison 모델 작성 | REQ-PO-030~036 | - | backend/order/models.py | pending |
| M1-T4 | DistributorVendorRule 모델 작성 | REQ-PO-050~054 | - | backend/order/models.py | pending |
| M1-T5 | Django 마이그레이션 생성 | REQ-PO-001 | M1-T2,T3,T4 | backend/order/migrations/0003_purchase_order_models.py | pending |
| M1-T6 | 모델 단위 테스트 작성 | REQ-PO-001 | M1-T5 | backend/order/tests/test_purchase_order_models.py | pending |
| M2-T1 | UnorderedItemsSerializer 작성 | REQ-PO-010,011 | M1 | backend/order/serializers.py | pending |
| M2-T2 | UnorderedItemsView 작성 (SKU 집계 쿼리) | REQ-PO-010,011,012,013 | M1 | backend/order/purchase_order_views.py | pending |
| M2-T3 | auto_distributor 결정 로직 | REQ-PO-012 | M2-T2 | backend/order/purchase_order_views.py | pending |
| M2-T4 | URL 등록: purchase-orders/unordered/ | REQ-PO-010 | M2-T2 | backend/order/urls.py | pending |
| M2-T5 | 미발주 현황 API 테스트 | REQ-PO-010~013 | M2-T4 | backend/order/tests/test_purchase_orders.py | pending |
| M3-T1 | GenerateOrderFileSerializer 작성 | REQ-PO-022,023 | M1 | backend/order/serializers.py | pending |
| M3-T2 | ExcelFileGenerator 유틸 클래스 작성 | REQ-PO-020,021 | M1-T1 | backend/order/excel_utils.py | pending |
| M3-T3 | GenerateOrderFileView 작성 | REQ-PO-020~024 | M3-T1,T2 | backend/order/purchase_order_views.py | pending |
| M3-T4 | URL 등록: purchase-orders/generate-order-file/ | REQ-PO-020 | M3-T3 | backend/order/urls.py | pending |
| M3-T5 | 발주 파일 생성 API 테스트 | REQ-PO-020~024 | M3-T4 | backend/order/tests/test_purchase_orders.py | pending |
| M4-T1 | ExcelParser 클래스 작성 (컬럼명+위치 fallback) | REQ-PO-032,036 | M1-T1 | backend/order/excel_utils.py | pending |
| M4-T2 | auto_select_distributor() 순수 함수 작성 | REQ-PO-033 | - | backend/order/excel_utils.py | pending |
| M4-T3 | UploadVendorFileView 작성 | REQ-PO-030~036 | M4-T1,T2 | backend/order/purchase_order_views.py | pending |
| M4-T4 | VendorComparisonSerializer + VendorComparisonView 작성 | REQ-PO-034 | M1 | backend/order/serializers.py, purchase_order_views.py | pending |
| M4-T5 | URL 등록: upload-vendor-file/, comparison/ | REQ-PO-030,034 | M4-T3,T4 | backend/order/urls.py | pending |
| M4-T6 | 업체 자료 업로드/비교 API 테스트 | REQ-PO-030~036 | M4-T5 | backend/order/tests/test_purchase_orders.py | pending |
| M5-T1 | ConfirmOrderSerializer 작성 | REQ-PO-041 | M1 | backend/order/serializers.py | pending |
| M5-T2 | ConfirmOrderView 작성 (atomic + select_for_update) | REQ-PO-040~044 | M5-T1 | backend/order/purchase_order_views.py | pending |
| M5-T3 | URL 등록: purchase-orders/confirm/ | REQ-PO-040 | M5-T2 | backend/order/urls.py | pending |
| M5-T4 | 발주 확정 API 테스트 | REQ-PO-040~044 | M5-T3 | backend/order/tests/test_purchase_orders.py | pending |
| M6-T1 | DistributorVendorRuleSerializer 작성 | REQ-PO-052 | M1 | backend/order/serializers.py | pending |
| M6-T2 | DistributorVendorRuleListCreateView + DeleteView 작성 | REQ-PO-050~054 | M6-T1 | backend/order/purchase_order_views.py | pending |
| M6-T3 | URL 등록: vendor-rules/, vendor-rules/<int:pk>/ | REQ-PO-050,054 | M6-T2 | backend/order/urls.py | pending |
| M6-T4 | 발주처 규칙 CRUD 테스트 | REQ-PO-050~054 | M6-T3 | backend/order/tests/test_purchase_orders.py | pending |
| M7-T1 | PurchaseOrderListSerializer + FilterSet + ListView 작성 | REQ-PO-060,061 | M1 | backend/order/serializers.py, purchase_order_views.py, filters.py | pending |
| M7-T2 | URL 등록: purchase-orders/ | REQ-PO-060 | M7-T1 | backend/order/urls.py | pending |
| M7-T3 | 발주 목록 조회 API 테스트 | REQ-PO-060,061 | M7-T2 | backend/order/tests/test_purchase_orders.py | pending |
| M8-T1 | purchaseOrderApi.ts 작성 (9개 엔드포인트) | REQ-PO-070~082 | - | frontend/src/services/purchaseOrderApi.ts | pending |
| M8-T2 | usePurchaseOrderQueries.ts 작성 (TanStack Query) | REQ-PO-070~082 | M8-T1 | frontend/src/hooks/usePurchaseOrderQueries.ts | pending |
| M8-T3 | usePurchaseOrderStore.ts 작성 (Zustand) | REQ-PO-073,077 | - | frontend/src/stores/usePurchaseOrderStore.ts | pending |
| M8-T4 | UnorderedItemsTab.tsx 작성 | REQ-PO-072,073,074 | M8-T2,T3 | frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx | pending |
| M8-T5 | VendorFileUploadTab.tsx 작성 | REQ-PO-075,076,077 | M8-T2 | frontend/src/pages/PurchaseOrders/tabs/VendorFileUploadTab.tsx | pending |
| M8-T6 | ConfirmOrderTab.tsx 작성 | REQ-PO-078 | M8-T2,T3 | frontend/src/pages/PurchaseOrders/tabs/ConfirmOrderTab.tsx | pending |
| M8-T7 | PurchaseOrderHistoryTab.tsx 작성 | REQ-PO-079 | M8-T2 | frontend/src/pages/PurchaseOrders/tabs/PurchaseOrderHistoryTab.tsx | pending |
| M8-T8 | VendorRulesTab.tsx 작성 | REQ-PO-080 | M8-T2 | frontend/src/pages/PurchaseOrders/tabs/VendorRulesTab.tsx | pending |
| M8-T9 | PurchaseOrderPage index.tsx + 라우터 + 사이드바 등록 | REQ-PO-070,071 | M8-T4~T8 | frontend/src/pages/PurchaseOrders/index.tsx, router/index.tsx, Sidebar.tsx | pending |
