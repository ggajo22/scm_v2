import { useState, useRef } from 'react'
import { Upload } from 'lucide-react'
import { useUploadVendorFile } from '@/hooks/usePurchaseOrderQueries'

const DISTRIBUTOR_OPTIONS = ['북센', '교보'] as const
type Distributor = (typeof DISTRIBUTOR_OPTIONS)[number]

const DISTRIBUTOR_API_KEY: Record<Distributor, string> = {
  '북센': 'booxen',
  '교보': 'kyobo',
}

export function VendorFileUploadTab() {
  const [distributor, setDistributor] = useState<Distributor>('북센')
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedCounts, setUploadedCounts] = useState<Partial<Record<Distributor, number>>>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  const uploadMutation = useUploadVendorFile()

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

      <p className="text-xs text-muted-foreground">
        북센·교보 파일 업로드 후 Daily Review 탭에서 발주처를 확인하고 확정하세요.
      </p>
    </div>
  )
}
