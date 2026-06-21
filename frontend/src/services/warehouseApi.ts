import { api } from '@/lib/axios'

export interface WarehouseStockRow {
  isbn: string
  korea: number | null
  korea_pk: number | null
  ca: number | null
  ca_pk: number | null
  nj: number | null
  nj_pk: number | null
}

export interface WarehouseStockUpsertPayload {
  isbn: string
  location: 'korea' | 'ca' | 'nj'
  quantity: number
}

export async function getWarehouseStock(): Promise<{ count: number; results: WarehouseStockRow[] }> {
  const res = await api.get('/api/warehouse/stock/')
  return res.data
}

export async function upsertWarehouseStock(data: WarehouseStockUpsertPayload): Promise<void> {
  await api.post('/api/warehouse/stock/upsert/', data)
}

export async function bulkUpsertWarehouseStock(items: WarehouseStockUpsertPayload[]): Promise<{ upserted_count: number }> {
  const res = await api.post('/api/warehouse/stock/bulk/', items)
  return res.data
}

export async function deleteWarehouseStockEntry(pk: number): Promise<void> {
  await api.delete(`/api/warehouse/stock/${pk}/`)
}
