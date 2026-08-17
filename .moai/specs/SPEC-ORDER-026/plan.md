# SPEC-ORDER-026 — 구현 계획

## 1. 접근 개요

단일 함수 `_compute_cost_breakdown_for_rate`(`backend/order/serializers.py:31-73`)의 **내부 산술만** 바꾼다. 시그니처, 반환 dict의 키 집합, 호출 규약, 메모이제이션 계층, 7개 게터, null 게이트 2곳은 전부 무변경이다. 두 소비처(`serializers.py:279`, `:553`)가 이미 이 함수를 공유하므로 **한 곳을 고치면 두 화면이 동시에 정정된다**.

핵심 설계 판단 3가지:

**(A) 순액화는 Python에서, prefetch 캐시로부터.**
`obj.refunds.all()`이 유일한 데이터 소스다. `refunds`는 두 뷰 모두에서 이미 prefetch되어 있으므로(`views.py:59`, `views.py:269`) 추가 쿼리가 0이다. `purchase_order_views.py:334-342`의 `Subquery`/`OuterRef` 패턴은 **직렬화기 안으로 가져오지 않는다** — 주문당 쿼리를 발급해 `OrderListSerializer`(페이지 50행, `views.py:159-160`)에서 +50 쿼리가 되고, 원격 DB 130ms/쿼리에서 약 +6.5초가 된다.

**(B) 참 순액 산술 — boolean 필터가 아니다.**
같은 파일 `serializers.py:186-191`의 `trackable` 컴프리헨션은 순액을 **포함/제외 판정**으로만 쓴다(순액 > 0이면 원래 수량 전량 유지). 출고/발주 판정에는 그것이 정답이지만 비용 계산에는 틀렸다. 비용 경로는 수량 3 중 1건 환불 시 권수·무게·확정매입가가 **2/3로** 줄어야 한다.

**(C) 양쪽 순액화는 원자적이다.**
수량만 고치면 #37454의 마진이 37.22 → 60.80으로 **더 틀려진다**(진실 23.52로부터의 거리가 13.70 → 37.28). 따라서 두 변경은 같은 커밋에 들어간다. 마일스톤을 M-수량 / M-매출로 쪼개는 것은 금지된다.

### 1.1 목표 산술 (의사코드 — 구현 지침)

```
# 1) 환불 수량 맵 — serializers.py:179-184 과 동일한 구성
refunded_qty = {}
refunded_amount = Decimal("0")
for refund in obj.refunds.all():                  # prefetch 캐시
    if refund.line_item_id is not None:
                # [HARD] 누적(+=)이어야 한다 — 대입이 아니다. 같은 line_item_id에
        # Refund 행이 여러 개 존재할 수 있다(models.py:342 unique_together).
        # 대입으로 쓰면 분할 환불을 과소 계산해 마진을 다시 과대 계상한다
        # (변이 M10, AC-NET-015가 단독 판별, 감사 D2).
        refunded_qty[refund.line_item_id] = refunded_qty.get(refund.line_item_id, 0) \
                                            + (refund.quantity or 0)
    # 매출 항은 line_item_id 매칭 여부와 무관하게 전체 합산 (REQ-NET-011)
    refunded_amount += (refund.subtotal or Decimal("0")) + (refund.total_tax or Decimal("0"))

# 2) 라인아이템 순회 — 순수량으로 집계 (REQ-NET-001/003/020)
for item in obj.line_items.all():
    quantity = max((item.quantity or 0) - refunded_qty.get(item.shopify_line_item_id, 0), 0)
    grams = item.grams or 0
    total_weight_grams += grams * quantity
    total_book_count += quantity
    if item.confirmed_price is not None:          # 게이트는 순액화 '전' (REQ-NET-024)
        has_any_confirmed = True
        confirmed_cost_krw += item.confirmed_price * quantity

# 3) 매출 항 순액화 + 하한 (REQ-NET-010/021)
total_price_usd = max(Decimal(str(obj.total_price or "0")) - refunded_amount, Decimal("0"))
```

