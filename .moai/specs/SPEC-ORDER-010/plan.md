# SPEC-ORDER-010 구현 계획

## 기술 스택

- Backend: Django 4.x + DRF, Python 3.12
- Frontend: React + TypeScript + TanStack Query v5
- DB: SQLite (개발), PostgreSQL 호환

---

## 구현 순서

### Phase 1: Backend 모델 및 마이그레이션

**1-1. LineItemNote 모델 추가** (`backend/order/models.py`)

```python
ASSIGNEE_CHOICES = [
    ("CS", "CS"),
    ("발주", "발주"),
    ("한국창고", "한국창고"),
    ("미국창고", "미국창고"),
]

class LineItemNote(models.Model):
    line_item = models.ForeignKey(LineItem, on_delete=models.CASCADE, related_name="notes")
    content = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="line_item_notes"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    assignee = models.CharField(max_length=20, choices=ASSIGNEE_CHOICES, default="CS")

    class Meta:
        db_table = "orders_line_item_note"
        ordering = ["-created_at"]
```

**1-2. 마이그레이션 3단계**

Migration 1 (스키마): `CREATE TABLE orders_line_item_note`
Migration 2 (데이터): `INSERT INTO ... SELECT ... FROM orders_line_item WHERE note IS NOT NULL AND note != ''`
Migration 3 (컬럼 제거): `ALTER TABLE orders_line_item DROP COLUMN note`

데이터 마이그레이션 시 author=NULL, assignee='CS', is_resolved=False로 설정.

### Phase 2: Backend Serializers & Views

**2-1. Serializers** (`backend/order/serializers.py`)

```python
class LineItemNoteSerializer(ModelSerializer):
    author_name = SerializerMethodField()

    def get_author_name(self, obj):
        return obj.author.get_full_name() if obj.author else None

    class Meta:
        model = LineItemNote
        fields = ["id", "content", "author_name", "assignee", "created_at", "is_resolved"]
        read_only_fields = ["id", "author_name", "created_at", "is_resolved"]
```

`LineItemDetailSerializer`에 `notes = LineItemNoteSerializer(many=True, read_only=True)` 추가.

**2-2. Views** (`backend/order/views.py`)

```
LineItemNoteListCreateView   GET/POST /api/orders/line-items/<pk>/notes/
LineItemNoteUnresolvedList   GET      /api/orders/line-item-notes/
LineItemNoteResolveView      PATCH    /api/orders/line-item-notes/<pk>/resolve/
```

`OrderDetailView` queryset: `.prefetch_related("line_items", "line_items__notes")` 추가.

**2-3. URLs** (`backend/order/urls.py`)

```python
path("line-items/<int:pk>/notes/", LineItemNoteListCreateView.as_view()),
path("line-item-notes/", LineItemNoteUnresolvedList.as_view()),
path("line-item-notes/<int:pk>/resolve/", LineItemNoteResolveView.as_view()),
```

### Phase 3: Frontend Types & Hooks

**3-1. Types** (`frontend/src/types/order.ts`)

```typescript
export interface LineItemNote {
  id: number
  content: string
  author_name: string | null
  assignee: 'CS' | '발주' | '한국창고' | '미국창고'
  created_at: string
  is_resolved: boolean
}
```

`LineItemDetail` 인터페이스에 `notes: LineItemNote[]` 추가.

**3-2. React Query Hook** (`frontend/src/features/order/hooks/useLineItemNotes.ts`)

- `useLineItemNotes(lineItemId)` — GET notes list
- `useCreateLineItemNote()` — POST new note (invalidate order-detail query on success)
- `useResolveLineItemNote()` — PATCH resolve (optimistic update, 주문 상세 + 전체 미해결 invalidate)

### Phase 4: Frontend UI

**4-1. OrderDetailPage 인라인 노트**

line_item 행에 노트 수 배지(예: `[노트 2]`) 추가.  
클릭 시 해당 행 아래에 인라인 패널 확장:
- 기존 노트 목록 (content, author, assignee, created_at, 해결 버튼)
- 새 노트 입력 폼 (textarea + assignee 선택 select + 추가 버튼)

**4-2. LineItemNotesPage**

`/line-item-notes` 경로.  
OrderNotesPage 구조 동일하게 구현:
- 미해결 노트 카드 목록
- 각 카드: 주문번호, line_item 제목/SKU, assignee, 내용, 작성자, 작성시각
- "해결" 버튼 → optimistic remove

**4-3. Sidebar 메뉴 추가**

기존 "주문 노트" 항목 하단에 "품목 노트" 메뉴 추가.

---

## 참조 구현체

- `backend/order/views.py:144-175` — OrderNoteListView, OrderNoteResolveView (동일 패턴 적용)
- `frontend/src/features/order/hooks/useOrderNotes.ts` — optimistic update 패턴 재사용
- `frontend/src/pages/OrderNotesPage.tsx` — 카드 목록 레이아웃 재사용

---

## 의존성 / 리스크

| 항목 | 내용 | 대응 |
|------|------|------|
| N+1 쿼리 | OrderDetailView prefetch 체인 변경 | `prefetch_related("line_items__notes")` 적용 |
| 데이터 마이그레이션 | 기존 note 유실 위험 | 데이터 마이그레이션 먼저, 컬럼 제거는 별도 마이그레이션 |
| API 호환성 | `LineItemDetail.note` 필드 제거 | Frontend 동시 배포 필요 |
| author null | 기존 데이터 마이그레이션 시 author 없음 | `author` nullable 허용, UI에서 "알 수 없음" 처리 |
