# SPEC-ORDER-027 — 구현 계획

## 0. v0.2.0 재설계 배경

plan-auditor 1차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-027-review-1.md`, **FAIL, 0.50**)의 D1(critical)이 v0.1.0의 전제를 무너뜨렸다: "입고"의 진짜 데이터 소스는 `logistics_status`가 아니라 `LineItem.received_quantity`(`backend/order/models.py:228`, 기존 필드)다. 이 필드는 그룹 요약 API 응답에 없으므로, 이번 버전은 **백엔드 변경을 포함한다** — v0.1.0의 "프런트엔드 전용" 전제는 폐기되었다.

이 재설계는 v0.1.0의 D2(critical)도 부수적으로 해소한다: 프런트엔드가 더 이상 어떤 산술도 하지 않으므로(단순히 API가 준 두 정수를 문자열에 끼워 넣을 뿐), `null`/`undefined` 가드 관련 판별 불가 문제 자체가 사라진다.

**v0.2.1 정정 (2차 감사 PASS 0.75, `.moai/reports/plan-audit/SPEC-ORDER-027-review-2.md`)**: 구조는 그대로이며 5건의 정정 + REQ-RACKRECV-006 정리만 반영했다 — 그룹 격리 미검증 공백(N9, AC-RACKRECV-012 신설), M1 단독 판별 오표기(N1), AC-010의 M5 공동 판별 누락(N2), 클램프 원인의 두 번째 독립 경로(N4, 가정 A2/A3), NULL 경로의 도달 불가능성 정직화(N6). 자세한 내용은 `spec.md` HISTORY v0.2.1과 `acceptance.md` 각 항목의 "v0.2.1 정정" 표시를 참조.

---

## 1. 접근 개요 — 2개 파일 수정 + 1개 신규 테스트 (프런트엔드 2개 파일 추가 수정)

### 1.1 백엔드 — `LineItemRackNumberSummaryView`에 그룹 레벨 `received_quantity` 추가

`purchase_order_views.py:3442-3479`의 기존 집계 루프에 한 줄을 추가한다. **기존 `net_qty` 계산(`:3446`)을 재사용**하며 중복 계산하지 않는다.

```python
# 기존 (:3442-3479, 발췌)
for li in line_items:
    net_qty = max((li.quantity or 0) - li.refunded_qty, 0)
    if li.refunded_qty and net_qty == 0:
        continue

    key = li.rack_number
    group = groups.setdefault(
        key,
        {
            "rack_number": key,
            "is_unassigned": key == "",
            "total_quantity": 0,
            "received_quantity": 0,          # [NEW]
            "line_items": [],
        },
    )
    group["total_quantity"] += net_qty
    # [NEW] REQ-RACKRECV-002/003: received_quantity는 환불 시점 이후 재조정되지
    # 않으므로(A2) net_qty보다 커질 수 있다 — 반드시 클램프한다. logistics_status는
    # 보지 않는다(REQ-RACKRECV-004) — 부분 입고(상태가 아직 "received"로 전환되지
    # 않은 행)도 그대로 기여해야 한다.
    group["received_quantity"] += min(li.received_quantity, net_qty)
    group["line_items"].append({...})  # 기존과 동일, 무변경
