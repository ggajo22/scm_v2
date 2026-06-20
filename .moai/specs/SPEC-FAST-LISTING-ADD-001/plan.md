---
id: SPEC-FAST-LISTING-ADD-001
document: plan
version: 1.0.0
---

## 구현 계획

### 기술 접근 방식

SPEC-INVEN-ADD-001(`InvenSkuBulkAddView`)의 구조를 참조 패턴으로 활용한다. 핵심 차이점은 다음과 같다:

| 항목 | SPEC-INVEN-ADD-001 (기존) | SPEC-FAST-LISTING-ADD-001 (신규) |
|------|--------------------------|----------------------------------|
| 엔드포인트 | `POST /api/book/inven-skus/` | `POST /api/book/fast-listing-skus/` |
| 신규 SKU status | 0 | 1 |
| 기존 SKU 처리 | 건너뜀 (중복으로 분류) | status에 따라 업데이트 or 건너뜀 |
| 응답 범주 | created / duplicates | created / updated / skipped |
| 활성 도서 보호 | 없음 | status 80/81/82 건너뜀 |

---

## 마일스톤

### M1: 백엔드 API (Priority High)

**구현 대상 파일**
- `backend/book/serializers.py` — `FastListingSkuSerializer` 추가
- `backend/book/views.py` — `FastListingSkuView` (APIView) 추가
- `backend/book/urls.py` — URL 패턴 등록

**핵심 구현 로직 (`FastListingSkuView.post`)**

```
1. Serializer로 skus 유효성 검사 (빈 배열/누락 → 400)
2. 입력 정규화: strip, 빈 문자열 제거, 순서 유지 중복 제거
3. DB 조회: Inven.objects.filter(inven_SKU__in=cleaned_skus)
4. 기존 SKU 분류:
   - active_statuses = {80, 81, 82}
   - skipped = [r for r in existing if r.status_of_shopify in active_statuses]
   - to_update = [r for r in existing if r.status_of_shopify not in active_statuses]
5. 신규 SKU: new_skus = [s for s in cleaned_skus if s not in existing_sku_set]
6. @transaction.atomic 블록:
   - Inven.objects.bulk_create(new Inven records with status=1)
   - Inven.objects.filter(inven_SKU__in=to_update_skus).update(status_of_shopify=1)
7. 응답: created / updated / skipped + count fields
```

**참조 파일 (패턴 확인용, 수정 없음)**
- `backend/book/views.py` → `InvenSkuBulkAddView` 구조
- `backend/book/serializers.py` → `InvenSkuBulkAddSerializer` 구조
- `backend/book/urls.py` → 기존 URL 패턴

---

### M2: 프론트엔드 UI (Priority High)

**구현 대상 파일**
- `frontend/src/features/book/hooks/useFastListing.ts` — TanStack Query `useMutation` 훅
- `frontend/src/pages/FastListingPage.tsx` — 메인 페이지 컴포넌트
- `frontend/src/router/index.tsx` — `/books/fast-listing` 라우트 등록
- `frontend/src/components/Sidebar.tsx` — "빠른 리스팅" 사이드바 항목 추가

**참조 파일 (패턴 확인용, 수정 없음)**
- `frontend/src/pages/AddIsbnPage.tsx` → 텍스트 영역 UI 패턴
- `frontend/src/features/book/hooks/useAddIsbn.ts` → mutation 훅 패턴
- `frontend/src/router/index.tsx` → 라우트 등록 패턴
- `frontend/src/components/Sidebar.tsx` → 사이드바 서브항목 패턴

**결과 표시 컴포넌트 구조**
```
FastListingPage
├── <textarea> (ISBN 입력)
├── <Button> (제출, API 호출 중 disabled)
├── ResultSection (created, green)
├── ResultSection (updated, blue)
└── ResultSection (skipped, muted)
```

---

### M3: 검증 (Priority High)

**백엔드 테스트**
- `backend/book/tests/test_fast_listing.py` 신규 생성
- `APITestCase` 기반으로 인수 시나리오 1~8 커버
- `@transaction.atomic` 롤백 테스트 포함

**프론트엔드 테스트**
- `useFastListing.ts` 단위 테스트
- TanStack Query `QueryClient` mock 환경 사용

---

## 위험 요소 및 완화 방안

| 위험 | 설명 | 완화 방안 |
|------|------|-----------|
| status 80/81/82 경계 조건 | 신규 status 값이 미래에 추가될 경우 하드코딩 문제 | `ACTIVE_STATUSES = frozenset({80, 81, 82})` 상수 정의 |
| bulk_create / bulk_update 동시 트랜잭션 | partial success 가능성 | `@transaction.atomic` 으로 전체 롤백 보장 |
| 프론트엔드 라우트 중복 | 기존 AddIsbnPage 패턴과 혼동 | 명확한 컴포넌트/훅 이름 구분 (`FastListing` prefix) |

---

## 구현 순서

1. **M1 백엔드** 먼저 구현 (Serializer → View → URL)
2. **M3 백엔드 테스트** 작성 및 통과 확인
3. **M2 프론트엔드** 구현 (훅 → 페이지 → 라우터 → 사이드바)
4. **M3 프론트엔드 테스트** 작성
5. 전체 통합 확인 (LSP 오류 0건, 타입 오류 0건)

---

## 변경 파일 요약

**백엔드 (수정)**
- `backend/book/serializers.py` — Serializer 추가
- `backend/book/views.py` — View 추가
- `backend/book/urls.py` — URL 등록

**백엔드 (신규)**
- `backend/book/tests/test_fast_listing.py` — 테스트

**프론트엔드 (신규)**
- `frontend/src/features/book/hooks/useFastListing.ts`
- `frontend/src/pages/FastListingPage.tsx`

**프론트엔드 (수정)**
- `frontend/src/router/index.tsx` — 라우트 추가
- `frontend/src/components/Sidebar.tsx` — 사이드바 항목 추가
