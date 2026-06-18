import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DashboardPage } from './DashboardPage'

describe('DashboardPage', () => {
  it('대시보드 제목을 렌더링한다', () => {
    render(<DashboardPage />)
    expect(screen.getByText('대시보드')).toBeInTheDocument()
  })
})
