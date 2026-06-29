# SPEC-SHOPIFY-SKU-SET-001 구현 계획 (Implementation Plan)

---

## 기술 접근 방향

### 백엔드

- **모델**: `backend/order/models.py`에 `ShopifySkuSetMapping` 추가
- **마이그레이션**: `backend/order/migrations/`에 새 마이그레이션 파일 생성
- **뷰**: `backend/order/purchase_order_views.py` 또는 별도 `sku_set_views.py`에 API 뷰 작성
- **URL 등록**: `backend/order/urls.py`에 `/api/shopify-sku-sets/` 경로 등록
- **전개 로직**: `UnorderedItemsView.get()` 내부에서 세트 매핑 딕셔너리를 조회 후 인메모리 전개

### 프론트엔드

- **API 클라이언트**: `frontend/src/api/skuSets.ts` (또는 기존 api 디렉토리 구조에 맞게)
- **페이지 컴포넌트**: `frontend/src/pages/settings/SkuSetsPage.tsx`
- **라우트 등록**: 기존 Router 설정에 `/settings/sku-sets` 추가
- **상태 관리**: TanStack Query (`useQuery`, `useMutation`) 사용

---

## 구현 단계

### Phase 1 — 백엔드 모델 및 마이그레이션 [Priority: High]

대상 파일:
- `backend/order/models.py` — `ShopifySkuSetMapping` 모델 추가
- `backend/order/migrations/` — 마이그레이션 파일 생성

작업 내용:
1. `ShopifySkuSetMapping` 모델 정의 (REQ-SKU-SET-001 필드 명세 준수)
2. `Meta.db_table = "order_shopify_sku_set_mapping"` 설정
3. `unique_together = [("bundle_sku", "member_isbn")]` 추가
4. `bundle_sku` 인덱스 추가
5. `python manage.py makemigrations order` 실행하여 마이그레이션 파일 생성
6. 마이그레이션 적용 확인

완료 조건:
- `order_shopify_sku_set_mapping` 테이블 생성 성공
- 중복 unique_together 제약 적용 확인

---

### Phase 2 — 번들 매핑 REST API [Priority: High]

대상 파일:
- `backend/order/sku_set_views.py` (신규) 또는 `backend/order/purchase_order_views.py` (확장)
- `backend/order/urls.py`

작업 내용:
1. `ShopifySkuSetListView` (GET, POST) 구현
   - GET: `bundle_sku` 기준 그룹화 응답
   - POST: `bundle_sku` + `member_isbns` 파싱, 원자적 저장
2. `ShopifySkuSetDetailView` (GET, PUT, DELETE) 구현
   - URL 파라미터에서 `bundle_sku` 추출 (URL 인코딩 고려)
   - PUT: `transaction.atomic()` 내 기존 행 삭제 후 신규 삽입
   - DELETE: 해당 `bundle_sku` 전체 삭제
3. JWT 인증(`IsAuthenticated`) 적용
4. URL 패턴 등록: `path("shopify-sku-sets/", ...)`, `path("shopify-sku-sets/<str:bundle_sku>/", ...)`
5. 유효성 검증: 빈 `bundle_sku`, 빈 `member_isbns` → HTTP 400

완료 조건:
- 5개 엔드포인트 모두 동작
- 인증 없는 요청 시 HTTP 401 반환
- PUT 교체 원자성 확인

---

### Phase 3 — UnorderedItemsView 세트 SKU 전개 [Priority: High]

대상 파일:
- `backend/order/purchase_order_views.py` — `UnorderedItemsView.get()` 수정

작업 내용:
1. `ShopifySkuSetMapping` 전체를 1회 쿼리로 로드
   ```python
   # 예시 구조 (실제 구현은 코드 리뷰 시 확정)
   # bundle_map: { "GITANMATH-F SET": [("9788926025451", 0), ...] }
   bundle_map = {}
   for mapping in ShopifySkuSetMapping.objects.all().order_by("bundle_sku", "sort_order"):
       bundle_map.setdefault(mapping.bundle_sku, []).append(mapping.member_isbn)
   ```
