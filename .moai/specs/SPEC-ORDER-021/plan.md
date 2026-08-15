---
id: SPEC-ORDER-021
document: plan
version: 1.3.0
status: implemented
updated: 2026-08-15
---

# 구현 계획 — SPEC-ORDER-021 마진 계산에 배송비·한국창고비 반영

`spec.md`의 요구사항(REQ-COST-001~019, v1.3.0 확장 REQ-COST-020~029)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD 사이클, 리스크와 완화책, MX 태그 계획을 정리한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을 재진술하지 않고 REQ ID로 참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의 `development_mode: "tdd"`(`:4`), `test_first_required: true`(`:43`), `min_coverage_per_commit: 80`(`:46`)에 따른다. 브라운필드 변경이므로 각 RED 단계 전에 대상 코드를 먼저 읽는다(`.claude/rules/moai/workflow/workflow-modes.md`의 Brownfield Enhancement 절).

**이 SPEC의 특이점**: 모델/마이그레이션 변경이 없다 — `backend/order/serializers.py` 한 파일의 계산 로직 확장과, 그 위에 얹히는 프론트엔드 타입/표시 변경뿐이다. 기존 테스트 2개 파일(`test_spec_008.py`, `test_spec_009.py`)의 마진 기대값 5건이 새 공식에 맞춰 바뀐다 — `spec.md` "기존 테스트 갱신 대상" 표가 규범 출처다.

## v1.3.0 확장 요약

기존 M0~M5 마일스톤은 그대로 유지하고(무수정), 아래를 동일한 RED-GREEN-REFACTOR 사이클로 추가했다.

- **M6 (High) — confirmed_cost/total_cost RED**: `_compute_cost_breakdown_uncached`가 이미 계산해 두던 `confirmed_cost_usd`를 반환값 dict에 추가하고, `total_cost_usd`(반올림 전 세 항의 합)를 새로 계산해 함께 반환하도록 하기 **전**, `test_spec_021.py`에 T14~T18(AC-COST-014~018)을 먼저 작성했다. 구현을 임시로 `git stash`해 되돌린 상태에서 5개 전부 `KeyError`로 실패함을 직접 확인한 뒤(RED), stash를 복원했다.
- **M7 (High) — GREEN**: `confirmed_cost`/`total_cost` `SerializerMethodField` 2개 + `Meta.fields` 추가. 기존 `margin_usd`/`get_margin_amount`/`get_margin_rate`/두 None 게이트는 한 글자도 수정하지 않았다(REQ-COST-024 인접 제약). T14~T18 GREEN 확인, 기존 T1~T13 무수정 통과 재확인(회귀 없음).
- **M8 (High) — 프론트엔드 RED→GREEN**: `types/order.ts`에 `confirmed_cost`/`total_cost` 추가, 두 `buildOrderDetail()`(`OrderDetailPage.test.tsx`, `SearchTab.test.tsx`)에 `null` 기본값 추가. `OrderDetailPage.test.tsx`에 신규 describe 블록(AC-COST-019, 6개 `it`)을 작성해 RED 확인 후, `OrderDetailPage.tsx`의 결제 정보 섹션을 재구성해 GREEN 전환.
- **M9 (Medium) — 회귀 확인**: `test_spec_021.py` 17개 전량, `backend/order/tests/` 전체 스위트, `OrderDetailPage.test.tsx`+`SearchTab.test.tsx` 34개, `tsc -b`(에러 24건 불변, 4개 대상 파일 신규 에러 0건), AC-COST-009 쿼리 수 무수정 통과(`ORDER_DETAIL_QUERY_COUNT=7` 등 실측값 변화 없음) 확인.

---

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 베이스라인 확인**: `backend/order/serializers.py:141-225`(`OrderDetailSerializer`), `backend/order/views.py:31-45`(`OrderDetailView.get_queryset`), `backend/order/models.py:152-238`(`LineItem`), `backend/order/tests/test_spec_008.py`, `test_spec_009.py`, `test_spec_018.py:483-549`(쿼리 캡처 관례), `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:1-75`(두 번째 `buildOrderDetail`) 전체를 다시 읽는다. 기존 백엔드·프론트엔드 테스트 스위트(`pytest backend/order/tests/`, `npm run test`)와 `npm run build`(`tsc -b`)의 현재 통과 상태를 기록한다 — 이 SPEC 이전부터 실패하던 것과 이 SPEC이 깬 것을 구분하는 기준이 된다.

