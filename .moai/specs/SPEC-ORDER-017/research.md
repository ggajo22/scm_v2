---
id: SPEC-ORDER-017
document: research
version: 1.0.4
status: completed
updated: 2026-08-13
---

# 조사 근거 — SPEC-ORDER-017 렉번호 엑셀 업로드 배치 처리

이 문서는 `spec.md` / `plan.md` / `acceptance.md`가 인용하는 모든 `file:line` 근거를 모은다.
모든 인용은 이 세션에서 Read/Grep으로 직접 재확인했다 — 이전 SPEC 문서(SPEC-ORDER-016)에서
plan.md의 옛 인용(`:2810-3101` 등)이 이후 구현으로 파일이 이동해 더 이상 유효하지 않은 사례가
확인되었으므로, 이 SPEC은 그 문서의 인용을 재사용하지 않고 전량 새로 검증했다.

**v1.0.1**: plan-auditor 리뷰(iteration 1, FAIL, 0.69) 후속 — D8(§1 step 3에 누락되어 있던
기존 `@MX:WARN`/`@MX:REASON` 반영)과 D10의 4개 인용 포인터 정밀화(§1, §2.1, §4, §9)를
적용했다. 독립 검증(plan-auditor)이 60여 개 인용 전량을 재확인해 허구 인용이 없음을
확인했으므로, 이 버전에서 기존 인용의 사실관계는 재검증하지 않고 지적된 항목만 정정한다.

**v1.0.2**: plan-auditor 리뷰(iteration 2, FAIL, 0.75) 후속, iteration 3/3 최종. 사용자 결정
(`_process_rack_number_rows` 모듈 레벨 순수 함수 추출)의 근거 자료를 §2.2(신설)에 추가했다
— `JWTAuthentication`의 사용자 조회 쿼리와 `auth_client`의 실제 JWT 발급을 확인해, 엔드포인트
레벨 측정이 왜 부정확했는지(D2)를 뒷받침한다. §2에 두 번째 아키텍처 선례
`_process_force_outbound_rows`를 추가했다. §5의 v1.0.1 절을 갱신해 함수 추출 이후의 측정
스코프 변경을 반영했다(D2). §10을 함수 추출 구조와 무조건 `transaction.atomic()` 진입
원칙(v1.0.1의 "즉시 반환" 서술과의 모순 해소)에 맞게 재작성했다.

**v1.0.3**: plan-auditor 리뷰(iteration 3/3, **PASS**, 0.88) 후속 — 문서 정리, 블로킹 결함
없음. §11(신설)에 D17(Django `bulk_update`의 실제 SQL 형태)의 근거를 추가했다. §5에 D21
정정(동명 Order tie-break 참조 테스트가 `pk` 뒤집기를 실증하지 않음)을 반영했다.

## 1. 현재 구현 — `UploadRackNumberView`

`backend/order/purchase_order_views.py:2163`에 정의된 `UploadRackNumberView`(문서화 주석
`:2164-2175`)의 `post()`(`:2180-2266`)는 다음 순서로 동작한다.

1. `.xlsx` 확장자 검증(`:2185-2190`, 아니면 400) → `parse_rack_number_excel` 호출
   (`:2193-2194`, `backend/order/excel_utils.py:994`) → `ValueError` 시 422(`:2195-2196`).
2. `dedup_map: dict[tuple, dict] = {}`를 `(order_name, sku)` 키로 구축한다(`:2205-2212`,
   `dedup_map` 선언부터 `dedup_map[key] = row` 대입까지). 그 위 `:2198-2204`는 이 로직의
   의도를 설명하는 주석이다 — 주문 식별자 셀이 빈 행은 `order_name=None`이 되며, 그런 행은
   `(None, idx)`로 키를 만들어 서로 병합되지 않고 각자 `skipped_count`에 반영되도록 한다.
