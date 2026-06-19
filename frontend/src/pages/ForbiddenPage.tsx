import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

// REQ-016: /403 page with navigation links
export function ForbiddenPage() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-destructive">403</h1>
        <h2 className="text-xl font-semibold">접근 권한이 없습니다.</h2>
        <p className="text-muted-foreground">
          이 페이지에 접근할 권한이 없습니다.
        </p>
        <div className="flex gap-4 justify-center pt-4">
          <Button asChild variant="outline">
            <Link to={-1 as unknown as string}>돌아가기</Link>
          </Button>
          <Button asChild>
            <Link to="/">대시보드로 이동</Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
