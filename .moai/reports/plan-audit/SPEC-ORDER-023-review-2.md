# SPEC Review Report: SPEC-ORDER-023

Iteration: 2/3
Verdict: **FAIL** (차단 결함 1건 + 고위험 결함 3건 — 단, iteration 1의 C1/C2/C3·H1~H6은 전부 실질 해소)
Overall Score: 0.76

Reasoning context ignored per M1 Context Isolation. 이 감사는 `.moai/specs/SPEC-ORDER-023/`의 세 문서(v1.1.0)와
저장소 소스만 사용했다. `review-1.md`는 **재검증 대상 주장**으로만 취급했고 ground truth로 채택하지 않았다 —
실제로 review-1이 제시한 행번호 2건(L1, L6)이 이 세션의 직접 확인에서 **오류**로 판명되었다(아래 "Regression
Check / 판정 뒤집기" 참조). 저자의 v1.1.0 HISTORY 주장(베이스라인 6, 임시 파일 삭제, Django 5.2.17 행번호,
lookback 반려)은 모두 문서를 근거로 채택하지 않고 소스·`git status`·poetry 가상환경에서 직접 재현했다.
36개 AC 전량에 대해 mutation을 독립 구성했고, 물류상태 우선순위 사슬은 문서 서술을 신뢰하지 않고
(logistics_status × shipped_quantity × quantity × sku) 조합 위에서 처음부터 재유도했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: `grep -cE '^\*\*REQ-OLIST-[0-9]{3}[a-z]?\*\*' spec.md` = **37**,
  `sort | uniq -d` 결과 없음. 본번호 001~034 연속·결번 없음, 하위번호 3개(011a/022a/024a)만 접미사 사용,
  3자리 패딩 일관. AC도 동일: spec.md 정의 36개, `acceptance.md` `### AC-OLIST-` 헤더 36개로 **정확히 일치**,
  중복 없음. spec.md:327의 "37개 요구사항 중 36개가 36개 인수 기준으로 커버"는 산술적으로 정확하다.

- **[PASS] MP-2 EARS format compliance**: v1.0.0의 퇴행(AC 27개가 한국어 시나리오 서술문)이 **해소되었다.**
  36개 AC 전량을 개별 확인한 결과 모두 굵게 표시한 EARS 연결어를 포함한 완전한 문장이다 — 예:
  spec.md:206 "**While** an order has a single trackable line item with `logistics_status='shipped'` **and**
  `shipped_quantity == quantity` …, the system **shall** set `logistics_display` to `"shipped"`.",
  spec.md:224 "**If** an order has zero trackable line items …, **then** the response item **shall** contain
  the key … **and** its value **shall** be `null`." 37개 REQ도 전부 유효한 EARS다.
  (라벨 불일치 7건은 아래 L1 — 패턴 자체는 5종 중 하나에 정확히 대응하므로 MP-2 위반이 아니다.)

- **[PASS] MP-3 YAML frontmatter validity**: spec.md:1-11 — `id: SPEC-ORDER-023`(string), `version: 1.1.0`(string),
  `status: draft`(string), `created_at: 2026-08-16`(ISO date), `priority: High`(string),
  `labels: [order, list, margin, logistics, purchase-status, frontend, backend]`(array). 6개 필수 필드 전부
  존재·타입 정확. 동반 문서도 동기화(plan.md:1-7, acceptance.md:1-7 — 둘 다 `version: 1.1.0`).

- **[N/A] MP-4 Section 22 language neutrality**: Django 백엔드 + React 프론트엔드로 범위가 한정된 단일
  프로젝트 SPEC. 다국어 툴링 주장 없음. 자동 통과.

---

## Half 1 — iteration 1 결함의 실제 해소 여부

각 항목은 **문서의 자기 주장이 아니라 소스와 대조**해 판정했다.

### 차단 결함 (C1~C3)

| ID | 판정 | 근거 |
|---|---|---|
| **C1** (REQ-OLIST-022 자기모순 + 검출 불가) | **해소** | REQ-OLIST-022(spec.md:150)가 "이 SPEC 이전 대비 증가 없음"→"페이지 크기·주문 수에 대해 O(1)"로 재작성됨. REQ-OLIST-022a(spec.md:152) 신설로 "베이스라인 6 + 정확히 1"을 명시. 목표 5(spec.md:42)도 함께 정정되어 배치 쿼리 1회를 "금지 대상이 아니라 의도적 대가"로 규정. AC-OLIST-021(spec.md:258, acceptance.md:260)이 절대값 **7**을 단정. 단, REQ-OLIST-022a 자체에 새 엣지 결함이 있다 → **H3-new**. |
| **C2** (규칙 1↔2 우선순위 미검증) | **해소** | AC-OLIST-006 Given이 `logistics_status='shipped', quantity=5, shipped_quantity=5`로 교체됨(spec.md:206, acceptance.md:79). `purchase_order_views.py:3411/3456/3972`를 직접 확인한 결과 `shipped_quantity >= effective_quantity`일 때만 `shipped`로 전이하므로 이 픽스처가 프로덕션 실제 상태이며, 규칙 2를 먼저 평가하는 mutation이 `partial_shipped`를 반환해 실패한다. AC-OLIST-022(acceptance.md:269)의 비교 대상 주문에도 동일 조건 적용. review-1이 지적한 "규칙 2와 3이 동시 성립 가능한 유일한 조합"이라는 거짓 문장도 세 문서에서 삭제 확인. |
| **C3** (`Order.status` 패스스루가 정상 구현을 깨뜨림) | **해소 — 잔존 의존 0건** | 세 문서에서 `Order.status`/`obj.status` 언급 37건을 전수 확인했다(spec 17 / plan 13 / acceptance 7). **전부 금지·부정 서술이며 어떤 계산·필터·픽스처도 이 컬럼에 의존하지 않는다.** 특히 (a) 필터 설계(plan.md:52-64)는 `trackable_qs = LineItem.objects.filter(order=OuterRef("pk"), sku__isnull=False)` 기반 `Exists` 8종만 쓰고 `Order.status`를 조건에 넣지 않는다, (b) AC-OLIST-008(acceptance.md:97)/AC-OLIST-013(:142)의 Given이 `Order.status`를 명시적으로 "설정할 필요 없음"으로 재작성되었다, (c) 범위 델타(spec.md:76)·Exclusions(spec.md:369)·plan.md:104가 `Order.status`/`ready_to_ship`/`_recompute_order_aggregates`를 무수정으로 못박는다. REQ-OLIST-011(uniform passthrough)/011a(non-uniform→`partial`) 신설도 확인. |

### 고위험 결함 (H1~H6)

