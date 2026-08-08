import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  useUploadVendorShipment,
  useUploadWarehouseReceipt,
} from '@/hooks/usePurchaseOrderQueries'
import type { UploadLogisticsResponse } from '@/services/purchaseOrderApi'

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
  const [warehouseResult, setWarehouseResult] = useState<UploadLogisticsResponse | null>(null)
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
      onSuccess: (data: UploadLogisticsResponse) => setWarehouseResult(data),
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
        </div>
      </div>
    </div>
  )
}