이후 `serializers.py:49-73`(환산·비용 3항·마진·반환 dict)은 **한 글자도 바꾸지 않는다** — 권수 0 분기(`:54-59`)와 매출 0 게이트(`:570-571`, `:283-284`)가 그대로 REQ-NET-005/022/023을 만족한다.

> 루프는 라인아이템을 **1회만** 순회한다(현재와 동일). 환불 루프 1회가 추가되며 `len(obj.refunds.all())`은 프로덕션 전체에서 311행(`research.md` §8)이라 무의미한 비용이다.

---

## 2. 마일스톤 (우선순위 순. 시간 예측 없음)

### M1 (Priority High) — RED: 신규 테스트 스위트 작성

`backend/order/tests/test_spec_026.py` `[NEW]` 신규 작성. AC-NET-001 ~ AC-NET-016에 대응하는 **17개 AC / 21개 테스트**(006a/006b 분리 + 003/004/006a/006b의 parametrize 분리).

지침:
- 헬퍼 픽스처는 `test_spec_021.py`의 관례를 따른다: `auth_client`(`:62-66`), `_make_order(total_price, shopify_order_id, **kwargs)`(`:69-77`), `_make_line_item(order, shopify_line_item_id, quantity, confirmed_price, grams)`(`:80-88`), `rate_1000`(`:92-96`), `DETAIL_URL`(`:23`)/`LIST_URL`(`:24`).
- `_make_line_item`은 `purchase_status`를 받지 않으므로 AC-NET-013용으로 인자를 확장한 자체 헬퍼가 필요하다. `quantity=None`(AC-NET-006a(b))은 원본이 그대로 받는다(`quantity=None` 기본값, `test_spec_021.py:80`).
- **[HARD] `_make_order`도 확장이 필요하다** (감사 N9): `test_spec_021.py:74`가 `total_price=Decimal(total_price)`를 **무조건** 호출하므로 `total_price=None`을 넘기면 `TypeError: conversion from NoneType to Decimal is not supported`로 죽는다(이 세션에서 직접 실행해 확인). **AC-NET-006b(b)는 `Order.total_price = None`을 요구하므로 원본 헬퍼로는 구현 불가능하다.** 자체 헬퍼에서 `total_price=Decimal(total_price) if total_price is not None else None` 형태로 감싼다. `Order.total_price`가 nullable임은 모델에서 확인된 사실이다.
- 환불 헬퍼는 `test_spec_023.py:866-872`의 `_refund` 형태를 유지하되 `subtotal`/`total_tax`/`line_item_id` 인자를 추가한다 (`acceptance.md` §0.1-2의 시그니처 사용). 원본 헬퍼는 `subtotal`/`total_tax`를 설정하지 않아 매출 측 순액화를 전혀 검증하지 못한다.

