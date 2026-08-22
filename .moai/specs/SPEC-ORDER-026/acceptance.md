# SPEC-ORDER-026 — 인수 기준 (Acceptance Criteria)

대상 파일: `backend/order/tests/test_spec_026.py` `[NEW]`

## 0. 이 문서를 읽는 방법 — 판별력(mutation discrimination) 규약

[HARD] 이 프로젝트는 과거에 **판별력 없는 AC**를 출하한 적이 있다(SPEC-ORDER-023 v1.4.0 HISTORY: 픽스처가 `PurchaseOrder`를 만들지 않아 `purchase_status`만 봐도 정답이 나왔고, 그 결과 프로덕션 97.5% 오표시를 감사 3라운드가 놓쳤다). 따라서 **모든 AC는 자신이 잡는 변이(mutation)를 명시한다.** 순액화를 삭제해도 통과하는 AC는 가치가 0이다.

이 SPEC이 반드시 잡아야 하는 **11개** 변이:

| ID | 변이 | 주 판별 AC |
|----|------|-----------|
| **M1** | 순액화 전체 삭제 (양쪽 gross 복귀) | AC-NET-001, AC-NET-002 |
| **M2** | 수량만 순액화 (매출은 gross) | AC-NET-001, AC-NET-002, AC-NET-003 |
| **M3** | 매출만 순액화 (수량은 gross) | AC-NET-001, AC-NET-002 |
| **M4** | **boolean 필터 복사** — 순액 > 0이면 원래 수량 전량 유지 (`serializers.py:186-191` 패턴) | **AC-NET-002 (유일)** |
| **M5** | `max(..., 0)` 하한 삭제 (수량 측 / 매출 측) | AC-NET-006a / AC-NET-006b |
| **M6** | 주문당 쿼리 도입 (`Subquery`/`OuterRef` 또는 `obj.refunds.filter(...)`) | AC-NET-009, AC-NET-010 |
| **M7** | 중간 반올림 도입 | AC-NET-012 |
| **M8** | 조인 키를 `LineItem.pk`로 잘못 사용 | AC-NET-002 (§0.1 픽스처 규약 전제) |
| **M9** | 공유 함수가 아닌 한쪽 소비처에만 순액화 적용 | AC-NET-011 |
| **M10** | **합산 → 덮어쓰기** — `refunded_qty[id] = (refund.quantity or 0)` (누적 `+=` 대신 대입) | **AC-NET-015 (유일)** |
| **M11** | 메모이제이션 우회 — 게터마다 `_compute_cost_breakdown_uncached`를 직접 호출 | **AC-NET-016 (유일)** — 쿼리 수로는 관측 불가 |

> **M10이 왜 별도 축인가** (감사 D2): `models.py:342`의 `unique_together = ("order", "shopify_refund_id", "line_item_id")`와 `:336-341` 주석은 **한 라인아이템에 여러 `Refund` 행이 존재 가능함**을 스키마 사실로 못 박고, `spec.md` 가정 A3이 "따라서 합산이어야 한다 — 마지막 값 덮어쓰기가 아니다"를 명시한다. 그런데 최초 버전의 AC 15개 중 **같은 `line_item_id`에 환불 2행을 붙인 픽스처가 하나도 없었다** — AC-NET-001은 서로 **다른** 라인 2건, AC-NET-007은 서로 **다른** 3건이다. 따라서 덮어쓰기 변이가 15개 AC 전부를 통과했다. 프로덕션의 분할 환불(같은 라인, 다른 `shopify_refund_id`)이 정확히 이 형태이며, 덮어쓰기는 순액을 과대 평가해 **이 SPEC이 고치려는 결함과 같은 방향으로** 마진을 다시 과대 계상한다. 참고: **매출 측** 합산은 AC-NET-001(2행)·AC-NET-007(3행)이 이미 커버하며, 미커버였던 것은 **수량 측 누적**뿐이다.
>
> **M11이 왜 쿼리 수로 안 잡히는가** (감사 D1): 순액화는 `obj.refunds.all()` **prefetch 캐시**를 읽으므로 7번 반복해도 `orders_refund` 쿼리는 1건이다(REQ-NET-030의 전제 그 자체). 그리고 `_get_exchange_rate`는 `serializers.py:466-498`에서 **독립적으로 메모이즈**되어 있어 `_compute_cost_breakdown_uncached`를 7번 호출해도 `orders_exchangerate` 쿼리도 1건이다. 즉 M11은 총 쿼리 수·`orders_refund` 수·`orders_exchangerate` 수를 **전혀 바꾸지 않는다**. 함수 호출 횟수를 직접 세는 AC-NET-016만이 이를 잡는다.

> **M4가 왜 별도 축인가**: 재현 케이스 #37454는 라인 단위로 **전량** 환불이므로 boolean 필터와 산술 순액화가 **같은 답**을 낸다. #37454만으로는 M4를 절대 잡을 수 없다. AC-NET-002(수량 3, 환불 1)가 유일한 방어선이다.

### 0.1 [HARD] 픽스처 규약

1. **`shopify_line_item_id`는 `17_000_000_000_000` 이상의 값을 쓴다.** `Refund.line_item_id`는 `LineItem.pk`가 아니라 `shopify_line_item_id`와 조인된다(`purchase_order_views.py:337`, `serializers.py:190`). `shopify_line_item_id`를 1, 2, 3처럼 작은 값으로 두면 자동증가 `pk`와 우연히 일치할 수 있고, 그러면 M8(잘못된 조인 키)이 통과해버린다.
2. **환불 헬퍼는 `subtotal`/`total_tax`를 받아야 한다.** `test_spec_023.py:866-872`의 `_refund(line_item, quantity)`는 두 필드를 설정하지 않는다 — 그 헬퍼를 그대로 쓰면 매출 측 순액화가 검증되지 않는다. 같은 형태를 유지하되 인자를 확장한 헬퍼를 신규 스위트에 만든다:
   ```python
   def _refund(line_item, quantity, subtotal=None, total_tax=None, line_item_id=_UNSET):
       return Refund.objects.create(
           order=line_item.order,
           shopify_refund_id=next(_next_refund_id),
           line_item_id=(line_item.shopify_line_item_id if line_item_id is _UNSET else line_item_id),
           quantity=quantity,
           subtotal=subtotal,
           total_tax=total_tax,
       )
   ```
   (`line_item_id`를 명시적으로 `None`이나 미매칭 값으로 넘길 수 있어야 AC-NET-007/008이 작성 가능하다.)
3. **모든 금액 단정은 문자열 비교로 한다** — 7개 게터가 문자열을 반환한다(`serializers.py:555-615`). `float` 비교를 쓰면 판별력이 떨어진다.
4. **`margin_rate`의 `null` 단정은 `res.data["margin_rate"] is None`으로 한다** — `.get()`은 키 부재와 `None`을 구별하지 못한다(SPEC-ORDER-021 감사 D6 전례).

---

## AC-NET-001 — 프로덕션 **집계값** 재현: 주문 #37454 (전량 환불 라인 2건) `[BE]`

> **제목의 정확한 의미** (감사 D13): 이 픽스처는 프로덕션의 **집계값**(gross 4453g / 74100 KRW, net 3418g / 49500 KRW, 환불 합 37.28 USD, `total_price` 116.04, rate 1427.11)을 정확히 재현하지만, **라인아이템별 값은 합성**이다 — 조사 세션에서 품목별 원본 값을 캡처하지 않았기 때문이다. 또한 위 집계값 자체는 **2026-08-17 원격 DB 스냅샷(UNVERIFIED)**이다(`research.md` §5/§13). 구현 시 실측이 어긋나면 실측값을 신뢰하고 이 AC의 픽스처·기대값을 재계산한다.

Traces: REQ-NET-001, REQ-NET-010, REQ-NET-013, REQ-NET-026
잡는 변이: **M1, M2, M3**

**Given** `ExchangeRate(effective_date=D, rate=Decimal("1427.11"))`, `Order(total_price=Decimal("116.04"), shopify_created_at=D)` — `D`는 그 환율의 유효일 이상 —, 그리고 `quantity=1`인 라인아이템 6건:

| 라벨 | `grams` | `confirmed_price` | 환불 |
|------|---------|-------------------|------|
| S1 | 900 | 13000.00 | — |
| S2 | 850 | 12500.00 | — |
| S3 | 834 | 12000.00 | — |
| S4 | 834 | 12000.00 | — |
| R1 | 535 | 16000.00 | `quantity=1, subtotal=24.00, total_tax=0.00` |
| R2 | 500 | 8600.00 | `quantity=1, subtotal=13.28, total_tax=0.00` |

