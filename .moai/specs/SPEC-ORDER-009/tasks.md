---
spec_id: SPEC-ORDER-009
version: "1.0.0"
created: 2026-06-27
methodology: TDD (RED-GREEN-REFACTOR)
status: ready
---

# SPEC-ORDER-009 Task Decomposition

## TDD Cycle Order (Implementation Sequence)

```
TASK-001 (RED — 실패 테스트 작성)
       ↓
TASK-002 (GREEN — ExchangeRate 모델 + 마이그레이션)
       ↓
TASK-003 (GREEN — 환율 API: serializer + views + urls)
       ↓
TASK-004 (MODIFY — 마진 계산 수정: get_margin_amount + get_margin_rate)
       ↓
TASK-005 (REFACTOR + 통합 검증)
```

TASK-001 (RED)은 반드시 먼저 완료해야 한다. TASK-002와 TASK-003은 모델이 먼저 존재해야 하므로 순차 실행한다. TASK-004는 TASK-002 완료 이후에 진행한다 (`ExchangeRate` import 필요). TASK-005는 전체 완료 후 진행한다.

---

## TASK-001 — 실패 테스트 작성 (RED)

**REQ 매핑**: REQ-001 ~ REQ-013 (전체 커버)

**의존성**: 없음 (최초 시작점)

**파일**:
- `backend/order/tests/test_spec_009.py` [CREATE]

**작업 내용**:

신규 테스트 파일을 생성하고, 아직 구현되지 않은 기능에 대한 실패 테스트를 작성한다.
기존 `test_spec_008.py` 패턴(`pytest.mark.django_db`, `APIClient`, JWT Bearer token)을 따른다.

### Fixtures

```python
@pytest.fixture
def exchange_rate_2026_01_15(db):
    """2026-01-15 환율: 1 USD = 1300.00 KRW"""
    return ExchangeRate.objects.create(
        effective_date="2026-01-15",
        rate=Decimal("1300.00"),
        source="manual",
    )

@pytest.fixture
def exchange_rate_2026_01_10(db):
    """2026-01-10 환율: 1 USD = 1280.00 KRW (폴백 테스트용)"""
    return ExchangeRate.objects.create(
        effective_date="2026-01-10",
        rate=Decimal("1280.00"),
        source="manual",
    )

@pytest.fixture
def order_with_confirmed_items_usd(db):
    """
    total_price = 100.00 USD, shopify_created_at = 2026-01-15
    line_item A: confirmed_price=50000 KRW, quantity=2
    line_item B: confirmed_price=null
    """
    from django.utils import timezone
    import datetime
    order = Order.objects.create(
        shopify_order_id=99020,
        store_type="gimssine",
        financial_status="paid",
        total_price="100.00",
        shopify_created_at=timezone.make_aware(
            datetime.datetime(2026, 1, 15, 12, 0, 0)
        ),
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=12010,
        title="상품 A", quantity=2, price="50.00",
        confirmed_price="50000.00", confirmed_distributor="bookseen",
    )
    LineItem.objects.create(
        order=order, shopify_line_item_id=12011,
        title="상품 B", quantity=1, price="50.00",
        confirmed_price=None, confirmed_distributor=None,
    )
    return order
```

### 추가할 테스트 케이스

```
# Module 3: 마진 계산 수정
test_margin_uses_exchange_rate_for_krw_conversion     # REQ-010, REQ-012
test_margin_fallback_to_prior_date_rate               # REQ-003, REQ-012
test_margin_null_when_no_exchange_rate                # REQ-011

# Module 2: 환율 API
test_exchange_rate_list_returns_200                   # REQ-004
test_exchange_rate_create_returns_201                 # REQ-005
test_exchange_rate_retrieve_returns_200               # REQ-006
test_exchange_rate_update_returns_200                 # REQ-007
test_exchange_rate_delete_returns_204                 # REQ-008
test_exchange_rate_duplicate_date_returns_400         # REQ-009
test_exchange_rate_unauthenticated_returns_401        # 인증 제약 검증
```

**완료 기준**: `pytest backend/order/tests/test_spec_009.py -v` 실행 시 전체 테스트가 FAIL 또는 ImportError 상태 (모델·뷰 미존재)

---

## TASK-002 — ExchangeRate 모델 + 마이그레이션 (GREEN)

**REQ 매핑**: REQ-001, REQ-002

**의존성**: TASK-001 완료

**파일**:
- `backend/order/models.py` [MODIFY] — `ExchangeRate` 모델 추가
- `backend/order/migrations/0017_create_exchange_rate.py` [CREATE]

**작업 내용**:

### 2-A: models.py에 ExchangeRate 추가

`backend/order/models.py` 파일 하단 (기존 모델 이후)에 추가:

```python
class ExchangeRate(models.Model):
    """
    Daily USD/KRW exchange rate for margin calculation.
    One record per day; effective_date is unique.
    """
    effective_date = models.DateField(unique=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders_exchangerate"
        indexes = [models.Index(fields=["effective_date"])]

    def __str__(self):
        return f"{self.effective_date}: {self.rate} KRW/USD"
```

### 2-B: 마이그레이션 파일 생성

`python manage.py makemigrations order --name create_exchange_rate` 실행으로 자동 생성하거나 수동 작성.

- 파일명: `0017_create_exchange_rate.py`
- 직전 의존: `('order', '0016_add_sungseoyunion_distributor')`

**완료 기준**:
```
python manage.py migrate --run-syncdb  (또는 migrate)
pytest backend/order/tests/test_spec_009.py -k "exchange_rate" --co  # 수집만 확인
```

---

## TASK-003 — 환율 API (GREEN: Serializer + Views + URLs)

**REQ 매핑**: REQ-004 ~ REQ-009

**의존성**: TASK-002 완료 (`ExchangeRate` 모델 존재)

**파일**:
- `backend/order/serializers.py` [MODIFY] — `ExchangeRateSerializer` 추가
- `backend/order/views.py` [MODIFY] — `ExchangeRateListCreateView`, `ExchangeRateDetailView` 추가
- `backend/order/urls.py` [MODIFY] — exchange rate URL 등록

**작업 내용**:

### 3-A: ExchangeRateSerializer (serializers.py)

기존 serializer 파일 하단에 추가:

```python
class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ["effective_date", "rate", "source", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]
```

`unique=True`가 모델에 적용되어 있으므로 DRF가 자동으로 `UniqueValidator`를 붙인다 (REQ-009).

### 3-B: ExchangeRateListCreateView (views.py)

```python
class ExchangeRateListCreateView(generics.ListCreateAPIView):
    queryset = ExchangeRate.objects.all().order_by('-effective_date')
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
```

### 3-C: ExchangeRateDetailView (views.py)

```python
class ExchangeRateDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExchangeRate.objects.all()
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "effective_date"
    lookup_url_kwarg = "date"
```

### 3-D: urls.py 등록

기존 urlpatterns에 추가:

```python
path("exchange-rates/", ExchangeRateListCreateView.as_view(), name="exchange-rate-list"),
path("exchange-rates/<str:date>/", ExchangeRateDetailView.as_view(), name="exchange-rate-detail"),
```

**완료 기준**:
```
pytest backend/order/tests/test_spec_009.py -k "exchange_rate" -v
# REQ-004~REQ-009 관련 테스트 전체 통과
```

---

## TASK-004 — 마진 계산 수정 (MODIFY: get_margin_amount + get_margin_rate)

**REQ 매핑**: REQ-003, REQ-010, REQ-011, REQ-012, REQ-013

**의존성**: TASK-002 완료 (`ExchangeRate` 모델 import 가능)

**파일**:
- `backend/order/serializers.py` [MODIFY]

**작업 내용**:

### 4-A: Import 추가

`backend/order/serializers.py` 상단 import 블록에 추가:

```python
from .models import ExchangeRate
```

### 4-B: OrderDetailSerializer에 _get_exchange_rate 헬퍼 추가

```python
def _get_exchange_rate(self, obj):
    """
    Look up exchange rate for order date with fallback to prior date.
    Returns ExchangeRate instance or None.
    REQ-003, REQ-013
    """
    order_date = obj.shopify_created_at.date() if obj.shopify_created_at else None
    if order_date is None:
        return None
    return ExchangeRate.objects.filter(
        effective_date__lte=order_date
    ).order_by('-effective_date').first()
```

### 4-C: get_margin_amount 수정 (lines 127-154 교체)

```python
def get_margin_amount(self, obj):
    """
    REQ-010, REQ-011:
    - USD total_price를 환율로 KRW 환산 후 confirmed_cost_krw 차감
    - 환율 없으면 None 반환
    - confirmed_price=null 항목은 부분 합산에서 제외
    """
    er = self._get_exchange_rate(obj)
    if er is None:
        return None
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
```

### 4-D: get_margin_rate 수정

