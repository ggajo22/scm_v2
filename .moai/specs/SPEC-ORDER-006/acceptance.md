# SPEC-ORDER-006 인수 기준 (Acceptance Criteria)

---

## 시나리오 1: 물리 매장 주문 동기화 — 위치 코드 저장

**Given** `sync_store("gimssine")` 실행 시
- Shopify Locations API가 `[{"id": 85951578417, "name": "GIMSSINE_CA"}, {"id": 111320793393, "name": "GIMSSINE_KR"}]`를 반환하고
- 첫 번째 주문 데이터에 `"location_id": 85951578417`이 포함된 경우

**When** `sync_store("gimssine")`이 완료되면

**Then**
- `_fetch_locations(domain, token)`이 정확히 1회 호출된다 (루프 밖에서)
- 해당 주문의 `Order.location`이 `"CA"`로 저장된다
- 두 번째 위치(`GIMSSINE_KR`)에 해당하는 주문이 있다면 `Order.location`이 `"KR"`로 저장된다

---

## 시나리오 2: 웹 주문 동기화 — 빈 문자열 저장

**Given** `sync_store("gimssine")` 실행 시
- 주문 데이터에 `"location_id": null`이 포함된 경우 (온라인 웹 주문)

**When** `sync_store("gimssine")`이 완료되면

**Then**
- 해당 주문의 `Order.location`이 `""`(빈 문자열)로 저장된다

---

## 시나리오 3: 비활성 위치 처리 — 빈 문자열 저장

**Given** Shopify Locations API가 `{"id": 98735030577, "name": "GIMSSINE"}`를 반환하고 (언더스코어 없음)
주문 데이터에 `"location_id": 98735030577`이 포함된 경우

**When** `_sync_single_order()`가 실행되면

**Then**
- `_fetch_locations()`가 해당 위치에 대해 `{98735030577: ""}`를 반환한다
- 해당 주문의 `Order.location`이 `""`(빈 문자열)로 저장된다

---

## 시나리오 4: Locations API 실패 — 동기화 계속 진행

**Given** `_get_with_headers(domain, token, "locations.json")` 호출 시 네트워크 오류 또는 HTTP 오류가 발생하는 경우

**When** `sync_store()` 또는 `sync_single_order_from_shopify()`가 실행되면

**Then**
- `_fetch_locations()`가 `{}`를 반환하고 예외를 외부로 전파하지 않는다
- 동기화는 중단 없이 계속 진행된다
- 해당 동기화로 저장되는 모든 주문의 `Order.location`이 `""`로 설정된다

---

## 시나리오 5: 개별 재동기화 — 위치 정보 반영

**Given** 로컬 DB에 `id=5`, `store_type="etoile"`, `shopify_order_id=987654321`인 주문이 존재하고
- Shopify Locations API가 `[{"id": 76370411705, "name": "ETOILE_CA"}]`를 반환하며
- Shopify 단일 주문 API가 `"location_id": 76370411705`를 포함한 데이터를 반환하는 경우

**When** `sync_single_order_from_shopify(987654321, "etoile")`이 실행되면

**Then**
- `_fetch_locations(etoile_domain, etoile_token)`이 호출된다
- 해당 주문의 `Order.location`이 `"CA"`로 업데이트된다

---

## 시나리오 6: 주문 목록 API 응답에 location 포함

**Given** DB에 `location="CA"`인 주문과 `location=""`인 주문이 존재하는 경우

**When** 인증된 관리자가 `GET /api/orders/`를 호출하면

**Then**
- 각 주문 객체에 `"location"` 필드가 포함된다
- `location="CA"` 주문의 응답 필드 값이 `"CA"`이다
- `location=""` 주문의 응답 필드 값이 `""`이다

---

## 시나리오 7: 주문 목록 UI — Location 컬럼 표시

**Given** 사용자가 `/orders` 주문 목록 페이지를 열어 데이터가 로드된 경우

**When** 페이지가 완전히 렌더링되면

**Then**
- 주문 목록 테이블에 "Location" 헤더를 가진 컬럼이 표시된다
- `location="CA"`인 주문 행에는 `"CA"`가 표시된다
- `location=""`인 주문 행에는 `"-"`가 표시된다 (빈 문자열이 `"-"`로 변환됨)

---

## 시나리오 8: `_sync_single_order` 하위 호환성

