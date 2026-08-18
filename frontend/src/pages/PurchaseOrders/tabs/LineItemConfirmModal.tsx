import { useState } from 'react'
import type { AxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useConfirmLineItem } from '@/hooks/usePurchaseOrderQueries'

// SPEC-ORDER-025 D2: the six pre-defined distributor dropdown values.
// warehouse_korea/ca/nj are deliberately excluded — see spec.md D2 and
// Exclusions 1 (this endpoint never touches WarehouseStock).
const DISTRIBUTOR_DROPDOWN_OPTIONS = [
  { value: 'booxen', label: '북센' },
  { value: 'kyobo', label: '교보' },
  { value: 'yes24', label: 'YES24' },
  { value: 'choeumgoyuk', label: '처음교육' },
  { value: 'agape', label: '아가페' },
  { value: 'sungseoyunion', label: '성서유니온' },
] as const

export interface LineItemConfirmTarget {
  id: number
  title: string
  sku: string
  quantity: number
}

interface LineItemConfirmModalProps {
  lineItem: LineItemConfirmTarget | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

// SPEC-ORDER-025 R2/M4: LineItem 단건 발주처리 모달.
//
// REQ-LCONF-103: the dropdown and the free-text input both write to the
// single `distributor` state below — whichever control the operator touched
// last is naturally the submitted value, with no separate precedence logic
// needed (plan.md 기술 접근).
// Reset the form whenever a different row is targeted: the parent renders
// this component with `key={lineItem.id}` (see UnorderedItemsTab.tsx), which
// remounts it with fresh useState instead of needing an effect to clear
// leftover input from a previous row's submission.
export function LineItemConfirmModal({ lineItem, open, onOpenChange }: LineItemConfirmModalProps) {
  const [distributor, setDistributor] = useState('')
  const [unitPrice, setUnitPrice] = useState('')
  // SPEC-ORDER-025 M2: prefilled with the row's current SKU so the operator
  // can correct it here (Shopify frequently still reports the old edition's
  // SKU when a book gets a new edition, but the operator is actually
  // purchasing the new one). Initialized directly from `lineItem.sku` — no
  // effect needed, since the parent remounts this component with
  // `key={lineItem.id}` for every row (see module docstring above).
  const [sku, setSku] = useState(lineItem?.sku ?? '')
  const confirmMutation = useConfirmLineItem()

  if (!lineItem) return null

  const handleClose = () => {
    onOpenChange(false)
  }

  const trimmedSku = sku.trim()
  // REQ-LCONF-SKU-002 precedent: a reverted-back-to-original value must also
  // count as "unchanged" so the payload stays byte-for-byte identical to the
  // pre-M2 shape, not just when the field was never touched at all.
  const skuChanged = trimmedSku !== '' && trimmedSku !== lineItem.sku

  const handleSubmit = () => {
    const trimmedDistributor = distributor.trim()
    if (!trimmedDistributor || trimmedSku === '') return
    confirmMutation.mutate(
      {
        id: lineItem.id,
        distributor: trimmedDistributor,
        unitPrice: unitPrice.trim() === '' ? null : unitPrice.trim(),
        // Send `sku` only when it actually differs from the row's current
        // value — an untouched (or reverted) field must produce a payload
        // with no `sku` key at all, reproducing today's behaviour exactly.
        ...(skuChanged ? { sku: trimmedSku } : {}),
      },
      {
        onSuccess: () => {
          setDistributor('')
          setUnitPrice('')
          setSku('')
          onOpenChange(false)
        },
      }
    )
  }

  // REQ-LCONF-105: on failure the modal stays open and shows the server's
  // own `error` message (not `detail` — <int:pk>/<segment>/ URL family
  // convention, OrderDetailPage.tsx's syncError pattern reused here).
  const errorMessage = confirmMutation.isError
    ? ((confirmMutation.error as AxiosError<{ error?: string }>).response?.data?.error ??
      '발주처리에 실패했습니다.')
    : null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>발주처리</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <dl className="text-sm space-y-1">
            <div className="flex gap-2">
              <dt className="text-muted-foreground w-16 shrink-0">도서명</dt>
              <dd>{lineItem.title}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-muted-foreground w-16 shrink-0">SKU</dt>
              <dd className="font-mono text-xs">{lineItem.sku}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-muted-foreground w-16 shrink-0">필요 수량</dt>
              <dd>{lineItem.quantity}</dd>
            </div>
          </dl>

          <div className="space-y-2">
            <Label htmlFor="lineitem-confirm-distributor-select">확정 발주처</Label>
            <select
              id="lineitem-confirm-distributor-select"
              value={distributor}
              onChange={(e) => setDistributor(e.target.value)}
              className="w-full h-10 rounded-md border border-input bg-white text-gray-900 px-3 text-sm"
            >
              <option value="">발주처 선택</option>
              {DISTRIBUTOR_DROPDOWN_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <Input
              type="text"
              value={distributor}
              onChange={(e) => setDistributor(e.target.value)}
              maxLength={20}
              placeholder="목록에 없으면 직접 입력 (최대 20자)"
              aria-label="확정 발주처 직접 입력"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="lineitem-confirm-sku">SKU 정정 (선택)</Label>
            <Input
              id="lineitem-confirm-sku"
              type="text"
              value={sku}
              onChange={(e) => setSku(e.target.value)}
              maxLength={255}
              placeholder="실제로 발주할 SKU가 다르면 여기서 정정"
            />
            {/* SPEC-ORDER-025 M2: this is a data-correcting action, not a
                display tweak — the SKU actually being purchased changes as
                soon as this differs from the row's original value. Reuses
                the codebase's existing amber warning-box vocabulary (see
                OutboundPage/UnmatchedForceSection.tsx and
                OrdersPage.tsx's `warn` badge) rather than inventing a new
                one. */}
            {skuChanged && (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-300 rounded px-2 py-1">
                SKU를 변경하면 실제로 발주하는 도서가 바뀝니다. 정정된 SKU(&quot;{trimmedSku}&quot;)로
                발주처리됩니다.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="lineitem-confirm-unit-price">확정 단가 (선택)</Label>
            <Input
              id="lineitem-confirm-unit-price"
              type="text"
              inputMode="decimal"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              placeholder="비워두면 미입력으로 저장"
            />
          </div>

          {errorMessage && (
            <p role="alert" className="text-sm text-destructive">
              {errorMessage}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose}>
            취소
          </Button>
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={distributor.trim() === '' || trimmedSku === '' || confirmMutation.isPending}
          >
            {confirmMutation.isPending ? '처리 중...' : '발주처리'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