- **M1 (High) — 인수 기준 계약 테스트 선작성 + 기존 테스트 갱신 (RED)**:
  - `backend/order/tests/test_spec_008.py`의 3개 테스트(`test_margin_amount_calculation_with_partial_confirmed`, `test_margin_rate_calculation_rounds_to_2_decimal_places`, `test_confirmed_price_zero_is_valid_not_null`)와 `backend/order/tests/test_spec_009.py`의 2개 테스트(`test_margin_uses_exchange_rate_for_usd_conversion`, `test_margin_fallback_to_prior_date_rate`)의 기대값을 `spec.md` "기존 테스트 갱신 대상" 표의 신규 기대값으로 갱신한다. 갱신 직후 이 5개 테스트는 **현재(무수정) 코드에서 반드시 실패해야 한다** — 현재 코드는 여전히 구 공식 값을 반환하기 때문이다. 실패하지 않으면 표의 계산이 틀렸다는 뜻이므로 재검산한다.
  - `backend/order/tests/test_spec_021.py`를 신규 작성한다 — AC-COST-001~013(13개)에 1:1 대응하는 테스트를 담는다. AC-COST-001~005, 008, 012, 013(정상 마진/환율/반올림 케이스)과 AC-COST-006/007(None 게이트)은 **현재 코드에서 반드시 실패**해야 한다(신규 필드 자체가 없어 `KeyError` 또는 `None` 불일치로 실패). **AC-COST-006/007은 반드시 `"shipping_cost" in res.data`류의 키 존재 단정을 포함해야 한다** — 관례적인 `res.data.get("shipping_cost")` 조회는 키가 없어도 `None`을 반환하므로(`test_spec_008.py:235,254,282` 등 기존 패턴), 이 조회 방식으로 작성하면 현재(미구현) 코드에서 **이미 통과**해버려 RED가 성립하지 않는다(감사 D6) — 두 테스트를 작성한 직후 반드시 무수정 코드에서 실행해 실패를 직접 확인한다. AC-COST-009(쿼리 불변식)는 워밍업 요청을 먼저 보낸 뒤 X/Y 두 주문의 쿼리를 캡처하며(감사 D10), 아이템 수 무관 절대값 고정(a)의 정확한 숫자는 **이 시점에 실제로 실행해 관측한 값**으로 채운다(`test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3` 관례와 동일 — 추측값을 넣지 않는다).
  - `frontend/src/pages/OrderDetailPage.test.tsx`의 `buildOrderDetail`(`:35-95`) 픽스처 헬퍼에 `shipping_cost`/`korea_warehouse_cost` 기본값(`null`)을 추가하고, AC-COST-011에 대응하는 신규 `it` 블록을 추가한다 — 현재 코드에서는 `OrderDetail` 타입에 해당 필드가 없어 TypeScript 컴파일이 실패해야 한다(RED). 픽스처는 `margin_amount="159.58"`, `shipping_cost="8.18"`, `korea_warehouse_cost="2.25"`를 쓴다 — `shipping_cost="0.00"`을 쓰면 `Number("0.00").toLocaleString()==="0"`이라 렌더링이 "0 USD"가 되어 정상 구현에서도 실패한다(감사 D3).

- **M2 (High) — 비용 계산 구현 (GREEN)**:
  - `backend/order/serializers.py`에 상수 3개(REQ-COST-001) 선언.
  - `_compute_margin_usd`(`:189-204`)를 비용 내역을 포함하는 헬퍼로 확장 — 무게/권수/배송비/한국창고비를 `obj.line_items.all()`의 기존 단일 루프(`:196`) 안에서 함께 집계한다(REQ-COST-002~007). 반환값은 `margin_usd`, `total_price_usd`, `shipping_cost_usd`, `korea_warehouse_usd`, `total_weight_grams`를 모두 담는 묶음으로 확장한다(REQ-COST-019, 설계 결정 E) — 이름·자료구조(dict/namedtuple/dataclass)는 구현자 재량.
  - **메모이제이션(REQ-COST-015, 설계 결정 C/F, 감사 D5): 이 헬퍼의 계산 결과를 주문(객체) 단위로 캐시한다.** 5개 게터가 동일한 `obj`에 대해 이 헬퍼를 각각 독립 호출하면 라인아이템 순회와 `ExchangeRate` 쿼리가 요청당 최대 5회까지 늘어난다 — DRF `SerializerMethodField`는 필드마다 독립 평가되므로 이 캐시를 헬퍼 자신이 책임져야 한다. 구현 방법은 구현자 재량이나(예: 시리얼라이저 인스턴스의 `{obj.pk: 결과}` 딕셔너리, 또는 `getattr(obj, "_cost_breakdown", None)`으로 `obj`에 직접 부착), 5개 게터 모두 이 캐시를 거쳐야 한다.
  - `get_margin_amount`/`get_margin_rate`(`:206-225`)를 확장된 헬퍼를 쓰도록 갱신하고, 신규 `get_shipping_cost`/`get_korea_warehouse_cost`/`get_total_weight_grams`를 추가한다 — 5개 게터 전부 동일한 None 게이트(헬퍼가 `None`을 반환하면 그대로 `None` 전파)를 공유한다(REQ-COST-009, 010, 설계 결정 D).
  - `OrderDetailSerializer`의 필드 선언(`:150-151` 인근)과 `Meta.fields`(`:164` 인근)에 `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams`를 추가한다.
  - `OrderListSerializer`(`:14-36`)는 **한 글자도 건드리지 않는다**(REQ-COST-014).
  - **`frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:47`의 두 번째 `buildOrderDetail()` 리터럴에 `shipping_cost: null, korea_warehouse_cost: null`을 추가한다(감사 D2).** `types/order.ts`의 `OrderDetail`에 REQ-COST-017의 두 필드를 추가하는 순간 이 파일도 함께 고쳐야 `tsc -b`(`npm run build`)가 통과한다 — `frontend/src/types/order.ts` 변경과 **같은 커밋/같은 단계**에서 처리해 컴파일이 깨지는 중간 상태를 만들지 않는다.

