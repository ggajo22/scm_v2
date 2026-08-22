# SPEC-ORDER-026 — 코드베이스 근거 및 검증 내역

이 문서는 SPEC-ORDER-026의 모든 주장에 대한 1차 근거를 담는다. **모든 `file:line` 인용은 이 세션에서 `Read`/`Grep`으로 직접 재확인했다** — 선행 SPEC 문서(SPEC-ORDER-021/023)에 기록된 인용을 그대로 재사용하지 않았다. 선행 SPEC의 인용 중 파일 변경으로 어긋난 것이 실제로 발견되었으며(§7), 그 정정 내역도 함께 기록한다.

---

## 1. 결함 위치와 정확한 코드

### 1.1 결함 본체 — `_compute_cost_breakdown_for_rate`

`backend/order/serializers.py:31-73`. 7개 비용 필드 전부의 유일한 계산 지점이다.

원시 수량 순회(`serializers.py:36-43`, 이 세션에서 직접 읽어 확인):

```python
for item in obj.line_items.all():
    quantity = item.quantity or 0          # :37  환불 차감 없음
    grams = item.grams or 0                # :38
    total_weight_grams += grams * quantity  # :39
    total_book_count += quantity            # :40
    if item.confirmed_price is not None:    # :41
        has_any_confirmed = True            # :42
        confirmed_cost_krw += item.confirmed_price * quantity  # :43
```

- `serializers.py:37` — `item.quantity or 0`. `Refund` 행을 조회하지도, 차감하지도 않는다.
- `serializers.py:41-46` — `has_any_confirmed` 게이트. `confirmed_price`가 non-null이면 **수량과 무관하게** 참이 되고, 하나도 없으면 `None`을 반환해 7필드 전부가 `null`이 된다.
- `serializers.py:48` — `total_price_usd = Decimal(str(obj.total_price or "0"))`. **총액(gross)** 그대로이며 환불이 반영되지 않는다.
- `serializers.py:54-59` — 한국물류비: `total_book_count == 0`이면 `0`, 그 외에는 `KOREA_WAREHOUSE_BASE_KRW + KOREA_WAREHOUSE_PER_BOOK_KRW * max(total_book_count - 1, 0)`.
- `serializers.py:62` — `margin_usd = total_price_usd - confirmed_cost_usd - shipping_cost_usd - korea_warehouse_usd`. 매출 항이 gross이므로 마진이 과대 계상된다.
- `serializers.py:63` — `total_cost_usd = confirmed_cost_usd + shipping_cost_usd + korea_warehouse_usd`.
- `serializers.py:65-73` — 반환 dict 7키(`margin_usd`, `total_price_usd`, `confirmed_cost_usd`, `shipping_cost_usd`, `korea_warehouse_usd`, `total_cost_usd`, `total_weight_grams`).

비용 상수는 `serializers.py:15-17`:

| 상수 | 값 |
|------|-----|
| `SHIPPING_COST_USD_PER_KG` | `Decimal("5.45")` |
| `KOREA_WAREHOUSE_BASE_KRW` | `Decimal("1250")` |
| `KOREA_WAREHOUSE_PER_BOOK_KRW` | `Decimal("500")` |

### 1.2 소비처 2곳 (fan_in = 2, 실측)

`grep -rn "_compute_cost_breakdown_for_rate" --include=*.py` 결과 **호출 지점은 정확히 2곳**이다(정의 1곳 + 주석 2곳 제외):

| 호출 지점 | 경로 | 영향 화면 |
|-----------|------|-----------|
| `serializers.py:553` | `OrderDetailSerializer._compute_cost_breakdown_uncached` (`:542-553`) | 주문 상세 `결제 정보` 패널 |
| `serializers.py:279` | `OrderListSerializer.get_margin_rate` (`:266-288`) | 주문 목록 `마진율` 컬럼 |

