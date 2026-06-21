import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useVendorRules, useCreateVendorRule, useDeleteVendorRule } from '@/hooks/usePurchaseOrderQueries'

const DISTRIBUTOR_OPTIONS = ['처음교육', '아가페'] as const
type Distributor = (typeof DISTRIBUTOR_OPTIONS)[number]

export function VendorRulesTab() {
  const { data, isPending, isError } = useVendorRules()
  const createMutation = useCreateVendorRule()
  const deleteMutation = useDeleteVendorRule()

  const [publisherName, setPublisherName] = useState('')
  const [distributor, setDistributor] = useState<Distributor>('처음교육')

  const handleAdd = () => {
    if (!publisherName.trim()) return
    createMutation.mutate(
      { publisher_name: publisherName.trim(), distributor },
      {
        onSuccess: () => {
          setPublisherName('')
        },
      }
    )
  }

  const handleDelete = (id: number, publisherNameLabel: string) => {
    if (!window.confirm(`"${publisherNameLabel}" 규칙을 삭제하시겠습니까?`)) return
    deleteMutation.mutate(id)
  }

  return (
    <div className="space-y-6">
      {/* Add rule form */}
      <div className="border rounded-lg p-4 space-y-3 bg-muted/20">
        <h3 className="text-sm font-semibold">새 규칙 추가</h3>
        <div className="flex flex-wrap gap-3 items-end">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor="publisher-name">
              출판사명
            </label>
            <input
              id="publisher-name"
              type="text"
              value={publisherName}
              onChange={(e) => setPublisherName(e.target.value)}
              placeholder="출판사명 입력"
              className="border rounded px-2 py-1 text-sm w-48"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAdd()
              }}
              aria-label="출판사명"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor="rule-distributor">
              발주처
            </label>
            <select
              id="rule-distributor"
              value={distributor}
              onChange={(e) => setDistributor(e.target.value as Distributor)}
              className="border rounded px-2 py-1 text-sm"
              aria-label="발주처 선택"
            >
              {DISTRIBUTOR_OPTIONS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <Button
            size="sm"
            onClick={handleAdd}
            disabled={!publisherName.trim() || createMutation.isPending}
          >
            {createMutation.isPending ? '추가 중...' : '추가'}
          </Button>
        </div>
      </div>

      {/* Rules table */}
      {isPending && (
        <div role="status" aria-label="로딩 중" className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted animate-pulse rounded" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-destructive">발주처 규칙을 불러오는데 실패했습니다.</p>
      )}

      {data && (
        <>
          <p className="text-sm text-muted-foreground">총 {data.count}건</p>
          <div className="overflow-x-auto rounded border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="py-2 px-3 text-left font-medium">출판사명</th>
                  <th className="py-2 px-3 text-left font-medium">발주처</th>
                  <th className="py-2 px-3 text-left font-medium">등록일</th>
                  <th className="py-2 px-3 text-center font-medium w-16">삭제</th>
                </tr>
              </thead>
              <tbody>
                {data.results.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-muted-foreground">
                      등록된 규칙이 없습니다.
                    </td>
                  </tr>
                )}
                {data.results.map((rule) => (
                  <tr key={rule.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-2 px-3">{rule.publisher_name}</td>
                    <td className="py-2 px-3">
                      <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                        {rule.distributor}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-xs text-muted-foreground">
                      {new Date(rule.created_at).toLocaleDateString('ko-KR')}
                    </td>
                    <td className="py-2 px-3 text-center">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                        onClick={() => handleDelete(rule.id, rule.publisher_name)}
                        disabled={deleteMutation.isPending}
                        aria-label={`${rule.publisher_name} 규칙 삭제`}
                      >
                        <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