- **M3 (Medium) — REFACTOR**: 확장된 헬퍼의 가독성을 다듬는다. 상수 3개에 이 SPEC을 가리키는 주석을 남긴다(REQ-COST-001). 5개 게터가 정말 단일 헬퍼만 호출하는지, 각자 별도 루프를 갖고 있지 않은지, 메모이제이션이 실제로 동작하는지(같은 `obj`에 대해 헬퍼 본문이 두 번째 호출부터 실행되지 않는지) 재확인한다(설계 결정 C).

- **M4 (Medium) — 회귀 확인**: 백엔드 테스트 스위트 전량 재실행. `git diff --stat backend/order/models.py backend/order/migrations/`가 비어 있는지 확인(모델/마이그레이션 무변경). `frontend/src/types/order.ts`, `frontend/src/pages/OrderDetailPage.tsx`, `frontend/src/pages/OrderDetailPage.test.tsx`, `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`(감사 D2 — 이 파일은 **제외 대상이 아니라 예상된 변경 대상**이다) 네 파일을 제외한 프론트엔드 파일에 diff가 없는지 확인. `npm run build`(`tsc -b`)와 `npm run test`(`SearchTab.test.tsx` 포함) 전량 통과를 확인한다.

- **M5 (Low) — MX 태그 적용 + 문서 동기화**: 아래 MX 태그 계획을 적용하고, `spec.md`/`plan.md`/`acceptance.md`의 `status`를 갱신하며 구현 중 발견한 발산을 `spec.md` HISTORY에 기록한다.

