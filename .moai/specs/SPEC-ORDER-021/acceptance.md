---
id: SPEC-ORDER-021
document: acceptance
version: 1.4.0
status: implemented
updated: 2026-08-15
---

# 인수 기준 — SPEC-ORDER-021 마진 계산에 배송비·한국창고비 반영

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의 AC-COST-XXX / REQ-COST-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` 인수 기준 절의 동일 AC 항목이 선언한 것과 완전히 일치한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다.

[HARD] **판별력 요건.** 모든 금전 단정은 손으로 계산한 정확한 문자열/숫자 값이다 — "마진이 null이 아니다"류의 약한 단정은 보조적으로만 쓰고, 핵심 단정은 항상 정확한 값이다. 이 프로젝트는 판별력 없는 인수 기준으로 이미 손해를 본 전례가 있다(`SPEC-ORDER-018` v1.0.3/v1.0.4, `SPEC-ORDER-020` v1.0.2 N1).

**검증 레이어**: `[BE]` = `backend/order/tests/test_spec_021.py`(pytest + DRF `APIClient`), `[FE]` = `frontend/src/pages/OrderDetailPage.test.tsx`(vitest + React Testing Library). 이 SPEC의 신규 시나리오는 대부분 `[BE]`다.

**공통 픽스처 관례**: `total_price`/`rate`는 나눗셈이 딱 떨어지도록 의도적으로 고른다(예: `rate=1000.00`) — 계산 과정의 반올림과 최종 결과의 반올림을 분리해서 검증하기 위함이다. `confirmed_price`는 항상 **개당(단가)** 값이다(`item.confirmed_price * quantity`가 라인아이템 원가라는 기존 관례, `serializers.py:199`).

---

## 정상 마진 계산

### AC-COST-001 — 단일 SKU 3권 주문의 한국창고비 `[BE]`

Traces: REQ-COST-004, REQ-COST-005, REQ-COST-008, REQ-COST-011, REQ-COST-012, REQ-COST-013

- **Given**: `Order(total_price="100.00", shopify_created_at=오늘)`, `ExchangeRate(effective_date=오늘, rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=3, confirmed_price="10000.00", grams=0)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: 응답의 `margin_amount == "67.75"`, `korea_warehouse_cost == "2.25"`, `shipping_cost == "0.00"`, `total_weight_grams == 0`.
  - 계산 근거: `confirmed_cost_usd = 10000×3/1000 = 30.00`. `total_book_count=3` → `korea_warehouse_krw = 1250+500×2 = 2250` → `/1000 = 2.25`. `margin_usd = 100 - 30 - 0 - 2.25 = 67.75`.
- **판별력**: base fee 없이 권수당 정액(`500×total_book_count`)으로 잘못 구현하면 `korea_warehouse_krw=1500` → `korea_warehouse_cost == "1.50"`이 되어 실패한다. `-1`을 빠뜨리고 `1250+500×total_book_count`로 구현하면 `korea_warehouse_krw=2750` → `korea_warehouse_cost == "2.75"`가 되어 실패한다. 둘 다 정답(`"2.25"`)과 다르다.

### AC-COST-002 — 여러 라인아이템에 걸친 권수 합산은 단일 SKU와 동일한 결과를 낸다 `[BE]`

Traces: REQ-COST-004, REQ-COST-005, REQ-COST-008

