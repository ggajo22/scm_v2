import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, useLocation, Outlet } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export interface BookLayoutContext {
  query: string
}

export function BookLayout() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()

  // Local input state — decoupled from URL to avoid mid-IME composition searches
  const [inputValue, setInputValue] = useState(searchParams.get('q') ?? '')

  // Sync input when URL query changes externally (e.g. browser back/forward)
  useEffect(() => {
    setInputValue(searchParams.get('q') ?? '')
  }, [searchParams])

  const submit = (value: string) => {
    const trimmed = value.trim()
    if (trimmed.length === 0) {
      navigate('/books', { replace: true })
    } else {
      navigate(
        `/books/search?q=${encodeURIComponent(trimmed)}`,
        { replace: location.pathname === '/books/search' }
      )
    }
  }

  return (
    <div className="flex flex-col">
      <div className="px-6 py-4 border-b bg-background sticky top-0 z-10">
        <div className="flex gap-2 max-w-md">
          <Input
            placeholder="ISBN 또는 도서명으로 검색"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit(inputValue)}
            className="flex-1"
            aria-label="도서 검색"
          />
          <Button onClick={() => submit(inputValue)} aria-label="검색">
            검색
          </Button>
        </div>
      </div>
      <Outlet context={{ query: searchParams.get('q') ?? '' } satisfies BookLayoutContext} />
    </div>
  )
}
