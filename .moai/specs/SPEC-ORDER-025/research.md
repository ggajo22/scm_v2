# Research — SPEC-ORDER-025 (LineItem 단건 발주처리 + 자동 추천 발주처 제거 + 타출판사 제외 뷰 숨김 + 수동 지정 통로 차단)

세션 내 직접 재검증. 선행 SPEC 문서의 인용을 재사용하지 않았다 — SPEC-ORDER-016/018이 기록한 "허구 인용/줄 번호 드리프트" 사고를 반복하지 않기 위해서다.

> v1.2.0: plan-audit 2차 리뷰(FAIL, 0.71) 반영. §2의 `DISTRIBUTOR_LABELS` 산수 오류 정정(ND6). 신규 §5 — R5(M2b, 타출판사 수동 지정 통로 차단) 근거 및 ND1(인증 mutation 오류)/ND5(동시성 테스트 인프라) 검증 추가.
> v1.3.0: plan-audit 3차(최종) 리뷰(FAIL, 0.78) 반영. §5-4를 "Daily Review는 항상 노트를 동반한다"는 거짓 명제 정정 + REQ-LCONF-309(메모 공란 시 기본 노트 생성) 근거로 재작성(ND-A). §5-1의 스트레이 인용(`:472`)을 `:495`로 정정(ND-E). 신규 §5-9 — `test_spec_024.py`/`test_daily_review_upload.py`에 이 변경으로 깨지는 기존 테스트가 없음을 전수 확인.

---

## 1. 문제 정의 근거

### 1-1. 미발주 현황 화면 구조

`frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`(511줄, `wc -l` 재검증) 한 컴포넌트가 `view` state(`'unordered' | 'excluded'`)로 두 화면을 전환한다(`:41-77`, 전환 버튼 `:153-170`).