3. `transaction.atomic()`(`:2217`) 내부, `for row in dedup_map.values():`(`:2227`) 루프
   바로 위에 기존 `@MX:WARN`/`@MX:REASON`(`:2218-2226`)이 있다 — "하나의 `(order_name,
   sku)` 키가 LineItem 2건 이상과 매칭될 수 있으며(SPEC-SHOPIFY-SKU-SET-002
   `unique_together`가 주문당 동일 SKU 중복을 허용하므로), 이 경우 매칭되는 LineItem
   **전부**가 같은 `rack_number`를 받는다(결정 E)"고 명시한다. REASON은 "행 하나가 정확히
   어느 LineItem을 가리키는지 판별할 방법이 없어 '같은 물리 도서, 같은 렉'으로 취급하는
   설계이지 버그가 아니다"라고 근거를 남긴다. 이 태그는 배치 재작성으로 사라지는 바로 그
   루프 안에 있으므로, 재작성 시 묵시적으로 삭제될 위험이 있다 — REQ-RACKBATCH-006이 이
   태그가 경고하는 조건을 그대로 보존하므로 삭제해서는 안 되며, `plan.md` mx_plan이 이관
   계획을 명시한다(plan-auditor D8).
4. `dedup_map.values()`를 순회하며 키마다 **쿼리 3개**를 실행한다:
   - `Order.objects.filter(name=order_name).first()` (`:2243`)
   - `LineItem.objects.filter(order=order, sku=sku)` + `.exists()` (`:2249-2250`)
   - `line_items.update(rack_number=row["rack_number"])` (`:2255`)
5. 예외 발생 시 500(`:2257-2261`, `try` 블록 전체는 `:2216`에서 시작한다). 정상 종료 시
   `{"matched_count", "skipped_count"}`를 200으로 반환(`:2263-2266`).

원격 MySQL 인스턴스는 쿼리 왕복당 약 130ms가 걸리므로(이 코드베이스에 이미 문서화된 비용
모델, 아래 §3 참조), 응답 시간은 dedup 키 개수에 선형 비례한다. `UploadRackNumberView`에는
쿼리 카운트 회귀 테스트가 **전혀 없다**(`backend/order/tests/test_spec_013.py` 전체를 확인).

## 2. 참조 구현 — `_process_outbound_rows`

같은 파일의 `_process_outbound_rows`(`backend/order/purchase_order_views.py:2423-2714`)가
SPEC-ORDER-015의 출고 처리에서 동일한 문제를 이미 해결했다. 구조:

- 순수 파이썬 그룹핑 1패스(DB 접근 없음), `transaction.atomic()`은 배치 전체에 1회
  (`:2518`).
- **배치 Order 조회** (`:2532-2538`): `Order.objects.filter(name__in={...}).order_by("pk")`
  후 `orders_by_name.setdefault(candidate.name, candidate)`. `order_by("pk")` + `setdefault`
  조합은 `.filter(name=X).first()`가 정렬 없는 쿼리셋에서 Django의 암묵적 `ORDER BY pk`
  폴백으로 얻던 "최저 pk 선점" tie-break를 재현하기 위한 것이다(주석 `:2524-2531`) —
  `Order.name`은 유일 제약이 없다.
- **배치 LineItem 조회** (`:2549-2558`): `LineItem.objects.filter(order_id__in=[...],
  sku__in={...}).order_by("pk")`를 `line_items_by_key: dict[tuple[int, str], list[LineItem]]`
  로 수집. 두 `__in` 필터는 독립적이라 교차곱을 과다 조회하지만, 이후 루프가 `grouped`에서
  만든 키만 조회하므로 무해하다(주석 `:2540-2547`).
- 순수 파이썬 판정 루프가 변경 대상 객체를 `to_update: list[LineItem]`에 누적.
- **단일 flush** (`:2701-2704`): `LineItem.objects.bulk_update(to_update, [...])`.

결과: 배치 크기와 무관하게 Order 조회 1회 + LineItem 조회 1회 + `bulk_update` 1회.

이 최적화의 의도와 비용 모델은 `@MX:NOTE`(`:2403-2414`)에 명시되어 있다: "원래 구현은 그룹당
3쿼리를 실행해 8행 업로드가 약 24왕복(~3초), 50행이 약 150왕복(~19초)이었다"고 기록하고,
"새로 추가되는 조회도 전부 배치하라"고 규범화한다. `@MX:WARN`/`@MX:REASON`(`:2415-2422`)은
락 없는 갱신이 `UploadRackNumberView`에서 유래한 기존에 수용된 격차임을 명시한다.

### 2.1 추가 발견 — 재사용 가능한 공유 헬퍼 `_resolve_orders_by_name`

`backend/order/purchase_order_views.py:2812-2829`에 SPEC-ORDER-016이 추출해 둔 헬퍼가 이미
존재한다:

```
def _resolve_orders_by_name(names) -> dict[str, "Order"]:
    orders_by_name: dict[str, Order] = {}
    if names:
        for candidate in Order.objects.filter(name__in=set(names)).order_by("pk"):
            orders_by_name.setdefault(candidate.name, candidate)
    return orders_by_name
