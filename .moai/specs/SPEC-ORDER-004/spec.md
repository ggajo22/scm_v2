---
id: SPEC-ORDER-004
version: "1.0.0"
status: Planned
created: 2026-06-22
updated: 2026-06-22
author: ggajo
priority: Medium
issue_number: ~
---

# 주문 개별 재동기화 (Order Resync)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-22 | ggajo | 최초 작성 — 주문 상세 페이지 재동기화 버튼 SPEC 초안 |

---

## 문제 정의

`SPEC-ORDER-001`에서 구현된 전체 동기화(`POST /api/orders/sync/`)는 모든 스토어의 미결 주문 전체를 Shopify에서 가져오는 배치 작업이다. 이 작업은 처리 시간이 길고 불필요한 API 호출이 다수 발생한다.

관리자가 주문 상세 페이지(`SPEC-ORDER-003`)를 열람하는 상황에서 다음과 같은 케이스가 발생한다:

- Shopify에서 주문 상태(결제 완료, 환불 처리 등)가 방금 변경되었으나, SCM 시스템에 아직 반영되지 않아 잘못된 정보를 보고 있을 수 있음
- 고객 CS 대응 중 최신 주문 상태를 즉시 확인해야 하나, 전체 재동기화를 실행하기엔 부담이 큰 상황
- 특정 주문 1건만 Shopify 최신 데이터로 갱신하고 싶으나 수단이 없음

이로 인해 관리자는 Shopify 어드민과 SCM 시스템을 번갈아 확인하거나, 전체 동기화를 불필요하게 실행하게 된다.

---

## 솔루션 개요

주문 상세 페이지 헤더에 "다시 동기화" 버튼을 추가한다. 버튼을 누르면 해당 주문 1건을 Shopify API에서 즉시 재조회하여 DB를 갱신하고, 화면을 최신 데이터로 다시 렌더링한다.

**백엔드**: `POST /api/orders/{id}/sync/` 엔드포인트를 신규 추가한다. 기존 `_get_with_headers`와 `_sync_single_order` 내부 함수를 재사용하여 단일 주문 Shopify API 호출 → DB 업서트 → 갱신된 `OrderDetailSerializer` 응답의 흐름을 구현한다.

**프론트엔드**: `OrderDetailPage.tsx` 헤더 영역에 버튼을 배치하고, TanStack Query v5의 `useMutation`을 사용하여 API 호출 상태(로딩, 성공, 오류)를 관리한다. 성공 시 `queryClient.invalidateQueries`로 상세 쿼리를 무효화하여 자동 리페치한다.

---

## 요구사항 (EARS 형식)

### 백엔드 — 재동기화 엔드포인트

**REQ-RS-001** (Ubiquitous)
The 시스템 **shall** `POST /api/orders/{id}/sync/` 엔드포인트(`OrderResyncView`)를 제공하며, JWT 인증(`JWTAuthentication` + `IsAuthenticated`)이 필요하다.

**REQ-RS-002** (Event-Driven)
**When** `POST /api/orders/{id}/sync/`가 유효한 주문 ID와 함께 호출되면, the 시스템 **shall** 다음 순서로 처리한다:
1. 로컬 DB에서 해당 `Order` 객체를 조회한다.
2. `settings.SHOPIFY_STORES[order.store_type]`에서 `domain`과 `token`을 읽는다.
3. `_get_with_headers(domain, token, f"orders/{order.shopify_order_id}.json")`으로 Shopify 단일 주문 API(`GET orders/{shopify_order_id}.json`)를 호출한다.
4. `_sync_single_order(body["order"], order.store_type)`으로 Order, Customer, ShippingAddress, LineItems, ShippingLines, Refunds를 DB에 업서트한다.
5. 갱신된 Order 객체에 대해 `OrderDetailSerializer`를 적용하여 HTTP 200으로 응답한다.

**REQ-RS-003** (Event-Driven)
**When** `POST /api/orders/{id}/sync/`에서 로컬 DB에 해당 주문이 존재하지 않으면, the 시스템 **shall** HTTP 404를 반환한다.