| ID | 판정 | 근거 |
|---|---|---|
| **H1** (`is None` 단정이 미구현 코드에서 통과) | **해소** | AC-OLIST-012/016/018/018a/018b 전부 "키 존재 **그리고** 값이 null" 이중 단정으로 재작성(spec.md:224/237/245/247/250, acceptance.md:135/181/211/219/228). plan.md:31, :220 Done 체크리스트에도 `"key" in item` 강제 조항 추가. SPEC-ORDER-021 D6 재발 방지 완료. |
| **H2** (6개 필터 값 중 1개만 검증) | **부분 해소 → H1-new** | AC-OLIST-022a~e 5건 신설로 6개 값 전량에 AC가 생겼다. 그러나 022b/022c/022e의 Given이 "그 외 상태의 주문 1건 이상"으로 **비특정**이라 핵심 mutation을 잡지 못할 수 있다(아래 H1-new). 022a/022d만 데이터셋을 열거한다. |
| **H3** (null 원인 3개 중 1개만 검증) | **해소** | AC-OLIST-018a(환율 전무, HTTP 200 + null — `IndexError` mutation 판별), AC-OLIST-018b(`total_price="0.00"`) 신설. REQ-OLIST-017(spec.md:138)이 `shopify_created_at` null(`serializers.py:245`)과 `total_price` null(`serializers.py:322`)까지 열거하도록 확장됨 — 두 인용 모두 소스에서 직접 확인. |
| **H4** (발주 경로 trackable 필터 미검증) | **해소** | AC-OLIST-011(spec.md:220, acceptance.md:123-127)에 `purchase_display == "ordered"` 단정 추가. trackable을 `in_stock`, non-trackable을 모델 기본값 `unordered`(`models.py:193` 확인)로 두어 필터 누락 시 `"unordered"` 오답이 나오도록 설계 — mutation 판별력 확인. |
| **H5** (7번째 라벨 `received` 누출) | **해소 — 재유도로 확인** | 규칙 4가 `received`를 통과시킬 수 있는 경로를 처음부터 재구성했다. uniform-`received`인 주문은 (i) 어떤 항목이든 `shipped_quantity>0`이면 규칙 2 → `partial_shipped`, (ii) 아니면 규칙 3 → `outbound_scheduled`. **두 경우 모두 규칙 4에 도달하지 않는다.** 따라서 `logistics_display`의 치역은 REQ-OLIST-024의 6개 + `null`로 닫힌다. `logisticsStatusLabels.ts:14`의 `received: '입고'`는 이 SPEC에서 구조적으로 도달 불가. |
| **H6** (`getDisplayStatus` 통째 재사용이 REQ-006 위반) | **해소** | 목표 2(spec.md:39)·결정 3(spec.md:48)이 "앞 3개 분기(`:82-85`)만"으로 한정되고 "라벨 맵(`:86-93`)은 재사용하지 않는다"를 명시. 인용 검증: `OrdersPage.tsx:82` refunded→취소, `:83` partially_refunded→부분취소, `:85` has_refund→부분취소, `:86-93` 결제상태 맵 — **행번호 정확**. AC-OLIST-004가 `queryByTestId('cancel-badge')` 요소 부재로 강화됨. plan.md:76이 `getCancelBadge` 신설 + `getDisplayStatus` 삭제를 지시. |

### Medium / Low

| ID | 판정 | 근거 |
|---|---|---|
| M3 (부분문자열 함정) | 해소 | AC-OLIST-002가 `data-testid` 스코프 + 정확 문자열 비교로 전환(spec.md:195). (acceptance.md:39의 판별력 서술 자체는 원래 M3 논지와 어긋나게 재작성되었으나 단정 문구는 올바르다 — L 참조) |
| M4 (라벨 중복 매칭) | 해소 | AC-OLIST-026이 `aria-label="물류상태 필터"` 셀렉트 스코프, AC-OLIST-027이 `within(row)` 행 스코프로 명시(spec.md:282,284). |
| **M6 (배치 로드 상한)** | **해소 — 저자 논거 타당** | 저자의 lookback 반려는 **옳다.** `Order.shopify_created_at`은 `null=True`인 `DateTimeField`(`models.py:77`)이고 마이그레이션 데이터가 임의로 오래될 수 있으므로, `effective_date__gte` 하한을 두면 윈도 밖의 유일 레코드를 놓쳐 REQ-OLIST-020("`_get_exchange_rate`가 해석했을 값과 동일")을 위반한다 — `_get_exchange_rate`(`serializers.py:249-251`)에는 하한이 없다. 채택안(`values_list("effective_date","rate")`)의 무한 증가 안전성도 성립한다: `ExchangeRate.effective_date`는 `unique=True`(`models.py:501`, 직접 확인)라 하루 1행이므로 10년치도 ~3,650행 × 2컬럼(DateField+DecimalField)에 불과하다. 요구사항은 구현 가능하며 상한 없이도 안전하다. |
| M7 (Django 버전 근거) | **해소 — 저자 판정이 옳다** | 아래 "판정 뒤집기" 참조. |
| M8 (SPEC-021 Exclusion supersede) | 해소 | spec.md:87에 명기. 인용 재확인: SPEC-ORDER-021 `spec.md:373` = "`OrderListSerializer`(목록 API)에 비용/마진 필드를 노출하지 않는다", `:61` = `[EXISTING]` — **정확**. `test_spec_021.py:321-334`의 T10이 `shipping_cost`/`korea_warehouse_cost`/`total_weight_grams` 3키만 금지함도 직접 확인(`margin_rate` 미언급 → T10은 깨지지 않는다). |
| M9 (`order_cancelled` 분류) | 해소(문서) | 명시적 가정 4(spec.md:66) 신설. `purchase_order_views.py:172-178`(status 집계, 제외 없음)과 `:187-199`(`non_cancelled` 제외)를 직접 확인 — 인용 정확. 다만 AC 부재는 남는다(L4-new). |
| M10 (AC-024 이진 단정 아님) | 해소 | AC-OLIST-024(spec.md:278)가 "정확히 1건" 카운트 단정으로 재작성. |
| M1 (AC의 EARS 퇴행) | 해소 | MP-2 참조. |
| M2 (마진 반올림 미판별) | **해소 — 손계산으로 확인** | 아래 "반올림 픽스처 독립 검증" 참조. |
| M5 (AC-025 자동화 불가) | 해소 | 자동화 단정(응답 키 집합 + `test_spec_021.py` 재통과)과 수동 게이트(`git diff`)로 분리(spec.md:280, acceptance.md:342, plan.md:87). |
| L2 ("T1~T22") | 해소 | `grep -n "^def test_"` 결과 21개, T10 다음이 T12 — **T11 결번 확인**. 세 문서 전부 "T1~T10, T12~T22(21개)"로 정정됨. |
| L3 ("sync 6개") | 해소 | `OrdersPage.test.tsx`의 `it(`는 `:85, 94, 104, 118, 132, 145, 159`로 **7개** — acceptance.md:391의 정정이 정확. |
| L4 (EARS 라벨) | **부분 해소 → L1-new** | REQ-OLIST-033/034는 Unwanted→Ubiquitous로 교정됨(spec.md:182,184). 그러나 AC 쪽 라벨 불일치 7건이 남았다. |
| L5 (AC-007 mutation 서술) | 해소 | 재설계로 서술이 참이 되었다 — 두 항목이 uniform `outbound_scheduled`이므로 규칙 4가 그 값을 통과시킨다. `Order.status` 전제가 사라졌다. |
| **L7 (타임존/`.date()`)** | **미해소** | plan.md:144-146은 `max_date`를 "`shopify_created_at`이 not null인 것들의 최댓값"으로만 규정하고 `.date()` 변환 시점·`USE_TZ` 처리를 정하지 않는다. `_get_exchange_rate`(`serializers.py:248`)는 `obj.shopify_created_at.date()`를 쓰므로 UTC 날짜 기준이다. REQ-OLIST-020이 "동일한 값"을 [HARD]로 요구하는데 자정 경계 케이스 AC가 없다 → **M5-new**. |
| L8 (AC-016 하위 케이스) | 해소 | acceptance.md:178-181이 (a) 전부 `sku=None`, (b) 라인아이템 0개 두 케이스를 모두 요구. |

### 저자 주장 독립 검증

**1) 임시 테스트 파일 삭제 — 확인됨.**
`git status --porcelain -- backend/` = **빈 출력**(수정·미추적 모두 없음). 저장소 전체에서 `zzz`/`tmp`/`scratch`
패턴 미추적 파일도 0건. 남은 잔여물 없음.