```

이 함수는 `_process_outbound_rows`의 `orders_by_name` 블록과 동일한 최저 `pk` tie-break를
공유 헬퍼로 추출한 것이며(문서화 주석 `:2813-2824`, 여는 `"""`부터 닫는 `"""`까지), 이름이
겹치는 요청 집합에 대해 배치
쿼리 1회(빈 입력이면 0회)를 보장한다. 렉번호 배치 재작성은 이 헬퍼를 **재사용**하는 편이
`order_by("pk")` + `setdefault` tie-break 로직을 세 번째로 복제하지 않는 길이다(plan.md
기술적 접근 참조). 단, 이 함수는 `order` 모듈 안에서 `UploadRackNumberView`보다 뒤쪽
(`:2812`)에 정의되어 있으므로 import/함수 순서상 앞으로 이동하거나 모듈 레벨 헬퍼로 승격할
필요가 있는지는 구현 시점에 확인한다.

### 2.2 아키텍처 선례 — "모듈 레벨 순수 함수 + 얇은 뷰 래퍼" (v1.0.2, 설계 결정 H 근거)

이 파일에는 `_process_outbound_rows` 외에도 같은 아키텍처를 쓰는 두 번째 함수가 있다:
`_process_force_outbound_rows`(`purchase_order_views.py:3021-`, 시그니처
`def _process_force_outbound_rows(rows: list[dict]) -> dict:`, docstring이 `:3022-3036`에
있으며 SPEC-ORDER-016이 확립했다). Grep으로 확인한 결과 이 함수의 호출부는
`OutboundForceProcessView.post()` 안의 `:3220`(`result = _process_force_outbound_rows(rows)`)
한 곳뿐이다. 즉 이 파일은 이미 "로직 전체를
소유하는 모듈 레벨 순수 함수, 뷰는 호출만 하는 얇은 래퍼" 패턴을 두 번 확립했다 —
`_process_rack_number_rows` 추출은 새 패턴의 도입이 아니라 기존 관례를 세 번째로 적용하는
것이다.

이 추출이 필요했던 이유는 v1.0.1의 쿼리 카운트 AC가 엔드포인트 레벨로 서술되어 있었기
때문이다(plan-auditor D2). `UploadRackNumberView`는
`authentication_classes = [JWTAuthentication]`(`purchase_order_views.py:2177`, 클래스는
`rest_framework_simplejwt.authentication`에서 `:47`에 임포트됨)를 쓰며, 이 인증 클래스의
`get_user()`는 매 인증 요청마다 `self.user_model.objects.get(...)` 형태의 사용자 조회 쿼리
1건을 발생시킨다(설치된 `rest_framework_simplejwt` 패키지 소스 확인). 이 프로젝트의
`backend/config/settings/` 어디에도 `ATOMIC_REQUESTS`가 설정되어 있지 않으므로, 이 추가
쿼리를 상쇄할 요청 단위 세이브포인트도 없다. 기존 15개 특성화 테스트는 전부
`auth_client`(`backend/order/tests/test_spec_013.py:76-79`)를 통해 엔드포인트를 호출하며,
이 픽스처는 `RefreshToken.for_user(user)`로 실제 JWT를 발급해
`client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")`로 요청에 싣는다
— 즉 뷰를 통한 측정은 이 인증 쿼리를 피할 수 없다.

함수를 추출하면 `_process_rack_number_rows(rows)`를 `CaptureQueriesContext`로 직접 감싸
측정할 수 있게 되어(아래 §5의 `test_spec_015.py:1118-1121`과 동일한 기법), 이 문제 자체가
사라진다.

