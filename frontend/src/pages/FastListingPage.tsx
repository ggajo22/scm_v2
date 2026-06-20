import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useFastListingSku, type FastListingResult } from '@/features/book/hooks/useFastListingSku'

export function FastListingPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<FastListingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { mutate, isPending } = useFastListingSku()

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
      <h1 className="text-xl font-semibold mb-4">빠른 리스팅 추가</h1>
      <textarea
        className="w-full h-48 border rounded p-2 text-sm font-mono resize-y"
        placeholder="ISBN을 한 줄에 하나씩 입력하세요"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button className="mt-2 w-full" onClick={handleSubmit} disabled={isPending}>
        {isPending ? '처리 중...' : '리스팅 등록'}
      </Button>

      {error && <p className="mt-4 text-sm text-red-500">{error}</p>}

      {result && (
        <div className="mt-4 space-y-3">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => { setText(''); setResult(null) }}
          >
            다시 등록하기
          </Button>
          <div className="flex gap-4 text-sm">
            <span className="text-green-600 font-medium">생성됨: {result.created_count}개</span>
            <span className="text-blue-600 font-medium">업데이트됨: {result.updated_count}개</span>
            <span className="text-muted-foreground">건너뜀: {result.skipped_count}개</span>
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
          {result.updated.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">업데이트된 ISBN</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.updated.map((sku) => (
                  <li key={sku} className="text-blue-700">
                    {sku}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {result.skipped.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">건너뜀 (활성 도서 보호)</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.skipped.map((sku) => (
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