> **헬퍼 확장 요약**: `test_spec_021.py`/`test_spec_023.py`의 헬퍼 3개 전부 그대로 쓸 수 없다 — `_make_order`(`total_price=None` 불가), `_make_line_item`(`purchase_status` 인자 없음), `_refund`(`subtotal`/`total_tax` 미설정). 신규 스위트는 세 헬퍼의 확장판을 자체 정의한다.
- [HARD] `shopify_line_item_id`는 `17_000_000_000_000` 이상을 쓴다 — 작은 값은 자동증가 `pk`와 우연히 일치해 M8(잘못된 조인 키) 변이를 통과시킨다 (`acceptance.md` §0.1-1).
- 쿼리 캡처(AC-NET-009/010)는 `django.test.utils.CaptureQueriesContext` + **워밍업 요청** 관례를 따른다(`test_spec_021.py:268-313`, `test_spec_023.py:638-681`). `orders_refund` 매칭은 단순 `in` 검사로 안전하다(접두사 충돌 없음, `research.md` §4.1). **절대 상수는 SPEC이 결정한 `8`을 쓴다** — `test_spec_021.py:48`에서 임포트하거나 동일 값을 자체 상수로 선언한다. 실측이 8이 아니면 상수를 갱신하지 말고 멈추고 보고한다(REQ-NET-031, 감사 D11).
- [HARD] AC-NET-015는 **같은** `shopify_line_item_id`에 환불 2행을 붙이고 `shopify_refund_id`는 **서로 다르게** 한다(`models.py:342`의 `unique_together`). 두 행이 실수로 다른 라인을 가리키면 M10(합산→덮어쓰기)이 즉시 미커버가 된다 — 이것이 감사 D2로 잡힌 결함의 정확한 형태다.
- AC-NET-016은 `unittest.mock.patch("order.serializers._compute_cost_breakdown_for_rate", wraps=order.serializers._compute_cost_breakdown_for_rate)`로 모듈 레벨 함수를 스파이한다. **[HARD] (a)는 스파이 밖에서 보낸 baseline 요청과의 바이트 동일성으로 구현하고, AC-NET-001의 하드코딩된 순액화 값을 참조하지 않는다**(감사 N1) — 그래야 이 AC가 순액화 여부에 무관한 불변식 보존 AC가 되어 무수정 코드에서도 통과한다. `wraps`가 빠지면 맨 `MagicMock`이 반환되는데 그것은 `is None`/`__getitem__`/`.quantize()`/`== Decimal("0")`을 전부 지원하므로(실측 확인) non-None 단정으로는 검출되지 않는다 — baseline과의 값 비교가 유일한 검출 수단이다.
- [HARD] AC-NET-002와 AC-NET-015를 작성한 직후 각각 무수정 코드에서 실행해 **실패를 직접 확인**한다. 통과한다면 픽스처가 판별력을 잃은 것이다.

**완료 조건 (감사 D3으로 정정)**: **17개 AC / 21개 테스트 중 12개 AC가 무수정 코드에서 실패한다** — AC-NET-001, 002, 003, 004, 005, 006a, 006b, 007, 008, 011, 012, 015.

**[HARD] 나머지 5개 AC는 무수정 코드에서 통과하는 것이 정상이며, 이것을 실패로 취급하지 않는다**:

| AC | 왜 오늘도 통과하는가 |
|----|---------------------|
| **AC-NET-009** (상세 쿼리 수) | 불변식 **보존** AC. 현재 코드가 이미 총 8, `orders_refund` 1, `orders_exchangerate` 1을 만족한다 |
| **AC-NET-010** (목록 쿼리 수) | 동일. 현재 코드가 이미 1건/5건 페이지 모두 8을 만족한다 |
| **AC-NET-013** (`order_cancelled` 비목표 고정) | 현재 코드는 `purchase_status`를 보지 않으므로 이미 기대값을 낸다 |
| **AC-NET-014** (하위 호환) | 환불 없는 주문은 gross == net이므로 이미 통과한다 |
| **AC-NET-016** (메모이제이션 계약) | 불변식 **보존** AC. (b) `call_count == 1`은 `serializers.py:513-540`의 캐시가 이미 보장하고, (a)는 **스파이 밖 baseline과의 바이트 동일성**이므로 순액화 여부에 무관하다 — 양쪽 단정이 무수정 코드에서 성립한다. **(a)를 AC-NET-001의 순액화된 기대값으로 쓰면 이 분류가 거짓이 된다**(감사 N1) |

> **[HARD] 이 구분을 지키지 않으면 생기는 피해**: 최초 버전은 "13개가 실패한다"고 적었다. 문자대로 따르면 구현자는 정상 통과 중인 AC-NET-009/010을 "픽스처가 잘못됐다"고 판단해 판별력을 훼손하는 방향으로 고치게 된다. 그 두 AC는 R3(주문당 +50 쿼리, 원격 DB 130ms/쿼리 → 약 +6.5초)에 대한 **유일한 방어선**이다. 불변식 보존 AC가 오늘 통과하는 것은 결함이 아니라 설계다 — 그것이 "변경 후에도 여전히 통과"를 의미 있게 만든다.