## 3. 비승계 지점 — 결정 A(2+ 매칭 거부)는 복제하지 않는다

`_process_outbound_rows`는 하나의 키가 LineItem 2건 이상과 매칭되면 `multiple_line_items`로
**거부**한다(`purchase_order_views.py:2582-2594`, SPEC-ORDER-015 설계 결정 A).

렉번호 엔드포인트의 계약은 **정반대**다. SPEC-ORDER-013 결정 E에 따라, `(order_name, sku)`
키 하나에 매칭되는 LineItem이 여러 건이면 **전부** 같은 `rack_number`를 받아야 하고,
`matched_count`는 여전히 그 키를 **1**로 센다. 이는
`test_upload_multiple_lineitems_matching_key_all_updated`
(`backend/order/tests/test_spec_013.py:748-764`)로 pin되어 있다:

```python
def test_upload_multiple_lineitems_matching_key_all_updated(self, auth_client):
    """Decision E / REQ-RACK-006: when (order_name, sku) matches 2+
    LineItems, all of them are updated."""
    ...
    assert res.data["matched_count"] == 1
    li1.refresh_from_db()
    li2.refresh_from_db()
    assert li1.rack_number == "SHELF-1"
    assert li2.rack_number == "SHELF-1"
```

따라서 배치 재작성은 `line_items_by_key`에서 후보 수가 0/1/2+인지로 분기하지 않고, **후보가
1건 이상이면 전부** `to_update`에 append해야 한다. 이것이 이 SPEC의 핵심 구현 함정이다 —
`_process_outbound_rows`의 판정 루프를 그대로 복사하면 이 계약을 깨뜨린다.

## 4. 기존 동작 계약 — 15개 특성화 테스트

`backend/order/tests/test_spec_013.py:607-856`의 `TestUploadRackNumberView`가 아래 15개
테스트를 무수정 통과해야 한다(전량 이 세션에서 라인 번호 재확인):

| 테스트 | 라인 | 검증 대상 |
|---|---|---|
| `test_upload_wrong_extension_returns_400` | 615 | 비-`.xlsx` → DB 접근 전 400 |
| `test_upload_corrupted_xlsx_returns_422_and_no_modification` | 620 | 파서 `ValueError` → 422, 무수정 |
| `test_upload_empty_xlsx_returns_422` | 637 | 빈 워크북 → 422 |
| `test_upload_malformed_header_returns_422_and_no_modification` | 649 | 헤더 누락 → 422, 무수정 |
| `test_upload_matches_and_updates_lineitem` | 664 | 정상 매칭 |
| `test_upload_matches_eb_prefixed_order_with_divergent_order_number` | 680 | 매칭은 항상 `Order.name` 문자열 일치, `Order.order_number` 사용 안 함 |
| `test_upload_order_not_found_skipped` | 703 | 주문 미발견 → skipped |
| `test_upload_sku_not_found_in_order_skipped` | 714 | SKU 미발견 → skipped |
| `test_upload_duplicate_order_sku_last_row_wins` | 729 | dedup은 **마지막 행 우선** |
| `test_upload_multiple_lineitems_matching_key_all_updated` | 748 | 결정 E — §3 참조 |
| `test_upload_cross_order_isolation` | 766 | 다른 Order의 동일 SKU는 불변 |
| `test_upload_matched_skipped_count_distinct_keys_after_dedup` | 784 | 카운트는 dedup 후 **고유 키** 단위, 원본 행/LineItem 단위 아님 |
| `test_upload_blank_order_identifier_counts_as_skipped` | 809 | 빈 주문 식별자 행도 skipped로 카운트 |
| `test_upload_unauthenticated_returns_401` | 836 | 미인증 → 401 |
| `test_upload_never_calls_recompute_order_aggregates` | 842 | `_recompute_order_aggregates` 미호출(spy) |

또한 `parse_rack_number_excel`(`backend/order/excel_utils.py:994`, `def` 줄)의 docstring
(본문 `:995-1030`, 특히 `:1018-1026`)은 빈 문자열 `rack_number`가 **명시적 "지움" 값**으로
보존되며 falsy로 걸러져서는 안 된다고 규정한다:

> "The rack_number value is NOT required — an empty string is preserved as an explicit
> "clear this rack_number" value rather than being skipped (plan.md M3)."

## 5. 쿼리 카운트 회귀 테스트 기법 — 재사용 대상

`backend/order/tests/test_spec_015.py`의 "T8 — batched DB access" 절이 이미 이 기법을
확립했다(모두 이 세션에서 재확인):

- `from django.test.utils import CaptureQueriesContext` (`:34`)
- `_seed_outbound_groups(n, offset)` 픽스처 빌더(`:1104-1115`)
- `_count_queries(rows)` 헬퍼(`:1118-1121`, `CaptureQueriesContext(connection)`로 감싸
  `len(ctx.captured_queries)` 반환)
- `class TestOutboundQueryCountIsIndependentOfRowCount`(`:1124-1157`)의 클래스 docstring
  (`:1126-1131`)이 이미 이 논지를 명시한다: "The discriminating assertion is the EQUALITY
  between a 2-group batch and a 10-group batch: any per-group query at all makes those two
  numbers differ, regardless of what the absolute constant happens to be on a given backend."
  - `test_query_count_is_identical_for_2_and_for_10_groups`(`:1133-1141`) — **판별력의
    핵심은 2그룹과 10그룹 쿼리 수의 동등성**이다. 그룹당 쿼리가 하나라도 있으면 이 두 수가
    달라지므로, 절대값이 무엇이든 이 동등성만으로 O(1) 여부를 증명한다.
  - `test_query_count_stays_within_a_small_fixed_bound`(`:1143-1147`) — 10그룹 전부 매칭
    시 `<= 6`.
  - `test_a_batch_that_writes_nothing_issues_no_write_query`(`:1149-1153`) — 전부
    미매칭이면 `<= 4`.
  - `test_an_empty_batch_touches_the_database_at_most_for_the_transaction`(`:1155-1157`)
    — 빈 입력이면 `<= 2`.
- `class TestOutboundBatchingPreservesMatchingSemantics`의
  `test_duplicate_order_names_resolve_to_the_lowest_pk_order`(`:1166-1186`) — 동명 `Order.name`
  충돌이 최저 `pk`로 해소됨을 pin. **(v1.0.3 정정, D21)**: 이 테스트의 픽스처는
  `first = _make_order(...)` 다음 `second = _make_order(...)`(`:1175-1176`) 순서로 생성해
  **`pk` 오름차순 = 생성 순서** 그대로다 — `pk`와 생성 시각을 일부러 어긋나게 만들지
  **않는다**. 렉번호 SPEC(spec.md AC-RACKBATCH-003)이 요구하는 "낮은 `pk`가 나중에
  생성되도록" 만드는 뒤집기는 이 참조 테스트가 실증하지 않는, 이 SPEC이 스스로 강화한
  요구사항이다 — tie-break 판정 로직(`name__in` + `order_by("pk")`) 자체는 동일한 기법을
  재사용할 수 있지만, 그 판정이 생성 순서가 아니라 진짜 `pk` 값에 의존한다는 것을 증명하는
  픽스처는 별도로 만들어야 한다.

`UploadRackNumberView`에는 이 클래스에 해당하는 테스트가 **전혀 없다**. 이 SPEC은 렉번호
엔드포인트에 동등한 쿼리 카운트 테스트와 동명 `Order.name` tie-break 테스트를 신설해야 한다.

**v1.0.1 정정(plan-auditor D2)**: v1.0.0의 이 절은 절대 상한을 "구현 후 실측치를 기준으로
고정"한다고 서술해, `spec.md` AC-RACKBATCH-001이 구현자가 사후에 스스로 정하는 기준을
갖게 만들었다. 렉번호 엔드포인트의 목표 구조(`transaction.atomic()` 1회 + Order 조회 1회 +
LineItem 조회 1회 + `bulk_update` 최대 1회)가 `_process_outbound_rows`와 구조적으로
동일하므로, 위 `test_spec_015.py:1143-1153`의 실측 상한(`<= 6` / `<= 4` / `<= 2`)을 그대로
적용하는 것이 타당하다 — `spec.md`/`plan.md`/`acceptance.md`는 이제 이 값을 사전에 확정된
숫자로 명시한다. 실제 측정치가 구조적 사유로 이 값과 다르면(예: pytest-django 트랜잭션
래핑 방식 차이) `spec.md` HISTORY에 근거를 남기고 세 문서를 함께 갱신한다.