2. `results` 구성 루프에서 `li.sku`가 `bundle_map`에 존재하면 N개 행으로 전개
3. 전개 행에 `is_bundle_member: True`, `bundle_sku: li.sku` 필드 추가
4. 기존 동작(비번들 SKU) 변경 없음

완료 조건:
- 세트 SKU가 전개되어 응답에 포함됨
- 비번들 SKU는 기존 응답과 동일
- `ShopifySkuSetMapping` 조회 쿼리 1회만 실행 (Django Debug Toolbar 또는 `assertNumQueries`로 확인)

---

### Phase 4 — 프론트엔드 설정 페이지 [Priority: Medium]

대상 파일:
- `frontend/src/api/skuSets.ts` (신규)
- `frontend/src/pages/settings/SkuSetsPage.tsx` (신규)
- 라우터 설정 파일

작업 내용:
1. API 클라이언트 함수 작성
   - `getSkuSets()`, `createSkuSet()`, `updateSkuSet()`, `deleteSkuSet()`
2. `SkuSetsPage` 컴포넌트 구현
   - TanStack Query `useQuery`로 목록 조회
   - 목록 테이블: `bundle_sku`, 구성 ISBN 표시, 편집/삭제 버튼
   - 번들 추가 폼 (bundle_sku input + ISBN 목록 textarea 또는 태그 입력)
   - 편집 모달 또는 인라인 편집
   - 삭제 확인 다이얼로그
   - 오류 상태 처리 (토스트 또는 인라인 메시지)
3. 라우트 등록: `/settings/sku-sets`

완료 조건:
- 목록 조회, 추가, 편집, 삭제 모두 동작
- 성공 시 목록 자동 갱신
- API 오류 시 사용자에게 메시지 표시

---

### Phase 5 — 테스트 [Priority: High]

대상 파일:
- `backend/order/tests/test_sku_set_api.py` (신규)
- `backend/order/tests/test_unordered_view.py` (기존 수정 또는 신규)
- `frontend/src/pages/settings/__tests__/SkuSetsPage.test.tsx` (신규)

작업 내용:

**백엔드 단위 테스트 (`pytest`)**:
- `ShopifySkuSetMapping` 모델 생성, 중복 방지 테스트
- API 5개 엔드포인트 정상/오류 케이스 테스트
- PUT 원자성 테스트 (중간 실패 시 롤백 확인)
- `UnorderedItemsView` 세트 전개 동작 테스트
- `UnorderedItemsView` 기존 동작 회귀 테스트 (비번들 SKU)
- N+1 쿼리 방지 테스트 (`assertNumQueries`)

**프론트엔드 컴포넌트 테스트 (`@testing-library/react`)**:
- `SkuSetsPage` 마운트 시 API 호출 확인
- 삭제 버튼 클릭 → 확인 다이얼로그 → API 호출 흐름 테스트
- API 오류 시 오류 메시지 렌더링 테스트

완료 조건:
- 백엔드 커버리지 85% 이상
- 기존 `UnorderedItemsView` 관련 테스트 모두 통과

---

## 리스크 및 완화 방안

| 리스크 | 영향 | 완화 방안 |
|--------|------|-----------|
| `bundle_sku`에 슬래시(`/`) 등 특수문자 포함 시 URL 라우팅 충돌 | 중 | `bundle_sku` URL 파라미터를 URL 인코딩/디코딩 처리, 또는 POST body로 전달하는 방식 검토 |
| 세트 전개로 `UnorderedItemsView` 응답 구조 변경 시 프론트엔드 하위 호환성 | 중 | `is_bundle_member` 필드를 신규 추가만 하고 기존 필드 구조는 유지 |
| 매핑 테이블이 대량 등록 시 인메모리 로드 비용 | 저 | 초기에는 전체 로드. 추후 캐싱(Redis) 도입 검토 |

---

## 구현 순서 요약

```
Phase 1 (모델) → Phase 2 (API) → Phase 3 (전개 로직) → Phase 4 (프론트엔드) → Phase 5 (테스트)
```

Phase 1, 2, 3은 백엔드 순서 의존성이 있으므로 순차 실행.  
Phase 4는 Phase 2 완료 후 병렬 진행 가능.  
Phase 5는 각 Phase 완료 직후 해당 테스트를 함께 작성하는 방식 권장.