> 라인아이템별 값은 프로덕션 집계값(gross 4453g / 74100 KRW, net 3418g / 49500 KRW, 환불 합 37.28 USD)을 정확히 재현하도록 합성한 것이다 — 조사 세션에서 품목별 원본 값을 캡처하지 않았기 때문이다(`research.md` §5). 검산: 900+850+834+834=3418, +535+500=4453 / 13000+12500+12000+12000=49500, +16000+8600=74100.

**When** `GET /api/orders/{pk}/`

**Then** 응답은 `200`이며 정확히 다음 값을 반환한다:

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `3418` |
| `confirmed_cost` | `"34.69"` |
| `shipping_cost` | `"18.63"` |
| `korea_warehouse_cost` | `"1.93"` |
| `total_cost` | `"55.24"` |
| `margin_amount` | `"23.52"` |
| `margin_rate` | `"29.86"` |

계산 근거: 49500/1427.11=34.685483 · 5.45×3.418=18.62810 · (1250+500×3)/1427.11=1.926971 · 합 55.240554 · 매출 116.04−37.28=78.76 · 78.76−55.240554=23.519446 · 23.519446/78.76×100=29.862171

**판별력 — 변이별 결과값 (전부 기대값과 다르다)**

| 변이 | `total_weight_grams` | `total_cost` | `margin_amount` | `margin_rate` |
|------|----------------------|--------------|-----------------|---------------|
| 기대(정답) | 3418 | "55.24" | "23.52" | "29.86" |
| **M1** 순액화 없음 (현재 결함) | 4453 | "78.82" | "37.22" | "32.08" |
| **M2** 수량만 | 3418 | "55.24" | "60.80" | "52.40" |
| **M3** 매출만 | 4453 | "78.82" | "-0.06" | "-0.08" |

> M2가 정답보다 **더 틀렸다**는 점을 이 표가 수치로 고정한다(오차 +13.70 → +37.28). REQ-NET-013의 "쪼갤 수 없다"가 이 AC로 검증된다.

---

## AC-NET-002 — [핵심] 진짜 부분 환불: 수량 3 중 1건 환불 → 순액 2 `[BE]`

Traces: REQ-NET-001, REQ-NET-002, **REQ-NET-003**, REQ-NET-026
잡는 변이: **M1, M2, M3, M4(유일), M8**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 1건 `quantity=3, confirmed_price=Decimal("10000.00"), grams=500`, `shopify_line_item_id = 17_851_226_325_297`, 그리고 환불 1건 `quantity=1, subtotal=Decimal("20.00"), total_tax=Decimal("0.00")`

**When** `GET /api/orders/{pk}/`

**Then**

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `1000` |
| `confirmed_cost` | `"20.00"` |
| `shipping_cost` | `"5.45"` |
| `korea_warehouse_cost` | `"1.75"` |
| `total_cost` | `"27.20"` |
| `margin_amount` | `"52.80"` |
| `margin_rate` | `"66.00"` |

계산 근거: 순수량 2 → 순무게 1000g, 순확정 20000 KRW · 20000/1000=20.00 · 5.45×1.0=5.45 · (1250+500×1)/1000=1.75 · 합 27.20 · 매출 100.00−20.00=80.00 · 80.00−27.20=52.80 · 52.80/80×100=66.00

**판별력 — 변이별 결과값**

| 변이 | `total_weight_grams` | `korea_warehouse_cost` | `total_cost` | `margin_amount` | `margin_rate` |
|------|----------------------|------------------------|--------------|-----------------|---------------|
| 기대(정답) | **1000** | **"1.75"** | **"27.20"** | **"52.80"** | **"66.00"** |
| M1 순액화 없음 | 1500 | "2.25" | "40.43" | "59.58" | "59.58" |
| M2 수량만 | 1000 | "1.75" | "27.20" | "72.80" | "72.80" |
| M3 매출만 | 1500 | "2.25" | "40.43" | "39.58" | "49.47" |
| **M4 boolean 필터 + 매출 순액화** | **1500** | **"2.25"** | **"40.43"** | **"39.58"** | **"49.47"** |
| M8 `pk`로 조인 (**수량 측만** 순액화 실패) | 1500 | "2.25" | "40.43" | "39.58" | "49.47" |

> **M4/M8이 M3과 동일한 값을 낸다**는 점이 중요하다 — 세 변이 모두 "부분 환불이 수량을 줄이지 않는다"는 하나의 관측 가능한 사실로 드러나며, `total_weight_grams == 1500`이 그 단일 판별자다. #37454(AC-NET-001)에서는 이 축이 존재하지 않는다.
>
> **[감사 D4 정정]** 최초 버전은 M8 행을 `"59.58"`/`"59.58"`(= M1 행의 값)로 적었다. M8은 **조인 키만** 틀린 변이이고, 매출 측 순액화(REQ-NET-011)는 **조인 키를 전혀 쓰지 않고** 전체 환불 행을 합산하므로 M8에서도 매출은 정상적으로 80.00으로 내려간다 → margin = 80.00 − 40.425 = 39.575 → `"39.58"`, rate = 49.46875 → `"49.47"`. 즉 M8은 M1이 아니라 M3/M4와 같은 행이다. AC의 실제 단정(`total_weight_grams == 1000`)은 어느 쪽이든 실패하므로 판별력 자체는 처음부터 유지되었으나, 변이 표는 이 SPEC이 판별력의 근거로 제시하는 1차 산출물이므로 재현되지 않는 행을 남겨둘 수 없다.

---

## AC-NET-003 — 백엔드 마진이 화면의 `최종 결제 금액`과 화해한다 `[BE]`

Traces: REQ-NET-010, REQ-NET-013, REQ-NET-043
잡는 변이: **M2** (M3는 잡지 못한다 — 아래 판별력 절 참조. 감사 D5로 헤더 정정)

**Given** AC-NET-001의 픽스처와 AC-NET-002의 픽스처 (parametrize 2건)

**When** `GET /api/orders/{pk}/`

**Then** 테스트는 프론트엔드 공식(`frontend/src/pages/OrderDetailPage.tsx:159-163`)을 백엔드 밖에서 재계산해 대조한다:

```python
net_paid = Decimal(str(order.total_price)) - sum(
    (r.subtotal or Decimal("0")) + (r.total_tax or Decimal("0"))
    for r in order.refunds.all()
)
assert Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"]) == net_paid
```

- AC-NET-001 픽스처: `23.52 + 55.24 == 78.76` (정확히 일치)
- AC-NET-002 픽스처: `52.80 + 27.20 == 80.00` (정확히 일치)

**일반 케이스 허용 오차** [HARD]: `margin_amount`와 `total_cost`는 각각 **1회씩** 양자화되므로(설계 결정 B, `serializers.py:606-615`) 일반적으로 합이 순매출과 최대 `0.01` USD 어긋날 수 있다. 위 두 픽스처는 오차 0으로 정확히 일치하도록 선정되었으므로 **정확 일치를 단정한다**. 다른 픽스처로 이 화해를 검증할 때는 `abs(...) <= Decimal("0.01")` 형태를 쓴다. 잔차가 실제로 `0.01`인 픽스처는 AC-NET-005(`27.12 + 2.89 = 30.01`)와 AC-NET-015(`66.03 + 13.98 = 80.01`)이며, **AC-NET-005는 정확 일치 대신 잔차 `0.01` 자체를 직접 단정한다**(§AC-NET-005 「추가 단정」 — 감사 N6 정정: 이전 버전은 "그 AC에서는 화해를 단정하지 않는다"고 적었다).

**판별력**: M2(수량만)에서 `60.80 + 55.24 = 116.04 ≠ 78.76`(오차 37.28). M3(매출만)에서 `-0.06 + 78.82 = 78.76`... **주의**: M3는 이 단정을 통과한다(매출 측이 순액이므로 항등식이 성립). 따라서 이 AC는 M3에 대한 판별력이 없고, M3는 AC-NET-001/002가 잡는다. 이 AC의 고유 가치는 **M2 차단**과 **화면 화해의 명문화**다.

---

## AC-NET-004 — 전 라인 전량 환불: 7필드의 결정된 값 `[BE]`

