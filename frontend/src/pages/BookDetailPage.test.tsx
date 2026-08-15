import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { http, HttpResponse } from 'msw'
import { BookDetailPage } from './BookDetailPage'
import { useBookDetail } from '@/features/book/hooks/useBookDetail'
import { useShopifyLiveInfo } from '@/features/book/hooks/useShopifyLiveInfo'
import { server } from '@/test/server'
import type { BookDetail, BookInfo } from '@/types/book'

vi.mock('@/features/book/hooks/useBookDetail', () => ({
  useBookDetail: vi.fn(),
}))

vi.mock('@/features/book/hooks/useShopifyLiveInfo', () => ({
  useShopifyLiveInfo: vi.fn(),
}))

const mockUseBookDetail = vi.mocked(useBookDetail)
const mockUseShopifyLiveInfo = vi.mocked(useShopifyLiveInfo)

function buildBookInfo(overrides: Partial<BookInfo> = {}): BookInfo {
  return {
    id: 1,
    status: 'A',
    price_sale: 10000,
    name: '테스트 도서',
    useruse1: '출판사',
    useruse2: '작가',
    price: 8000,
    opndate: '2026-01-01',
    outrt2: 0,
    qty: 1,
    retyn: 'N',
    booxen_cate_cd1: 0,
    booxen_cate_cd2: 0,
    booxen_cate_cd3: 0,
    page: 200,
    weight: 300,
    kyobo_weight: 555,
    kyobo_status: '',
    kyobo_supply_price: 0,
    yes24_weight: 320,
    aladin_weight: 310,
    manual_weight: null,
    dim1: null,
    dim2: null,
    dim3: null,
    image_detail: '',
    cover_image_url: '',
    cover_image_url2: null,
    desc_table: '',
    desc_pub: '',
    desc_author: '',
    desc_desc: '',
    kyobo_category1: '',
    kyobo_category2: '',
    kyobo_category3: '',
    kyobo_category4: '',
    kyobo_category5: '',
    updated_at: '2026-08-01T00:00:00Z',
    ...overrides,
  }
}

function buildBookDetail(infoOverrides: Partial<BookInfo> = {}): BookDetail {
  return {
    id: 1,
    inven_SKU: 'SKU-TEST-1',
    vendor: '',
    store: '',
    status_of_shopify: 80,
    info: buildBookInfo(infoOverrides),
    notes: [],
    shopify_products: [],
    etoile: null,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // NOTE: build a fresh element tree on every call (not a captured/reused
  // reference) — reusing the same element object across rerender() hits
  // React's referential bailout and silently skips re-invoking the tree.
  function buildTree() {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/books/1']}>
          <Routes>
            <Route path="/books/:id" element={<BookDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const utils = render(buildTree())
  return { ...utils, rerenderPage: () => utils.rerender(buildTree()) }
}

// SPEC-PURCHASE-ORDER-011 회귀 방지: BookDetailPage 내 WeightSection은 저장 직후
// info 리페치로 새 객체 참조가 들어와도 교보 무게 입력값을 유지해야 한다.
describe('BookDetailPage - WeightSection 교보 무게 동기화', () => {
  it('info가 리렌더로 새 참조를 받아도 교보 무게 입력값이 비워지지 않는다', () => {
    // BooxenCategorySection이 내부적으로 호출하는 카테고리 조회는
    // 이 테스트의 관심사가 아니므로 빈 목록으로 무해화한다.
    server.use(
      http.get('http://localhost:8000/api/book/booxen-categories/', () => HttpResponse.json([]))
    )

    mockUseShopifyLiveInfo.mockReturnValue({
      isPending: true,
      isError: false,
      data: undefined,
    } as unknown as ReturnType<typeof useShopifyLiveInfo>)

    mockUseBookDetail.mockReturnValue({
      isPending: false,
      isError: false,
      error: null,
      data: buildBookDetail({ kyobo_weight: 555 }),
    } as unknown as ReturnType<typeof useBookDetail>)

    const { rerenderPage } = renderPage()

    expect(screen.getByDisplayValue('555')).toBeInTheDocument()

    // 저장 후 refetch를 흉내낸다: 서버의 최신 교보 무게(777)를 담은 새 info 객체가 들어온다.
    mockUseBookDetail.mockReturnValue({
      isPending: false,
      isError: false,
      error: null,
      data: buildBookDetail({ kyobo_weight: 777 }),
    } as unknown as ReturnType<typeof useBookDetail>)

    rerenderPage()

    // useEffect가 kyobo_weight를 누락하면 이 input은 undefined로 빠지며
    // 최신 값(777)을 반영하지 못한다.
    expect(screen.getByDisplayValue('777')).toBeInTheDocument()
  })
})
