# SPEC-ORDER-004 구현 계획

## 개요

주문 상세 페이지에서 단일 주문을 Shopify로부터 즉시 재동기화하는 기능을 추가한다. 백엔드 신규 엔드포인트 1개와 프론트엔드 버튼 UI 변경 1개로 구성된다.

---

## 구현 범위

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/views.py` | 추가 | `OrderResyncView` 클래스 추가 |
| `backend/order/urls.py` | 수정 | `orders/<int:pk>/sync/` 패턴 등록 (기존 패턴 앞에) |
| `frontend/src/pages/OrderDetailPage.tsx` | 수정 | 재동기화 버튼 및 `useMutation` 로직 추가 |

### 변경하지 않는 파일

- `backend/order/shopify_orders.py` — `_get_with_headers`, `_sync_single_order` 재사용, 수정 없음
- `backend/order/serializers.py` — `OrderDetailSerializer` 재사용, 수정 없음
- `frontend/src/features/order/hooks/useOrderDetail.ts` — 수정 없음
- DB 마이그레이션 파일 — 모델 변경 없으므로 불필요

---

## 구현 마일스톤

### Priority High

**M1. 백엔드 — `OrderResyncView` 구현**
- `backend/order/views.py`에 `OrderResyncView(APIView)` 추가
- 인증: `JWTAuthentication` + `IsAuthenticated`
- 로직: Order 조회 → Shopify 단일 주문 API 호출 → DB 업서트 → `OrderDetailSerializer` 응답
- 오류 처리: `HTTPError(404)` → HTTP 404, 그 외 `HTTPError`/`URLError` → HTTP 502

**M2. 백엔드 — URL 패턴 등록**
- `backend/order/urls.py`에 `path('orders/<int:pk>/sync/', ...)` 추가
- `orders/<int:pk>/` 패턴 앞에 위치시켜 Django 라우팅 충돌 방지

### Priority Medium

**M3. 프론트엔드 — 재동기화 버튼 추가**
- `OrderDetailPage.tsx`에 `useMutation` + `useQueryClient` 추가
- 헤더 영역에 "다시 동기화" 버튼 배치 (상태 배지 인근)
- 로딩 상태: `isPending` → `disabled` + "동기화 중..."
- 성공: `invalidateQueries({ queryKey: ['order-detail', id] })`
- 실패: 버튼 인근 에러 메시지 표시

---

## 기술적 위험 요소

| 위험 | 설명 | 완화 방안 |
|------|------|-----------|
| URL 패턴 순서 오류 | `orders/<int:pk>/` 앞에 `orders/<int:pk>/sync/`를 등록하지 않으면 `sync`가 pk 값으로 파싱됨 | REQ-RS-006에 명시, urls.py 수정 시 반드시 순서 확인 |
| `_sync_single_order` 부작용 | 내부 구현이 변경되었을 경우 재사용 시 예상치 못한 동작 발생 가능 | 구현 전 `shopify_orders.py` 내 함수 시그니처 확인 |
| queryKey 불일치 | `invalidateQueries`의 queryKey가 `useOrderDetail` 훅의 queryKey와 다를 경우 리페치가 발생하지 않음 | 구현 시 `useOrderDetail.ts`의 queryKey 값 직접 확인 |
| 동시 요청 | 버튼 연타 시 복수 요청 발생 가능 | `isPending` 상태에서 버튼 `disabled` 처리로 자연스럽게 방지 |

---

## 의존성 확인 체크리스트

구현 시작 전 다음 항목을 확인한다:

- [ ] `backend/order/shopify_orders.py`에서 `_get_with_headers`, `_sync_single_order` 함수 시그니처 확인
- [ ] `backend/order/serializers.py`에서 `OrderDetailSerializer` 클래스명 및 import 경로 확인
- [ ] `backend/order/views.py`에서 기존 import 목록 확인 (`APIView`, `JWTAuthentication`, `IsAuthenticated`, `get_object_or_404` 등)
- [ ] `frontend/src/features/order/hooks/useOrderDetail.ts`에서 queryKey 값 확인
- [ ] 기존 axios/fetch 클라이언트 인스턴스 경로 확인 (POST 요청 시 사용)
