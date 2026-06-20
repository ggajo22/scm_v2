---
id: SPEC-BOOK-EDIT-001
version: "0.1.0"
status: draft
created: "2026-06-20"
updated: "2026-06-20"
author: ggajo
---

## 구현 계획

### 기술 접근 방법

#### 백엔드 (Django REST Framework)

기존 `backend/book/views.py`에 신규 ViewSet 및 APIView를 추가하는 방식으로 구현한다.
레거시 `UpdateBookInfoView`의 비즈니스 로직을 참조하되, DRF Serializer + APIView 패턴으로 재작성한다.

**핵심 설계 결정**:
- `BookDetailView` (RetrieveAPIView): `GET /api/book/{id}/` — 단일 도서 전체 컨텍스트 조회
- `BookInfoUpdateView` (UpdateAPIView, partial=True): `PATCH /api/book/{id}/info/`
- `BookNoteListCreateView` (ListCreateAPIView): `POST /api/book/{id}/notes/`
- `BookNoteResolveView` (APIView): `PATCH /api/book/notes/{note_id}/resolve/`
- `BookShopifyStatusView` (APIView): `PATCH /api/book/{id}/shopify-status/`
- `EtoileShopifyStatusView` (APIView): `PATCH /api/book/{id}/etoile-shopify-status/`
- `EtoileTagsView` (APIView): `PATCH /api/book/{id}/etoile-tags/`

**Serializer 구성**:
- `BookDetailSerializer` (기존 확장 또는 신규): Inven + Info + Notes + Shopify + Etoile 중첩 직렬화
- `InfoUpdateSerializer`: partial=True, 수정 가능 필드만 포함
- `BookNoteSerializer`: 노트 생성/조회
- `ShopifyStatusSerializer`: action 필드 유효성 검증

#### 프론트엔드 (React + TypeScript)

- `BookDetailPage.tsx`: `/book/:id/edit` 라우트에 마운트되는 페이지 컴포넌트
- `useBookDetail.ts`: 도서 상세 조회 훅 (`GET /api/book/{id}/`)
- `useBookInfoUpdate.ts`: Info 수정 mutation 훅
- `useBookNotes.ts`: 노트 생성/해결 훅
- `useShopifyStatus.ts`: Shopify 상태 변경 훅
- `useEtoileTags.ts`: 에투알 태그 관리 훅
- `BookSearchPage.tsx` 수정: 도서 행 클릭 시 `/book/:id/edit`으로 라우팅 추가

shadcn/ui 컴포넌트 활용:
- `Tabs`: 섹션 그룹 구분
- `Button`, `Input`, `Label`, `Select`: 폼 필드
- `Badge`: 노트 타입, Shopify 상태 표시
- `Dialog` (또는 `Sheet`): 노트 추가 폼
- `toast` (sonner): 저장 성공/실패 피드백

---

### 마일스톤

#### Priority High (핵심 기능)

1. **백엔드 기반 구조**
   - `BookDetailSerializer` 작성 (Inven + Info + Notes + Shopify + Etoile 중첩)
   - `GET /api/book/{id}/` 엔드포인트 구현
   - `PATCH /api/book/{id}/info/` 엔드포인트 구현
   - URL 라우팅 등록

2. **프론트엔드 기반 구조**
   - `/book/:id/edit` 라우트 추가
   - `useBookDetail.ts` 훅 구현
   - `BookDetailPage.tsx` 기본 레이아웃 (탭 구조)
   - `BookSearchPage.tsx` 클릭 이벤트 → 라우팅 연결

3. **Info 수정 폼**
   - 필드 그룹별 폼 섹션 구현
   - 저장 버튼 및 성공/실패 피드백

#### Priority Medium (운영 필수 기능)

4. **노트 관리**
   - `POST /api/book/{id}/notes/` 구현
   - `PATCH /api/book/notes/{note_id}/resolve/` 구현
   - 프론트엔드 노트 패널 (목록 + 추가 폼 + 해결 버튼)

5. **Shopify 상태 변경**
   - `PATCH /api/book/{id}/shopify-status/` 구현 (Shopify API 연동)
   - `PATCH /api/book/{id}/etoile-shopify-status/` 구현
   - 프론트엔드 Shopify 상태 패널

#### Priority Low (부가 기능)

6. **에투알 태그 관리**
   - `PATCH /api/book/{id}/etoile-tags/` 구현 (DB 저장 + Shopify 동기화)
   - 프론트엔드 에투알 섹션 (조건부 렌더링)

---

### 위험 요소

| 위험 | 영향 | 대응 방안 |
|------|------|-----------|
| Shopify API 외부 의존성 | 상태 변경 기능 차단 | mock/stub으로 단위 테스트, 통합 테스트에서 실제 API 사용 |
| `BookDetailSerializer` 중첩 쿼리 N+1 | 응답 지연 | `select_related` / `prefetch_related` 적용 필수 |
| 레거시 필드명 불일치 | Info 수정 오류 | 실제 DB 스키마와 serializer 필드명 대조 검증 |
| EtoileBookInven 미존재 도서 | 에투알 섹션 오류 | null-safe 처리, 프론트엔드 조건부 렌더링 |

---

### 기존 코드 영향 범위

| 파일 | 변경 유형 | 이유 |
|------|-----------|------|
| `backend/book/views.py` | 추가 | 신규 View 클래스 추가 |
| `backend/book/serializers.py` | 추가/수정 | BookDetail, InfoUpdate, BookNote Serializer |
| `backend/book/urls.py` | 추가 | 신규 URL 패턴 등록 |
| `frontend/src/features/book/` | 추가 | 훅 및 컴포넌트 추가 |
| `frontend/src/pages/` | 추가/수정 | BookDetailPage 신규, BookSearchPage 클릭 핸들러 추가 |
| `frontend/src/router/index.tsx` | 수정 | `/book/:id/edit` 라우트 추가 |