추가 완료 조건:
- AC-NET-015(합산 축)와 AC-NET-002(비례 축)는 작성 직후 **개별적으로** 무수정 코드에서 실행해 실패를 눈으로 확인한다. 두 AC는 각각 M10·M4의 **단독** 판별자이므로 여기서 통과하면 픽스처가 판별력을 잃은 것이다.
- AC-NET-016은 스파이가 응답을 바꾸지 않음을 (a) 단정으로 함께 확인한다 — baseline 요청과의 바이트 동일성이며, `wraps` 누락 시 `MagicMock` 문자열 repr이 baseline과 달라 즉시 드러난다.

### M2 (Priority High) — GREEN: `_compute_cost_breakdown_for_rate` 순액화

`backend/order/serializers.py:31-73` `[MODIFY]`. §1.1의 산술을 적용한다. **수량 측과 매출 측을 같은 편집에서** 넣는다(REQ-NET-013).

금지 사항:
- `serializers.py:49-73`(환산 이후 전 구간) 수정 금지
- 함수 시그니처·반환 dict 키 변경 금지
- `serializers.py:186-191`의 boolean 필터 복사 금지
- ORM 쿼리(`Refund.objects...`, `obj.refunds.filter(...)`, `.exists()`, `.count()`, `annotate`) 사용 금지 — `obj.refunds.all()`만 허용
- 새 헬퍼 함수를 만들어 `_derive_line_item_states`와 `refunded_qty` 구성을 "공유"하려는 리팩터링 금지 — 두 경로는 순액을 **다른 목적**(boolean 필터 vs 산술)으로 쓰며, 공유 추상화는 M4 변이를 구조적으로 초대한다. 중복 8행이 잘못된 추상화보다 싸다

완료 조건: AC-NET-001 ~ AC-NET-016 전부 통과 (17개 AC / 21개 테스트).

### M3 (Priority High) — 회귀 확인

- `backend/order/tests/test_spec_021.py` 21개 **무수정** 통과. 고정값 편집 0건 — `git diff test_spec_021.py`가 공집합이어야 한다
- `backend/order/tests/test_spec_023.py` 전량(1027행) **무수정** 통과. 특히 `:848`(필드셋 **45개**), `:638-681`(쿼리 8), `:875-1027`(환불 순액 **표시** 판정 6건)
- `backend/order/tests/` 전체 스위트
- `git diff --stat frontend/` 공집합
- `backend/order/migrations/` 신규 파일 0건

> **[HARD] 실행 규약**: 원격 공유 DB이므로 테스트를 **동시에 실행하지 않는다**(가짜 실패 발생). 서브셋 실행에는 `--no-cov`를 반드시 붙인다(누락 시 전부 통과해도 종료코드 1).

### M4 (Priority Medium) — @MX 태그 갱신 및 강등 보고

§mx_plan 실행. ANCHOR 한도 충돌 처리와 보고를 포함한다.

### M5 (Priority Low) — 프로덕션 확인 (배포 후, 선택)

주문 `#37454`(`Order.pk = 3513`)의 상세 화면에서 `최종 결제 금액 78.76 − 비용 합계 55.24 = 마진 23.52`가 화면상 성립하는지 눈으로 확인한다. 이는 `research.md` §5.3이 기록한 자기모순의 해소 확인이며, 자동 테스트로 대체 가능한 항목이 아니다(프론트엔드 로컬 계산과 백엔드 계산의 실제 화해).

---

## 3. 영향 파일 ([DELTA] 마커)

