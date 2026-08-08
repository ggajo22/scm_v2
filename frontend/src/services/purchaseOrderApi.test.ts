import { describe, it, expect } from 'vitest'
import { PURCHASE_STATUS_OPTIONS } from './purchaseOrderApi'

// SPEC-PURCHASE-ORDER-010 (T9): PURCHASE_STATUS_OPTIONS gains a 파손/교환
// (damaged_exchange) entry, consumed automatically by the existing dropdowns
// in UnorderedItemsTab.tsx / ConfirmOrderTab.tsx.
describe('PURCHASE_STATUS_OPTIONS', () => {
  it('includes damaged_exchange (파손/교환)', () => {
    expect(PURCHASE_STATUS_OPTIONS).toContainEqual({
      value: 'damaged_exchange',
      label: '파손/교환',
    })
  })

  it('preserves all six existing options unmodified', () => {
    const existing = [
      { value: 'unordered', label: '미발주' },
      { value: 'on_hold', label: '주문보류' },
      { value: 'order_cancelled', label: '주문취소' },
      { value: 'other_publisher', label: '타출판사' },
      { value: 'cs_required', label: 'CS필요' },
      { value: 'in_stock', label: '재고' },
    ]
    for (const option of existing) {
      expect(PURCHASE_STATUS_OPTIONS).toContainEqual(option)
    }
  })
})
