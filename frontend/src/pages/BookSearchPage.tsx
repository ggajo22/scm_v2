import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useBookSearch } from '@/features/book/hooks/useBookSearch'

export function BookSearchPage() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') ?? ''
  const [page, setPage] = useState(1)
  useEffect(() => { setPage(1) }, [query])
  const { data, isPending, isFetching, isError } = useBookSearch(query, page)

  // isPending  = no cache at all (very first search)
  // isFetching = request in-flight (first load OR re-search with stale/placeholder data)
  const showSkeleton = isPending
  const showResults  = !isPending && !isError

  return (
    <div className="p-6 space-y-4">

      {/* Progress bar: inline style to avoid Tailwind v4 @keyframes resolution issue */}
      {isFetching && (
        <div className="fixed top-0 left-0 right-0 z-50 h-1 overflow-hidden bg-primary/20">
          <div
            className="h-full bg-primary"
            style={{ animation: 'search-progress 1.2s ease-in-out infinite' }}
          />
        </div>
      )}

      {/* Search query header */}
      {query && !isPending && data && (
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{query}</span> 검색 결과: {data.count}건
        </p>
      )}

      {/* First-load skeleton */}
      {showSkeleton && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-destructive" role="alert">
          도서 목록을 불러오는데 실패했습니다.
        </p>
      )}

      {showResults && data?.count === 0 && !isFetching && (
        <p className="text-muted-foreground">검색 결과가 없습니다.</p>
      )}

      {/* Results table — dim while re-fetching to signal stale data */}
      {showResults && data && data.count > 0 && (
        <div
          className="rounded-md border transition-opacity duration-200"
          style={{ opacity: isFetching ? 0.5 : 1 }}
        >
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ISBN</TableHead>
                <TableHead>도서명</TableHead>
                <TableHead className="text-right">판매가</TableHead>
                <TableHead className="text-right">Shopify 상태</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.results.map((book) => (
                <TableRow key={book.inven_SKU}>
                  <TableCell className="font-mono text-sm">{book.inven_SKU}</TableCell>
                  <TableCell>{book.name}</TableCell>
                  <TableCell className="text-right">
                    {book.price_sale.toLocaleString()}원
                  </TableCell>
                  <TableCell className="text-right">{book.status_of_shopify}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {showResults && data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">전체 {data.count}건</span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!data.previous || isFetching}
              aria-label="이전 페이지"
            >
              이전
            </Button>
            <span className="flex items-center text-sm px-2">{page} 페이지</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!data.next || isFetching}
              aria-label="다음 페이지"
            >
              다음
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