| 마커 | 파일 | 변경 내용 |
|------|------|-----------|
| **[MODIFY]** | `backend/order/serializers.py` | `_compute_cost_breakdown_for_rate`(`:31-73`) 본문 — 환불 수량 맵 구성 + 순수량 집계 + 매출 항 순액화·하한. 함수 위 `@MX` 주석 블록(`:20-30`) 확장 |
| **[NEW]** | `backend/order/tests/test_spec_026.py` | AC-NET-001~016 대응 **21개 테스트**(17개 AC) + 헬퍼. `unittest.mock`(AC-NET-016 스파이) 임포트 필요 |
| **[EXISTING]** | `frontend/src/pages/OrderDetailPage.tsx` | **무변경** (REQ-NET-044). `:159-163`의 `netPaidAmount` 로컬 계산 유지 — 백엔드가 동일 공식을 채택하므로 두 값이 구조적으로 일치한다 |
| **[EXISTING]** | `backend/order/views.py` | **무변경**. `refunds` prefetch가 `:59`/`:269`에 이미 있다 |
| **[EXISTING]** | `backend/order/models.py` | **무변경**. 저장 컬럼·마이그레이션 없음 |
| **[EXISTING]** | `backend/order/purchase_order_views.py` | **무변경**. `:334-342`/`:366-370`은 참조 근거일 뿐이며 옮겨오지 않는다 |
| **[EXISTING]** | `backend/order/tests/test_spec_021.py` | **무변경** (편집 0건이 DoD) |
| **[EXISTING]** | `backend/order/tests/test_spec_023.py` | **무변경** |

변경 파일은 **2개**다(1 MODIFY + 1 NEW). CLAUDE.md Rule 2(3파일 이상 분해)의 임계 미달이므로 단일 논리 단위로 진행한다.

---

## 4. 위험과 대응

