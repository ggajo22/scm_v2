# SPEC-ORDER-010 Compact

## 요구사항

- REQ-LIN-001: `orders_line_item_note` 테이블 생성 (line_item FK, content, author FK nullable, created_at, is_resolved, assignee enum)
- REQ-LIN-002: 기존 `orders_line_item.note` 데이터를 새 테이블로 마이그레이션 후 컬럼 제거
- REQ-LIN-003: `POST /api/orders/line-items/<pk>/notes/` — 노트 생성 (author=request.user 자동)
- REQ-LIN-004: `GET /api/orders/line-items/<pk>/notes/` — line_item별 노트 목록 (역순)
- REQ-LIN-005: `GET /api/orders/line-item-notes/` — 전체 미해결 노트 목록 (pagination 없음)
- REQ-LIN-006: `PATCH /api/orders/line-item-notes/<pk>/resolve/` — is_resolved=True 처리
- REQ-LIN-007: `GET /api/orders/<pk>/` 응답에 `line_items[].notes[]` 포함 (N+1 방지 prefetch)
- REQ-LIN-008: OrderDetailPage line_item 행 인라인 노트 UI (배지 + 확장 패널 + 입력 폼)
- REQ-LIN-009: LineItemNotesPage 전용 페이지 (`/line-item-notes`, 카드 목록 + 해결 버튼)

## 인수 기준 요약

- POST notes → 201, DB 저장 확인
- PATCH resolve → 200 + is_resolved:true, 전체 목록에서 제거 확인
- GET line-item-notes → 미해결만 반환
- GET /orders/<pk>/ → line_items[].notes 포함, N+1 없음
- 데이터 마이그레이션 → 기존 note 값 이전, 컬럼 제거 확인
- 미인증 → HTTP 401
- OrderDetailPage 인라인 노트 UI 동작 확인
- LineItemNotesPage optimistic 해결 확인

## 제외

- 노트 수정/삭제 API
- assignee 필터링
- 실시간 알림
- Order 레벨 note 변경
