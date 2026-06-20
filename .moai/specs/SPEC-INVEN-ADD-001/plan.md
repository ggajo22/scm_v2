---
id: SPEC-INVEN-ADD-001
title: ISBN 일괄 추가 기능 — 구현 계획
status: Planned
updated: 2026-06-20
---

## 구현 접근 방식

레거시(`c:/app/scm/main/book/views.py`)의 `_dedupe_preserve_order` + `_process_inven_skus` 패턴을 DRF APIView로 이식한다. 프론트엔드는 기존 TanStack Query 훅 패턴을 따른다.

---

## 마일스톤

### Phase 1 — 백엔드 API (Priority High)

1. `InvenSkuBulkAddSerializer` 작성
   - `skus` 필드: `ListField(child=CharField())`, 빈 리스트 validate
2. `InvenSkuBulkAddView` 작성
   - `IsAuthenticated` permission 적용
   - `@transaction.atomic` 데코레이터로 원자성 보장
   - `_dedupe_preserve_order` 헬퍼 함수 구현 (strip + 순서 유지 중복 제거)
   - 기존 SKU 조회: `Inven.objects.filter(inven_SKU__in=skus).values_list()`
   - `bulk_create(ignore_conflicts=True)` 호출
   - 응답 직렬화: `created`, `duplicates`, `created_count`, `duplicate_count`
3. URL 등록: `path("book/inven-skus/", InvenSkuBulkAddView.as_view())`

### Phase 2 — 프론트엔드 UI (Priority High)

1. `useAddIsbn.ts` 훅 작성
   - `useMutation`으로 `POST /api/book/inven-skus/` 호출
   - 요청 타입: `{ skus: string[] }`
   - 응답 타입: `{ created: string[], duplicates: string[], created_count: number, duplicate_count: number }`
2. `AddIsbnPage.tsx` 페이지 작성
   - `<textarea>` 컴포넌트 (placeholder 지정)
   - 줄바꿈 파싱 후 `mutation.mutate()` 호출
   - 로딩 중 버튼 비활성화
   - 결과 섹션 조건부 렌더링
   - 오류 메시지 표시
3. `App.tsx` 라우트 추가: `/books/add-isbn`
4. `BookLayout.tsx` 네비게이션 링크 추가

---

## 기술 고려사항

### 트랜잭션 원자성

`bulk_create`는 `@transaction.atomic` 내에서 실행한다. DB 오류 발생 시 전체 롤백되어 부분 삽입을 방지한다.

### 중복 처리 전략

`ignore_conflicts=True`를 `bulk_create`에 적용하여 race condition 상황(동시 요청)에서도 안전하게 처리한다. 단, 응답의 `created` 목록은 조회 시점 기준으로 계산되므로 극히 드물게 race가 발생한 경우 실제 생성 수와 1개 차이날 수 있다 — 허용 범위로 간주한다.

### 프론트엔드 파싱

텍스트 영역의 내용을 `\n`으로 split한 후 각 항목을 trim하고 빈 문자열을 필터링하는 작업은 프론트엔드에서도 수행한다. 이는 백엔드의 dedupe 로직과 독립적으로 빈 항목을 API에 전송하지 않기 위함이다.

---

## 리스크

| 리스크 | 영향 | 완화 방법 |
|--------|------|-----------|
| 대용량 입력(수천 개 SKU) | DB 쿼리 성능 저하 | `bulk_create` 배치 크기 제한 검토 (현재 요구사항에 없음, 추후 고려) |
| 동시 요청 중복 | 부분 중복 가능 | `ignore_conflicts=True` + unique constraint로 방어 |
| 프론트엔드 빈 줄 전송 | 불필요한 API 호출 | 클라이언트 측 사전 필터링 |