| ID | 위험 | 대응 |
|----|------|------|
| R1 | 구현자가 `serializers.py:186-191`의 boolean 필터를 복사해 부분 환불에서 gross 값이 남는다 (**M4 변이**) | AC-NET-002가 유일한 방어선. `total_weight_grams == 1000`이 단일 판별자. §2 M2의 "금지 사항"에 명시. #37454만으로는 절대 잡히지 않음을 `spec.md` REQ-NET-003 인라인 경고로 고정 |
| R2 | 조인 키를 `LineItem.pk`로 잘못 사용 (`Refund.line_item_id`는 `shopify_line_item_id`와 조인) | `acceptance.md` §0.1-1의 `shopify_line_item_id >= 17_000_000_000_000` 픽스처 규약. 이 규약을 지키지 않으면 M8 변이가 조용히 통과한다 |
| R3 | `purchase_order_views.py:334-342`의 ORM 패턴을 직렬화기로 옮겨 주문당 쿼리가 발생. 목록 페이지에서 +50 쿼리 | AC-NET-009/010을 **MUST-PASS**로 지정. `orders_refund` 참조 쿼리 정확히 1개 단정. §2 M2 금지 사항에 명시 |
| R4 | 수량만 순액화한 부분 배포 → 마진 오차가 13.70에서 37.28로 **확대** | REQ-NET-013 [HARD]. AC-NET-001의 변이 표가 M2의 결과값(`"60.80"`)을 수치로 고정. 마일스톤 분할 금지를 §2에 명시 |
| R5 | 과다 환불에서 음수 무게·비용이 흘러 한국물류비가 오히려 부과된다(권수 −1은 `== 0` 분기를 통과하지 못한다) | REQ-NET-020 + AC-NET-006a. `total_weight_grams` 음수 여부가 단일 판별자 |
| R6 | 매출 하한 누락 → 음수/음수로 마진율 +100%가 표시된다 | REQ-NET-021 + AC-NET-006b |
| R7 | `has_any_confirmed`를 순액화 후로 옮겨 7필드가 `null`로 뒤집힌다 | REQ-NET-024가 사전 평가를 [HARD]로 고정. AC-NET-005가 7필드 non-null을 단정 |
| R8 | `Refund.quantity`/`subtotal`/`total_tax` NULL로 `TypeError` → 500 | REQ-NET-002/012 + AC-NET-007(`status_code == 200` 단정 포함) |
| R9 | 순액화 도중 항목별 양자화로 `total_cost`가 13.98 대신 13.99가 된다 | REQ-NET-025 + AC-NET-012(T15와 동일한 이중 단정) |
| R10 | 공유 함수가 아닌 한쪽 소비처에만 순액화를 넣어 목록/상세가 갈라진다 | AC-NET-011(동일성 + 절대값 `"29.86"` 동시 단정). 동일성만으로는 양쪽 gross도 통과하므로 절대값이 필수 |
| R11 | 다른 세션이 같은 저장소를 동시에 수정 중일 수 있다 | 커밋 전 세션 시작 시점의 `git status`와 대조해 이 SPEC의 hunk만 선별 스테이징한다 |
| R12 | `_derive_line_item_states`와 순액화 코드를 "중복 제거"하려는 리팩터링 유혹 | §2 M2 금지 사항. 두 경로는 순액을 다른 의미로 쓴다(`spec.md` Exclusions 7). 공유 추상화는 R1을 구조적으로 초대한다 |
| **R13** `[감사 D2]` | 환불 수량 맵을 `+=` 누적이 아니라 **대입**으로 구현해(`refunded_qty[id] = (refund.quantity or 0)`) 같은 라인의 분할 환불을 과소 계산 → 순액 과대 → 마진 재과대 계상. 프로덕션의 분할 환불이 정확히 이 형태이며(`models.py:342`가 허용), 최초 SPEC의 AC 15개가 **전부 통과시켰다** | AC-NET-015가 단독 판별. `plan.md` §1.1 의사코드가 `+=`를 명시. 픽스처 규약(같은 `line_item_id`, 다른 `shopify_refund_id`)을 §2 M1에 [HARD]로 기재 |
| **R14** `[감사 D1]` | 메모이제이션 우회를 쿼리 수로 잡을 수 있다고 오신 → REQ-NET-033이 실질 미커버. 순액화는 prefetch 캐시를 읽고 `_get_exchange_rate`는 `serializers.py:466-498`에서 독립 메모이즈되어 있어 우회해도 쿼리 수가 **전혀 변하지 않는다** | AC-NET-016(함수 호출 횟수 스파이)이 단독 판별. AC-NET-009의 Traces에서 REQ-NET-033을 제거하고 거짓 판별력 주장을 삭제 |
| **R15** `[감사 D3]` | 구현자가 무수정 코드에서 통과하는 불변식 보존 AC 5개(009/010/013/014/016)를 "고장난 테스트"로 판단해 픽스처를 고침 → R3의 유일한 방어선 소실 | §2 M1 완료 조건 표가 5개를 "통과가 정상"으로 명시. 각 AC 본문 상단에도 [HARD] 경고를 삽입. `acceptance.md` DoD가 RED 대상 12개를 열거 |
| **R16** `[감사 N1]` | AC-NET-016의 (a)를 AC-NET-001의 하드코딩된 순액화 값으로 작성 → 무수정 코드에서 실패 → R15의 [HARD] 분류와 충돌 → 가장 값싼 해소가 (a) 삭제 → **`wraps` 누락 검출력 소실 → M11 단독 판별자 무력화**. 맨 `MagicMock`은 `is None`/`__getitem__`/`.quantize()`/`== Decimal("0")`을 전부 지원하므로 약한 단정으로 대체할 수도 없다 | (a)를 스파이 밖 baseline 요청과의 **바이트 동일성**으로 규정([HARD], §2 M1 + `acceptance.md` AC-NET-016 + DoD 3곳). 이 형태는 순액화 여부에 무관하므로 분류가 참이 되고 검출력도 강화된다 |
| **R17** `[감사 N9]` | `test_spec_021.py:74`의 `_make_order`가 `Decimal(total_price)`를 무조건 호출하므로 AC-NET-006b(b)의 `total_price=None` 픽스처가 `TypeError`로 죽음 → 그 AC가 구현 불가로 판단되어 조용히 누락 | §2 M1에 헬퍼 3개(`_make_order`/`_make_line_item`/`_refund`) 전부 확장 필요를 [HARD]로 명시 + `None` 우회 형태 제시 |

---

## 5. mx_plan

### 5.1 대상

`backend/order/serializers.py:31` `_compute_cost_breakdown_for_rate`.