**2) 베이스라인 6 / 사후 7 — 분해가 정확하다(도출 검증).**
소스에서 직접 재구성했다.
- `OrderListView`(`views.py:155-159`)는 `authentication_classes = [JWTAuthentication]` 단독 → `get_user`가 요청당 `accounts_adminuser` 1회. **(1)**
- `OrderPagination`(`views.py:151-152`, `PageNumberPagination`, `page_size = 50`) → `Paginator.count` COUNT(*) **(2)** + 페이지 슬라이스 본문 SELECT **(3)**.
- `get_queryset`(`views.py:162`)의 `prefetch_related("refunds", "line_items", "customer")` → **(4)(5)(6)**.
- `ATOMIC_REQUESTS`는 저장소 어디에도 설정되어 있지 않다(`grep -rn ATOMIC_REQUESTS backend/` = 0건) → SAVEPOINT가 측정 창에 섞이지 않는다. `test_spec_018.py:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`(= JWT 1 + 뷰 2)이 이 전제와 정합한다.
→ **베이스라인 6은 정확하다.**
- `customer`가 forward FK(`Order.customer`)임에도 `prefetch_related`에 들어 있다는 지적은 사실이나 **결론을 바꾸지 않는다**: Django는 forward FK prefetch도 별도 `WHERE id IN (...)` 쿼리 1회를 발급하며, 모든 `customer_id`가 NULL이면 `In.process_rhs`가 `EmptyResultSet`을 던져 쿼리를 아예 생략한다. 저자의 "고객 없으면 5로 줄어든다"(spec.md:350, plan.md:171)는 서술과 AC-OLIST-021의 "고객 연결 주문만 사용" 픽스처 제약은 **옳다.**
- 사후 추가분: `logistics_display`/`purchase_display`는 prefetch된 `obj.line_items.all()`만 순회(추가 0), `margin_rate`는 배치 `ExchangeRate` 1회. → **총 7이 맞다.** plan.md:159-169의 7행 분해표도 이 도출과 일치한다.
- 유일한 미해소 지점은 절대상수 자체가 아니라 REQ-OLIST-022a의 **문언**이다(H3-new).
- (원격 RDS 공유 DB 제약상 pytest 재실행은 하지 않았다. 위는 소스 도출에 의한 검증이며, plan.md:27/:208이 M0 재실측과 불일치 시 SPEC 갱신을 강제하는 것은 적절한 안전장치다.)

**3) Django `count()` 행번호 — 저자가 옳고 review-1이 틀렸다.**
- poetry 락파일: `backend/poetry.lock:168` = `version = "5.2.17"` — **행번호까지 정확**.
- poetry 가상환경(`.../virtualenvs/scm-v2-backend-GSYY1g0K-py3.12`)의 `django/__init__.py` = `VERSION = (5, 2, 17, 'final', 0)`. 그 안에서 `def count(self):` = **595행**, `def exists(self):` = **1293행**, `related_descriptors.py`의 역방향 매니저 `get_queryset` = **755행**(`_prefetched_objects_cache` 접근이 765행). spec.md:345-346·plan.md:268의 인용 **3건 전부 정확**.
- 시스템 전역 인터프리터(`.../Programs/Python/Python312`)의 Django는 **5.1.6**이고 그곳의 `def count(self):`는 **609행**이다.
- 즉 **608은 5.1.6에서도 5.2.17에서도 재현되지 않는다.** review-1의 드리프트 #1(L1)은 오류였고, v1.0.0의 "609"는 5.1.6 기준으로는 맞았다. 저자의 반박이 전면 타당하다.

**4) lookback 반려 — 논거 성립**(위 M6 행 참조).

### 반올림 픽스처 독립 검증 (AC-OLIST-017a)

`grams=500, quantity=1, confirmed_price="10005.00", rate="1000.00", total_price="100.00"`을
`_compute_cost_breakdown_uncached`(`serializers.py:298-360`)에 손으로 대입했다.

| 항목 | 정확값(비양자화) | 개별 양자화값 |
|---|---|---|
| `confirmed_cost_usd` = 10005/1000 | 10.005 | "10.01" |
| `shipping_cost_usd` = 5.45 × 500 / 1000 | 2.725 | "2.73" |
| `korea_warehouse_usd` = 1250/1000 (book_count=1 → `max(0,0)`) | 1.25 | "1.25" |

- 정답: `margin_usd = 100 − 10.005 − 2.725 − 1.25 = 86.020` → `margin_rate = 86.020/100×100` → **"86.02"**
- 재합산 mutation: `100 − 10.01 − 2.73 − 1.25 = 86.01` → **"86.01"**
- **두 값이 정확히 1센트 갈린다 → AC-OLIST-017a는 장식이 아니라 진짜 판별력이 있다.**
- 교차 확인: `test_spec_021.py:411-415`의 `order_x15` 픽스처가 `quantity=1, confirmed_price=10005.00, grams=500`으로 **동일**하며, `:443` 주석이 `margin_amount="86.02"`를 독립적으로 못박는다. spec.md:242의 "AC-COST-015/016과 동일 픽스처"라는 주장도 사실이다.

### 인용 재검증 (v1.0.0 이후 신규/변경분 전량)

| 인용 | 검증 |
|---|---|
| `OrdersPage.tsx:82-85`(앞 3분기), `:86-93`(라벨 맵) — 신규 | 82 refunded, 83 partially_refunded, 84 주석, 85 has_refund / 86-92 맵 + 93 return — **정확** |
| `models.py:207`(logistics_status default) — 신규 | 204-208 필드, 207 `default="not_shipped"` — **정확** |
| `models.py:193`(purchase_status default) | 190-194 필드, 193 `default="unordered"` — **정확** |
| `models.py:49-54`(Order.status), `:501`(effective_date unique), `:507`(db_table) | 49 `status = models.CharField(`, 501 `effective_date = models.DateField(unique=True)`, 507 `db_table = "orders_exchangerate"` — **정확** |
| `shopify_orders.py:130-143` / `:140-143` — 변경 | 130 `update_or_create`, 133 `defaults={`, 140-143 "status intentionally excluded" 주석 4행 — **정확**. 단 plan.md:262는 같은 대상을 `:130-147`로 인용(불일치, L6-new) |
| `purchase_order_views.py:172-178`, `:187-199`, `:176-177`, `:160-161`, `:123-209` | 172 주석 → 178 `status_whens.append`; 187 `non_cancelled = [...]` → 199 `)`; 176-177 `len(statuses)==1`; 160-161 `sku__isnull=False`; 123 `def` — **5건 전부 정확** |
| Django 5.2.17 `query.py:595-606`/`:1293-1299`, `related_descriptors.py:755-770` | **3건 전부 정확**(위 참조) |
| `poetry.lock:168` | `version = "5.2.17"` — **정확** |
| SPEC-021 `spec.md:373`, `:61`, `test_spec_021.py:321-334` | **3건 전부 정확** |
| `serializers.py:245`(shopify_created_at 게이트), `:322`(total_price or "0") — 신규 | 245 `if not obj.shopify_created_at:`, 322 `Decimal(str(obj.total_price or "0"))` — **정확** |
| `OrdersPage.test.tsx:85,94,104,118,132,145,159` | `it(` 7개 위치 **전부 일치** |
| `views.py:151-152,155-218,161-218,162,171-173,186-191` | **전부 정확**(재확인) |
| `OrdersPage.tsx:203-214, 229-239, 278-289, 280-287, 284-285, 293, 300-348, 306-308` | 203 결제상태 `<select>`(207 aria-label), 229 출고상태(233 aria-label), 278 `<thead>`~289, 280-287 `<th>` 8개, 293 `colSpan={8}`, 300 map~348, 306-308 주문번호 `<td>` — **전부 정확** |

