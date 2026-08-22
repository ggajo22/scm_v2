---
id: SPEC-BOOK-SEARCH-001
version: "1.1.0"
status: completed
created: "2026-06-19"
updated: "2026-08-21"
author: ggajo
priority: medium
issue_number: 0
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-19 | ggajo | 최초 작성 — ISBN 및 제목 부분 검색 기능 SPEC |
| 1.0.1 | 2026-06-19 | ggajo | 구현 완료 — TDD 방식으로 백엔드/프론트엔드 전체 구현, 18/18 테스트 통과 |
| 1.0.2 | 2026-06-19 | ggajo | 레이아웃 개선 — BookLayout 도입, 도서 관련 URL 상단 고정 검색바, Sidebar 도서 관리 메뉴 추가 |
| 1.0.3 | 2026-06-20 | ggajo | UX 개선 — FULLTEXT AND 검색(정확도), ISBN 즉시검색, 검색 후 입력창 초기화, 검색결과 헤더 표시 |
| 1.0.4 | 2026-08-21 | ggajo | 성능 수정 — ISBN 즉시검색(0ms) 철회하고 250ms 디바운스 적용, 요청 취소(AbortSignal) 연결, `__startswith`(LIKE BINARY, 인덱스 미사용) → `__istartswith`. REQ-SEARCH-009 본문을 실제 동작과 일치시킴(1.0.3에서 HISTORY만 갱신되고 요구사항 본문은 300ms로 남아 있던 불일치 해소) |
| 1.1.0 | 2026-08-21 | ggajo | 결과 표시 항목 변경 — 판매가 제거(응답 필드 포함), 표지 썸네일 및 ETOILE 리스팅 상태 추가 (REQ-SEARCH-011 개정, REQ-SEARCH-018·019 신설, REQ-SEARCH-008 확장) |

---

## 개요

SCM v2 어드민 앱에서 도서 검색 기능을 제공한다. 관리자는 ISBN(inven_SKU) 또는 도서 제목(info.name) 일부로 도서를 검색하고, 페이지네이션된 결과를 테이블 형태로 조회할 수 있다.

---

## 배경 및 동기

현재 도서 대시보드(SPEC-BOOK-DASHBOARD-001)는 집계 지표만 제공하며, 특정 도서를 ISBN이나 제목으로 찾는 기능이 없다. 관리자가 특정 재고 항목을 조회하거나 Shopify 상태를 확인하려면 직접 DB 쿼리를 실행해야 하는 불편함이 있다.

---

## 요구사항 (EARS 형식)

### 핵심 검색 동작

**REQ-SEARCH-001**: `WHERE` 검색어(search 파라미터)가 제공된 경우, 시스템은 `Inven.inven_SKU` 및 `Info.name` 필드에 대해 OR 조건 icontains 검색을 수행하여야 한다.

**REQ-SEARCH-002**: `WHEN` search 파라미터가 비어 있거나 없는 경우, 시스템은 모든 도서를 페이지네이션하여 반환하여야 한다.

**REQ-SEARCH-003**: 시스템은 모든 도서 검색 엔드포인트에 대해 유효한 JWT 인증을 요구하여야 한다 (`IsAuthenticated`).

**REQ-SEARCH-004**: 시스템은 데이터베이스 마이그레이션을 통해 `Info.name` 필드에 인덱스를 추가하여야 한다.

**REQ-SEARCH-005**: 시스템은 검색 결과를 페이지당 50건으로 페이지네이션하여 반환하여야 한다 (`PageNumberPagination`, `PAGE_SIZE=50`).

**REQ-SEARCH-006**: `WHEN` 인증되지 않은 요청이 도서 검색 엔드포인트에 도달하는 경우, 시스템은 HTTP 401 Unauthorized를 반환하여야 한다.

**REQ-SEARCH-007**: 시스템은 검색 결과 응답에 `count`, `next`, `previous`, `results` 필드를 포함한 표준 DRF 페이지네이션 구조를 반환하여야 한다.

**REQ-SEARCH-008**: 시스템은 `Inven.objects.select_related('info', 'etoile_inven')` 쿼리를 사용하여 N+1 쿼리 문제를 방지하여야 한다.

### 프론트엔드 요구사항