- **Given**: AC-COST-001과 동일한 `total_price`/`rate`, 라인아이템 2개 — `LineItem(quantity=2, confirmed_price="10000.00", grams=0)`, `LineItem(quantity=1, confirmed_price="10000.00", grams=0)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: 응답의 `margin_amount == "67.75"` — AC-COST-001과 **정확히 동일**.
- **판별력**: 한국창고 기본료(1250원)를 주문당이 아니라 **라인아이템당** 적용하면 `korea_warehouse_krw = (1250+500×1) + (1250+500×0) = 3000`이 되어 `korea_warehouse_cost == "3.00"`, `margin_amount == "67.00"`이 된다 — AC-COST-001 단독으로는 이 mutation을 잡지 못한다(라인아이템이 1개뿐이라 "주문당"과 "아이템당"이 우연히 같은 결과를 내기 때문). 이 AC가 그 구분을 전담한다.

### AC-COST-003 — 무게 가중 배송비와 노출 필드의 반올림 아티팩트 `[BE]`

Traces: REQ-COST-002, REQ-COST-003, REQ-COST-008, REQ-COST-011, REQ-COST-012, REQ-COST-013

- **Given**: `Order(total_price="200.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=3, grams=500, confirmed_price="10000.00")`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**:
  - (a) `total_weight_grams == 1500`(`500×3`).
  - (b) `shipping_cost == "8.18"`(정확값 `5.45×1500/1000 = 8.175`를 ROUND_HALF_UP).
  - (c) `korea_warehouse_cost == "2.25"`.
  - (d) `margin_amount == "159.58"`, `margin_rate == "79.79"`.
- **알려진 반올림 아티팩트(정보성, mutation 아님)**: `200.00 - 30.00(confirmed) - 8.18(shipping_cost) - 2.25(korea_warehouse_cost) = 159.57`로 노출된 `margin_amount`(`159.58`)와 1센트 다르다 — `margin_usd`는 정확값(`8.175`)으로 계산되기 때문이며 의도된 설계다(`spec.md` 설계 결정 B). 테스트는 이 불일치를 재현하지 않고, `margin_amount`가 정확히 `"159.58"`임만 단정한다.
- **판별력**: `total_weight_grams`를 kg 단위로 변환하지 않고(`/1000` 누락) 그대로 곱하면 `shipping_cost == "8175.00"`이 되어 (b)와 (d) 둘 다 실패한다. `total_weight_grams` 노출값을 그램이 아니라 kg로 잘못 노출하면(a)가 `2`(또는 `1`)가 되어 실패한다.

### AC-COST-004 — `grams=None`과 `grams=0`은 동일하게 0으로 처리되며 마진이 `null`이 되지 않는다 `[BE]`

Traces: REQ-COST-002

- **Given**: `Order(total_price="50.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 2개 — A: `LineItem(quantity=2, grams=None, confirmed_price="5000.00")`, B: `LineItem(quantity=1, grams=0, confirmed_price="5000.00")`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: HTTP 200. `margin_amount == "32.75"`(`not None`). `total_weight_grams == 0`, `shipping_cost == "0.00"`.
  - 계산 근거: `confirmed_cost_usd = (5000×2+5000×1)/1000 = 15.00`. `total_book_count=3` → `korea_warehouse_usd=2.25`. `margin_usd=50-15-0-2.25=32.75`.
- **판별력**: `grams`가 `None`일 때 `0`으로 치환하지 않고 산술 연산에 그대로 쓰면 `TypeError`가 발생해 응답이 500이 된다 — 이 시나리오의 HTTP 200 자체가 1차 판별력이며, `margin_amount` 정확값이 2차 판별력이다.

### AC-COST-005 — 미확정 라인아이템도 무게·권수 합산에는 포함되지만 매입원가 합산에는 제외된다 `[BE]`

Traces: REQ-COST-002, REQ-COST-004, REQ-COST-008

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 2개 — A(확정): `LineItem(quantity=2, confirmed_price="10000.00", grams=300)`, B(미확정): `LineItem(quantity=1, confirmed_price=None, grams=600)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `total_weight_grams == 1200`(A의 `300×2=600` + B의 `600×1=600`). `margin_amount == "71.21"`.
  - 계산 근거: `confirmed_cost_usd = 10000×2/1000 = 20.00`(B 제외). `shipping_cost_usd = 5.45×1200/1000 = 6.54`. `total_book_count=2+1=3`(B의 수량 포함) → `korea_warehouse_usd=2.25`. `margin_usd=100-20-6.54-2.25=71.21`.
- **판별력**: 무게/권수 집계 루프를 `confirmed_price is not None` 조건 안으로 옮기면(원가 합산 루프와 게이트를 공유) B가 무게·권수에서도 빠져 `total_weight_grams == 600`, `total_book_count == 2`(→ `korea_warehouse_krw=1750`, `usd=1.75`), `margin_amount == "74.98"`이 되어 실패한다(`100-20-3.27-1.75=74.98`).

## None 게이트 (기존 동작 보존 + 확장)

### AC-COST-006 — 환율 없음 → 5개 필드 전부 `null` `[BE]`

Traces: REQ-COST-009

- **Given**: AC-COST-001과 동일한 라인아이템 구성(`quantity=3, confirmed_price="10000.00", grams=0`)이지만 해당 주문일 이전 어떤 날짜에도 `ExchangeRate` 레코드가 없다.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: HTTP 200. `margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams` 다섯 키 **전부가 응답에 존재**하며(`"shipping_cost" in res.data`), 각각의 값이 `None`이다. [HARD] 이 단정은 **키 존재**와 **값이 `None`** 둘 다를 확인해야 한다 — `res.data.get("shipping_cost") is None`처럼 `.get(...)`만 쓰는 조회는 키가 아예 없어도(필드 미구현) `None`을 반환하므로(감사 D6, `test_spec_008.py:235,254,282` 등에 이미 있는 관례), 그 방식으로는 "필드를 아예 구현하지 않은" 상태와 "필드는 있지만 null을 반환하는" 상태를 구분하지 못한다.
- **판별력**: `shipping_cost`/`total_weight_grams` 계산을 환율 게이트 밖에서 독립적으로 수행하면(무게 계산 자체는 환율이 필요 없으므로) 이 두 필드만 값을 반환해버려 실패한다 — 설계 결정 D(단일 게이트)의 직접 판별 지점. 별도로, 신규 필드를 아예 구현하지 않으면(`Meta.fields` 누락) 키 존재 단정이 즉시 실패한다 — 이것이 이 AC가 현재(무수정) 코드에서 반드시 실패해야 하는 이유이며(`plan.md` M1), 키 존재 단정이 없으면 이 시나리오는 무수정 코드에서도 통과해버린다.

### AC-COST-007 — 확정 매입가 전무 → 5개 필드 전부 `null` `[BE]`

Traces: REQ-COST-010

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1000.00")`(유효), 라인아이템 1개 `LineItem(quantity=3, grams=500, confirmed_price=None)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: 다섯 키 **전부가 응답에 존재**하며(`"shipping_cost" in res.data` 등, AC-COST-006과 동일한 이중 단정 요건), 각각의 값이 `None`이다 — 무게 데이터(`grams=500, quantity=3` → 이론상 `total_weight_grams=1500` 계산 가능)가 존재함에도 불구하고.
- **판별력**: AC-COST-006과 대칭적인 판별 지점 — `shipping_cost`/`total_weight_grams`가 `has_any_confirmed` 게이트 밖에서 독립 계산되면 무게 데이터가 있으므로 값을 반환해버려 실패한다. 키 존재 단정이 없으면 신규 필드 미구현 상태가 `res.data.get(...) is None`을 그대로 통과시켜버린다 — 키 존재 단정이 이 mutation의 유일한 판별 수단이다.

### AC-COST-008 — `total_book_count == 0`일 때 한국창고비는 0원이다(기본료를 청구하지 않는다) `[BE]`

Traces: REQ-COST-006

- **Given**: `Order(total_price="50.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=None, confirmed_price="5000.00", grams=None)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `korea_warehouse_cost == "0.00"`, `margin_amount == "50.00"`.
  - 계산 근거: `quantity=None`이므로 `confirmed_cost_krw = 5000×0 = 0`, `total_weight_grams=0`, `total_book_count=0` → `korea_warehouse_krw=0`(REQ-COST-006) → `margin_usd=50-0-0-0=50.00`.
- **판별력**: REQ-COST-006의 0-분기 없이 공식을 그대로 적용하면 `korea_warehouse_krw = 1250 + 500×max(0-1,0) = 1250+0 = 1250`(음수 방지용 `max`가 base fee 자체는 상쇄하지 못함)이 되어 `korea_warehouse_cost == "1.25"`, `margin_amount == "48.75"`가 된다 — `"0.00"`과 명확히 다르다.

## 성능 불변식

### AC-COST-009 — 쿼리 수 불변식: 라인아이템 수와 무관하고, 신규 필드가 라인아이템 재쿼리·환율 재조회를 추가하지 않는다 `[BE]`

Traces: REQ-COST-015

- **Given**: 무관한 주문 1건(워밍업 대상). 주문 X — 라인아이템 1개, 확정(`confirmed_price` 설정) + 유효 `ExchangeRate`. 주문 Y — 라인아이템 5개, 전부 확정 + 동일 `ExchangeRate`.
- **When**:
  1. **워밍업**: 워밍업 대상 주문에 대해 `GET /api/orders/{warmup.pk}/`를 캡처 없이 1회 먼저 호출한다 — `test_spec_018.py:490-492`의 선례와 동일한 이유(첫 요청에서만 발생하는 쿼리 — 예: Django 콘텐츠타입/권한 캐시 최초 적재 — 가 X 또는 Y 어느 한쪽의 측정 창에만 비대칭적으로 들어가는 것을 방지)다.
  2. `django.test.utils.CaptureQueriesContext(connection)`(`backend/order/tests/test_spec_018.py:40`의 기존 임포트를 재사용)로 각각 `GET /api/orders/{X.pk}/`, `GET /api/orders/{Y.pk}/`를 감싸 캡처한다.
- **Then**:
  - (a) `len(ctx_x.captured_queries) == len(ctx_y.captured_queries) == ORDER_DETAIL_QUERY_COUNT` — `ORDER_DETAIL_QUERY_COUNT`는 이 테스트를 작성하는 시점에 올바른(메모이즈된) 구현으로 실제 실행해 관측한 값을 상수로 고정한다(`test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`와 동일한 관례 — 추측값을 넣지 않는다). 라인아이템 수가 5배 늘어도 총 쿼리 수는 이 절대값과 동일해야 한다.
  - (b) `ctx_x`와 `ctx_y` 각각에서, `orders_line_item` 테이블(`backend/order/models.py:240-241`에 `db_table = "orders_line_item"`으로 명시적으로 선언됨)을 참조하는 쿼리의 개수가 **정확히 1**이다 — 매칭은 부분 문자열(`"orders_line_item" in sql`)이 아니라 정규식 `orders_line_item(?!_)`(부정 전방탐색으로 뒤에 `_`가 오지 않는 경우만 매치) 또는 `connection.ops.quote_name("orders_line_item")`(백틱/따옴표로 감싼 완전한 식별자)과의 완전 일치를 쓴다. [HARD] 단순 `in` 검사를 쓰면 안 되는 이유: `LineItemNote.Meta.db_table = "orders_line_item_note"`(`backend/order/models.py:296-298`)이고, 뷰가 `line_items__notes__author`를 prefetch하므로(`backend/order/views.py:41-45`) 올바른 구현도 `orders_line_item_note`를 참조하는 쿼리를 1개 더 발급한다 — 부분 문자열 매칭은 이 두 번째 쿼리까지 세어 **정상 구현에서 2를 반환하는 거짓 실패**를 낸다(감사 D1, `test_spec_016.py:1026`이 같은 부분 문자열 패턴을 쓰지만 그 코드 경로는 notes를 조회하지 않아 우연히 안전하다 — 이 SPEC에서는 안전하지 않다).
  - (c) `ctx_x`와 `ctx_y` 각각에서, `orders_exchangerate` 테이블(`backend/order/models.py:507`에 `db_table = "orders_exchangerate"`로 명시적으로 선언됨 — 이 테이블명은 다른 어떤 테이블명의 부분 문자열도 아니므로 단순 `in` 검사로 충분하다)을 참조하는 쿼리의 개수가 **정확히 1**이다.
- **판별력**: (a)는 무게/권수 집계를 라인아이템별 개별 쿼리로 구현하면(N+1) X(1개 아이템)와 Y(5개 아이템)의 쿼리 수가 달라져 실패한다. (a)의 **절대값 고정**은 아이템 수와 무관한 상수 +1 쿼리(예: `obj.line_items.all()` 재사용 대신 신규 `LineItem.objects.filter(order=obj).aggregate(...)` 호출, 또는 5개 게터가 헬퍼를 메모이제이션 없이 독립 호출)도 잡는다 — X와 Y가 서로 같다는 상대 비교만으로는(둘 다 동일하게 늘어나 여전히 같으므로) 이런 종류의 mutation을 잡지 못하기 때문에 절대값 고정이 필수다(감사 D5). (b)는 위 라인아이템 상수 +1 mutation이 `orders_line_item` 정확 매칭 쿼리 수를 2로 만들어 별도로 원인을 지목한다. (c)는 REQ-COST-015의 "주문 직렬화당 최대 1회" 요건을 어기고 5개 게터가 헬퍼를 캐시 없이 독립 호출하면(설계 결정 F) `ExchangeRate` 쿼리가 최대 5개까지 늘어나는 것을 직접 잡는다 — (a)의 절대값도 이 mutation에서 함께 어긋나지만, (c)가 원인을 `ExchangeRate` 테이블로 직접 지목해 진단을 좁힌다(감사 D5).

## 범위 경계

### AC-COST-010 — 목록 API는 비용 내역을 노출하지 않는다 `[BE]`

Traces: REQ-COST-014

- **Given**: 유효한 `ExchangeRate`와 확정 매입가를 가진 주문 1건 이상.
- **When**: `GET /api/orders/`(목록).
- **Then**: 응답 `results`(또는 배열)의 각 항목에 `"shipping_cost"`, `"korea_warehouse_cost"`, `"total_weight_grams"` 키가 없다(`"margin_amount" not in item`과 동일한 기존 단정 패턴을 세 키로 확장).
- **판별력**: `OrderListSerializer.Meta.fields`(`backend/order/serializers.py:14-36`)에 신규 필드를 실수로 추가하면 해당 키가 나타나 실패한다.

## 프론트엔드 표시

### AC-COST-011 — 배송비·한국창고비가 마진 옆에 표시된다 `[FE]`

Traces: REQ-COST-016, REQ-COST-017

- **Given (1차)**: `buildOrderDetail({ margin_amount: "159.58", margin_rate: "79.79", shipping_cost: "8.18", korea_warehouse_cost: "2.25" })`(`frontend/src/pages/OrderDetailPage.test.tsx:35-95`의 기존 헬퍼에 두 필드를 추가한 것, AC-COST-003과 동일한 값)로 `useOrderDetail` 모킹.
- **When (1차)**: `renderPage()`(`:20-33`)로 렌더링.
- **Then (1차)**: 기존 마진/마진율 표시 영역(`OrderDetailPage.tsx:512-525`) 안에서 "8.18 USD"와 "2.25 USD" 텍스트가 모두 발견된다.
- **픽스처 참고(감사 D3)**: `shipping_cost: "0.00"`을 쓰지 않는 이유 — 기존 표시 관례는 `` `${Number(data.margin_amount).toLocaleString()} USD` ``(`OrderDetailPage.tsx:515-517`)이고, `Number("0.00").toLocaleString()`은 `"0"`이다. 즉 `"0.00"` 픽스처를 쓰면 정상 구현이 "0.00 USD"가 아니라 "0 USD"를 렌더링해 `/0\.00 USD/` 단정이 **정상 구현에서도 실패한다.** `"8.18"`은 `Number("8.18").toLocaleString() === "8.18"`이라 왕복이 보존된다.
- **Given (2차)**: 동일 헬퍼를 `shipping_cost: null, korea_warehouse_cost: null`로 오버라이드.
- **When (2차)**: `renderPage()`로 렌더링.
- **Then (2차)**: 배송비·한국창고비 표시 위치에 "—"가 렌더링된다(기존 `margin_amount=null` → "—" 폴백과 동일 패턴).
- **판별력**: `OrderDetail` 타입(`frontend/src/types/order.ts:168-`)에 `shipping_cost`/`korea_warehouse_cost`를 추가하지 않으면 컴포넌트가 해당 필드에 접근하는 코드 자체가 TypeScript 컴파일 오류로 실패한다(회귀 게이트 — `tsc -b`, `npm run build`가 실제로 실행하는 명령이다. `frontend/tsconfig.json`은 `"files": []`인 솔루션 파일이라 단독 `tsc --noEmit`은 아무 파일도 타입 체크하지 않는다 — 감사 D13). 표시 로직에서 `null` 분기를 빠뜨리면 2차 단정이 "null USD" 또는 빈 문자열 렌더링으로 실패한다.

## 환율 적용 검증

### AC-COST-012 — 한국창고비 환산은 실제 환율을 사용한다(하드코딩된 나눗셈 상수가 아니다) `[BE]`

Traces: REQ-COST-007

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1250.00")`(AC-COST-001~011은 전부 `rate="1000.00"`을 공유하므로 의도적으로 다른 값을 쓴다), 라인아이템 1개 `LineItem(quantity=3, confirmed_price="12500.00", grams=0)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `korea_warehouse_cost == "1.80"`, `margin_amount == "68.20"`.
  - 계산 근거: `confirmed_cost_usd = 12500×3/1250 = 30.00`. `total_book_count=3` → `korea_warehouse_krw=2250` → `/1250 = 1.80`. `margin_usd = 100-30-0-1.80 = 68.20`.
- **이 AC가 필요한 이유(감사 D4)**: `korea_warehouse_krw / Decimal("1000")`처럼 나눗셈 상수를 실제 `er.rate` 대신 하드코딩해도(한국창고비 공식 자체가 1000 단위 숫자를 다루므로 그럴듯한 실수다) 그 값이 `rate=1000.00`과 우연히 일치해 AC-COST-001~011(전부 T1~T11) 전부를 통과한다 — 이전 버전 `spec.md`가 "AC-COST-001이 묵시적으로 REQ-COST-007을 커버한다"고 주장한 것은 재검증 결과 거짓이었다. `rate=1250.00`에서는 하드코딩된 `/1000` 구현이 `korea_warehouse_cost == "2.25"`(`2250/1000`, 오답)를 반환해 정답(`"1.80"`)과 명확히 갈린다.
- **판별력**: `korea_warehouse_usd = korea_warehouse_krw / Decimal("1000")`으로 하드코딩하면 `korea_warehouse_cost == "2.25"`, `margin_amount == "67.75"`가 되어 정답과 어긋난다.

## 반올림 모드 검증

### AC-COST-013 — ROUND_HALF_UP은 ROUND_HALF_EVEN과 구별된다 `[BE]`

Traces: REQ-COST-003, REQ-COST-011

- **Given**: `Order(total_price="50.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=1, grams=500, confirmed_price="10000.00")`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `shipping_cost == "2.73"`(정확값 `5.45×500/1000 = 2.725`를 ROUND_HALF_UP).
- **이 AC가 필요한 이유(감사 D11)**: AC-COST-003의 반올림 경계값(`8.175→8.18`, `159.575→159.58`)은 반올림 대상 자릿수 바로 앞의 숫자가 홀수(7)라서, ROUND_HALF_UP과 ROUND_HALF_EVEN(은행가 반올림 — 짝수로 반올림)이 우연히 같은 결과를 낸다(둘 다 올림해서 짝수 8이 되므로). 즉 `ROUND_HALF_EVEN` 구현도 AC-COST-003을 통과해버린다. `2.725`는 앞자리가 짝수(2)라서 HALF_UP은 올림(`"2.73"`)하고 HALF_EVEN은 이미 짝수인 앞자리를 유지하려 내림(`"2.72"`)한다 — 두 방식이 실제로 갈리는 케이스다.
- **판별력**: `ROUND_HALF_EVEN`으로 양자화하면 `shipping_cost == "2.72"`가 되어 정답(`"2.73"`)과 어긋난다.

## 확장 — confirmed_cost / total_cost 노출 및 결제 정보 화면 재구성 (v1.3.0)

이 절의 AC-COST-014~019는 v1.3.0에서 추가된 두 신규 필드(`confirmed_cost`, `total_cost`)와 `OrderDetailPage`의 결제 정보 섹션 재구성을 검증한다. `spec.md` v1.3.0의 REQ-COST-020~029를 인용한다.

### AC-COST-014 — `confirmed_cost`는 확정 매입원가(USD)를 정확히 반영한다 `[BE]`

Traces: REQ-COST-020, REQ-COST-022

- **Given**: AC-COST-001과 동일한 라인아이템 구성(`total_price="100.00"`, `rate="1000.00"`, `LineItem(quantity=3, confirmed_price="10000.00", grams=0)`).
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `confirmed_cost == "30.00"`(`confirmed_cost_usd = 10000×3/1000 = 30.00`, AC-COST-001이 이미 감사한 중간값).
- **판별력**: `confirmed_cost`를 노출하지 않거나 다른 값(예: `total_price_usd`, `margin_usd`)을 반환하면 실패한다.

### AC-COST-015 — `total_cost`는 반올림되지 않은 세 항의 합을 서버에서 계산한다(프론트엔드가 반올림된 세 필드를 합산하지 않는다) `[BE]`

Traces: REQ-COST-021, REQ-COST-023

- **Given**: `Order(total_price="100.00")`, `ExchangeRate(rate="1000.00")`, 라인아이템 1개 `LineItem(quantity=1, confirmed_price="10005.00", grams=500)`.
- **When**: `GET /api/orders/{pk}/`.
- **Then**:
  - `confirmed_cost == "10.01"`(정확값 `10.005`를 ROUND_HALF_UP).
  - `shipping_cost == "2.73"`(정확값 `2.725`를 ROUND_HALF_UP).
  - `korea_warehouse_cost == "1.25"`(정확값, 반올림 없음).
  - `total_cost == "13.98"`(정확값 `10.005+2.725+1.25=13.980`을 **한 번만** ROUND_HALF_UP한 결과).
- **판별력(핵심)**: 위 세 노출 필드(`confirmed_cost`+`shipping_cost`+`korea_warehouse_cost` = `"10.01"+"2.73"+"1.25"`)를 그대로 합산하면 `"13.99"`가 된다 — 정답(`"13.98"`)과 **1센트 차이**가 난다. 이 픽스처는 `confirmed_cost_usd`(`.005`)와 `shipping_cost_usd`(`.725`)가 각각 개별 반올림 시 올림되어 두 번의 `+0.005`가 누적되지만, 정확값의 합(`13.980`)은 이미 2자리 정밀도라 추가 반올림이 필요 없다는 사실에서 그 차이가 발생한다 — "반올림된 세 필드를 프론트엔드에서 합산하지 않고 서버가 반올림 전 정확값으로 `total_cost`를 계산한다"([HARD] 요건)는 것을 직접 판별하는 유일한 시나리오다.

### AC-COST-016 — `margin_amount == total_price − total_cost`(1센트 이내) `[BE]`

Traces: REQ-COST-021, REQ-COST-024

- **Given**: AC-COST-015와 동일한 픽스처.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `margin_amount == "86.02"`(`margin_usd = 100 - 10.005 - 2.725 - 1.25 = 86.020`). `Decimal(total_price) - Decimal(total_cost)`와 `Decimal(margin_amount)`의 차이가 `0.01` 이하임을 수치로 단정한다(`100.00 - 13.98 = 86.02`, 이 픽스처에서는 정확히 일치).
- **판별력**: `margin_usd` 계산이 변경되거나 `total_cost` 계산이 잘못되면 두 값의 차이가 1센트를 초과해 실패한다.

### AC-COST-017 — 환율 없음 → `confirmed_cost`/`total_cost`도 `null`(기존 5필드 게이트에 합류) `[BE]`

Traces: REQ-COST-025

- **Given**: AC-COST-006과 동일(환율 레코드 없음).
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `confirmed_cost`, `total_cost` 두 키 모두 응답에 존재하며(`"confirmed_cost" in res.data`), 값이 `None`이다 — AC-COST-006과 동일한 키 존재 + `None` 값 이중 단정 요건(D6 계승).
- **판별력**: 두 필드를 아예 구현하지 않으면(`Meta.fields` 누락) 키 존재 단정이 실패한다. 두 필드가 단일 게이트를 공유하지 않고 독립적으로 계산되면(설계 결정 D 위반) 값이 반환되어 `None` 단정이 실패한다.

### AC-COST-018 — 확정 매입가 전무 → `confirmed_cost`/`total_cost`도 `null` `[BE]`

Traces: REQ-COST-026

- **Given**: AC-COST-007과 동일(유효한 환율, `confirmed_price=null`, `grams=500`).
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `confirmed_cost`, `total_cost` 두 키 모두 응답에 존재하며 값이 `None`이다.
- **판별력**: AC-COST-017과 대칭 — `has_any_confirmed` 게이트 밖에서 독립 계산되면 실패한다.

### AC-COST-019 — 결제 정보 섹션이 새 순서·라벨로 재구성되고, 비용 세부항목은 시각적으로 하위 표시된다 `[FE]`

Traces: REQ-COST-023, REQ-COST-027, REQ-COST-028, REQ-COST-029

- **Given**: `buildOrderDetail({ margin_amount: "159.58", margin_rate: "79.79", shipping_cost: "8.18", korea_warehouse_cost: "2.25", confirmed_cost: "30.00", total_cost: "40.43" })`로 `useOrderDetail` 모킹(AC-COST-003 기반 픽스처 + 손계산한 `confirmed_cost`/`total_cost`).
- **When**: `renderPage()`.
- **Then**:
  - (a) DOM 순서가 `최종 결제 금액` → `비용 합계` → `원가 (확정 단가 합계)` → `배송비` → `한국물류` → `마진` → `마진율`이다(`compareDocumentPosition`으로 단정).
  - (b) `한국물류` 라벨이 렌더링되고, 이전 라벨 `한국창고비`는 더 이상 존재하지 않는다.
  - (c) `원가`/`배송비`/`한국물류` 세 줄의 컨테이너 class가 `비용 합계` 줄의 class와 다르고(`pl-` 들여쓰기 클래스를 포함), 기존 코드베이스의 옅어짐 관례(`text-muted-foreground/70`, `VendorFileUploadTab.tsx:93` 선례)를 재사용해 시각적으로 한 단계 더 옅다.
  - (d) `total_cost`/`confirmed_cost`가 `null`이면 각 줄에 `"—"`가 렌더링된다(기존 `margin_amount=null` 폴백과 동일 패턴).
- **판별력**: 순서를 뒤바꾸거나(예: `마진`을 `비용 합계`보다 먼저 렌더링) 라벨을 갱신하지 않으면(`한국창고비` 잔존) (a)/(b)가 실패한다. 세 세부항목에 들여쓰기·저채도 클래스를 적용하지 않으면(c)가 실패한다.

## 확장 — 적용 환율 노출 (v1.4.0)

이 절의 AC-COST-020~024는 v1.4.0에서 추가된 신규 필드(`exchange_rate`, `exchange_rate_date`)와 `OrderDetailPage`의 적용 환율 표시를 검증한다. `spec.md` v1.4.0의 REQ-COST-030~036을 인용한다.

### AC-COST-020 — 주문일 자체에 환율 레코드가 있을 때 `exchange_rate`/`exchange_rate_date`가 정확한 값을 반환한다 `[BE]`

Traces: REQ-COST-030, REQ-COST-031

- **Given**: `Order(shopify_created_at=오늘)`, `ExchangeRate(effective_date=오늘, rate="1427.05")`, 확정 매입가가 있는 라인아이템 1개.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `exchange_rate == "1427.05"`, `exchange_rate_date == 오늘의 ISO 문자열`.
- **판별력**: `exchange_rate`를 노출하지 않거나 다른 값을 반환하면 실패한다. 단, `exchange_rate_date`를 레코드의 `effective_date`가 아니라 주문일을 그대로 에코해도 이 시나리오만으로는 잡히지 않는다 — 이 케이스는 폴백이 없어 두 값이 우연히 같기 때문이다. 그 mutation은 AC-COST-021이 전담한다.

### AC-COST-021 — 폴백 발생 시 `exchange_rate_date`는 주문일이 아니라 실제 적용된 레코드의 날짜다(핵심 판별 테스트) `[BE]`

Traces: REQ-COST-030, REQ-COST-031, REQ-COST-034

- **Given**: `Order(shopify_created_at=D)`, `D` 당일에는 `ExchangeRate` 레코드가 없고 `D-3`에만 `ExchangeRate(effective_date=D-3, rate="1300.00")`가 존재, 확정 매입가가 있는 라인아이템 1개.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `exchange_rate == "1300.00"`, `exchange_rate_date == (D-3)의 ISO 문자열`, **그리고** `exchange_rate_date != D의 ISO 문자열`.
- **이 AC가 필요한 이유**: 이 기능 전체의 존재 이유는 `_get_exchange_rate`의 폴백(`backend/order/serializers.py:208-` 인근)을 눈에 보이게 만드는 것이다 — `exchange_rate_date`가 조회 결과의 `effective_date`가 아니라 `obj.shopify_created_at.date()`를 그대로 에코하면, 값 자체는 그럴듯해 보이지만 폴백이 발생했다는 사실이 여전히 완전히 숨겨진다.
- **판별력**: `get_exchange_rate_date`를 `obj.shopify_created_at.date().isoformat()`으로 구현하면(레코드 조회 결과를 무시하고 주문일을 그대로 반환) `exchange_rate_date == D`가 되어 정답(`D-3`)과 명확히 어긋난다.

### AC-COST-022 — `margin_amount`가 `null`이어도 `exchange_rate`/`exchange_rate_date`는 `null`이 아니다(별도 게이트) `[BE]`

Traces: REQ-COST-033

- **Given**: `Order(total_price="100.00")`, 유효한 `ExchangeRate`, 라인아이템 1개 `LineItem(quantity=3, grams=500, confirmed_price=None)`(AC-COST-007과 동일 — 확정 매입가 전무).
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `margin_amount is None`이면서 동시에 `exchange_rate`, `exchange_rate_date` 둘 다 **non-null**이다.
- **판별력**: 이 두 필드를 `_compute_cost_breakdown`(`has_any_confirmed` 게이트를 가진 기존 헬퍼)의 반환값을 거쳐 구현하면 `margin_amount`와 동일하게 `null`이 되어 실패한다 — 설계 결정 H(별도의 좁은 게이트)의 직접 판별 지점.

### AC-COST-023 — 환율 레코드 자체가 없을 때만 `exchange_rate`/`exchange_rate_date`가 `null`이다 `[BE]`

Traces: REQ-COST-032

- **Given**: AC-COST-006과 동일 조건(해당 주문일 이전 어떤 날짜에도 `ExchangeRate` 레코드가 없음), 확정 매입가가 있는 라인아이템 1개.
- **When**: `GET /api/orders/{pk}/`.
- **Then**: `exchange_rate`, `exchange_rate_date` 두 키 모두 응답에 존재하며(`"exchange_rate" in res.data`), 값이 `None`이다 — AC-COST-006/017과 동일한 키 존재 + `None` 값 이중 단정 요건(D6 계승).
- **판별력**: 두 필드를 아예 구현하지 않으면(`Meta.fields` 누락) 키 존재 단정이 실패한다.

### AC-COST-024 — 프론트엔드가 적용 환율을 마진율 다음, 비용 세부항목 그룹 밖에 표시한다 `[FE]`

Traces: REQ-COST-035, REQ-COST-036

- **Given**: `buildOrderDetail({ exchange_rate: "1427.05", exchange_rate_date: "2026-08-03" })`로 `useOrderDetail` 모킹.
- **When**: `renderPage()`.
- **Then**: "적용 환율" 라벨과 "1,427.05 KRW/USD (2026-08-03)" 텍스트가 렌더링되고, DOM 순서상 `마진율` **다음**에 위치하며, 컨테이너 class에 `pl-` 들여쓰기 클래스가 **없다**(비용 세부항목 그룹과 시각적으로 구분됨).
- **Given (2차)**: `exchange_rate: null, exchange_rate_date: null`로 오버라이드.
- **When (2차)**: `renderPage()`.
- **Then (2차)**: "적용 환율" 줄에 "—"가 렌더링된다.
- **판별력**: `OrderDetail` 타입에 두 필드를 추가하지 않으면 컴포넌트가 접근하는 코드 자체가 `tsc -b` 컴파일 오류로 실패한다(회귀 게이트). 표시 위치를 `pl-3` 들여쓰기 그룹 안에 넣으면 "들여쓰기 없음" 단정이 실패한다. `null` 폴백을 빠뜨리면 2차 단정이 실패한다.

---

## 기존 회귀 테스트 — 기대값 변경 (재작성이 아니라 값만 갱신)

아래 5개는 새 시나리오가 아니라, 새 공식 반영으로 기존 기대값이 달라지는 기존 테스트다 — `spec.md` "기존 테스트 갱신 대상" 표와 `plan.md` M1이 규범 출처다. 여기서는 계산 과정만 재확인한다.

| 테스트 | 이전 | 이후 | 계산 근거 |
|---|---|---|---|
| `test_spec_008.py::test_margin_amount_calculation_with_partial_confirmed` | `margin_amount="49981.54"` | `margin_amount="49979.81"` | `total_price=50000.00, rate=1300.00`, 확정 원가 `24000/1300≈18.4615`, `total_book_count=3`(item A qty2 + item B qty1) → `korea_warehouse_usd=2250/1300≈1.7308`. `margin=50000-18.4615-1.7308=49979.8077→49979.81`. |
| `test_spec_008.py::test_margin_rate_calculation_rounds_to_2_decimal_places` | `margin_amount="59963.08"`, `margin_rate="99.94"` | `margin_amount="59961.35"`, `margin_rate="99.94"`(값 자체는 우연히 동일 — 별도 검증 필요) | `total_price=60000.00, rate=1300.00`, 확정 원가 `48000/1300≈36.9231`, `total_book_count=3` → `korea_warehouse_usd≈1.7308`. `margin=60000-36.9231-1.7308=59961.3462→59961.35`. `rate=59961.3462/60000×100=99.9356→99.94`(반올림 경계상 이전 값과 동일하게 귀결됨). |
| `test_spec_008.py::test_confirmed_price_zero_is_valid_not_null` | `margin_amount="20000.00"`, `margin_rate="100.00"` | `margin_amount="19998.65"`, `margin_rate="99.99"` | `total_price=20000.00, rate=1300.00`, 확정 원가 `0`, `total_book_count=2` → `korea_warehouse_krw=1750` → `usd≈1.3462`. `margin=20000-0-1.3462=19998.6538→19998.65`. `rate=19998.6538/20000×100=99.9933→99.99`. |
| `test_spec_009.py::test_margin_uses_exchange_rate_for_usd_conversion` | `margin_amount="23.08"`, `margin_rate="23.08"` | `margin_amount="21.35"`, `margin_rate="21.35"` | `total_price=100.00, rate=1300.00`, 확정 원가 `100000/1300≈76.9231`, `total_book_count=3`(item A qty2 + item B qty1) → `korea_warehouse_usd≈1.7308`. `margin=100-76.9231-1.7308=21.3462→21.35`. |
| `test_spec_009.py::test_margin_fallback_to_prior_date_rate` | `margin_amount="26.56"`, `margin_rate="53.13"` | `margin_amount="25.59"`, `margin_rate="51.17"` | `total_price=50.00, rate=1280.00`(폴백), 확정 원가 `30000/1280=23.4375`, `total_book_count=1` → `korea_warehouse_krw=1250` → `usd=1250/1280=0.9765625`. `margin=50-23.4375-0.9765625=25.5859375→25.59`. `rate=25.5859375/50×100=51.171875→51.17`. |

**영향 없음(재검증만)**: `test_spec_008.py::test_margin_amount_is_null_when_all_confirmed_price_null`, `test_spec_009.py::test_margin_null_when_no_exchange_rate` — 둘 다 애초에 `None`을 기대하며, 이 SPEC의 None 게이트(REQ-COST-009/010)가 기존 게이트를 그대로 계승하므로 값 변경이 없다. `test_spec_008.py::test_line_item_contains_confirmed_price_when_set`, `test_line_item_confirmed_fields_null_when_unset`과 `test_spec_009.py`의 환율 CRUD 테스트(`:234-322`)는 마진과 무관해 영향 없음.

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 테스트 번호 | 검증 대상 REQ |
|---|---|---|---|
| AC-COST-001 `[BE]` | `test_spec_021.py` | T1 | 004, 005, 008, 011, 012, 013 |
| AC-COST-002 `[BE]` | `test_spec_021.py` | T2 | 004, 005, 008 |
| AC-COST-003 `[BE]` | `test_spec_021.py` | T3 | 002, 003, 008, 011, 012, 013 |
| AC-COST-004 `[BE]` | `test_spec_021.py` | T4 | 002 |
| AC-COST-005 `[BE]` | `test_spec_021.py` | T5 | 002, 004, 008 |
| AC-COST-006 `[BE]` | `test_spec_021.py` | T6 | 009 |
| AC-COST-007 `[BE]` | `test_spec_021.py` | T7 | 010 |
| AC-COST-008 `[BE]` | `test_spec_021.py` | T8 | 006 |
| AC-COST-009 `[BE]` | `test_spec_021.py` | T9 | 015 |
| AC-COST-010 `[BE]` | `test_spec_021.py` | T10 | 014 |
| AC-COST-011 `[FE]` | `OrderDetailPage.test.tsx` | T11 | 016, 017 |
| AC-COST-012 `[BE]` | `test_spec_021.py` | T12 | 007 |
| AC-COST-013 `[BE]` | `test_spec_021.py` | T13 | 003, 011 |
| AC-COST-014 `[BE]` | `test_spec_021.py` | T14 | 020, 022 |
| AC-COST-015 `[BE]` | `test_spec_021.py` | T15 | 021, 023 |
| AC-COST-016 `[BE]` | `test_spec_021.py` | T16 | 021, 024 |
| AC-COST-017 `[BE]` | `test_spec_021.py` | T17 | 025 |
| AC-COST-018 `[BE]` | `test_spec_021.py` | T18 | 026 |
| AC-COST-019 `[FE]` | `OrderDetailPage.test.tsx` | (신규 describe 블록, v1.3.0) | 023, 027, 028, 029 |
| AC-COST-020 `[BE]` | `test_spec_021.py` | T19 | 030, 031 |
| AC-COST-021 `[BE]` | `test_spec_021.py` | T20 | 030, 031, 034 |
| AC-COST-022 `[BE]` | `test_spec_021.py` | T21 | 033 |
| AC-COST-023 `[BE]` | `test_spec_021.py` | T22 | 032 |
| AC-COST-024 `[FE]` | `OrderDetailPage.test.tsx` | (신규 describe 블록, v1.4.0) | 035, 036 |

이 표는 각 AC 섹션 상단의 `Traces:` 목록과 완전히 일치한다(감사 D7 — 이전 버전은 AC-COST-001 행에 REQ-007을 잘못 나열했고 AC-COST-003 행에 REQ-012를 이중 나열하면서도 REQ-COST-011/012/013의 REQ→AC 역방향 표는 AC-COST-001/003을 빠뜨리는 등 네 곳이 서로 어긋나 있었다).

시나리오로 직접 검증하지 않는 요구사항: REQ-COST-001(상수 존재), REQ-COST-018(신규 필드 없음), REQ-COST-019(단일 헬퍼 구조) — 셋 다 `plan.md` 완료 조건의 코드 리뷰/`git diff` 게이트로 확인한다.

**추가 회귀 게이트**(신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `backend/order/tests/test_spec_008.py` 전량(3건 기대값 갱신 포함)
- `backend/order/tests/test_spec_009.py` 전량(2건 기대값 갱신 포함)
- `frontend/src/pages/OrderDetailPage.test.tsx` 전량
- `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx` 전량 — REQ-COST-017이 `OrderDetail`에 필수 필드 2개를 추가하면서 이 파일의 별도 `buildOrderDetail()`(`:47`)도 갱신 대상이 된다(감사 D2). `npm run build`(`tsc -b`)가 이 파일을 포함해 통과해야 한다.

## v1.3.0 확장 회귀 게이트

- AC-COST-009(쿼리 수 불변식)는 **무수정**으로 재실행해 통과해야 한다 — `confirmed_cost`/`total_cost` 게터 2개가 늘어나도 메모이제이션(설계 결정 C/F)으로 인해 `ORDER_DETAIL_QUERY_COUNT`, `orders_line_item`/`orders_exchangerate` 참조 쿼리 수(각 1) 모두 **변하지 않아야** 한다. 변경 시 상수를 실측값으로 갱신하고 그 사실을 `spec.md` HISTORY에 남긴다.
- `margin_usd`/`get_margin_amount`/`get_margin_rate`/두 None 게이트는 **한 글자도 변경되지 않는다** — `git diff`로 확인.
- `OrderListSerializer`는 무수정.

## v1.4.0 확장 회귀 게이트

- AC-COST-009(쿼리 수 불변식)는 **무수정**으로 재실행해 통과해야 한다 — `exchange_rate`/`exchange_rate_date` 게터 2개가 늘어나(9개 `SerializerMethodField`) `_get_exchange_rate`가 직접 호출되는 경로가 새로 생겼음에도, `_get_exchange_rate` 자체의 메모이제이션(REQ-COST-034)으로 인해 `ORDER_DETAIL_QUERY_COUNT`, `orders_line_item`/`orders_exchangerate` 참조 쿼리 수(각 1) 모두 **변하지 않아야** 한다. 실측 결과: 변경 전 `ORDER_DETAIL_QUERY_COUNT=7`(`orders_line_item`=1, `orders_exchangerate`=1) → 변경 후 동일(무수정 상수로 재통과, 21/21 테스트 통과 실측 확인).
- `margin_usd`/`get_margin_amount`/`get_margin_rate`/`_compute_cost_breakdown`(및 그 uncached 버전)의 계산 로직/두 None 게이트는 **한 글자도 변경되지 않는다** — `git diff`로 확인(`_get_exchange_rate`의 메모이제이션 래핑만 예외, 폴백 조회 로직 자체는 무변경).
- `OrderListSerializer`는 무수정.
- `backend/order/tests/test_spec_008.py`, `test_spec_009.py` 전량 무수정 재통과(마진 계산 영향 없음 확인, 17/17 테스트 통과 실측 확인).
- `tsc -b` 에러 수는 이 SPEC 이전부터 존재하던 베이스라인과 동일해야 하며(실측 베이스라인은 26건 — 과거 버전 문서가 기록한 24건과 2건 차이가 있고, 그 2건은 `frontend/src/hooks/usePurchaseOrderQueries.test.tsx`에 이 SPEC과 무관하게 이미 존재했다), `types/order.ts`/`OrderDetailPage.tsx`/`OrderDetailPage.test.tsx`/`SearchTab.test.tsx` 4개 파일에는 신규 에러가 0건이어야 한다.