근거:
- **불변식 계약(invariant contract)**: 7개 비용 필드 전부(`margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams`, `confirmed_cost`, `total_cost`)의 유일한 계산 지점이며, 원가(cost-of-goods) 산정의 단일 진실 소재다.
- **fan_in = 2** (실측: `serializers.py:279`, `:553`). `mx.yaml:182`의 `thresholds.fan_in_anchor: 3` **미달**이다 — 따라서 ANCHOR 근거는 fan_in이 아니라 불변식 계약이다. 이 점을 정직하게 기록한다(자동 임계 충족을 사후 정당화하지 않는다).

### 5.2 [HARD] ANCHOR 한도 충돌과 강등 결정

`serializers.py`의 기존 `@MX:ANCHOR`는 **3개**이며(`:93`, `:346`, `:387` — 실측), `mx.yaml:175`의 `limits.anchor_per_file: 3`에 **이미 도달**해 있다. @MX 프로토콜의 "When limits exceeded: ANCHOR: Demote excess by lowest fan_in" 규칙에 따라:

**결정**: `serializers.py:346`(`LineItemDetailSerializer` 필드 블록)의 ANCHOR를 `@MX:NOTE`로 **강등**하고, 그 자리를 신규 ANCHOR에 넘긴다.

강등 대상 선정 근거 — 세 ANCHOR의 fan_in 근거 비교:

| 라인 | 대상 | `@MX:REASON`의 fan_in 근거 |
|------|------|---------------------------|
| `:93` | "발주 대기" predicate | SPEC-ORDER-023 REQ-OLIST-013/014a — 목록·상세·SQL 필터 3경로가 일치해야 하는 계약 |
| **`:346`** | `LineItemDetailSerializer` 필드 블록 | **"Extended by SPEC-ORDER-008 and SPEC-ORDER-010" — fan_in 주장 없음. 셋 중 유일** |
| `:387` | `OrderDetailSerializer` | "Fan-in >= 3" 명시 |

`:346`은 확장 이력을 기록한 것으로 실질은 NOTE의 성격이다. 강등 후에도 `@MX:REASON` 내용은 그대로 보존한다(정보 손실 없음).

**보고 의무** (@MX 프로토콜: "ANCHOR: NEVER auto-delete; demote to NOTE via report"): M4 완료 시 다음을 보고한다 — 강등 대상(`serializers.py:346`), 사유(anchor_per_file=3 한도 + 셋 중 유일하게 fan_in 근거 없음), 신규 ANCHOR 대상(`serializers.py:31`), 파일 내 ANCHOR 총수(강등 전 3 → 신규 추가 후 3, 한도 준수).

> 대안(강등하지 않고 `serializers.py:31`에 `@MX:NOTE`만 추가)도 프로토콜 위반은 아니다. 하지만 이 함수는 이 SPEC이 정정하는 결함의 발원지이자 원가 산정의 단일 진실 소재이므로, 파일 내 4개 ANCHOR 후보 중 **가장 강한 불변식**을 가진다. 구현 시 강등이 불가하다고 판단되면(예: 다른 세션이 `:346`을 동시 편집 중) `@MX:NOTE`로 대체하고 그 사실과 사유를 보고에 남긴다.

### 5.3 태그 내용 (`code_comments: en`)

`backend/order/serializers.py:31` 위, 기존 `@MX:NOTE` 블록(`:20-30`) 다음에 삽입:

```python
# @MX:ANCHOR: [AUTO] SPEC-ORDER-026 REQ-NET-001/010/013: single source of
# truth for all 7 cost fields (margin_amount, margin_rate, shipping_cost,
# korea_warehouse_cost, total_weight_grams, confirmed_cost, total_cost) on
# BOTH the order detail panel and the order list 마진율 column. fan_in=2
# (serializers.py:279 list, :553 detail) — below mx.yaml fan_in_anchor=3, so
# this ANCHOR is justified by invariant contract, not caller count.
# @MX:REASON: Refund netting is REQUIRED on BOTH sides and they are
# inseparable. (1) Quantity side: every per-line-item aggregate must use
# max((item.quantity or 0) - refunded_qty[item.shopify_line_item_id], 0) —
# true net ARITHMETIC, proportional. Do NOT copy the boolean include/exclude
# filter at :186-191: that one keeps a partially refunded item at FULL
# quantity, which is correct for shipping/purchase derivation and WRONG here.
# (2) Revenue side: total_price minus the sum of (subtotal + total_tax) over
# EVERY refund row, matched or not, floored at 0 — the same formula the
# frontend already uses for 최종 결제 금액 (OrderDetailPage.tsx:159-163).
# Netting only one side is worse than netting neither: for order #37454,
# quantity-only netting moves margin 37.22 -> 60.80, further from the truth
# (23.52) than the original defect. Netting must stay in this shared function
# — moving it into either caller silently desynchronizes the list column from
# the detail panel (AC-NET-011). No ORM query here: read obj.refunds.all()
# from the prefetch cache (views.py:59, :269); the Subquery/OuterRef pattern
# at purchase_order_views.py:334-342 would cost one query per serialized
# order, i.e. up to 50 per list page (AC-NET-009/010).
```

### 5.4 기타 태그 작업

- `serializers.py:20-30`의 기존 `@MX:NOTE`(SPEC-ORDER-023 추출 근거)는 **유지**한다 — 여전히 유효한 맥락이다.
- `serializers.py:524-530`의 메모이제이션 `@MX:NOTE`는 **유지**한다 — REQ-NET-033이 그 계약을 그대로 요구한다.
- `serializers.py:165-178`의 순액화 주석은 **유지**하되, "이 boolean 필터를 비용 경로에 복사하면 안 된다"는 역방향 참조 1행을 추가하는 것을 권장한다(선택). 두 경로가 순액을 다른 의미로 쓴다는 사실이 그 자리에서도 읽혀야 미래의 잘못된 통합을 막는다.
- `@MX:TODO` 신설 없음 — 이 SPEC은 미완성 작업을 남기지 않는다.
- `@MX:WARN` 신설 없음 — 순액화는 복잡도를 유의하게 늘리지 않는다(순회 1회 추가, 분기 증가 없음).

파일 내 태그 수 변화: ANCHOR 3 → 3 (한도 준수), NOTE +1 (강등분) 또는 +2 (5.4의 선택 항목 포함) — `mx.yaml:177`의 `note_per_file: 10` 이내인지 구현 시 확인한다.

---

## 6. 검증 명령 (참고)

```bash
# 신규 스위트만 (서브셋 → --no-cov 필수)
pytest backend/order/tests/test_spec_026.py --no-cov -v

# 회귀 (무수정 통과 확인) — 동시 실행 금지, 순차로
pytest backend/order/tests/test_spec_021.py --no-cov -v
pytest backend/order/tests/test_spec_023.py --no-cov -v

# 전체 (커버리지 포함)
pytest backend/order/tests/

# 범위 규율 확인
git diff --stat frontend/                        # 공집합이어야 한다
git diff --stat backend/order/tests/test_spec_021.py  # 공집합이어야 한다
git status backend/order/migrations/             # 신규 파일 0건
```

---

## 7. 완료 후 기록

`spec.md` HISTORY에 다음을 추가한다:
- 실측 쿼리 수(상세/목록, `orders_refund` 참조 수). **`8`이 아니면 REQ-NET-031 위반이므로 정정 내역이 아니라 차단 사유로 기록한다**
- 통과 테스트 수(신규 21개 + `test_spec_021.py` 21개 무수정 + `test_spec_023.py` 전량)
- mx_plan 실행 결과(ANCHOR 강등 여부와 사유)
- **AC-NET-002(M4 단독 판별자)와 AC-NET-015(M10 단독 판별자)가 각각 무수정 코드에서 실패했음을 확인한 사실**(RED 성립), 그리고 AC-NET-009/010/013/014/016이 무수정 코드에서 통과했음(정상)
- 프로덕션 96건이 백필 없이 정정되었음(다음 조회 시 자동). **구현 시점에 재실측한 실제 건수를 병기한다** — 96건은 2026-08-17 스냅샷(UNVERIFIED)이다
