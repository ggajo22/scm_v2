---
id: SPEC-ORDER-009
version: "1.0.0"
status: draft
created: 2026-06-27
updated: 2026-06-27
author: ggajo
priority: high
related_spec: SPEC-ORDER-008
---

## HISTORY

| 버전  | 날짜       | 작성자 | 변경 내용                                                          |
|-------|------------|--------|--------------------------------------------------------------------|
| 1.0.0 | 2026-06-27 | ggajo  | 최초 작성 — 환율 테이블 및 주문일 기준 USD→KRW 환율 적용 마진 계산 |

---

## 문제 정의

`SPEC-ORDER-008`에서 구현된 마진 계산 로직(`get_margin_amount`, `get_margin_rate`)은 통화 단위 불일치 버그를 포함하고 있다. 구체적으로 `backend/order/serializers.py`의 `get_margin_amount` 메서드(lines 127–154)에서 Shopify에서 동기화된 `total_price`(USD 단위)와 국내 유통사(Bookseen, 교보문고)의 `confirmed_price`(KRW 단위)를 환율 변환 없이 직접 빼서 마진을 계산한다.

이 버그로 인해 마진 금액 및 마진율이 수치적으로 무의미한 값을 반환하며, 수익성 판단의 근거로 사용될 수 없다.

---

## 목표

1. 일별 USD/KRW 환율을 저장하는 `ExchangeRate` 모델 및 REST API를 신설한다.
2. 주문일(`shopify_created_at.date()`) 기준 환율을 조회하여 `total_price`(USD)를 KRW로 환산한 후 마진을 계산하도록 `get_margin_amount`와 `get_margin_rate`를 수정한다.
3. 해당 주문일의 환율 데이터가 없을 경우 가장 최근 이전 날짜의 환율을 폴백으로 사용한다.
4. 마진 관련 모든 금액은 KRW 단위로 통일한다.

---

## 관련 SPEC

- `SPEC-ORDER-008` v1.0.0 — 마진 계산 필드 최초 구현 (통화 불일치 버그 포함) — 본 SPEC으로 수정됨

---

## 요구사항 (EARS 형식)

### Module 1: ExchangeRate 모델

**REQ-001 [CREATE]** The system **shall** provide an `ExchangeRate` model with the following fields:
- `effective_date`: `DateField(unique=True)` — 환율 적용 날짜 (하루 1건)
- `rate`: `DecimalField(max_digits=10, decimal_places=2)` — 1 USD 기준 KRW 금액 (예: `1300.50`)
- `source`: `CharField(max_length=50, default="manual")` — 환율 출처
- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

The model **shall** use `db_table = "orders_exchangerate"` and define an index on `effective_date`.

**REQ-002 [CREATE]** The `ExchangeRate` model **shall** enforce `unique=True` on `effective_date` at the database level (한 날짜에 환율 1건만 허용).

**REQ-003 [DEFINE]** When the system looks up an exchange rate for a given `order_date`, the system **shall** query `ExchangeRate.objects.filter(effective_date__lte=order_date).order_by('-effective_date').first()` to return the most recent rate on or before the order date (폴백 포함).

---

### Module 2: 환율 REST API

**REQ-004 [CREATE]** When an authenticated user sends `GET /api/exchange-rates/`, the system **shall** return a list of all `ExchangeRate` records ordered by `effective_date` descending (최신순).

**REQ-005 [CREATE]** When an authenticated user sends `POST /api/exchange-rates/` with valid `effective_date` and `rate` fields, the system **shall** create and return the new `ExchangeRate` record with HTTP 201.

**REQ-006 [CREATE]** When an authenticated user sends `GET /api/exchange-rates/{date}/` (YYYY-MM-DD), the system **shall** return the `ExchangeRate` record for that date with HTTP 200, or HTTP 404 if not found.

**REQ-007 [CREATE]** When an authenticated user sends `PUT /api/exchange-rates/{date}/`, the system **shall** update the `rate` field of the matching `ExchangeRate` record and return the updated record with HTTP 200.

**REQ-008 [CREATE]** When an authenticated user sends `DELETE /api/exchange-rates/{date}/`, the system **shall** delete the matching `ExchangeRate` record and return HTTP 204.

**REQ-009 [CONSTRAINT]** If a `POST /api/exchange-rates/` request contains an `effective_date` that already exists in the database, then the system **shall** return HTTP 400 with a field-level validation error (DRF `UniqueValidator` via `unique=True` on model).

