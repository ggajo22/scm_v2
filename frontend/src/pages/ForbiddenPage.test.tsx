import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ForbiddenPage } from './ForbiddenPage'

describe('ForbiddenPage', () => {
  it('REQ-016: 403 메시지와 링크를 렌더링한다', () => {
    render(
      <MemoryRouter>
        <ForbiddenPage />
      </MemoryRouter>
    )

    expect(screen.getByText('403')).toBeInTheDocument()
    expect(screen.getByText(/접근 권한이 없습니다/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /돌아가기/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /대시보드로 이동/i })).toBeInTheDocument()
  })
})