Traces: REQ-NET-005, REQ-NET-022, REQ-NET-023
잡는 변이: **M1, M3, REQ-NET-005 삭제(권수 0에서 기본료 부과)**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("30.00"))`, 라인아이템 1건 `quantity=2, confirmed_price=Decimal("10000.00"), grams=500`, 환불 1건 `quantity=2, subtotal=Decimal("30.00"), total_tax=Decimal("0.00")`

### (a) 상세 경로

**When** `GET /api/orders/{pk}/`

**Then**

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `0` |
| `confirmed_cost` | `"0.00"` |
| `shipping_cost` | `"0.00"` |
| `korea_warehouse_cost` | `"0.00"` |
| `total_cost` | `"0.00"` |
| `margin_amount` | `"0.00"` |
| `margin_rate` | `None` (`is None`, 키는 존재해야 한다) |

### (b) 목록 경로 — 매출 0 게이트의 두 번째 구현 지점 `[감사 D12 신규]`

**When** 동일 주문에 대해 `GET /api/orders/`

**Then** 해당 행의 `margin_rate`가 `None`이다 (`is None`).

**왜 별도로 필요한가**: REQ-NET-022는 매출 0 게이트를 **두 곳** 인용한다 — 상세 `serializers.py:570-571`과 목록 `serializers.py:283-284`. 두 게이트는 **서로 다른 코드 블록**이며 (a)는 상세만 검증한다. 최초 버전에서는 "전량 환불 주문이 **목록**에서 `margin_rate: null`을 내는지" 어떤 AC도 확인하지 않았다. `serializers.py:283-284`를 삭제한 변이는 (a)를 통과하면서 목록에서 `ZeroDivisionError`(또는 `decimal.InvalidOperation`)로 500을 내거나 잘못된 값을 반환한다 — (b)가 그것을 잡는다.

**판별력**

| 변이 | `korea_warehouse_cost` | `total_cost` | `margin_amount` | `margin_rate` (상세) | `margin_rate` (목록) |
|------|------------------------|--------------|-----------------|---------------------|---------------------|
| 기대(정답) | "0.00" | "0.00" | "0.00" | None | None |
| 권수 0 분기 삭제 (REQ-NET-005) | "1.25" | "1.25" | "-1.25" | None | None |
| M1 순액화 없음 | "1.75" | "27.20" | "2.80" | "9.33" | "9.33" |
| M3 매출만 | "1.75" | "27.20" | "-27.20" | None | None |
| REQ-NET-024를 사후 평가로 뒤집음 | None | None | None | None | None |
| 목록 게이트(`:283-284`) 삭제 | "0.00" | "0.00" | "0.00" | None | **예외/오값** ← (b)만 잡는다 |

---

## AC-NET-005 — `has_any_confirmed`는 순액화 **전에** 평가된다 `[BE]`

Traces: REQ-NET-024
잡는 변이: **사후 평가(post-netting) 변이**, **M2**(잔차 단정이 잡는다 — 순매출 gross 시 잔차 `20.01`). **M7은 잡지 못한다** — 이 픽스처의 순확정 금액이 0이므로 관측되지 않는다(감사 N2 정정, 아래 「추가 단정」 절 참조)

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("50.00"))`, 라인아이템 2건:

| 라벨 | `quantity` | `confirmed_price` | `grams` | 환불 |
|------|-----------|-------------------|---------|------|
| A | 1 | 10000.00 | 500 | `quantity=1, subtotal=20.00, total_tax=0.00` (전량) |
| B | 1 | `None` | 300 | — |

즉 **확정매입가를 가진 유일한 라인이 전량 환불된** 상태다.

**When** `GET /api/orders/{pk}/`

**Then** 7필드는 `null`이 아니며(주문이 여전히 마진 계산 자격을 갖는다):

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `300` |
| `confirmed_cost` | `"0.00"` |
| `shipping_cost` | `"1.64"` |
| `korea_warehouse_cost` | `"1.25"` |
| `total_cost` | `"2.89"` |
| `margin_amount` | `"27.12"` |
| `margin_rate` | `"90.38"` |

계산 근거: 순액 A=0, B=1 → 권수 1, 무게 300g, 순확정 0 KRW · 5.45×0.3=1.635→"1.64" · (1250+500×0)/1000=1.25 · 합 0+1.635+1.25=2.885→"2.89" · 매출 50.00−20.00=30.00 · 30.00−2.885=27.115→"27.12" · 27.115/30×100=90.38333

**판별력**: `has_any_confirmed`를 순액화 **후**에 평가하는 변이에서는 A의 순수량이 0이므로 플래그가 거짓이 되고 함수가 `None`을 반환해 **7필드 전부 `null`**이 된다. 위 7개 단정 전부가 실패한다.

### 추가 단정 — 잔차 `0.01`을 특성화 단정으로 고정한다 `[감사 D12 신규]`

이 픽스처는 잔차가 `0.01`로 **실제 발생**한다: `27.12 + 2.89 = 30.01`, 순매출 `30.00` → 잔차 `+0.01`. (AC-NET-015도 잔차 `+0.01`이다 — 감사 N5 정정: 이전 버전은 "유일한 픽스처"라고 적었다.) 따라서 여기서 그 값을 직접 못 박는다:

```python
net_paid = Decimal("30.00")
residual = (Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])) - net_paid
assert residual == Decimal("0.01")                 # 잔차가 실재함 (0이 아님)
assert abs(residual) <= Decimal("0.01")            # REQ-NET-043의 상한을 넘지 않음
```

**이 단정이 정확히 하는 일** (감사 N10으로 문구 축소): 이것은 **이 픽스처의 잔차가 정확히 `0.01`임을 고정하는 특성화(characterization) 단정**이다. REQ-NET-043의 "≤ `0.01`" 상한 준수는 그 **귀결**이며, 상한을 일반적으로 검증하는 것이 아니다(다른 픽스처에서 화해를 확인할 때는 `abs(...) <= Decimal("0.01")` 형태를 쓴다 — AC-NET-003 참조). 이 픽스처에서 잔차가 결정적인 근거는 REQ-NET-025(중간 반올림 금지) + Exclusions 3(공식·상수 무변경)이 공식과 양자화 지점을 완전히 고정하기 때문이다.

**왜 필요한가**: 최초 버전에서는 AC-NET-003이 오차 0 픽스처 2건만 **정확 일치**로 단정하고, 오차가 실제로 발생하는 이 픽스처에서는 화해를 아예 단정하지 않았다. 그 결과 "잔차가 실재하며 `0.01`을 넘지 않는다"를 **어떤 테스트도 실행하지 않았다**. 위 두 줄이 그 공백을 무비용으로 닫는다 — 첫 줄은 잔차가 실재함을(따라서 AC-NET-003이 일반 케이스에 정확 일치를 요구하면 안 된다는 것을), 둘째 줄은 그 잔차가 상한 내라는 것을 각각 고정한다.

**이 단정이 잡는 변이 / 잡지 못하는 변이** (감사 N2 정정): 매출 항을 잘못 계산하는 변이는 잡는다 — 예컨대 M2(수량만 순액화)에서는 순매출이 gross `50.00`이 되어 잔차가 `20.01`이 되고 두 단정이 모두 깨진다. 반면 **M7(중간 반올림 도입)은 이 픽스처에서 관측되지 않는다**: 이 픽스처의 순확정 금액은 **0 KRW**(확정매입가를 가진 유일한 라인 A가 전량 환불)이므로 항목별로 선반올림해도 `confirmed_cost`가 `"0.00"`으로 동일하고, 3개 항을 각각 양자화해 합산해도 `0.00 + 1.64 + 1.25 = 2.89`로 `total_cost` 문자열이 변하지 않는다. 이전 버전은 여기에 M7을 적었으나 **그 주장은 재현되지 않으므로 삭제했다** — M7은 순확정 금액이 `10.005`인 AC-NET-012가 T15와 동일한 이중 단정으로 잡는다.

---

## AC-NET-006a — 과다 환불: 수량 측 하한 `max(..., 0)` `[BE]`

