import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateAdminUser } from './hooks/useAdminUsers'
import type { AdminUser } from '@/types/auth'
import { useAuthStore } from '@/store/authStore'

const editAdminSchema = z.object({
  username: z.string().min(1, '사용자명을 입력해주세요'),
  role: z.enum(['super_admin', 'admin']),
  is_active: z.boolean(),
})

type EditAdminFormValues = z.infer<typeof editAdminSchema>

interface EditAdminDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: AdminUser | null
}

// REQ-023: Edit admin dialog with partial update
export function EditAdminDialog({ open, onOpenChange, user }: EditAdminDialogProps) {
  const updateMutation = useUpdateAdminUser()
  const currentUser = useAuthStore((state) => state.user)
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<EditAdminFormValues>({
    resolver: zodResolver(editAdminSchema),
  })

  const isActive = watch('is_active')

  useEffect(() => {
    if (user) {
      reset({
        username: user.username,
        role: user.role,
        is_active: user.is_active,
      })
    }
  }, [user, reset])

  const handleClose = () => {
    setServerError(null)
    onOpenChange(false)
  }

  const onSubmit = async (data: EditAdminFormValues) => {
    if (!user) return
    setServerError(null)

    // REQ-025: Block deactivating own account
    if (currentUser?.id === user.id && !data.is_active) {
      setServerError('자신의 계정을 비활성화할 수 없습니다.')
      return
    }

    // REQ-024: Only send changed fields
    const payload: Partial<EditAdminFormValues> = {}
    if (data.username !== user.username) payload.username = data.username
    if (data.role !== user.role) payload.role = data.role
    if (data.is_active !== user.is_active) payload.is_active = data.is_active

    if (Object.keys(payload).length === 0) {
      handleClose()
      return
    }

    try {
      await updateMutation.mutateAsync({ id: user.id, payload })
      toast.success('관리자 정보가 수정되었습니다.')
      handleClose()
    } catch (error: unknown) {
      const err = error as { response?: { status?: number; data?: Record<string, string[]> } }
      if (err.response?.status === 400 && err.response.data) {
        const messages = Object.values(err.response.data).flat().join(', ')
        setServerError(messages || '수정에 실패했습니다.')
      } else {
        setServerError('수정에 실패했습니다.')
      }
    }
  }

  if (!user) return null

  const isSelfDeactivation = currentUser?.id === user.id

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>관리자 수정</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-username">사용자명</Label>
            <Input
              id="edit-username"
              {...register('username')}
              aria-invalid={!!errors.username}
            />
            {errors.username && (
              <p role="alert" className="text-sm text-destructive">
                {errors.username.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="edit-role">역할</Label>
            <Select
              defaultValue={user.role}
              onValueChange={(value) => setValue('role', value as 'super_admin' | 'admin')}
            >
              <SelectTrigger id="edit-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="super_admin">최고관리자</SelectItem>
                <SelectItem value="admin">관리자</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center gap-3">
            <Switch
              id="edit-is-active"
              checked={isActive}
              onCheckedChange={(checked) => setValue('is_active', checked)}
              disabled={isSelfDeactivation}
              aria-label="계정 활성화 여부"
            />
            <Label htmlFor="edit-is-active">
              {isActive ? '활성' : '비활성'}
              {isSelfDeactivation && (
                <span className="ml-2 text-xs text-muted-foreground">
                  (자신의 계정은 비활성화할 수 없습니다)
                </span>
              )}
            </Label>
          </div>

          {serverError && (
            <p role="alert" className="text-sm text-destructive">
              {serverError}
            </p>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
