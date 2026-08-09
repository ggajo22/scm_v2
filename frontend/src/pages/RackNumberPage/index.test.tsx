import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { RackNumberPage } from './index'

vi.mock('./tabs/SearchTab', () => ({
  SearchTab: () => <div data-testid="search-tab-content">search-tab</div>,
}))

vi.mock('./tabs/SummaryTab', () => ({
  SummaryTab: () => <div data-testid="summary-tab-content">summary-tab</div>,
}))

describe('RackNumberPage tab shell — SPEC-ORDER-014', () => {
  it('AC-RACKSUM-009b: shows the "주문 검색" tab content immediately on first load, without any tab click', () => {
    render(<RackNumberPage />)

    expect(screen.getByTestId('search-tab-content')).toBeInTheDocument()
    expect(screen.queryByTestId('summary-tab-content')).not.toBeInTheDocument()
  })

  it('AC-RACKSUM-009: renders exactly two tab controls labeled "주문 검색" and "렉번호 요약"', () => {
    render(<RackNumberPage />)

    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(2)
    expect(screen.getByRole('tab', { name: '주문 검색' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '렉번호 요약' })).toBeInTheDocument()
  })

  it('AC-RACKSUM-009/010: clicking the "렉번호 요약" tab switches the panel to SummaryTab', () => {
    render(<RackNumberPage />)

    fireEvent.click(screen.getByRole('tab', { name: '렉번호 요약' }))

    expect(screen.getByTestId('summary-tab-content')).toBeInTheDocument()
    expect(screen.queryByTestId('search-tab-content')).not.toBeInTheDocument()
  })

  it('switching back to "주문 검색" restores the SearchTab panel', () => {
    render(<RackNumberPage />)

    fireEvent.click(screen.getByRole('tab', { name: '렉번호 요약' }))
    fireEvent.click(screen.getByRole('tab', { name: '주문 검색' }))

    expect(screen.getByTestId('search-tab-content')).toBeInTheDocument()
    expect(screen.queryByTestId('summary-tab-content')).not.toBeInTheDocument()
  })
})
