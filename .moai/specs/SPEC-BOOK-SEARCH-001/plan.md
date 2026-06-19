# 구현 계획 — SPEC-BOOK-SEARCH-001

## 개요

도서 검색 기능을 백엔드(Django DRF)와 프론트엔드(React + TypeScript) 두 레이어로 나누어 순차 구현한다. 백엔드를 먼저 완료하여 API 계약을 확정한 후 프론트엔드를 개발한다.

---

## Phase 1: 백엔드 구현

### 단계 1-A: DB 마이그레이션 (우선순위 높음)

**대상 파일**: `backend/book/migrations/000X_add_info_name_index.py`

`Info.name` 필드에 B-Tree 인덱스를 추가하는 마이그레이션을 작성한다. 기존 데이터가 있는 테이블에 인덱스를 추가하는 작업이므로 락 최소화 방식(`ALGORITHM=INPLACE, LOCK=NONE`)을 고려한다.

참조: `Info` 모델의 기존 인덱스는 `price_sale`, `price` 필드에만 있으며 `name` 필드에는 없다.

### 단계 1-B: Serializer 작성 (우선순위 높음)

**대상 파일**: `backend/book/serializers.py`

작성할 Serializer:
- `InvenSerializer`: `Inven` 모델 기반, `info` 관계 포함 (nested)
- `BookDetailSerializer`: 검색 응답용, 반환 필드 — `inven_SKU`, `vendor`, `store`, `status_of_shopify`, `is_use` + nested `info` 필드 (`name`, `price_sale`, `price`, `qty`, `status`, `cover_image_url`)

설계 원칙: `depth` 옵션 대신 명시적 `SerializerMethodField` 또는 중첩 Serializer 사용 (직렬화 필드 명확화).

### 단계 1-C: ViewSet 및 URL 등록 (우선순위 높음)

**대상 파일**: `backend/book/views.py`, `backend/book/urls.py`

ViewSet 설계:
```
class BookListViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = BookDetailSerializer
    filter_backends = [SearchFilter]
    search_fields = ['inven_SKU', 'info__name']
    queryset = Inven.objects.select_related('info').all()
    pagination_class = BookPageNumberPagination  # 또는 전역 설정
```

URL 패턴:
- `GET /api/book/search/` — 검색 및 전체 목록 (search 파라미터 선택적)
- DRF Router 사용 또는 `path('search/', BookListViewSet.as_list())` 직접 등록

참조 패턴: `backend/book/views.py`의 `DashboardMetricsView` — `IsAuthenticated` 적용 방식

### 단계 1-D: 페이지네이션 설정 (우선순위 높음)

**대상 파일**: `backend/config/settings/base.py`

추가 설정:
```python
REST_FRAMEWORK = {
    ...existing settings...,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
```

주의: 전역 페이지네이션 설정이 기존 `DashboardMetricsView`에 영향을 주지 않는지 확인 필요. `DashboardMetricsView`는 목록 반환이 아니므로 영향 없음.

### 단계 1-E: 테스트 작성 (우선순위 높음)

**대상 파일**: `backend/book/tests/test_book_search.py`

테스트 범위:
- `Inven` 및 `Info` 모델 특성화 테스트 (기존 동작 보존 검증)
- ISBN 정확 검색 — 결과 포함 확인
- ISBN 부분 검색 — icontains 동작 확인
- 제목 부분 검색 — icontains 동작 확인
- OR 조합 검색 — 두 필드 모두 매칭되는 케이스
- 검색어 없음 → 전체 목록 반환 확인
- 미인증 요청 → 401 반환 확인
- 결과 없음 → 빈 results 배열 (404 아님) 확인
- 페이지네이션 구조 검증 (`count`, `next`, `previous`, `results`)
- `select_related` 동작 확인 (Django `assertNumQueries` 활용)

테스트 도구: `pytest-django`, `factory-boy` (테스트 픽스처 생성)

---

## Phase 2: 프론트엔드 구현

### 단계 2-A: TypeScript 타입 정의 (우선순위 높음)

**대상 파일**: `frontend/src/types/book.ts`

정의할 타입:
```typescript
interface BookInfo {
  name: string;
  price_sale: number | null;
  price: number | null;
  qty: number;
  status: string;
  cover_image_url: string | null;
}

interface BookItem {
  inven_SKU: string;
  vendor: string;
  store: string;
  status_of_shopify: string;
  is_use: boolean;
  info: BookInfo;
}

interface BookSearchResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: BookItem[];
}

interface BookSearchParams {
  search?: string;
  page?: number;
}
```

### 단계 2-B: useBookSearch 훅 작성 (우선순위 높음)

