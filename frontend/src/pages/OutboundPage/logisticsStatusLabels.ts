// SPEC-ORDER-016 REQ-FORCE-021: `logistics_status` code -> Korean label map
// for the force-outbound candidate picker (REQ-FORCE-020). Mirrors
// LOGISTICS_STATUS_CHOICES in backend/order/models.py. Record (not Partial)
// so a new status code added to the backend choices becomes a compile-time
// gap here rather than a raw snake_case string leaking into the UI.
//
// No `purchase_status` label map is defined here: cancelled LineItems are
// excluded from candidates server-side (REQ-FORCE-005) and `purchase_status`
// is never included in the candidate payload (REQ-FORCE-006), so that value
// structurally cannot reach this UI.
export const LOGISTICS_STATUS_LABELS: Record<string, string> = {
  not_shipped: '미입고',
  shipment_confirmed: '입고예정',
  received: '입고',
  outbound_scheduled: '출고예정',
  shipped: '출고',
}