**REQ-SEARCH-009**: `WHEN` 사용자가 검색 입력란에 2자 이상을 입력하는 경우, 시스템은 디바운스 후 검색 API를 호출하여야 한다. 디바운스 시간은 입력이 숫자만으로 구성된 경우(ISBN 경로) 250ms, 그 외(텍스트 경로) 300ms로 한다.

**REQ-SEARCH-009a**: `WHEN` 디바운스 대기 중 새 검색어가 확정되는 경우, 시스템은 직전에 전송된 검색 요청을 취소하여야 한다 (`AbortSignal`).

**REQ-SEARCH-009b**: `WHEN` 완성된 검색어가 이미 확정된 상태로 컴포넌트에 전달되는 경우(URL 직접 진입, 붙여넣기, 바코드 스캐너), 시스템은 디바운스 대기 없이 즉시 검색 API를 호출하여야 한다.

**REQ-SEARCH-016**: 시스템은 `/books` 경로 및 모든 하위 도서 관련 URL에서 검색 입력란을 페이지 상단에 항상 표시하여야 한다 (`BookLayout` 공유 레이아웃).

**REQ-SEARCH-017**: 시스템은 사이드바 내비게이션에 도서 관리(`/books`) 메뉴 항목을 표시하여야 한다.

**REQ-SEARCH-010**: `WHEN` 사용자가 검색 입력란에 1자 이하를 입력하는 경우, 시스템은 API 호출을 수행하지 않아야 한다.

**REQ-SEARCH-011**: 시스템은 검색 결과 테이블에 표지 썸네일(`cover_image_url`), ISBN(`inven_SKU`), 도서 제목(`name`), ETOILE 리스팅 상태(`etoile_status_label`), Shopify 상태(`status_of_shopify`) 열을 표시하여야 한다. 판매가(`price_sale`)는 표시하지 않으며 검색 응답 필드에도 포함하지 않는다.

**REQ-SEARCH-018**: 시스템은 `etoile_book_inven.status_of_shopify` 가 `80`(리스팅 완료)인 경우에만 ETOILE 리스팅됨(`etoile_listed: true`)으로 판정하여야 한다. ETOILE 레코드가 없으면 `"미등록"`, 상태값이 `NULL`이면 `"상태 없음"`, 그 외 정의되지 않은 코드는 `"정의되지 않은 상태"`를 상태 문구로 반환한다.

**REQ-SEARCH-019**: `WHEN` 표지 이미지 URL이 비어 있거나 이미지 로드에 실패하는 경우, 시스템은 깨진 이미지 대신 중립 플레이스홀더를 표시하여야 한다.

**REQ-SEARCH-012**: `WHEN` API 응답이 로딩 중인 경우, 시스템은 로딩 상태 UI를 표시하여야 한다.

**REQ-SEARCH-013**: `WHEN` API 요청이 실패하는 경우, 시스템은 에러 메시지를 표시하여야 한다.

**REQ-SEARCH-014**: `WHEN` 검색 결과가 없는 경우, 시스템은 빈 상태(empty state) 메시지를 표시하여야 한다.

**REQ-SEARCH-015**: 시스템은 페이지네이션 컨트롤(이전/다음)을 제공하여야 한다.

---

## 델타 마커 (브라운필드 변경 대상)

| 마커 | 대상 | 설명 |
|------|------|------|
| [EXISTING] | `backend/book/models.py` | `Inven`, `Info` 모델 — 구조 변경 없음, 특성화 테스트만 작성 |
| [MODIFY] | `backend/book/views.py` | `BookListViewSet` (ReadOnlyModelViewSet) 추가 |
| [MODIFY] | `backend/book/urls.py` | 검색 엔드포인트 URL 추가 |
| [MODIFY] | `backend/book/serializers.py` | `InvenSerializer`, `BookDetailSerializer` 추가 |
| [MODIFY] | `backend/config/settings/base.py` | `DEFAULT_PAGINATION_CLASS`, `PAGE_SIZE` 설정 추가 |
| [NEW] | `backend/book/migrations/000X_add_info_name_index.py` | `Info.name` 인덱스 추가 마이그레이션 |
| [NEW] | `backend/book/tests/test_book_search.py` | 검색 API 테스트 |
| [NEW] | `frontend/src/features/book/hooks/useBookSearch.ts` | TanStack Query 검색 훅 |
| [NEW] | `frontend/src/pages/BookSearchPage.tsx` | 도서 검색 페이지 컴포넌트 |
| [NEW] | `frontend/src/types/book.ts` | 도서 관련 TypeScript 타입 정의 |
| [NEW] | `frontend/src/features/book/BookLayout.tsx` | 도서 관련 URL 공유 레이아웃 (검색바 상단 고정) |
| [MODIFY] | `frontend/src/components/Sidebar.tsx` | 도서 관리 메뉴 항목 추가 |
| [MODIFY] | `frontend/src/router/index.tsx` | /books 라우트를 BookLayout으로 래핑 |

