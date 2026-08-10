import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { useOrders } from '@/features/order/hooks/useOrders'
import { useOrderDetail } from '@/features/order/hooks/useOrderDetail'
import {
  useUpdateLineItemRackNumber,
  useBulkUpdateLineItemRackNumber,
  useUploadRackNumber,
} from '@/hooks/useRackNumberQueries'
import type { LineItemDetail } from '@/types/order'

// BUGFIX: normalizes an order search term for name matching — case-insensitive,
// tolerant of an optional leading '#' on either side (Order.name is stored as
// "#EB10011778"; users may type "EB10011778", "eb10011778", or "#EB10011778").
function normalizeOrderSearch(value: string): string {
  return value.trim().replace(/^#/, '').toUpperCase()
}

// SPEC-ORDER-013: independent rack_number management page (REQ-RACK-008).
// Search-only flow scoped to a single Order — selection state is local
// (결정 F), never the global usePurchaseOrderStore.
// SPEC-ORDER-014 TASK-002: extracted verbatim from the former flat
// RackNumberPage.tsx into the "주문 검색" tab of the new tab shell
// (RackNumberPage/index.tsx) — no logic, styling, or behavior changed.
export function SearchTab() {
  const [searchInput, setSearchInput] = useState('')
  const [submittedSearch, setSubmittedSearch] = useState<string | null>(null)
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [bulkValue, setBulkValue] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 결정 C: reuse GET /api/orders/?search= (which also OR-matches on name),
  // then filter client-side to an exact order_number OR order name match.
  // BUGFIX: manually-entered orders can have a name (e.g. "#EB10011778")
  // that does not numerically correlate with order_number (e.g. 1778) — an
  // order_number-only filter silently discarded these backend hits.
  const { data: searchResults, isFetching: isSearching } = useOrders(
    { search: submittedSearch ?? '' },
    { enabled: submittedSearch !== null }
  )

  const matchedOrder = searchResults?.results.find((o) => {
    if (String(o.order_number) === submittedSearch) return true
    if (submittedSearch === null || o.name == null) return false
    return normalizeOrderSearch(o.name) === normalizeOrderSearch(submittedSearch)
  })

  const { data: orderDetail } = useOrderDetail(matchedOrder?.id ?? 0, {
    enabled: matchedOrder !== undefined,
  })

  const updateMutation = useUpdateLineItemRackNumber()
  const bulkMutation = useBulkUpdateLineItemRackNumber()
  const uploadMutation = useUploadRackNumber()

  const lineItems = orderDetail?.line_items ?? []
  const allSelected = lineItems.length > 0 && lineItems.every((li) => selectedIds.includes(li.id))
  const notFound = submittedSearch !== null && !isSearching && !matchedOrder

  const handleSearch = () => {
    const trimmed = searchInput.trim()
    if (!trimmed) return
    setSubmittedSearch(trimmed)
    setSelectedIds([]) // AC-RACK-010c: reset selection on every fresh search
    setBulkValue('')
  }

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const handleSelectAll = () => {
    setSelectedIds(allSelected ? [] : lineItems.map((li) => li.id))
  }

  const handleBulkApply = () => {
    if (selectedIds.length === 0) return
    bulkMutation.mutate(
      { ids: selectedIds, rackNumber: bulkValue },
      {
        onSuccess: () => {
          setSelectedIds([])
          setBulkValue('')
        },
      }
    )
  }

  const handleInlineCommit = (id: number, value: string) => {
    updateMutation.mutate({ id, rackNumber: value })
  }

  const handleUploadChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    uploadMutation.mutate(formData, {
      onSettled: () => {
        if (fileInputRef.current) fileInputRef.current.value = ''
      },
    })
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="space-y-1">
        <h1 className="text-lg font-semibold">렉번호 관리</h1>
        <p className="text-sm text-muted-foreground">
          주문번호로 검색해 해당 주문 품목의 렉번호를 개별 또는 일괄로 기록합니다.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSearch()
          }}
          placeholder="주문번호 입력"
          aria-label="주문번호 검색"
          className="border rounded px-2 py-1 text-sm"
        />
        <Button size="sm" onClick={handleSearch}>
          검색
        </Button>

        <div className="ml-auto flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadMutation.isPending}
          >
            {uploadMutation.isPending ? '업로드 중...' : 'Excel 업로드'}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            className="hidden"
            onChange={handleUploadChange}
          />
        </div>
      </div>

      {notFound && (
        <p className="text-sm text-muted-foreground">일치하는 주문을 찾을 수 없습니다.</p>
      )}

      {matchedOrder && orderDetail && (
        <>
          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2">
              <input
                type="text"
                maxLength={10}
                value={bulkValue}
                onChange={(e) => setBulkValue(e.target.value)}
                placeholder="렉번호 값"
                aria-label="일괄 적용할 렉번호"
                className="border rounded px-2 py-1 text-sm"
              />
              <Button size="sm" onClick={handleBulkApply} disabled={bulkMutation.isPending}>
                일괄 적용
              </Button>
            </div>
          )}

          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-2 px-3 text-left w-10">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={handleSelectAll}
                      aria-label="전체 선택"
                      className="cursor-pointer"
                    />
                  </th>
                  <th className="py-2 px-3 text-left font-medium">SKU</th>
                  <th className="py-2 px-3 text-left font-medium">도서명</th>
                  <th className="py-2 px-3 text-left font-medium">렉번호</th>
                </tr>
              </thead>
              <tbody>
                {lineItems.map((item) => (
                  <RackNumberRow
                    key={item.id}
                    item={item}
                    checked={selectedIds.includes(item.id)}
                    onToggle={() => toggleSelect(item.id)}
                    onCommit={(value) => handleInlineCommit(item.id, value)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

// REQ-RACK-011: isolated local input state per row so an in-progress edit on
// one row is never disturbed by re-renders triggered by other rows/selection.
function RackNumberRow({
  item,
  checked,
  onToggle,
  onCommit,
}: {
  item: LineItemDetail
  checked: boolean
  onToggle: () => void
  onCommit: (value: string) => void
}) {
  const [value, setValue] = useState(item.rack_number)
  // Tracks the last value actually submitted, independent of the
  // (possibly-stale, pre-invalidation) `item.rack_number` prop — prevents a
  // duplicate PATCH when Enter triggers both commit() and a native blur.
  const lastCommittedRef = useRef(item.rack_number)

  useEffect(() => {
    setValue(item.rack_number)
    lastCommittedRef.current = item.rack_number
  }, [item.rack_number])

  const commit = () => {
    if (value !== lastCommittedRef.current) {
      lastCommittedRef.current = value
      onCommit(value)
    }
  }

  return (
    <tr className="border-b last:border-0 hover:bg-muted/30">
      <td className="py-2 px-3">
        <input
          type="checkbox"
          checked={checked}
          onChange={onToggle}
          aria-label={`${item.sku ?? item.title} 선택`}
          className="cursor-pointer"
        />
      </td>
      <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
      <td className="py-2 px-3 max-w-xs truncate" title={item.title ?? undefined}>
        {item.title}
      </td>
      <td className="py-2 px-3">
        <input
          type="text"
          maxLength={10}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              commit()
              e.currentTarget.blur()
            }
          }}
          aria-label={`${item.sku ?? item.title} 렉번호`}
          className="border rounded px-2 py-1 text-sm w-24"
        />
      </td>
    </tr>
  )
}