**REQ-RS-004** (Event-Driven)
**If** Shopify API 호출에서 `urllib.error.HTTPError` 또는 `urllib.error.URLError`가 발생하면, **then** the 시스템 **shall** HTTP 502와 함께 `{"error": "<에러 메시지>"}` JSON 응답을 반환한다.

**REQ-RS-005** (Event-Driven)
**If** Shopify API가 HTTP 404를 반환하면 (Shopify에서 해당 주문이 삭제된 경우), **then** the 시스템 **shall** HTTP 404와 함께 `{"error": "Shopify에서 주문을 찾을 수 없습니다."}` JSON 응답을 반환한다.

**REQ-RS-006** (Ubiquitous)
The 시스템 **shall** `backend/order/urls.py`에 `orders/<int:pk>/sync/` 패턴을 `orders/<int:pk>/` 패턴보다 **앞에** 등록한다. (Django URL 패턴 매칭 순서에 따라 `sync/`가 `pk/` 패턴에 흡수되지 않도록 보장)

---

### 프론트엔드 — 재동기화 버튼 UI

**REQ-RS-007** (Ubiquitous)
The `OrderDetailPage` **shall** 헤더 영역의 상태 배지 인근에 "다시 동기화" 버튼을 표시한다.

**REQ-RS-008** (State-Driven)
**While** 재동기화 API 호출이 진행 중인 경우, the 시스템 **shall** 버튼을 비활성화(`disabled`)하고 버튼 텍스트를 "동기화 중..."으로 변경하여 로딩 상태임을 시각적으로 표시한다.

**REQ-RS-009** (Event-Driven)
**When** 재동기화 API 호출이 HTTP 200으로 성공하면, the 시스템 **shall** `queryClient.invalidateQueries({ queryKey: ['order-detail', id] })`를 호출하여 주문 상세 쿼리를 무효화하고, TanStack Query가 자동으로 최신 데이터를 리페치하도록 한다.

**REQ-RS-010** (Event-Driven)
**If** 재동기화 API 호출이 실패(네트워크 오류 또는 HTTP 4xx/5xx)하면, **then** the 시스템 **shall** 버튼 인근에 에러 메시지를 표시한다. 에러 메시지는 API 응답의 `error` 필드 값을 우선 표시하며, 없을 경우 "동기화에 실패했습니다." 기본 메시지를 표시한다.

---

### 프론트엔드 — useMutation 훅

**REQ-RS-011** (Ubiquitous)
The 시스템 **shall** TanStack Query v5의 `useMutation`을 사용하여 재동기화 로직을 관리한다. mutation 함수는 `POST /api/orders/{id}/sync/`를 호출하며, `onSuccess` 콜백에서 쿼리 무효화를 수행한다.

---

## 제외 사항 (What NOT to Build)

- **전체 재동기화 트리거**: "다시 동기화" 버튼은 현재 페이지의 주문 1건만 재동기화한다. 전체 동기화(`POST /api/orders/sync/`)는 별도 메뉴/버튼에서만 실행 가능하며, 이 SPEC에서 UI를 변경하지 않는다.
- **자동 주기적 동기화**: 일정 시간마다 자동으로 재동기화하는 polling 또는 WebSocket 기반 자동 갱신은 이 SPEC의 범위가 아니다.
- **동기화 이력 로그 UI**: 언제 마지막으로 동기화되었는지 기록하고 표시하는 이력 기능은 포함하지 않는다.
- **Shopify 데이터 삭제 감지 및 소프트 딜리트**: Shopify에서 주문이 삭제된 경우 로컬 DB 레코드를 삭제하거나 `deleted` 플래그를 설정하는 로직은 포함하지 않는다. REQ-RS-005에서 HTTP 404만 반환한다.
- **재동기화 성공 알림 Toast/Modal**: 성공 시 별도 성공 알림 UI(예: Toast 메시지)는 제공하지 않는다. TanStack Query의 자동 리페치로 화면이 갱신되는 것이 성공 피드백으로 충분하다.
- **주문 일괄 재동기화**: 목록 페이지에서 여러 주문을 선택하여 일괄 재동기화하는 기능은 이 SPEC의 범위가 아니다.

