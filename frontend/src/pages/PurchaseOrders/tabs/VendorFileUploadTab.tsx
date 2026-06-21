import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useUploadVendorFile, useComparison } from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'
import type { ConfirmItem } from '@/services/purchaseOrderApi'

const DISTRIBUTOR_OPTIONS = ['북센', '교보'] as const
type Distributor = (typeof DISTRIBUTOR_OPTIONS)[number]

export function VendorFileUploadTab() {
  const [distributor, setDistributor] = useState<Distributor>('북센')
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadMutation = useUploadVendorFile()
  const { data: comparison, isFetching } = useComparison()
  const setConfirmItems = usePurchaseOrderStore((s) => s.setConfirmItems)

  const handleFile = (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('distributor', distributor)
    uploadMutation.mutate(formData)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    // Reset input so the same file can be re-uploaded
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  // Build confirm items from comparison results for the selected distributor
  const handlePrepareConfirm = () => {
    if (!comparison) return
    const items: ConfirmItem[] = comparison.results
      .filter((item) => item.selected_distributor === distributor)
      .map((item) => ({
        sku: item.sku,
        distributor,
        quantity: 1, // Default quantity; user adjusts in ConfirmOrderTab
        unit_price:
          distributor === '북센' ? item.bookseen_price : item.kyobo_price,
      }))
    setConfirmItems(items)
  }

  return (
    <div className="space-y-6">
      {/* Distributor selector */}
      <div className="flex items-center gap-3">
        <label className="text-sm font-medium" htmlFor="distributor-select">
          발주처
        </label>
        <select
          id="distributor-select"
          value={distributor}
          onChange={(e) => setDistributor(e.target.value as Distributor)}
          className="border rounded px-2 py-1 text-sm"
          aria-label="발주처 선택"
        >
          {DISTRIBUTOR_OPTIONS.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
      </div>

      {/* Drag and drop upload area */}
      <div
        role="button"
        tabIndex={0}
        aria-label="파일 업로드 영역 (클릭하거나 파일을 드래그하세요)"
        className={`border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors ${
          isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:border-primary/50'
        }`}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto h-8 w-8 text-muted-foreground mb-2" aria-hidden="true" />
        <p className="text-sm text-muted-foreground">
          {uploadMutation.isPending
            ? '업로드 중...'
            : '파일을 드래그하거나 클릭하여 선택하세요'}
        </p>
        <p className="text-xs text-muted-foreground/70 mt-1">지원 형식: .xlsx, .xls</p>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFileInput}
          className="hidden"
          aria-hidden="true"
        />
      </div>

      {/* Comparison table */}
      {(comparison || isFetching) && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">재고 비교 결과</h3>
            {comparison && comparison.results.length > 0 && (
              <Button size="sm" variant="outline" onClick={handlePrepareConfirm}>
                발주 확정 탭으로 이동
              </Button>
            )}
          </div>

          {isFetching && (
            <div role="status" aria-label="로딩 중" className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-10 bg-muted animate-pulse rounded" />
              ))}
            </div>
          )}

          {comparison && !isFetching && (
            <div className="overflow-x-auto rounded border">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-2 px-3 text-left font-medium">SKU</th>
                    <th className="py-2 px-3 text-left font-medium">도서명</th>
                    <th className="py-2 px-3 text-center font-medium">북센 재고</th>
                    <th className="py-2 px-3 text-right font-medium">북센 단가</th>
                    <th className="py-2 px-3 text-center font-medium">교보 재고</th>
                    <th className="py-2 px-3 text-right font-medium">교보 단가</th>
                    <th className="py-2 px-3 text-left font-medium">자동선택</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.results.length === 0 && (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-muted-foreground">
                        비교 데이터가 없습니다.
                      </td>
                    </tr>
                  )}
                  {comparison.results.map((item) => (
                    <tr key={item.sku} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                      <td className="py-2 px-3 max-w-xs truncate" title={item.title}>
                        {item.title}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {item.bookseen_available === null ? (
                          '-'
                        ) : item.bookseen_available ? (
                          <span className="text-green-600 text-xs">재고있음</span>
                        ) : (
                          <span className="text-red-500 text-xs">재고없음</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {item.bookseen_price
                          ? Number(item.bookseen_price).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {item.kyobo_available === null ? (
                          '-'
                        ) : item.kyobo_available ? (
                          <span className="text-green-600 text-xs">재고있음</span>
                        ) : (
                          <span className="text-red-500 text-xs">재고없음</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {item.kyobo_price
                          ? Number(item.kyobo_price).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-2 px-3">
                        {item.selected_distributor ? (
                          <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                            {item.selected_distributor}
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
