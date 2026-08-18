import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LineItemConfirmModal } from './LineItemConfirmModal'
import { useConfirmLineItem } from '@/hooks/usePurchaseOrderQueries'

vi.mock('@/hooks/usePurchaseOrderQueries', () => ({
  useConfirmLineItem: vi.fn(),
}))

const SAMPLE_LINE_ITEM = {
  id: 42,
  title: '테스트도서',
  sku: 'ISBN-A',
  quantity: 5,
}

describe('LineItemConfirmModal (SPEC-ORDER-025 R2)', () => {
  const mutate = vi.fn()
  const onOpenChange = vi.fn()

  beforeEach(() => {
    mutate.mockClear()
    onOpenChange.mockClear()
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate,
      isPending: false,
      isError: false,
      error: null,
    } as unknown as ReturnType<typeof useConfirmLineItem>)
  })

  it('renders nothing when lineItem is null, even if open=true', () => {
    render(<LineItemConfirmModal lineItem={null} open={true} onOpenChange={onOpenChange} />)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  // AC-LCONF-101/108: title/SKU/quantity shown as-is — the quantity passed
  // in is already the net quantity the unordered row displayed (REQ-LCONF-108;
  // UnorderedItemsTab passes item.quantity straight through, no recompute
  // needed on the frontend since the backend already nets it).
  it('AC-LCONF-101/108: shows the line item title, SKU, and quantity', () => {
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByText('테스트도서')).toBeInTheDocument()
    expect(dialog.getByText('ISBN-A')).toBeInTheDocument()
    expect(dialog.getByText('5')).toBeInTheDocument()
  })

  // AC-LCONF-106: submit stays disabled until distributor is non-blank.
  it('AC-LCONF-106: submit is disabled while distributor is blank, enabled once set', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))
    const submitButton = dialog.getByRole('button', { name: '발주처리' })
    expect(submitButton).toBeDisabled()

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    expect(submitButton).toBeEnabled()
  })

  // AC-LCONF-102/103: shared distributor state — last-touched control wins.
  it('AC-LCONF-102/103: dropdown then free-text edit submits the free-text value', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '교보')
    const freeText = dialog.getByLabelText('확정 발주처 직접 입력')
    expect(freeText).toHaveValue('kyobo')

    await user.clear(freeText)
    await user.type(freeText, '특수출판사')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(mutate).toHaveBeenCalledTimes(1)
    const [payload] = mutate.mock.calls[0] as [
      { id: number; distributor: string; unitPrice: string | null },
    ]
    expect(payload).toEqual({ id: 42, distributor: '특수출판사', unitPrice: null })
  })

  it('sends unitPrice when provided, and null when left blank', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    await user.type(dialog.getByLabelText('확정 단가 (선택)'), '12000')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    const [payload] = mutate.mock.calls[0] as [
      { id: number; distributor: string; unitPrice: string | null },
    ]
    expect(payload.unitPrice).toBe('12000')
  })

  // AC-LCONF-105: server error message rendered inline; modal does not
  // close itself on error (no onOpenChange(false) call from this path).
  it('AC-LCONF-105: renders the server error message and does not call onOpenChange', () => {
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate,
      isPending: false,
      isError: true,
      error: {
        response: { status: 409, data: { error: '이미 발주서에 연결되어 있습니다.' } },
      },
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )

    expect(screen.getByRole('alert')).toHaveTextContent('이미 발주서에 연결되어 있습니다.')
    expect(onOpenChange).not.toHaveBeenCalled()
  })

  it('falls back to a generic message when the error response has no `error` key', () => {
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate,
      isPending: false,
      isError: true,
      error: { response: { status: 500, data: {} } },
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )

    expect(screen.getByRole('alert')).toHaveTextContent('발주처리에 실패했습니다.')
  })

  // AC-LCONF-104: successful submission closes the modal.
  it('AC-LCONF-104: on success, calls onOpenChange(false)', async () => {
    mutate.mockImplementation((_payload, opts?: { onSuccess?: () => void }) => {
      opts?.onSuccess?.()
    })
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('clicking 취소 closes the modal without submitting', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.click(dialog.getByRole('button', { name: '취소' }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(mutate).not.toHaveBeenCalled()
  })

  // -------------------------------------------------------------------------
  // SPEC-ORDER-025 M2 — SKU correction at confirm time
  // -------------------------------------------------------------------------

  it('AC-LCONF-SKU: the SKU field is prefilled with the row current SKU', () => {
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))
    expect(dialog.getByLabelText('SKU 정정 (선택)')).toHaveValue(SAMPLE_LINE_ITEM.sku)
  })

  it('AC-LCONF-SKU: an untouched SKU field submits a payload with no `sku` key', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(mutate).toHaveBeenCalledTimes(1)
    const [payload] = mutate.mock.calls[0] as [Record<string, unknown>]
    expect('sku' in payload).toBe(false)
  })

  it('AC-LCONF-SKU: an edited SKU field submits the new value', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    const skuInput = dialog.getByLabelText('SKU 정정 (선택)')
    await user.clear(skuInput)
    await user.type(skuInput, 'ISBN-NEW-EDITION')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    expect(mutate).toHaveBeenCalledTimes(1)
    const [payload] = mutate.mock.calls[0] as [{ sku?: string }]
    expect(payload.sku).toBe('ISBN-NEW-EDITION')
  })

  it('AC-LCONF-SKU: shows a warning once the SKU field is edited to a different value', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))
    const skuInput = dialog.getByLabelText('SKU 정정 (선택)')

    expect(dialog.queryByText(/실제로 발주하는 도서가 바뀝니다/)).not.toBeInTheDocument()

    await user.clear(skuInput)
    await user.type(skuInput, 'ISBN-NEW-EDITION')

    expect(dialog.getByText(/실제로 발주하는 도서가 바뀝니다/)).toBeInTheDocument()
  })

  it('AC-LCONF-SKU: reverting the SKU back to its original value clears the warning and omits `sku` from the payload', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))
    const skuInput = dialog.getByLabelText('SKU 정정 (선택)')

    await user.clear(skuInput)
    await user.type(skuInput, 'ISBN-NEW-EDITION')
    await user.clear(skuInput)
    await user.type(skuInput, SAMPLE_LINE_ITEM.sku)

    expect(dialog.queryByText(/실제로 발주하는 도서가 바뀝니다/)).not.toBeInTheDocument()

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    await user.click(dialog.getByRole('button', { name: '발주처리' }))

    const [payload] = mutate.mock.calls[0] as [Record<string, unknown>]
    expect('sku' in payload).toBe(false)
  })

  it('AC-LCONF-SKU: submit is disabled while the SKU field is blank', async () => {
    const user = userEvent.setup()
    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )
    const dialog = within(screen.getByRole('dialog'))

    await user.selectOptions(dialog.getByLabelText('확정 발주처'), '북센')
    const skuInput = dialog.getByLabelText('SKU 정정 (선택)')
    await user.clear(skuInput)

    expect(dialog.getByRole('button', { name: '발주처리' })).toBeDisabled()
  })

  // AC-LCONF-SKU-007 (frontend surfacing): 409 collision response renders
  // the server's specific message — not the generic fallback — and the
  // modal stays open (same REQ-LCONF-105 mechanism as the pre-existing 409
  // test above, exercised here with the SKU-collision error text).
  it('AC-LCONF-SKU-007: renders the SKU collision message on 409 and keeps the modal open', () => {
    vi.mocked(useConfirmLineItem).mockReturnValue({
      mutate,
      isPending: false,
      isError: true,
      error: {
        response: {
          status: 409,
          data: {
            error:
              "sku 'ISBN-MEMBER-B' is already used by another item in this order — pick a different sku or correct the other item first.",
          },
        },
      },
    } as unknown as ReturnType<typeof useConfirmLineItem>)

    render(
      <LineItemConfirmModal lineItem={SAMPLE_LINE_ITEM} open={true} onOpenChange={onOpenChange} />
    )

    expect(screen.getByRole('alert')).toHaveTextContent(
      "sku 'ISBN-MEMBER-B' is already used by another item in this order"
    )
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalled()
  })
})
