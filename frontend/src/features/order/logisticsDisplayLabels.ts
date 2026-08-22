import { LOGISTICS_STATUS_LABELS } from '@/pages/OutboundPage/logisticsStatusLabels'

// 주문상세/주문목록 표시 일원화: single label map for the derived
// `logistics_display` value, shared by OrdersPage (목록) and OrderDetailPage
// (상세). Both screens read the same backend field — computed live from
// LineItem rows by LineItemStateDerivationMixin — so they must also render it
// through the same labels; two copies drifted before (the detail badge used
// the stored `Order.status` column with its own map).
//
// Extends the SPEC-ORDER-016-owned LOGISTICS_STATUS_LABELS (imported, not
// modified) with the 2 additional display values SPEC-ORDER-023 introduces.
// `received` from the shared map is intentionally unused here — it is never
// emitted as a logistics_display value (see Order.logistics_display).
export const ORDER_LOGISTICS_DISPLAY_LABELS: Record<string, string> = {
  ...LOGISTICS_STATUS_LABELS,
  partial_shipped: '부분출고',
  partial: '부분입고',
}
