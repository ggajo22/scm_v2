import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { skuSetsApi, type SkuBundle } from './api'

function formatIsbnList(bundle: SkuBundle): string {
  return bundle.member_isbns
    .map((m) => `${m.isbn} (${m.book_title ?? '—'})`)
    .join('\n')
}

function parseIsbnLines(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
}

// @MX:ANCHOR: [AUTO] SKU 세트 매핑 관리 페이지 — CRUD 전체 흐름 통합
// @MX:REASON: 라우터 진입점이며 list/create/update/delete 뮤테이션을 모두 조율
export function SkuSetsPage() {
  const queryClient = useQueryClient()

  // ──────────────────────────────────────────────
  // Fetch
  // ──────────────────────────────────────────────
  const { data: bundles, isPending, isError } = useQuery({
    queryKey: ['sku-sets'],
    queryFn: skuSetsApi.list,
  })

  // ──────────────────────────────────────────────
  // Create dialog state
  // ──────────────────────────────────────────────
  const [createOpen, setCreateOpen] = useState(false)
  const [newBundleSku, setNewBundleSku] = useState('')
  const [newIsbnText, setNewIsbnText] = useState('')

  // ──────────────────────────────────────────────
  // Edit dialog state
  // ──────────────────────────────────────────────
  const [editBundle, setEditBundle] = useState<SkuBundle | null>(null)
  const [editIsbnText, setEditIsbnText] = useState('')

  // ──────────────────────────────────────────────
  // Delete confirm state
  // ──────────────────────────────────────────────
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  // ──────────────────────────────────────────────
  // Mutations
  // ──────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: ({ bundle_sku, isbns }: { bundle_sku: string; isbns: string[] }) =>
      skuSetsApi.create(bundle_sku, isbns),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sku-sets'] })
      toast.success('번들이 생성되었습니다.')
      setCreateOpen(false)
      setNewBundleSku('')
      setNewIsbnText('')
    },
    onError: () => {
      toast.error('번들 생성에 실패했습니다.')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ bundle_sku, isbns }: { bundle_sku: string; isbns: string[] }) =>
      skuSetsApi.update(bundle_sku, isbns),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sku-sets'] })
      toast.success('번들이 수정되었습니다.')
      setEditBundle(null)
    },
    onError: () => {
      toast.error('번들 수정에 실패했습니다.')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (bundle_sku: string) => skuSetsApi.delete(bundle_sku),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sku-sets'] })
      toast.success('번들이 삭제되었습니다.')
      setDeleteTarget(null)
    },
    onError: () => {
      toast.error('번들 삭제에 실패했습니다.')
    },
  })

  // ──────────────────────────────────────────────
  // Handlers
  // ──────────────────────────────────────────────
  function handleCreate() {
    const isbns = parseIsbnLines(newIsbnText)
    if (!newBundleSku.trim()) {
      toast.error('Bundle SKU를 입력해주세요.')
      return
    }
    if (isbns.length === 0) {
      toast.error('ISBN을 한 줄에 하나씩 입력해주세요.')
      return
    }
    createMutation.mutate({ bundle_sku: newBundleSku.trim(), isbns })
  }

  function handleOpenEdit(bundle: SkuBundle) {
    setEditBundle(bundle)
    setEditIsbnText(bundle.member_isbns.map((m) => m.isbn).join('\n'))
  }

  function handleUpdate() {
    if (!editBundle) return
    const isbns = parseIsbnLines(editIsbnText)
    if (isbns.length === 0) {
      toast.error('ISBN을 한 줄에 하나씩 입력해주세요.')
      return
    }
    updateMutation.mutate({ bundle_sku: editBundle.bundle_sku, isbns })
  }

  function handleDeleteConfirm() {
    if (!deleteTarget) return
    deleteMutation.mutate(deleteTarget)
  }

  // ──────────────────────────────────────────────
  // Render states
  // ──────────────────────────────────────────────
  if (isPending) {
    return (
      <div className="p-6 space-y-4" role="status" aria-label="로딩 중">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-10 bg-muted animate-pulse rounded" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="p-6">
        <p className="text-destructive">SKU 세트 목록을 불러오는데 실패했습니다.</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">SKU 세트 매핑</h1>
        <Button onClick={() => setCreateOpen(true)}>번들 추가</Button>
      </div>

      {/* Table */}
      <div className="border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-56">Bundle SKU</TableHead>
              <TableHead>구성 ISBN 목록</TableHead>
              <TableHead className="w-36 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(bundles ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
                  등록된 번들이 없습니다.
                </TableCell>
              </TableRow>
            ) : (
              (bundles ?? []).map((bundle) => (
                <TableRow key={bundle.bundle_sku}>
                  <TableCell className="font-mono text-sm align-top pt-3">
                    {bundle.bundle_sku}
                  </TableCell>
                  <TableCell className="align-top pt-3">
                    <div className="space-y-0.5">
                      {bundle.member_isbns.map((m) => (
                        <div key={m.isbn} className="text-sm text-muted-foreground">
                          {m.isbn} ({m.book_title ?? '—'})
                        </div>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-right align-top pt-2">
                    <div className="flex justify-end gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleOpenEdit(bundle)}
                        aria-label={`${bundle.bundle_sku} 수정`}
                      >
                        수정
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => setDeleteTarget(bundle.bundle_sku)}
                        aria-label={`${bundle.bundle_sku} 삭제`}
                      >
                        삭제
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>번들 추가</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="new-bundle-sku">
                Bundle SKU
              </label>
              <Input
                id="new-bundle-sku"
                placeholder="예: GITANMATH-F SET"
                value={newBundleSku}
                onChange={(e) => setNewBundleSku(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium" htmlFor="new-isbn-text">
                ISBN 목록 (한 줄에 하나씩)
              </label>
              <textarea
                id="new-isbn-text"
                placeholder={'9788926025451\n9788926025468'}
                rows={6}
                value={newIsbnText}
                onChange={(e) => setNewIsbnText(e.target.value)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              취소
            </Button>
            <Button onClick={handleCreate} disabled={createMutation.isPending}>
              {createMutation.isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={!!editBundle} onOpenChange={(open) => !open && setEditBundle(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>번들 수정</DialogTitle>
          </DialogHeader>
          {editBundle && (
            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <p className="text-sm font-medium">Bundle SKU</p>
                <p className="text-sm font-mono text-muted-foreground">{editBundle.bundle_sku}</p>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium" htmlFor="edit-isbn-text">
                  ISBN 목록 (한 줄에 하나씩)
                </label>
                <textarea
                  id="edit-isbn-text"
                  rows={6}
                  value={editIsbnText}
                  onChange={(e) => setEditIsbnText(e.target.value)}
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
                <p className="text-xs text-muted-foreground">
                  현재 ISBN에 책 제목이 있으면 참고용으로 표시됩니다:
                </p>
                <div className="text-xs text-muted-foreground space-y-0.5 pl-2">
                  {editBundle.member_isbns.map((m) => (
                    <div key={m.isbn}>
                      {m.isbn} ({m.book_title ?? '—'})
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditBundle(null)}>
              취소
            </Button>
            <Button onClick={handleUpdate} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? '저장 중...' : '저장'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>번들 삭제</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            <span className="font-mono">{deleteTarget}</span> 번들을 삭제하시겠습니까?
            이 작업은 되돌릴 수 없습니다.
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              취소
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? '삭제 중...' : '삭제'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
