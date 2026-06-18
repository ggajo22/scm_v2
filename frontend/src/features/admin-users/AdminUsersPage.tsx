import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAdminUsers } from './hooks/useAdminUsers'
import { AdminUsersTable } from './AdminUsersTable'
import { CreateAdminDialog } from './CreateAdminDialog'
import { EditAdminDialog } from './EditAdminDialog'
import { ResetPasswordDialog } from './ResetPasswordDialog'
import type { AdminUser } from '@/types/auth'
import { useAuthStore } from '@/store/authStore'

// @MX:ANCHOR: [AUTO] Admin users management page — integrates all admin user CRUD dialogs
// @MX:REASON: Fan-in from router, and coordinates Table + Create + Edit + Reset dialogs
export function AdminUsersPage() {
  const { data: users, isPending, isError } = useAdminUsers()
  const currentUser = useAuthStore((state) => state.user)
  const [createOpen, setCreateOpen] = useState(false)
  const [editUser, setEditUser] = useState<AdminUser | null>(null)
  const [resetUser, setResetUser] = useState<AdminUser | null>(null)

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
        <p className="text-destructive">관리자 목록을 불러오는데 실패했습니다.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">관리자 계정 관리</h1>
        <Button onClick={() => setCreateOpen(true)}>
          관리자 생성
        </Button>
      </div>

      {/* REQ-017: Admin users table */}
      <AdminUsersTable
        users={users ?? []}
        currentUserId={currentUser?.id ?? 0}
        onEdit={(user) => setEditUser(user)}
        onResetPassword={(user) => setResetUser(user)}
      />

      {/* REQ-019: Create dialog */}
      <CreateAdminDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />

      {/* REQ-023: Edit dialog */}
      <EditAdminDialog
        open={!!editUser}
        onOpenChange={(open) => !open && setEditUser(null)}
        user={editUser}
      />

      {/* REQ-026: Reset password dialog */}
      <ResetPasswordDialog
        open={!!resetUser}
        onOpenChange={(open) => !open && setResetUser(null)}
        user={resetUser}
      />
    </div>
  )
}