**날조 인용 0건.** 이 SPEC의 인용 무결성은 2회 연속 강점이다.

---

## Half 2 — 재설계가 새로 깨뜨린 것

### 우선순위 사슬 재유도 (전수성·배타성)

trackable 집합 T(`sku is not null`) 위에서 규칙을 처음부터 재구성했다.

| # | 조건 | 결과 |
|---|---|---|
| 1 | \|T\|≥1 ∧ ∀t: ls=shipped | `shipped` |
| 2 | ¬1 ∧ ∃t: shipped_quantity>0 | `partial_shipped` |
| 3 | ¬1 ∧ ¬2 ∧ ∀t: ls=received | `outbound_scheduled` |
| 4 | ¬1~3 ∧ \|{ls}\|=1 | 그 값 |
| 4a | ¬1~3 ∧ \|{ls}\|≥2 | `partial` |
| 0 | \|T\|=0 | `null` |

- **배타성**: 각 규칙이 선행 규칙의 부정으로 가드되어 있어 중첩 없음 ✓
- **치역 닫힘**: 규칙 4가 `shipped`를 통과시킬 수 없고(규칙 1이 선점), `received`도 통과시킬 수 없음(규칙 2 또는 3이 선점) → 출력은 {shipped, partial_shipped, outbound_scheduled, not_shipped, shipment_confirmed, partial} ∪ {null}. REQ-OLIST-024의 6개와 정확히 일치 ✓ (H5 구조적 해소 확인)
- **전수성**: |T|≥1이면 4/4a가 나머지를 전부 흡수 ✓
- **그러나 |T|=0에서 겹침이 발생한다 → C1-new (아래).**

### 표시(Python) ↔ 필터(SQL) 등가성

plan.md:52-64의 `Exists` 조합을 6개 값 전부에 대해 위 표와 대조했다.

| 값 | SQL 조건 | Python 규칙 | 판정 |
|---|---|---|---|
| shipped | `all_shipped` | 1 | ✓ |
| partial_shipped | `¬all_shipped ∧ any_partial` | 2 | ✓ (`any_partial`이 `has_trackable`을 함의) |
| outbound_scheduled | `¬all_shipped ∧ ¬any_partial ∧ (all_received ∨ all_outbound_scheduled)` | 3 ∨ 4(outbound) | ✓ (두 이접항은 \|T\|≥1에서 상호배타) |
| not_shipped | 앞 3개 부정 ∧ `all_not_shipped` | 4(not_shipped) | ✓ |
| shipment_confirmed | 앞 3개 부정 ∧ `all_shipment_confirmed` | 4(shipment_confirmed) | ✓ |
| partial | 앞 3개 부정 ∧ `¬all_not_shipped ∧ ¬all_shipment_confirmed ∧ ¬all_outbound_scheduled ∧ has_trackable` | 4a | ✓ (uniform이면 6개 `all_*` 중 정확히 하나가 참이므로 여집합이 곧 non-uniform) |

**결론: SQL 표현은 완전하고 등가이며, 행별 쿼리 없이 8개 상관 `Exists`로 단일 문장 안에 표현 가능하다.**
`Order.status` 제거가 필터 경로에도 빠짐없이 반영되었다. 설계 결정 B(spec.md:335)와 REQ-OLIST-023의
"derived logistics_display equals the supplied value"라는 선언적 결속은 v1.0.0 대비 실질적 개선이다.

다만 **AC가 여섯 값 모두에서 두 경로의 발산을 잡지는 못한다** → H1-new, H2-new.

### 비목표 재유입 점검

- 마진 정렬/범위 필터: REQ 어디에도 없음 ✓ (제약사항 spec.md:354, Exclusion :362와 일관)
- 발주상태 필터: REQ-OLIST-026은 물류상태 드롭다운만 규정 ✓, plan.md M4도 `logistics_display` 단일 파라미터 ✓
- 부분출고 사유 분류: 어떤 REQ도 사유 필드를 만들지 않음 ✓
- `OrderDetail` 변경: REQ-OLIST-033 + 범위 델타 `[EXISTING]` + Exclusion + plan.md:101 "순수 추출 리팩터링만" ✓
- `LOGISTICS_STATUS_CHOICES` enum 확장 금지 Exclusion(spec.md:367) 유지 ✓
- **밀수 없음.** 유일한 신규 범위는 REQ-OLIST-024a(허용 외 값 fail-open)이며 이는 필터 요구사항의 정당한 보완이다.

---

## Defects Found

### Critical

**C1-new. spec.md:118 (REQ-OLIST-010) ⊥ spec.md:124 (REQ-OLIST-012) — 빈 trackable 집합에서 두
요구사항이 정면으로 모순되며, SPEC을 문자 그대로 구현하면 SPEC 자신의 AC-OLIST-012가 실패한다.**

REQ-OLIST-008(spec.md:114)은 `"While an order has **at least one trackable line item** and every trackable
line item's logistics_status equals shipped"`로 **존재 가드를 명시**한다. 그런데 재작성된
REQ-OLIST-010(spec.md:118)에는 그 가드가 없다:

> "While neither REQ-OLIST-008 nor REQ-OLIST-009 holds for an order and **every one of its trackable line
> items** has `logistics_status` equal to `"received"`, the system shall set `logistics_display` to
> `"outbound_scheduled"`."

trackable 라인아이템이 **0개**인 주문에 대해:
- REQ-OLIST-008 → 거짓(≥1 요구)
- REQ-OLIST-009 → 거짓(∃ 요구)
- REQ-OLIST-010의 "every … has received" → **공허하게 참**(`all([])` = `True`)
- → REQ-OLIST-010이 발화해 `logistics_display = "outbound_scheduled"`

그러나 REQ-OLIST-012는 같은 주문에 대해 `null`을 요구하고, AC-OLIST-012(spec.md:224)는 `null`을 단정한다.
**요구사항 집합이 자기모순이며, 두 요구사항 중 하나를 반드시 위반한다.**

이것은 순수한 문서 흠결이 아니다. Python의 `all()`과 SQL의 `NOT EXISTS`는 둘 다 빈 집합에서 참이므로,
REQ 문언을 그대로 옮긴 구현이 실제로 이 버그를 재현한다. plan.md는 우연히 안전하다 — 의사코드(plan.md:123)가
`if not trackable: return None, None`을 먼저 두고, SQL 쪽(plan.md:56)은 `all_received = has_trackable &
~not_all_received`로 가드한다. 즉 **plan.md만 알고 있고 [HARD] 단일 출처인 spec.md는 모르는 규칙**이 존재하며,
이는 plan.md:13("규범 진술의 단일 출처는 spec.md")을 정면으로 위반한다.

REQ-OLIST-011(spec.md:120)도 동일한 결함을 갖는다 — "the order's trackable line items share a single
identical logistics_status value"는 빈 집합에서 해석이 미정이다(REQ-OLIST-011a는 "two or more distinct
values present"라는 단서 덕분에 안전하다).

**정정**: REQ-OLIST-010과 REQ-OLIST-011의 While 절 첫머리에 REQ-OLIST-008과 동일한 문구
`an order has at least one trackable line item and` 를 추가하라. REQ-OLIST-011a에도 명시하면 대칭이 완성된다.
(모듈 3은 이미 올바르다 — REQ-OLIST-013/014 둘 다 "at least one trackable line item" 가드를 갖는다.)