의존 관계: M0 → M1 → M2 → M3 → M4 → M5.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/serializers.py`(`:141-225` 인근, `OrderDetailSerializer`) | 상수 3개 추가(REQ-COST-001). `_compute_margin_usd`(`:189-204`) 확장 — 무게/권수/배송비/한국창고비 집계를 기존 라인아이템 루프(`:196`) 안에 통합하고 주문 단위로 메모이즈(REQ-COST-002~008, 015). `get_margin_amount`/`get_margin_rate`(`:206-225`) 갱신, 신규 `get_shipping_cost`/`get_korea_warehouse_cost`/`get_total_weight_grams` 추가(REQ-COST-011~013). `OrderDetailSerializer` 필드 선언(`:150-151`)과 `Meta.fields`(`:164`)에 3개 필드 추가. |
| EXISTING (무수정) | `backend/order/serializers.py`의 `OrderListSerializer`(`:14-36`) | REQ-COST-014. |
| EXISTING (무수정) | `backend/order/models.py`, `backend/order/migrations/` | 신규 모델 필드나 마이그레이션 없음 — `grams`/`quantity`/`confirmed_price`/`ExchangeRate.rate`가 이미 존재한다. |
| EXISTING (무수정) | `backend/order/views.py`의 `OrderDetailView.get_queryset`(`:38-45`) | 기존 `prefetch_related("line_items__notes__author", ...)`가 이미 이 SPEC이 의존하는 단일 쿼리 전제를 제공한다 — 변경 불필요. |
| MODIFY | `backend/order/tests/test_spec_008.py` | 3개 테스트 기대값 갱신(`:219-237`, `:264-286`, `:293-319`) — `spec.md` "기존 테스트 갱신 대상" 표 참조. |
| MODIFY | `backend/order/tests/test_spec_009.py` | 2개 테스트 기대값 갱신(`:160-183`, `:186-212`). |
| NEW | `backend/order/tests/test_spec_021.py` | AC-COST-001~013(13개) 대응 테스트. 픽스처는 `test_spec_009.py`의 `exchange_rate_2026_01_15`류 패턴(`:43-49`)과 `test_spec_008.py`의 order/line-item 생성 패턴(`:34-65`)을 따른다. AC-COST-009의 쿼리 캡처는 `test_spec_018.py:40,483-549`의 `CaptureQueriesContext` + 워밍업 관례를 따르되, `orders_line_item` 매칭은 부분 문자열이 아니라 정규식(`orders_line_item(?!_)`) 또는 `connection.ops.quote_name(...)` 완전 일치를 쓴다(감사 D1 — `LineItemNote.db_table = "orders_line_item_note"`, `models.py:297`가 단순 `in` 검사를 오염시킨다). |
| MODIFY | `frontend/src/types/order.ts` | `OrderDetail`(`:168-` 인근, `margin_amount`/`margin_rate` `:196-197`)에 `shipping_cost: string \| null`, `korea_warehouse_cost: string \| null` 추가(REQ-COST-017). |
| MODIFY | `frontend/src/pages/OrderDetailPage.tsx` | 결제 정보 섹션(`:505-527`)의 마진율 표시(`:520-525`) 다음에 배송비·한국창고비 두 줄 추가, `margin_amount`와 동일한 `"{value} USD"` / `"—"` 폴백 패턴(`:515-518`) 재사용(REQ-COST-016). |
| MODIFY | `frontend/src/pages/OrderDetailPage.test.tsx` | `buildOrderDetail`(`:35-95`) 기본 픽스처에 `shipping_cost: null, korea_warehouse_cost: null` 추가, AC-COST-011 대응 신규 `it` 블록 추가(`renderPage()` `:20-33` 재사용). 픽스처 값은 `shipping_cost="8.18"`(`"0.00"` 아님 — 감사 D3). |
| MODIFY | `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`(`:47`) | 두 번째 `buildOrderDetail()` 객체 리터럴(REQ-COST-017 이전에는 `OrderDetail`을 완전히 채우는 별개의 헬퍼)에 `shipping_cost: null, korea_warehouse_cost: null` 추가. `tsconfig.app.json`의 `"include": ["src"]`와 `package.json`의 `build: "tsc -b && vite build"` 때문에, 이 파일을 고치지 않으면 REQ-COST-017 적용 즉시 빌드가 깨진다(감사 D2). 이 페이지의 다른 로직(파손/렉번호 검색)은 이 SPEC과 무관하므로 건드리지 않는다. |

---

## 기술적 접근

### 비용 계산 (M2)

1. **입력**: `obj.line_items.all()` — 뷰의 기존 `prefetch_related`(`views.py:41-45`)로 이미 채워진 캐시. 기존 `_compute_margin_usd`의 루프(`:196-199`)가 이미 이 쿼리셋을 순회하며 `confirmed_cost_krw`와 `has_any_confirmed`를 누적한다 — 이 SPEC은 **같은 루프 안에** `total_weight_grams`(`(grams or 0) * (quantity or 0)`의 누적, REQ-COST-002)와 `total_book_count`(`(quantity or 0)`의 누적, REQ-COST-004)를 추가로 누적한다. 두 값 모두 라인아이템의 `confirmed_price` 유무와 무관하게(즉 `has_any_confirmed` 조건 밖에서) 누적해야 한다 — AC-COST-005가 이를 판별한다.
2. **배송비**: 루프 종료 후 `shipping_cost_usd = SHIPPING_COST_USD_PER_KG * total_weight_grams / Decimal("1000")`(REQ-COST-003). 정수 `total_weight_grams`를 `Decimal`로 변환해 곱한다.
3. **한국창고비**: 루프 종료 후 `total_book_count == 0`이면 `korea_warehouse_krw = Decimal("0")`(REQ-COST-006), 그렇지 않으면 `korea_warehouse_krw = KOREA_WAREHOUSE_BASE_KRW + KOREA_WAREHOUSE_PER_BOOK_KRW * max(total_book_count - 1, 0)`(REQ-COST-005). `max(total_book_count - 1, 0)`은 `total_book_count >= 1`인 분기에서는 항상 `total_book_count - 1`과 같으므로(음수가 될 수 없음) 사실상 방어적 표현이다 — 0-분기를 **먼저** 체크하는 순서가 REQ-COST-006을 성립시키는 핵심이다(AC-COST-008이 이 순서 누락을 판별).
4. **환산**: 게이트를 통과한 경우(`er`이 `None`이 아님) `korea_warehouse_usd = korea_warehouse_krw / er.rate`(REQ-COST-007) — `confirmed_cost_usd` 환산(`:203`)과 동일한 `er.rate`를 재사용한다. 신규 환율 조회를 만들지 않는다.
5. **마진**: `margin_usd = total_price_usd - confirmed_cost_usd - shipping_cost_usd - korea_warehouse_usd`(REQ-COST-008). 양자화는 오늘과 동일하게 `get_margin_amount`/`get_margin_rate`에서만 수행한다(`:212,222-224`) — 설계 결정 B.
6. **반환 묶음**: 헬퍼는 `margin_usd`, `total_price_usd`, `shipping_cost_usd`, `korea_warehouse_usd`, `total_weight_grams`를 이름별로 구분해 반환한다(REQ-COST-019) — 5개 게터가 각자 필요한 값만 골라 쓰고, 공통으로 양자화(`Decimal("0.01")`, `ROUND_HALF_UP`)한다. `total_weight_grams`는 정수이므로 양자화하지 않는다(REQ-COST-013).
7. **None 게이트**: 헬퍼가 `None`을 반환하면(환율 없음, REQ-COST-009 / 확정 매입가 전무, REQ-COST-010) 5개 게터 전부 `None`을 반환한다 — 설계 결정 D.
8. **메모이제이션(REQ-COST-015)**: 위 1~7단계 전체가 **동일 `obj`에 대해 요청당 최대 1회만 실행**되도록, 헬퍼 진입부에서 이미 계산된 결과가 있으면 그것을 재사용하고 없으면 계산 후 저장한다. 5개 게터 모두 이 캐시를 거쳐 호출해야 하며, 캐시를 건너뛰고 헬퍼 본문을 직접 재실행하는 경로가 있으면 안 된다(감사 D5).

**구현자를 위한 이름 제안(강제 아님)**: 확장된 헬퍼의 이름은 `_compute_margin_usd`를 유지해도 되고(반환 형태만 확장), `_compute_cost_breakdown` 같은 새 이름으로 대체해도 된다 — `spec.md`는 이를 규정하지 않는다. 다만 헬퍼가 하나뿐이어야 한다는 것(REQ-COST-019), 라인아이템 순회가 하나뿐이어야 한다는 것, 그리고 헬퍼 자체가 주문당 최대 1회만 실행되어야 한다는 것(REQ-COST-015)은 강제된다.

**하지 말 것**:
- 5개 게터 중 하나라도 `obj.line_items.all()`을 직접 재순회하거나 `LineItem.objects.filter(order=obj)`류의 신규 쿼리를 발급 — REQ-COST-015 위반, AC-COST-009 (b)가 판별.
- 5개 게터가 메모이제이션 없이 헬퍼를 매번 새로 호출 — REQ-COST-015 위반("주문 직렬화당 최대 1회"), 요청당 `ExchangeRate` 쿼리가 최대 5개까지 늘어난다, AC-COST-009 (c)가 판별(감사 D5).
- `total_weight_grams`/`total_book_count` 누적을 `has_any_confirmed` 조건 안으로 이동 — REQ-COST-002/004 위반, AC-COST-005가 판별.
- `korea_warehouse_krw` 계산에서 0-분기(REQ-COST-006)를 생략하고 `max(total_book_count - 1, 0)` 하나로만 처리 — `total_book_count == 0`일 때 base fee가 잘못 남는다, AC-COST-008이 판별.
- `korea_warehouse_usd` 환산에 `er.rate` 대신 상수(예: `Decimal("1000")`)를 하드코딩 — REQ-COST-007 위반, AC-COST-012가 판별(감사 D4 — 다른 AC는 전부 `rate=1000.00`을 공유해 이 mutation을 잡지 못한다).
- `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams` 노출 필드를 양자화한 뒤 그 양자화된 값을 `margin_usd` 계산에 재대입 — 설계 결정 B 위반(이중 반올림).
- `OrderListSerializer.Meta.fields`에 신규 필드 추가 — REQ-COST-014 위반, AC-COST-010이 판별.

### 테스트 (M1)

- **T1**(AC-COST-001): 단일 라인아이템, `quantity=3, confirmed_price=10000.00, grams=0`, `total_price=100.00, rate=1000.00`. `margin_amount == "67.75"`, `korea_warehouse_cost == "2.25"`, `shipping_cost == "0.00"`, `total_weight_grams == 0` 단정.
- **T2**(AC-COST-002): 동일 총액/환율, 라인아이템 2개(`quantity=2`+`quantity=1`, 각 `confirmed_price=10000.00`). `margin_amount == "67.75"`(T1과 동일값) 단정 — 라인아이템당 base fee 오적용을 잡기 위해 T1과 **반드시 함께** 실행되어야 하는 대조군.
- **T3**(AC-COST-003): 단일 라인아이템, `quantity=3, grams=500, confirmed_price=10000.00`, `total_price=200.00, rate=1000.00`. `total_weight_grams == 1500`, `shipping_cost == "8.18"`, `korea_warehouse_cost == "2.25"`, `margin_amount == "159.58"`, `margin_rate == "79.79"` 단정.
- **T4**(AC-COST-004): 라인아이템 2개(`grams=None` 1개, `grams=0` 1개), `total_price=50.00, rate=1000.00`. `margin_amount == "32.75"`(`not None`) 단정 — 500 에러가 아니라 200 응답 자체가 1차 판별.
- **T5**(AC-COST-005): 확정 라인아이템(`quantity=2, grams=300, confirmed_price=10000.00`) + 미확정 라인아이템(`quantity=1, grams=600, confirmed_price=None`), `total_price=100.00, rate=1000.00`. `total_weight_grams == 1200`, `margin_amount == "71.21"` 단정.
- **T6**(AC-COST-006): T1과 동일 라인아이템 구성이지만 `ExchangeRate` 레코드 없음. 5개 필드(`margin_amount`, `margin_rate`, `shipping_cost`, `korea_warehouse_cost`, `total_weight_grams`) 각각에 대해 **키 존재 단정(`"shipping_cost" in res.data`)과 값이 `None`이라는 단정을 모두** 수행한다(감사 D6 — `res.data.get(...)` 단독 조회는 키 부재와 `None` 값을 구분하지 못해 미구현 코드에서도 통과한다).
- **T7**(AC-COST-007): 유효한 `ExchangeRate` + 라인아이템(`quantity=3, grams=500, confirmed_price=None`). T6과 동일하게 5개 필드 전부 키 존재 + `None` 값 이중 단정. 무게 데이터가 존재해도 게이트가 우선한다는 것이 판별 지점.
- **T8**(AC-COST-008): 라인아이템(`quantity=None, confirmed_price=5000.00, grams=None`), `total_price=50.00, rate=1000.00`. `korea_warehouse_cost == "0.00"`, `margin_amount == "50.00"` 단정.
- **T9**(AC-COST-009): 무관한 주문 1건에 대한 워밍업 요청(`test_spec_018.py:490-492` 선례 — 첫 요청에서만 발생하는 쿼리를 측정 창 밖으로 뺀다) 후, 주문 X(라인아이템 1개)와 Y(라인아이템 5개), 둘 다 전부 확정 + 유효 환율에 대해 `django.test.utils.CaptureQueriesContext`(`test_spec_018.py:40`)로 각각 캡처. (a) `len(ctx_x.captured_queries) == len(ctx_y.captured_queries) == ORDER_DETAIL_QUERY_COUNT`(이 상수는 M1 실행 시점에 실측해 고정 — `test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3` 관례와 동일). (b) 두 컨텍스트 각각에서 `orders_line_item` 정확 매칭(정규식 `orders_line_item(?!_)` 또는 `connection.ops.quote_name("orders_line_item")` — 단순 `"orders_line_item" in sql`은 `orders_line_item_note`까지 세어 정상 구현에서도 2가 된다, 감사 D1) 쿼리 개수가 정확히 1인지 단정. (c) 두 컨텍스트 각각에서 `orders_exchangerate`를 참조하는 쿼리 개수가 정확히 1인지 단정(감사 D5 — 메모이제이션 누락 시 최대 5까지 늘어난다).
- **T10**(AC-COST-010): `GET /api/orders/`(목록) 응답의 첫 항목에 `"shipping_cost"`, `"korea_warehouse_cost"`, `"total_weight_grams"` 키가 없음을 단정(`"margin_amount" not in item` 기존 패턴과 동일).
- **T11**(AC-COST-011, 프론트엔드): `buildOrderDetail({ margin_amount: "159.58", shipping_cost: "8.18", korea_warehouse_cost: "2.25" })`로 렌더링, `screen.getByText(/8\.18 USD/)`와 `/2\.25 USD/` 존재 단정(`shipping_cost="0.00"`은 쓰지 않는다 — `Number("0.00").toLocaleString()==="0"`이라 "0 USD"로 렌더되어 정상 구현에서도 실패한다, 감사 D3). 별도 케이스로 `shipping_cost: null`일 때 "—" 렌더링 단정. 회귀 게이트는 `tsc -b`(`npm run build`)다 — `frontend/tsconfig.json`은 `"files": []`인 솔루션 파일이라 단독 `tsc --noEmit`은 아무것도 체크하지 않는다(감사 D13).
- **T12**(AC-COST-012): 단일 라인아이템, `quantity=3, confirmed_price=12500.00, grams=0`, `total_price=100.00, rate=1250.00`(다른 T와 다른 환율값). `korea_warehouse_cost == "1.80"`, `margin_amount == "68.20"` 단정 — `korea_warehouse_usd` 환산에 `er.rate` 대신 `Decimal("1000")`을 하드코딩하는 mutation은 T1~T11(전부 `rate=1000.00`)을 통과하지만 T12(`rate=1250.00`)에서 `korea_warehouse_cost == "2.25"`(오답)로 실패한다(감사 D4).
- **T13**(AC-COST-013): 단일 라인아이템, `quantity=1, grams=500, confirmed_price=10000.00`, `total_price=50.00, rate=1000.00`. `shipping_cost == "2.73"`(정확값 `2.725`) 단정 — `ROUND_HALF_EVEN`으로 양자화하면 `"2.72"`가 되어 실패한다. T3의 `8.175`/`159.575`는 반올림 자릿수 앞이 홀수라 HALF_UP과 HALF_EVEN이 우연히 같은 값을 내므로 이 mutation을 잡지 못한다(감사 D11).

**공통 픽스처 원칙**: T1~T8, T13은 `rate=1000.00`처럼 나눗셈이 딱 떨어지는 환율을 의도적으로 골라 중간값 반올림 모호성을 없앤다(AC-COST-003/013만 예외적으로 `8.175`/`2.725`의 정확한 반올림 경계를 검증하기 위해 `5.45/1000` 곱셈 자체가 만드는 소수를 그대로 쓴다). T12는 REQ-COST-007을 판별하기 위해 의도적으로 `rate=1250.00`을 쓴다.

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | 노출된 `shipping_cost`/`korea_warehouse_cost`(양자화된 값)를 실수로 `margin_usd` 계산에 재대입해 이중 반올림이 발생한다 | 설계 결정 B가 정확값/노출값을 명확히 분리하도록 지시. T3(AC-COST-003)이 `159.58` vs 부분합 `159.57`의 의도된 불일치를 구체적으로 고정해, 반대로 구현이 두 값을 일치시키려 하면(=재대입 버그) 그 자체가 실패로 드러난다. |
| R2 | 한국창고비 base fee(1250원)를 라인아이템당 적용하는 실수 | T2가 T1과 동일한 값을 기대하도록 설계되어, 단일 라인아이템 픽스처만으로는 드러나지 않는 이 버그를 잡는다. |
| R3 | `total_book_count == 0`일 때 base fee가 잘못 남는다 | REQ-COST-006의 0-분기를 명시, T8이 판별. |
| R4 | 무게/권수 집계가 `has_any_confirmed` 게이트 안으로 잘못 이동해 미확정 라인아이템이 누락된다 | T5가 확정/미확정 혼합 픽스처로 판별. |
| R5 | 신규 필드가 라인아이템별 추가 쿼리를 발생시킨다(N+1) 또는 아이템 수와 무관한 상수 추가 쿼리를 발생시킨다 | T9의 (a)(절대값 고정)/(b)(`orders_line_item` 정확 매칭) 단정이 각각 판별(기술적 접근 절 참조). |
| R6 | 기존 `test_spec_008.py`/`test_spec_009.py`의 기대값을 갱신하지 않아 회귀 실패로 오인된다 | M1에서 5개 테스트 기대값을 최우선으로 갱신하고, 갱신 직후 현재 코드에서 실패함을 확인한 뒤에만 M2로 진행한다. |
| R7 | 5개 게터가 메모이제이션 없이 헬퍼를 독립 호출해 `ExchangeRate` 쿼리가 요청당 최대 5개까지 늘어난다(REQ-COST-015 위반) — 원격 RDS(`us-west-2`) 배포에서 쿼리당 왕복 지연이 누적된다(감사 D5) | REQ-COST-015를 "주문 직렬화당 최대 1회"로 강화(설계 결정 C/F). M2에서 헬퍼 결과를 주문 단위로 메모이즈하도록 명시. T9 (c)가 `orders_exchangerate` 참조 쿼리 수를 정확히 1로 판별. |
| R8 | `OrderListSerializer`에 실수로 신규 필드가 노출된다 | T10이 판별, `git diff`로 `OrderListSerializer` 블록(`:14-36`) 무변경 확인. |
| R9 | `korea_warehouse_usd` 환산에 `er.rate` 대신 상수를 하드코딩해도 T1~T11이 전부 `rate=1000.00`을 공유해 발견되지 않는다(감사 D4) | T12가 `rate=1250.00`으로 REQ-COST-007을 독립 판별. |
| R10 | AC-COST-009 (b)의 쿼리 매칭을 단순 부분 문자열(`"orders_line_item" in sql`)로 구현하면 `LineItemNote.db_table = "orders_line_item_note"`(`models.py:297`)까지 세어 정상 구현에서도 거짓 실패가 난다(감사 D1) | T9 (b)를 정규식(`orders_line_item(?!_)`) 또는 `connection.ops.quote_name(...)` 완전 일치로 구현. |
| R11 | `frontend/src/types/order.ts`에 REQ-COST-017 필드를 추가하는 순간 `SearchTab.test.tsx:47`의 별도 `buildOrderDetail()`이 타입 에러가 되어 빌드가 깨진다(감사 D2) | M2에서 `types/order.ts` 변경과 같은 단계로 `SearchTab.test.tsx`에 `null` 기본값 추가, M4에서 `npm run build` 통과 확인. |
| R12 | AC-COST-006/007을 `res.data.get("shipping_cost")` 관례로 작성하면 키 부재와 `None`을 구분하지 못해 미구현 코드에서도 통과해 RED가 성립하지 않는다(감사 D6) | T6/T7에 `"shipping_cost" in res.data`류의 키 존재 단정을 명시적으로 요구(기술적 접근 절 T6/T7 참조). |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | 확장된 비용 계산 헬퍼 정의부(`serializers.py`, `_compute_margin_usd` 인근) | 무게/권수 집계가 `confirmed_price` 유무와 무관하게(즉 `has_any_confirmed` 조건 밖에서) 전체 라인아이템을 대상으로 한다는 사실(REQ-COST-002/004), `korea_warehouse_krw`의 0-분기가 base fee 오적용을 막기 위한 것이라는 사실(REQ-COST-006), 5개 필드가 이 헬퍼를 공유하는 단일 게이트를 갖는다는 사실(설계 결정 D)을 포함. |
| 검토 후 갱신 | `@MX:ANCHOR`(`serializers.py:142-143`, `OrderDetailSerializer`) | fan-in 사유(OrderDetailView, 테스트 스위트, 프론트엔드 클라이언트)는 이 SPEC과 무관 — 갱신 불필요. 필드 3개 추가는 fan-in을 바꾸지 않는다. |
| `@MX:NOTE` (신규) | 상수 선언부 | 세 상수(`SHIPPING_COST_USD_PER_KG`, `KOREA_WAREHOUSE_BASE_KRW`, `KOREA_WAREHOUSE_PER_BOOK_KRW`)가 SPEC-ORDER-021에서 도입되었고 값 변경 시 이 SPEC의 인수 기준(AC-COST-001~008, 012, 013)의 고정 예시가 함께 깨진다는 경고. |
| `@MX:NOTE` (신규) | 메모이제이션 캐시 지점(헬퍼 진입부) | 5개 게터가 이 캐시를 공유하며, 캐시를 우회하면 요청당 `ExchangeRate` 쿼리가 최대 5개까지 늘어난다는 사실(REQ-COST-015, 감사 D5). |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문은 영어로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 확인 — `serializers.py:141-225`, `views.py:31-45`, `models.py:152-238`, `SearchTab.test.tsx:1-75`을 재확인했다
- [ ] 기존 백엔드·프론트엔드 테스트 스위트와 `npm run build`의 현재 통과 상태를 기록했다

**Done (구현)**

- [ ] `test_spec_008.py`/`test_spec_009.py`의 5개 기대값 갱신 완료, 갱신 직후 현재(무수정) 코드에서 5개 전부 실패함을 확인했다
- [ ] `test_spec_021.py` T1~T13(13개) 전량 통과
- [ ] T1~T5, T8, T12, T13이 신규 필드 부재 상태(되돌린 코드)에서 실패함을 확인했다
- [ ] T6/T7이 `"shipping_cost" in res.data`류의 키 존재 단정을 실제로 포함하며, 되돌린 코드에서 실패함을 확인했다(감사 D6 — `res.data.get(...)` 단독 조회는 되돌린 코드에서도 통과해버려 판별력이 없다)
- [ ] T2가 "라인아이템당 base fee" mutation에서 실패함을 확인했다(`margin_amount != "67.75"`가 된다)
- [ ] T8이 "0-분기 생략" mutation에서 실패함을 확인했다(`korea_warehouse_cost != "0.00"`가 된다)
- [ ] T5가 "무게/권수 집계를 확정 게이트 안으로 이동" mutation에서 실패함을 확인했다
- [ ] T12가 "`er.rate` 대신 `Decimal(\"1000\")` 하드코딩" mutation에서 실패함을 확인했다(`korea_warehouse_cost != "1.80"`가 된다) — T1~T11만으로는 이 mutation이 통과해 버림을 재확인했다(감사 D4)
- [ ] T13이 "`ROUND_HALF_EVEN`" mutation에서 실패함을 확인했다(`shipping_cost != "2.73"`가 된다) — T3만으로는 이 mutation이 통과해 버림을 재확인했다(감사 D11)
- [ ] T9 (a)의 절대값(`ORDER_DETAIL_QUERY_COUNT`)을 실측해 고정했다(추측값 아님)
- [ ] T9 (b)가 "라인아이템 재쿼리" mutation에서 실패함을 확인했다(`orders_line_item` 정확 매칭 쿼리가 2개가 된다) — 정규식/`quote_name` 매칭을 실제로 쓰는지 재확인했다(감사 D1)
- [ ] T9 (c)가 "메모이제이션 누락" mutation(5개 게터가 헬퍼를 캐시 없이 독립 호출)에서 실패함을 확인했다(`orders_exchangerate` 참조 쿼리가 5개가 된다) — (a)의 절대값도 이 mutation에서 함께 어긋남을 재확인했다(감사 D5)
- [ ] T9에 워밍업 요청이 포함되어 있다(감사 D10)
- [ ] T10이 통과 상태에서 `git diff`로 `OrderListSerializer` 블록(`:14-36`) 무변경을 확인했다
- [ ] `git diff --stat backend/order/models.py backend/order/migrations/`가 비어 있다(REQ-COST-018 인접 — 모델 무변경)
- [ ] T11(프론트엔드) 통과, `shipping_cost="8.18"` 픽스처(`"0.00"` 아님, 감사 D3) + `null` 폴백 케이스 포함
- [ ] `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx`가 `null` 기본값 추가 후에도 통과한다(감사 D2)
- [ ] 기존 프론트엔드 테스트 스위트(`OrderDetailPage.test.tsx`, `SearchTab.test.tsx` 포함 전량) 무수정 통과
- [ ] `npm run build`(`tsc -b`) 통과 — `tsc --noEmit` 단독 실행이 아니다(감사 D13)
- [ ] ESLint/TypeScript 신규 에러 0, 백엔드 `ruff`/`black` 신규 이슈 0

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001 | 코드 리뷰 (상수 존재) |
| 002 | T3, T4, T5 |
| 003 | T3, T13 |
| 004 | T1, T2, T5 |
| 005 | T1, T2 |
| 006 | T8 |
| 007 | T12 |
| 008 | T1, T2, T3, T5 |
| 009 | T6 |
| 010 | T7 |
| 011 | T1, T3, T13 |
| 012 | T1, T3 |
| 013 | T1, T3 |
| 014 | T10 |
| 015 | T9 |
| 016, 017 | T11 |
| 018 | `git diff` — 신규 필드 없음 |
| 019 | 코드 리뷰 — 단일 헬퍼 구조 |

---

## 관련 참조 구현

- **기존 마진 계산 전체**: `backend/order/serializers.py:176-225`(`_get_exchange_rate`, `_compute_margin_usd`, `get_margin_amount`, `get_margin_rate`)
- **뷰 레벨 prefetch 근거**: `backend/order/views.py:38-45`
- **LineItem 무게/수량/원가 필드**: `backend/order/models.py:169-195`(`order` FK `:169`, `quantity` `:176`, `confirmed_price` `:195`), `:181`(`grams`)
- **쿼리 카운트 관례 선례**: `backend/order/tests/test_spec_018.py:40`(`CaptureQueriesContext` 임포트), `:64`(`UNORDERED_ENDPOINT_QUERY_COUNT = 3` 절대값 고정 관례), `:483-549`(캡처·비교·SQL 텍스트 매칭 패턴), `:490-492`(워밍업 요청)
- **`LineItem`/`LineItemNote` 테이블명**: `backend/order/models.py:240-241`(`db_table = "orders_line_item"`), `:296-298`(`LineItemNote.Meta`, `db_table = "orders_line_item_note"` — AC-COST-009 (b)의 부분 문자열 충돌 원인), `:507`(`ExchangeRate.Meta`, `db_table = "orders_exchangerate"`)
- **프론트엔드 마진 표시 원본**: `frontend/src/pages/OrderDetailPage.tsx:505-527`(특히 `:515-517`의 `Number(...).toLocaleString()` 포맷 — AC-COST-011 픽스처가 `"8.18"`이어야 하는 근거)
- **프론트엔드 타입 원본**: `frontend/src/types/order.ts:168-197`(`OrderDetail`, `margin_amount`/`margin_rate` `:196-197`)
- **프론트엔드 테스트 관례 원본**: `frontend/src/pages/OrderDetailPage.test.tsx:1-95`(모킹·렌더 헬퍼, 픽스처 빌더)
- **두 번째 `OrderDetail` 구성 지점(회귀 대상)**: `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx:47`(`buildOrderDetail()`), 빌드 게이트 근거는 `frontend/tsconfig.app.json`의 `"include": ["src"]`와 `frontend/package.json:8`의 `"build": "tsc -b && vite build"`
- **환율 조회 중복 허용 전례(이 SPEC이 정정한 부분)**: `.moai/specs/SPEC-ORDER-009/spec.md:204`(NOTE) — 2회는 수용했으나 5회로의 확장은 이 SPEC(설계 결정 F)이 기각했다
