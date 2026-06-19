import { useSearchParams, useNavigate, useLocation, Outlet } from 'react-router-dom'
import { Input } from '@/components/ui/input'

export interface BookLayoutContext {
  query: string
}

export function BookLayout() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()
  const query = searchParams.get('q') ?? ''

  const handleQueryChange = (value: string) => {
    if (value.length >= 2) {
      // Go to search page with query param
      navigate(`/books/search?q=${encodeURIComponent(value)}`, { replace: location.pathname === '/books/search' })
    } else if (value.length === 0) {
      // Return to dashboard
      if (location.pathname !== '/books') {
        navigate('/books', { replace: true })
      } else {
        setSearchParams({}, { replace: true })
      }
    } else {
      // 1 char — update param but stay on current page
      setSearchParams({ q: value }, { replace: true })
    }
  }

  return (
    <div className="flex flex-col">
      <div className="px-6 py-4 border-b bg-background sticky top-0 z-10">
        <Input
          placeholder="ISBN 또는 도서명으로 검색 (2자 이상)"
          value={query}
          onChange={(e) => handleQueryChange(e.target.value)}
          className="max-w-md"
          aria-label="도서 검색"
        />
      </div>
      <Outlet context={{ query } satisfies BookLayoutContext} />
    </div>
  )
}
