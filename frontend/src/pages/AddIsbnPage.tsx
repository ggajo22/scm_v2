import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useAddIsbn, type AddIsbnResult } from '@/features/book/hooks/useAddIsbn'

export function AddIsbnPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<AddIsbnResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { mutate, isPending } = useAddIsbn()

  const handleSubmit = () => {
    const skus = text.split('\n').map((s) => s.trim()).filter(Boolean)
    setError(null)
    setResult(null)
    mutate(
      { skus },
      {
        onSuccess: (data) => setResult(data),
        onError: () => setError('요청에 실패했습니다. 다시 시도해 주세요.'),
      },
    )
  }

  return (
    <div className="p-6 max-w-lg">
      <div className="mb-4">
        <Link to="/books" className="text-sm text-muted-foreground hover:underline">
          ← 도서 검색으로 돌아가기
        </Link>
      </div>
      <h1 className="text-xl font-semibold mb-4">ISBN 일괄 추가</h1>
      <textarea
        className="w-full h-48 border rounded p-2 text-sm font-mono resize-y"
        placeholder="ISBN을 한 줄에 하나씩 입력하세요"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button className="mt-2 w-full" onClick={handleSubmit} disabled={isPending}>
        {isPending ? '처리 중...' : '추가'}
      </Button>

      {error && <p className="mt-4 text-sm text-red-500">{error}</p>}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="flex gap-4 text-sm">
            <span className="text-green-600 font-medium">생성됨: {result.created_count}개</span>
            <span className="text-muted-foreground">중복: {result.duplicate_count}개</span>
          </div>
          {result.created.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">생성된 ISBN</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.created.map((sku) => (
                  <li key={sku} className="text-green-700">
                    {sku}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.duplicates.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">중복 ISBN</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.duplicates.map((sku) => (
                  <li key={sku} className="text-muted-foreground">
                    {sku}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
