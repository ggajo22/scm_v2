import { create } from 'zustand'
import type { ConfirmItem } from '@/services/purchaseOrderApi'

interface PurchaseOrderState {
  // SKUs selected (checked) in UnorderedItemsTab
  selectedSkus: string[]
  // Items staged for order confirmation
  confirmItems: ConfirmItem[]

  toggleSku: (sku: string) => void
  selectAllSkus: (skus: string[]) => void
  clearSelections: () => void
  setConfirmItems: (items: ConfirmItem[]) => void
}

// @MX:ANCHOR: [AUTO] Central Zustand store for purchase order UI state
// @MX:REASON: Fan-in >= 3 — UnorderedItemsTab, ConfirmOrderTab, and VendorFileUploadTab all use this store

export const usePurchaseOrderStore = create<PurchaseOrderState>((set) => ({
  selectedSkus: [],
  confirmItems: [],

  toggleSku: (sku) =>
    set((state) => ({
      selectedSkus: state.selectedSkus.includes(sku)
        ? state.selectedSkus.filter((s) => s !== sku)
        : [...state.selectedSkus, sku],
    })),

  selectAllSkus: (skus) => set({ selectedSkus: skus }),

  clearSelections: () => set({ selectedSkus: [], confirmItems: [] }),

  setConfirmItems: (items) => set({ confirmItems: items }),
}))