```python
def get_margin_rate(self, obj):
    """
    REQ-012, REQ-013:
    - 분모는 total_price_krw (KRW 환산값)
    - 환율 재조회 (캐시 없으므로 2회 쿼리 — NOTE 참조)
    """
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

> **NOTE (REQ-013)**: `_get_exchange_rate`는 `get_margin_amount`와 `get_margin_rate`에서 각각 1회씩 DB를 조회한다. API 호출당 최대 2 쿼리이며 허용 범위다. 향후 고트래픽 요구 시 `SerializerContext` 캐싱으로 개선 가능.

**완료 기준**:
```
pytest backend/order/tests/test_spec_009.py -k "margin" -v
# REQ-010~REQ-013 관련 테스트 전체 통과
```

---

## TASK-005 — REFACTOR + 통합 검증

**REQ 매핑**: 전체

**의존성**: TASK-004 완료

**파일**:
- `backend/order/serializers.py` (검토)
- `backend/order/tests/test_spec_009.py` (검토)

**작업 내용**:

### 검토 체크리스트

1. `_get_exchange_rate` 메서드가 `get_margin_amount`와 `get_margin_rate` 두 곳에서 동일한 쿼리를 실행하는지 확인
2. `Decimal(str(item.confirmed_price))` 변환이 `DecimalField` 출력값(`Decimal`)을 문자열로 거쳤다가 다시 `Decimal`로 변환하는 불필요한 과정인지 검토 → `item.confirmed_price`가 이미 `Decimal`이므로 직접 사용 가능
3. `obj.line_items.all()` 호출이 `prefetch_related`로 커버되는지 확인 (`OrderDetailView`의 `queryset` 확인)
4. `total_price`가 `None`인 경우 처리: `str(obj.total_price or "0")` 패턴 유지 확인
5. `ExchangeRate` import가 순환 참조를 일으키지 않는지 확인 (`models.py` → `serializers.py` 방향 정상)

### 수정 권장 사항

```python
# BEFORE (불필요한 str 변환)
confirmed_cost_krw += Decimal(str(item.confirmed_price)) * (item.quantity or 0)

# AFTER (DecimalField 직접 사용)
confirmed_cost_krw += item.confirmed_price * (item.quantity or 0)
```

### 기존 테스트 회귀 검증

```
pytest backend/order/tests/ -v
# SPEC-ORDER-008 관련 기존 테스트 회귀 없음 확인
# 특히 margin_amount, margin_rate 관련 기존 테스트가 환율 없는 상황에서 null 반환으로 변경됨 — 기존 픽스처 조정 필요
```

> **주의**: SPEC-ORDER-008 기존 테스트(`test_spec_008.py`)에서 `margin_amount` 값을 하드코딩으로 검증하는 테스트 케이스가 있다면 환율 데이터 fixture 추가 없이는 실패할 수 있다. 해당 테스트를 `margin_amount = null` (환율 없음) 또는 환율 fixture를 주입하는 방식으로 조정해야 한다.

**완료 기준**:
```
pytest backend/order/tests/test_spec_009.py -v     # 전체 통과
pytest backend/order/tests/ -v                     # 회귀 없음 (또는 조정된 기존 테스트 통과)
```

---

## 위험 매트릭스

| 위험 | 발생 시나리오 | 대응 전략 |
|------|-------------|----------|
| SPEC-ORDER-008 테스트 회귀 | 기존 테스트가 `margin_amount`를 환율 없이 검증 | TASK-005에서 기존 테스트 픽스처에 환율 추가 또는 null 기대값으로 조정 |
| Decimal 정밀도 | `total_price * rate` 부동소수점 오차 | `Decimal` 타입 유지 — `float()` 변환 금지 |
| `shopify_created_at = None` 엣지 케이스 | 주문일 없는 주문에서 `order_date = None` → 환율 조회 불가 | `_get_exchange_rate`에서 `None` 반환 처리 (REQ-011 경로로 수렴) |
| URL 충돌 | `/api/exchange-rates/<str:date>/` 가 다른 URL 패턴과 충돌 | `exchange-rates/` prefix로 기존 URL과 분리됨 — 충돌 없음 |
| 마이그레이션 순서 오류 | `0017`이 `0016`을 의존하지 않을 경우 | `dependencies = [('order', '0016_add_sungseoyunion_distributor')]` 명시 |
| `confirmed_price = Decimal("0")` falsy 오동작 | `if item.confirmed_price` 가 0을 제외 | `if item.confirmed_price is not None` 으로 명시적 null 체크 사용 |

---

## 레퍼런스 구현 (기존 코드 패턴)

| 패턴 | 위치 | 적용 태스크 |
|------|------|------------|
| `BookseenData` 모델 패턴 | `backend/order/models.py` | TASK-002 (db_table, DecimalField, auto_now_add/auto_now) |
| `SerializerMethodField` 패턴 | `backend/order/serializers.py` line 97 (`get_has_refund`) | TASK-004 |
| `generics.ListCreateAPIView` 패턴 | `backend/order/views.py` | TASK-003 |
| JWT 인증 테스트 패턴 | `backend/order/tests/test_spec_008.py` | TASK-001 |
| `APIClient` + Bearer token | `backend/order/tests/test_spec_008.py` | TASK-001 |
| `prefetch_related("line_items")` | `backend/order/views.py` (OrderDetailView) | TASK-004 (N+1 방지 전제 조건) |