Traces: REQ-NET-020
잡는 변이: **M5 (수량 측 하한 삭제)**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("50.00"))`, 환불 1건 `subtotal=Decimal("30.00"), total_tax=Decimal("0.00")`, 그리고 **parametrize 2건** — 둘 다 `confirmed_price=Decimal("10000.00"), grams=500`:

| 케이스 | 라인아이템 `quantity` | 환불 `quantity` | 순액 계산 |
|--------|----------------------|-----------------|-----------|
| **(a)** 수량 초과 환불 | `1` | `2` | `max(1 − 2, 0) = 0` |
| **(b)** `quantity IS NULL` + 환불 `[감사 D12 신규]` | `None` (스키마상 nullable) | `1` | `max((None or 0) − 1, 0) = 0` |

**When** 각 케이스에 대해 `GET /api/orders/{pk}/`

**Then** 두 케이스 모두 **동일한** 값을 반환한다:

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `0` (**음수가 아니다**) |
| `confirmed_cost` | `"0.00"` |
| `shipping_cost` | `"0.00"` |
| `korea_warehouse_cost` | `"0.00"` |
| `total_cost` | `"0.00"` |
| `margin_amount` | `"20.00"` |
| `margin_rate` | `"100.00"` |

**판별력**: 하한을 뺀 변이(`net = quantity - refunded`)는 **두 케이스 모두** 순수량 `-1`을 만들어 아래를 반환한다:

| 필드 | 하한 삭제 변이 (a)/(b) 공통 |
|------|------------------------------|
| `total_weight_grams` | `-500` |
| `confirmed_cost` | `"-10.00"` |
| `shipping_cost` | `"-2.73"` |
| `korea_warehouse_cost` | `"1.25"` (권수 `-1`이 `== 0` 분기를 통과하지 못해 **기본료가 부과된다**) |
| `total_cost` | `"-11.48"` |
| `margin_amount` | `"31.48"` |
| `margin_rate` | `"157.38"` |

`total_weight_grams`가 음수인지만 봐도 즉시 잡힌다.

**(b)가 왜 별도 케이스인가**: `LineItem.quantity`는 nullable이며 `test_spec_021.py`의 AC-COST-008이 이미 `quantity=null`을 다루므로 프로덕션에 존재하는 형태다. 순액화 도입 후 `None`이 개입하는 경로는 `(item.quantity or 0)` 가드와 `max(..., 0)` 하한이 **함께** 걸려야 안전하며, `or 0` 가드만 있고 하한이 없으면 (b)에서 `-1`이 나온다. (a)와 동일한 기대값을 갖도록 픽스처를 설계했으므로 parametrize 한 줄로 축을 추가할 수 있다.

---

## AC-NET-006b — 과다 환불: 매출 측 하한 `max(..., 0)` `[BE]`

Traces: REQ-NET-021, REQ-NET-022
잡는 변이: **M5 (매출 측 하한 삭제)**

**Given** `rate = Decimal("1000.00")`, 라인아이템 1건 `quantity=1, confirmed_price=Decimal("5000.00"), grams=0`, 환불 1건 `quantity=1, subtotal=Decimal("15.00"), total_tax=Decimal("0.00")`, 그리고 **parametrize 2건**:

| 케이스 | `Order.total_price` | 순매출 계산 |
|--------|---------------------|-------------|
| **(a)** 환불액이 총액 초과 | `Decimal("10.00")` | `max(10.00 − 15.00, 0) = 0` |
| **(b)** `total_price IS NULL` + 환불 `[감사 D12 신규]` | `None` | `max(0 − 15.00, 0) = 0` (`obj.total_price or "0"`) |

**When** 각 케이스에 대해 `GET /api/orders/{pk}/`

**Then** 두 케이스 모두 **동일한** 값을 반환한다:

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `0` |
| `total_cost` | `"0.00"` |
| `margin_amount` | `"0.00"` |
| `margin_rate` | `None` (`is None`) — 기존 매출 0 게이트(`serializers.py:570-571`)가 발동한다 |

**판별력**: 매출 하한을 뺀 변이는 순매출을 음수로 만들고, 비용이 0이므로:

| 케이스 | 순매출 | `margin_amount` | `margin_rate` |
|--------|--------|-----------------|---------------|
| (a) 하한 삭제 | `-5.00` | `"-5.00"` | `(-5 / -5) × 100 = "100.00"` |
| (b) 하한 삭제 | `-15.00` | `"-15.00"` | `(-15 / -15) × 100 = "100.00"` |

**전량 환불되고 초과 환불된 주문에 마진율 100%가 표시된다.** 두 단정(`margin_amount`, `margin_rate is None`)이 각각 독립적으로 이 변이를 잡으며, 두 케이스 모두에서 잡는다.

**(b)가 왜 별도 케이스인가**: `Order.total_price`도 nullable이며 기존 코드가 `obj.total_price or "0"`(`serializers.py:48`)로 방어한다. 순액화 도입 후에는 `0 − 환불액`이 되어 **하한이 없으면 반드시 음수**가 된다 — 즉 `total_price`가 NULL이고 환불이 있는 주문은 (a)보다 이 결함에 더 쉽게 노출된다.

---

## AC-NET-007 — NULL 내구성: `line_item_id` / `quantity` / `subtotal` / `total_tax` `[BE]`

Traces: REQ-NET-002, REQ-NET-011, REQ-NET-012
잡는 변이: **NULL 가드 삭제 (500 에러), 매출 측을 매칭된 환불로 한정하는 변이**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 2건 `A(quantity=3, confirmed_price=10000.00, grams=0)`, `B(quantity=1, confirmed_price=10000.00, grams=0)`, 그리고 환불 3건:

| # | `line_item_id` | `quantity` | `subtotal` | `total_tax` |
|---|----------------|-----------|-----------|------------|
| R1 | `None` | 5 | 3.00 | `None` |
| R2 | A의 `shopify_line_item_id` | `None` | `None` | `None` |
| R3 | B의 `shopify_line_item_id` | 1 | 8.00 | 0.80 |

**When** `GET /api/orders/{pk}/`

**Then** 응답은 **`200`**(예외 없음)이며:

| 필드 | 기대값 | 근거 |
|------|--------|------|
| `total_weight_grams` | `0` | 두 라인 모두 `grams=0` |
| `confirmed_cost` | `"30.00"` | R1의 `quantity=5`는 `line_item_id`가 `None`이라 어떤 라인도 줄이지 못한다. R2는 `quantity=None`→0. R3만 B를 0으로 만든다 → 순확정 3×10000=30000 |
| `korea_warehouse_cost` | `"2.25"` | 순권수 3 → (1250+500×2)/1000 |
| `total_cost` | `"32.25"` | |
| `margin_amount` | `"55.95"` | 순매출 100.00 − (3.00+0+0+0+8.00+0.80) = 88.20; 88.20−32.25 |
| `margin_rate` | `"63.44"` | 55.95/88.20×100 = 63.4353741 |

**판별력**
- `refund.quantity or 0` 가드 삭제 → R2에서 `int + None` → `TypeError` → `500`. `status_code == 200` 단정이 잡는다.
- `subtotal`/`total_tax`의 `or Decimal("0")` 가드 삭제 → `Decimal + None` → `TypeError` → `500`.
- `line_item_id is not None` 스킵 누락 → R1의 5가 어떤 라인에도 매칭되지 않으므로 값은 같지만, 구현이 `None` 키로 dict에 쓰는 것 자체는 무해하다. 이 축은 이 AC가 판별하지 않는다(설계상 관측 불가).
- **매출 측을 "매칭된 환불"로만 한정하는 변이** → 순매출 100.00 − 8.80 = 91.20 → `margin_amount = "58.95"`, `margin_rate = "64.64"`. 두 단정이 잡는다.

화해 검산(정확 일치): `55.95 + 32.25 = 88.20` ✓

---

## AC-NET-008 — 미매칭 환불은 매출만 줄이고 수량은 줄이지 않는다 `[BE]`

Traces: REQ-NET-011
잡는 변이: **매출 측을 매칭된 환불로 한정하는 변이**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 1건 `quantity=2, confirmed_price=Decimal("10000.00"), grams=0, shopify_line_item_id=17_851_226_358_065`, 그리고 환불 1건 `line_item_id=17_999_999_999_999`(어떤 `LineItem`과도 매칭되지 않음), `quantity=2, subtotal=Decimal("25.00"), total_tax=Decimal("0.00")`

**When** `GET /api/orders/{pk}/`

**Then**

| 필드 | 기대값 |
|------|--------|
| `confirmed_cost` | `"20.00"` (수량 **미감소** — 매칭되는 라인이 없다) |
| `korea_warehouse_cost` | `"1.75"` (순권수 2) |
| `total_cost` | `"21.75"` |
| `margin_amount` | `"53.25"` (순매출 75.00 − 21.75) |
| `margin_rate` | `"71.00"` |

**판별력**: 매출 측이 매칭된 환불만 합산하는 변이는 순매출 100.00을 써서 `margin_amount = "78.25"`, `margin_rate = "78.25"`를 반환한다. 이 동작은 프론트엔드가 이미 하는 것(`OrderDetailPage.tsx:159-162`는 필터가 없고, 미매칭 행을 `:491-504`에서 "상품 정보 없음"으로 별도 렌더한다)과 정확히 일치해야 한다.

---

## AC-NET-009 — [MUST-PASS] 상세 API 쿼리 수 불변식 `[BE]`

Traces: REQ-NET-030, REQ-NET-031 (**REQ-NET-033은 이 AC로 검증되지 않는다** — 감사 D1, AC-NET-016 참조)
잡는 변이: **M6**

> **[HARD] 이 AC는 무수정 코드에서 통과하는 것이 정상이다.** 불변식 **보존** AC이므로 현재 코드가 이미 만족한다(총 8, `orders_refund` 1, `orders_exchangerate` 1). 통과한다는 이유로 픽스처를 고치지 말 것 — 이 AC와 AC-NET-010은 R3(주문당 +50 쿼리, 프로덕션 약 +6.5초)에 대한 **유일한 방어선**이다(감사 D3).

**Given** 무관한 주문 1건에 대한 **워밍업 요청**을 먼저 보낸 뒤(`test_spec_021.py:268-313`의 관례 — 첫 요청에서만 발생하는 쿼리를 측정 창 밖으로 뺀다), 환불을 가진 두 주문:
- 주문 X: 라인아이템 1건 + `Refund` 1건
- 주문 Y: 라인아이템 5건 + `Refund` 5건 (각 라인에 1건씩, 각각 부분 환불)
둘 다 확정매입가 보유 + 유효 환율

**When** 각각 `GET /api/orders/{pk}/`를 `django.test.utils.CaptureQueriesContext`로 캡처

**Then**
- (a) `len(ctx_x.captured_queries) == len(ctx_y.captured_queries) == 8`. **이 절대값은 SPEC이 결정한 것이며(REQ-NET-031) 구현자가 실측값으로 재핀하지 않는다**(감사 D11). 근거: `test_spec_021.py:48`의 `ORDER_DETAIL_QUERY_COUNT = 8`이 이미 절대값으로 고정하고 있고 그 스위트의 무수정 통과가 DoD다 — 즉 `8`은 추측값이 아니라 이 SPEC 밖에서 이미 강제되는 값이다. 신규 스위트는 `test_spec_021.py:48`에서 `from order.tests.test_spec_021 import ORDER_DETAIL_QUERY_COUNT`로 임포트하거나 동일 값 `8`을 자체 상수로 선언한다. **실측이 `8`이 아니면 상수를 갱신하지 말고 작업을 멈추고 원인(추가된 쿼리)을 보고한다** — 그것은 새 기준선이 아니라 REQ-NET-031 위반이다.
- (b) 두 컨텍스트 각각에서 `"orders_refund" in sql`인 쿼리가 **정확히 1개**. 단순 `in` 검사로 안전하다 — `orders_refund`는 이 스키마의 다른 어떤 테이블명의 접두사가 아니다(`models.py`의 `db_table` 18개 전수 확인, `research.md` §4.1). 대비: `orders_line_item`은 `orders_line_item_note`(`models.py:306`)의 접두사이므로 정규식이 필요했다(`test_spec_021.py:30`).
- (c) 두 컨텍스트 각각에서 `EXCHANGE_RATE_TABLE`(`"orders_exchangerate"`, `models.py:516`) 참조 쿼리가 **정확히 1개** — SPEC-ORDER-021 AC-COST-009(c) 유지.

**판별력**: `Refund.objects.filter(order=obj)` 또는 `purchase_order_views.py:334-342`의 `Subquery`/`OuterRef`를 직렬화기로 옮긴 변이(M6)는 (b)를 2 이상으로 만든다. 주문 Y(라인 5건)에서는 (a)도 함께 깨진다.

**[감사 D1] 이 AC가 잡지 못하는 것 — 명시적 한계**: 최초 버전은 여기에 "게터마다 순액화를 다시 계산하는(메모이제이션 우회) 변이는 (b)를 최대 7까지 늘린다"고 적었다. **그 주장은 거짓이며 삭제했다.** 반증 3중:

1. **(b)는 늘지 않는다.** 순액화는 `obj.refunds.all()` **prefetch 캐시**에서 읽는다 — 이 SPEC 자신의 REQ-NET-030 전제다(`views.py:59`/`:269`). 캐시 읽기를 7번 반복해도 `orders_refund` 쿼리는 **1건 그대로**다. 원래 주장은 SPEC의 핵심 전제와 정면으로 모순했다.
2. **(c)도 늘지 않는다.** `_get_exchange_rate`는 `serializers.py:466-498`에서 **독립적으로 주문 단위 메모이즈**되어 있다(SPEC-ORDER-021 REQ-COST-034, 독스트링 `:472-480`이 명시). 따라서 `_compute_cost_breakdown_uncached`를 게터 7개가 각각 직접 호출해도 `orders_exchangerate` 쿼리는 1건이다.
3. **(a)도 8에서 변하지 않는다.** 1·2로부터 자명.

원인: SPEC-ORDER-021 시절 AC-COST-009(c)는 실제 판별력이 있었으나, v1.4.0이 `_get_exchange_rate`를 메모이즈하면서 그 판별력이 소멸했다(SPEC-ORDER-021 `spec.md:20`이 "게터가 7→9개로 늘어도 쿼리는 1"이라고 스스로 기록). 낡은 판별력 주장을 검증 없이 승계한 것이다. **메모이제이션 우회(M11)는 AC-NET-016만이 잡는다.**

---

## AC-NET-010 — [MUST-PASS] 목록 API 쿼리 수 불변식 (페이지 크기 무관) `[BE]`

Traces: REQ-NET-030, REQ-NET-032
잡는 변이: **M6** (목록 경로 — 실질 위험이 가장 큰 지점)

> **[HARD] 이 AC도 무수정 코드에서 통과하는 것이 정상이다** (AC-NET-009와 동일한 이유, 감사 D3). 통과를 근거로 픽스처를 수정하지 말 것.

**Given** 워밍업 요청 후, 두 페이지:
- 1건 페이지: `Refund`를 가진 주문 1건 (`store_type` 필터로 격리, `test_spec_023.py:638-681` 관례)
- 5건 페이지: `Refund`를 가진 주문 5건 (각 주문에 라인아이템 + 환불)
전부 확정매입가 + 고객 + 유효 환율 보유

**When** 각각 `GET /api/orders/`를 `CaptureQueriesContext`로 캡처

**Then**
- (a) 두 요청의 총 쿼리 수가 **동일**하며 `TOTAL_QUERY_COUNT`(현재 실측값 **8**, `test_spec_023.py:34`)와 같다.
- (b) 두 컨텍스트 각각에서 `"orders_refund" in sql`인 쿼리가 **정확히 1개**.

**판별력**: 주문당 환불 쿼리를 발급하는 변이는 5건 페이지에서 총 `8 + 5 = 13`, `orders_refund` 참조 6을 만든다. `OrderPagination.page_size = 50`(`views.py:159-160`)이므로 프로덕션에서는 페이지당 +50 쿼리(원격 DB 130ms/쿼리 → 약 +6.5초)가 된다. 이 AC가 SPEC-ORDER-023 REQ-OLIST-021(`.moai/specs/SPEC-ORDER-023/spec.md:162`)의 [HARD] 보증을 지킨다.

---

## AC-NET-011 — 목록 `마진율`과 상세 `마진율`이 동일하다 `[BE]`

Traces: REQ-NET-042
잡는 변이: **M9 (한쪽 소비처에만 순액화 적용)**

**Given** AC-NET-001의 픽스처(#37454 재현) 그대로

**When** `GET /api/orders/{pk}/`와 `GET /api/orders/`를 모두 호출

**Then** 두 응답의 `margin_rate`가 **모두 `"29.86"`이며 서로 같다**.

**판별력**: 순액화를 공유 함수 `_compute_cost_breakdown_for_rate`(`serializers.py:31-73`)가 아니라 `OrderDetailSerializer._compute_cost_breakdown_uncached`(`:542-553`)에 넣은 변이에서는 상세 `"29.86"`, 목록 `"32.08"`로 갈라진다. 반대로 `OrderListSerializer.get_margin_rate`(`:266-288`)에만 넣으면 반대로 갈라진다. **동일성 단정만으로는 부족하다** — 양쪽이 gross여도 같기 때문이다. 그래서 절대값 `"29.86"`을 함께 단정한다.

---

## AC-NET-012 — 중간 반올림 금지 `[BE]`

Traces: REQ-NET-025
잡는 변이: **M7 (유일)** — 순확정 금액이 `10.005`로 5로 끝나는 유일한 픽스처이므로 선반올림이 여기서만 관측된다

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 1건 `quantity=2, confirmed_price=Decimal("10005.00"), grams=500`, 환불 1건 `quantity=1, subtotal=Decimal("10.00"), total_tax=Decimal("0.00")`

(T15(`test_spec_021.py:415-441`)의 반올림 함정 형태에 부분 환불을 얹은 것이다.)

**When** `GET /api/orders/{pk}/`

**Then**

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `500` |
| `confirmed_cost` | `"10.01"` (순확정 10005 KRW → 10.005, 개별 양자화) |
| `shipping_cost` | `"2.73"` (5.45×0.5 = 2.725) |
| `korea_warehouse_cost` | `"1.25"` (순권수 1 → 1250/1000) |
| `total_cost` | **`"13.98"`** (반올림 전 10.005+2.725+1.25 = **13.980**) |
| `margin_amount` | `"76.02"` (90.00 − 13.980) |
| `margin_rate` | `"84.47"` (76.02/90×100 = 84.46666) |

**판별력** — T15와 동일한 형태의 이중 단정을 포함한다:
```python
naive_sum = Decimal(res.data["confirmed_cost"]) + Decimal(res.data["shipping_cost"]) \
          + Decimal(res.data["korea_warehouse_cost"])