**v1.0.2 정정(plan-auditor D2/D2a/D2b/D2c)**: v1.0.1의 "구조적으로 동일"이라는 판단은
`_process_outbound_rows`가 **함수 직접 호출**로 측정된다는 사실을 놓쳤다 — 당시 계획은
렉번호 로직을 뷰 안에서 재작성하는 것이었으므로, 실제 테스트는 `auth_client`를 통해
엔드포인트를 호출할 수밖에 없었고, §2.2가 확인한 `JWTAuthentication`의 사용자 조회 쿼리
1건이 상한 계산에서 누락되어 있었다(특히 빈 입력 케이스의 `<= 2`는 인증 쿼리를 포함하면
3이 되어 애초에 달성 불가능했다). §2.2의 함수 추출 결정으로 측정 스코프가 함수 직접 호출로
바뀌면서 이 문제 자체가 해소된다 — 세 상한(`<= 6`/`<= 4`/`<= 2`) 수치는 그대로지만, 이제는
"참조 구현과 같은 숫자를 옮겨왔다"가 아니라 "같은 측정 컨텍스트(함수 직접 호출)에서 같은
가드 구조를 가진 함수를 재본다면 같은 상한이 나온다"는 근거로 성립한다(도출 과정은
`spec.md` AC-RACKBATCH-001과 `plan.md` 기술적 접근 9단계 참조). 인용 범위도 `<= 2`가
`:1143-1153` 밖의 `:1155-1157`에 있다는 D2c 지적에 따라 본 문서(§5, 위)는 처음부터 세
테스트를 개별적으로 정확히 인용하고 있었다 — 부정확했던 것은 `spec.md`/`acceptance.md`/
`plan.md`의 인용이었다(각 문서에서 정정).

## 6. 인덱스 현실

- `Order.name`은 **이미 인덱스가 있다**: `backend/order/models.py` `Order.Meta`
  (`:92-111`)의 `indexes` 리스트 마지막 항목이 `models.Index(fields=["name"])`(`:110`)이며,
  그 위 주석(`:100-109`)이 정확히 `UploadRackNumberView`와 `_process_outbound_rows`의
  `Order.name` 배치 조회를 근거로 이 인덱스가 추가되었다고 기록한다. 따라서 `name__in`은
  인덱스를 탄다.
- `LineItem.order`는 `ForeignKey`(`models.py:169`)이므로 `order_id`에 암묵적 인덱스가 있다.
- `LineItem.sku`는 단독 인덱스가 없다. `sku`가 관여하는 유일한 인덱스는
  `unique_together = [("order", "shopify_line_item_id", "sku")]`(`models.py:228`)이며
  `sku`는 후행 컬럼이다. 배치 조회 `order_id__in` + `sku__in`은 인덱스가 있는 `order_id`로
  먼저 좁혀지므로 렉번호 업로드 배치 규모에서는 충분하다. **신규 인덱스 추가는 이 SPEC의
  범위가 아니다.**

## 7. 리스크 입력 — 모델 side-effect 부재 확인

`LineItem`(`backend/order/models.py:152-229`)에는 `save()` 오버라이드가 없고, `auto_now`/
`auto_now_add` 필드도 없다(모델 필드 전체를 `:169-222`에서 확인 — `created_at`/`updated_at`
류 필드가 `LineItem`에는 존재하지 않는다). `backend/order/` 디렉터리 전체에서
`post_save`/`pre_save`/`receiver`/`signals` 문자열도 발견되지 않는다(Grep 결과 매치 없음).
따라서 `.update()`(쿼리셋 UPDATE) → `bulk_update()`(객체 단위 UPDATE) 전환은 우회하는
자동 관리 필드나 시그널이 없다 — 이 SPEC이 확인한 non-risk다.

기존에 수용된, 이 SPEC이 악화시키지 않는 격차: 렉번호 엔드포인트는 `select_for_update()` 없이
락-프리로 갱신한다. 이는 `@MX:WARN`/`@MX:REASON`(`purchase_order_views.py:2415-2422`)에
명시되어 있으며, 그 REASON이 `UploadRackNumberView`를 이 패턴의 **원조**로 지목한다. 락 도입은
이 SPEC의 범위 밖이다.

