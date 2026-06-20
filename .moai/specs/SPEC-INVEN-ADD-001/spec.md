---
id: SPEC-INVEN-ADD-001
title: ISBN 일괄 추가 기능
status: Completed
created: 2026-06-20
updated: 2026-06-20
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-06-20 | 1.0.0 | 최초 작성 |

---

## 문제 정의

현재 scm_v2에는 개별 도서 검색 및 상세 조회 기능은 존재하지만, 재고(Inven) 레코드를 대량으로 등록하는 방법이 없다. 운영자가 새 입고 도서를 시스템에 반영하려면 하나씩 수작업으로 처리해야 하며, 대량 입고 시 반복 작업이 발생한다.

## 솔루션 개요

운영자가 ISBN을 한 줄에 하나씩 텍스트 영역에 입력하면, 백엔드에서 중복 제거 후 신규 Inven 레코드를 일괄 생성한다. 이미 존재하는 ISBN은 건너뛰고, 결과를 생성됨/중복으로 구분하여 반환한다.

---

## 요구사항 (EARS 형식)

### 백엔드 API

**REQ-IADD-001** (Ubiquitous)
The 시스템 shall `POST /api/book/inven-skus/` 엔드포인트를 제공한다.

**REQ-IADD-002** (Event-Driven)
When `POST /api/book/inven-skus/` 요청이 수신될 때, the 시스템 shall 요청 헤더의 JWT Bearer 토큰을 검증한다.

**REQ-IADD-003** (Unwanted)
If 유효한 JWT 토큰이 없으면, then the 시스템 shall HTTP 401 응답을 반환한다.

**REQ-IADD-004** (Event-Driven)
When 요청 바디의 `skus` 필드가 빈 배열(`[]`)이거나 누락된 경우, the 시스템 shall HTTP 400 응답을 반환한다.

**REQ-IADD-005** (Event-Driven)
When 유효한 `skus` 배열이 수신될 때, the 시스템 shall 각 항목에 대해 앞뒤 공백을 제거(strip)하고 빈 문자열을 제외한 뒤, 순서를 유지하며 중복을 제거한다.

**REQ-IADD-006** (Event-Driven)
When 중복 제거 후 유효한 SKU 목록이 확정될 때, the 시스템 shall `Inven.inven_SKU__in` 조회를 통해 이미 존재하는 SKU와 신규 SKU를 구분한다.

**REQ-IADD-007** (Event-Driven)
When 신규 SKU가 1개 이상 존재할 때, the 시스템 shall 단일 트랜잭션 내에서 `Inven.objects.bulk_create()`를 사용하여 레코드를 일괄 삽입한다. 각 레코드의 고정 값은 `vendor="북센"`, `store="책방"`, `is_prepared=0`, `status_of_shopify=0`, `is_use=1`이다.

**REQ-IADD-008** (Unwanted)
If `bulk_create` 중 데이터베이스 오류가 발생하면, then the 시스템 shall 트랜잭션을 롤백하고 HTTP 500 응답을 반환한다.

**REQ-IADD-009** (Event-Driven)
When 처리가 완료될 때, the 시스템 shall 다음 구조의 HTTP 200 응답을 반환한다:
```json
{
  "created": ["SKU1", "SKU2"],
  "duplicates": ["SKU3"],
  "created_count": 2,
  "duplicate_count": 1
}
```

**REQ-IADD-010** (State-Driven)
While 모든 입력 SKU가 이미 존재하는 경우, the 시스템 shall `created`가 빈 배열이고 `created_count`가 0인 HTTP 200 응답을 반환한다.

---

### 프론트엔드 UI

**REQ-IADD-011** (Ubiquitous)
The 시스템 shall `/books/add-isbn` 경로에 ISBN 일괄 추가 페이지를 제공한다.

**REQ-IADD-012** (Ubiquitous)
The 시스템 shall 기존 네비게이션에서 ISBN 일괄 추가 페이지로 이동하는 링크를 제공한다.

**REQ-IADD-013** (Ubiquitous)
The 시스템 shall ISBN 입력을 위한 다중 행 텍스트 영역을 제공하며, placeholder는 "ISBN을 한 줄에 하나씩 입력하세요"이다.

