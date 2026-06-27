---
id: SPEC-ORDER-010
version: "1.0.0"
status: draft
created: 2026-06-27
updated: 2026-06-27
author: ggajo
priority: high
issue_number: 0
---

## HISTORY

| 버전  | 날짜       | 작성자 | 변경 내용                                                      |
|-------|------------|--------|----------------------------------------------------------------|
| 1.0.0 | 2026-06-27 | ggajo  | 최초 작성 — line_item 다중 노트(LineItemNote) 모델 및 UI 구현 |

---

# SPEC-ORDER-010: Line Item 다중 노트 기능

## 개요

현재 `orders_line_item` 테이블의 단일 `note` TextField를 별도 `LineItemNote` 테이블로 분리하여, 하나의 line_item에 여러 노트를 추가할 수 있도록 한다.

각 노트는 **내용, 작성자, 작성시각, 해결여부, 대상자(담당부서)**를 포함한다.

대상자(assignee) 값: `CS` / `발주` / `한국창고` / `미국창고`

기존 `orders_line_item.note` 데이터는 새 테이블로 마이그레이션 후 컬럼을 제거한다.

## UI 제공 범위

1. **OrderDetailPage 인라인**: 각 line_item 행에서 노트 목록 표시 및 추가
2. **LineItemNotesPage (전용 페이지)**: 전체 미해결 line_item 노트 목록 (OrderNotesPage 패턴 재사용)

---

## 요구사항 (EARS Format)

### REQ-LIN-001: LineItemNote 모델

WHEN 시스템이 초기화될 때,  
THE SYSTEM SHALL `orders_line_item_note` 테이블을 생성하여  
각 노트가 `line_item(FK)`, `content(TextField)`, `author(FK→AdminUser, nullable)`,  
`created_at(auto_now_add)`, `is_resolved(BooleanField, default=False)`,  
`assignee(CharField, choices: CS/발주/한국창고/미국창고)` 필드를 갖도록 한다.

### REQ-LIN-002: 기존 데이터 마이그레이션

WHEN 마이그레이션이 실행될 때,  
THE SYSTEM SHALL 기존 `orders_line_item.note` 컬럼의 비어있지 않은 값을  
새 `LineItemNote` 레코드로 이전하고,  
이전 완료 후 `orders_line_item.note` 컬럼을 제거한다.

### REQ-LIN-003: 노트 생성 API

WHILE 인증된 사용자가 접근할 때,  
THE SYSTEM SHALL `POST /api/orders/line-items/<line_item_pk>/notes/` 엔드포인트를 제공하여  
`content`, `assignee` 필드로 노트를 생성하고,  
`author`는 `request.user`로 자동 설정한다.

### REQ-LIN-004: line_item별 노트 목록 API

WHILE 인증된 사용자가 접근할 때,  
THE SYSTEM SHALL `GET /api/orders/line-items/<line_item_pk>/notes/` 엔드포인트를 제공하여  
해당 line_item의 모든 노트를 `created_at` 역순으로 반환한다.

### REQ-LIN-005: 전체 미해결 노트 목록 API

WHILE 인증된 사용자가 접근할 때,  
THE SYSTEM SHALL `GET /api/orders/line-item-notes/` 엔드포인트를 제공하여  
`is_resolved=False`인 모든 LineItemNote를  
관련 line_item, order 정보와 함께 반환한다. (pagination 없음)

### REQ-LIN-006: 노트 해결 처리 API

WHILE 인증된 사용자가 접근할 때,  
THE SYSTEM SHALL `PATCH /api/orders/line-item-notes/<pk>/resolve/` 엔드포인트를 제공하여  
`is_resolved=True`로 설정하고 `{"is_resolved": true}`를 반환한다.

### REQ-LIN-007: OrderDetail API 응답에 노트 포함

WHEN `GET /api/orders/<pk>/` 요청이 올 때,  
THE SYSTEM SHALL `line_items` 배열 각 항목에  
`notes: LineItemNote[]` 필드를 포함시킨다.  
N+1 방지를 위해 `prefetch_related("line_items__notes")` 사용.

### REQ-LIN-008: OrderDetailPage 인라인 노트 UI

