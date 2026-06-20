import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useEtoileAddIsbn, type EtoileAddIsbnResult } from '@/features/book/hooks/useEtoileAddIsbn'

export function EtoileAddIsbnPage() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<EtoileAddIsbnResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { mutate, isPending } = useEtoileAddIsbn()

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
      <h1 className="text-xl font-semibold mb-1">Etoile ISBN 일괄 추가</h1>
      <p className="text-sm text-muted-foreground mb-4">
        본관에 없는 ISBN은 자동으로 등록 후 Etoile에 추가됩니다.
      </p>
      <textarea
        className="w-full h-48 border rounded p-2 text-sm font-mono resize-y"
        placeholder="ISBN을 한 줄에 하나씩 입력하세요"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button className="mt-2 w-full" onClick={handleSubmit} disabled={isPending}>
        {isPending ? '처리 중...' : 'Etoile 추가'}
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

          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            <span className="text-green-600 font-medium">
              본관+Etoile 신규: {result.etoile_created_new_book_count}개
            </span>
            <span className="text-blue-600 font-medium">
              Etoile 추가: {result.etoile_created_existing_book_count}개
            </span>
            <span className="text-muted-foreground">
              이미 등록됨: {result.etoile_existing_count}개
            </span>
          </div>

          {result.etoile_created_new_book_skus.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">본관 신규 생성 후 Etoile 등록 (status=-1)</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.etoile_created_new_book_skus.map((sku) => (
                  <li key={sku} className="text-green-700">{sku}</li>
                ))}
              </ul>
            </div>
          )}

          {result.etoile_created_existing_book_skus.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">본관 기존 → Etoile 등록 (status=0)</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.etoile_created_existing_book_skus.map((sku) => (
                  <li key={sku} className="text-blue-700">{sku}</li>
                ))}
              </ul>
            </div>
          )}

          {result.etoile_existing_skus.length > 0 && (
            <div>
              <p className="text-xs font-medium mb-1">이미 Etoile에 등록됨 (건너뜀)</p>
              <ul className="text-xs font-mono space-y-0.5">
                {result.etoile_existing_skus.map((sku) => (
                  <li key={sku} className="text-muted-foreground">{sku}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