- `view === 'unordered'`(미발주 품목, `:325-511`): 8열 테이블 — 체크박스/주문번호/SKU/도서명/출판사/필요 수량/**자동 추천 발주처**(`:426`)/발주 상태. 빈 상태 행의 `colSpan={8}`은 `:433`.
- `view === 'excluded'`(보류/제외 품목, `:172-310`): 8열 테이블 — 체크박스/주문번호/SKU/도서명/출판사/필요 수량/제외 사유/발주 상태. 빈 상태 행의 `colSpan={8}`은 `:252`.

"자동 추천 발주처" `<th>`는 `:426`, 그 값을 렌더링하는 `<td>`는 `:463-471`(`item.auto_distributor`가 있으면 파란 배지, 없으면 `-`).

두 테이블 모두 현재 8열이므로, 자동 추천 발주처 열 1개를 제거하고 발주처리 열 1개를 추가하면 미발주 품목 테이블은 8열을 유지한다(제외 뷰는 이 SPEC에서 열 구성 변경 없음).

### 1-2. 백엔드 미발주 목록 응답

`backend/order/purchase_order_views.py`(4468줄):

- `UnorderedItemsView`(`:322-395`) — `get()`은 `_reorder_candidate_filter`(아래)로 후보를 뽑고, `:357-359`에서 `DistributorVendorRule.objects.values_list("publisher_name", "distributor")`로 `rule_map` 딕셔너리를 만든 뒤 `:387`에서 각 행에 `"auto_distributor": rule_map.get(li.vendor or "")`를 채운다. `rule_map` 빌드는 이 뷰에서만 쓰이는 전용 쿼리 — 제거하면 이 요청의 쿼리 수가 정확히 1 감소한다.
- `_reorder_candidate_filter`(정의 `:94`, 독스트링 `:87-93`, 본체 `:108-111`): `purchase_status="unordered"`(미연결) 또는 `purchase_status="damaged_exchange"`(연결 무관)만 통과. `:87-93`의 NOTE 주석이 이미 "fan_in==4(UnorderedItemsView/RunComparisonView/DailyReviewExcelView/UploadDailyReviewView) — 원래 ANCHOR 대상이지만 파일이 이미 anchor_per_file 한도라 NOTE로 강등"이라고 기록해 두었다.
- `UnorderedItemsView.get()`의 각 행은 LineItem 단위(`li.pk`)로 구성되며(`:378-389`), 순 수량(`net_qty`)은 `:371-375`에서 계산한다 — `damaged_exchange`면 `damaged_quantity`, 아니면 `quantity`를 base로 하고 환불 수량을 차감, 0이면 스킵(`:374-375`).

### 1-3. 발주처 문자열 자유 입력의 기존 선례

`ConfirmOrderView`(`:1030-1213`, SKU 단위 발주 확정)는 `distributor`를 화이트리스트 없이 받는다 — `:1088-1089`에서 `not dist or not dist.strip()`만 검사한다. 반면 `GenerateOrderFileView`(`:526-540`)는 `VALID_DISTRIBUTORS`(`:77-78`, 9개 값 — 6개 발주처 + `warehouse_korea/ca/nj`)로 화이트리스트 검증한다(`:536-540`). 즉 이 프로젝트에는 "자유 입력 허용" 경로와 "화이트리스트 강제" 경로가 이미 공존하며, 이 SPEC의 신규 엔드포인트는 전자(ConfirmOrderView) 계열이다 — 사용자 확정 결정 D2와 일치.

`PurchaseOrder.distributor`(모델 `:354`, `backend/order/models.py`)는 `CharField(max_length=20, choices=DISTRIBUTOR_CHOICES)`이지만 `DISTRIBUTOR_CHOICES`(`:339-345`)는 5개 값(booxen/kyobo/choeumgoyuk/agape/sungseoyunion)뿐이다. Django는 `full_clean()`을 호출하지 않는 한 `choices`를 저장 시점에 강제하지 않으므로(`ConfirmOrderView`도 `full_clean()`을 호출하지 않는다), `warehouse_korea` 같은 목록 밖 값이나 자유 텍스트도 실제로 저장된다 — D2가 말한 "백엔드가 이미 임의의 비어있지 않은 발주처 문자열을 받는다"는 사실과 일치한다. 다만 **`max_length=20`은 실제 제약이다** — 20자를 넘는 자유 텍스트는 MySQL이 non-strict 모드면 자름, strict 모드면 오류를 낼 수 있다. `ConfirmOrderView`는 이 길이를 검증하지 않는다(기존의 미해결 격차). 이 SPEC의 신규 엔드포인트는 자유 텍스트를 명시적으로 허용하므로 이 위험이 실제로 발생할 확률이 ConfirmOrderView보다 높다고 판단해, 20자 초과 시 HTTP 400으로 명시적으로 거부하기로 결정했다(REQ-LCONF-010) — ConfirmOrderView의 선례에서 벗어나는 지점이며 그 이유를 spec.md에 기록한다.

### 1-4. status="confirmed" 선례

`UploadDailyReviewView`(`:1443-2032`)의 non-warehouse 분기는 PurchaseOrder를 `status="confirmed"`로 생성한다(`:2030`, 주석 `:2025-2029`: "Daily Review upload reflects the distributor's actual confirmed response, so the PO it creates starts 'confirmed' rather than 'pending' — unlike ConfirmOrderView, which stages a PO before that response exists"). `quantity`는 `sum(li.quantity or 0 for li in group_lis)`(`:2023`) — **환불 미차감 원본 수량**이다.

`ConfirmOrderView`는 `status="pending"`으로 생성한다(`:1153`).

사용자 확정 결정 D3에 따라 이 SPEC의 신규 엔드포인트는 `UploadDailyReviewView` 쪽 선례(`status="confirmed"`)를 따른다 — 담당자가 확정 발주처/단가를 직접 입력하는 행위 자체가 "확정된 응답"이기 때문이다.

### 1-5. quantity 필드 — 순 수량 vs 원본 수량의 실제 영향

`_attach_net_quantity`(`:4333-4389`, `PurchaseOrderListView`가 소비)는 발주서 목록 페이지에 표시되는 `net_quantity`를 **연결된 LineItem을 다시 조회해서** 계산한다 — `li_qty = row["quantity"]`(`:4379`, **`LineItem.quantity`를 읽는다, `damaged_quantity`가 아니다**) 빼기 환불 수량. 즉:

- `damaged_exchange`가 아닌 일반 행: 신규 엔드포인트가 쓰는 `PurchaseOrder.quantity`(순 수량, REQ-LCONF-003)와 `_attach_net_quantity`가 표시 시점에 재계산하는 값이 **환불이 없다면 일치**한다(둘 다 결국 `LineItem.quantity` 빼기 환불).
- `damaged_exchange` 행: 신규 엔드포인트는 미발주 목록이 보여준 `damaged_quantity` 기반 순 수량을 `PurchaseOrder.quantity`에 쓰지만(REQ-LCONF-003, 화면에 보인 값과 결제 문서를 일치시키기 위함), `_attach_net_quantity`는 항상 `LineItem.quantity`(원본 주문 수량, damaged_quantity 아님) 기준으로 재계산한다. **이 두 값은 다를 수 있다** — 예: `quantity=10, damaged_quantity=3`이면 발주서 생성 시점의 `PurchaseOrder.quantity=3`이지만, 발주서 목록 페이지의 `net_quantity` 컬럼은 `10`(환불 없으면)으로 표시된다.
- 이 괴리는 **이 SPEC이 만드는 것이 아니라 기존에 이미 존재한다** — `ConfirmOrderView`도 클라이언트가 보낸 `quantity`(프론트가 damaged_quantity 기반으로 계산해 보낼 가능성이 있는 값)를 그대로 쓰고, `_attach_net_quantity`는 그것과 무관하게 항상 `LineItem.quantity`로 재계산하기 때문이다. 이 SPEC은 이 괴리를 고치지 않는다(범위 밖) — spec.md에 알려진 제약으로 기록한다.

### 1-6. urls.py 배치 규칙

`backend/order/urls.py`(194줄). `<int:pk>/status/`(`:88`), `<int:pk>/damaged-exchange/`(`:92-96`), `<int:pk>/logistics-status/`(`:103-107`), `<int:pk>/rack-number/`(`:114-118`) — 전부 "purchase-orders/line-items/<int:pk>/<고정 세그먼트>/" 패턴이며 서로 다른 리터럴 세그먼트라 충돌 위험이 없다(각 주석이 명시). 신규 라우트 `purchase-orders/line-items/<int:pk>/confirm/`도 같은 패밀리에 속하며 "confirm"이 고유 리터럴이므로 위치는 이 그룹 안 어디든 안전하다 — `status/` 바로 다음에 배치할 것을 권고(관련 기능 로컬리티).

### 1-7. 에러 응답 바디 키 컨벤션 — `error` vs `detail`

같은 파일 안에 두 컨벤션이 공존한다:

- **`<int:pk>/<세그먼트>/` 단건 뷰 계열**: `LineItemStatusUpdateView`(`:2503-2507`, 404), `DamagedExchangeSubmitView`(`:2701-2723`, 404/400) 전부 `{"error": "..."}` 키를 쓴다.
- **`ConfirmOrderView`(SKU 단위 배치 확정)**: `try/except ConflictError/ValueError` 블록(`:1205-1208`)에서 `{"detail": str(exc)}`를 쓴다.

프론트엔드도 이미 `error` 키를 실제로 읽는 선례가 있다 — `frontend/src/pages/OrderDetailPage.tsx:102-106`의 `resync` 뮤테이션이 `axiosErr.response?.data?.error`를 읽어 에러 메시지를 표시한다. 신규 엔드포인트는 URL 패밀리(`<int:pk>/<세그먼트>/`)가 같으므로 **`error` 키를 채택**한다 — 코드 유사성(ConfirmOrderView)보다 URL 패밀리 일관성과 이미 검증된 프론트 읽기 패턴을 우선했다.

### 1-8. LineItemConfirmView의 fan_in 및 MX 태그 예산

`.moai/config/sections/mx.yaml`: `anchor_per_file: 3`, `warn_per_file: 5`, `note_per_file: 10`.

`backend/order/purchase_order_views.py`의 **실측** 태그 인벤토리(이 세션에서 grep으로 직접 확인):

- `@MX:ANCHOR` 5개 — `:14`(파일 전체 JWT 계약), `:1049`(ConfirmOrderView), `:1365`(`_batch_upsert_vendor_data`), `:4005`(**`_process_force_outbound_rows`**에 부착된 불변 계약 — 함수 정의는 `:4021`; 이 계약이 규율하는 대상인 `OutboundForceProcessView` 클래스 자체는 별도 위치 `:4199`에 있다 — 최초 초안이 이 ANCHOR를 `OutboundForceProcessView`에 잘못 귀속시켰던 것을 이 세션에서 재확인해 정정했다), `:4345`(`_attach_net_quantity`). **이미 `anchor_per_file: 3` 한도를 2개 초과한 상태**다 — 이 SPEC 이전부터 그렇다.
- `@MX:WARN` 7개 — `:638, :1045, :1468, :3046, :3146, :3318, :3989`. **이미 `warn_per_file: 5` 한도를 2개 초과한 상태**다.
- `@MX:NOTE` 중 "ANCHOR 강등" 성격 2개 — `_reorder_candidate_filter`(`:87-93`), `_recompute_order_aggregates`(`:114-123`). 작업 지시서가 언급한 "2개의 의도적 강등 NOTE"와 일치.

작업 지시서는 "4개의 기존 ANCHOR"라고 언급했으나 실측 결과는 **5개**다 — 이 불일치를 plan.md의 mx_plan 절에 기록하고, 사용자/오케스트레이터에게 보고한다. 결론(신규 ANCHOR를 추가하지 않는다)에는 영향이 없다 — 어느 쪽 숫자든 이미 한도 초과다.

신규 `LineItemConfirmView`의 fan_in은 1(이 URL 라우트만 호출) — `fan_in_anchor: 3` 문턱값에도 못 미치므로, 파일이 한도 이내였더라도 애초에 ANCHOR 대상이 아니다. `select_for_update()` + `transaction.atomic()`을 쓰므로 WARN 후보(ConfirmOrderView의 `:1045-1046` 선례와 동형)지만, 파일이 이미 `warn_per_file` 한도를 2개 초과했으므로 신규 WARN도 추가하지 않는다. `@MX:NOTE` 1개만 추가한다(에러 키 컨벤션 선택 이유 + `_attach_net_quantity` 표시값 괴리 문서화).

---

## 2. 프론트엔드 관련 파일 검증

- `frontend/src/services/purchaseOrderApi.ts`(368줄, `wc -l` 재검증): `UnorderedItem` 인터페이스(`:5-14`, `auto_distributor: string | null` at `:12`), `ExcludedItem` 인터페이스(`:21-29`, 이미 `auto_distributor` 없음 — SPEC-ORDER-018이 애초에 그렇게 설계했다는 주석 `:16-20`), `PURCHASE_STATUS_LABELS`(`:36-50`), `PURCHASE_STATUS_OPTIONS`(`:58-65`), `getUnorderedItems`(`:130-133`). 발주처리(confirm) API 함수는 아직 없다.
- `frontend/src/hooks/usePurchaseOrderQueries.ts`(256줄, `wc -l` 재검증): `QUERY_KEYS`(`:27-35`) — `unordered`(`:28`), `excludedItems`(`:31`), `purchaseOrders(params)`(`:32-33`, 파라미터화된 키라 `['purchase-orders','list']` 프리픽스로 무효화해야 모든 파라미터 조합이 갱신됨 — `useUploadDailyReview`가 `:182`에서 이미 이 패턴 사용). `useUpdateLineItemStatus`(`:116-132`)는 `unordered` + `excludedItems` 둘 다 무효화한다(양방향 동기화, SPEC-ORDER-018 REQ-RESTORE-021 선례).
- `frontend/src/pages/OrderDetailPage.tsx`: `DISTRIBUTOR_LABELS`(`:13-22`, **8개 값 — 발주처 5개(booxen/kyobo/choeumgoyuk/agape/sungseoyunion) + `warehouse_korea/ca/nj` 3개**, ND6 정정 — v1.1.0은 "6개 발주처 + 창고 3"이라 적었으나 6+3=9로 산수부터 틀렸고, 실제로는 발주처가 5개뿐이며 `yes24`가 없다. `VALID_DISTRIBUTORS`(`purchase_order_views.py:77-78`, 6개 발주처 + 창고 3개 = 9개, `yes24` 포함)와 혼동한 것으로 보인다 — 이 둘은 서로 다른 상수다. `yes24` 라벨 부재의 실무 영향은 `spec.md` "알려진 제약" 참조).
- `frontend/src/pages/PurchaseOrders/tabs/VendorRulesTab.tsx`: `DISTRIBUTOR_OPTIONS`(`:6-10`), `DISTRIBUTOR_LABEL`(`:13-17`, 3개 값만 — 처음교육/아가페/성서유니온).
- 두 라벨 맵은 이미 중복 정의돼 있다(프로젝트 기존 상태) — 이 SPEC은 이를 공용 상수로 리팩터링하지 않는다(요청받지 않은 범위 확장, Scope Discipline). 신규 모달의 6개 드롭다운 옵션(booxen/kyobo/yes24/choeumgoyuk/agape/sungseoyunion)은 자체 상수로 정의한다.
- shadcn/ui `Dialog` 컴포넌트가 이미 프로젝트에 존재하고 사용 중이다(`frontend/src/components/ui/dialog.tsx`, 소비처 예: `frontend/src/features/admin-users/CreateAdminDialog.tsx`) — 신규 모달은 이 기존 패턴을 재사용한다.

---

## 3. 영향받는 테스트 (실측)

> plan-audit 1차 리뷰(D1/D2/D3)가 이 절의 최초 버전이 `grep`이 아니라 부분 회상에 의존해 누락 3건을 냈다고 지적했다. 아래는 `grep -n "other_publisher\|EXCLUDED_STATUSES" backend/order/tests/test_spec_018.py`와 `grep -n "auto_distributor" backend/order/tests/*.py`를 이 세션에서 다시 실행해 전수 재검증한 결과다.

### 3-1. `backend/order/tests/test_spec_018.py` — `EXCLUDED_STATUSES` 참조 **7곳**(4곳 아님)

`grep -n "other_publisher\|EXCLUDED_STATUSES"` 결과 **7개** 라인이 나온다 — 최초 버전은 이 중 4개만 열거했다(D2):

| 줄 | 내용 | 이 SPEC과의 관계 |
|----|------|-------------------|
| `:57` | `EXCLUDED_STATUSES = ("on_hold", "order_cancelled", "cs_required", "other_publisher")` 튜플 정의 | 3개로 축소 필요 |
| `:183` | `("other_publisher", "SKU-OTHERPUB")` 개별 케이스 | `other_publisher` 기대값을 "이제 응답에 없음"으로 반전 |
| `:320` | `purchase_status=EXCLUDED_STATUSES[line_no % 4]` | **튜플이 3개가 되면 `% 4`가 인덱스 3(존재하지 않음)을 만들어낼 수 있어 `IndexError`로 하드 크래시** — `% len(EXCLUDED_STATUSES)`로 수정하거나 고정 리스트로 치환 필요 |
| `:439` | `("on_hold", "order_cancelled", "cs_required", "other_publisher"), start=2` 루프 | `other_publisher` 기대값 반전 |
| `:474` | `"SKU-E": "other_publisher"` 딕셔너리 값 | 기대값 반전 |
| `:516` | `purchase_status=EXCLUDED_STATUSES[idx % 4]` | `:320`과 동일한 모듈러 인덱싱 위험 — `IndexError` |
| `:550` | `for status in EXCLUDED_STATUSES:` (SQL 문자열에 제외 상태 미등장을 단정하는 루프, `:542-543`의 쿼리 수 단정과 같은 테스트 함수 안) | 튜플이 3개가 되면 크래시 없이 조용히 `other_publisher` 절의 SQL 부재 검증만 사라짐 — 별도 대응 불필요(이미 안전하게 축소됨)하지만 `:64`(아래 3-2)와 같은 함수 안이므로 함께 갱신 |

`:320`/`:516`의 모듈러 인덱싱 수정은 REQ-LCONF-301 구현의 필수 부수 작업이다 — `plan.md` M2에 명시한다.

### 3-2. `backend/order/tests/test_spec_018.py:64` — 쿼리 수 핀(pin), REQ-LCONF-201과 정면 충돌(critical, D1)

`:64`에 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`이 정의되어 있고 `:542-543`에서 두 번 단정된다:

```python
assert queries_without_excluded == UNORDERED_ENDPOINT_QUERY_COUNT
assert queries_with_excluded == UNORDERED_ENDPOINT_QUERY_COUNT
```

`:59-63`의 주석이 그 3의 구성을 명시한다: "JWT user lookup (1) + the two this view issued before SPEC-ORDER-018". REQ-LCONF-201(`rule_map` 쿼리 제거)은 그 "2" 중 1개를 없애므로, **이 SPEC 적용 후 정확한 신규 값은 2**다 — 추정이 아니라 `:59-63`의 구성 설명과 REQ-LCONF-201의 "쿼리 1개 감소" 주장을 대수적으로 합친 결과다. `:537-540`의 주석은 이런 의도적 변경을 정확히 예견하고 있다("temporarily assert a wrong value and read the reported count"로 재도출하는 절차까지 적어 두었다).

**최초 버전(v1.0.0)의 오류**: 이 핀을 영향 범위에서 완전히 누락했고, `plan.md`의 리스크 R-C는 "베이스라인을 Plan 단계에서 추정하지 않고 Run 단계에서 재측정한다"고 서술해 **이미 저장소에 존재하는 값을 미지로 취급**했다. `plan.md`는 이제 "기존 핀 3 → 2로 갱신, Run에서 실측 재확인"으로 정정한다(`plan.md` M2 참조). 대응 인수 기준은 `acceptance.md` AC-LCONF-205.

### 3-3. `backend/order/tests/test_purchase_orders.py` — auto_distributor 단정 2건(major, D3)

`grep -n "auto_distributor" backend/order/tests/*.py`로 전 테스트 파일을 재스캔한 결과, 최초 버전이 놓친 파일이 나왔다:

- `test_purchase_orders.py:1-15`(파일 헤더 독스트링) — `:5` "SC-PO-001 unordered aggregation + auto_distributor"
- `test_purchase_orders.py:300-313` `test_auto_distributor_from_vendor_rule` — `:313` `assert result["auto_distributor"] == "choeumgoyuk"`
- `test_purchase_orders.py:315-325` `test_auto_distributor_null_when_no_rule` — `:325` `assert result["auto_distributor"] is None`

REQ-LCONF-201이 응답에서 `auto_distributor` 키 자체를 제거하므로 두 단정 모두 `KeyError`로 실패한다(`next(...)`로 얻은 `result` 딕셔너리에 그 키가 없다). `acceptance.md` 품질 게이트가 "회귀 없음"을 요구하는 이상, 이 2건은 삭제하거나 "`"auto_distributor" not in result`"로 재작성해야 한다 — `plan.md` M2/파일 목록에 반영했다.

### 3-4. 나머지 영향 파일(변경 없음, 재확인)

- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx` — `auto_distributor: null` 픽스처 3곳: `:170, :328, :356`.
- `frontend/src/services/purchaseOrderApi.test.ts`(66줄) — **`auto_distributor` 참조 없음(재검증 확인)**. 이 파일은 [MODIFY] 대상이 아니다.
- 신규: `backend/order/tests/test_spec_025.py`(프로젝트 명명 관례).

---

## 4. 모델 필드 검증

`backend/order/models.py`:

- `LineItem`(`:152-244`): `PURCHASE_STATUS_CHOICES`(`:156-167`, 7개 값), `confirmed_price`(`:195`, `DecimalField(null=True, blank=True)`), `confirmed_distributor`(`:196`, `CharField(max_length=50, null=True, blank=True)`), `damaged_quantity`(`:238`, `IntegerField(default=0)`), `sku`(`nullable`).
- `PurchaseOrder`(`:336-373`): `DISTRIBUTOR_CHOICES`(`:339-345`, 5값, 저장 시점 강제 안 됨 — 위 1-3 참조), `STATUS_CHOICES`(`:346-350`, pending/confirmed/cancelled), `sku`(`:352`, `CharField` **non-null**), `quantity`(`:355`, `IntegerField()` **non-null, 기본값 없음**), `unit_price`(`:356`, nullable), `line_items` M2M(`:359`).
- `DistributorVendorRule`(`:514-532`): `publisher_name`(unique), `distributor`(`SECONDARY_DISTRIBUTOR_CHOICES`, 3값 — 처음교육/아가페/성서유니온). 이 SPEC은 이 모델과 그 CRUD 뷰(`DistributorVendorRuleListCreateView`/`DistributorVendorRuleDeleteView`)를 건드리지 않는다 — `UnorderedItemsView`가 그 데이터를 소비하던 방식(`rule_map`)만 제거한다.

`ConflictError`는 `purchase_order_views.py:2461`에 정의된 평범한 `Exception` 서브클래스 — 신규 뷰에서 그대로 import 없이 재사용 가능(같은 모듈).

---

## 5. v1.2.0/v1.3.0 추가 — 타출판사 노트 없는 생성 통로 전부 차단(M2b, plan-audit ND2/ND-A 대응)

### 5-1. 사각지대 확인 — 왜 R4만으로는 불충분한가

`frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`의 미발주 품목 표 행별 select(`:495`)와 일괄 상태 변경 select(`:344`)는 `PURCHASE_STATUS_OPTIONS`(`frontend/src/services/purchaseOrderApi.ts:58-65`)를 렌더링하며, `:62`에 `{ value: 'other_publisher', label: PURCHASE_STATUS_LABELS.other_publisher }`가 포함되어 있다. 이 값을 선택하면 `PATCH /api/purchase-orders/line-items/<pk>/status/`(`LineItemStatusUpdateView.patch`, `:2503-2532`) 또는 bulk 버전이 호출되는데, 두 뷰 모두 `purchase_status` 필드만 갱신하고(`li.save(update_fields=["purchase_status"])`) `LineItemNote`를 생성하지 않는다. 즉 R4(REQ-LCONF-301/302) 하나만 적용하면, 담당자가 이 드롭다운으로 계속 `other_publisher`를 새로 만들 수 있고, 그렇게 만들어진 행은 노트가 없어 보류/제외 뷰(R4가 숨김)와 품목 노트 타출판사 탭(노트가 없어 원래도 안 보임) 어디에도 나타나지 않게 된다 — 주문번호를 이미 알고 있어야만 주문상세에서 찾을 수 있다. 이 사각지대를 plan-audit iteration 2의 ND2가 지적했다.

### 5-2. PURCHASE_STATUS_OPTIONS의 전 소비처(grep 전수 확인)

```
grep -rn "PURCHASE_STATUS_OPTIONS" frontend/src --include="*.ts" --include="*.tsx"
```

- `UnorderedItemsTab.tsx:13`(import), `:207`(보류/제외 품목 일괄 상태 변경 select), `:294`(보류/제외 품목 행별 select), `:344`(미발주 품목 일괄 상태 변경 select, `.filter((o) => o.value !== 'unordered')` 적용), `:495`(미발주 품목 행별 select) — 렌더 사이트 4곳 전부 이 배열을 소스로 그대로(또는 `unordered` 필터만 추가로) 쓴다. 소스 배열에서 `other_publisher`를 제거하면 4곳 전부에 자동 전파된다 — 개별 사이트 수정 불필요.
- `purchaseOrderApi.test.ts:3,15,17,20,33,48`(테스트) — 이미 `damaged_exchange` 배제를 검증하는 기존 패턴(`:15-21`)이 있다. `other_publisher` 배제도 동일 패턴으로 추가한다.
- `purchaseOrderApi.ts:35,44,58,67,71`(정의/주석/타입) — 정의 자체(`:58-65`)만 수정하면 된다.

### 5-3. damaged_exchange 거부 정확한 구현(복제 대상 선례)

`LineItemStatusUpdateView.patch()`(`:2503-2532`):

```python
purchase_status_value = request.data.get("purchase_status")
valid_choices = [c[0] for c in LineItem.PURCHASE_STATUS_CHOICES]
if purchase_status_value not in valid_choices:
    return Response({"error": f"Invalid purchase_status. Valid choices: {valid_choices}"}, status=400)
if purchase_status_value == "damaged_exchange":
    return Response({"error": _DAMAGED_EXCHANGE_BLOCKED_MESSAGE}, status=400)
```

`_DAMAGED_EXCHANGE_BLOCKED_MESSAGE`(`:2475-2479`)는 파일 상단에 공유 상수로 정의되어 두 뷰(`LineItemStatusUpdateView` `:2518`, `LineItemBulkStatusUpdateView` `:2575`)가 재사용한다. `LineItemBulkStatusUpdateView`는 `:2540`에서 클래스로 선언되고 `patch()` 메서드 정의는 `:2557`이다(이 세션에서 `grep -n "def patch"`로 재확인 — v1.2.0판이 `:2540-2598`을 통째로 "`patch()`"라 지칭해 클래스 선언과 메서드를 혼동했다, ND-E 정정). 그 메서드는 동일 위치(`valid_choices` 검사 직후, `ids` 빈 값 검사와 `existing.update()` 호출 사이)에 동일한 damaged_exchange 거부 분기를 갖는다(`:2573-2577`). `other_publisher` 거부는 이 두 분기를 그대로 복제하는 것으로 충분하다 — 새로운 설계가 필요하지 않다.

### 5-4. UploadDailyReviewView의 타출판사 분기 — PATCH 뷰 우회는 참이지만 "항상 노트 동반"은 거짓이었다(REQ-LCONF-308/309 근거, v1.3.0 정정 — ND-A)

`excel_utils.py:656-660`의 `_NOTE_TYPE_STATUS_MAP`이 `"타출판사": "other_publisher"`를 매핑한다. `UploadDailyReviewView`(`purchase_order_views.py:1443-2032`)의 CS 분기(`:1780-1817`)는:

```python
if note_type == "타출판사":                                   # :1792
    publisher_distributor = resolve_publisher_distributor(...)
    publisher_price = _other_publisher_unit_price(sku, item)
for li in unordered_lis:
    li.purchase_status = new_status                            # :1799 — 무조건
    ...
cs_status_updates.extend(unordered_lis)                        # :1804
if note is not None:                                            # :1805 — 조건부
    for li in unordered_lis:
        pending_notes.append(LineItemNote(..., content=note, note_type=note_type, assignee="CS"))
```

**주장 1(참, REQ-LCONF-308 근거)**: `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`를 호출하지 않고 모델 인스턴스를 직접 조작한 뒤 `pending_notes`(리스트 선언 `:1714`)를 모아 함수 뒷부분에서 `LineItemNote.objects.bulk_create(pending_notes)`(`:1967` — v1.2.0판이 이를 `:1711-1714`로 잘못 인용했다. `:1711-1713`은 주석, `:1714`는 리스트 선언일 뿐 `bulk_create()` 호출 자체는 아니다, ND-E 정정)로 일괄 저장하는 완전히 별개의 코드 경로다 — 이 세션에서 직접 코드를 추적해 확인했다. 따라서 M2b가 두 PATCH 뷰에 추가하는 400 거부는 Daily Review 업로드 흐름에 어떤 영향도 주지 않는다.

**주장 2(v1.2.0판 — 거짓이었다, ND-A로 정정)**: v1.2.0판은 "이 경로로 생성되는 모든 `other_publisher` 행은 항상 노트를 동반한다"고 서술했다. **거짓이다** — `:1805`의 `if note is not None:`이 노트 생성을 조건부로 만든다. `note` 자체가 어디서 오는지 추적하면:

- `excel_utils.py:881-884`: `note_idx`는 신규 템플릿이면 `"Status"` 컬럼, 레거시 템플릿이면 `"메모"` 컬럼에서 가져온다 — `note_type`을 결정하는 `"선택"` 컬럼과는 **별개의 컬럼**이다.
- `excel_utils.py:944`: `note = _str_or_none(_cell(row, note_idx))`.
- `excel_utils.py:760-764` `_str_or_none`: `value.strip()`이 빈 문자열이면 `None`을 반환한다.

즉 **'선택'="타출판사"이면서 메모/Status 셀이 공란인 업로드 행은 `purchase_status="other_publisher"`가 기록되지만 `LineItemNote`는 생성되지 않는다.** 이것이 REQ-LCONF-303이 "타출판사 노트가 연결된 경우에 한해"로 조건화된 이유이며, v1.2.0판이 이 조건을 "향후 생성되는 모든 행에 대해 성립"이라고 (부정확하게) 확대 해석했던 지점이다. v1.3.0에서 REQ-LCONF-309를 신설해 이 분기(오직 `note_type == "타출판사"`인 경우만)에서 `note is None`이면 기본 안내 문구로 노트를 생성하도록 좁게 고친다 — 이제서야 "이 SPEC 적용 이후 생성되는 모든 행은 노트를 동반한다"는 주장이 참이 된다.

### 5-5. ND1 — 인증 mutation 오류 정정 근거

`backend/config/settings/base.py:102-108`:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
```

이 세션에서 직접 확인. DRF는 뷰에 `permission_classes`/`authentication_classes`가 선언되지 않으면 이 프로젝트 전역 설정으로 폴백한다 — 즉 `LineItemConfirmView`가 이 두 속성을 선언하지 않아도 익명 요청은 여전히 401이다. **"선언을 제거하면 401이 무너진다"는 주장은 이 프로젝트에서 성립하지 않는다.** v1.1.0은 iteration 1 plan-audit 보고서의 이 서술을 코드 대조 없이 그대로 옮겨 적었다 — 이번 세션에서 `base.py`를 직접 읽어 오류를 확인하고 정정했다(감사 산출물도 검증 대상이지 그대로 신뢰할 근거가 아니라는 프로젝트 원칙의 재확인). 실제로 판별력을 갖는 mutation은 `permission_classes = [AllowAny]`처럼 **다른 값을 명시적으로 설정**하는 것뿐이다.

같은 URL 패밀리(`<int:pk>/<세그먼트>/`, 쓰기 엔드포인트)의 401 테스트 선례는 `test_purchase_orders.py:2300-2304` `test_patch_unauthenticated_returns_401`이다 — `test_spec_018.py:86/:408`(읽기 전용 GET 엔드포인트)보다 그레인이 더 맞는다.

### 5-6. ND5 — 동시성 테스트 인프라 제약 근거

- `backend/config/settings/local.py:11`: `"ENGINE": config("DB_ENGINE", default="django.db.backends.sqlite3")` — 프로젝트 기본 테스트 DB 엔진은 SQLite. Django의 `select_for_update()`는 SQLite 백엔드에서 무시된다(Django 공식 문서상 알려진 제약) — 즉 기본 설정으로 스레드 테스트만 돌리면 락이 실제로 없어도 우연히 통과할 수 있다.
- `backend/pytest.ini:8`: `concurrency: uses transaction=True + real threads against the shared remote test DB (SPEC-ORDER-016 AC-FORCE-023) — do not run concurrently with other pytest processes; select with -m concurrency, deselect with -m "not concurrency"` — 마커가 프로젝트 규약 그 자체를 담고 있다.
- `test_spec_016.py:1012-1027` `TestForceProcessLockingDeterministic.test_target_select_uses_for_update` — `CaptureQueriesContext`로 `orders_line_item` 테이블 대상 쿼리의 SQL 텍스트에 `"FOR UPDATE" in q["sql"].upper()`를 직접 단정. 독스트링: *"Fast, deterministic companion to the threaded test below: if the lock is ever accidentally removed, this fails immediately instead of relying on a possibly-flaky concurrency test."*
- `test_spec_016.py:1030-1064` `TestForceProcessLockingConcurrent.test_two_concurrent_requests_cannot_both_pass_the_limit` — `@pytest.mark.concurrency` + `@pytest.mark.django_db(transaction=True)`, `threading.Barrier(2)` + 스레드 2개로 실제 동시 요청을 재현.

이 두 테스트가 한 쌍으로 존재하는 이유가 정확히 "SQLite에서는 결정론적 SQL 검증이 필요하고, 실제 락 경합은 스레드 테스트가 필요하다"는 것이다 — AC-LCONF-012a/012b가 이 쌍을 그대로 재사용한다.

### 5-7. 모델 레벨 테스트 3곳은 영향 없음(무변경 확인)

`grep -n "other_publisher" backend/order/tests/*.py`로 전 파일 재확인한 결과, `test_purchase_orders.py`/`test_spec_018.py`/`test_spec_024.py` 외에 2개 파일이 더 나온다:

- `test_purchase_order_models.py:321,455` — 둘 다 `LineItem.objects.create(...)` 직접 호출(각각 `test_all_valid_choices_accepted`, `test_all_seven_choices_accepted`). 모델 필드 자체의 허용값을 검증하는 테스트이며 어떤 뷰도 거치지 않는다.
- `test_spec_012.py:257` — `_make_line_item(..., purchase_status="other_publisher", ...)` 헬퍼 직접 호출(`test_received_alone_satisfies_true`). 마찬가지로 뷰를 거치지 않는다.
- `test_purchase_orders.py:2238` `test_all_non_unordered_statuses_excluded` — `LineItem.objects.create(...)` 직접 호출로 5개 상태(`other_publisher` 포함)를 만들고 `GET /unordered/`에 안 나타남을 확인하는 테스트. 이것도 PATCH 엔드포인트를 거치지 않는다.

세 파일 모두 `LineItem.PURCHASE_STATUS_CHOICES`(모델 필드 자체의 허용값)를 검증하며, M2b는 이 모델 필드에서 `other_publisher`를 제거하지 않으므로(spec.md Exclusions 7번) 전부 무변경이다.

### 5-8. purchaseOrderApi.test.ts의 기존 구조(재사용 대상)

`:1-52` 전체가 이미 `damaged_exchange`에 대해 정확히 같은 패턴을 갖고 있다 — `describe('PURCHASE_STATUS_OPTIONS')` 블록의 "does NOT include damaged_exchange"(`:16-21`)와 "preserves all six existing options unmodified"(`:23-35`), `describe('PURCHASE_STATUS_LABELS')` 블록의 "still maps damaged_exchange to its Korean label"(`:43-45`). `other_publisher`에 대해서도 동일한 세 종류의 단정을 추가하고, "여섯 개"였던 `:23`의 문구를 "다섯 개"로 갱신한다.

### 5-9. REQ-LCONF-309가 기존 테스트를 깨뜨리지 않는다는 확인(v1.3.0 신규, ND-A 후속)

REQ-LCONF-309가 `UploadDailyReviewView`의 실제 동작(타출판사 분기의 노트 생성 조건)을 바꾸는 이상, 그 분기를 실행하는 기존 테스트가 깨지지 않는지 이 세션에서 전수 확인했다.

- `grep -n '"status"\|"selected": "타출판사"' backend/order/tests/test_spec_024.py` → 타출판사 행 10개 전부가 `"status"` 키에 비공백 값(`"아가페"`, `"성서유니온"`, `"기타"` 등)을 명시하거나(`:96,117,150,193,217,235,253`), 레거시 `_make_daily_review_excel` 경로로 `"note": "아가페"`를 직접 지정한다(`:136`). **메모/Status가 공란인 타출판사 행 픽스처는 `test_spec_024.py`에 하나도 없다** — 즉 이 파일의 어떤 테스트도 REQ-LCONF-309의 blank-memo 분기를 실행하지 않는다.
- `grep -n "LineItemNote\|note_type" backend/order/tests/test_spec_024.py` → **0건**. 이 파일은 `purchase_status`/`confirmed_distributor`/`confirmed_price`만 단정하며 노트 존재 여부를 검증하는 코드가 없다 — REQ-LCONF-309 적용 전후로 이 파일의 단정 결과는 동일하다.
- `grep -n "타출판사" backend/order/tests/test_daily_review_upload.py` → `:779`/`:869`의 legend 값 목록(엑셀 템플릿 구조를 구성하는 참조 목록일 뿐 실제 행 데이터가 아님) 2건만 나오며, `"selected": "타출판사"` 형태의 실제 테스트 행은 **0건**이다 — 이 파일에는 타출판사 업로드를 실행하는 기존 테스트 자체가 없다.
- `_make_daily_review_excel`(`test_daily_review_upload.py:77-116`)의 메모 컬럼은 `row.get("note", "")`(`:106`)로 기본값이 빈 문자열이다 — `"note"` 키를 넘기지 않고 이 헬퍼를 호출하면 정확히 REQ-LCONF-309의 blank-memo 분기를 재현한다. AC-LCONF-308a가 이 헬퍼를 그대로 활용한다.

**결론**: REQ-LCONF-309는 기존 백엔드 테스트를 하나도 깨뜨리지 않는다 — `plan.md` M2b의 신규 테스트 3건(AC-308a/308b/308c)은 순수 추가이며, 어떤 기존 테스트도 수정할 필요가 없다.