WHEN 사용자가 OrderDetailPage에서 line_item 행을 확인할 때,  
THE SYSTEM SHALL 각 line_item 행에 노트 수 표시 배지와  
클릭 시 해당 line_item의 노트 목록 및 추가 폼을 표시한다.

### REQ-LIN-009: LineItemNotesPage 전용 페이지

WHEN 사용자가 LineItemNotesPage에 접근할 때,  
THE SYSTEM SHALL 전체 미해결 line_item 노트를 카드 형식으로 표시하고  
각 카드에 "해결" 버튼을 제공한다. (OrderNotesPage 패턴 재사용)

---

## 제외 범위 (What NOT to Build)

- 노트 수정(PATCH content) 기능 — 조회 및 해결만 지원
- 노트 삭제 기능 — 해결 처리로 대체
- 노트 assignee 필터링 API — 초기 버전에선 전체 목록만 제공
- 실시간 알림(WebSocket) — 페이지 진입 시 fetch로 충분
- Order 레벨 note(기존 `orders.note`, `note_resolved`) 변경 — 이 SPEC 범위 외

---

## 영향받는 파일

### [NEW] Backend
- `backend/order/models.py` — LineItemNote 모델 추가
- `backend/order/migrations/NNNN_create_line_item_note.py` — 스키마 마이그레이션
- `backend/order/migrations/NNNN_backfill_line_item_notes.py` — 데이터 마이그레이션
- `backend/order/migrations/NNNN_remove_line_item_note_column.py` — 컬럼 제거 마이그레이션
- `backend/order/serializers.py` — LineItemNoteSerializer, LineItemDetailSerializer 업데이트
- `backend/order/views.py` — LineItemNoteListCreateView, LineItemNoteUnresolvedListView, LineItemNoteResolveView
- `backend/order/urls.py` — 3개 신규 라우트 추가

### [NEW] Frontend
- `frontend/src/types/order.ts` — LineItemNote 인터페이스 추가, LineItemDetail 업데이트
- `frontend/src/features/order/hooks/useLineItemNotes.ts` — React Query 훅 (목록, 생성, 해결)
- `frontend/src/pages/LineItemNotesPage.tsx` — 전용 노트 페이지 (OrderNotesPage 패턴)
- `frontend/src/router/index.tsx` — 신규 라우트 추가

### [MODIFY] Frontend
- `frontend/src/pages/OrderDetailPage.tsx` — line_item 행 인라인 노트 UI 추가
- `frontend/src/components/Sidebar.tsx` — LineItemNotesPage 네비 메뉴 추가

---

## Delta Markers (Brownfield)

### [DELTA] Backend Order App
- [EXISTING] `LineItem` 모델 — 변경 없음 (note 컬럼 제거 외)
- [MODIFY] `LineItem.note` 컬럼 — 마이그레이션으로 제거 (데이터 이전 후)
- [MODIFY] `OrderDetailSerializer` — `line_items` 직렬화에 `notes` 중첩 추가
- [MODIFY] `OrderDetailView` — `prefetch_related` 체인에 `line_items__notes` 추가
- [NEW] `LineItemNote` 모델, `LineItemNoteSerializer`, 3개 신규 뷰/URL

### [DELTA] Frontend
- [EXISTING] `OrderDetailPage` 테이블 구조 — 컬럼 순서 유지, 노트 UI만 추가
- [EXISTING] `OrderNotesPage` — 참조용 패턴, 수정 없음
- [NEW] `LineItemNotesPage`, `useLineItemNotes`, `LineItemNote` 타입

---

## mx_plan

### MX:ANCHOR 후보
- `LineItemNoteListCreateView` — fan_in >= 3 예상 (OrderDetailPage, LineItemNotesPage, resolve hook)
- `useLineItemNotes` 쿼리 키 — 다중 컴포넌트에서 공유

### MX:WARN 후보
- `OrderDetailView` queryset — `prefetch_related` 체인 변경 시 N+1 위험
- 데이터 마이그레이션 — 기존 note 데이터 유실 방지 필요

### MX:NOTE 후보
- `ASSIGNEE_CHOICES` 상수 — 비즈니스 도메인 열거값 (CS, 발주, 한국창고, 미국창고)
