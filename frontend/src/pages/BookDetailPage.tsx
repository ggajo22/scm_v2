import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { api } from '@/lib/axios'
import { useBookDetail } from '@/features/book/hooks/useBookDetail'
import { useShopifyLiveInfo } from '@/features/book/hooks/useShopifyLiveInfo'
import {
  useUpdateBookInfo,
  useAddNote,
  useResolveNote,
  useUpdateShopifyStatus,
  useUpdateEtoileShopifyStatus,
  useUpdateEtoileTags,
} from '@/features/book/hooks/useBookMutations'
import type { BookInfo, BookNote, ShopifyStoreInfo } from '@/types/book'

// ---------------------------------------------------------------------------
// status_of_shopify labels (mirrors backend book/constants.py STATUS_LABELS)
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<number, string> = {
  5:   '북센 상품 없음',
  6:   '북센 상품 없음 · 교보 공급가 완료',
  12:  '구판 / 절판',
  14:  '카테고리 / 이미지 정보 없음',
  15:  '정보 수정 시 리스팅·업데이트 대상',
  30:  '이미지 다운로드 완료',
  31:  '이미지 다운로드 에러',
  32:  '이미지 URL 이상',
  80:  'Active (교보 미포함)',
  81:  'Active (교보 포함)',
}

// ---------------------------------------------------------------------------
// Small presentational helpers
// ---------------------------------------------------------------------------

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-card p-6 space-y-4">
      <h2 className="text-base font-semibold text-foreground">{title}</h2>
      {children}
    </div>
  )
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[160px_1fr] items-start gap-3">
      <Label className="pt-2 text-sm text-muted-foreground leading-tight">{label}</Label>
      <div>{children}</div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div role="status" aria-label="로딩 중" className="space-y-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="rounded-lg border p-6 space-y-3">
          <div className="h-5 w-32 bg-muted animate-pulse rounded" />
          {Array.from({ length: 4 }).map((_, j) => (
            <div key={j} className="h-9 bg-muted animate-pulse rounded" />
          ))}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section: 기본 정보
// ---------------------------------------------------------------------------

type BasicInfoState = Pick<
  BookInfo,
  | 'name'
  | 'cover_image_url'
  | 'price'
  | 'price_sale'
  | 'kyobo_supply_price'
  | 'status'
  | 'useruse1'
  | 'useruse2'
  | 'opndate'
  | 'dim1'
  | 'dim2'
  | 'dim3'
  | 'page'
  | 'image_detail'
>

