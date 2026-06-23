import { useRef } from 'react'
import { Button } from '@/components/ui/button'
import { useDownloadDailyReview, useUploadDailyReview } from '@/hooks/usePurchaseOrderQueries'

export function DailyReviewTab() {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const downloadMutation = useDownloadDailyReview()
  const uploadMutation = useUploadDailyReview()

  const handleDownload = () => {
    downloadMutation.mutate()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
    <div className="space-y-6">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">Daily Order Review</h2>
        <p className="text-sm text-muted-foreground">
          미발주 항목을 엑셀로 다운받아 발주처를 선택한 후 업로드하면 발주가 확정됩니다.
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        {/* Step 1: Download */}
        <div className="flex-1 rounded-lg border p-4 space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">1단계 — 파일 다운로드</p>
            <p className="text-xs text-muted-foreground">
              현재 미발주 항목과 업체 단가/재고 정보가 포함된 엑셀 파일을 받습니다.
              <br />
              <span className="font-medium text-foreground">선택</span> 컬럼에 발주처(북센, 교보 등)를 입력하세요.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleDownload}
            disabled={downloadMutation.isPending}
          >
            {downloadMutation.isPending ? '생성 중...' : 'Excel 다운로드'}
          </Button>
        </div>

        {/* Step 2: Upload */}
        <div className="flex-1 rounded-lg border p-4 space-y-3">
          <div className="space-y-1">
            <p className="text-sm font-medium">2단계 — 수정 후 업로드</p>
            <p className="text-xs text-muted-foreground">
              선택 컬럼을 작성한 파일을 업로드합니다.
              <br />
              선택이 비어 있는 행은 건너뜁니다.
            </p>
          </div>
          <div className="flex gap-2 items-center">
            <Button
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? '처리 중...' : '파일 업로드'}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
          {uploadMutation.isSuccess && (
            <div className="text-xs text-muted-foreground">
              확정: {uploadMutation.data.confirmed_count}건 / 건너뜀: {uploadMutation.data.skipped_count}건
            </div>
          )}
        </div>
      </div>

      {/* Selection guide */}
      <div className="rounded-lg bg-muted/40 p-4 space-y-2">
        <p className="text-xs font-medium text-muted-foreground">선택 컬럼 입력 가능 값</p>
        <div className="flex flex-wrap gap-2">
          {['북센', '교보', '처음교육', '아가페', '성서유니온'].map((label) => (
            <span
              key={label}
              className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium"
            >
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
