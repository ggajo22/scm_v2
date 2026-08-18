import { describe, it, expect } from 'vitest'
import {
  PURCHASE_STATUS_OPTIONS,
  PURCHASE_STATUS_LABELS,
  LOGISTICS_STATUS_OPTIONS,
} from './purchaseOrderApi'

// SPEC-PURCHASE-ORDER-011 (dropdown removal): damaged_exchange is exclusive
// to the new /damaged-exchange page — the backend now rejects it on
// PATCH .../line-items/<pk>/status/ and PATCH .../line-items/bulk-status/, so
// it must not be offered as a selectable dropdown option.
//
// INVERTS the SPEC-PURCHASE-ORDER-010 (T9) assertion this test used to make
// ("includes damaged_exchange") — that behavior is now deliberately removed.
describe('PURCHASE_STATUS_OPTIONS', () => {
  it('does NOT include damaged_exchange (SPEC-PURCHASE-ORDER-011: exclusive to /damaged-exchange page)', () => {
    expect(PURCHASE_STATUS_OPTIONS).not.toContainEqual(
      expect.objectContaining({ value: 'damaged_exchange' })
    )
    expect(PURCHASE_STATUS_OPTIONS.map((o) => o.value)).not.toContain('damaged_exchange')
  })

  it('preserves all five remaining options unmodified', () => {
    const existing = [
      { value: 'unordered', label: '미발주' },
      { value: 'on_hold', label: '주문보류' },
      { value: 'order_cancelled', label: '주문취소' },
      { value: 'cs_required', label: 'CS필요' },
      { value: 'in_stock', label: '재고' },
    ]
    for (const option of existing) {
      expect(PURCHASE_STATUS_OPTIONS).toContainEqual(option)
    }
  })

  // SPEC-ORDER-025 REQ-LCONF-304/AC-LCONF-304: other_publisher may only be
  // produced by the Daily Review upload path now — the manual dropdown must
  // no longer offer it, mirroring the damaged_exchange exclusion above.
  it('does NOT include other_publisher (SPEC-ORDER-025: exclusive to Daily Review upload)', () => {
    expect(PURCHASE_STATUS_OPTIONS).not.toContainEqual(
      expect.objectContaining({ value: 'other_publisher' })
    )
    expect(PURCHASE_STATUS_OPTIONS.map((o) => o.value)).not.toContain('other_publisher')
  })
})

// SPEC-PURCHASE-ORDER-011: PURCHASE_STATUS_LABELS is the full display map —
// unlike PURCHASE_STATUS_OPTIONS above, it still carries damaged_exchange so
// existing rows at that status render "파손/교환" instead of the raw enum
// string wherever they are displayed (e.g. SPEC-ORDER-018 REQ-RESTORE-017).
describe('PURCHASE_STATUS_LABELS', () => {
  it('still maps damaged_exchange to its Korean label for display purposes', () => {
    expect(PURCHASE_STATUS_LABELS.damaged_exchange).toBe('파손/교환')
  })

  // SPEC-ORDER-025 REQ-LCONF-305/AC-LCONF-305: other_publisher was removed
  // from PURCHASE_STATUS_OPTIONS above, but existing rows at that status
  // must still render their Korean label wherever displayed — same
  // "selectable removed, display-map kept" pattern as damaged_exchange.
  it('still maps other_publisher to its Korean label for display purposes', () => {
    expect(PURCHASE_STATUS_LABELS.other_publisher).toBe('타출판사')
  })

  it('has a label for every selectable PURCHASE_STATUS_OPTIONS value', () => {
    for (const opt of PURCHASE_STATUS_OPTIONS) {
      expect(PURCHASE_STATUS_LABELS[opt.value]).toBe(opt.label)
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
