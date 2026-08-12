import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ResultSection } from '@/components/ResultSection'
import {
  useUploadVendorShipment,
  useUploadWarehouseReceipt,
} from '@/hooks/usePurchaseOrderQueries'
import {
  LOGISTICS_STATUS_OPTIONS,
  type UploadLogisticsResponse,
  type UploadWarehouseReceiptResponse,
  type WarehouseReceiptUnmatchedReason,
} from '@/services/purchaseOrderApi'

// REQ-LOGI-017: each backend `reason` code (unmatched category only —
// quantity_exceeded's reason is a fixed constant) gets its own Korean
// label, mirroring OutboundPage's UNMATCHED_REASON_LABELS. Record (not
// Partial) so adding a reason code to the union without a label here is a
// compile error rather than a raw snake_case string in the UI.
const WAREHOUSE_RECEIPT_REASON_LABELS: Record<WarehouseReceiptUnmatchedReason, string> = {
  order_not_found: '주문 없음',
  line_item_not_found: 'SKU 불일치',
  multiple_line_items: '동일 SKU 복수 품목',
  invalid_row: '행 형식 오류',
}

// REQ-LOGI-017: reuse the existing logistics_status Korean labels
// (LOGISTICS_STATUS_OPTIONS, SPEC-ORDER-011 REQ-LOGI-001) instead of
// defining a second status label map.
const LOGISTICS_STATUS_LABELS: Record<string, string> = Object.fromEntries(
  LOGISTICS_STATUS_OPTIONS.map((option) => [option.value, option.label])
)