assert naive_sum == Decimal("13.99")                       # 반올림된 3항의 합
assert res.data["total_cost"] == "13.98"                   # 반올림 전 합의 1회 양자화
assert Decimal(res.data["total_cost"]) != naive_sum
```
순액화 도중 항목별로 양자화하는 변이(예: 순확정 금액을 10.01로 먼저 반올림)는 `total_cost = "13.99"`를 반환해 위 세 단정 중 두 개를 깬다.

화해 검산(정확 일치): `76.02 + 13.98 = 90.00` ✓

---

## AC-NET-013 — `purchase_status`는 순액화 신호가 아니다 (Exclusions 1의 검증) `[BE]`

Traces: REQ-NET-004
잡는 변이: **범위 초과 변이 — `order_cancelled`도 함께 제외해버리는 구현**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 1건 `quantity=3, confirmed_price=Decimal("10000.00"), grams=0, purchase_status="order_cancelled"`(`models.py:159`), **`Refund` 행 없음**

**When** `GET /api/orders/{pk}/`

**Then** 순액화가 전혀 적용되지 않은 것과 동일한 값:

| 필드 | 기대값 |
|------|--------|
| `confirmed_cost` | `"30.00"` |
| `korea_warehouse_cost` | `"2.25"` |
| `total_cost` | `"32.25"` |
| `margin_amount` | `"67.75"` |
| `margin_rate` | `"67.75"` |

**판별력**: `purchase_status == "order_cancelled"`인 라인을 비용에서 제외하는(범위를 넘어선) 구현은 순권수 0을 만들어 4필드 전부 `"0.00"`, `margin_amount = "100.00"`을 반환한다. 이 AC는 `spec.md` Exclusions 1을 **테스트로 고정된 비목표**로 만든다 — 프로덕션 61건의 동작이 이 SPEC으로 바뀌지 않음을 보증한다.

---

## AC-NET-014 — 환불 없는 주문은 값이 완전히 불변이다 (하위 호환) `[BE]`

Traces: REQ-NET-040
잡는 변이: **환불 유무와 무관하게 값을 바꿔버리는 구현(예: 상수 변경, 공식 변경)**

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 1건 `quantity=3, confirmed_price=Decimal("10000.00"), grams=0`, **`Refund` 행 없음** (`test_spec_021.py:104-115`의 T1 픽스처와 동일 형태)

**When** `GET /api/orders/{pk}/`

**Then** 7필드 전부가 아래 값을 반환한다. **각 값의 기존 근거를 정확히 구분한다** (감사 D8 — 최초 버전은 7개 전부를 T1이 단정한다고 과장했다):

| 필드 | 기대값 | 기존 스위트의 근거 |
|------|--------|--------------------|
| `margin_amount` | `"67.75"` | **T1** (`test_spec_021.py:112`) |
| `korea_warehouse_cost` | `"2.25"` | **T1** (`:113`) |
| `shipping_cost` | `"0.00"` | **T1** (`:114`) |
| `total_weight_grams` | `0` | **T1** (`:115`) |
| `confirmed_cost` | `"30.00"` | **T14** (`test_spec_021.py:385-395`, 동일 픽스처 `quantity=3, confirmed_price=10000.00, grams=0`) |
| `total_cost` | `"32.25"` | **기존 단정 없음** — 이 AC가 이 픽스처에 대해 처음 고정한다 |
| `margin_rate` | `"67.75"` | **기존 단정 없음** — 이 AC가 이 픽스처에 대해 처음 고정한다 |

즉 T1은 `res.status_code`를 제외하면 **4개만** 단정한다(`test_spec_021.py:111-115` 실측). 이 AC의 하위 호환 보증 범위는 T1 ∪ T14(5개) + 신규 2개다.

**판별력**: 비용 상수 3개(`serializers.py:15-17`) 중 하나를 건드리거나 한국물류비 공식(`serializers.py:54-59`)을 바꾼 변이를 잡는다. 이 AC는 `test_spec_021.py`의 무수정 통과 요구(§DoD)와 중복되지만, 신규 스위트 안에서 하위 호환을 **명시적 계약으로** 갖는다. 무수정 코드에서 **통과하는 것이 정상**이다.

---

## AC-NET-015 — [핵심] 같은 라인아이템에 환불 2행: 합산인가 덮어쓰기인가 `[BE]` `[감사 D2 신규]`

Traces: REQ-NET-001, **REQ-NET-002** (합산 축), REQ-NET-026
잡는 변이: **M10 (유일)**, M1

**Given** `rate = Decimal("1000.00")`, `Order(total_price=Decimal("100.00"))`, 라인아이템 **1건** `quantity=3, confirmed_price=Decimal("10000.00"), grams=500`, `shopify_line_item_id = 17_851_226_325_297`, 그리고 **같은 `line_item_id`를 가리키는 환불 2행**(서로 다른 `shopify_refund_id` — `models.py:342`의 `unique_together`가 정확히 이 형태를 허용한다):

| # | `line_item_id` | `quantity` | `subtotal` | `total_tax` |
|---|----------------|-----------|-----------|------------|
| R1 | 17_851_226_325_297 | 1 | 10.00 | 0.00 |
| R2 | 17_851_226_325_297 | 1 | 10.00 | 0.00 |

**When** `GET /api/orders/{pk}/`

**Then**

| 필드 | 기대값 |
|------|--------|
| `total_weight_grams` | `500` |
| `confirmed_cost` | `"10.00"` |
| `shipping_cost` | `"2.73"` |
| `korea_warehouse_cost` | `"1.25"` |
| `total_cost` | `"13.98"` |
| `margin_amount` | `"66.03"` |
| `margin_rate` | `"82.53"` |

계산 근거: 환불 수량 **합산** 1+1=2 → 순수량 `max(3−2, 0) = 1` → 순무게 500g, 순확정 10000 KRW · 10000/1000 = 10.00 · 5.45×0.5 = 2.725 → `"2.73"` · 권수 1 → 1250/1000 = 1.25 · 합 10+2.725+1.25 = **13.975** → `"13.98"` · 순매출 100.00 − (10.00+10.00) = 80.00 · 80.00 − 13.975 = **66.025** → ROUND_HALF_UP → `"66.03"` · 66.025/80.00×100 = 82.53125 → `"82.53"`

> **반올림 주의**: `13.975`와 `66.025`는 둘 다 정확히 5로 끝나는 Decimal이므로 `ROUND_HALF_UP`이 0에서 멀어지는 방향으로 올린다 → `13.98`, `66.03`. 1차 감사 보고서가 제시한 예상값 `"66.02"`는 이 규칙을 적용하지 않은 값이며, 재검산 결과 **`"66.03"`이 맞다**(2차 감사가 독립 재계산으로 이 반박을 확인했다).

### 추가 단정 — 잔차 `0.01` (AC-NET-005와 동일한 특성화 단정) `[감사 N5 신규]`

```python
net_paid = Decimal("80.00")   # 100.00 − (10.00 + 10.00)
residual = (Decimal(res.data["margin_amount"]) + Decimal(res.data["total_cost"])) - net_paid
assert residual == Decimal("0.01")
assert abs(residual) <= Decimal("0.01")     # REQ-NET-043 상한
```

`66.03 + 13.98 = 80.01`, 순매출 `80.00` → 잔차 `+0.01`. AC-NET-005와 함께 REQ-NET-043 상한 검증을 2중화한다(감사 N5: 잔차 `0.01` 픽스처는 이 둘이며 AC-NET-005 단독이 아니다). **M10 아래에서는 잔차가 `0.00`이 되어**(`52.80 + 27.20 = 80.00`) 첫 단정이 깨진다 — 즉 이 두 줄도 M10의 부수 판별자다.

**판별력 — 변이별 결과값**

| 변이 | `total_weight_grams` | `confirmed_cost` | `korea_warehouse_cost` | `total_cost` | `margin_amount` | `margin_rate` |
|------|----------------------|------------------|------------------------|--------------|-----------------|---------------|
| 기대(정답, 합산) | **500** | **"10.00"** | **"1.25"** | **"13.98"** | **"66.03"** | **"82.53"** |
| **M10 덮어쓰기** (`refunded_qty[id] = qty`) | **1000** | **"20.00"** | **"1.75"** | **"27.20"** | **"52.80"** | **"66.00"** |
| M1 순액화 없음 | 1500 | "30.00" | "2.25" | "40.43" | "59.58" | "59.58" |

**M10 아래에서 이 AC가 실패하는 정확한 이유**: 덮어쓰기 변이는 R1 처리 후 `refunded_qty[id] = 1`, R2 처리 후 `refunded_qty[id] = 1`(마지막 값으로 대입)이 되어 총 환불 수량을 **2가 아니라 1로** 본다 → 순수량 `3−1 = 2`. **매출 측은 별도 누산기이므로 영향받지 않아** 순매출은 정상적으로 80.00이다. 따라서 7필드 중 **6개가 동시에 갈린다** — `total_weight_grams`(500 vs 1000)만으로도 즉시 실패한다.

**왜 기존 15개 AC로는 못 잡았는가**: AC-NET-001은 환불 2행이지만 **서로 다른 라인**을 가리키고, AC-NET-007은 3행이지만 역시 **전부 다른** 대상(`None`/A/B)이다. 나머지 AC는 모두 환불 1행 이하다. 같은 `line_item_id`에 2행이 붙은 픽스처가 하나도 없어 덮어쓰기와 합산이 **관측상 구별되지 않았다**(감사 D2의 픽스처 전수 열거표).

---

## AC-NET-016 — 메모이제이션 계약: 주문당 계산 1회 `[BE]` `[감사 D1 신규]`

Traces: **REQ-NET-033**
잡는 변이: **M11 (유일)**

> **[HARD] 이 AC는 무수정 코드에서 통과하는 것이 정상이다** — 불변식 **보존** AC다(감사 D3). 현재 `serializers.py:513-540`의 캐시가 이미 `call_count == 1`을 보장하고, (a)는 순액화 여부에 무관한 바이트 동일성 단정이므로 무수정/수정 후 양쪽에서 통과한다(감사 N1의 조치 근거 — 아래 (a) 주석 참조).

**Given** AC-NET-001의 픽스처(#37454 형태) 그대로. **먼저 스파이 밖에서 기준(baseline) 요청 1건**을 보내고, 그 다음 `_compute_cost_breakdown_for_rate`(모듈 레벨 함수, `serializers.py:31`)를 원본 동작을 보존하는 스파이로 감싸 **동일 요청**을 한 번 더 보낸다:

```python
COST_FIELDS = (
    "margin_amount", "margin_rate", "shipping_cost", "korea_warehouse_cost",
    "total_weight_grams", "confirmed_cost", "total_cost",
)

