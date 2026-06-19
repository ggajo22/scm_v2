# SPEC-BOOK-SEARCH-001 컴팩트 참조

## EARS 요구사항

**REQ-SEARCH-001**: `WHERE` 검색어(search 파라미터)가 제공된 경우, 시스템은 `Inven.inven_SKU` 및 `Info.name` 필드에 대해 OR 조건 icontains 검색을 수행하여야 한다.

**REQ-SEARCH-002**: `WHEN` search 파라미터가 비어 있거나 없는 경우, 시스템은 모든 도서를 페이지네이션하여 반환하여야 한다.

**REQ-SEARCH-003**: 시스템은 모든 도서 검색 엔드포인트에 대해 유효한 JWT 인증을 요구하여야 한다 (`IsAuthenticated`).

**REQ-SEARCH-004**: 시스템은 데이터베이스 마이그레이션을 통해 `Info.name` 필드에 인덱스를 추가하여야 한다.

**REQ-SEARCH-005**: 시스템은 검색 결과를 페이지당 50건으로 페이지네이션하여 반환하여야 한다 (`PageNumberPagination`, `PAGE_SIZE=50`).

**REQ-SEARCH-006**: `WHEN` 인증되지 않은 요청이 도서 검색 엔드포인트에 도달하는 경우, 시스템은 HTTP 401 Unauthorized를 반환하여야 한다.

**REQ-SEARCH-007**: 시스템은 검색 결과 응답에 `count`, `next`, `previous`, `results` 필드를 포함한 표준 DRF 페이지네이션 구조를 반환하여야 한다.

**REQ-SEARCH-008**: 시스템은 `Inven.objects.select_related('info')` 쿼리를 사용하여 N+1 쿼리 문제를 방지하여야 한다.

**REQ-SEARCH-009**: `WHEN` 사용자가 검색 입력란에 2자 이상을 입력하는 경우, 시스템은 300ms 디바운스 후 검색 API를 호출하여야 한다.

**REQ-SEARCH-010**: `WHEN` 사용자가 검색 입력란에 1자 이하를 입력하는 경우, 시스템은 API 호출을 수행하지 않아야 한다.

**REQ-SEARCH-011**: 시스템은 검색 결과 테이블에 ISBN(`inven_SKU`), 도서 제목(`name`), 판매가(`price_sale`), Shopify 상태(`status_of_shopify`) 열을 표시하여야 한다.

**REQ-SEARCH-012**: `WHEN` API 응답이 로딩 중인 경우, 시스템은 로딩 상태 UI를 표시하여야 한다.

**REQ-SEARCH-013**: `WHEN` API 요청이 실패하는 경우, 시스템은 에러 메시지를 표시하여야 한다.

**REQ-SEARCH-014**: `WHEN` 검색 결과가 없는 경우, 시스템은 빈 상태(empty state) 메시지를 표시하여야 한다.

**REQ-SEARCH-015**: 시스템은 페이지네이션 컨트롤(이전/다음)을 제공하여야 한다.

---

## 인수 시나리오 (Given/When/Then)

**시나리오 1 — ISBN 정확 검색**
- Given: 인증된 관리자, `inven_SKU="978-89-954321-0-5"` 도서 존재
- When: `GET /api/book/search/?search=978-89-954321-0-5`
- Then: 200, `results[0].inven_SKU == "978-89-954321-0-5"`, 페이지네이션 구조 존재

**시나리오 2 — 도서 제목 부분 검색**
- Given: 인증된 관리자, `info.name="파이썬 프로그래밍 입문"` 도서 존재
- When: `GET /api/book/search/?search=파이썬`
- Then: 200, `results[0].info.name`에 "파이썬" 포함

**시나리오 3 — OR 조건 복합 검색**
- Given: 도서 A (inven_SKU에 "123" 포함), 도서 B (info.name에 "123" 포함)
- When: `GET /api/book/search/?search=123`
- Then: 200, 도서 A와 도서 B 모두 results에 포함

**시나리오 4 — 미인증 요청 차단**
- Given: JWT 토큰 없음
- When: `GET /api/book/search/?search=test`
- Then: HTTP 401 Unauthorized

**시나리오 5 — 검색 결과 없음**
- Given: 인증된 관리자, 매칭 도서 없음
- When: `GET /api/book/search/?search=ZZZNOMATCH99999`
- Then: 200, `results == []`, `count == 0`

**시나리오 6 — 페이지네이션**
- Given: 인증된 관리자, DB에 100건 이상 도서 존재
- When: `GET /api/book/search/` (search 없음)
- Then: 200, `results` 최대 50건, `count`는 전체 수, `next` URL 존재, `previous == null`

**시나리오 7 — 프론트엔드 2자 미만 API 미호출**
- Given: 사용자가 `/books/search` 페이지에 있음
- When: 검색 입력란에 1자 입력
- Then: API 호출 없음, 로딩 스피너 없음

**시나리오 8 — 프론트엔드 디바운스**
- Given: 사용자가 `/books/search` 페이지에 있음
- When: 300ms 이내에 "파이썬" 빠르게 입력
- Then: 마지막 입력 후 300ms 경과 시 단 1회 API 호출

**시나리오 9 — 결과 테이블 열 확인**
- Given: 검색 결과 1건 이상 존재
- When: 결과 테이블 렌더링
- Then: ISBN, 도서 제목, 판매가, Shopify 상태 열 존재

**시나리오 10 — 에러 상태 처리**
- Given: 사용자가 검색어 입력, 백엔드 5xx 오류 발생
- When: API 응답 수신
- Then: 에러 메시지 표시, 페이지 크래시 없음

---

## 델타 마커 (변경 대상 파일)

| 마커 | 파일 |
|------|------|
| [EXISTING] | `backend/book/models.py` — 특성화 테스트만 작성 |
| [MODIFY] | `backend/book/views.py` — BookListViewSet 추가 |
| [MODIFY] | `backend/book/urls.py` — 검색 URL 추가 |
| [MODIFY] | `backend/book/serializers.py` — InvenSerializer, BookDetailSerializer 추가 |
| [MODIFY] | `backend/config/settings/base.py` — 페이지네이션 설정 추가 |
| [NEW] | `backend/book/migrations/000X_add_info_name_index.py` |
| [NEW] | `backend/book/tests/test_book_search.py` |
| [NEW] | `frontend/src/features/book/hooks/useBookSearch.ts` |
| [NEW] | `frontend/src/pages/BookSearchPage.tsx` |
| [NEW] | `frontend/src/types/book.ts` |

---

## 제외 범위

- 도서 생성/수정/삭제 (읽기 전용)
- 고급 필터 (가격 범위, 상태 필터)
- Shopify 동기화 트리거
- MySQL FULLTEXT 검색
- 도서 상세 페이지
- 내보내기/다운로드
- 실시간 자동완성 드롭다운
