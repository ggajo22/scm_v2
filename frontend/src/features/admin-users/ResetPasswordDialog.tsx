import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { useResetPassword } from './hooks/useAdminUsers'
import type { AdminUser } from '@/types/auth'

const resetPasswordSchema = z
  .object({
    new_password: z.string().min(8, '비밀번호는 최소 8자 이상이어야 합니다'),
    confirm_password: z.string().min(1, '비밀번호 확인을 입력해주세요'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: '비밀번호가 일치하지 않습니다.',
    path: ['confirm_password'],
  })

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>

interface ResetPasswordDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: AdminUser | null
}

// REQ-026: Reset password dialog with validation
export function ResetPasswordDialog({ open, onOpenChange, user }: ResetPasswordDialogProps) {
  const resetMutation = useResetPassword()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
  })

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  const onSubmit = async (data: ResetPasswordFormValues) => {
    if (!user) return
    try {
      await resetMutation.mutateAsync({
        id: user.id,
        payload: { new_password: data.new_password },
      })
      // REQ-028: Close dialog and show toast on success
      toast.success('비밀번호가 초기화되었습니다.')
      handleClose()
    } catch {
      toast.error('비밀번호 초기화에 실패했습니다.')
    }
  }

  if (!user) return null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{user.username}의 비밀번호 초기화</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="new-password">새 비밀번호</Label>
            <Input
              id="new-password"
              type="password"
              {...register('new_password')}
              aria-invalid={!!errors.new_password}
            />
            {errors.new_password && (
              <p role="alert" className="text-sm text-destructive">
                {errors.new_password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm-password">비밀번호 확인</Label>
            <Input
              id="confirm-password"
              type="password"
              {...register('confirm_password')}
              aria-invalid={!!errors.confirm_password}
            />
            {errors.confirm_password && (
              <p role="alert" className="text-sm text-destructive">
                {errors.confirm_password.message}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose}>
              취소
            </Button>
            <Button type="submit" disabled={resetMutation.isPending}>
              {resetMutation.isPending ? '초기화 중...' : '초기화'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