---

### Module 3: 마진 계산 수정

**REQ-010 [MODIFY]** When computing `margin_amount`, the system **shall** first retrieve the exchange rate for the order's `shopify_created_at.date()` using the fallback query defined in REQ-003, then apply the formula:

```
total_price_krw = Decimal(obj.total_price) * exchange_rate.rate
confirmed_cost_krw = sum(confirmed_price * quantity for line items where confirmed_price IS NOT NULL)
margin_amount = total_price_krw - confirmed_cost_krw
```

모든 금액의 단위는 KRW이다.

**REQ-011 [MODIFY]** If the fallback exchange rate query (REQ-003) returns no result, then the system **shall** return `null` for `margin_amount` (환율 데이터 부재 시 계산 불가).

**REQ-012 [MODIFY]** When computing `margin_rate`, the system **shall** use `total_price_krw` (USD를 KRW로 환산한 값) as the denominator:

```
margin_rate = (margin_amount / total_price_krw) * 100  [소수점 2자리 반올림]
```

`total_price_krw == 0` 또는 `margin_amount == null`이면 `null`을 반환한다.

**REQ-013 [CONSTRAINT]** The exchange rate lookup in `get_margin_rate` **shall** reuse the rate object already fetched in `get_margin_amount` to avoid redundant database queries (NOTE: 구현 시 캐시 또는 헬퍼 메서드로 중복 쿼리 방지).

---

## 인수 기준 (Acceptance Criteria)

상세 시나리오는 `acceptance.md` 참조.

| REQ | 인수 기준 요약 | acceptance.md 시나리오 |
|-----|---------------|------------------------|
| REQ-001 | `ExchangeRate` 모델이 DB에 존재하며 `orders_exchangerate` 테이블로 마이그레이션된다 | 시나리오 4 |
| REQ-002 | 동일 `effective_date` 중복 생성 시 DB 레벨 오류 발생 | 시나리오 5 |
| REQ-003 | 주문일 이전 가장 최근 환율이 조회된다 | 시나리오 2 |
| REQ-004 | `GET /api/exchange-rates/` 가 최신순 목록을 반환한다 | 시나리오 4 |
| REQ-005 | `POST /api/exchange-rates/` 가 신규 환율을 생성하고 201을 반환한다 | 시나리오 4 |
| REQ-006 | `GET /api/exchange-rates/{date}/` 가 단건 조회를 반환한다 | 시나리오 4 |
| REQ-007 | `PUT /api/exchange-rates/{date}/` 가 환율을 수정하고 200을 반환한다 | 시나리오 4 |
| REQ-008 | `DELETE /api/exchange-rates/{date}/` 가 환율을 삭제하고 204를 반환한다 | 시나리오 4 |
| REQ-009 | 중복 날짜 `POST` 시 HTTP 400이 반환된다 | 시나리오 5 |
| REQ-010 | `margin_amount`가 `total_price(USD) * rate - confirmed_cost(KRW)` 로 정확히 계산된다 | 시나리오 1 |
| REQ-011 | 환율 레코드가 전혀 없을 때 `margin_amount = null`이 반환된다 | 시나리오 3 |
| REQ-012 | `margin_rate`가 `(margin_amount / total_price_krw) * 100` 으로 계산된다 | 시나리오 1, 2 |
| REQ-013 | 환율 조회가 단일 쿼리로 실행된다 (N+1 방지) | 시나리오 1 |

---

## 기술 설계

### ExchangeRate 모델 설계

```python
class ExchangeRate(models.Model):
    effective_date = models.DateField(unique=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_exchangerate"
        indexes = [models.Index(fields=["effective_date"])]
```

### 마이그레이션

- 파일: `backend/order/migrations/0017_create_exchange_rate.py`
- 직전 마이그레이션: `0016_add_sungseoyunion_distributor`

### API 엔드포인트 설계

| Method | URL | View | 설명 |
|--------|-----|------|------|
| GET | `/api/exchange-rates/` | `ExchangeRateListCreateView` | 목록 (최신순) |
| POST | `/api/exchange-rates/` | `ExchangeRateListCreateView` | 생성 |
| GET | `/api/exchange-rates/{date}/` | `ExchangeRateDetailView` | 단건 조회 |
| PUT | `/api/exchange-rates/{date}/` | `ExchangeRateDetailView` | 수정 |
| DELETE | `/api/exchange-rates/{date}/` | `ExchangeRateDetailView` | 삭제 |

