import { useState } from 'react'
import { useSearchParams, useNavigate, useLocation, Outlet, Link } from 'react-router-dom'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export interface BookLayoutContext {
  query: string
}

export function BookLayout() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const location = useLocation()

  const [inputValue, setInputValue] = useState('')

  // clearAfter: true when user explicitly submits (button/Enter) — clears input for next search
  // false for ISBN auto-submit (onChange) — user is still typing
  const submit = (value: string, clearAfter = false) => {
    const trimmed = value.trim()
    if (trimmed.length === 0) {
      navigate('/books', { replace: true })
    } else {
      navigate(
        `/books/search?q=${encodeURIComponent(trimmed)}`,
        { replace: location.pathname === '/books/search' }
      )
    }
    if (clearAfter) setInputValue('')
  }

  return (
    <div className="flex flex-col">
      <div className="px-6 py-4 border-b bg-white dark:bg-gray-900 sticky top-0 z-10">
        <div className="flex gap-2 max-w-md">
          <Input
            placeholder="ISBN 또는 도서명으로 검색"
            value={inputValue}
            onChange={(e) => {
              const value = e.target.value
              setInputValue(value)
              // Digits-only → ISBN path: auto-submit on every keystroke (0 ms debounce, index scan)
              if (/^\d*$/.test(value)) submit(value)
            }}
            onKeyDown={(e) => e.key === 'Enter' && submit(inputValue, true)}
            className="flex-1"
            aria-label="도서 검색"
          />
          <Button onClick={() => submit(inputValue, true)} aria-label="검색">
            검색
          </Button>
          <Link to="/books/add-isbn">
            <Button variant="outline" type="button">ISBN 추가</Button>
          </Link>
        </div>
      </div>
      <Outlet context={{ query: searchParams.get('q') ?? '' } satisfies BookLayoutContext} />
    </div>
  )
}