- 상세 경로는 `serializers.py:513-540`의 메모이제이션(`_compute_cost_breakdown`)을 반드시 경유한다. `serializers.py:524-530`의 `@MX:NOTE`가 이를 명시한다 — "all 7 cost getters MUST go through this cache. Bypassing it ... reopens the up-to-7x ExchangeRate query multiplication AC-COST-009 (c) guards against."
- 7개 게터: `get_margin_amount`(`:555-561`), `get_margin_rate`(`:563-575`), `get_shipping_cost`(`:577-582`), `get_korea_warehouse_cost`(`:584-589`), `get_total_weight_grams`(`:591-596`), `get_confirmed_cost`(`:598-604`), `get_total_cost`(`:606-615`). 전부 `self._compute_cost_breakdown(obj)` 경유가 확인됨.
- 매출 0 게이트가 두 경로에 각각 존재: 상세 `serializers.py:570-571`, 목록 `serializers.py:283-284` (둘 다 `if total_price_usd == Decimal("0"): return None`).
- 반올림 규약: `get_total_cost` 독스트링(`serializers.py:606-615`)이 "summed from the unrounded Decimals ... and quantized here exactly once — NOT summed from the already-quantized ... fields (design decision B)"를 명시한다.

---

## 2. 왜 설계 선택이 아니라 결함인가 — 확립된 환불 순액화 관례

### 2.1 정경(canonical) ORM 패턴

`backend/order/purchase_order_views.py:332-342`(이 세션 직접 확인):

```python
refund_sum_sq = (
    Refund.objects.filter(
        order_id=OuterRef("order_id"),
        line_item_id=OuterRef("shopify_line_item_id"),   # :337
    )
    .values("order_id", "line_item_id")
    .annotate(total=Sum("quantity"))
    .values("total")[:1]
)
```

그리고 `purchase_order_views.py:366-370`:

```python
is_damaged_exchange = li.purchase_status == "damaged_exchange"   # :366
base_qty = li.damaged_quantity if is_damaged_exchange else li.quantity  # :367
net_qty = max((base_qty or 0) - li.refunded_qty, 0)               # :368  ← 하한 0
if net_qty == 0:
    continue  # Fully refunded — exclude from unordered list      # :369-370
```

핵심 관찰 2가지:
1. **조인 키는 `(order_id, shopify_line_item_id)`** — `Refund.line_item_id`는 `LineItem`의 PK가 아니라 `shopify_line_item_id`를 담는다.
2. **`max(..., 0)` 하한이 관례** — 과다 환불이 음수로 흘러가지 않는다.

### 2.2 같은 파일 안에 이미 존재하는 관례 (SPEC-ORDER-023이 추가)

`backend/order/serializers.py:179-184` — prefetch 캐시(`obj.refunds.all()`)에서 Python으로 dict를 만든다:

```python
refunded_qty: dict[int, int] = {}          # :179
for refund in obj.refunds.all():           # :180
    if refund.line_item_id is not None:     # :181  ← NULL line_item_id 스킵
        refunded_qty[refund.line_item_id] = (
            refunded_qty.get(refund.line_item_id, 0) + (refund.quantity or 0)  # :183  ← NULL quantity 내구성
        )
```

`serializers.py:165-178`의 주석은 취소 신호의 소재를 명시한다 — "That item carried `purchase_status="cs_required"`, NOT `"order_cancelled"` — **the cancellation signal lives in the Refund rows**, which is why this nets refunds instead of testing `purchase_status`."

즉 이 코드베이스에서 "환불/취소 반영"의 규범은 (a) `Refund` 행을 읽고, (b) `shopify_line_item_id`로 매칭하고, (c) `max(...,0)` 하한을 두는 것이다. 비용 경로만 이 규범을 건너뛴다.

### 2.3 [결정적] 기존 관례는 boolean 필터, 비용 경로는 산술이 필요하다

`serializers.py:186-191`:

```python
trackable = [
    li
    for li in obj.line_items.all()
    if li.sku is not None
    and (li.quantity or 0) - refunded_qty.get(li.shopify_line_item_id, 0) > 0   # :190
]
```

`_derive_line_item_states`는 순액을 **포함/제외 판정용 boolean으로만** 쓴다 — 순액이 0보다 크면 그 품목은 **원래 수량 전량으로** 남는다(`serializers.py:165-171`의 주석이 "a PARTIAL refund leaves stock still owed and is deliberately not an exclusion"로 명시).