### High

**H1-new. spec.md:267,269,273 / acceptance.md:286,294,311 (AC-OLIST-022b/022c/022e) — 신규 필터 AC 3건의
데이터셋이 "그 외 상태의 주문 1건 이상"으로 비특정이라, H2가 지목한 바로 그 mutation을 잡지 못할 수 있다.**

AC-OLIST-022a(spec.md:265)는 데이터셋을 열거한다("AC-OLIST-007/009/010/013/013a 픽스처 전부 제외"),
AC-OLIST-022d는 (a)/(b) 두 원인을 모두 요구한다. 반면 022b/022c/022e는 비교 대상을 특정하지 않는다.

구체적 mutation: `not_shipped` 필터를 `Exists(trackable_qs.filter(logistics_status="not_shipped"))`
(**any**, plan.md:62의 `all_not_shipped`가 아니라)로 잘못 구현하면, AC-OLIST-013a 픽스처
(A=`not_shipped`, B=`shipment_confirmed` → 표시값 `partial`)가 결과에 **잘못 포함된다.**
그런데 AC-OLIST-022b의 Given은 그 주문이 데이터셋에 있을 것을 요구하지 않는다 — 테스트 작성자가
비교 대상으로 `shipped` 주문 하나만 넣으면 mutation이 통과한다. 022c(`shipment_confirmed`)와
022e(`partial`, `¬all_outbound_scheduled` 누락 mutation)도 동일 구조다.

**정정**: 022b/022c/022e의 Given을 022a와 동일하게 **6개 상태 픽스처 전량**으로 고정하고, 특히
`partial`(혼재) 주문이 반드시 데이터셋에 포함되도록 명시하라. 022e에는 uniform `outbound_scheduled` 주문을
반드시 포함시켜라.

**H2-new. spec.md:271 (AC-OLIST-022d) — 규칙 4가 `outbound_scheduled`를 통과시키는 경로가 **표시 측에서는
전혀 검증되지 않는다.** 6개 값 중 이 값만 표시 AC가 없다.**

표시값별 AC 커버리지를 세었다: `shipped`→AC-006, `partial_shipped`→AC-007/009, `not_shipped`→AC-008,
`shipment_confirmed`→AC-013, `partial`→AC-013a, `outbound_scheduled`(규칙 3 경유)→AC-010.
**규칙 4 경유 `outbound_scheduled`(trackable이 uniform하게 `logistics_status='outbound_scheduled'`)에 대해
`logistics_display == "outbound_scheduled"`를 단정하는 AC가 없다.** 이 조합은 AC-OLIST-022d의 Given (b)에만
등장하는데, 그 Then은 "필터 결과에 포함된다"만 단정하고 표시값을 단정하지 않는다.

이 값은 하필 **두 원인이 하나의 라벨로 수렴하는 유일한 값**(명시적 가정 1)이며, plan.md:61에서 필터가
이접 조건으로 특별 취급하는 유일한 값이다. 규칙 4를 3개 값에 대한 명시적 if-체인으로 구현하면서
`outbound_scheduled` 분기를 빠뜨리는 mutation(→ `partial` 반환)은 전 스위트를 통과한다.
AC-OLIST-022는 부분출고에 대해 "필터 결과 ∧ 표시값" 이중 단정을 쓰는데, 그 패턴이 022a~e로 전파되지 않았다.

**정정**: AC-OLIST-022d의 Then에 "(a)의 표시값과 (b)의 표시값이 **둘 다** `"outbound_scheduled"`"를 추가하라.
가능하면 022a~022e 전체에 AC-OLIST-022와 동일한 "반환된 주문의 `logistics_display`가 요청값과 같다"
이중 단정을 일괄 적용하라 — 이것이 설계 결정 B가 요구하는 두 경로 일치를 6개 값 전부에서 강제하는 유일한 방법이다.

**H3-new. spec.md:152 (REQ-OLIST-022a) [HARD] — C1의 축소 재발: 절대 쿼리 수 요구사항이 자기 설계로
충족 불가능한 도달 가능 케이스가 두 개 있다.**

REQ-OLIST-022a는 "post-SPEC-023 총계 = 베이스라인 + **정확히 1**, and no more"를 [HARD]로 규정한다.
그런데 plan.md:145와 :46은 **"페이지에 유효한 주문(`shopify_created_at` not null)이 하나도 없으면 이 쿼리
자체를 건너뛴다"**를 명시적으로 설계한다. `Order.shopify_created_at`은 `null=True`(`models.py:77`)이고
목록은 `-shopify_created_at`으로 정렬되므로(`views.py:163`) NULL 주문만 있는 마지막 페이지는 **도달 가능**하다.
그 페이지에서 총계는 베이스라인 + **0**이며 REQ-OLIST-022a는 문자 그대로 위반된다.

두 번째 케이스: REQ-OLIST-022a는 베이스라인을 "고객이 non-null인 주문이 하나 이상 있는 페이지에 대해
6"으로 스코프하지만, 고객이 전무한 페이지(베이스라인 5)에 대해서는 "+1"의 의미가 정의되지 않는다.
spec.md:350/plan.md:171이 이 사실을 인지하고 있으면서도 REQ 문언에는 반영하지 않았다.

REQ-OLIST-019는 "**at most** one query"로 올바르게 쓰였는데 022a만 등식이다. AC-OLIST-021은 픽스처로
두 엣지를 회피하므로 검출되지 않는다 — C1에서 지적된 "요구사항이 검출 불가능하게 위반된다"는 구조가
좁은 형태로 남아 있다.

**정정**: REQ-OLIST-022a를 "…shall equal that baseline plus **at most** 1 — exactly 1 whenever the page
contains at least one order with a non-null `shopify_created_at`, and exactly 0 otherwise"로 한정하고,
베이스라인 정의에 "고객이 non-null인 주문을 하나 이상 포함하는 페이지"라는 스코프가 "+1" 절에도
적용됨을 명시하라.

### Medium

**M1-new. spec.md:220 vs spec.md:299 — AC-OLIST-011의 `Traces:`와 Traceability 검증표가 어긋나며,
표가 커버리지를 과장한다.**
AC-OLIST-011의 Traces는 `REQ-OLIST-007, REQ-OLIST-013`인데(acceptance.md:121도 동일), 검증표
spec.md:299는 `REQ-OLIST-011 | AC-OLIST-008, AC-OLIST-011, AC-OLIST-013`으로 AC-011을 REQ-011의
커버리지로 계상한다. 실제 AC-011의 픽스처(trackable 1개 `received` + non-trackable 1개)는 **규칙 3**으로
판정되며 규칙 4(REQ-011)를 전혀 경유하지 않는다. 표에서 AC-OLIST-011을 삭제하거나 AC의 Traces를 맞춰라.
(review-1이 "매핑이 실제 커버리지를 과장한다"고 지적한 계열이 이 한 건 남았다.)

**M2-new. spec.md:315 / plan.md — REQ-OLIST-024a가 위임한 검증 게이트가 위임 대상에 존재하지 않는다.**
Traceability 표(spec.md:315)는 REQ-OLIST-024a를 "`plan.md` DoD (코드 리뷰)"로 위임한다. plan.md의
"완료 조건 → Done(구현)" 체크리스트(plan.md:212-232)에는 **허용 외 필터 값 fail-open에 대한 항목이 없다.**
plan.md:250의 REQ→검증 수단 매핑 표에만 한 줄 있을 뿐 실행 게이트가 아니다. 결과적으로 REQ-OLIST-024a는
런타임 AC도 없고 체크리스트 게이트도 없다 — 화이트리스트를 구현하지 않아 `?logistics_display=bogus`가
0건을 반환하는 mutation(REQ-024a가 명시적으로 금지한 동작)이 전 스위트를 통과한다. 검증 비용이 1줄
(`?logistics_display=bogus` → 전체 건수 반환)에 불과하므로 AC 1건을 추가하는 편이 낫다.

