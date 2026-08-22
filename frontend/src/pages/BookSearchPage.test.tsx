import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { BookSearchPage } from './BookSearchPage'
import type { BookSearchResult, PaginatedResponse } from '@/types/book'

vi.mock('@/features/book/hooks/useBookSearch')

import { useBookSearch } from '@/features/book/hooks/useBookSearch'

const mockUseBookSearch = vi.mocked(useBookSearch)

const listedBook: BookSearchResult = {
  id: 1,
  inven_SKU: '9788937460123',
  name: '토지',
  cover_image_url: 'https://cdn.example.com/toji.jpg',
  status_of_shopify: 100,
  etoile_listed: true,
  etoile_status_label: '리스팅 완료',
}

const unlistedBook: BookSearchResult = {
  id: 2,
  inven_SKU: '9791162540123',
  name: '데미안',
  cover_image_url: '',
  status_of_shopify: 100,
  etoile_listed: false,
  etoile_status_label: '미등록',
}

function renderWithResults(results: BookSearchResult[], { hasNextPage = false } = {}) {
  const page: PaginatedResponse<BookSearchResult> = {
    count: results.length,
    next: hasNextPage ? 'http://api.test/api/book/search/?page=2' : null,
    previous: null,
    results,
  }
  mockUseBookSearch.mockReturnValue({
    data: page,
    isPending: false,
    isFetching: false,
    isError: false,
  } as ReturnType<typeof useBookSearch>)

  const router = createMemoryRouter(
    [{ path: '/books', element: <BookSearchPage /> }],
    { initialEntries: ['/books?q=토지'] }
  )
  render(<RouterProvider router={router} />)
  return router
}

/** The `page` argument of the most recent useBookSearch call. */
function requestedPage() {
  const calls = mockUseBookSearch.mock.calls
  return calls[calls.length - 1][1]
}

beforeEach(() => {
  mockUseBookSearch.mockReset()
})

describe('BookSearchPage — 결과 표시 항목', () => {
  it('판매가 컬럼을 표시하지 않는다', () => {
    renderWithResults([listedBook])

    expect(screen.queryByRole('columnheader', { name: '판매가' })).not.toBeInTheDocument()
    expect(screen.queryByText(/원$/)).not.toBeInTheDocument()
  })

  it('표지 이미지를 썸네일로 표시한다', () => {
    renderWithResults([listedBook])

    const cover = screen.getByRole('img', { name: '토지 표지' })
    expect(cover).toHaveAttribute('src', 'https://cdn.example.com/toji.jpg')
    // 원본 URL은 툴팁으로 확인 가능해야 한다
    expect(cover).toHaveAttribute('title', 'https://cdn.example.com/toji.jpg')
  })

  it('표지 URL이 비어 있으면 플레이스홀더를 표시한다', () => {
    renderWithResults([unlistedBook])

    expect(screen.getByRole('img', { name: '표지 이미지 없음' })).toBeInTheDocument()
  })

  it('표지 URL이 깨지면 플레이스홀더로 대체한다', () => {
    renderWithResults([listedBook])

    fireEvent.error(screen.getByRole('img', { name: '토지 표지' }))

    expect(screen.queryByRole('img', { name: '토지 표지' })).not.toBeInTheDocument()
    expect(screen.getByRole('img', { name: '표지 이미지 없음' })).toBeInTheDocument()
  })

  it('ETOILE 리스팅 상태를 행마다 표시한다', () => {
    renderWithResults([listedBook, unlistedBook])

    expect(screen.getByRole('columnheader', { name: 'ETOILE' })).toBeInTheDocument()
    expect(screen.getByText('리스팅 완료')).toBeInTheDocument()
    expect(screen.getByText('미등록')).toBeInTheDocument()
  })
})

describe('BookSearchPage — 페이지 상태', () => {
  it('검색어가 바뀌면 첫 페이지로 되돌린다', async () => {
    const router = renderWithResults([listedBook], { hasNextPage: true })
    expect(requestedPage()).toBe(1)

    fireEvent.click(screen.getByRole('button', { name: '다음 페이지' }))
    await waitFor(() => expect(requestedPage()).toBe(2))

    await act(async () => {
      await router.navigate('/books?q=데미안')
    })

    // 2페이지를 보던 중 새 검색어가 들어오면 이전 페이지 번호로 조회해선 안 된다
    expect(requestedPage()).toBe(1)
  })
})