비용 경로에는 **참(true) 순액 산술**이 필요하다. 수량 3 중 1건 환불이면 권수·무게·확정매입가가 **비례적으로 2/3로 줄어야** 한다. 구현자가 `serializers.py:186-191`의 boolean 필터를 복사하면 부분 환불 주문에서 여전히 gross 값이 나온다. 이 변이는 §5의 재현 케이스(#37454)로는 **잡히지 않는다**(그 주문에는 부분 환불 라인이 없다) — 그래서 별도 합성 시나리오가 필수다(`acceptance.md` AC-NET-002).

---

## 3. Refund 모델 — 필드 nullability와 조인 키

`backend/order/models.py:323-342`(직접 확인):

| 필드 | 정의 | 라인 |
|------|------|------|
| `order` | FK → `Order`, `related_name="refunds"` | `:324` |
| `shopify_refund_id` | `BigIntegerField()` | `:325` |
| `line_item_id` | `BigIntegerField(null=True, blank=True)` | `:328` |
| `quantity` | `IntegerField(null=True, blank=True)` | `:329` |
| `subtotal` | `DecimalField(..., null=True, blank=True)` | `:330` |
| `total_tax` | `DecimalField(..., null=True, blank=True)` | `:331` |
| `db_table` | `"orders_refund"` | `:335` |
| `unique_together` | `("order", "shopify_refund_id", "line_item_id")` | `:342` |

`models.py:336-341`의 주석: "One row per REFUNDED LINE ITEM, not per Shopify refund. ... keying on `shopify_refund_id` alone made every line item after the first unstorable, so their refunds were silently dropped and the items kept counting as live stock in every refund-netting query." → **한 주문에 같은 `line_item_id`를 가진 행이 여러 개 존재할 수 있다**(다른 `shopify_refund_id`). 따라서 순액화는 `line_item_id`별 **합산**이어야 하며 마지막 값 덮어쓰기가 아니다. `serializers.py:182-184`가 이미 `+=` 방식으로 합산한다.

`line_item_id`가 `null=True`인 것은 결함 대응이 아니라 스키마 사실이다 → §6 엣지 케이스 4의 근거.

---

## 4. 성능 제약 — prefetch는 이미 갖춰져 있다

| 소비처 | prefetch 선언 | `refunds` 포함 라인 |
|--------|---------------|---------------------|
| `OrderDetailView.get_queryset` | `backend/order/views.py:46-60` | `views.py:59` |
| `OrderListView.get_queryset` | `backend/order/views.py:262-270` | `views.py:269` |

- `views.py:53-60`: `select_related("customer", "shipping_address").prefetch_related("line_items__notes__author", "line_items__purchase_orders", "shipping_lines", "refunds")`
- `views.py:268-270`: `Order.objects.prefetch_related("refunds", "line_items", "line_items__purchase_orders", "customer").order_by("-shopify_created_at")`

따라서 `obj.refunds.all()`는 **추가 쿼리 0**이다. 반대로 `purchase_order_views.py:334-342`의 `Subquery`/`OuterRef` 패턴을 직렬화기 안으로 옮기면 주문마다 쿼리가 발생해 아래 두 불변식을 깨뜨린다.

### 4.1 지켜야 하는 쿼리 수 핀 (현재 값 실측 확인)

| 상수 | 위치 | 현재 값 | 원 SPEC |
|------|------|---------|---------|
| `ORDER_DETAIL_QUERY_COUNT` | `backend/order/tests/test_spec_021.py:48` | **8** | SPEC-ORDER-021 AC-COST-009 (`.moai/specs/SPEC-ORDER-021/spec.md:222`) |
| `TOTAL_QUERY_COUNT` | `backend/order/tests/test_spec_023.py:34` | **8** | SPEC-ORDER-023 AC-OLIST-021 (`.moai/specs/SPEC-ORDER-023/spec.md:279`) |

- SPEC-ORDER-021 AC-COST-009(c)는 "`orders_exchangerate`를 참조하는 쿼리를 정확히 1개"를 요구한다(`spec.md:222`).
- SPEC-ORDER-023 REQ-OLIST-021(`spec.md:162`)은 "without issuing any per-order or per-line-item database query"를 [HARD]로 규정한다.
- `OrderListSerializer`는 페이지당 최대 50행에서 동작한다(`OrderPagination.page_size = 50`, `views.py:159-160`; `OrderListView.pagination_class`, `views.py:260`) → 주문당 쿼리 1개는 페이지당 50개가 된다.
- 쿼리 매칭 도구는 이미 존재: `test_spec_021.py:30` `LINE_ITEM_TABLE_RE = re.compile(r"orders_line_item(?!_)")`, `test_spec_021.py:33` `EXCHANGE_RATE_TABLE = "orders_exchangerate"`, 캡처 관례는 `test_spec_021.py:268-313`(`CaptureQueriesContext` + 워밍업).
- **`orders_refund`는 다른 어떤 테이블명의 부분 문자열도 아니다** — `order/models.py`의 `db_table` 18개 전수 확인 결과 `orders_refund`로 시작하는 다른 테이블이 없다(대비: `orders_line_item`은 `orders_line_item_note`(`models.py:306`)의 접두사라서 정규식이 필요했다). 따라서 신규 AC의 `orders_refund` 매칭은 단순 `in` 검사로 안전하다.

### 4.2 메모이제이션 계약 유지

`serializers.py:513-540`의 `_compute_cost_breakdown` 캐시(주문 `pk` 단위)와 `serializers.py:524-530`의 `@MX:NOTE`가 규정하는 "7개 게터 전부가 이 캐시를 경유"는 이 SPEC에서 **변경되지 않는다**. 순액화는 `_compute_cost_breakdown_for_rate` 내부 산술만 바꾸므로 캐시 계층과 직교한다.

---

## 5. 재현 케이스 — 주문 #37454

> **출처 표기**: 아래 주문/환불/환율 값과 §8의 모집단 통계는 **이 SPEC의 조사 세션(2026-08-17)에서 프로덕션 DB에 대해 실측된 값**이다. 이 문서를 작성한 시점에 DB를 재조회하지는 않았다(원격 공유 DB에 대한 불필요한 재조회를 피함). 수치는 2026-08-17 시점 스냅샷으로 취급해야 하며, 구현 시점에 어긋나면 실측값을 신뢰하고 이 문서를 갱신한다. **반면 아래 계산 결과 20개는 이 문서 작성 중 전부 손으로 재계산해 일치를 확인했다.**

주문 사실:

| 항목 | 값 |
|------|-----|
| 주문 번호 / PK | `#37454` / `Order.pk = 3513` |
| `store_type` | `gimssine` |
| `shopify_created_at` | 2026-08-04 |
| `total_price` | 116.04 USD |
| 라인아이템 | 6건, 각 `quantity = 1` |
| 적용 `ExchangeRate` | 1427.11 KRW/USD (`effective_date` 2026-08-04) |

환불 행 2건(2026-08-14, 둘 다 해당 라인 **전량** 환불):

| `shopify_line_item_id` | `quantity` | `subtotal` | `total_tax` |
|------------------------|-----------|-----------|------------|
| 17851226325297 | 1 | 24.00 | 0.00 |
| 17851226358065 | 1 | 13.28 | 0.00 |
| **합계** | **2** | **37.28** | **0.00** |

### 5.1 현재값 vs 수정 후 (전부 재계산 확인)

| 항목 | 현재(결함) | 수정 후 | 검산 |
|------|-----------|---------|------|
| 권수 (`total_book_count`) | 6 | 4 | 6 − 2 |
| `total_weight_grams` | 4453 | 3418 | 환불 2건 합 1035g |
| 확정매입가 (KRW) | 74100 | 49500 | 환불 2건 합 24600 |
| `confirmed_cost` | 51.92 | 34.69 | 49500 / 1427.11 = 34.68549 |
| `shipping_cost` | 24.27 | 18.63 | 5.45 × 3.418 = 18.62810 |
| `korea_warehouse_cost` | 2.63 | 1.93 | (1250 + 500×3) / 1427.11 = 1.92696 |
| `total_cost` | 78.82 | 55.24 | 34.68549 + 18.62810 + 1.92696 = 55.24055 |
| 매출 기준 | 116.04 | 78.76 | 116.04 − 37.28 |
| `margin_amount` | 37.22 | 23.52 | 78.76 − 55.24055 = 23.51945 |
| `margin_rate` | 32.08 | 29.86 | 23.51945 / 78.76 × 100 = 29.86216 |

### 5.2 이 케이스의 형태와 한계

#37454는 **주문 단위로는 부분 환불, 라인 단위로는 전량 환불**이다 — 어떤 라인아이템도 부분 환불되지 않았다. 따라서 이 케이스는 §2.3의 "boolean 필터 복사" 변이를 **판별하지 못한다**(전량 환불 라인은 boolean 필터로도 산술 순액화로도 동일하게 사라진다). `acceptance.md`는 진짜 부분 환불(수량 3, 환불 1 → 순액 2) 합성 시나리오를 별도 AC로 둔다.

### 5.3 화면이 이미 자기모순 상태라는 근거

`frontend/src/pages/OrderDetailPage.tsx:159-163`(직접 확인):

```tsx
const totalRefunded = data.refunds.reduce(
  (sum, r) => sum + Number(r.subtotal ?? 0) + Number(r.total_tax ?? 0),   // :160
  0,
)
const netPaidAmount = Number(data.total_price ?? 0) - totalRefunded        // :163
```

- 프론트엔드는 `최종 결제 금액`에 `netPaidAmount`(#37454 → **78.76**)를 표시한다.
- 같은 패널의 `마진`은 백엔드가 gross 116.04로 계산한 **37.22**를 표시한다.
- `결제 정보` 섹션(`OrderDetailPage.tsx:511-513`)은 SPEC-ORDER-021 v1.3.0에서 `최종 결제 금액 → 비용 합계 → [원가/배송비/한국물류] → 마진 → 마진율` 세로 레이아웃으로 재구성되어, 이 뺄셈이 성립하는 것처럼 보이게 만든다.
- 이 불일치는 SPEC-ORDER-021 v1.3.0 HISTORY(`.moai/specs/SPEC-ORDER-021/spec.md:20`)에 "알려진 기존 불일치(수정하지 않음, 발견만 기록)"로 이미 기록되어 있다 — 당시에는 범위 밖으로 미뤘고, 이 SPEC이 그 미결 항목을 종결한다. (해당 HISTORY는 `OrderDetailPage.tsx:168`을 인용하지만 현재 파일에서는 `:163`이다 — §7 참조.)

### 5.4 부분 수정이 무수정보다 나쁜 이유 (수치 근거)

| 시나리오 | 매출 기준 | 비용 합계 | 표시 마진 | 진실(78.76 − 55.24)로부터의 거리 |
|----------|-----------|-----------|-----------|-----------------------------------|
| 현재(양쪽 gross) | 116.04 | 78.82 | 37.22 | +13.70 |
| **수량만 순액화** | 116.04 | 55.24 | **60.80** | **+37.28** ← 더 멀어진다 |
| 매출만 순액화 | 78.76 | 78.82 | −0.06 | −23.58 |
| 양쪽 순액화 (정답) | 78.76 | 55.24 | 23.52 | 0 |

수량만 고치면 오차가 13.70 → 37.28로 **2.7배 커진다**. 두 변경은 반드시 한 번에 나가야 하며 마일스톤을 쪼갤 수 없다.

---

## 6. 엣지 케이스별 코드 근거

| # | 엣지 케이스 | 코드 근거 |
|---|-------------|-----------|
| 1 | 전 라인 전량 환불 → 순권수 0 | 권수 0 분기 존재: `serializers.py:54-55`. 매출 0 게이트 2곳: `serializers.py:570-571`(상세), `:283-284`(목록) → `margin_rate`는 이미 `None`이 된다. `total_cost`/`margin_amount`는 결정 필요 |
| 2 | `has_any_confirmed` 상호작용 | `serializers.py:41-46`. 현재는 `confirmed_price is not None`만 보므로 수량과 무관하게 참. 순액화 전/후 평가 시점을 결정해야 하며, 후에 평가하면 7필드 전부 `null`로 뒤집힌다 |
| 3 | 과다 환불 하한 | 관례 존재: `purchase_order_views.py:368` `max((base_qty or 0) - li.refunded_qty, 0)` |
| 4 | `line_item_id` / `quantity` NULL | 스키마: `models.py:328`, `:329`. 기존 방어: `serializers.py:181`(NULL `line_item_id` 스킵), `:183`(`refund.quantity or 0`). 매출 항은 `subtotal`/`total_tax`(`models.py:330-331`)에 대해 **독립적으로** NULL 내구성이 필요 |
| 5 | 미매칭 환불 | 프론트엔드는 매칭 여부와 무관하게 전체 환불을 합산한다(`OrderDetailPage.tsx:159-162`는 필터가 없다). 미매칭 행은 `OrderDetailPage.tsx:491-504`에서 "상품 정보 없음"으로 별도 렌더된다. 백엔드 매출 항이 이 동작과 일치해야 두 값이 화해한다 |
| 6 | 반올림 | 설계 결정 B: `get_total_cost` 독스트링(`serializers.py:606-615`). 중간 반올림을 도입하면 T15(`test_spec_021.py:422-441`)가 검증하는 불변식이 깨진다 |

---

## 7. 선행 SPEC 인용 중 파일 변경으로 어긋난 것 (이 세션에서 정정)

`.moai/specs/SPEC-ORDER-021/`의 문서들이 인용한 아래 위치는 현재 파일에서 이동했다. **SPEC-ORDER-026은 아래 "현재" 값만 사용한다.**

| 대상 | 선행 SPEC 기재 | 현재 실측 |
|------|----------------|-----------|
| `LineItem.Meta.db_table` | `models.py:240-241` | **`models.py:250`** |
| `LineItemNote.Meta.db_table` | `models.py:297` | **`models.py:306`** |
| `ExchangeRate.Meta.db_table` | `models.py:507` | **`models.py:516`** |
| `netPaidAmount` | `OrderDetailPage.tsx:168` | **`OrderDetailPage.tsx:163`** |

`.moai/config/sections/mx.yaml`의 실측값(§9에서 사용): `limits.anchor_per_file: 3`(`mx.yaml:175`), `thresholds.fan_in_anchor: 3`(`mx.yaml:182`).

Django 버전: `backend/pyproject.toml:10` `django = "^5.0"` → prefetch 캐시가 채워진 관련 매니저의 `count()`/`exists()`도 캐시를 사용한다(`serializers.py:261,264`의 `obj.refunds.exists()`/`obj.line_items.count()`가 `test_spec_023.py:34`의 `TOTAL_QUERY_COUNT = 8`을 1건/5건 페이지 양쪽에서 만족하는 것으로 실측 확인됨 — `test_spec_023.py:638-681`).

---

## 8. 프로덕션 영향 규모 (조사 세션 2026-08-17 실측)

| 지표 | 값 |
|------|-----|
| 전체 주문 | 3,730건 |
| `margin_rate`가 non-null로 렌더되는 주문(확정매입가 ≥ 1건) | 2,847건 |
| 그중 `Refund` 행을 가진 주문 → **현재 마진 과대 계상** | **96건** |
| 전체 `Refund` 행 | 311건 |

순액 권수가 0에 도달하는 전량 환불 예: `#38416`(10 → 0), `#38368`(10 → 0), `#38372`(2 → 0).
부분 예: `#38417`(6 → 5), `#38257`(7 → 6), `#38000`(7 → 5).

---

## 9. 기존 테스트 스위트 영향 (실측)

### 9.1 `test_spec_021.py` — 무영향, 무수정

`grep -c "Refund" backend/order/tests/test_spec_021.py` → **0** (매치 없음, 종료코드 1). 이 스위트는 `Refund` 픽스처를 **단 하나도 만들지 않는다**. 따라서 모든 주문에서 gross == net이며, 아래 고정값 단정은 순액화 후에도 그대로 성립한다:

| 테스트 | 위치 | 고정값 |
|--------|------|--------|
| T1 | `test_spec_021.py:104-115` | `margin_amount "67.75"`, `korea_warehouse_cost "2.25"`(`:113`), `shipping_cost "0.00"`, `total_weight_grams 0` |
| T3 | `test_spec_021.py:141-153` | `total_weight_grams 1500`, `shipping_cost "8.18"`, `korea_warehouse_cost "2.25"`(`:151`), `margin_amount "159.58"`, `margin_rate "79.79"` |
| T12 | `test_spec_021.py:347-359` | `korea_warehouse_cost "1.80"`(`:358`), `margin_amount "68.20"` (rate 1250.00) |
| T15 | `test_spec_021.py:422-441` | `confirmed_cost "10.01"`, `shipping_cost "2.73"`, `korea_warehouse_cost "1.25"`(`:429`), `total_cost "13.98"` (≠ 13.99) |
| T9 | `test_spec_021.py:268-313` | `ORDER_DETAIL_QUERY_COUNT = 8`, `orders_line_item` 정확히 1, `orders_exchangerate` 정확히 1 |

> **[구현자 신호]** `test_spec_021.py`의 고정값을 편집하고 싶어진다면 그것은 수정이 잘못됐다는 신호다. 환불이 없는 주문의 값은 정의상 불변이어야 한다.

### 9.2 `test_spec_023.py` — 무영향, 재사용할 헬퍼 존재

- `test_ac025_detail_serializer_field_set_unchanged`(`test_spec_023.py:839-852`)는 환불 픽스처가 없다 → 단정 4건(`margin_amount "67.75"` 등) 무변경. `DETAIL_SERIALIZER_FIELDS`(`:39-58`, **45개 필드** — 이 세션에서 정규식 추출 + `set()` 카운트로 확정, 중복 0. 감사 D7 정정: 이전 버전은 세지 않고 "41개"로 적었다)도 무변경 — 이 SPEC은 필드를 추가/제거하지 않는다.
- **재사용할 헬퍼**: `_refund(line_item, quantity)`(`test_spec_023.py:866-872`)는 `order`, `shopify_refund_id`(`next(_next_line_item_id)`, `:90`의 시퀀스 재사용), `line_item_id=line_item.shopify_line_item_id`, `quantity`만 채운다 — **`subtotal`/`total_tax`를 설정하지 않는다**. 매출 순액화를 검증하려면 신규 스위트에 `subtotal`/`total_tax`를 받는 확장 헬퍼가 필요하다.
- `test_spec_021.py`의 헬퍼: `_make_order(total_price, shopify_order_id, **kwargs)`(`:69-77`), `_make_line_item(order, shopify_line_item_id, quantity=None, confirmed_price=None, grams=None)`(`:80-88`), `rate_1000`(`:92-96`), `auth_client`(`:62-66`), `DETAIL_URL`(`:23`)/`LIST_URL`(`:24`).

### 9.3 신규 파일

`backend/order/tests/test_spec_026.py` (신규). 기존 두 스위트에 테스트를 추가하지 않는다 — SPEC별 파일 분리 관례(`test_spec_018.py`, `test_spec_021.py`, `test_spec_023.py`, `test_spec_025.py`)를 따른다.

---

## 10. 백필 불필요 근거

7개 필드 전부 `SerializerMethodField`이며 읽기 시점에 계산된다(`serializers.py:555-615`, `OrderDetailSerializer` / `serializers.py:233,266-288`, `OrderListSerializer`). 저장 컬럼도, 마이그레이션도, 데이터 백필도 없다. 영향받는 96건은 **다음 조회 시 자동으로 정정된다**. `Order`/`LineItem`/`Refund` 모델에 `margin`류 컬럼이 없음을 `models.py` 전수 확인(§3의 `db_table` 목록 근거)으로 검증했다.

---

## 11. 프론트엔드 결정 근거

두 선택지:

| 선택지 | 변경 | 비용 | 편익 |
|--------|------|------|------|
| **A (권장)** 프론트 로컬 계산 유지 | 프론트엔드 변경 0 | `OrderDetailPage.tsx:159-163`와 백엔드 매출 항의 공식 중복 | `tsc` 베이스라인·픽스처 위험 0. 두 경로가 **동일 공식**이라 결과가 구조적으로 일치하며, 어긋나면 화면에서 즉시 드러나는 상호 검산이 된다 |
| B 백엔드 net revenue 필드 신설 | `DETAIL_SERIALIZER_FIELDS`(`test_spec_023.py:39-58`) 확장, 프론트 타입 + 픽스처 2곳 | 필드셋 계약 변경 → `test_spec_023.py:848`의 `set(res.data.keys()) == DETAIL_SERIALIZER_FIELDS` 단정 수정 필요. SPEC-ORDER-021 v1.4.0이 기록한 "두 번째 픽스처 누락" 함정 재발 위험(`OrderDetailPage.test.tsx` + `SearchTab.test.tsx`) | 단일 진실 소재 |

**A 채택.** 이 SPEC의 목표는 "백엔드 마진이 화면의 최종 결제 금액과 화해하게 만드는 것"이며, 그것은 백엔드가 프론트와 **동일한 공식**(`total_price − Σ(subtotal + total_tax)`, 전체 환불 행 대상, NULL은 0)을 채택하는 것만으로 달성된다. 필드 신설은 목표에 기여하지 않으면서 계약 변경 비용을 만든다. 대신 백엔드 단위 테스트에서 `margin_amount + total_cost == net revenue` 화해를 직접 단정해(`acceptance.md` AC-NET-003) 두 경로의 일치를 코드로 고정한다.

---

## 12. mx_plan 근거 — ANCHOR 한도 충돌 (실측)

`backend/order/serializers.py`의 기존 `@MX:ANCHOR`는 **3개**다(`grep -n "@MX:ANCHOR"` 실측):

| 라인 | 대상 | 근거 |
|------|------|------|
| `:93` | `_is_awaiting_purchase` 관련 "발주 대기" predicate | SPEC-ORDER-023 REQ-OLIST-013/014a, `@MX:REASON` 있음 |
| `:346` | `LineItemDetailSerializer` 필드 블록 | `@MX:REASON`은 "Extended by SPEC-ORDER-008 and SPEC-ORDER-010" — **fan_in 주장 없음** |
| `:387` | `OrderDetailSerializer` | `@MX:REASON`에 "Fan-in >= 3" 명시 |

`.moai/config/sections/mx.yaml:175`의 `limits.anchor_per_file: 3` → **이미 한도 도달**. 또한 `mx.yaml:182`의 `thresholds.fan_in_anchor: 3`에 대해 `_compute_cost_breakdown_for_rate`의 fan_in은 **2**(§1.2)로 자동 임계 미달이다.

따라서 신규 ANCHOR의 근거는 fan_in이 아니라 **불변식 계약(invariant contract)**이며(@MX 프로토콜의 ANCHOR 정의), 한도 충족을 위해 프로토콜의 "Demote excess by lowest fan_in" 규칙에 따라 `:346`을 `@MX:NOTE`로 강등하는 것이 유일한 정합적 경로다(`:346`은 세 ANCHOR 중 유일하게 fan_in 근거가 없다). 강등은 보고 의무를 수반한다 → `plan.md` mx_plan 참조.

---

## 13. 검증 완료 체크리스트

- [x] `serializers.py` 인용 20건 전부 `Read`로 직접 확인 (`:15-17`, `:20-30`, `:31-73`, `:36-43`, `:41-46`, `:48`, `:54-59`, `:62-63`, `:65-73`, `:157-213`, `:165-178`, `:179-184`, `:186-191`, `:224-288`, `:266-288`, `:283-284`, `:500-540`, `:524-530`, `:542-553`, `:555-615`, `:570-571`, `:606-615`)
- [x] `views.py:46-60`, `:262-270` 확인 — `refunds` prefetch 양쪽 존재
- [x] `purchase_order_views.py:332-342`, `:366-370` 확인
- [x] `models.py:323-342` 확인 — 4개 필드 nullability + `db_table` + `unique_together`
- [x] `models.py` `db_table` 18개 전수 확인 — `orders_refund` 접두사 충돌 없음
- [x] `OrderDetailPage.tsx:159-163`, `:170-179`, `:491-504`, `:511-513` 확인
- [x] `test_spec_021.py`에 `Refund` 매치 0건 (`grep -c` 실측)
- [x] `test_spec_021.py:30,33,48,62-66,69-77,80-88,92-96,104-115,141-153,268-313,347-359,422-441` 확인
- [x] `test_spec_023.py:24-25,34,39-58,638-681,839-852,866-872` 확인
- [x] `_compute_cost_breakdown_for_rate` fan_in = 2 (`grep -rn` 전역 실측)
- [x] `mx.yaml:175,182` 실측 + `serializers.py` 기존 ANCHOR 3개 실측
- [x] `pyproject.toml:10` Django `^5.0` 확인
- [x] #37454 계산 20개 손 재계산 일치
- [x] 선행 SPEC 인용 어긋남 4건 발견·정정 (§7)
- [ ] §8 모집단 통계 4건 + #37454 원본 사실 — 조사 세션 실측값을 그대로 인용(이 문서 작성 중 DB 재조회 안 함, 출처 명시)