```

**핵심 설계 판단**:

- **(A) 상태 무관, 필드 기반.** v0.1.0의 `logistics_status == "received"` 게이트를 완전히 제거한다. `received_quantity`가 0보다 크면 그 자체로 "몇 권이 입고되었는지"를 말해준다 — 상태 전환 여부와 무관하다(REQ-RACKRECV-004).
- **(B) 클램프는 선택이 아니라 필수.** `received_quantity`는 원본 `quantity`(환불 미반영) 기준으로 누적되고(가정 A3), 환불이 기록되어도 소급 감산되지 않는다(가정 A2, 이 세션에서 `grep -r received_quantity backend/`로 다른 쓰기 경로가 없음을 확인). 클램프 없이는 "입고 5 / 총 3"처럼 입고가 총을 초과하는 표시가 나올 수 있다. **[v0.2.1 추가, 감사 N4]** 이 괴리의 원인은 환불만이 아니다 — `LineItem.quantity` 자체가 Shopify 재동기화마다 덮어써진다(`shopify_orders.py:236`의 `"quantity": li.get("quantity")`가 `LineItem.objects.update_or_create`의 `defaults`로 쓰이는 지점은 `:265`/`:281`). 전량 입고 후 재동기화가 `quantity`를 하향 정정하면 환불이 전혀 없어도 같은 괴리가 생긴다 — REQ-RACKRECV-003의 조건은 원인을 명시하지 않으므로(cause-agnostic) 이미 이 경로도 커버한다.
- **(C) 행 레벨 노출 없음.** 그룹 딕셔너리에만 추가한다 — `line_items.append({...})` 블록(개별 라인아이템 필드)은 손대지 않는다(REQ-RACKRECV-007, Exclusion #2). 행별 `수량` 컬럼(프런트엔드)이 무변경이어야 하므로 데이터도 노출할 필요가 없다.

### 1.2 프런트엔드 — API가 준 두 정수를 그대로 렌더링

`rackNumberApi.ts`의 `RackNumberSummaryGroup`에 `received_quantity: number`를 추가하고, `SummaryTab.tsx:96`의 헤더 span을:

```
총 {group.total_quantity}권
```

에서

```
입고 {group.received_quantity} / 총 {group.total_quantity}권
```

으로 바꾼다. **양쪽 값 모두 API 응답에서 직접 읽으며 클라이언트에서 어떤 산술도 하지 않는다** — `?? 0` 가드도, 재계산도, 재클램프도 없다(REQ-RACKRECV-008). `group.received_quantity`는 백엔드 `IntegerField` 집계 결과이므로 `undefined`/`null`이 될 수 없다.

**[HARD] 단일 텍스트 노드 요구 (D5 대응)**: 헤더의 개수 텍스트는 **하나의 요소** 안에 결합된 문자열로 렌더링해야 한다 — `<span>입고</span><span>{n} / 총 {t}권</span>`처럼 "입고"를 별도 요소로 분리하지 않는다. 기존 `SummaryTab.test.tsx:103`의 `expect(screen.getByText('입고')).toBeInTheDocument()`는 펼쳐진 라인아이템 테이블의 `received` 물류상태 라벨(`purchaseOrderApi.ts:78`, 동일 리터럴 `입고`)을 겨냥한 단정이다 — 헤더가 별도 노드로 "입고"만 담으면 `getByText`가 다중 매치로 예외를 던진다. `SummaryTab.tsx:96`의 현재 구조(하나의 `<span>` 안에 텍스트+표현식 혼합)를 그대로 유지하면 이 요구를 자동으로 만족한다 — **새 `<span>`을 추가로 쪼개지 않는다.**

---

## 2. 마일스톤 (우선순위 순. 시간 예측 없음. CLAUDE.md Rule 2 — 5개 파일을 4단위로 분해)

### M1 (Priority High) — 백엔드: RED → GREEN

1. `backend/order/tests/test_spec_027.py` `[NEW]` 작성. `test_spec_014.py`의 관례를 그대로 따른다(이 세션에서 그 파일을 직접 읽고 확인한 패턴):
   - `_make_order(shopify_order_id=..., store_type="gimssine", **kwargs)`, `_make_line_item(order, shopify_line_item_id=..., sku=..., **kwargs)`(`defaults = {"quantity": 1, "title": "Test Book"}`), `_find_group(groups, rack_number)` 헬퍼를 재사용하거나 동일 시그니처로 재정의한다.
   - `received_quantity`는 `LineItem`의 실제 모델 필드이므로 `_make_line_item(..., received_quantity=3)`처럼 **`**kwargs`로 바로 전달 가능** — SPEC-ORDER-026처럼 헬퍼를 확장할 필요가 없다.
   - 환불 픽스처는 `test_spec_014.py:343-349`의 `_refund(order, line_item, quantity, shopify_refund_id=900001)`를 그대로 재사용한다(이 SPEC은 매출 필드를 다루지 않으므로 `subtotal`/`total_tax` 확장 불필요).
   - AC-RACKRECV-001 ~ AC-RACKRECV-006, **AC-RACKRECV-012**(`acceptance.md`, v0.2.1 신규 — 그룹 2개짜리 교차 오염 방지 테스트)에 대응하는 7개 테스트 클래스/함수를 작성한다.
2. 작성 직후 무수정 코드에서 실행해 RED 확인: AC-001, 002, 003, 004, 006, 012는 실패해야 하고(현재 `received_quantity` 필드 자체가 응답에 없으므로 `KeyError`로 실패), AC-005도 마찬가지로 `KeyError`로 실패한다 — 이 SPEC의 신규 필드는 **7개 AC 전부**가 현재 응답 스키마에 없는 값을 요구하므로 전부 RED다(v0.1.0처럼 일부만 RED인 상황이 아니다).
3. `purchase_order_views.py:3442-3479` `[MODIFY]` — §1.1의 한 줄(`group["received_quantity"] += min(li.received_quantity, net_qty)`)과 그룹 딕셔너리 초기값(`"received_quantity": 0`)을 추가한다.

금지 사항:
- `line_items.append({...})` 내부(행 레벨 필드) 변경 금지 — `received_quantity`를 행에 노출하지 않는다
- `net_qty` 계산(`:3446`)을 중복하거나 변형 금지 — 그대로 재사용
- `logistics_status`를 조건으로 사용하는 어떤 필터도 추가 금지(REQ-RACKRECV-004)
- `_process_warehouse_receipt_rows`(`:2392-2579`) 수정 금지

완료 조건: AC-RACKRECV-001 ~ AC-RACKRECV-006, AC-RACKRECV-012 전부 통과.

### M2 (Priority High) — 프런트엔드: 타입 + 컴포넌트

1. `frontend/src/services/rackNumberApi.ts:68-73` `[MODIFY]` — `RackNumberSummaryGroup`에 `received_quantity: number` 추가. `RackNumberSummaryLineItem`(`:59-66`)은 무변경.
2. `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx:96` `[MODIFY]` — 헤더 span 텍스트를 §1.2 형태로 변경. 새 `<span>` 분리 금지(D5).

금지 사항:
- `group.total_quantity`/`group.received_quantity`에 대한 어떤 클라이언트 산술(재계산, `?? 0`, 재클램프)도 추가 금지 — REQ-RACKRECV-008
- 체크박스·인풋·버튼 추가 금지(REQ-RACKRECV-014)
- `SearchTab.tsx` 수정 금지
- 행별 `수량` 셀(`:122`) 값 변경 금지

완료 조건: AC-RACKRECV-007 ~ AC-RACKRECV-011 전부 통과.

### M3 (Priority High) — 프런트엔드: 테스트 확장 + 기존 어서션 재검증

1. `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` `[MODIFY]` — `buildResponse()`(`:12-56`) 픽스처에 `received_quantity` 필드를 추가하고, AC-RACKRECV-007 ~ AC-RACKRECV-011에 대응하는 신규 테스트를 추가한다.
2. **[HARD] `:103`의 기존 어서션을 직접 재실행해 확인한다** — `expect(screen.getByText('입고')).toBeInTheDocument()`가 헤더 변경 후에도 정확히 1개 노드에 매치하는지. §1.2의 단일 `<span>` 구조를 지켰다면 통과해야 한다. **이것은 가정이 아니라 검증 항목이다** — 통과를 확인하지 못하면(예: 다중 매치 예외) M2로 돌아가 헤더 구조를 수정한다. AC-RACKRECV-011이 이 불변식을 영구적인 회귀 테스트로 고정한다.
3. 나머지 기존 테스트(`AC-RACKSUM-011/004b`, `AC-RACKSUM-011a`, `AC-RACKSUM-013`, `AC-RACKSUM-014/015`, 접힘/펼침 스위트 `:178-271`)가 `received_quantity` 필드 추가만으로 깨지지 않는지 확인한다 — 이 필드는 헤더 텍스트에만 영향을 주므로, `총 {n}권` 형식을 가정하던 매처(`getByText(/8/)` 등)는 새 형식에서도 정규식이 매치되어 대부분 무수정 통과할 것으로 예상되나, 값만 확인하는 매처가 아니라 정확 문자열을 확인하는 매처가 있으면 최소 수정한다.

완료 조건: `SummaryTab.test.tsx` 전체 통과, `:103` 어서션 무수정 통과 확인.

### M4 (Priority Medium) — @MX 태그

§5 실행. `purchase_order_views.py`에 신규 `@MX:NOTE` 1건 추가(클램프 근거), `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE` 무삭제 확인.

---

## 3. 영향 파일 ([DELTA] 마커)

| 마커 | 파일 | 변경 내용 |
|------|------|-----------|
| **[MODIFY]** | `backend/order/purchase_order_views.py` | `LineItemRackNumberSummaryView`의 집계 루프(`:3442-3479`)에 그룹 `received_quantity` 필드 추가 + 신규 `@MX:NOTE` |
| **[NEW]** | `backend/order/tests/test_spec_027.py` | AC-RACKRECV-001~006, 012 대응 7개 테스트, `test_spec_014.py` 헬퍼 관례 재사용 |
| **[MODIFY]** | `frontend/src/services/rackNumberApi.ts` | `RackNumberSummaryGroup`에 `received_quantity: number` 추가(`:68-73`) |
| **[MODIFY]** | `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx` | 헤더 span(`:96`) 텍스트 변경 |
| **[MODIFY]** | `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` | AC-RACKRECV-007~011 대응 신규 테스트 + `buildResponse()` 픽스처 확장 |
| **[EXISTING]** | `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` | **무변경** (REQ-RACKRECV-013) |
| **[EXISTING]** | `backend/order/purchase_order_views.py`의 `_process_warehouse_receipt_rows`(`:2392-2579`) | **무변경** (REQ-RACKRECV-017) — 같은 파일이지만 다른 함수/뷰이므로 diff 범위를 명확히 분리해 확인한다 |
| **[EXISTING]** | `frontend/src/services/rackNumberApi.ts`의 `RackNumberSummaryLineItem`(`:59-66`) | **무변경** (REQ-RACKRECV-007) |

변경/신규 파일은 **5개**다(백엔드 2 + 프런트엔드 3). CLAUDE.md Rule 2(3개 이상 파일 분해)에 따라 §2의 M1(백엔드)/M2(프런트엔드 구현)/M3(프런트엔드 테스트)/M4(MX)로 분해해 순차 진행한다.

---

## 4. 위험과 대응

| ID | 위험 | 대응 |
|----|------|------|
| R1 | 구현자가 `logistics_status == "received"`를 남겨둔 채로 게이트를 추가해 부분 입고(상태 미전환)를 여전히 0으로 표시한다 | AC-RACKRECV-001과 AC-RACKRECV-004가 **공동으로** 잡는다(v0.2.1 N1 정정 — 이전 버전은 AC-001을 sole이라 적었으나 AC-004도 잡는다) — `logistics_status="shipment_confirmed"` + `received_quantity=3`인 픽스처(AC-001)가 이를 직접 잡는다. §2 M1 "금지 사항"에 명시 |
| R2 | 클램프(`min(received_quantity, net_qty)`)를 생략하고 raw `received_quantity`를 그대로 합산 — "입고"가 "총"을 초과해 표시된다 | AC-RACKRECV-002(환불로 인한 축소)와 AC-RACKRECV-003(NULL quantity로 인한 축소) 두 경로가 함께 방어한다 |
| R3 | `received_quantity` 키를 그룹 딕셔너리에 아예 추가하지 않는다(초기값 누락 등) | 모든 백엔드 AC가 `KeyError`로 이를 잡는다. AC-RACKRECV-005가 "값이 0이어도 키가 존재한다"를 명시적으로 증명하는 대표 케이스 |
| R4 | 미지정(`is_unassigned`) 그룹에서만 집계 로직이 빠지는 특수 케이스 실수(예: `if key:` 같은 조건 분기 실수) | AC-RACKRECV-006이 sole 판별자 — 이 픽스처는 `logistics_status="received"`를 써서 R1의 상태 게이트 변이와 겹치지 않게 격리했다 |
| R5 | 헤더를 별도 요소로 쪼개 `getByText('입고')`(`SummaryTab.test.tsx:103`)가 다중 매치로 예외를 던진다(D5) | REQ-RACKRECV-012 [HARD] + AC-RACKRECV-011(전용 회귀 테스트, `getAllByText('입고', {exact:true})`가 정확히 1건임을 단정) + §2 M3에서 `:103`을 직접 재실행 확인 |
| R6 | `receivedQuantity === 0`일 때 조건부로 "입고" 세그먼트를 숨기는 UX "개선" 유혹 | REQ-RACKRECV-009 [HARD] + AC-RACKRECV-008이 0값도 그대로 렌더되는지 직접 단정 |
| R7 | 프런트엔드에서 API 값에 `?? 0`이나 재계산을 추가해(불필요한 방어 코드) `total_quantity`/`received_quantity` 필드를 뒤바꿔 쓴다 | AC-RACKRECV-007이 서로 다른 두 값(3과 5)으로 필드 순서 오류를 잡는다. §2 M2 "금지 사항"에 명시 |
| R8 | `_process_warehouse_receipt_rows`(`:2392-2579`)를 실수로 함께 수정(같은 파일 내 인접 코드) | M3에서 `git diff`로 그 블록이 공집합인지 별도 확인(REQ-RACKRECV-017) |
| R9 | `net_qty` 계산을 중복 정의하거나 `:3446`과 다르게 재구현해 두 값이 갈린다 | §2 M1 "금지 사항"에서 기존 `net_qty` 변수 재사용을 명시. `total_quantity`(기존 AC, `test_spec_014.py`)와 신규 `received_quantity`가 같은 루프에서 나오므로 회귀 테스트가 두 값의 일관성을 자연히 검증 |
| **R10** `[v0.2.1, 감사 N9]` | `received_quantity` 누산기를 그룹별 딕셔너리가 아니라 함수 스코프의 공유 변수로 잘못 선언해, 그룹이 여러 개일 때 값이 서로 오염된다 — 그룹이 1개뿐인 기존 AC 6개로는 검출되지 않는다 | AC-RACKRECV-012(그룹 2개, 각자 다른 값)가 sole 판별자. §2 M1의 신규 테스트에 포함 |

---

## 5. MX 태그 계획

### 5.1 백엔드 — 신규 `@MX:NOTE`

`purchase_order_views.py:3442`(집계 루프 시작) 또는 신규 `received_quantity` 라인 바로 위에 `@MX:NOTE`를 추가한다. 근거: "매직 상수/설명 없는 비즈니스 규칙"(mx-tag-protocol.md의 NOTE 트리거) — 클램프가 왜 필요한지(A2/A3, 환불과 입고 누적의 비동기화)는 코드만 봐서는 전혀 드러나지 않는 비직관적 규칙이다.

```python
# @MX:NOTE: [AUTO] SPEC-ORDER-027 REQ-RACKRECV-002/003: received_quantity is
# clamped to net_qty because it is NEVER retroactively decremented when a
# refund is recorded afterward (_process_warehouse_receipt_rows,
# purchase_order_views.py:2392-2579, is the only writer). A LineItem fully
# received (received_quantity == quantity) and later partially refunded will
# have received_quantity > net_qty — without min(received_quantity, net_qty)
# the rack summary would show 입고 exceeding 총. logistics_status is
# deliberately NOT checked here — partial receipts (status still
# "shipment_confirmed") must still contribute (REQ-RACKRECV-004).
```

작업 전 `purchase_order_views.py`의 기존 NOTE 개수를 확인해 `mx.yaml`의 `note_per_file` 한도(기본 10)를 넘지 않는지 확인한다.

### 5.2 프런트엔드 — 신규 태그 없음

`RackNumberSummaryGroupSection`은 여전히 내부 컴포넌트(fan_in=1)이며, 이번 변경은 렌더링 로직만 한 줄 바뀐다. 복잡도가 유의하게 늘지 않으므로 `@MX:WARN` 불필요. `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE`는 **유지**한다 — 이 변경은 인터랙션 요소를 추가하지 않으므로 그 주장은 계속 참이다.

파일 내 태그 수 변화: `purchase_order_views.py` NOTE +1. `SummaryTab.tsx` 무변경(0).

---

## 6. 검증 명령 (참고)

```bash
# 백엔드 신규 테스트만 (동시 실행 금지, 서브셋에는 --no-cov 필수)
pytest backend/order/tests/test_spec_027.py --no-cov -v

# 백엔드 회귀 (동일 뷰의 기존 스위트)
pytest backend/order/tests/test_spec_014.py --no-cov -v

# 프런트엔드
npx vitest run frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx

# 범위 규율 확인
git diff --stat frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx     # 공집합
git diff purchase_order_views.py                                          # :3442-3479 범위 내인지 육안 확인, :2392-2579/:3481-3489 무변경 확인
git status backend/order/migrations/                                      # 신규 파일 0건
```

---

## 7. 완료 후 기록

`spec.md` HISTORY에 다음을 추가한다:
- 통과 테스트 수(백엔드 신규 7개 + `test_spec_014.py` 무수정 + 프런트엔드 전체)
- `SummaryTab.test.tsx:103`의 기존 어서션이 무수정으로 통과했음을 확인한 사실
- `SummaryTab.tsx:17-20`의 기존 `@MX:NOTE` 무삭제 확인
- mx_plan 실행 결과(`purchase_order_views.py` 신규 NOTE 추가 여부)
