## Task Decomposition
SPEC: SPEC-ORDER-015

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T1 | LineItem.shipped_quantity/shipped_at 필드 + migration 0035 | REQ-001,002,002a | - | backend/order/models.py, backend/order/migrations/0035_lineitem_add_shipped_fields.py | completed |
| T2 | 동일 요청 내 (order_name, sku) 중복 행 합산 그룹화 | REQ-007 | - | backend/order/purchase_order_views.py | completed |
| T3 | Order.name 매칭 + (order, sku) LineItem 매칭 분기(0/1/2건+) | REQ-003,003a,004,005,005a,006 | T2 | backend/order/purchase_order_views.py | completed |
| T4 | 수량초과 판정(null=0) + shipped_quantity 증분 + shipped_at 갱신 + logistics_status 전이 | REQ-008,009,010,010a | T1,T3 | backend/order/purchase_order_views.py | completed |
| T5 | parse_outbound_excel 헤더 자동탐색 파서 | REQ-012,012a | - | backend/order/excel_utils.py | completed |
| T6 | OutboundProcessView/UploadOutboundView + URL 등록 | REQ-011,013,014 | T4,T5 | backend/order/purchase_order_views.py, backend/order/urls.py | completed |
| T7 | LineItemDetailSerializer shipped_quantity/shipped_at 노출 (사용자 승인, 포함 확정) | - | T1 | backend/order/serializers.py | completed |
| T8 | outboundApi.ts + useOutboundQueries.ts | REQ-016 | T6 | frontend/src/services/outboundApi.ts, frontend/src/hooks/useOutboundQueries.ts | completed |
| T9 | OutboundPage + 라우터 + 사이드바 | REQ-015,016,017,018 | T8 | frontend/src/pages/OutboundPage/index.tsx, frontend/src/pages/OutboundPage/parseManualRows.ts, frontend/src/router/index.tsx, frontend/src/components/Sidebar.tsx | completed |
| T10 | Exclusions 위반 검증 + SPEC-ORDER-013/014 회귀 스위트 재실행 + LSP 게이트 | REQ-019 | T6,T9 | (검증 전용) | completed |

Dependency order: T1‖T2‖T5 → T3 → T4 → T6 → T8 → T9 → T10. T7 independent after T1.