**Given** `_sync_single_order(order_data, store_type)`을 `location_map` 인자 없이 호출하는 기존 코드가 있는 경우

**When** 해당 코드가 실행되면

**Then**
- `location_map=None` 기본값이 적용된다
- `Order.location`이 `""`으로 저장된다
- TypeError 등 예외가 발생하지 않는다

---

## 시나리오 9: `_fetch_locations` 코드 추출 규칙 검증

**Given** Shopify Locations API가 다음 데이터를 반환하는 경우:
```
[
  {"id": 85951578417, "name": "GIMSSINE_CA"},
  {"id": 111320793393, "name": "GIMSSINE_KR"},
  {"id": 101550260529, "name": "GIMSSINE_NJ"},
  {"id": 98735030577, "name": "GIMSSINE"},
  {"id": 76370411705, "name": "ETOILE_CA"},
  {"id": 79188459705, "name": "ETOILE_NJ"}
]
```

**When** `_fetch_locations(domain, token)`이 실행되면

**Then**
- 반환된 딕셔너리가 다음과 같다:
  ```python
  {
      85951578417: "CA",
      111320793393: "KR",
      101550260529: "NJ",
      98735030577: "",
      76370411705: "CA",
      79188459705: "NJ"
  }
  ```

---

## 시나리오 10: 인증 없이 주문 목록 API 호출

**Given** JWT 토큰이 없는 상태인 경우

**When** `GET /api/orders/`를 호출하면

**Then**
- HTTP 401 응답이 반환된다 (기존 동작 유지, 회귀 없음)

---

## Definition of Done

- [ ] `backend/order/models.py`에 `location` 필드가 추가되어 있다 (REQ-LOC-001)
- [ ] `backend/order/migrations/` 디렉토리에 `location` 필드 마이그레이션 파일이 존재한다 (REQ-LOC-002)
- [ ] `backend/order/shopify_orders.py`에 `_fetch_locations(domain, token)` 함수가 구현되어 있다 (REQ-LOC-003, REQ-LOC-004)
- [ ] `_fetch_locations()`는 API 실패 시 `{}`를 반환하고 예외를 전파하지 않는다 (REQ-LOC-005)
- [ ] `sync_store()`에서 `_fetch_locations()`가 루프 **밖**에서 1회만 호출된다 (REQ-LOC-006)
- [ ] `sync_store()`에서 `_sync_single_order()`에 `location_map`이 전달된다 (REQ-LOC-007)
- [ ] `sync_single_order_from_shopify()`에서 `_fetch_locations()` 호출 후 `location_map`이 전달된다 (REQ-LOC-008)
- [ ] `_sync_single_order()`가 `location_map` 기본값 `None`을 가지며 하위 호환성이 유지된다 (REQ-LOC-009, REQ-LOC-010)
- [ ] `OrderListSerializer`의 응답에 `location` 필드가 포함된다 (REQ-LOC-011)
- [ ] `frontend/src/types/order.ts`의 `OrderListItem`에 `location?: string`이 추가되어 있다 (REQ-LOC-012)
- [ ] 주문 목록 테이블에 Location 컬럼이 표시된다 (REQ-LOC-013, REQ-LOC-014)
- [ ] 위치 코드 없는 주문(웹 주문)은 Location 셀에 `"-"`가 표시된다
- [ ] 기존 `GET /api/orders/` 인증 동작(HTTP 401)이 유지된다 (시나리오 10)
- [ ] `python manage.py migrate`가 오류 없이 실행된다

---

## 품질 기준

- **백엔드 단위 테스트**: `_fetch_locations()` 함수에 대해 다음 케이스를 테스트한다:
  - 정상 응답 → `{location_id: code}` 딕셔너리 반환 (시나리오 9)
  - 언더스코어 없는 이름 → `""` 코드 반환 (시나리오 3)
  - API 예외 발생 → `{}` 반환, 예외 미전파 (시나리오 4)
- **백엔드 통합 테스트**: `_sync_single_order()`가 `location_map` 있을 때와 없을 때 모두 정상 동작함을 검증한다 (시나리오 8)
- **회귀 방지**: 기존 `sync_store()` 및 `sync_single_order_from_shopify()` 동작이 위치 정보 추가 외에 변경되지 않음을 기존 테스트로 검증한다