import order.serializers as ser

res_baseline = auth_client.get(DETAIL_URL.format(pk=order.pk))     # 스파이 밖

with mock.patch(
    "order.serializers._compute_cost_breakdown_for_rate",
    wraps=ser._compute_cost_breakdown_for_rate,
) as spy:
    res_spied = auth_client.get(DETAIL_URL.format(pk=order.pk))    # 스파이 안
```

`_compute_cost_breakdown_uncached`(`serializers.py:553`)는 이 함수를 **모듈 전역에서 호출 시점에** 조회하므로 `mock.patch`로 가로챌 수 있다. `wraps`가 원본을 그대로 실행하므로 응답 값은 변하지 않아야 한다 — (a)가 바로 그것을 검증한다.

**When** 위 두 요청

**Then**
- (a) `res_spied.status_code == res_baseline.status_code == 200`이고 **7필드가 두 응답 사이에 바이트 동일하다**:
  ```python
  assert {k: res_spied.data[k] for k in COST_FIELDS} \
      == {k: res_baseline.data[k] for k in COST_FIELDS}
  ```
  즉 **AC-NET-001의 순액화된 기대값을 참조하지 않는다** — 스파이가 관측을 넘어 동작에 개입하지 않았다는 것만 검증한다.
- (b) `spy.call_count == 1` — **주문 1건 직렬화당 정확히 1회**

> **[감사 N1] (a)를 이 형태로 쓰는 이유 — 이 AC를 진짜 불변식 보존 AC로 만들기 위해서다.** 이전 버전의 (a)는 "응답의 7필드가 **AC-NET-001의 기대값**과 동일하다"였다. AC-NET-001의 기대값은 **순액화된** 값(`3418 / "34.69" / … / "29.86"`)이므로, 무수정 코드(`4453 / "51.92" / … / "32.08"`)에서 (a)는 **반드시 실패한다** — 그런데 이 AC는 6곳에서 "무수정 코드에서 통과가 정상"으로 분류되어 있었다. 구현자가 RED 단계에서 그 충돌을 만나면 가장 값싼 해소책은 (a)의 값 단정을 지우는 것이고, 그러면 `wraps` 누락 검출력이 사라져 **M11의 단독 판별자가 조용히 무력화된다**. 바이트 동일성 형태는 순액화 여부에 무관하므로 무수정 코드와 수정 후 코드 **양쪽에서 통과**한다 — REQ-NET-033이 이 SPEC이 바꾸지 않는 `[EXISTING]` 불변식이라는 사실과 정확히 일치하는 의미론이다.
>
> **(a)가 `wraps` 누락을 잡는 이유 (실측 확인)**: `wraps`를 빼면 `mock.patch`는 맨 `MagicMock`을 만들고, 그것은 `is None`(False), `__getitem__`, `.quantize()`, `== Decimal("0")`(False)을 **전부 지원한다** — 이 세션에서 직접 실행해 확인했다. 따라서 "7필드가 `None`이 아니다" 수준의 약한 단정으로는 검출되지 않는다. 반면 게터가 반환하는 값은 `str(MagicMock.quantize(...))` = `"<MagicMock name='...' id='...'>"` 형태의 문자열이 되어 baseline의 실제 값과 다르므로, **바이트 동일성 단정이 즉시 잡는다**. 즉 이 형태는 검출력을 유지하는 데 그치지 않고 하드코딩된 값 대신 살아있는 기준과 비교하므로 더 견고하다.

**M11 아래에서 이 AC가 실패하는 정확한 이유**: DRF는 7개 `SerializerMethodField`를 각각 독립적으로 평가한다(`serializers.py:555-615`). 메모이제이션을 우회하는 변이 — 게터가 `self._compute_cost_breakdown(obj)`(`:513-540`, 캐시) 대신 `self._compute_cost_breakdown_uncached(obj)`(`:542-553`)를 직접 호출하거나, `:531-536`의 캐시 조회 3행을 삭제한 경우 — 에서는 `_compute_cost_breakdown_for_rate`가 **7회** 호출되어 `spy.call_count == 7`이 된다. (b)가 실패한다.

**이 AC가 없으면 REQ-NET-033은 완전히 미커버다**: 위 변이는 총 쿼리 수(8), `orders_refund` 수(1), `orders_exchangerate` 수(1)를 **하나도 바꾸지 않는다** — 순액화는 prefetch 캐시를 읽고(REQ-NET-030), `_get_exchange_rate`는 `serializers.py:466-498`에서 독립 메모이즈되어 있기 때문이다. 따라서 AC-NET-009는 이 변이를 검출할 수 없다(감사 D1). 함수 호출 횟수는 이 위반의 **유일한 관측 가능한 신호**다.

**이 AC가 잡지 못하는 것 — 명시적 한계** (감사 N3): 이전 버전은 "이 AC는 M6에 대해서도 2차 방어선이 된다"고 적었으나 **그 주장은 무근거이며 삭제했다**. M6의 정의(§0 표)는 "`Subquery`/`OuterRef` 또는 `obj.refunds.filter(...)`"이며, 그 변이는 `_compute_cost_breakdown_for_rate` **내부**에 쿼리를 추가한다 — 함수는 여전히 `_compute_cost_breakdown`(`serializers.py:513-540`) 캐시를 경유해 주문당 **1회** 호출되므로 `spy.call_count == 1`이 그대로 통과한다. 호출 수를 7로 만드는 것은 캐시 우회(= M11)뿐이다. M6은 AC-NET-009/010이 잡는다.

---

## 추적표 (AC → 테스트)

| AC | 테스트 수 | 성격 | 잡는 변이 | 무수정 코드에서 |
|----|-----------|------|-----------|-----------------|
| AC-NET-001 | 1 | 프로덕션 집계값 재현 | M1, M2, M3 | 실패 |
| AC-NET-002 | 1 | **핵심 판별자** | M1, M2, M3, **M4**, M8 | 실패 |
| AC-NET-003 | 2 (parametrize) | 화면 화해 | M2 | 실패 |
| AC-NET-004 | 2 ((a) 상세 / (b) 목록) | 경계 | M1, M3, 권수0 분기, 목록 게이트 삭제 | 실패 |
| AC-NET-005 | 1 | 경계 + 잔차 `0.01` 특성화 | 사후 평가, M2(잔차 20.01) | 실패 |
| AC-NET-006a | 2 (parametrize) | 방어 | M5 (수량) | 실패 |
| AC-NET-006b | 2 (parametrize) | 방어 | M5 (매출) | 실패 |
| AC-NET-007 | 1 | NULL 내구성 | 가드 삭제, 매출 한정 | 실패 |
| AC-NET-008 | 1 | 미매칭 환불 | 매출 한정 | 실패 |
| AC-NET-009 | 1 | **MUST-PASS** 성능 | M6 (상세) | **통과 (정상)** |
| AC-NET-010 | 1 | **MUST-PASS** 성능 | M6 (목록) | **통과 (정상)** |
| AC-NET-011 | 1 | 두 경로 일치 | M9 | 실패 |
| AC-NET-012 | 1 | 반올림 | **M7 (단독)** | 실패 |
| AC-NET-013 | 1 | 비목표 고정 | 범위 초과 | **통과 (정상)** |
| AC-NET-014 | 1 | 하위 호환 | 상수/공식 변경 | **통과 (정상)** |
| **AC-NET-015** | 1 | **합산 축 판별자** + 잔차 `0.01` `[신규]` | **M10 (단독)**, M1 | 실패 |
| **AC-NET-016** | 1 | 메모이제이션 계약 `[신규]` | **M11 (단독)** | **통과 (정상)** |

합계 **17개 AC / 21개 테스트**. 무수정 코드에서:

| 단위 | 실패 | 통과 | 합계 |
|------|------|------|------|
| **AC 단위** | **12** (001,002,003,004,005,006a,006b,007,008,011,012,015) | **5** (009,010,013,014,016) | **17** |
| **테스트 단위** | **16** | **5** | **21** |

(감사 N4 정정: 이전 버전은 "12개 실패 / 9개 통과"로 AC 단위 실패 수와 테스트 단위 총수를 섞었다 — `12 + 9 = 21`은 어느 단위에도 해당하지 않는다.)

**변이 커버리지 확인**: M1(001,002,004,015) M2(001,002,003,**005**) M3(001,002,004,007) **M4(002 단독)** M5(006a,006b) M6(009,010) M7(**012 단독**) M8(002) M9(011) **M10(015 단독)** **M11(016 단독)** — **11개 변이 전부** 최소 1개 AC가 잡으며, 단독 판별자는 **M4/M7/M10/M11 네 건**이다.

(감사 N2/N3 정정: M7에서 005를 제거했다 — 그 픽스처의 순확정 금액이 0이어서 관측되지 않는다. M6에서 016을 제거했다 — M6은 캐시를 경유하므로 호출 수가 1로 유지된다. 두 정정으로 M7은 AC-NET-012 **단독** 판별자가 된다.)

**[HARD] 단독 판별자 보호 규칙**: M4는 AC-NET-002만, M7은 AC-NET-012만, M10은 AC-NET-015만, M11은 AC-NET-016만 잡는다. 이 **네** AC 중 하나라도 삭제·약화·픽스처 변경되면 해당 변이가 즉시 미커버가 된다. 특히:
- AC-NET-002의 "수량 3 중 1건 환불" — 부분 환불 구조 자체가 판별력이다
- AC-NET-012의 "`confirmed_price=10005.00`" — 순확정 금액이 `10.005`로 5로 끝나야 선반올림이 관측된다
- AC-NET-015의 "같은 `line_item_id`에 환불 2행" — 두 행이 다른 라인을 가리키면 즉시 무력화
- AC-NET-016의 (a) 바이트 동일성 단정 — 삭제하면 `wraps` 누락을 검출할 수단이 사라진다(맨 `MagicMock`은 non-None 단정을 통과한다)

픽스처를 단순화하거나 단정을 줄이지 말 것.

---

## Definition of Done

### 신규 검증
- [ ] AC-NET-001 ~ AC-NET-016 (**17개 AC / 21개 테스트**) 전부 통과
- [ ] AC-NET-009/010은 **MUST-PASS** — 다른 AC 점수로 상쇄될 수 없다
- [ ] **RED 성립 확인은 아래 12개 AC에만 적용한다**: AC-NET-001, 002, 003, 004, 005, 006a, 006b, 007, 008, 011, 012, **015**. 작성 직후 무수정 코드에서 실행해 실패를 직접 확인한다. 이 중 하나가 현재 코드에서 통과한다면 픽스처가 판별력을 잃은 것이다(예: `shopify_line_item_id`를 작은 값으로 두어 M8이 통과, 또는 AC-NET-015의 환불 2행이 실수로 서로 다른 라인을 가리켜 M10이 통과)
- [ ] **[HARD] 아래 5개 AC는 무수정 코드에서 통과하는 것이 정상이며, 통과를 근거로 픽스처를 수정하지 않는다** (감사 D3): **AC-NET-009**(상세 쿼리 수), **AC-NET-010**(목록 쿼리 수), **AC-NET-013**(비목표 고정), **AC-NET-014**(하위 호환), **AC-NET-016**(메모이제이션 계약). 이들은 불변식 **보존** AC이므로 "현재 코드가 이미 만족한다 = 정상"이다. 특히 AC-NET-009/010을 "고장난 테스트"로 판단해 픽스처를 고치면 R3(주문당 +50 쿼리, 원격 DB 130ms/쿼리 → 약 +6.5초)에 대한 **유일한 방어선**이 사라진다
- [ ] **[HARD] AC-NET-016의 (a)는 AC-NET-001의 기대값을 참조해서는 안 된다** (감사 N1). 스파이 **밖에서** 보낸 baseline 요청과의 **바이트 동일성**으로 구현한다 — 그래야 순액화 여부에 무관해져 무수정 코드에서도 통과하고, 위 항목의 분류가 참이 된다. 하드코딩된 순액화 값을 (a)에 넣으면 이 AC가 RED 대상이 되어 위 [HARD]와 충돌하고, 그 충돌을 (a) 삭제로 해소하면 `wraps` 누락 검출력이 사라진다
- [ ] AC-NET-015 작성 시 두 `Refund` 행이 **같은** `shopify_line_item_id`를 가리키고 `shopify_refund_id`는 **서로 다름**을 픽스처에서 눈으로 확인한다 — `unique_together`(`models.py:342`)가 요구하는 형태이며, 같은 `shopify_refund_id`를 쓰면 `IntegrityError`로 테스트가 엉뚱한 이유로 실패한다

### 회귀 검증 (전부 **무수정** 통과)
- [ ] `backend/order/tests/test_spec_021.py` 21개 — 고정값 편집 **0건**. `korea_warehouse_cost "2.25"`(`:113`, `:151`), `"1.80"`(`:358`), `"1.25"`(`:429`), `total_cost "13.98"`(`:433`), `margin_amount "67.75"`/`"159.58"`/`"68.20"` 전부 무수정
- [ ] `test_spec_021.py:268-313` (T9, `ORDER_DETAIL_QUERY_COUNT = 8`) 무수정 통과
- [ ] `backend/order/tests/test_spec_023.py` 전량 (1027행) — 특히 `:848`(`DETAIL_SERIALIZER_FIELDS` **45개** 필드셋 — 프로그램 카운트로 확정), `:638-681`(`TOTAL_QUERY_COUNT = 8`), `:875-1027`(환불 순액 **표시** 판정 테스트 6건 — 이 SPEC이 건드리지 않는 boolean 필터 경로가 그대로 동작함을 확인)
- [ ] `backend/order/tests/` 전체 스위트

> **[HARD] 실행 규약**: 이 프로젝트는 원격 공유 DB를 쓴다. **테스트를 동시에 실행하지 않는다**(동시 실행 시 가짜 실패). 서브셋 실행 시 `--no-cov`를 반드시 붙인다(안 붙이면 전부 통과해도 종료코드 1).

### 코드 범위 검증
- [ ] `git diff backend/order/serializers.py` — 변경이 `_compute_cost_breakdown_for_rate`(`:31-73`) 본문과 그 위 `@MX` 주석 블록에 국한된다
- [ ] 7개 게터(`:555-615`), 메모이제이션(`:513-540`), null 게이트 2곳(`:570-571`, `:283-284`)의 조건식 **무변경**
- [ ] `git diff --stat frontend/` **공집합** (REQ-NET-044)
- [ ] `git diff --stat backend/order/models.py backend/order/views.py` **공집합** (마이그레이션·prefetch 변경 없음)
- [ ] `backend/order/migrations/` 신규 파일 **0건** (`spec.md` Exclusions 2)

### 문서
- [ ] mx_plan 실행 완료 및 ANCHOR 강등 보고 (`plan.md` §mx_plan)
- [ ] `spec.md` HISTORY에 구현 결과(실측 쿼리 수, 통과 테스트 수)를 기록
