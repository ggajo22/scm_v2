import { useState } from 'react'
import { Input } from '@/components/ui/input'
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

// REQ-SEARCH-009: debounce 300ms, REQ-SEARCH-010: no call for <2 chars (handled in hook)
// REQ-SEARCH-011: columns — ISBN(inven_SKU), title(name), price_sale, status_of_shopify
// REQ-SEARCH-012: loading state, REQ-SEARCH-013: error state, REQ-SEARCH-014: empty state
// REQ-SEARCH-015: pagination controls

export function BookSearchPage() {
  const [inputValue, setInputValue] = useState('')
  const [page, setPage] = useState(1)

  // Reset to page 1 when search changes
  const handleSearchChange = (value: string) => {
    setInputValue(value)
    setPage(1)
  }

  const { data, isPending, isError } = useBookSearch(inputValue, page)

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">도서 검색</h1>

      {/* Search input */}
      <Input
        placeholder="ISBN 또는 도서명으로 검색 (2자 이상)"
        value={inputValue}
        onChange={(e) => handleSearchChange(e.target.value)}
        className="max-w-md"
        aria-label="도서 검색"
      />

      {/* REQ-SEARCH-012: Loading state */}
      {isPending && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-8 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {/* REQ-SEARCH-013: Error state */}
      {isError && (
        <p className="text-destructive" role="alert">
          도서 목록을 불러오는데 실패했습니다.
        </p>
      )}

      {/* REQ-SEARCH-014: Empty state */}
      {!isPending && !isError && data?.count === 0 && (
        <p className="text-muted-foreground">검색 결과가 없습니다.</p>
      )}

      {/* REQ-SEARCH-011: Table */}
      {!isPending && !isError && data && data.count > 0 && (
        <div className="rounded-md border">
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

      {/* REQ-SEARCH-015: Pagination controls */}
      {!isPending && !isError && data && data.count > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            전체 {data.count}건
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={!data.previous}
              aria-label="이전 페이지"
            >
              이전
            </Button>
            <span className="flex items-center text-sm px-2">{page} 페이지</span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!data.next}
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