---

## 비기능 요구사항

- **성능**: 검색 응답 시간 P95 < 500ms (인덱스 추가 후 기준)
  - 실측 (2026-08-21, 운영 DB 63만 행, 13자리 ISBN, best-of-3): 요청 1건 **295ms** — 충족
  - `__startswith`는 MySQL에서 `LIKE BINARY`로 컴파일되어 `inven_SKU` 인덱스를 사용할 수 없다 (EXPLAIN `key=PRIMARY`). ISBN 경로는 반드시 `__istartswith`를 사용한다 — `backend/book/views.py` `BookListViewSet.get_queryset`
  - 디바운스 없이 매 키 입력마다 요청하면 13자리 ISBN 입력 시 요청 12건 / 약 5.5초의 서버 작업이 발생한다. REQ-SEARCH-009의 디바운스는 UX가 아니라 성능 요구사항이다
- **인증**: 모든 엔드포인트 IsAuthenticated 적용 — SPEC-AUTH-001 패턴 준수
- **N+1 방지**: select_related('info', 'etoile_inven') 필수 사용 — ETOILE 상태를 행마다 조회하면 50건 페이지에서 왕복 50회가 추가된다
- **DB 마이그레이션**: Info.name 인덱스 추가는 데이터 락 최소화 방식 적용 권장

---

## 제외 범위 (What NOT to Build)

- **도서 생성/수정/삭제**: 읽기 전용 검색만 구현 (CRUD는 향후 별도 SPEC)
- **고급 필터**: 가격 범위 필터, 상태 필터 등 — 향후 범위
- **Shopify 동기화**: 이 기능에서 Shopify 동기화 트리거 없음
- **MySQL FULLTEXT 검색**: 단순 icontains로 충분, FULLTEXT 불필요
- **도서 상세 페이지**: 검색 결과 목록만 제공, 상세 페이지 없음
- **내보내기/다운로드**: CSV, Excel 등 내보내기 기능 없음
- **실시간 검색 자동완성**: 디바운스 방식 사용, 자동완성 드롭다운 없음

---

## 구현 완료 노트

### 구현 방식
- 개발 방법론: TDD (RED-GREEN-REFACTOR)
- 백엔드: DRF `SearchFilter` (내장, 추가 의존성 없음)
- 검색 필드: `['inven_SKU', 'info__name']` — OR 조건 자동 처리
- 쿼리 최적화: `select_related('info', 'etoile_inven')` — N+1 방지 확인 (v1.1.0에서 `etoile_inven` 추가)
- 페이지네이션: `PageNumberPagination`, PAGE_SIZE=50

### 구현된 파일
- [MODIFY] backend/book/views.py — BookListViewSet 추가
- [MODIFY] backend/book/urls.py — GET /api/book/search/ 등록
- [MODIFY] backend/book/serializers.py — BookDetailSerializer 추가
- [MODIFY] backend/config/settings/base.py — 페이지네이션 설정
- [NEW] backend/book/migrations/0002_add_info_name_index.py
- [NEW] backend/book/tests/test_book_search.py — 13개 테스트
- [NEW] frontend/src/features/book/hooks/useBookSearch.ts
- [NEW] frontend/src/pages/BookSearchPage.tsx
- [NEW] frontend/src/types/book.ts
- [NEW] frontend/src/features/book/BookLayout.tsx — 도서 URL 공유 레이아웃, 검색바 상단 고정
- [MODIFY] frontend/src/components/Sidebar.tsx — 도서 관리 메뉴(BookOpen 아이콘) 추가
- [MODIFY] frontend/src/router/index.tsx — /books 라우트를 BookLayout children으로 재구성

### 테스트 결과
- 신규 테스트: 13/13 PASS
- 기존 회귀 없음: 5/5 PASS (DashboardMetrics)
- 전체: 18/18 PASS