**REQ-IADD-014** (State-Driven)
While API 요청이 진행 중인 경우, the 시스템 shall 제출 버튼을 비활성화(disabled) 상태로 표시한다.

**REQ-IADD-015** (Event-Driven)
When 제출 버튼이 클릭될 때, the 시스템 shall 텍스트 영역의 내용을 줄바꿈(`\n`)으로 분리하여 `skus` 배열로 변환한 후 `POST /api/book/inven-skus/` 요청을 전송한다.

**REQ-IADD-016** (Event-Driven)
When API 응답이 성공적으로 수신될 때, the 시스템 shall 생성된 SKU 수(`created_count`)를 녹색으로, 중복 SKU 수(`duplicate_count`)를 음소거 색상으로 표시한다.

**REQ-IADD-017** (Event-Driven)
When API 응답이 성공적으로 수신될 때, the 시스템 shall 생성된 SKU 목록과 중복 SKU 목록을 각각 구분하여 표시한다.

**REQ-IADD-018** (Unwanted)
If API 요청이 실패하면, then the 시스템 shall 오류 메시지를 사용자에게 표시한다.

**REQ-IADD-019** (Ubiquitous)
The 시스템 shall 도서 검색 페이지(`/books`)로 돌아가는 링크를 제공한다.

**REQ-IADD-020** (Event-Driven)
When 페이지가 처음 로드될 때, the 시스템 shall 텍스트 영역과 제출 버튼만 표시하며 결과 영역은 숨긴다.

---

## 제외 범위 (What NOT to Build)

- **Info 레코드 생성 없음**: `book_info` 테이블에 레코드를 생성하지 않는다. ISBN 추가는 Inven 레코드 생성에만 해당한다.
- **EtoileBookInven 생성 없음**: 외부 연동 테이블에 대한 레코드 생성을 수행하지 않는다.
- **ISBN 형식 유효성 검사 없음**: 입력값의 ISBN-10/ISBN-13 형식 검증을 수행하지 않는다. SKU는 임의의 문자열로 허용한다.
- **Shopify 동기화 없음**: 레코드 생성 후 Shopify API 연동 작업을 수행하지 않는다. `status_of_shopify=0`으로 생성만 한다.
- **벌크 수정/삭제 없음**: 일괄 수정이나 일괄 삭제 기능은 이 SPEC의 범위에 포함되지 않는다.

---

## 변경 파일 목록

### 백엔드
- `backend/book/views.py` — `InvenSkuBulkAddView` (APIView) 추가
- `backend/book/urls.py` — `POST /api/book/inven-skus/` 엔드포인트 등록
- `backend/book/serializers.py` — `InvenSkuBulkAddSerializer` 추가

### 프론트엔드
- `frontend/src/pages/AddIsbnPage.tsx` — 신규 페이지 컴포넌트 생성
- `frontend/src/features/book/hooks/useAddIsbn.ts` — TanStack Query mutation 훅 추가
- `frontend/src/router/index.tsx` — `/books/add-isbn` 라우트 등록 (SPEC에는 App.tsx로 기재되었으나 실제 라우터 파일 위치에 맞게 수정)
- `frontend/src/features/book/BookLayout.tsx` — 네비게이션 링크 추가

---

## 구현 노트 (Implementation Notes)

**구현 완료일**: 2026-06-20
**커밋**: `7f2bff8` (master)

### 계획 대비 변경사항

- **라우터 파일**: SPEC에서 `App.tsx`로 명시했으나 프로젝트의 실제 라우팅 구조상 `frontend/src/router/index.tsx`에 등록. 기능 동일.
- **훅 파일명**: `useBookMutations.ts`에 추가 예정이었으나 독립 파일 `useAddIsbn.ts`로 분리하여 관심사 분리 개선.

### 미구현 항목

- 없음 — 모든 REQ-IADD-001~REQ-IADD-020 구현 완료.

### 후속 고려사항

- `skus` 목록 최대 크기 제한 미적용 (내부 도구, JWT 필수로 DoS 위험 낮음)
- 현재 별도 테스트 파일 없음 — 추후 `test_inven_sku_bulk_add.py` 작성 권장