**M3-new. spec.md:164,174 (REQ-OLIST-026, REQ-OLIST-030) vs AC-OLIST-026/027 — 프론트엔드 6개 라벨 중
1~2개만 검증되는데 추적표는 완전 커버로 계상한다.**
REQ-OLIST-026은 드롭다운이 "전체 + 6개 값, 미입고/입고예정/출고예정/부분출고/출고/부분입고 라벨"을
제공할 것을 요구하지만 AC-OLIST-026은 "부분출고" 옵션 선택 1건만 확인한다 — 옵션이 2개뿐인 구현도 통과한다.
REQ-OLIST-030은 6개 값 각각의 한글 라벨을 요구하지만 AC-OLIST-027은 `partial_shipped`와 `null` 2개만
확인한다. 백엔드 필터는 H2 대응으로 6개 값을 전부 커버했으나 **동일한 확장이 프론트엔드에는 적용되지
않았다.** `logisticsStatusLabels.ts:11-17`을 스프레드로 확장하면서 `partial_shipped`/`partial` 키를
빠뜨리는 mutation(→ raw snake_case 노출)이 AC-027의 `partial_shipped` 단정에만 걸리고 `partial`에는
걸리지 않는다. 6개 옵션 존재 단정과 6개 라벨 렌더 단정(파라미터화 1건)을 추가하라.

**M4-new. spec.md:265 / acceptance.md:278 (AC-OLIST-022a) — Given의 사실 오류.**
"AC-OLIST-007/009/010/013/013a 픽스처(**그 외 5개 상태**)"라고 하지만, AC-007과 AC-009는 **둘 다
`partial_shipped`**로 판정되므로 실제로는 4개 상태뿐이고, `not_shipped`(AC-OLIST-008 픽스처)는
데이터셋에서 **누락**되어 있다. 문구를 "그 외 4개 상태"로 고치거나 AC-OLIST-008 픽스처를 추가하라
(후자를 권장 — H1-new와 함께 6개 상태 표준 데이터셋을 정의하는 편이 낫다).

**M5-new (= review-1 L7 미해소). plan.md:144-146 / spec.md:146 (REQ-OLIST-020) — 주문일의 시간대·
`.date()` 변환 시점이 규정되지 않았고 경계 AC도 없다.**
`_get_exchange_rate`(`serializers.py:248`)는 `obj.shopify_created_at.date()`를 쓴다 —
`USE_TZ` 하에서 이는 **UTC 날짜**다. 배치 로더가 로컬 시간대로 `.date()`를 적용하거나 `max_date`를
datetime 그대로 비교하면, 자정 경계 주문에서 REQ-OLIST-020의 [HARD] "동일한 값" 요건이 깨진다.
AC-OLIST-019/020의 픽스처는 `timezone.now()` 기반이라 이 경계를 건드리지 않는다.
plan.md 기술적 접근에 "`.date()`를 `_get_exchange_rate`와 동일한 시점·동일한 시간대에서 적용한다"를
명시하고, UTC 자정 직전/직후 주문 1건의 경계 AC를 추가하라.

### Low

- **L1-new.** AC 라벨 7건이 문장 패턴과 불일치한다 — AC-OLIST-004/005/017/021/023/024/025/027은
  `(Ubiquitous)` 라벨인데 본문은 `**While** …`(State-Driven)이다(spec.md:200,203,239,258,275,278,280,284).
  review-1 L4가 REQ 쪽만 교정되고 AC 쪽은 남았다. **번호는 유지하고 라벨만** `(State-Driven)`으로 교정하라.
