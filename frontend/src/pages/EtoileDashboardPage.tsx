import { useEtoileDashboard } from '@/features/book/hooks/useEtoileDashboard'
import type { EtoileStatusCount } from '@/types/book'

export function EtoileDashboardPage() {
  const { data, isPending, isError } = useEtoileDashboard()

  if (isPending) {
    return (
      <div className="p-6" role="status" aria-label="로딩 중">
        <div className="h-8 w-48 bg-muted animate-pulse rounded mb-4" />
        <div className="h-48 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">Etoile 현황을 불러오는데 실패했습니다.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">Etoile 현황</h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard label="전체 Etoile 재고" value={data.total} />
      </div>

      <section aria-label="Etoile 상태별 현황">
        <h2 className="text-lg font-semibold mb-2">상태별 현황</h2>
        <EtoileStatusTable rows={data.status_counts} />
      </section>
    </div>
  )
}

function MetricCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card p-4 text-card-foreground shadow-sm">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
    </div>
  )
}

function EtoileStatusTable({ rows }: { rows: EtoileStatusCount[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">데이터가 없습니다.</p>
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b bg-muted/50">
          <th className="py-2 px-3 text-left font-medium">상태값</th>
          <th className="py-2 px-3 text-left font-medium">레이블</th>
          <th className="py-2 px-3 text-right font-medium">건수</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={String(row.status)} className="border-b last:border-0">
            <td className="py-2 px-3">{row.status ?? '-'}</td>
            <td className="py-2 px-3">{row.label}</td>
            <td className="py-2 px-3 text-right">{row.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
