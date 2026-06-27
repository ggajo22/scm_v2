import { create } from 'zustand'

interface PurchaseOrderState {
  // SKUs selected (checked) in UnorderedItemsTab
  selectedSkus: string[]

  toggleSku: (sku: string) => void
  selectAllSkus: (skus: string[]) => void
  clearSelections: () => void
}

// @MX:ANCHOR: [AUTO] Central Zustand store for purchase order UI state
// @MX:REASON: Fan-in >= 3 — UnorderedItemsTab and VendorFileUploadTab use this store

export const usePurchaseOrderStore = create<PurchaseOrderState>((set) => ({
  selectedSkus: [],

  toggleSku: (sku) =>
    set((state) => ({
      selectedSkus: state.selectedSkus.includes(sku)
        ? state.selectedSkus.filter((s) => s !== sku)
        : [...state.selectedSkus, sku],
    })),

  selectAllSkus: (skus) => set({ selectedSkus: skus }),

  clearSelections: () => set({ selectedSkus: [] }),
}))
