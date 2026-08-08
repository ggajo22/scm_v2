import { describe, it, expect } from 'vitest'
import { PURCHASE_STATUS_OPTIONS, LOGISTICS_STATUS_OPTIONS } from './purchaseOrderApi'

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

// SPEC-ORDER-011 T11: LOGISTICS_STATUS_OPTIONS mirrors REQ-LOGI-001's five
// logistics_status values, independent of PURCHASE_STATUS_OPTIONS above.
describe('LOGISTICS_STATUS_OPTIONS', () => {
  it('contains exactly the five REQ-LOGI-001 values in pipeline order', () => {
    expect(LOGISTICS_STATUS_OPTIONS).toEqual([
      { value: 'not_shipped', label: '미입고' },
      { value: 'shipment_confirmed', label: '입고예정' },
      { value: 'received', label: '입고' },
      { value: 'outbound_scheduled', label: '출고예정' },
      { value: 'shipped', label: '출고' },
    ])
  })
})
