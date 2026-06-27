# SPEC-ORDER-002 인수 조건

## Given-When-Then 시나리오

### 시나리오 1: 주문번호로 검색 (숫자 입력)

**Given** 주문 목록에 `order_number=1234`, `name="#1234"` 인 주문과 관계없는 다른 주문들이 존재한다.

**When** `GET /api/orders/?search=1234` 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `results`에 `order_number=1234` 또는 `name`에 "1234" 를 포함하는 주문이 포함된다.
- `results`에 관계없는 주문은 포함되지 않는다.

---

### 시나리오 2: "#" 접두사 포함 주문번호 검색

**Given** `name="#1234"` 인 주문이 존재한다.

**When** `GET /api/orders/?search=%231234` (`#1234` URL 인코딩)를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `results`에 `name="#1234"` 주문이 포함된다.

---

### 시나리오 3: ISBN(13자리) 검색

**Given** `sku="9791234567890"` 인 LineItem을 가진 주문 A와 해당 SKU 없는 주문 B가 존재한다.

**When** `GET /api/orders/?search=9791234567890` 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `results`에 주문 A가 포함된다.
- `results`에 주문 B가 포함되지 않는다.
- 주문 A가 복수의 LineItem을 가지더라도 결과에 중복으로 나타나지 않는다 (`distinct()` 보장).

---

### 시나리오 4: ISBN(10자리) 검색

**Given** `sku="1234567890"` 인 LineItem을 가진 주문이 존재한다.

**When** `GET /api/orders/?search=1234567890` 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `results`에 해당 주문이 포함된다.

---

### 시나리오 5: 빈 검색어 — 전체 목록 반환

**Given** 주문이 다수 존재한다.

**When** `GET /api/orders/?search=` (빈 문자열) 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- 검색 필터가 적용되지 않고 기존 전체 주문 목록이 반환된다.
- `count`가 전체 주문 수와 동일하다.

---

### 시나리오 6: 검색 + 기존 필터 AND 결합

**Given** `store_type="gimssine"` 주문과 `store_type="etoile"` 주문이 각각 `order_number=1234` 로 존재한다.

**When** `GET /api/orders/?search=1234&store_type=gimssine` 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `results`에 `store_type="gimssine"` AND `order_number=1234` 를 만족하는 주문만 포함된다.
- `store_type="etoile"` 주문은 포함되지 않는다.

---

### 시나리오 7: 검색 결과 없음

**Given** 어떤 주문도 `order_number=9999`가 아니고, `name`에 "9999"가 없다.

**When** `GET /api/orders/?search=9999` 를 호출한다.

**Then**
- HTTP 200 응답을 반환한다.
- `count=0`, `results=[]` 를 반환한다.

---

### 시나리오 8: 프론트엔드 — debounce 후 API 호출

**Given** 사용자가 주문 목록 페이지(`/orders`)에 있다.

**When** 검색 입력 필드에 "1234" 를 타이핑한다.

**Then**
- 입력 완료 후 300ms 동안 추가 입력이 없으면 `GET /api/orders/?search=1234` 가 호출된다.
- 300ms 이내에 추가 입력이 발생하면 타이머가 초기화되어 중간 값으로 API가 호출되지 않는다.

---

### 시나리오 9: 프론트엔드 — Enter 키 즉시 검색

**Given** 검색 입력 필드에 "9791234567890" 이 입력되어 있다.

**When** Enter 키를 누른다.

**Then**
- debounce 300ms 대기 없이 즉시 `GET /api/orders/?search=9791234567890` 가 호출된다.

---

### 시나리오 10: 프론트엔드 — 검색어 삭제 시 전체 목록 복귀

**Given** 검색어 "1234" 로 필터링된 상태이다.

**When** 검색 입력 필드를 완전히 지운다 (빈 문자열).

**Then**
- `search` 파라미터 없이 `GET /api/orders/` 가 호출된다.
- 전체 주문 목록이 표시된다.

---

### 시나리오 11: 프론트엔드 — 검색 결과 없음 메시지

**Given** 검색어 "zzzzzz" 로 검색했을 때 API가 `count=0, results=[]` 를 반환한다.

**When** API 응답이 렌더링된다.

**Then**
- 주문 테이블 데이터 행이 표시되지 않는다.
- "검색 결과가 없습니다" 텍스트가 화면에 표시된다.

---

## 엣지 케이스

| 케이스 | 입력 | 기대 동작 |
|--------|------|-----------|
| 공백만 있는 검색어 | `search=   ` | `.strip()` 후 빈 문자열 → 전체 조회 |
| 11~12자리 숫자 | `search=12345678901` | 10/13자리 아님 → ISBN 조건 추가 안 함, 숫자이므로 `order_number` 조건만 추가 |
| 문자+숫자 혼합 | `search=abc123` | `isdigit()` 실패 → `name__icontains` 조건만 적용 |
| 하이픈 포함 ISBN | `search=978-12-34567-89-0` | 숫자 아님 → `name__icontains` 조건만 적용 (하이픈 제거 로직 없음) |
| 매우 긴 입력 | 255자 이상 문자열 | DB 쿼리는 실행되나 일치 결과 없음 (범위 외 처리) |

---

## 품질 게이트 (Definition of Done)

- [ ] `GET /api/orders/?search=<주문번호>` 로 해당 주문이 반환된다
- [ ] `GET /api/orders/?search=<ISBN>` 으로 해당 SKU 포함 주문이 반환된다
- [ ] `search` + `store_type` 동시 적용 시 AND 결합이 정상 동작한다
- [ ] 동일 주문이 복수 LineItem을 가질 때 `distinct()`로 중복 없이 반환된다
- [ ] 빈 `search` 파라미터는 전체 조회와 동일한 결과를 반환한다
- [ ] 프론트엔드 검색 input에 `placeholder="주문번호 또는 ISBN"` 이 표시된다
- [ ] 입력 후 300ms debounce 후 API가 호출된다
- [ ] Enter 키 입력 시 즉시 API가 호출된다
- [ ] 검색어 삭제 시 전체 목록으로 복귀한다
- [ ] 검색 결과 0건 시 "검색 결과가 없습니다" 메시지가 표시된다
- [ ] `OrderListParams` 타입에 `search?: string` 이 추가되어 있다
- [ ] `useOrders` 훅이 `search` 파라미터를 API에 전달한다
- [ ] 새 마이그레이션 파일이 없다 (모델 변경 없음)
- [ ] 기존 `SPEC-ORDER-001` 필터 기능이 회귀 없이 정상 동작한다
