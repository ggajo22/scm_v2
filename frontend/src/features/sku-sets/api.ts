import { api } from '@/lib/axios'

export interface MemberIsbn {
  isbn: string
  sort_order: number
  book_title: string | null
}

export interface SkuBundle {
  bundle_sku: string
  member_isbns: MemberIsbn[]
}

export const skuSetsApi = {
  list: (): Promise<SkuBundle[]> =>
    api.get('/api/shopify-sku-sets/').then((r) => r.data),

  create: (bundle_sku: string, member_isbns: string[]): Promise<SkuBundle> =>
    api.post('/api/shopify-sku-sets/', { bundle_sku, member_isbns }).then((r) => r.data),

  update: (bundle_sku: string, member_isbns: string[]): Promise<SkuBundle> =>
    api.put(`/api/shopify-sku-sets/${encodeURIComponent(bundle_sku)}/`, { member_isbns }).then((r) => r.data),

  delete: (bundle_sku: string): Promise<void> =>
    api.delete(`/api/shopify-sku-sets/${encodeURIComponent(bundle_sku)}/`).then((r) => r.data),
}