function BasicInfoSection({ info, bookId }: { info: BookInfo; bookId: number }) {
  const [form, setForm] = useState<BasicInfoState>({
    name: info.name,
    cover_image_url: info.cover_image_url,
    price: info.price,
    price_sale: info.price_sale,
    kyobo_supply_price: info.kyobo_supply_price,
    status: info.status,
    useruse1: info.useruse1,
    useruse2: info.useruse2,
    opndate: info.opndate,
    dim1: info.dim1,
    dim2: info.dim2,
    dim3: info.dim3,
    page: info.page,
    image_detail: info.image_detail,
  })

  useEffect(() => {
    setForm({
      name: info.name,
      cover_image_url: info.cover_image_url,
      price: info.price,
      price_sale: info.price_sale,
      kyobo_supply_price: info.kyobo_supply_price,
      status: info.status,
      useruse1: info.useruse1,
      useruse2: info.useruse2,
      opndate: info.opndate,
      dim1: info.dim1,
      dim2: info.dim2,
      dim3: info.dim3,
      page: info.page,
        image_detail: info.image_detail,
    })
  }, [info])

  const mutation = useUpdateBookInfo(bookId)

  const setStr = (key: keyof BasicInfoState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const setNum = (key: keyof BasicInfoState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value === '' ? null : Number(e.target.value)
    setForm((prev) => ({ ...prev, [key]: val }))
  }

  return (
    <SectionCard title="기본 정보">
      <div className="space-y-3">
        <FieldRow label="도서명">
          <Input value={form.name} onChange={setStr('name')} />
        </FieldRow>
        <FieldRow label="표지 이미지 URL">
          <Input value={form.cover_image_url} onChange={setStr('cover_image_url')} />
        </FieldRow>
        <FieldRow label="MSRP">
          <Input type="number" value={form.price_sale} onChange={setNum('price_sale')} />
        </FieldRow>
        <FieldRow label="북센 COST">
          <Input type="number" value={form.price} onChange={setNum('price')} />
        </FieldRow>
        <FieldRow label="교보 COST">
          <Input type="number" value={form.kyobo_supply_price} onChange={setNum('kyobo_supply_price')} />
        </FieldRow>
        <FieldRow label="상태">
          <Input value={form.status} onChange={setStr('status')} />
        </FieldRow>
        <FieldRow label="출판사">
          <Input value={form.useruse1} onChange={setStr('useruse1')} />
        </FieldRow>
        <FieldRow label="작가">
          <Input value={form.useruse2} onChange={setStr('useruse2')} />
        </FieldRow>
        <FieldRow label="출판일">
          <Input type="date" value={form.opndate} onChange={setStr('opndate')} />
        </FieldRow>
        <FieldRow label="Dim1 (mm)">
          <Input type="number" value={form.dim1 ?? ''} onChange={setNum('dim1')} />
        </FieldRow>
        <FieldRow label="Dim2 (mm)">
          <Input type="number" value={form.dim2 ?? ''} onChange={setNum('dim2')} />
        </FieldRow>
        <FieldRow label="Dim3 (mm)">
          <Input type="number" value={form.dim3 ?? ''} onChange={setNum('dim3')} />
        </FieldRow>
        <FieldRow label="페이지">
          <Input type="number" value={form.page} onChange={setNum('page')} />
        </FieldRow>
        <FieldRow label="이미지 상세 URL">
          <Input value={form.image_detail} onChange={setStr('image_detail')} />
        </FieldRow>
      </div>
      <div className="flex justify-end pt-2">
        <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
          {mutation.isPending ? '저장 중...' : '저장'}
        </Button>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: 북센 카테고리 (cascading dropdowns)
// ---------------------------------------------------------------------------

interface BooksenCategoryItem {
  category_code: number
  category_name: string
  category_rank: number
}

function useBooksenCategories(topCode: number) {
  return useQuery<BooksenCategoryItem[]>({
    queryKey: ['booksen-categories', topCode],
    queryFn: async () => {
      const res = await api.get(`/api/book/booksen-categories/?top_code=${topCode}`)
      return res.data
    },
    staleTime: 1000 * 60 * 10,
  })
}

function BooksenCategorySection({ info, bookId }: { info: BookInfo; bookId: number }) {
  const [cd1, setCd1] = useState(info.booxen_cate_cd1)
  const [cd2, setCd2] = useState(info.booxen_cate_cd2)
  const [cd3, setCd3] = useState(info.booxen_cate_cd3)

  useEffect(() => {
    setCd1(info.booxen_cate_cd1)
    setCd2(info.booxen_cate_cd2)
    setCd3(info.booxen_cate_cd3)
  }, [info])

  const { data: level1 = [] } = useBooksenCategories(0)
  const { data: level2 = [] } = useBooksenCategories(cd1)
  const { data: level3 = [] } = useBooksenCategories(cd2)

  const mutation = useUpdateBookInfo(bookId)

  const handleCd1 = (val: string) => {
    const code = Number(val)
    setCd1(code)
    setCd2(0)
    setCd3(0)
  }

  const handleCd2 = (val: string) => {
    const code = Number(val)
    setCd2(code)
    setCd3(0)
  }

  const CategorySelect = ({
    value,
    options,
    onChange,
    disabled,
    placeholder,
  }: {
    value: number
    options: BooksenCategoryItem[]
    onChange: (val: string) => void
    disabled?: boolean
    placeholder: string
  }) => (
    <Select
      value={value > 0 ? String(value) : ''}
      onValueChange={onChange}
      disabled={disabled || options.length === 0}
    >
      <SelectTrigger>
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {options.map((cat) => (
          <SelectItem key={cat.category_code} value={String(cat.category_code)}>
            {cat.category_code} - {cat.category_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )

  return (
    <SectionCard title="북센 카테고리">
      <div className="space-y-3">
        <FieldRow label="카테고리1 (대)">
          <CategorySelect
            value={cd1}
            options={level1}
            onChange={handleCd1}
            placeholder="카테고리1 선택"
          />
        </FieldRow>
        <FieldRow label="카테고리2 (중)">
          <CategorySelect
            value={cd2}
            options={level2}
            onChange={handleCd2}
            disabled={cd1 === 0}
            placeholder={cd1 === 0 ? '카테고리1을 먼저 선택하세요' : '카테고리2 선택'}
          />
        </FieldRow>
        <FieldRow label="카테고리3 (소)">
          <CategorySelect
            value={cd3}
            options={level3}
            onChange={(val) => setCd3(Number(val))}
            disabled={cd2 === 0}
            placeholder={cd2 === 0 ? '카테고리2를 먼저 선택하세요' : '카테고리3 선택'}
          />
        </FieldRow>
      </div>
      <div className="flex justify-end pt-2">
        <Button
          onClick={() => mutation.mutate({ booxen_cate_cd1: cd1, booxen_cate_cd2: cd2, booxen_cate_cd3: cd3 })}
          disabled={mutation.isPending}
        >
          {mutation.isPending ? '저장 중...' : '저장'}
        </Button>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: 교보 카테고리
// ---------------------------------------------------------------------------

type KyoboCategoryState = Pick<
  BookInfo,
  | 'kyobo_category1'
  | 'kyobo_category2'
  | 'kyobo_category3'
  | 'kyobo_category4'
  | 'kyobo_category5'
>

function KyboCategorySection({ info, bookId }: { info: BookInfo; bookId: number }) {
  const [form, setForm] = useState<KyoboCategoryState>({
    kyobo_category1: info.kyobo_category1,
    kyobo_category2: info.kyobo_category2,
    kyobo_category3: info.kyobo_category3,
    kyobo_category4: info.kyobo_category4,
    kyobo_category5: info.kyobo_category5,
  })

  useEffect(() => {
    setForm({
      kyobo_category1: info.kyobo_category1,
      kyobo_category2: info.kyobo_category2,
      kyobo_category3: info.kyobo_category3,
      kyobo_category4: info.kyobo_category4,
      kyobo_category5: info.kyobo_category5,
      kyobo_weight: info.kyobo_weight,
    })
  }, [info])

  const mutation = useUpdateBookInfo(bookId)
  const setStr = (key: keyof KyoboCategoryState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))
  const setNum = (key: keyof KyoboCategoryState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [key]: Number(e.target.value) }))

  return (
    <SectionCard title="교보 카테고리">
      <div className="space-y-3">
        <FieldRow label="교보 카테고리1">
          <Input value={form.kyobo_category1} onChange={setStr('kyobo_category1')} />
        </FieldRow>
        <FieldRow label="교보 카테고리2">
          <Input value={form.kyobo_category2} onChange={setStr('kyobo_category2')} />
        </FieldRow>
        <FieldRow label="교보 카테고리3">
          <Input value={form.kyobo_category3} onChange={setStr('kyobo_category3')} />
        </FieldRow>
        <FieldRow label="교보 카테고리4">
          <Input value={form.kyobo_category4} onChange={setStr('kyobo_category4')} />
        </FieldRow>
        <FieldRow label="교보 카테고리5">
          <Input value={form.kyobo_category5} onChange={setStr('kyobo_category5')} />
        </FieldRow>
      </div>
      <div className="flex justify-end pt-2">
        <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
          {mutation.isPending ? '저장 중...' : '저장'}
        </Button>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: 중량 정보
// ---------------------------------------------------------------------------

type WeightState = Pick<BookInfo, 'weight' | 'kyobo_weight' | 'yes24_weight' | 'aladin_weight' | 'manual_weight'>

function WeightSection({ info, bookId }: { info: BookInfo; bookId: number }) {
  const [form, setForm] = useState<WeightState>({
    weight: info.weight,
    kyobo_weight: info.kyobo_weight,
    yes24_weight: info.yes24_weight,
    aladin_weight: info.aladin_weight,
    manual_weight: info.manual_weight,
  })

  useEffect(() => {
    setForm({
      weight: info.weight,
      yes24_weight: info.yes24_weight,
      aladin_weight: info.aladin_weight,
      manual_weight: info.manual_weight,
    })
  }, [info])

  const mutation = useUpdateBookInfo(bookId)
  const setNum = (key: keyof WeightState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value === '' ? null : Number(e.target.value)
    setForm((prev) => ({ ...prev, [key]: val }))
  }

  return (
    <SectionCard title="Weight 정보 (g)">
      <div className="space-y-3">
        <FieldRow label="Manual">
          <Input
            type="number"
            value={form.manual_weight ?? ''}
            onChange={setNum('manual_weight')}
            placeholder="미입력 시 자동 계산"
          />
        </FieldRow>
        <FieldRow label="북센">
          <Input type="number" value={form.weight} onChange={setNum('weight')} />
        </FieldRow>
        <FieldRow label="교보">
          <Input type="number" value={form.kyobo_weight} onChange={setNum('kyobo_weight')} />
        </FieldRow>
        <FieldRow label="예스24">
          <Input type="number" value={form.yes24_weight} onChange={setNum('yes24_weight')} />
        </FieldRow>
        <FieldRow label="알라딘">
          <Input type="number" value={form.aladin_weight} onChange={setNum('aladin_weight')} />
        </FieldRow>
      </div>
      <div className="flex justify-end pt-2">
        <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
          {mutation.isPending ? '저장 중...' : '저장'}
        </Button>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: 장문 텍스트
// ---------------------------------------------------------------------------

type LongTextState = Pick<BookInfo, 'desc_desc' | 'desc_table' | 'desc_pub' | 'desc_author'>

function LongTextSection({ info, bookId }: { info: BookInfo; bookId: number }) {
  const [form, setForm] = useState<LongTextState>({
    desc_desc: info.desc_desc,
    desc_table: info.desc_table,
    desc_pub: info.desc_pub,
    desc_author: info.desc_author,
  })

  useEffect(() => {
    setForm({
      desc_desc: info.desc_desc,
      desc_table: info.desc_table,
      desc_pub: info.desc_pub,
      desc_author: info.desc_author,
    })
  }, [info])

  const mutation = useUpdateBookInfo(bookId)
  const setStr = (key: keyof LongTextState) => (e: React.ChangeEvent<HTMLTextAreaElement>) =>
    setForm((prev) => ({ ...prev, [key]: e.target.value }))

  return (
    <SectionCard title="장문 텍스트">
      <div className="space-y-3">
        <FieldRow label="도서 소개">
          <textarea
            className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={form.desc_desc}
            onChange={setStr('desc_desc')}
          />
        </FieldRow>
        <FieldRow label="목차">
          <textarea
            className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={form.desc_table}
            onChange={setStr('desc_table')}
          />
        </FieldRow>
        <FieldRow label="출판사 서평">
          <textarea
            className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={form.desc_pub}
            onChange={setStr('desc_pub')}
          />
        </FieldRow>
        <FieldRow label="저자 소개">
          <textarea
            className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            value={form.desc_author}
            onChange={setStr('desc_author')}
          />
        </FieldRow>
      </div>
      <div className="flex justify-end pt-2">
        <Button onClick={() => mutation.mutate(form)} disabled={mutation.isPending}>
          {mutation.isPending ? '저장 중...' : '저장'}
        </Button>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: 노트
// ---------------------------------------------------------------------------

function NoteItem({
  note,
  onResolve,
  resolving,
}: {
  note: BookNote
  onResolve?: () => void
  resolving?: boolean
}) {
  return (
    <div className="flex items-start gap-3 rounded-md border p-3 text-sm">
      <Badge
        variant={note.note_type === 'SHIPPING' ? 'secondary' : 'outline'}
        className="shrink-0 mt-0.5"
      >
        {note.note_type === 'SHIPPING' ? '배송' : '일반'}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="whitespace-pre-wrap break-words">{note.content}</p>
        <p className="text-xs text-muted-foreground mt-1">
          {note.created_by} · {new Date(note.created_at).toLocaleString('ko-KR')}
        </p>
      </div>
      {onResolve && (
        <Button
          variant="outline"
          size="sm"
          onClick={onResolve}
          disabled={resolving}
          className="shrink-0"
        >
          해결
        </Button>
      )}
    </div>
  )
}

function NotesSection({ notes, bookId }: { notes: BookNote[]; bookId: number }) {
  const [noteType, setNoteType] = useState<'GENERAL' | 'SHIPPING'>('GENERAL')
  const [content, setContent] = useState('')
  const [showResolved, setShowResolved] = useState(false)

  const addMutation = useAddNote(bookId)
  const resolveMutation = useResolveNote(bookId)

  const unresolvedGeneral = notes.filter((n) => !n.is_resolved && n.note_type === 'GENERAL')
  const shipping = notes.filter((n) => n.note_type === 'SHIPPING')
  const resolved = notes.filter((n) => n.is_resolved)

  const handleAdd = () => {
    if (!content.trim()) return
    addMutation.mutate(
      { note_type: noteType, content: content.trim() },
      { onSuccess: () => setContent('') }
    )
  }

  return (
    <SectionCard title="노트">
      {/* Unresolved GENERAL notes */}
      {unresolvedGeneral.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            미해결 일반 노트 ({unresolvedGeneral.length})
          </p>
          {unresolvedGeneral.map((note) => (
            <NoteItem
              key={note.id}
              note={note}
              onResolve={() => resolveMutation.mutate(note.id)}
              resolving={resolveMutation.isPending}
            />
          ))}
        </div>
      )}

      {/* SHIPPING notes */}
      {shipping.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            배송 노트 ({shipping.length})
          </p>
          {shipping.map((note) => (
            <NoteItem key={note.id} note={note} />
          ))}
        </div>
      )}

      {/* Resolved notes (collapsed) */}
      {resolved.length > 0 && (
        <div className="space-y-2">
          <button
            type="button"
            className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setShowResolved((v) => !v)}
          >
            {showResolved ? '▲' : '▶'} 해결된 노트 ({resolved.length})
          </button>
          {showResolved && (
            <div className="space-y-2 opacity-60">
              {resolved.map((note) => (
                <NoteItem key={note.id} note={note} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add note form */}
      <div className="border-t pt-4 space-y-3">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          노트 추가
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setNoteType('GENERAL')}
            className={cn(
              'px-3 py-1.5 rounded-md text-sm border transition-colors',
              noteType === 'GENERAL'
                ? 'bg-gray-100 text-gray-700 border-gray-300'
                : 'bg-white border-gray-300 hover:bg-gray-50'
            )}
          >
            일반
          </button>
          <button
            type="button"
            onClick={() => setNoteType('SHIPPING')}
            className={cn(
              'px-3 py-1.5 rounded-md text-sm border transition-colors',
              noteType === 'SHIPPING'
                ? 'bg-gray-100 text-gray-700 border-gray-300'
                : 'bg-white border-gray-300 hover:bg-gray-50'
            )}
          >
            배송
          </button>
        </div>
        <textarea
          className="w-full min-h-[80px] rounded-md border border-input bg-background px-3 py-2 text-sm resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          placeholder="노트 내용을 입력하세요"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <div className="flex justify-end">
          <Button
            onClick={handleAdd}
            disabled={addMutation.isPending || !content.trim()}
            size="sm"
          >
            {addMutation.isPending ? '추가 중...' : '추가'}
          </Button>
        </div>
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Section: Shopify 상태
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// Section: Shopify 실시간 정보 (SPEC-SHOPIFY-INFO-001)
// ---------------------------------------------------------------------------

function ShopifyStoreBadge({ info }: { info: ShopifyStoreInfo }) {
  if (!info.registered) {
    return (
      <Badge variant="secondary" className="bg-gray-100 text-gray-500">
        미등록
      </Badge>
    )
  }

  const statusClass =
    info.status === 'active'
      ? 'bg-green-100 text-green-800'
      : info.status === 'draft'
        ? 'bg-amber-100 text-amber-800'
        : 'bg-gray-100 text-gray-600'

  const statusLabel =
    info.status === 'active' ? 'Active' : info.status === 'draft' ? 'Draft' : info.status ?? '-'

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        statusClass,
      )}
    >
      {statusLabel}
    </span>
  )
}

function ShopifyLiveInfoSection({
  bookId,
  etoileInfo,
}: {
  bookId: number
  etoileInfo: import('@/types/book').EtoileInfo | null | undefined
}) {
  const { data, isPending, isError } = useShopifyLiveInfo(bookId)
  const booksenMutation = useUpdateShopifyStatus(bookId)
  const etoileMutation = useUpdateEtoileShopifyStatus(bookId)
  const tagsMutation = useUpdateEtoileTags(bookId)

  const [tagsInput, setTagsInput] = useState(etoileInfo?.tags.join(', ') ?? '')
  useEffect(() => {
    setTagsInput(etoileInfo?.tags.join(', ') ?? '')
  }, [etoileInfo?.tags])

  if (isPending) {
    return (
      <SectionCard title="Shopify 실시간 정보">
        <div className="space-y-2">
          <div className="h-5 w-48 bg-muted animate-pulse rounded" />
          <div className="h-5 w-48 bg-muted animate-pulse rounded" />
        </div>
      </SectionCard>
    )
  }

  if (isError || !data) {
    return (
      <SectionCard title="Shopify 실시간 정보">
        <p className="text-sm text-muted-foreground">실시간 정보를 불러올 수 없습니다.</p>
      </SectionCard>
    )
  }

  const stores: Array<{
    label: string
    info: ShopifyStoreInfo
    mutation: ReturnType<typeof useUpdateShopifyStatus>
    showTags?: boolean
    showImageCount?: boolean
  }> = [
    { label: 'GIMSSINE', info: data.booksen, mutation: booksenMutation },
    ...(data.etoile.registered
      ? [{ label: 'ETOILE', info: data.etoile, mutation: etoileMutation, showTags: !!etoileInfo, showImageCount: true }]
      : []),
  ]

  return (
    <SectionCard title="Shopify 실시간 정보">
      <div className="space-y-4">
        {stores.map(({ label, info, mutation, showTags, showImageCount }) => (
          <div key={label} className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {label}
            </p>
            <div className="flex items-center gap-3 flex-wrap">
              <ShopifyStoreBadge info={info} />
              {info.registered && (
                <span className="text-sm text-muted-foreground">
                  {info.weight != null
                    ? `${info.weight} ${info.weight_unit ?? ''}`
                    : '중량 없음'}
                </span>
              )}
              {info.registered && (
                <span className="text-sm text-muted-foreground">
                  {info.price != null ? `$${info.price}` : '-'}
                </span>
              )}
              {info.registered && showImageCount && (
                <span className="text-sm text-muted-foreground">
                  Preview {info.image_count != null ? `${info.image_count}개` : '-'}
                </span>
              )}
              {info.registered && (
                <div className="ml-auto flex gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => mutation.mutate('active')}
                    disabled={mutation.isPending}
                  >
                    Active로 변경
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => mutation.mutate('draft')}
                    disabled={mutation.isPending}
                  >
                    Draft로 변경
                  </Button>
                </div>
              )}
            </div>
            {info.error && (
              <p className="text-xs text-destructive">{info.error}</p>
            )}
            {showTags && (
              <div className="flex gap-2 pt-1">
                <Input
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="tag1, tag2, tag3"
                  className="flex-1 h-8 text-sm"
                />
                <Button
                  size="sm"
                  onClick={() =>
                    tagsMutation.mutate(
                      tagsInput.split(',').map((t) => t.trim()).filter(Boolean),
                    )
                  }
                  disabled={tagsMutation.isPending}
                >
                  {tagsMutation.isPending ? '저장 중...' : '태그 저장'}
                </Button>
              </div>
            )}
          </div>
        ))}
      </div>
    </SectionCard>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

// @MX:ANCHOR: [AUTO] BookDetailPage is the top-level route component for /books/:id
// @MX:REASON: Fan-in >= 3 — router lazy import, BookSearchPage row click, and direct URL entry all reach this component
export function BookDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const bookId = id ? Number(id) : undefined

  const { data, isPending, isError, error } = useBookDetail(bookId)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/books/search')}
          aria-label="목록으로 돌아가기"
        >
          ← 목록
        </Button>
        <h1 className="text-xl font-semibold">도서 정보 수정</h1>
        {data && (
          <span className="text-sm text-muted-foreground font-mono">{data.inven_SKU}</span>
        )}
        {data && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground font-mono">
            {data.status_of_shopify} · {STATUS_LABELS[data.status_of_shopify] ?? '-'}
          </span>
        )}
      </div>

      {/* Loading */}
      {isPending && <LoadingSkeleton />}

      {/* Error */}
      {isError && (
        <div className="rounded-lg border border-destructive/50 p-6 text-center" role="alert">
          <p className="text-destructive font-medium">도서 정보를 불러오는데 실패했습니다.</p>
          {error instanceof Error && (
            <p className="text-sm text-muted-foreground mt-1">{error.message}</p>
          )}
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => navigate('/books/search')}
          >
            목록으로 돌아가기
          </Button>
        </div>
      )}

      {/* Content */}
      {data && (
        <div className="space-y-6">
          {/* Row 1: 기본 정보(좌) + Shopify 상태·Etoile·노트(우) */}
          <div className="grid grid-cols-3 gap-6 items-start">
            <div className="col-span-2">
              <BasicInfoSection info={data.info} bookId={data.id} />
            </div>
            <div className="space-y-6">
              <ShopifyLiveInfoSection bookId={data.id} etoileInfo={data.etoile?.info ?? null} />
              <WeightSection info={data.info} bookId={data.id} />
              <NotesSection notes={data.notes} bookId={data.id} />
            </div>
          </div>

          {/* Row 2: 카테고리 2열 */}
          <div className="grid grid-cols-2 gap-6 items-start">
            <BooksenCategorySection info={data.info} bookId={data.id} />
            <KyboCategorySection info={data.info} bookId={data.id} />
          </div>

          {/* Row 3: 장문 텍스트 (전체 폭) */}
          <LongTextSection info={data.info} bookId={data.id} />
        </div>
      )}
    </div>
  )
}
