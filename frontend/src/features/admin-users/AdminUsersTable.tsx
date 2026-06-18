import type { AdminUser } from '@/types/auth'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface AdminUsersTableProps {
  users: AdminUser[]
  currentUserId: number
  onEdit: (user: AdminUser) => void
  onResetPassword: (user: AdminUser) => void
}

// REQ-017: Admin users table with action buttons
export function AdminUsersTable({
  users,
  currentUserId,
  onEdit,
  onResetPassword,
}: AdminUsersTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>사용자명</TableHead>
          <TableHead>역할</TableHead>
          <TableHead>상태</TableHead>
          <TableHead>가입일</TableHead>
          <TableHead className="text-right">작업</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => (
          <TableRow key={user.id}>
            <TableCell className="font-medium">
              {user.username}
              {user.id === currentUserId && (
                <span className="ml-2 text-xs text-muted-foreground">(나)</span>
              )}
            </TableCell>
            <TableCell>
              <Badge variant={user.role === 'super_admin' ? 'default' : 'secondary'}>
                {user.role === 'super_admin' ? '최고관리자' : '관리자'}
              </Badge>
            </TableCell>
            <TableCell>
              <Badge variant={user.is_active ? 'default' : 'destructive'}>
                {user.is_active ? '활성' : '비활성'}
              </Badge>
            </TableCell>
            <TableCell>
              {user.date_joined
                ? new Date(user.date_joined).toLocaleDateString('ko-KR')
                : '-'}
            </TableCell>
            <TableCell className="text-right space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(user)}
                aria-label={`${user.username} 수정`}
              >
                수정
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onResetPassword(user)}
                aria-label={`${user.username} 비밀번호 초기화`}
              >
                비밀번호 초기화
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
