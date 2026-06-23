import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useUploadVendorFile, useRunComparison } from '@/hooks/usePurchaseOrderQueries'
import { usePurchaseOrderStore } from '@/stores/usePurchaseOrderStore'
import type { ComparisonResult, ConfirmItem } from '@/services/purchaseOrderApi'

const DISTRIBUTOR_OPTIONS = ['북센', '교보'] as const
type Distributor = (typeof DISTRIBUTOR_OPTIONS)[number]

const DISTRIBUTOR_API_KEY: Record<Distributor, string> = {
  '북센': 'bookseen',
  '교보': 'kyobo',
}

const DISTRIBUTOR_LABEL: Record<string, string> = {
  bookseen: '북센',
  kyobo: '교보',
  warehouse: '재고',
  warehouse_west: '재고(서부)',
  choeumgoyuk: '처음교육',
  agape: '아가페',
  check_required: '확인필요',
}

export function VendorFileUploadTab() {
  const [distributor, setDistributor] = useState<Distributor>('북센')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedCounts, setUploadedCounts] = useState<Partial<Record<Distributor, number>>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadMutation = useUploadVendorFile()
  const runComparisonMutation = useRunComparison()
  const setConfirmItems = usePurchaseOrderStore((s) => s.setConfirmItems)

  const handleFile = (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('distributor', DISTRIBUTOR_API_KEY[distributor])
    uploadMutation.mutate(formData, {
      onSuccess: (data) => {
        setUploadedCounts((prev) => ({ ...prev, [distributor]: data.parsed_count }))
      },
    })
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handlePrepareConfirm = (results: ComparisonResult[]) => {
    const items: ConfirmItem[] = results
      .filter((item) => item.selected_distributor !== null)
      .map((item) => ({
        sku: item.sku,
        distributor: item.selected_distributor!,
        quantity: item.total_qty,
        unit_price:
          item.selected_distributor === 'bookseen' ? item.bookseen_price : item.kyobo_price,
      }))
    setConfirmItems(items)
  }

  const comparisonResults = runComparisonMutation.data?.results ?? null

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

      {/* Upload status — per-distributor counts */}
      {Object.keys(uploadedCounts).length > 0 && (
        <div className="flex items-center gap-4 text-sm">
          {DISTRIBUTOR_OPTIONS.map((d) =>
            uploadedCounts[d] !== undefined ? (
              <span key={d} className="text-green-600">
                {d} {uploadedCounts[d]}건
              </span>
            ) : (
              <span key={d} className="text-muted-foreground">
                {d} 미업로드
              </span>
            )
          )}
        </div>
      )}

      {/* Run comparison button */}
      <div className="flex items-center gap-3">
        <Button
          onClick={() => runComparisonMutation.mutate()}
          disabled={runComparisonMutation.isPending}
          variant="outline"
        >
          {runComparisonMutation.isPending ? '비교 중...' : '비교 실행'}
        </Button>
        <span className="text-xs text-muted-foreground">
          북센·교보 업로드 후 실행하면 미발주 항목과 매칭합니다
        </span>
      </div>

      {/* Comparison results matched with unordered LineItems */}
      {comparisonResults && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">
              비교 결과 ({comparisonResults.length}개 SKU)
            </h3>
            {comparisonResults.length > 0 && (
              <Button size="sm" variant="outline" onClick={() => handlePrepareConfirm(comparisonResults)}>
                발주 확정 탭으로 이동
              </Button>
            )}
          </div>

          {comparisonResults.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              미발주 항목이 없습니다.
            </p>
          ) : (
            <div className="overflow-x-auto rounded border">
              <table className="w-full text-sm border-collapse">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="py-2 px-3 text-left font-medium">SKU</th>
                    <th className="py-2 px-3 text-left font-medium">도서명</th>
                    <th className="py-2 px-3 text-center font-medium">주문 수량</th>
                    <th className="py-2 px-3 text-left font-medium">주문 목록</th>
                    <th className="py-2 px-3 text-center font-medium">북센 재고</th>
                    <th className="py-2 px-3 text-right font-medium">북센 단가</th>
                    <th className="py-2 px-3 text-center font-medium">교보 재고</th>
                    <th className="py-2 px-3 text-right font-medium">교보 단가</th>
                    <th className="py-2 px-3 text-left font-medium">선택</th>
                    <th className="py-2 px-3 text-right font-medium">확정 단가</th>
                    <th className="py-2 px-3 text-left font-medium">근거</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonResults.map((item) => (
                    <tr key={item.sku} className="border-b last:border-0 hover:bg-muted/30">
                      <td className="py-2 px-3 font-mono text-xs">{item.sku}</td>
                      <td className="py-2 px-3 max-w-[160px] truncate" title={item.title}>
                        {item.title}
                      </td>
                      <td className="py-2 px-3 text-center font-medium">{item.total_qty}</td>
                      <td className="py-2 px-3">
                        <div className="flex flex-col gap-0.5">
                          {item.line_items.map((li) => (
                            <span key={li.id} className="text-xs text-muted-foreground">
                              {li.order_name ?? `#${li.id}`} ×{li.quantity}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-center">
                        {item.bookseen_available === null ? (
                          <span className="text-muted-foreground text-xs">-</span>
                        ) : item.bookseen_available ? (
                          <span className="text-green-600 text-xs">{item.bookseen_stock ?? '?'}권</span>
                        ) : (
                          <span className="text-red-500 text-xs">없음</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right">
                        {item.bookseen_price
                          ? Number(item.bookseen_price).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-2 px-3 text-center">
                        {item.kyobo_available === null ? (
                          <span className="text-muted-foreground text-xs">-</span>
                        ) : item.kyobo_available ? (
                          <span className="text-green-600 text-xs">{item.kyobo_stock ?? '?'}권</span>
                        ) : (
                          <span className="text-red-500 text-xs">없음</span>
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
                            {DISTRIBUTOR_LABEL[item.selected_distributor] ?? item.selected_distributor}
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs">미정</span>
                        )}
                      </td>
                      <td className="py-2 px-3 text-right font-medium">
                        {item.confirmed_price
                          ? Number(item.confirmed_price).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-2 px-3 text-xs text-muted-foreground">
                        {item.candidate_basis ?? '-'}
                        {item.price_diff_alert && (
                          <span className="ml-1 text-orange-500">⚠</span>
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