- **L2-new.** spec.md:120 REQ-OLIST-011의 괄호 논거("REQ-OLIST-008/010 already exhaust the
  uniform-`shipped`/uniform-`received` cases")가 부정확하다. uniform-`received`이면서 `shipped_quantity>0`인
  경우를 소진하는 것은 REQ-OLIST-010이 아니라 **REQ-OLIST-009**다(REQ-010 자체가 009의 부정으로 가드되므로).
  결론(치역이 3개 값으로 한정된다)은 참이지만 근거가 틀렸다.
- **L3-new.** spec.md:260의 AC-OLIST-021 mutation 서술이 자기모순이다 — "페이지 크기 불변성은 우연히
  지킬 수 있어도(… 여전히 서로 다름 — 실제로는 불변성 자체도 깨진다)". acceptance.md:261의 서술
  (1건→7, 5건→11)이 정확하므로 그쪽으로 통일하라.
- **L4-new.** 명시적 가정 4(spec.md:66, trackable 전부 `order_cancelled` → "발주완료")에 대응하는 AC가 없다.
  `ready_to_ship` 관례(제외)로 구현하는 mutation은 이 케이스에서 `null`을 반환하므로 관측 가능한 차이가
  생기지만 어떤 AC도 확인하지 않는다. AC-OLIST-015에 `order_cancelled` 단독 픽스처를 1건 추가하면 닫힌다.
- **L5-new.** acceptance.md:39(AC-OLIST-002 판별력)의 서술이 원래 M3 논지와 어긋나게 재작성되어
  "느슨한 매칭이어도 통과하는 것은 맞지만…"이라는 자기 부정 문장이 되었다. 단정 문구 자체는 올바르므로
  판별력 설명만 정리하라.
- **L6-new.** 동일 대상에 대한 인용이 문서 간 불일치한다 — spec.md:32는 `shopify_orders.py:130-143`,
  plan.md:262는 `:130-147`. 둘 다 유효 범위지만 하나로 통일하라.
- **L7-new.** acceptance.md:374의 DoD 매핑표가 `AC-OLIST-006~011 | 007~010`으로 적어 AC-OLIST-011이
  커버하는 REQ-OLIST-013(H4 대응으로 추가된 `purchase_display` 단정)을 누락한다.
- **L8-new.** REQ-OLIST-024a(spec.md:160)의 "return the unfiltered result set"이
  "`logistics_display`만 무시"인지 "모든 필터를 무시"인지 문언상 모호하다. "ignore **this** filter"로 고쳐라.

---

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.70 | 0.50–0.75 | 37개 REQ 대부분이 단일 해석이며 v1.0.0의 3대 모호성(C1 문언 충돌, C3 거짓 등식, H6 "그대로 재사용")이 전부 제거되었다(spec.md:150, :112-124, :48). 감점: (1) REQ-OLIST-010/012의 빈 집합 모순은 **명시적 모순**이다(C1-new), (2) REQ-OLIST-022a의 [HARD] 등식이 자기 설계와 두 지점에서 충돌(H3-new), (3) REQ-OLIST-011 괄호 논거 오류(L2-new), (4) REQ-OLIST-024a 범위 모호(L8-new) |
| Completeness | 0.90 | 0.75–1.0 | 전 섹션 존재: HISTORY(:15-20), 문제 정의(:24-34), 목표(:36-42), 확정된 사용자 결정(:44-59), 명시적 가정(:61-66), 범위 델타(:68-83), 관련 SPEC(:85-90), 요구사항(:94-184), 인수 기준(:188-327), 설계 결정(:331-339), 사전 검증(:341-350), 제약사항(:352-358), **Exclusions 8건 전부 구체적**(:360-369), 후속 과제(:371-377). frontmatter 6필드 완비, 3문서 버전 동기. 감점: REQ-OLIST-024a의 위임 게이트가 plan.md에 실재하지 않음(M2-new), 타임존 규정 부재(M5-new) |
| Testability | 0.70 | 0.50–0.75 | 36개 AC 전수 mutation 분석 결과 **오늘 코드에서 통과하는 AC 0건**(H1 해소 확인), **정상 구현에서 실패하는 AC 0건**(C3 해소 확인). AC-006(규칙1↔2)/009(규칙2↔3)/011(trackable 양방향)/017a(1센트 반올림, 손계산 확인)/018a(IndexError→500)/021(절대값 7)/022d(이접)는 진짜로 강력하다. 감점: 022b/c/e 데이터셋 비특정(H1-new), 규칙 4 `outbound_scheduled` 표시 미검증(H2-new), REQ-024a 무검증(M2-new), FE 6개 라벨 중 2개만(M3-new), `order_cancelled` 무검증(L4-new) |
| Traceability | 0.80 | 0.75–1.0 | 37개 REQ 중 36개가 ≥1 AC를 갖고, 36개 AC 전부가 실재 REQ를 참조하며 고아 AC 0건. spec.md:327의 "37개 중 36개" 주장은 산술적으로 정확하다(v1.0.0의 과장이 정정됨). 감점: AC-OLIST-011의 Traces와 검증표 불일치 + 실제 커버 안 함(M1-new), REQ-026/030의 매핑이 커버리지 과장(M3-new), acceptance.md DoD 표의 REQ-013 누락(L7-new) |

---

## Chain-of-Verification Pass

1차 통과 후 재독하며 찾아낸 것들:

1. **37개 REQ를 처음부터 끝까지 다시 읽으며 "가드 문구"만 대조했다.** 1차에는 모듈 2 전체를
   "재설계로 깨끗해졌다"로 읽고 넘어갔다. 재독에서 REQ-OLIST-008만 `at least one trackable line item`을
   갖고 REQ-OLIST-010/011은 갖지 않는다는 **비대칭**이 보였고, `all([])==True`를 대입해
   REQ-OLIST-012와의 직접 모순을 확인했다(**C1-new — 이번 감사 최대 수확**). review-1의
   Chain-of-Verification #8은 "REQ-OLIST-008~012는 trackable 개수 위에서 전수적·배타적 ✓"라고 적었는데
   이는 **오판이었다.** 재설계 SPEC의 경계 조건은 "선행 리뷰가 통과시켰다"는 이유로 건너뛰면 안 된다.

2. **표시값 6개 각각에 대해 "이 값을 단정하는 AC가 존재하는가"를 표로 세었다.** 필터 AC는 6/6이 되었기에
   1차에는 H2를 완전 해소로 표시할 뻔했다. 값별로 세고 나서야 규칙 4 경유 `outbound_scheduled`만
   표시 AC가 0건이라는 것이 드러났다(**H2-new**). 022d의 Given이 두 원인을 요구한다는 사실이
   Then까지 강화되었다는 착시를 만든다.

3. **AC-OLIST-022a의 "그 외 5개 상태"를 곧이곧대로 세어 봤다.** AC-007과 AC-009가 둘 다
   `partial_shipped`로 수렴한다는 것을 규칙 사슬에 대입하고 나서야 알았다(**M4-new**). 문서가 제시한
   개수를 그대로 받아들이면 놓친다.

4. **plan.md의 "쿼리를 건너뛴다"는 최적화 조항을 REQ 문언과 다시 대조했다.** 1차에는 C1이 해소된
   것으로 만족했으나, plan.md:145의 조건부 스킵과 REQ-OLIST-022a의 등식("plus exactly 1, and no more")이
   충돌한다는 것을 재독에서 발견했다(**H3-new**). C1과 정확히 같은 실패 유형(성능 REQ의 한정어)이
   좁은 형태로 살아남았다 — review-1의 교훈("성능 REQ의 문언은 반드시 재독")이 이번에도 유효했다.

5. **review-1의 인용 판정을 짐작하지 않고 두 개의 Django 설치본을 모두 열었다.** poetry 가상환경(5.2.17)과
   시스템 인터프리터(5.1.6)를 각각 확인해 `count()`가 595행/609행임을 직접 읽었고, **608은 어느 쪽에서도
   재현되지 않음**을 확정했다. 덤으로 review-1의 L6(`_get_exchange_rate`의 254행이 공백)도 오류임을
   확인했다 — `serializers.py:254`는 `return result`이며 `:222-254`는 **정확한** 범위다.

6. **Exclusions 8건을 개별 확인했다**(spec.md:362-369). 전부 구체적 산출물 또는 사용자 결정을 지목하며,
   포함된 요구사항과 충돌하지 않는다. 신규 항목(`Order.status` 읽기/쓰기 금지, :369)은 REQ-OLIST-007/021,
   범위 델타 :76, plan.md:104와 일관 ✓.

7. **REQ 상호 모순 스윕(37개 전수).** REQ-016(margin_rate 노출)↔018(6키 금지) 충돌 없음 ✓.
   REQ-019("at most one")↔022(O(1))↔022a(등식) → **022a만 문제**(H3-new). REQ-033(상세 무변경)↔
   설계 결정 C(공용 헬퍼 추출)는 "관측 가능한 출력 동일" 단서로 양립 ✓. REQ-024(6개 값)↔결정 7(6개 라벨)↔
   `logisticsStatusLabels.ts` 확장 계획 일관 ✓. **진짜 모순은 REQ-010↔012 하나다.**

8. **필터 SQL을 표시 규칙에 대입해 6개 값 전부를 손으로 대조했다**(Half 2 표). 1차에는 "plan에 6개가
   다 있다"로 넘어갔으나, `partial`의 정의(6개 `all_*`의 여집합 ∧ `has_trackable`)가 실제로 non-uniform과
   동치인지 증명이 필요했다 — uniform이면 6개 중 정확히 하나가 참이므로 동치 성립 ✓. **필터 설계는 옳다.**

9. **비목표 재유입 재점검.** 마진 정렬/필터, 발주상태 필터, 부분출고 사유, OrderDetail 변경 — 4개 모두
   REQ·plan·acceptance 어디에도 재유입 없음 ✓.

10. **결함으로 올리지 않은 잔여 사항 1건**: `logistics_display` 필터는 최대 8개의 상관 `Exists`
    서브쿼리를 생성한다. 원격 RDS(쿼리당 ~130ms) 환경에서 쿼리 **수**는 1개로 유지되지만 실행 **비용**은
    분석되지 않았다. `LineItem.order`가 FK 인덱스를 가지므로 인덱스 스캔이며, plan.md:66이 필터 미적용 시
    annotation 자체를 건너뛰도록 규정한다. 구현 후 실측 대상이지 SPEC 결함은 아니다.

---

## Regression Check (Iteration 1 → 2)

| review-1 결함 | 상태 | 근거 |
|---|---|---|
| C1 REQ-022 자기모순 | **RESOLVED** | spec.md:150 재작성, :152 REQ-022a 신설, :258 AC-021 절대값 7 |
| C2 규칙 1↔2 미검증 | **RESOLVED** | spec.md:206 / acceptance.md:79 픽스처 교체, 거짓 문장 삭제 |
| C3 `Order.status` 의존 | **RESOLVED** | 3문서 37건 전수 확인, 잔존 의존 0건 |
| H1 `is None` 단정 | **RESOLVED** | 5개 AC 이중 단정 |
| H2 필터 값 1/6 | **PARTIALLY RESOLVED** | 6개 AC 생겼으나 3건 데이터셋 비특정 → H1-new |
| H3 null 원인 1/3 | **RESOLVED** | AC-018a/018b 신설, REQ-017 확장 |
| H4 발주 trackable | **RESOLVED** | AC-011에 `purchase_display` 단정 |
| H5 7번째 라벨 | **RESOLVED** | 치역 재유도로 구조적 불가 확인 |
| H6 `getDisplayStatus` | **RESOLVED** | 목표 2/결정 3 한정 + AC-004 요소 부재 |
| M1 EARS 퇴행 | **RESOLVED** | 36개 AC 전량 EARS 문장 |
| M2 반올림 | **RESOLVED** | AC-017a, 손계산 86.02 vs 86.01 확인 |
| M3/M4/M5/M6/M8/M9/M10 | **RESOLVED** | 개별 확인(위 표) |
| M7 Django 버전 | **RESOLVED (저자 판정 채택)** | 5.2.17 / 595행 직접 확인 |
| L2/L3/L5/L8 | **RESOLVED** | 소스 대조로 정정 확인 |
| L4 EARS 라벨 | **PARTIALLY RESOLVED** | REQ만 교정, AC 7건 잔존 → L1-new |
| **L7 타임존/`.date()`** | **UNRESOLVED** | plan.md:144-146에 규정 없음 → M5-new |

**판정 뒤집기(review-1이 틀린 항목):**

- **L1** — review-1의 "Django `def count(self):`는 608행"은 **오류**. 5.1.6=609행, 5.2.17=595행,
  608은 어느 쪽도 아니다. **저자의 반박이 옳다.**
- **L6** — review-1의 "`_get_exchange_rate`는 222-253, 254는 공백"은 **오류**.
  `serializers.py:253` = `cache[obj.pk] = result`, `:254` = `return result`. `:222-254`는 정확한 범위다.
  저자가 정정하지 않은 것이 옳다.
- **Chain-of-Verification #8** — "REQ-OLIST-008~012는 trackable 개수 위에서 전수적·배타적"이라는
  review-1의 확인은 **오판**이었다(C1-new).

**정체(stagnation) 없음.** 3회 반복 중 변화 없이 남은 결함은 없다. review-1이 지적한 20건 중 17건이
완전 해소, 2건 부분 해소, 1건 미해소이며, 신규 결함은 전부 **재설계가 만든 새 표면**에서 나왔다.

---

## Recommendation

**FAIL** — 그러나 v1.0.0 → v1.1.0의 진전은 실질적이다. 차단 결함 3건과 고위험 6건이 전부 **문구 땜질이
아니라 설계 수준에서** 해소되었고(특히 C3의 `Order.status` 제거는 H5까지 구조적으로 소멸시켰다),
"AC를 통과시키려고 범위를 좁힌" 흔적은 발견되지 않았다. 오늘 코드에서 통과하는 AC와 정상 구현을 깨뜨리는
AC가 **모두 0건**이 되었다는 점, 절대상수 7이 추측이 아니라 소스에서 재도출 가능하다는 점,
`file:line` 인용 60여 건이 2회 연속 날조 0건이라는 점은 이 SPEC의 실질적 강점이다.

RED에 들어갈 수 없는 이유는 하나의 **자기모순**과, 재설계가 새로 만든 표면에서 아직 닫히지 않은
**판별력 구멍 세 개**다.

### RED 진입 전 필수 (차단)

1. **spec.md:118,120 (C1-new)** — REQ-OLIST-010과 REQ-OLIST-011의 While 절에 REQ-OLIST-008과 동일한
   `an order has at least one trackable line item and` 가드를 추가하라. 현재 문언은 trackable 0개 주문에서
   `all([])==True`로 발화해 REQ-OLIST-012 및 AC-OLIST-012와 정면 충돌한다. plan.md만 이 규칙을 알고
   있다는 상태는 plan.md:13의 "규범 진술 단일 출처 = spec.md" 원칙 위반이다.

2. **spec.md:267,269,273 / acceptance.md:286,294,311 (H1-new)** — AC-OLIST-022b/022c/022e의 Given을
   AC-OLIST-022a와 동일하게 **6개 상태 표준 데이터셋**으로 고정하라. 특히 022b에는 `partial`(혼재) 주문을,
   022e에는 uniform `outbound_scheduled` 주문을 반드시 포함시켜 `any` 대 `all` mutation을 강제 판별하게 하라.

3. **spec.md:271 / acceptance.md:304 (H2-new)** — AC-OLIST-022d의 Then에 "(a)와 (b) **둘 다**의
   `logistics_display`가 `"outbound_scheduled"`"를 추가하라. 가능하면 AC-OLIST-022a~e 전체에
   AC-OLIST-022가 이미 쓰고 있는 "필터 결과 ∧ 표시값" 이중 단정을 일괄 적용하라 — 설계 결정 B가 요구하는
   두 경로 일치는 6개 값 전부에서 이중 단정으로만 강제된다.

4. **spec.md:152 (H3-new)** — REQ-OLIST-022a의 "plus exactly 1"을 "plus **at most** 1 — exactly 1 when the
   page contains at least one order with a non-null `shopify_created_at`, and 0 otherwise"로 한정하고,
   베이스라인의 "고객 non-null" 스코프가 "+1" 절에도 적용됨을 명시하라. 현재 문언은 plan.md:145의
   조건부 스킵 설계와 도달 가능한 두 케이스에서 충돌한다.

### 강력 권장 (RED를 막지는 않으나 각각 실제 구멍을 닫는다)

5. **spec.md:299 (M1-new)** — Traceability 표에서 REQ-OLIST-011의 커버 AC에서 AC-OLIST-011을 삭제하라
   (그 픽스처는 규칙 3으로 판정되어 규칙 4를 경유하지 않는다).
6. **spec.md:315 / plan.md:212-232 (M2-new)** — REQ-OLIST-024a에 AC 1건(`?logistics_display=bogus` →
   전체 건수 반환, 200)을 추가하거나, 최소한 plan.md의 Done 체크리스트에 실제 항목을 만들어라.
7. **spec.md:164,174 / acceptance.md:346-364 (M3-new)** — AC-OLIST-026에 6개 옵션 존재 단정을,
   AC-OLIST-027에 6개 라벨 렌더 단정(파라미터화)을 추가하라. 백엔드만 6/6이고 프론트엔드는 1/6이다.
8. **spec.md:265 / acceptance.md:278 (M4-new)** — AC-OLIST-022a의 "그 외 5개 상태"를 사실에 맞게
   고치고 `not_shipped` 픽스처를 포함시켜라(권장 4개 상태 → 5개 상태로 보강).
9. **plan.md:144-146 / spec.md:146 (M5-new, review-1 L7 미해소)** — 배치 로더가 `_get_exchange_rate`와
   **동일한 시점·동일한 시간대**에 `.date()`를 적용한다는 규정과, UTC 자정 경계 주문 1건의 AC를 추가하라.
10. **L1-new ~ L8-new** — AC 라벨 7건 교정(번호 유지), REQ-OLIST-011 괄호 논거 정정,
    spec.md:260 mutation 서술 정리, `order_cancelled` 픽스처 1건 추가, acceptance.md:39 판별력 서술 정리,
    `shopify_orders.py` 인용 범위 통일, acceptance.md:374 매핑에 REQ-013 추가, REQ-024a 문언을
    "ignore this filter"로 한정.

Verdict: **FAIL** (iteration 2/3)
