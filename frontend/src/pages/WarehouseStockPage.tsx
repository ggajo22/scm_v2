import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  useBulkUpsertWarehouseStock,
  useDeleteWarehouseStock,
  useUpsertWarehouseStock,
  useWarehouseStock,
} from '@/hooks/useWarehouseQueries'
import type { WarehouseStockUpsertPayload } from '@/services/warehouseApi'

const LOCATION_LABELS: Record<string, string> = {
  korea: '한국',
  ca: 'CA',
  nj: 'NJ',
}

interface AddModalState {
  isbn: string
  location: 'korea' | 'ca' | 'nj'
  quantity: string
}

const EMPTY_FORM: AddModalState = { isbn: '', location: 'korea', quantity: '' }

// Bulk input textarea format: each line = "ISBN 위치 수량" (e.g. "9788901234567 korea 10")
function parseBulkText(text: string): WarehouseStockUpsertPayload[] {
  const validLocations = new Set(['korea', 'ca', 'nj'])
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .flatMap((line) => {
      const parts = line.split(/\s+/)
      if (parts.length < 3) return []
      const [isbn, location, rawQty] = parts
      const quantity = parseInt(rawQty, 10)
      if (!isbn || !validLocations.has(location) || isNaN(quantity)) return []
      return [{ isbn, location: location as 'korea' | 'ca' | 'nj', quantity }]
    })
}

export function WarehouseStockPage() {
  const { data, isLoading } = useWarehouseStock()
  const upsert = useUpsertWarehouseStock()
  const bulkUpsert = useBulkUpsertWarehouseStock()
  const deleteEntry = useDeleteWarehouseStock()

  const [showAddModal, setShowAddModal] = useState(false)
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [form, setForm] = useState<AddModalState>(EMPTY_FORM)
  const [bulkText, setBulkText] = useState('')
  const [search, setSearch] = useState('')

  const rows = data?.results ?? []
  const filtered = search
    ? rows.filter((r) => r.isbn.includes(search.trim()))
    : rows

  function handleAddSubmit(e: React.FormEvent) {
    e.preventDefault()
    const quantity = parseInt(form.quantity, 10)
    if (!form.isbn || isNaN(quantity)) return
    upsert.mutate(
      { isbn: form.isbn.trim(), location: form.location, quantity },
      {
        onSuccess: () => {
          setShowAddModal(false)
          setForm(EMPTY_FORM)
        },
      }
    )
  }

  function handleBulkSubmit(e: React.FormEvent) {
    e.preventDefault()
    const items = parseBulkText(bulkText)
    if (!items.length) return
    bulkUpsert.mutate(items, {
      onSuccess: () => {
        setShowBulkModal(false)
        setBulkText('')
      },
    })
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">창고 재고</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowBulkModal(true)}>
            일괄 등록
          </Button>
          <Button onClick={() => setShowAddModal(true)}>재고 추가</Button>
        </div>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="ISBN 검색"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      {isLoading ? (
        <p className="text-muted-foreground text-sm">불러오는 중...</p>
      ) : (
        <div className="rounded-md border overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left font-medium">ISBN</th>
                <th className="px-4 py-3 text-center font-medium">한국</th>
                <th className="px-4 py-3 text-center font-medium">CA</th>
                <th className="px-4 py-3 text-center font-medium">NJ</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-muted-foreground">
                    {search ? '검색 결과가 없습니다.' : '등록된 재고가 없습니다.'}
                  </td>
                </tr>
              ) : (
                filtered.map((row) => (
                  <tr key={row.isbn} className="border-b hover:bg-muted/30">
                    <td className="px-4 py-3 font-mono">{row.isbn}</td>
                    {(['korea', 'ca', 'nj'] as const).map((loc) => {
                      const qty = row[loc]
                      const pk = row[`${loc}_pk` as keyof typeof row] as number | null
                      return (
                        <td key={loc} className="px-4 py-3 text-center">
                          {qty !== null ? (
                            <span className="inline-flex items-center gap-2">
                              <span>{qty}</span>
                              <button
                                type="button"
                                onClick={() => pk !== null && deleteEntry.mutate(pk)}
                                className="text-muted-foreground hover:text-destructive transition-colors"
                                aria-label={`${LOCATION_LABELS[loc]} 재고 삭제`}
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </span>
                          ) : (
                            <span className="text-muted-foreground">-</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Add single entry modal */}
      {showAddModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowAddModal(false)}
        >
          <div
            className="bg-background rounded-lg border shadow-lg w-full max-w-sm p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold">재고 추가</h2>
            <form onSubmit={handleAddSubmit} className="space-y-3">
              <div className="space-y-1">
                <label className="text-sm font-medium">ISBN</label>
                <Input
                  placeholder="9788901234567"
                  value={form.isbn}
                  onChange={(e) => setForm((f) => ({ ...f, isbn: e.target.value }))}
                  autoFocus
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">위치</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={form.location}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, location: e.target.value as 'korea' | 'ca' | 'nj' }))
                  }
                >
                  <option value="korea">한국</option>
                  <option value="ca">CA</option>
                  <option value="nj">NJ</option>
                </select>
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">수량</label>
                <Input
                  type="number"
                  min="0"
                  placeholder="0"
                  value={form.quantity}
                  onChange={(e) => setForm((f) => ({ ...f, quantity: e.target.value }))}
                />
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <Button type="button" variant="outline" onClick={() => setShowAddModal(false)}>
                  취소
                </Button>
                <Button type="submit" disabled={upsert.isPending}>
                  {upsert.isPending ? '저장 중...' : '저장'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk upsert modal */}
      {showBulkModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowBulkModal(false)}
        >
          <div
            className="bg-background rounded-lg border shadow-lg w-full max-w-lg p-6 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold">일괄 등록</h2>
            <p className="text-sm text-muted-foreground">
              한 줄에 하나씩 입력하세요: <code className="bg-muted px-1 rounded">ISBN 위치 수량</code>
              <br />
              위치: <code className="bg-muted px-1 rounded">korea</code> /&nbsp;
              <code className="bg-muted px-1 rounded">ca</code> /&nbsp;
              <code className="bg-muted px-1 rounded">nj</code>
            </p>
            <form onSubmit={handleBulkSubmit} className="space-y-3">
              <textarea
                className="w-full rounded-md border bg-background px-3 py-2 text-sm font-mono min-h-40 resize-y"
                placeholder={"9788901234567 korea 10\n9788901234568 ca 5\n9788901234568 nj 3"}
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                autoFocus
              />
              <div className="flex gap-2 justify-end pt-2">
                <Button type="button" variant="outline" onClick={() => setShowBulkModal(false)}>
                  취소
                </Button>
                <Button
                  type="submit"
                  disabled={bulkUpsert.isPending || !bulkText.trim()}
                >
                  {bulkUpsert.isPending ? '등록 중...' : '일괄 등록'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
