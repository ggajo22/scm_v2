---
id: SPEC-INVEN-ADD-001
title: ISBN 일괄 추가 기능 — 인수 기준
status: Planned
updated: 2026-06-20
---

## 인수 시나리오 (Given-When-Then)

### 시나리오 1: 신규 SKU 정상 등록

```
Given  인증된 운영자가 `/books/add-isbn` 페이지에 접근하고
       DB에 해당 SKU가 존재하지 않으며
       텍스트 영역에 "9791234567890\n9799876543210"을 입력했을 때
When   "추가" 버튼을 클릭하면
Then   API가 HTTP 200을 반환하고
       응답의 created = ["9791234567890", "9799876543210"]
       응답의 duplicates = []
       응답의 created_count = 2, duplicate_count = 0
       DB에 2개의 Inven 레코드가 생성되며
       각 레코드의 vendor="북센", store="책방", is_prepared=0, status_of_shopify=0, is_use=1
       UI에 "2개 생성됨"이 녹색으로 표시된다
```

### 시나리오 2: 이미 존재하는 SKU 처리

```
Given  인증된 운영자가 텍스트 영역에 "9791234567890"을 입력하고
       DB에 해당 SKU를 가진 Inven 레코드가 이미 존재할 때
When   "추가" 버튼을 클릭하면
Then   API가 HTTP 200을 반환하고
       응답의 created = []
       응답의 duplicates = ["9791234567890"]
       응답의 created_count = 0, duplicate_count = 1
       DB의 기존 레코드는 변경되지 않으며
       UI에 "0개 생성됨", "1개 중복"이 표시된다
```

### 시나리오 3: 혼합 입력 (신규 + 중복)

```
Given  텍스트 영역에 "NEW001\nEXIST001\nNEW002"를 입력하고
       DB에 "EXIST001"만 존재할 때
When   "추가" 버튼을 클릭하면
Then   응답의 created = ["NEW001", "NEW002"]
       응답의 duplicates = ["EXIST001"]
       created_count = 2, duplicate_count = 1
```

### 시나리오 4: 입력 중복 제거

```
Given  텍스트 영역에 "SKU001\nSKU001\n SKU002 \n\n"을 입력할 때
When   "추가" 버튼을 클릭하면
Then   실제 처리 대상은 ["SKU001", "SKU002"]이며 (공백 strip, 빈 줄 제거, 중복 제거)
       DB에 최대 2개의 레코드만 생성 시도된다
```

### 시나리오 5: 빈 입력 거부

```
Given  텍스트 영역이 비어 있거나 공백만 있을 때
When   "추가" 버튼을 클릭하면 (또는 빈 배열로 API 호출 시)
Then   API가 HTTP 400을 반환하고
       오류 메시지가 UI에 표시된다
```

### 시나리오 6: 인증 실패

```
Given  JWT 토큰이 없거나 만료된 상태에서
When   POST /api/book/inven-skus/ 요청이 전송되면
Then   API가 HTTP 401을 반환한다
```

### 시나리오 7: 로딩 중 버튼 비활성화

```
Given  운영자가 "추가" 버튼을 클릭하여 API 요청이 진행 중일 때
When   UI 상태를 확인하면
Then   "추가" 버튼이 disabled 상태이다
```

---

## 엣지 케이스

| 케이스 | 기대 동작 |
|--------|-----------|
| 1000개 이상 SKU 입력 | 전체 bulk_create 처리, 타임아웃 없이 완료 |
| 탭 문자 포함 SKU | strip() 후 탭이 제거된 문자열로 처리 |
| 유니코드 문자 포함 | 그대로 inven_SKU에 저장 (형식 검증 없음) |
| 모든 SKU가 중복 | created=[], created_count=0으로 HTTP 200 반환 |
| 동시 동일 SKU 요청 | ignore_conflicts=True로 방어, 한 쪽만 삽입 성공 |

---

## 품질 게이트 기준

- [ ] `POST /api/book/inven-skus/` 엔드포인트가 응답함
- [ ] JWT 없는 요청에 401 반환 확인
- [ ] 빈 skus 배열에 400 반환 확인
- [ ] bulk_create 후 DB 레코드 고정값 확인 (vendor, store, is_prepared, status_of_shopify, is_use)
- [ ] 트랜잭션 원자성: DB 오류 시 전체 롤백 확인
- [ ] 프론트엔드: `/books/add-isbn` 라우트 접근 가능
- [ ] 프론트엔드: 로딩 중 버튼 비활성화 확인
- [ ] 프론트엔드: 결과 섹션 조건부 렌더링 확인
- [ ] 프론트엔드: 오류 메시지 표시 확인

## Definition of Done

- [ ] 모든 인수 시나리오(7개)가 통과
- [ ] 백엔드 뷰에 대한 단위 테스트 작성 (중복 제거 로직, 응답 구조)
- [ ] URL 패턴이 `backend/book/urls.py`에 등록됨
- [ ] 프론트엔드 라우트가 `App.tsx`에 등록됨
- [ ] 네비게이션 링크가 `BookLayout.tsx`에 추가됨
- [ ] TypeScript 타입 오류 없음
