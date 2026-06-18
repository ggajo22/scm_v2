import { useState } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateAdminUser } from './hooks/useAdminUsers'

const createAdminSchema = z.object({
  username: z.string().min(1, '사용자명을 입력해주세요'),
  password: z.string().min(8, '비밀번호는 최소 8자 이상이어야 합니다'),
  role: z.enum(['super_admin', 'admin'] as const, {
    message: '역할을 선택해주세요',
  }),
})

type CreateAdminFormValues = z.infer<typeof createAdminSchema>

interface CreateAdminDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// REQ-019: Create admin dialog with form validation
export function CreateAdminDialog({ open, onOpenChange }: CreateAdminDialogProps) {
  const createMutation = useCreateAdminUser()
  const [serverError, setServerError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<CreateAdminFormValues>({
    resolver: zodResolver(createAdminSchema),
  })

  const handleClose = () => {
    reset()
    setServerError(null)
    onOpenChange(false)
  }

  const onSubmit = async (data: CreateAdminFormValues) => {
    setServerError(null)
    try {
      await createMutation.mutateAsync(data)
      // REQ-021: Show toast on success
      toast.success('관리자가 생성되었습니다.')
      handleClose()
    } catch (error: unknown) {
      // REQ-022: Show inline error on 400
      const err = error as { response?: { status?: number; data?: Record<string, string[]> } }
      if (err.response?.status === 400 && err.response.data) {
        const messages = Object.values(err.response.data).flat().join(', ')
        setServerError(messages || '생성에 실패했습니다.')
      } else {
        setServerError('생성에 실패했습니다.')
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>관리자 생성</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="create-username">사용자명</Label>
            <Input
              id="create-username"
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
            <Label htmlFor="create-password">비밀번호</Label>
            <Input
              id="create-password"
              type="password"
              {...register('password')}
              aria-invalid={!!errors.password}
            />
            {errors.password && (
              <p role="alert" className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="create-role">역할</Label>
            <Select onValueChange={(value) => setValue('role', value as 'super_admin' | 'admin')}>
              <SelectTrigger id="create-role" aria-invalid={!!errors.role}>
                <SelectValue placeholder="역할을 선택하세요" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="super_admin">최고관리자</SelectItem>
                <SelectItem value="admin">관리자</SelectItem>
              </SelectContent>
            </Select>
            {errors.role && (
              <p role="alert" className="text-sm text-destructive">
                {errors.role.message}
              </p>
            )}
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
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? '생성 중...' : '생성'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
