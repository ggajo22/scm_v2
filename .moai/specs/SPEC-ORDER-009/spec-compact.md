# SPEC-ORDER-009 Compact — 환율 테이블 및 USD→KRW 마진 계산 수정

## Requirements

### Module 1: ExchangeRate 모델

| ID | 요약 |
|----|------|
| REQ-001 | `ExchangeRate` 모델 생성: `effective_date(unique)`, `rate(Decimal 10,2)`, `created_at`, `updated_at`. `db_table="orders_exchangerate"` [CREATE] |
| REQ-002 | `effective_date` DB 레벨 `unique=True` 강제 (날짜별 1건) |
| REQ-003 | 환율 폴백 조회: `filter(effective_date__lte=order_date).order_by('-effective_date').first()` |

### Module 2: 환율 REST API

| ID | 요약 |
|----|------|
| REQ-004 | `GET /api/exchange-rates/` — 인증 후 목록 반환 (최신순) [CREATE] |
| REQ-005 | `POST /api/exchange-rates/` — 인증 후 생성, HTTP 201 [CREATE] |
| REQ-006 | `GET /api/exchange-rates/{date}/` — 단건 조회, HTTP 200 or 404 [CREATE] |
| REQ-007 | `PUT /api/exchange-rates/{date}/` — 수정, HTTP 200 [CREATE] |
| REQ-008 | `DELETE /api/exchange-rates/{date}/` — 삭제, HTTP 204 [CREATE] |
| REQ-009 | 중복 `effective_date` POST → HTTP 400 (DRF UniqueValidator) |

### Module 3: 마진 계산 수정

| ID | 요약 |
|----|------|
| REQ-010 | `get_margin_amount`: `total_price(USD) * rate → KRW`, 이후 `confirmed_cost_krw` 차감 [MODIFY] |
| REQ-011 | 환율 레코드 없으면 `margin_amount = null` 반환 |
| REQ-012 | `get_margin_rate`: 분모를 `total_price_krw` (KRW 환산값) 로 사용 [MODIFY] |
| REQ-013 | 환율 조회 중복 방지 — `_get_exchange_rate()` 헬퍼로 캐시 (N+1 방지 NOTE) |

---

## Acceptance Criteria (요약)

| 시나리오 | 적용 REQ | 검증 대상 |
|----------|----------|-----------|
| 시나리오 1 | REQ-010, REQ-012, REQ-013 | 주문일 환율 존재 시 KRW 기준 마진 정확성 |
| 시나리오 2 | REQ-003, REQ-011, REQ-012 | 주문일 환율 없을 때 이전 날짜 폴백 사용 |
| 시나리오 3 | REQ-011 | 환율 레코드 전혀 없을 때 margin = null |
| 시나리오 4 | REQ-001~REQ-008 | 환율 CRUD API 정상 동작 |
| 시나리오 5 | REQ-002, REQ-009 | 중복 날짜 POST → 400 오류 |

---

## Exclusions

- 환율 자동 수집 (외부 API) 금지
- 환율 Admin/Frontend UI 금지
- 환율 수정 이력 관리 금지
- EUR/JPY 등 추가 통화 금지
- `margin_amount` / `margin_rate` DB 저장 금지
- 마진 기반 필터/정렬 금지

---

## Files Impacted

```
backend/order/models.py                                    [MODIFY]
backend/order/migrations/0017_create_exchange_rate.py      [CREATE]
backend/order/serializers.py                               [MODIFY]
backend/order/views.py                                     [MODIFY]
backend/order/urls.py                                      [MODIFY]
backend/order/tests/test_spec_009.py                       [CREATE]
```