- URL lookup field: `effective_date` (YYYY-MM-DD 형식)
- 인증: JWT Bearer token (기존 패턴과 동일)

### 마진 계산 수정 핵심 로직

```python
def _get_exchange_rate(self, obj):
    """주문일 기준 환율 조회 (폴백 포함). 캐시용 헬퍼."""
    order_date = obj.shopify_created_at.date() if obj.shopify_created_at else None
    if order_date is None:
        return None
    return ExchangeRate.objects.filter(
        effective_date__lte=order_date
    ).order_by('-effective_date').first()

def get_margin_amount(self, obj):
    er = self._get_exchange_rate(obj)
    if er is None:
        return None
    # Accumulate confirmed cost in KRW
    confirmed_cost_krw = Decimal("0")
    has_any_confirmed = False
    for item in obj.line_items.all():
        if item.confirmed_price is not None:
            has_any_confirmed = True
            confirmed_cost_krw += Decimal(str(item.confirmed_price)) * (item.quantity or 0)
    if not has_any_confirmed:
        return None
    total_price_krw = Decimal(str(obj.total_price or "0")) * er.rate
    return str(total_price_krw - confirmed_cost_krw)

def get_margin_rate(self, obj):
    margin_str = self.get_margin_amount(obj)
    if margin_str is None:
        return None
    er = self._get_exchange_rate(obj)
    if er is None:
        return None
    total_price_krw = Decimal(str(obj.total_price or "0")) * er.rate
    if total_price_krw == Decimal("0"):
        return None
    rate = (Decimal(margin_str) / total_price_krw * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return str(rate)
```

> **NOTE (REQ-013)**: `_get_exchange_rate` 헬퍼는 동일 직렬화 컨텍스트 내에서 호출되므로 `get_margin_amount`와 `get_margin_rate`가 각각 DB를 1회씩 조회한다. API 응답 1건당 최대 2 쿼리이며, Django ORM 캐시가 없으므로 성능상 허용 범위다. 고트래픽 최적화가 필요한 경우 `SerializerContext`에 환율 객체를 캐시하는 패턴으로 개선 가능하다.

---

## 제약사항

- `admin.py`가 order 앱에 존재하지 않으므로 `ExchangeRate` admin 등록은 본 SPEC 범위에 포함하지 않는다.
- 환율 데이터는 수동 입력(`source="manual"`) 방식만 지원한다. 외부 API 자동 수집은 본 SPEC 범위 외다.
- 마진 계산 결과는 DB 저장 없이 런타임 계산(`SerializerMethodField`)으로 반환한다.
- `confirmed_price = null`인 line item은 매입 원가 합산에서 제외한다 (부분 합산 허용, SPEC-ORDER-008 REQ-006 패턴 유지).
- 기존 `SPEC-ORDER-008`에서 구현된 프론트엔드(TypeScript 타입, UI 표시)는 변경하지 않는다. 백엔드 직렬화 수정만으로 프론트엔드가 자동으로 올바른 KRW 마진 값을 수신한다.

---

## Exclusions (What NOT to Build)

- **환율 자동 수집**: 외부 환율 API(한국은행, Open Exchange Rates 등)로부터 환율을 자동으로 가져오는 스케줄러·크론잡은 구현하지 않는다.
- **환율 Admin UI**: Django Admin 또는 React Admin 화면을 통한 환율 관리 UI를 구현하지 않는다.
- **환율 이력 관리**: `ExchangeRate` 수정 이력(버전 관리, 변경 로그)을 저장하는 기능을 구현하지 않는다.
- **프론트엔드 환율 입력 화면**: `/exchange-rates` 관리 페이지(React)를 구현하지 않는다. API만 제공한다.
- **다중 통화 지원**: USD→KRW 단방향 변환만 지원한다. EUR, JPY 등 추가 통화는 포함하지 않는다.
- **마진 기반 필터/정렬**: 주문 목록 페이지의 마진 기준 필터·정렬 기능은 포함하지 않는다.
- **`margin_amount` / `margin_rate` DB 저장**: 런타임 계산으로 유지하며 DB 컬럼화하지 않는다.