---

## 기술적 접근 방식

### 백엔드

**신규 파일/코드 변경 대상:**

1. **`backend/order/views.py`** — `OrderResyncView` 클래스 추가

   ```python
   # 참고 패턴 (구현 시 실제 코드는 구현 에이전트가 작성)
   class OrderResyncView(APIView):
       authentication_classes = [JWTAuthentication]
       permission_classes = [IsAuthenticated]

       def post(self, request, pk):
           order = get_object_or_404(Order, pk=pk)
           store_cfg = settings.SHOPIFY_STORES[order.store_type]
           domain = store_cfg["domain"]
           token = store_cfg["token"]
           try:
               body, _ = _get_with_headers(domain, token, f"orders/{order.shopify_order_id}.json")
           except urllib.error.HTTPError as e:
               if e.code == 404:
                   return Response({"error": "Shopify에서 주문을 찾을 수 없습니다."}, status=404)
               return Response({"error": str(e)}, status=502)
           except urllib.error.URLError as e:
               return Response({"error": str(e)}, status=502)
           _sync_single_order(body["order"], order.store_type)
           order.refresh_from_db()
           serializer = OrderDetailSerializer(order)
           return Response(serializer.data, status=200)
   ```

2. **`backend/order/urls.py`** — `orders/<int:pk>/sync/` 패턴 추가 (기존 `orders/<int:pk>/` 패턴 앞에 위치)

   ```python
   # 순서가 중요함 — sync/ 가 먼저 와야 함
   path('orders/<int:pk>/sync/', OrderResyncView.as_view(), name='order-resync'),
   path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
   ```

**재사용하는 기존 함수 (수정 불필요):**
- `backend/order/shopify_orders.py` 내 `_get_with_headers()` — Shopify API 호출
- `backend/order/shopify_orders.py` 내 `_sync_single_order()` — DB 업서트
- `backend/order/serializers.py` 내 `OrderDetailSerializer` — 응답 직렬화

**DB 마이그레이션:** 불필요 (모델 변경 없음)

---

### 프론트엔드

**변경 대상 파일:**

1. **`frontend/src/pages/OrderDetailPage.tsx`** — 재동기화 버튼 및 `useMutation` 추가

   - `useMutation` import 및 `useQueryClient` import 추가
   - mutation 정의:
     ```
     mutationFn: () => POST /api/orders/{id}/sync/
     onSuccess: () => queryClient.invalidateQueries({ queryKey: ['order-detail', id] })
     ```
   - 헤더 JSX에 버튼 추가:
     - 평상시: "다시 동기화" 텍스트 버튼
     - `mutation.isPending === true`일 때: `disabled` + "동기화 중..." 텍스트
     - `mutation.isError === true`일 때: 버튼 하단에 에러 메시지 표시

**참고 사항:**
- `useOrderDetail(id)` 훅의 `queryKey`는 `['order-detail', id]`이며 (SPEC-ORDER-003 기준), `invalidateQueries`도 동일한 키를 사용해야 한다.
- `id` 값은 라우트 파라미터에서 number로 파싱하여 사용 (기존 `OrderDetailPage` 구현 방식과 동일).
- axios 또는 fetch 사용 방식은 기존 `useOrderDetail` 훅의 API 클라이언트 패턴을 따른다.
- 새로운 파일/컴포넌트 생성 없이 기존 `OrderDetailPage.tsx` 수정만으로 구현 완료 가능.

---

## 의존성 (Dependencies)

- **SPEC-ORDER-001** (주문관리 백엔드/프론트엔드 구현) — `Order` 모델, `_get_with_headers`, `_sync_single_order` 함수, `OrderDetailSerializer`의 전제 조건
- **SPEC-ORDER-003** (주문 상세 페이지) — `OrderDetailPage.tsx`, `useOrderDetail` 훅, `OrderDetailView`가 이미 구현되어 있어야 한다. 이 SPEC은 SPEC-ORDER-003의 결과물 위에서만 동작한다.
