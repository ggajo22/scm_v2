import { useDashboardMetrics } from '@/features/book/hooks/useDashboardMetrics'
import type { StatusCount } from '@/types/book'

// @MX:ANCHOR: [AUTO] DashboardPage — top-level consumer of useDashboardMetrics hook
// @MX:REASON: All dashboard metric display logic flows through this component
export function DashboardPage() {
  const { data, isPending, isError } = useDashboardMetrics()

  if (isPending) {
    return (
      <div className="p-6" role="status" aria-label="로딩 중">
        <div className="h-8 w-48 bg-muted animate-pulse rounded" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">대시보드 지표를 불러오는데 실패했습니다.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">대시보드</h1>

      {/* Summary metrics grid */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard label="오류 건수" value={data.error_total} />
        <MetricCard label="대기 건수" value={data.waiting_total} />
        <MetricCard label="24h Shopify 생성" value={data.shopify_created_24h} />
        <MetricCard label="미해결 메모" value={data.unresolved_note_count} />
        <MetricCard label="판매가 0" value={data.sale_zero_count} />
        <MetricCard label="원가 0" value={data.cost_zero_count} />
      </div>

      {/* Status counts table */}
      <section aria-label="상태별 현황">
        <h2 className="text-lg font-semibold mb-2">상태별 현황</h2>
        <StatusTable rows={data.status_counts} />
      </section>

      {/* Error rows breakdown */}
      {data.error_rows.length > 0 && (
        <section aria-label="오류 상태 분류">
          <h2 className="text-lg font-semibold mb-2">오류 상태 분류</h2>
          <StatusTable rows={data.error_rows} />
        </section>
      )}
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

function StatusTable({ rows }: { rows: StatusCount[] }) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">데이터가 없습니다.</p>
  }

  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="border-b bg-muted/50">
          <th className="py-2 px-3 text-left font-medium">상태</th>
          <th className="py-2 px-3 text-left font-medium">레이블</th>
          <th className="py-2 px-3 text-right font-medium">건수</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.status} className="border-b last:border-0">
            <td className="py-2 px-3">{row.status}</td>
            <td className="py-2 px-3">{row.label}</td>
            <td className="py-2 px-3 text-right">{row.count}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