## 8. 프론트엔드 — 변경 불필요

- `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx`: `handleUploadChange`
  (`:93-103`)는 `FormData`를 그대로 POST하고, 업로드 버튼(`:130-138`)은
  `disabled={uploadMutation.isPending}`이며 라벨을 `'업로드 중...'` / `'Excel 업로드'`로
  토글할 뿐 진행률 UI가 없다.
- `frontend/src/hooks/useRackNumberQueries.ts`의 `useUploadRackNumber`(`:53-67`)는 성공 시
  `ORDER_DETAIL_QUERY_KEY`를 무효화하고 `matched_count`/`skipped_count`를 토스트로 표시한다.
- `frontend/src/services/rackNumberApi.ts:48`의 `uploadRackNumber`가 실제 POST 호출부다.
- `frontend/src/lib/axios.ts`(전체 파일 확인) — 공유 `api` 인스턴스는 `baseURL`과
  `Content-Type` 헤더만 설정하며, **`frontend/src` 어디에도 axios `timeout`이 설정되어
  있지 않다.** 즉 현재의 느림은 클라이언트 타임아웃이 아니라 요청이 그냥 오래 걸리는 것이다.
  응답 계약 `{matched_count, skipped_count}`가 변경되지 않으므로 프론트엔드는 **수정이
  불필요**하다.

## 9. 범위 밖 이웃 — 확인만 하고 손대지 않음

- `ConfirmOrderView`(`purchase_order_views.py:841`)는 여전히 항목별 루프 안에서 DB에
  접근한다. 락을 쥔 조회는 `LineItem.objects.filter(sku=sku).exclude(...)
  .select_for_update()`(`:918-925`)이고, 그 직후 `if not unordered_lis:` 분기 안의
  `.exists()` 호출(`:927-929`)은 **별도의, 락을 쥐지 않는** 조회다 — 배치 조회로 단순
  치환할 수 없는 락 보유 구조다. 별도 후속 SPEC 후보로만 기록하고 이 SPEC에서는 다루지
  않는다.
- `UploadDailyReviewView`(`:1229`), `UploadVendorShipmentView`(`:1723`),
  `UploadWarehouseReceiptView`(`:1788`), `_process_outbound_rows`(`:2423`),
  `_resolve_orders_by_name`(`:2812`), SPEC-ORDER-016 강제 출고 경로는 **이미 배치 처리되어
  있다.** 범위 밖.

## 10. 요약 — 대상 함수/뷰 구조 (v1.0.2, §2.2 설계 결정 H 반영)

**`_process_rack_number_rows(rows: list[dict]) -> dict`(신설, 모듈 레벨):**

1. `dedup_map` 구축(기존 로직을 그대로 이 함수 안으로 이동, `order_name is None` 분기
   포함) — 순수 파이썬, DB 접근 없음.
2. `transaction.atomic()`에 **조건 없이 진입한다** — `dedup_map`이 비어 있어도 마찬가지다.
   `_process_outbound_rows`가 `grouped`가 비어도 `with transaction.atomic():`을 그대로
   실행하는 것과 동일한 원칙이며, `test_spec_015.py:1155-1157`의 빈 배치 상한 `<= 2`가
   이 무조건 진입을 전제로 성립한다. **v1.0.1 정정**: 이 절이 이전에 서술했던 "빈
   `dedup_map`이면 조회를 건너뛰고 즉시 반환"은 이 원칙과 모순되므로 폐기한다 — atomic
   블록 진입 자체는 무조건이고, 블록 내부의 가드(아래 3~5단계)가 실제 쿼리 발생 여부를
   결정한다.
3. `Order.objects.filter(name__in={...}).order_by("pk")` + `setdefault`(또는
   `_resolve_orders_by_name` 재사용) — 최저 `pk` tie-break. **`if grouped:`류 가드로 감싼다**
   (`_process_outbound_rows`의 `:2533`과 동일 역할).
