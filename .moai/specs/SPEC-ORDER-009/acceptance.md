# SPEC-ORDER-009 인수 기준

## 시나리오 1: 주문일 환율 존재 시 KRW 기준 마진 정확성

**적용 REQ**: REQ-010, REQ-012, REQ-013

**Given** `ExchangeRate(effective_date="2026-01-15", rate=1300.00)` 레코드가 존재하고,
`total_price = "100.00"` (USD), `shopify_created_at = 2026-01-15T12:00:00+09:00` 인 주문이 있으며,
해당 주문의 line_item A: `confirmed_price = 50000.00 KRW, quantity = 2` 가 존재할 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- `margin_amount` = `(100.00 * 1300.00) - (50000.00 * 2)` = `130000.00 - 100000.00` = `"30000.00"` 이어야 한다
- `margin_rate` = `(30000.00 / 130000.00) * 100` = `"23.08"` (소수점 2자리 반올림) 이어야 한다
- DB 쿼리 횟수는 `ExchangeRate` 조회 기준 최대 2회이어야 한다 (get_margin_amount 1회 + get_margin_rate 1회)

---

## 시나리오 2: 주문일 환율 없을 때 이전 날짜 폴백 사용

**적용 REQ**: REQ-003, REQ-012

**Given** `ExchangeRate(effective_date="2026-01-10", rate=1280.00)` 레코드만 존재하고 (1월 15일 환율 없음),
`total_price = "50.00"` (USD), `shopify_created_at = 2026-01-15T09:00:00+09:00` 인 주문이 있으며,
line_item: `confirmed_price = 30000.00 KRW, quantity = 1` 이 존재할 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- 시스템은 `2026-01-10` 의 환율 `1280.00` 을 폴백으로 사용하여야 한다
- `margin_amount` = `(50.00 * 1280.00) - (30000.00 * 1)` = `64000.00 - 30000.00` = `"34000.00"` 이어야 한다
- `margin_rate` = `(34000.00 / 64000.00) * 100` = `"53.13"` 이어야 한다
- `null` 이 반환되지 않아야 한다 (폴백 성공)

---

## 시나리오 3: 환율 레코드 전혀 없을 때 margin = null

**적용 REQ**: REQ-011

**Given** `ExchangeRate` 테이블에 레코드가 한 건도 없고,
`total_price = "100.00"`, `shopify_created_at = 2026-01-15T00:00:00+09:00` 인 주문이 있으며,
line_item: `confirmed_price = 50000.00 KRW, quantity = 2` 가 존재할 때

**When** `GET /api/orders/{id}/` 를 호출하면

**Then**
- `margin_amount` 는 `null` 이어야 한다
- `margin_rate` 는 `null` 이어야 한다
- HTTP 상태 코드는 `200` 이어야 한다 (오류 아님 — 정상 응답)

---

## 시나리오 4: 환율 CRUD API 정상 동작

**적용 REQ**: REQ-001, REQ-002, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008

**Given** 인증된 사용자(JWT Bearer token)가 API를 호출할 때

**POST — 생성**

**When** `POST /api/exchange-rates/` body: `{"effective_date": "2026-06-27", "rate": "1350.50"}` 를 전송하면

**Then**
- HTTP 201 이 반환되어야 한다
- 응답 body에 `effective_date = "2026-06-27"`, `rate = "1350.50"` 이 포함되어야 한다

**GET — 목록**

**When** `GET /api/exchange-rates/` 를 호출하면 (레코드 2건 이상 존재 시)

**Then**
- HTTP 200 이 반환되어야 한다
- 응답 목록이 `effective_date` 내림차순(최신순)으로 정렬되어야 한다

**GET — 단건**

**When** `GET /api/exchange-rates/2026-06-27/` 를 호출하면

**Then**
- HTTP 200 이 반환되어야 한다
- 응답 body에 `effective_date = "2026-06-27"`, `rate = "1350.50"` 이 포함되어야 한다

**PUT — 수정**

**When** `PUT /api/exchange-rates/2026-06-27/` body: `{"effective_date": "2026-06-27", "rate": "1360.00"}` 를 전송하면