**대상 파일**: `frontend/src/features/book/hooks/useBookSearch.ts`

구현 방식:
- TanStack Query `useQuery` 사용
- `enabled: query.length >= 2` — 2자 미만 시 API 호출 비활성화
- `queryKey: ['books', 'search', query, page]` — 쿼리 캐싱
- 300ms 디바운스: `useState` + `useEffect` 또는 `useDeferredValue` 활용
- `keepPreviousData: true` — 페이지 전환 시 이전 데이터 유지 (깜빡임 방지)

참조 패턴: `frontend/src/features/book/hooks/useDashboardMetrics.ts`

### 단계 2-C: 검색 페이지 컴포넌트 (우선순위 중간)

**대상 파일**: `frontend/src/pages/BookSearchPage.tsx`

UI 구성:
- 검색 입력란 (shadcn/ui `Input` 컴포넌트)
- 결과 테이블 — 열: ISBN, 도서 제목, 판매가, Shopify 상태
- 로딩 상태: shadcn/ui `Skeleton` 또는 스피너
- 에러 상태: 에러 메시지 표시
- 빈 상태: "검색 결과가 없습니다" 메시지
- 페이지네이션 컨트롤 (이전/다음 버튼)

참조 패턴: `frontend/src/features/admin-users/AdminUsersPage.tsx` — 리스트 + 테이블 패턴

### 단계 2-D: 라우팅 등록 (우선순위 중간)

기존 React Router 설정에 `/books/search` 경로를 `BookSearchPage`와 연결한다.

---

## 기술적 결정 사항

| 결정 | 선택 | 이유 |
|------|------|------|
| 검색 방식 | DRF `SearchFilter` (내장) | django-filter 의존성 불필요, OR 검색 기본 지원 |
| ViewSet 타입 | `ReadOnlyModelViewSet` | 읽기 전용, 불필요한 write 액션 차단 |
| 쿼리 최적화 | `select_related('info')` | OneToOne 관계 JOIN으로 N+1 방지 |
| 페이지네이션 | `PageNumberPagination`, PAGE_SIZE=50 | DRF 내장, 대용량 데이터 안전 처리 |
| 프론트엔드 쿼리 | TanStack Query `useQuery` | 기존 대시보드와 동일 패턴 유지 |
| 디바운스 | 300ms | 불필요한 API 호출 최소화 (tech.md 권장값) |
| 최소 검색 길이 | 2자 | 단일 문자 검색의 과도한 결과 방지 |

---

## 리스크 분석

### 리스크 1: Info.name 인덱스 추가 시 마이그레이션 지연 (우선순위 높음)
- **상황**: 프로덕션 `book_info` 테이블에 대용량 데이터가 있을 경우 인덱스 추가에 테이블 락이 발생할 수 있다.
- **완화**: MySQL 8.0의 `ALGORITHM=INPLACE, LOCK=NONE` 옵션으로 온라인 DDL 실행. 배포 전 스테이징 환경에서 마이그레이션 시간 측정 필요.

### 리스크 2: 전역 페이지네이션 설정이 기존 뷰에 미치는 영향 (우선순위 중간)
- **상황**: `DEFAULT_PAGINATION_CLASS` 전역 설정이 기존 `DashboardMetricsView`의 응답 구조를 변경할 수 있다.
- **완화**: `DashboardMetricsView`는 `APIView`이며 `list()` 메서드를 사용하지 않으므로 영향 없음. 단, 테스트로 기존 뷰 응답 구조 회귀 검증 필요.

### 리스크 3: inven_SKU 복합 인덱스와 SearchFilter 성능 (우선순위 낮음)
- **상황**: 기존 `[inven_SKU, status_of_shopify]` 복합 인덱스가 있으나 SearchFilter의 icontains 조건이 이를 활용하지 못할 수 있다.
- **완화**: icontains는 LIKE '%query%' 형태로 앞 와일드카드가 있어 인덱스를 완전히 활용하기 어렵다. `Info.name` 단순 인덱스와 함께 EXPLAIN ANALYZE로 실행 계획 확인 권장.

---

## 구현 순서 요약

```
Phase 1 (백엔드)
  └── 1-A: Info.name 마이그레이션
  └── 1-B: Serializer 작성
  └── 1-C: ViewSet + URL 등록
  └── 1-D: 페이지네이션 설정
  └── 1-E: 테스트 작성 및 통과 확인

Phase 2 (프론트엔드)  ← Phase 1 완료 후 시작
  └── 2-A: TypeScript 타입 정의
  └── 2-B: useBookSearch 훅
  └── 2-C: BookSearchPage 컴포넌트
  └── 2-D: 라우팅 등록
```