4. `LineItem.objects.filter(order_id__in=[...], sku__in={...}).order_by("pk")`를
   `(order_id, sku)` 키로 그룹핑. **`if orders_by_name:`류 가드로 감싼다**
   (`_process_outbound_rows`의 `:2550`과 동일 역할).
5. `dedup_map`을 순회하며 각 키의 후보 리스트를 조회 — **0건이면 skip, 1건 이상이면 전부**
   `rack_number` 갱신 대상으로 `to_update`에 append(§3, 결정 A 비승계). 기존
   `@MX:WARN`/`@MX:REASON`(`:2218-2226`)을 이 지점(새 함수 **본문 안**)으로 이관한다
   (§1 step 3, D8, D20(b)).
6. `if to_update: LineItem.objects.bulk_update(to_update, ["rack_number"])`. **이 가드도
   필수다**(`_process_outbound_rows`의 `:2701`과 동일 역할) — 3~6단계의 가드 세 개가
   AC-RACKBATCH-001의 쿼리 상한 도출 전제다.
7. `{"matched_count": ..., "skipped_count": ...}`를 반환한다 — dedup 키 단위 카운트는
   그대로 유지.

**`UploadRackNumberView.post()`(축소):**

8. 파일 존재 확인(`:2181-2183`) → `.xlsx` 확장자 확인(`:2185-2190`) →
   `parse_rack_number_excel` 호출·`ValueError`→422(`:2193-2196`) →
   `_process_rack_number_rows(parsed_rows)` 호출 → 반환 dict를 `Response(..., 200)`으로
   포장. 기존 `try/except Exception -> 500`(`:2216-2261`)은 재작성 없이 그대로 유지하되
   감싸는 대상만 "dedup-키 순회 루프"에서 "`_process_rack_number_rows` 호출"로 바뀐다 —
   REQ-RACKBATCH-015(처리되지 않은 예외 → HTTP 500 + 부분 미반영)의 구현이 이미 존재한다.
   **알려진 동작 변화(v1.0.3, 결함 아님)**: 현재 `dedup_map` 구축(`:2198-2212`)은 `try`
   (`:2216`) **밖**에 있어 dedup 단계 예외가 DRF로 무가공 전파된다. 추출 후에는 dedup이
   `_process_rack_number_rows` 호출 **안**으로 들어가므로 같은 예외가 `except Exception`
   가드에 잡혀 `{"detail": ...}` 500 JSON 본문으로 바뀐다. 둘 다 500 계열이며 이를 pin하는
   기존 테스트가 없으므로 15개 특성화 테스트에 대한 회귀는 아니다.

## 11. `bulk_update`의 실제 SQL 형태 — AC-RACKBATCH-011(a) 근거 (v1.0.3, D17)

이 프로젝트에 설치된 Django는 5.1.6이다(`python -c "import django; print(django.VERSION)"`
확인, `(5, 1, 6, 'final', 0)`). Django 소스
(`site-packages/django/db/models/query.py`)의 `QuerySet.bulk_update`(`:875-`)를 열어 확인한
결과:

- `:897` 주석: `"PK is used twice in the resulting update query, once in the filter and once
  in the WHEN."` — 즉 각 필드는 `Case`/`When` 식으로 감싸이고, `When(pk=obj.pk, then=attr)`
  (`:914`)이 그 조건절에 `pk`(=`id`)를 사용한다.
- 결과 SQL은 `UPDATE ... SET "rack_number" = CASE WHEN "id" = %s THEN %s ... END WHERE "id"
  IN (...)` 형태다 — `id`는 `SET` 절의 **대입 대상(좌변)**이 아니라 `CASE WHEN` **조건절**
  안에 등장한다.

따라서 AC-RACKBATCH-011(a)가 "SET 절에 등장하는 모든 컬럼이 `rack_number`뿐"으로 검증하면
정상 구현도 실패한다(`id`가 조건절에 있으므로) — 검증 대상은 "SET 절에서 대입되는(각
대입식의 좌변) 컬럼"으로 한정해야 한다. `bulk_update`에 두 번째 필드(예:
`shipped_quantity`)가 추가되면 그 필드가 새로운 대입식의 좌변으로 나타나므로, 이 좁혀진
검증도 여전히 판별력을 유지한다.