**Then**
- HTTP 200 이 반환되어야 한다
- 응답 body의 `rate` 가 `"1360.00"` 이어야 한다

**DELETE — 삭제**

**When** `DELETE /api/exchange-rates/2026-06-27/` 를 전송하면

**Then**
- HTTP 204 이 반환되어야 한다
- 이후 `GET /api/exchange-rates/2026-06-27/` 를 호출하면 HTTP 404 가 반환되어야 한다

**미인증 접근**

**When** Authorization 헤더 없이 `GET /api/exchange-rates/` 를 호출하면

**Then**
- HTTP 401 이 반환되어야 한다

---

## 시나리오 5: 중복 날짜 POST → 400 오류

**적용 REQ**: REQ-002, REQ-009

**Given** `ExchangeRate(effective_date="2026-06-27", rate=1300.00)` 이 이미 존재할 때

**When** `POST /api/exchange-rates/` body: `{"effective_date": "2026-06-27", "rate": "1400.00"}` 를 전송하면

**Then**
- HTTP 400 이 반환되어야 한다
- 응답 body에 `effective_date` 키의 필드 레벨 유효성 오류가 포함되어야 한다
- DB에 중복 레코드가 생성되지 않아야 한다 (기존 `rate = 1300.00` 유지)

---

## 엣지 케이스

| 케이스 | 적용 REQ | 기대 동작 |
|--------|----------|-----------|
| `shopify_created_at = null` 인 주문 | REQ-011 | `order_date = None` → `_get_exchange_rate` → `None` → `margin_amount = null` |
| `total_price = "0.00"` 이고 환율 존재 | REQ-012 | `total_price_krw = 0` → `margin_rate = null` (0 나누기 방지) |
| `confirmed_price = Decimal("0.00")` | REQ-010 | `is not None` 체크이므로 0도 합산에 포함 (falsy 오동작 없음) |
| line_item이 0개인 주문 | REQ-011 | `has_any_confirmed = False` → `margin_amount = null` |
| `rate = Decimal("0.00")` 인 환율 레코드 | REQ-012 | `total_price_krw = 0` → `margin_rate = null` |
| `GET /api/exchange-rates/9999-99-99/` 존재하지 않는 날짜 조회 | REQ-006 | HTTP 404 반환 |
| 환율 레코드가 주문일보다 모두 미래 날짜인 경우 | REQ-011 | `filter(effective_date__lte=order_date)` 결과 없음 → `margin_amount = null` |

---

## Definition of Done

- [ ] `ExchangeRate` 모델 생성 및 `orders_exchangerate` 테이블로 마이그레이션 완료 (REQ-001)
- [ ] `effective_date` DB unique 제약 적용 (REQ-002)
- [ ] `GET /api/exchange-rates/` 목록 API 정상 동작, 최신순 정렬 (REQ-004)
- [ ] `POST /api/exchange-rates/` 생성 API HTTP 201 반환 (REQ-005)
- [ ] `GET /api/exchange-rates/{date}/` 단건 조회, HTTP 200/404 (REQ-006)
- [ ] `PUT /api/exchange-rates/{date}/` 수정 API HTTP 200 (REQ-007)
- [ ] `DELETE /api/exchange-rates/{date}/` 삭제 API HTTP 204 (REQ-008)
- [ ] 중복 날짜 POST 시 HTTP 400 (REQ-009)
- [ ] `get_margin_amount`: USD total_price를 환율로 KRW 환산 후 confirmed_cost_krw 차감 (REQ-010)
- [ ] 환율 없을 때 `margin_amount = null` 반환 (REQ-011)
- [ ] `get_margin_rate`: `total_price_krw` 를 분모로 사용 (REQ-012)
- [ ] `_get_exchange_rate` 헬퍼로 쿼리 중복 최소화 (REQ-013)
- [ ] 폴백 쿼리 (`effective_date__lte`) 정상 동작 검증 (REQ-003)
- [ ] 신규 테스트 `test_spec_009.py` 전체 통과
- [ ] 기존 `backend/order/tests/` 전체 통과 (회귀 없음, 또는 환율 fixture 추가로 조정 완료)
- [ ] `python manage.py migrate` 오류 없음
