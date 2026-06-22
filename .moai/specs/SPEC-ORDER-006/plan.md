# SPEC-ORDER-006 구현 계획

## 개요

`Order` 모델에 `location` 필드를 추가하고, Shopify Locations API를 통해 위치 코드(CA, KR, NJ 등)를 조회하여 동기화 시 저장한다. 주문 목록 API 응답과 프론트엔드 테이블에 Location 컬럼을 추가한다.

---

## 구현 범위

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/models.py` | 수정 | `Order` 모델에 `location` CharField 추가 |
| `backend/order/migrations/000X_add_order_location.py` | 신규 | `location` 필드 마이그레이션 |
| `backend/order/shopify_orders.py` | 수정 | `_fetch_locations()` 헬퍼 추가 + `_sync_single_order()` 시그니처 확장 + `sync_store()` / `sync_single_order_from_shopify()` 업데이트 |
| `backend/order/serializers.py` | 수정 | `OrderListSerializer.fields`에 `"location"` 추가 |
| `frontend/src/types/order.ts` | 수정 | `OrderListItem`에 `location?: string` 추가 |
| `frontend/src/pages/OrdersPage.tsx` | 수정 | 주문 목록 테이블에 Location 컬럼 추가 |

### 변경하지 않는 파일

- `backend/order/views.py` — 뷰 로직 변경 없음
- `backend/order/urls.py` — URL 패턴 변경 없음
- `frontend/src/features/order/hooks/useOrderList.ts` — 훅 변경 없음 (serializer가 필드를 추가하므로 자동 반영)

---

## 구현 마일스톤

### M1. 백엔드 — 모델 + 마이그레이션 (Priority High)

**목표**: DB 스키마에 `location` 컬럼을 추가한다.

**작업**:
- `backend/order/models.py`의 `Order` 클래스에 다음 필드 추가:
  ```python
  location = models.CharField(max_length=10, blank=True, default="")
  ```
- `python manage.py makemigrations order --name add_order_location`으로 마이그레이션 생성
- 생성된 마이그레이션 파일 내용 검토 후 커밋

**완료 기준**:
- `backend/order/migrations/` 디렉토리에 새 마이그레이션 파일이 존재한다
- `python manage.py migrate`가 오류 없이 실행된다
- `Order` 모델 인스턴스에서 `.location` 속성 접근이 가능하다

---

### M2. 백엔드 — 동기화 로직 업데이트 (Priority High)

**목표**: `shopify_orders.py`에 위치 조회 헬퍼를 추가하고, 전체/개별 동기화 모두 위치 정보를 저장하도록 업데이트한다.

**작업 순서**:

1. `_fetch_locations(domain, token)` 함수 추가:
   - `_get_with_headers(domain, token, "locations.json")` 호출
   - 반환 JSON에서 `response["locations"]` 리스트 순회
   - `code = loc["name"].rsplit("_", 1)[-1] if "_" in loc["name"] else ""`
   - `{loc["id"]: code}` 딕셔너리 반환
   - 예외 발생 시 `{}` 반환 (로그 기록 후 계속 진행)

2. `_sync_single_order(order_data, store_type, location_map=None)` 시그니처 확장:
   - `location_id = order_data.get("location_id")` 추출
   - `location = location_map.get(location_id, "") if location_map and location_id else ""`
   - `Order` 객체 생성/업데이트 시 `location=location` 설정

3. `sync_store(store_type)` 업데이트:
   - 주문 루프 시작 전 `location_map = _fetch_locations(domain, token)` 한 번 호출
   - 루프 내 `_sync_single_order(order_data, store_type, location_map=location_map)` 전달

4. `sync_single_order_from_shopify(shopify_order_id, store_type)` 업데이트:
   - `_sync_single_order()` 호출 전 `location_map = _fetch_locations(domain, token)` 호출
   - `_sync_single_order(order_data, store_type, location_map=location_map)` 전달

**완료 기준**:
- `_fetch_locations()` 함수가 `{location_id: code}` 딕셔너리를 반환한다
- `sync_store()` 실행 후 물리 매장 주문의 `Order.location`이 `"CA"`, `"KR"`, `"NJ"` 등으로 저장된다
- `sync_store()` 실행 후 웹 주문의 `Order.location`이 `""`로 저장된다

---

### M3. 백엔드 — Serializer 업데이트 (Priority Medium)

**목표**: 주문 목록 API 응답에 `location` 필드를 포함한다.

**작업**:
- `backend/order/serializers.py`의 `OrderListSerializer`에서 `fields` 리스트(또는 `Meta.fields`)에 `"location"` 추가

**완료 기준**:
- `GET /api/orders/` 응답의 각 주문 객체에 `"location": "CA"` (또는 `""`) 필드가 포함된다

---

### M4. 프론트엔드 — 타입 + UI (Priority Medium)

**목표**: 주문 목록 테이블에 Location 컬럼을 추가한다.

**작업**:

1. `frontend/src/types/order.ts`:
   - `OrderListItem` 인터페이스에 `location?: string` 추가

2. `frontend/src/pages/OrdersPage.tsx`:
   - 컬럼 정의에 Location 컬럼 추가
   - 헤더: `"Location"`
   - 셀 렌더링: `order.location || "-"`
   - 배치: 스토어 컬럼(`store_type`) 바로 오른쪽

**완료 기준**:
- 주문 목록 페이지에 Location 컬럼이 표시된다
- 위치 코드가 있는 주문은 `"CA"`, `"KR"`, `"NJ"` 등을 표시한다
- 위치 코드가 없는 주문(웹 주문)은 `"-"`를 표시한다

---

## 기술적 위험 요소

| 위험 | 설명 | 완화 방안 |
|------|------|-----------|
| `_fetch_locations()` API 실패 | Locations API 호출 오류 시 전체 동기화가 중단될 수 있음 | REQ-LOC-005: 예외 삼킴 후 `{}` 반환, 동기화 계속 진행 |
| `_sync_single_order()` 시그니처 변경 영향 | 기존 호출부에 `location_map` 인자 미전달 시 `location=""`으로 처리됨 | `location_map=None` 기본값으로 하위 호환성 보장 |
| 마이그레이션 번호 충돌 | 다른 브랜치에서 동시에 마이그레이션을 생성한 경우 번호 충돌 가능 | `makemigrations` 실행 직전 `migrations/` 디렉토리 최신 번호 확인 |
| `location_id` 정수/문자열 타입 불일치 | Shopify API가 `location_id`를 정수로 반환하고, `_fetch_locations()`의 딕셔너리 키도 정수(`loc["id"]`)여야 일치 | `_fetch_locations()` 구현 시 `int(loc["id"])` 명시적 타입 캐스팅 |

---

## 의존성 확인 체크리스트

구현 시작 전 다음 항목을 확인한다:

- [ ] `backend/order/shopify_orders.py`에서 `_get_with_headers` 함수 시그니처 및 반환 형식 확인
- [ ] `backend/order/shopify_orders.py`에서 `_sync_single_order` 현재 시그니처 확인 (`(order_data, store_type)`)
- [ ] `backend/order/shopify_orders.py`에서 `sync_store` 내 `_sync_single_order` 호출 위치 확인
- [ ] `backend/order/shopify_orders.py`에서 `sync_single_order_from_shopify` 내 `_sync_single_order` 호출 위치 확인
- [ ] `backend/order/serializers.py`에서 `OrderListSerializer`의 현재 `fields` 목록 확인
- [ ] `backend/order/migrations/` 디렉토리의 최대 마이그레이션 번호 확인
- [ ] `frontend/src/types/order.ts`에서 `OrderListItem` 인터페이스의 현재 필드 목록 확인
- [ ] `frontend/src/pages/OrdersPage.tsx`에서 컬럼 정의 구조 확인 (TanStack Table 컬럼 정의 방식)