// SPEC-ORDER-011 T11: two upload cards for the logistics_status pipeline
// (REQ-LOGI-003 vendor shipment confirmation, REQ-LOGI-005 warehouse
// receiving results), reusing DailyReviewTab.tsx's card layout pattern.
export function LogisticsStatusTab() {
  const vendorFileInputRef = useRef<HTMLInputElement>(null)
  const warehouseFileInputRef = useRef<HTMLInputElement>(null)

  const uploadVendorShipmentMutation = useUploadVendorShipment()
  const uploadWarehouseReceiptMutation = useUploadWarehouseReceipt()

  const [vendorResult, setVendorResult] = useState<UploadLogisticsResponse | null>(null)
  const [vendorError, setVendorError] = useState<string | null>(null)
  // REQ-LOGI-017: warehouse receipt result carries the per-row detail lists;
  // the vendor shipment card's response shape is unchanged (counts only).
  const [warehouseResult, setWarehouseResult] = useState<UploadWarehouseReceiptResponse | null>(
    null
  )
  const [warehouseError, setWarehouseError] = useState<string | null>(null)

  const handleVendorFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    setVendorResult(null)
    setVendorError(null)
    uploadVendorShipmentMutation.mutate(formData, {
      onSuccess: (data: UploadLogisticsResponse) => setVendorResult(data),
      onError: () => setVendorError('벤더 출고확인 파일 업로드에 실패했습니다.'),
      onSettled: () => {
        if (vendorFileInputRef.current) vendorFileInputRef.current.value = ''
      },
    })
  }

  const handleWarehouseFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    setWarehouseResult(null)
    setWarehouseError(null)
    uploadWarehouseReceiptMutation.mutate(formData, {
      onSuccess: (data: UploadWarehouseReceiptResponse) => setWarehouseResult(data),
      onError: () => setWarehouseError('창고 입고결과 파일 업로드에 실패했습니다.'),
      onSettled: () => {
        if (warehouseFileInputRef.current) warehouseFileInputRef.current.value = ''
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">입고/출고 물류 상태 관리</h2>
        <p className="text-sm text-muted-foreground">
          벤더 출고확인 및 창고 입고결과 파일을 업로드하면 대상 SKU의 물류 상태가 자동으로 갱신됩니다.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        {/* Card 1: 벤더 출고확인 (REQ-LOGI-003) */}
        <div className="flex-1 rounded-lg border p-4 space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">벤더 출고확인 업로드</p>
            <p className="text-xs text-muted-foreground">
              벤더가 실제로 출고했음을 확인하는 파일을 업로드합니다.
              <br />
              대상 SKU는 <span className="font-medium text-foreground">미입고 → 입고예정</span>으로 전환됩니다.
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              size="sm"
              onClick={() => vendorFileInputRef.current?.click()}
              disabled={uploadVendorShipmentMutation.isPending}
            >
              {uploadVendorShipmentMutation.isPending ? '처리 중...' : '파일 업로드'}
            </Button>
            <input
              ref={vendorFileInputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleVendorFileChange}
            />
          </div>
          {vendorResult && (
            <div className="text-xs text-muted-foreground">
              매칭: {vendorResult.matched_count}건 / 건너뜀: {vendorResult.skipped_count}건
            </div>
          )}
          {vendorError && <div className="text-xs text-destructive">{vendorError}</div>}
        </div>

        {/* Card 2: 창고 입고결과 (REQ-LOGI-005) */}
        <div className="flex-1 rounded-lg border p-4 space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">창고 입고결과 업로드</p>
            <p className="text-xs text-muted-foreground">
              미국창고에 실물이 도착했음을 확인하는 파일을 업로드합니다.
              <br />
              대상 SKU는 <span className="font-medium text-foreground">미입고/입고예정 → 입고</span>로 전환됩니다.
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              size="sm"
              onClick={() => warehouseFileInputRef.current?.click()}
              disabled={uploadWarehouseReceiptMutation.isPending}
            >
              {uploadWarehouseReceiptMutation.isPending ? '처리 중...' : '파일 업로드'}
            </Button>
            <input
              ref={warehouseFileInputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleWarehouseFileChange}
            />
          </div>
          {warehouseResult && (
            <div className="text-xs text-muted-foreground">
              매칭: {warehouseResult.matched_count}건 / 건너뜀: {warehouseResult.skipped_count}건
            </div>
          )}
          {warehouseError && <div className="text-xs text-destructive">{warehouseError}</div>}

          {/* REQ-LOGI-017: all three categories render together, each with
              its own count, so an empty category is visibly empty rather
              than absent — mirrors OutboundPage's result rendering. */}
          {warehouseResult && (
            <div className="space-y-3">
              <ResultSection
                testId="warehouse-matched"
                title="성공"
                count={warehouseResult.matched_count}
                toneClassName="border-green-300 bg-green-50"
                columns={['주문번호', 'SKU', '이번 입고', '누적/주문 수량', '상태']}
                rows={warehouseResult.matched.map((item) => ({
                  key: `${item.line_item_id}`,
                  cells: [
                    item.name,
                    item.sku,
                    String(item.received_count),
                    `${item.received_quantity} / ${item.quantity ?? 0}`,
                    LOGISTICS_STATUS_LABELS[item.logistics_status] ?? item.logistics_status,
                  ],
                }))}
              />

              <ResultSection
                testId="warehouse-unmatched"
                title="매칭 실패"
                count={warehouseResult.unmatched_count}
                toneClassName="border-amber-300 bg-amber-50"
                columns={['주문번호', 'SKU', '행 수', '사유']}
                rows={warehouseResult.unmatched.map((item, index) => ({
                  key: `${item.name}-${item.sku}-${index}`,
                  cells: [
                    item.name,
                    item.sku,
                    String(item.received_count),
                    WAREHOUSE_RECEIPT_REASON_LABELS[item.reason] ?? item.reason,
                  ],
                }))}
              />

              <ResultSection
                testId="warehouse-quantity-exceeded"
                title="수량초과"
                count={warehouseResult.quantity_exceeded_count}
                toneClassName="border-red-300 bg-red-50"
                columns={['주문번호', 'SKU', '행 수', '누적/주문 수량']}
                rows={warehouseResult.quantity_exceeded.map((item) => ({
                  key: `${item.line_item_id}`,
                  cells: [
                    item.name,
                    item.sku,
                    String(item.received_count),
                    `${item.received_quantity} / ${item.quantity ?? 0}`,
                  ],
                }))}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
