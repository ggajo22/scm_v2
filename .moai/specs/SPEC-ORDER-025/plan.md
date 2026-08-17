# Implementation Plan — SPEC-ORDER-025

> v1.1.0: plan-audit 1차 리뷰(FAIL, 0.62) 반영. D1(쿼리 수 핀 갱신 누락)/D2(`EXCLUDED_STATUSES` 참조 개수 오측 4→7)/D3(`test_purchase_orders.py` 영향 누락)/D6(REQ-LCONF-015 검증 방법 정렬)/D10(무효화되는 독스트링 미기재)을 해소했다.
> v1.2.0: plan-audit 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-025-review-2.md`, FAIL, 0.71) 반영 + 사용자 승인 범위 추가. **범위 추가**: R4를 확장해 `other_publisher`의 수동 지정 통로(PATCH 엔드포인트 2개 + 프론트 드롭다운)를 차단하는 M2b를 신설했다(spec.md D4/REQ-LCONF-304~308). **ND1**(AC-014 mutation이 DRF 프로젝트 기본 설정 때문에 실패하지 않는 오류를 M1 작업 지시에서도 정정), **ND2**(REQ-LCONF-303의 Daily Review 경로 사실 오류를 spec.md에서 정정한 데 맞춰 이 문서의 관련 서술도 동기화), **ND5**(AC-012를 결정론적 SQL 단정 + 마커 명시 스레드 테스트로 분할한 데 맞춰 M1 테스트 목록 갱신), **ND3/ND6/ND7**(수치·범위 정정)을 반영했다.
> v1.3.0: plan-audit 3차(최종) 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-025-review-3.md`, FAIL, 0.78) 반영 + 사용자 승인 범위 추가. **범위 추가**: M2b가 v1.2.0에서 "UploadDailyReviewView 무변경"이라 기술했던 것이 ND-A로 거짓임이 드러났다 — `:1805`의 `if note is not None:` 가드 때문에 메모/Status 공란 타출판사 행은 노트 없이 업로드됐다. M2b를 확장해 REQ-LCONF-309(타출판사 분기 한정, 메모 공란 시 기본 노트 생성) 구현을 추가했다. **ND-E**(minor, 인용 3건 정정: `:1711-1714` bulk_create 인용을 실제 3개 지점(`:1714`/`:1805`/`:1967`)으로 분리, `LineItemBulkStatusUpdateView.patch()`를 `:2557`(이 세션에서 `grep -n "def patch"`로 재확인)로 정정)을 반영했다.

## 개요

3개 독립적이지만 같은 화면(`UnorderedItemsTab.tsx`)에 모이는 변경을 백엔드 → 프론트엔드 순으로 진행한다. R3(자동 추천 발주처 제거)와 R4(타출판사 제외 + 수동 지정 차단)는 기존 코드를 좁히는 변경이라 리스크가 낮아 보이지만, **셋 다 기존 테스트의 고정 상수·모듈러 인덱싱·선택 가능 상태 목록과 직접 충돌한다** — 아래 M2/M2b를 상세히 참조.

규범 진술의 단일 출처는 `spec.md`다 — 이 문서의 의사코드/설명은 참고용이며 `spec.md`의 EARS 요구사항과 충돌하면 `spec.md`가 우선한다. 단, 검증 **방법**(어떤 테스트 기법을 쓰는지)은 `acceptance.md`가 규범이다 — 이 문서가 `acceptance.md`와 다른 검증 방법을 지시해서는 안 된다(v1.0.0의 D6 결함이 정확히 이 규칙 위반이었다).

---

## 마일스톤

### M1 (Priority High) — 백엔드: LineItem 단건 발주처리 엔드포인트

- `backend/order/purchase_order_views.py`에 `LineItemConfirmView` 신설. `ConfirmOrderView`(`:1030-1213`)의 자격 확인·`select_for_update()`·원자적 트랜잭션·`ConflictError` 재사용 패턴을 LineItem 단건 그레인으로 축소해 적용한다.
  - 자격 확인: `purchase_status == "damaged_exchange"` 이거나 (`purchase_status == "unordered"` 이고 `purchase_orders.exists()`가 False) 여야 함 — 그 외 전부 `ConflictError` → 409(REQ-LCONF-006). 이미 연결된 `unordered` 행은 별도로 REQ-LCONF-005의 409를 낸다(메시지만 다르게, 상태 코드는 동일).
  - 순 수량 계산: `_reorder_candidate_filter`가 admit하는 조건과 `UnorderedItemsView.get()`의 net_qty 계산(`:371-375`)을 그대로 재사용 — 별도 헬퍼로 뽑아낼지, 인라인 복제할지는 구현 시점에 fan_in을 보고 결정(현재 fan_in=1이라 헬퍼 추출은 필수 아님).
  - 응답 바디 키는 `error`(URL 패밀리 컨벤션, `research.md` §1-7).
  - **인증 클래스는 명시적으로 선언한다**(`authentication_classes = [JWTAuthentication]`, `permission_classes = [IsAuthenticated]`) — 프로젝트 전역 `DEFAULT_PERMISSION_CLASSES`(`base.py:106-108`)가 어차피 같은 값으로 폴백하지만, `acceptance.md` AC-LCONF-014b가 이 클래스 속성을 직접 단정하므로 명시 선언이 필요하다(ND1 해소 — 다른 `<int:pk>/<세그먼트>/` 뷰들의 기존 관례이기도 하다).
- `backend/order/urls.py`에 `path("purchase-orders/line-items/<int:pk>/confirm/", LineItemConfirmView.as_view(), name="po-line-item-confirm")` 추가 — `<int:pk>/status/`(`:88`) 바로 다음에 배치.
- 신규 `backend/order/tests/test_spec_025.py` — REQ-LCONF-001~015 전항 커버. 필수 케이스:
  - 정상 생성(damaged_exchange 아닌 행 + damaged_exchange 행 둘 다, `acceptance.md` AC-LCONF-001/002)
  - 이미 연결됨 409(AC-003)
  - **부적격 상태 5종 전수**(`on_hold`/`order_cancelled`/`cs_required`/`other_publisher`/`in_stock`, 각각 개별 케이스로 parametrize — AC-LCONF-004a~e) — `on_hold` 1건만 검증하는 단일값 블랙리스트 구현이 통과해버리는 것을 막기 위해 5종 전부 필수(D5 해소)
  - 순수량 0 이하 409(AC-005), sku 없음 400(AC-011), distributor 공백/21자 400(AC-006/007), **distributor 정확히 20자는 성공**(AC-015, 경계값 — `> 20` vs `>= 20` 오류를 잡기 위해 007과 짝으로 필수)
  - unit_price 파싱 실패 400(AC-008), 존재하지 않는 pk 404(AC-010), unit_price 생략 시 null 저장(AC-009)
  - `_recompute_order_aggregates` 호출 확인 — **`unittest.mock.patch`로 스파이해 정확히 1회 호출되고 인자에 대상 order_id가 포함됨을 직접 단정한다(AC-LCONF-013).** ~~주문의 `status`/`ready_to_ship` 값 변화를 관찰하는 간접 검증은 사용하지 않는다~~ — `_recompute_order_aggregates`는 `logistics_status` 기반 집계이고(`:124-130`), 발주처리 쓰기는 `logistics_status`를 건드리지 않으므로 간접 관찰은 호출 누락을 잡지 못한다(D6 해소, v1.0.0의 오류였다).
  - **미인증 요청 401**(AC-014, 정정 — ND1) — `anon_client` 픽스처(`test_purchase_orders.py:2300-2304` `test_patch_unauthenticated_returns_401` 선례, 같은 쓰기 URL 패밀리라 `test_spec_018.py:86/:408`보다 그레인이 맞다)와 `assert res.status_code == 401` 패턴을 재사용. `PurchaseOrder` 미생성도 함께 단정. ~~판별 mutation은 `permission_classes` 제거~~ — **이 mutation은 프로젝트 전역 `DEFAULT_PERMISSION_CLASSES`(`base.py:106-108`) 폴백 때문에 401을 그대로 유지해 판별력이 없다(이 세션에서 `base.py`를 직접 읽어 확인, v1.1.0이 iteration 1 감사 원문의 오류를 검증 없이 옮겨 적었던 지점).** 실제 판별 mutation은 `permission_classes = [AllowAny]` 명시다. 별도로 **AC-LCONF-014b**(뷰 클래스 속성 `permission_classes`/`authentication_classes`에 `IsAuthenticated`/`JWTAuthentication`이 포함됨을 정적으로 단정)를 추가해, "선언 자체를 빠뜨리는" 실수가 프로젝트 기본값 폴백에 가려지지 않게 한다.
  - **동시성 검증 분할**(AC-012a/012b, 정정 — ND5): (a) `test_spec_016.py:1013-1027` `TestForceProcessLockingDeterministic`의 결정론적 companion 패턴을 재사용해, `CaptureQueriesContext`로 대상 LineItem 조회 SQL에 `FOR UPDATE`가 존재함을 단정하는 케이스(AC-012a) — SQLite 기본 테스트 엔진(`local.py:11`)에서는 `select_for_update()`가 무시되므로 이 결정론적 단정이 없으면 스레드 테스트만으로 락 누락을 잡지 못할 수 있다. (b) `test_spec_016.py:1030-1064` `TestForceProcessLockingConcurrent`의 `threading.Barrier(2)` 구조를 재사용한 스레드 테스트(AC-012b) — **`@pytest.mark.concurrency` + `@pytest.mark.django_db(transaction=True)`를 반드시 명시**한다(`backend/pytest.ini` markers 절, 프로젝트 메모리 `feedback_pytest_remote_db_concurrency`).

### M2 (Priority High) — 백엔드: 자동 추천 발주처 제거 + 타출판사 제외

- `UnorderedItemsView.get()`(`:322-395`)에서 `rule_map` 빌드(`:357-359`)와 `"auto_distributor"` 키(`:387`) 제거. `DistributorVendorRule` import는 파일 상단(`DistributorVendorRuleListCreateView` 등이 여전히 사용)이라 그대로 둔다. **클래스 독스트링(`:323-328`)의 "Each result includes auto_distributor derived from DistributorVendorRule." 문장도 함께 제거한다** — 남겨두면 코드와 모순되는 거짓 문서가 된다(D10 해소).
- `EXCLUDED_PURCHASE_STATUSES`(`:405-410`)에서 `"other_publisher"` 제거. **`ExcludedItemsView` 독스트링(`:414-427`)의 "purchase_status is one of the four excluded states" 문장(`:418`)을 "three excluded states"로 갱신한다**(D10 해소, 인용 범위 정정 — ND7: `:414-421`이 아니라 `:414-427`이 독스트링 전체 범위다).
- `backend/order/tests/test_spec_018.py` 변경 — **최초 계획(v1.0.0)이 4곳이라 기술했던 것은 오류였다. 실제로는 다음 7곳 + 파생 수정 1곳, 총 3개 그룹**(`research.md` §3-1/3-2 참조, D2/D1 해소):
  1. `:57` — `EXCLUDED_STATUSES` 튜플을 3개로 축소.
  2. `:183, :439, :474` — `other_publisher` 기대값을 "더 이상 응답에 없음"으로 반전.
  3. **`:320`, `:516`** — `EXCLUDED_STATUSES[line_no % 4]` / `EXCLUDED_STATUSES[idx % 4]`의 모듈러 인덱싱을 `EXCLUDED_STATUSES[line_no % len(EXCLUDED_STATUSES)]` 형태로 수정한다. **수정하지 않으면 튜플이 3개로 줄어든 순간 `line_no % 4`가 3을 만들어낼 수 있어 `IndexError`로 하드 크래시한다** — 이것은 "고쳐지면 좋은 것"이 아니라 M2 없이는 테스트 스위트 자체가 실행 불가능해지는 필수 수정이다.
  4. **`:64`** — `UNORDERED_ENDPOINT_QUERY_COUNT = 3`을 **`2`로 갱신**한다. 근거: `:59-63`의 주석이 3을 "JWT 조회 1 + 뷰가 SPEC-ORDER-018 이전부터 발행하던 2"로 분해해 두었고, 이번 SPEC의 REQ-LCONF-201이 그 2 중 `rule_map` 조회 1개를 제거하므로 신규 값은 대수적으로 2다 — Run 단계에서 `CaptureQueriesContext`로 실측해 2임을 재확인한 뒤 상수를 확정한다(추정이 아니라 이미 아는 값의 실측 검증).
  5. **`:542-543`** — 위 `:64` 상수를 참조하는 두 단정은 상수만 바뀌면 자동으로 정합된다(코드 수정 불필요, 상수 갱신의 파급효과).
  6. `:550` — `for status in EXCLUDED_STATUSES:` 루프는 튜플이 3개로 줄어도 크래시하지 않는다(코드 수정 불필요) — 다만 같은 테스트 함수 안이므로 `:542-543`과 함께 재실행해 통과를 재확인한다.
- **`backend/order/tests/test_purchase_orders.py` 변경(v1.0.0 최초 계획에서 완전히 누락됐던 파일, D3 해소)**:
  - `:300-313` `test_auto_distributor_from_vendor_rule` — `assert result["auto_distributor"] == "choeumgoyuk"`(`:313`)를 `assert "auto_distributor" not in result`로 재작성(테스트 이름/목적을 "auto_distributor 키가 완전히 사라졌다"로 전환하거나, 테스트 자체를 삭제하고 그 취지를 `test_spec_025.py`의 AC-LCONF-201 대응 케이스에 흡수 — 구현 세션에서 선택, 단 삭제를 선택하면 `test_spec_025.py`에 동등한 회귀 커버리지가 반드시 있어야 한다).
  - `:315-325` `test_auto_distributor_null_when_no_rule` — 동일하게 재작성 또는 삭제+흡수.
  - `:5`(파일 헤더 독스트링 "SC-PO-001 unordered aggregation + auto_distributor") — "auto_distributor" 언급 제거.
  - (M2b가 이 파일에 추가로 손을 댄다 — 아래 참조.)

### M2b (Priority High) — 백엔드+프론트엔드: 타출판사 노트 없는 생성 통로 전부 차단(v1.2.0 신설, v1.3.0 확장, spec.md D4/D5/REQ-LCONF-304~309)

plan-audit 2차 리뷰의 ND2와 3차 리뷰의 ND-A가 드러낸 두 사각지대(수동 지정된 `other_publisher` 행이 노트 없이 R4 적용 후 고아화됨 + Daily Review 업로드도 메모 공란이면 동일하게 고아화됨)를 근본 차단하는 마일스톤. R4의 나머지 절반이며, 반드시 M2와 같은 세션에서 함께 반영해야 한다 — M2만 반영하고 이 마일스톤을 건너뛰면 "알려진 제약"에 기재된 고아화 시나리오가 이 SPEC 이후로도 계속 새로 발생한다.

- **프론트엔드** `frontend/src/services/purchaseOrderApi.ts`: `PURCHASE_STATUS_OPTIONS`(`:58-65`)에서 `other_publisher` 옵션(현재 `:62`)을 제거한다. `PURCHASE_STATUS_LABELS`(`:36-50`)의 `other_publisher: '타출판사'`(`:40`)는 유지한다 — 이미 존재하는 `damaged_exchange` 항목(`:43-49`)과 동일한 "선택 불가하지만 표시는 유지" 패턴. `PURCHASE_STATUS_OPTIONS`의 4개 소비처(`UnorderedItemsTab.tsx:207,294,344,495`, `research.md` §2 그렙 결과)는 모두 이 배열을 그대로 렌더링하므로 소스 1곳만 고치면 4곳 전부에 전파된다 — 개별 렌더 사이트를 수정할 필요 없음.
- **백엔드** `backend/order/purchase_order_views.py`:
  - `LineItemStatusUpdateView.patch()`(`:2503-2532`)의 기존 `damaged_exchange` 거부 분기(`:2516-2520`, `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE` 사용)를 정확히 본뜬 `other_publisher` 거부 분기를 `valid_choices` 검사 직후·damaged_exchange 검사와 나란히 추가한다. 신규 상수 `_OTHER_PUBLISHER_BLOCKED_MESSAGE`(또는 `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE`처럼 파일 상단에 공유 상수로 배치)를 정의해 "other_publisher can only be set via the Daily Review upload" 취지의 안내 메시지를 담는다.
  - `LineItemBulkStatusUpdateView.patch()`(정의는 `:2557` — `:2540`은 클래스 선언, 이 세션에서 `grep -n "def patch"`로 재확인)의 동일 위치(`valid_choices` 검사 직후, `:2573-2577` damaged_exchange 분기와 나란히)에 동일한 거부 분기를 추가한다.
  - **`UploadDailyReviewView`의 타출판사 분기 수정(v1.3.0 신규, REQ-LCONF-309)** — CS 분기(`:1780-1817`)의 `if note is not None:`(`:1805`)을 `note_type == "타출판사"`일 때만 다르게 동작하도록 좁게 수정한다. 예:
    ```python
    if note_type == "타출판사":
        publisher_distributor = resolve_publisher_distributor(...)
        publisher_price = _other_publisher_unit_price(sku, item)
        effective_note = note if note is not None else _OTHER_PUBLISHER_DEFAULT_NOTE
    else:
        effective_note = note
    ...
    if effective_note is not None:
        ...
        content=effective_note,
    ```
    신규 상수 `_OTHER_PUBLISHER_DEFAULT_NOTE`(예: `"타출판사 확정 처리 (Daily Review 업로드, 메모 없음)"`, 파일 상단 `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE` 근처에 배치)를 정의한다. `note_type`은 계속 `"타출판사"`로, `assignee`는 계속 `"CS"`로 유지해 `LineItemNotesPage.tsx:36`의 필터가 그대로 픽업하게 한다. **다른 3개 CS 유형(주문취소/주문보류/CS필요)의 분기는 `effective_note = note`로 완전히 그대로 유지** — `if note_type == "타출판사":` 조건 밖이므로 자동으로 보존된다.
  - `UploadDailyReviewView`의 나머지 로직(경고/CS 분기 진입 조건, warehouse 분기, non-warehouse 분기, `bulk_update`/`bulk_create` 호출 구조)은 **무변경** — REQ-LCONF-308이 규정하는 "두 PATCH 뷰를 거치지 않는다"는 사실 자체는 이 수정과 무관하게 여전히 참이다(이 세션에서 코드로 재확인).
- **`backend/order/tests/test_purchase_orders.py` 추가 변경**:
  - `:2306-2319` `test_patch_all_six_choices` — `valid_choices` 리스트에서 `"other_publisher"`를 제거해 5개로 축소(제목도 "five choices"로 갱신).
  - 신규 `test_patch_other_publisher_rejected` — `test_patch_damaged_exchange_rejected`(`:2321-2335`)와 동일 구조로 추가(AC-LCONF-306).
  - `LineItemBulkStatusUpdateView`에 대해서도 동일한 신규 테스트 추가(AC-LCONF-307) — 기존 bulk 관련 테스트 클래스 위치 확인 후 그 안에 배치.
  - `:2238` `test_all_non_unordered_statuses_excluded`와 `:2236-2253`은 **무변경** — `LineItem.objects.create()`로 직접 생성하는 모델 레벨 테스트라 PATCH 엔드포인트 게이트와 무관함을 이 세션에서 확인했다(`research.md` §5).
- **`backend/order/tests/test_daily_review_upload.py` 추가 변경(v1.3.0 신규, AC-LCONF-308a/308b/308c — 308c는 v1.4.0에서 `309c`→`308c`로 개명, ND-H)**:
  - 신규 테스트 — '선택'="타출판사" + 메모/Status 공란(`_make_daily_review_excel`을 `"note"` 키 없이 호출) → `purchase_status="other_publisher"` + `LineItemNote` 1건(기본 문구) 생성 확인(AC-308a).
  - 신규 테스트 — '선택'="타출판사" + 메모 있음(`"note": "아가페"`) → 기존과 동일하게 그 값으로 노트 생성 확인(AC-308b, 회귀).
  - 신규 테스트 — '선택'="주문취소" + 메모/Status 공란 → 노트 미생성 확인(AC-308c, 대조군 — REQ-LCONF-309의 범위가 타출판사로만 한정됨을 증명).
  - `test_spec_024.py:87-103`과 그 형제 테스트(`:107-260` 부근)는 **무변경 확인** — 이 세션에서 재검토한 결과 모든 타출판사 행이 Status 셀에 비공백 값(`"아가페"`/`"성서유니온"`/`"기타"` 등)을 명시하며(`grep -n '"status"' test_spec_024.py`로 10개 행 전수 확인), 노트 존재를 단정하는 코드도 없다(`grep -n "LineItemNote\|note_type" test_spec_024.py` 결과 0건) — REQ-LCONF-309의 blank-memo 분기를 실행하는 기존 테스트가 없으므로 무수정으로 통과한다.
- **`frontend/src/services/purchaseOrderApi.test.ts` 변경(v1.2.0 신규 — 이제 [MODIFY] 대상)**:
  - `:23-35` "preserves all six existing options unmodified" — `other_publisher` 항목을 제거하고 "다섯 값"으로 갱신.
  - 신규: `damaged_exchange` 배제 검증(`:16-21`)과 동일 패턴으로 "does NOT include other_publisher" 케이스 추가(AC-LCONF-304).
  - `PURCHASE_STATUS_LABELS` describe 블록(`:38-52`)에 `damaged_exchange` 케이스(`:43-45`)와 동일 패턴으로 "still maps other_publisher to its Korean label" 케이스 추가(AC-LCONF-305).
- **`test_purchase_order_models.py`(`:315-324`, `:448-459`)와 `test_spec_012.py`(`:250-262`)는 무변경** — 셋 다 `LineItem.objects.create()`/`_make_line_item()` 직접 ORM 호출로 `other_publisher`를 쓰는 모델 레벨 테스트이며, `LineItem.PURCHASE_STATUS_CHOICES` 자체에서는 `other_publisher`를 제거하지 않으므로(Exclusions 7번) 영향받지 않음을 이 세션에서 확인했다.

### M3 (Priority High) — 프론트엔드: API/훅 계층

- `frontend/src/services/purchaseOrderApi.ts`: `UnorderedItem` 인터페이스(`:5-14`)에서 `auto_distributor` 제거. 신규 `confirmLineItem(id: number, data: {distributor: string; unit_price: string | null}): Promise<{line_item_id: number; purchase_order_id: number; distributor: string; unit_price: string | null}>` 함수 추가(같은 파일의 `updateLineItemStatus` 패턴 참조).
- `frontend/src/hooks/usePurchaseOrderQueries.ts`: 신규 `useConfirmLineItem()` 뮤테이션 — `onSuccess`에서 `QUERY_KEYS.unordered` + `QUERY_KEYS.excludedItems` + `['purchase-orders','list']` 3개 무효화(`useUploadDailyReview`의 `:181-182` 패턴과 동일하게 리스트 키는 파라미터 프리픽스로 무효화). `onError`는 토스트만 표시하고 무효화하지 않는다(REQ-LCONF-105).

### M4 (Priority Medium) — 프론트엔드: 모달 컴포넌트 + 테이블 통합

- 신규 컴포넌트(예: `frontend/src/pages/PurchaseOrders/tabs/LineItemConfirmModal.tsx`) — shadcn `Dialog`(`frontend/src/components/ui/dialog.tsx`, `CreateAdminDialog.tsx` 선례) 기반. `distributor` state 하나를 드롭다운(`<select>`)과 자유 텍스트 `<input>`이 공유(REQ-LCONF-103) — 드롭다운 `onChange`는 `setDistributor(e.target.value)`, 자유 텍스트 `onChange`도 동일하게 `setDistributor(e.target.value)`를 호출하므로 "마지막 조작"이 자연스럽게 최종값이 된다(별도 우선순위 로직 불필요 — 단일 state 공유로 충분). `damaged_exchange` 행은 미발주 목록이 표시한 순수량(`damaged_quantity` 기반)을 그대로 초기 표시값으로 넘긴다(REQ-LCONF-108, `acceptance.md` AC-LCONF-108).
- `UnorderedItemsTab.tsx`: "자동 추천 발주처" `<th>`(`:426`)/`<td>`(`:463-471`) 제거, "발주처리" 액션 열 추가(열 수 8 유지 확인 — 빈 상태 행 `colSpan={8}`은 `:433` 그대로 둔다, REQ-LCONF-204/`acceptance.md` AC-LCONF-206으로 정식 검증). 행 클릭 시 SKU 선택 토글(`:442`)과 발주처리 버튼 클릭이 충돌하지 않도록 버튼에 `onClick={(e) => e.stopPropagation()}` 적용(같은 파일의 체크박스 `:449`, 발주 상태 select `:472` 선례와 동일한 패턴, REQ-LCONF-107/`acceptance.md` AC-LCONF-107로 정식 검증).
- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx`의 3곳(`:170, :328, :356`) `auto_distributor: null` 픽스처 라인 제거. 신규 테스트: 발주처리 버튼 클릭 → 모달 오픈, 드롭다운/자유텍스트 최종값 제출 검증(REQ-LCONF-103 판별), 성공 시 3개 쿼리 무효화 검증(`usePurchaseOrderQueries.test.tsx`의 실제 `QueryClientProvider` + spy 패턴 재사용 — SPEC-ORDER-018 v1.0.1 선례), 실패 시 무효화 없음 + 모달 유지 검증, stopPropagation 검증(AC-107), 열 수 8 검증(AC-206). M2b로 `other_publisher` 옵션이 select에서 사라지므로 이 파일의 기존 픽스처/스냅샷 중 `other_publisher`를 select 옵션으로 기대하는 부분이 있다면 함께 갱신.

### M5 (Priority Low) — 문서/후속

- `spec.md` HISTORY에 구현 결과(테스트 통과 수, 계획 대비 발산) 기록.
- plan-auditor 리뷰가 지시하는 경우에 한해 반영.

---

## 기술 접근

- 백엔드 쓰기 로직은 `ConfirmOrderView`를 참조 구현으로 삼되 복사가 아니라 LineItem 그레인에 맞게 재작성한다 — SKU 루프, 여러 LineItem 동시 처리, `already_linked` 리스트 컴프리헨션 등 배치 전용 구조는 불필요.
- `other_publisher` 거부는 `damaged_exchange` 거부의 정확한 복제다 — 새로운 패턴을 설계하지 않는다(Enforce Simplicity). 공유 메시지 상수를 `_DAMAGED_EXCHANGE_BLOCKED_MESSAGE` 바로 옆에 배치해 두 "엔드포인트별 상태 차단" 사례가 나란히 보이게 한다.
- 프론트 모달은 React Hook Form 없이 로컬 `useState` 3개(`distributor`, `unitPrice`, `error`)로 충분하다 — 이 폼은 필드 2개(단가는 선택)뿐이라 폼 라이브러리 도입은 과잉설계(Enforce Simplicity 원칙).
- `distributor` 자유 텍스트 20자 제한(REQ-LCONF-010)은 프론트에서도 `maxLength={20}` 속성으로 선반영해 불필요한 400 왕복을 줄인다(백엔드 검증이 최종 게이트, 프론트는 UX 보조).

---

## 리스크

- **R-A (필드 길이)**: `PurchaseOrder.distributor`는 `max_length=20`이다. 자유 텍스트를 명시적으로 허용하는 이 SPEC은 `ConfirmOrderView`보다 이 위험에 노출되기 쉽다 — REQ-LCONF-010(400 거부)으로 완화. 프론트 `maxLength`로 사전 차단. 정확히 20자는 성공해야 한다는 경계 조건을 AC-LCONF-015로 별도 고정.
- **R-B (표시값 괴리, 수용된 기존 제약)**: `_attach_net_quantity`(`:4333-4389`)는 발주서 목록의 `net_quantity`를 항상 `LineItem.quantity`(원본) 기준으로 재계산하며 `damaged_quantity`를 반영하지 않는다. 이 SPEC이 `damaged_exchange` 행에 대해 `PurchaseOrder.quantity`를 `damaged_quantity` 기반 순수량으로 쓰더라도(REQ-LCONF-003), 발주서 목록 페이지의 `net_quantity` 컬럼은 그 값과 다르게 표시될 수 있다 — `ConfirmOrderView`도 동일한 괴리를 이미 갖고 있는 기존 제약이며 이 SPEC의 범위에서 고치지 않는다(`research.md` §1-5). 이 제약은 `spec.md`의 "알려진 제약" 절에 규범적으로 기재되어 있다.
- **R-C (쿼리 수 — 베이스라인은 이미 알려져 있다)**: 베이스라인은 이미 `test_spec_018.py:64`에 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`으로 권위 있게 존재하며, `research.md` §1-2가 REQ-LCONF-201의 델타를 −1로 확정했으므로, 신규 값 **2**는 지금 대수적으로 도출 가능하다. M2에서 이 상수를 3→2로 갱신하고, `acceptance.md` AC-LCONF-205로 정식 고정한다. Run 단계에서는 "미지의 값을 측정"하는 것이 아니라 "도출된 값 2를 `CaptureQueriesContext`로 실측 재확인"하는 것이다.
- **R-D (MX 태그 예산 초과, 사전 존재)**: 아래 `mx_plan` 참조.
- **R-E (동시성)**: 신규 엔드포인트는 `select_for_update()` + `transaction.atomic()`으로 이중 제출을 막는다(`ConfirmOrderView`의 `:1045-1046` WARN 주석과 동일한 위험군). `test_spec_016.py`의 결정론적 SQL 단정(`:1013-1027`) + 마커 명시 스레드 테스트(`:1030-1064`) 이중 구조를 그대로 재사용한다(AC-012a/012b, ND5 해소) — 스레드 테스트 단독으로는 SQLite 기본 엔진에서 `select_for_update()`가 무시되어 판별력을 잃을 수 있다.
- **R-F (인증 가드)**: 신규 쓰기 엔드포인트가 인증 없이 호출 가능한 상태로 배포되면 임의의 발주 확정이 가능해진다. `permission_classes` 삭제만으로는 프로젝트 전역 기본값(`base.py:106-108`)이 401로 폴백하므로 이 리스크가 저절로 완화되지만, 뷰가 **다른** 값(`AllowAny` 등)을 명시적으로 잘못 설정하는 실수는 기본값 폴백으로 막을 수 없다 — AC-LCONF-014(401 응답, mutation=`AllowAny` 명시)와 AC-LCONF-014b(클래스 속성 정적 확인)가 함께 이 리스크를 커버한다(ND1 해소로 정정된 이해).
- **R-G (부적격 상태 가드가 R4의 방어선 중 하나)**: REQ-LCONF-006의 5종 부적격 상태 검사가 뚫리면(특히 `other_publisher`) API 직접 호출이나 레거시 데이터에 대해 잘못된 발주처리가 가능해진다 — 5종 전수 parametrize(AC-LCONF-004a~e)로 방어. v1.2.0의 M2b(프론트 드롭다운 제거 + 백엔드 PATCH 400 거부)가 **정상 UI 경로**에서 `other_publisher`가 애초에 재생성되지 않도록 원천 차단하므로, REQ-LCONF-006의 이 항목은 이제 "정상 경로 방어"가 아니라 "API 직접 호출/레거시 데이터 방어"로 역할이 좁아졌다.
- **R-H (레거시 고아 데이터, v1.2.0 신규, v1.3.0 범위 확장)**: M2b 적용 이전에 (수동 PATCH 지정 또는 메모 공란 Daily Review 업로드로) 생성되어 노트가 없는 `other_publisher` 행은 R4 적용 후 주문상세 화면 외에는 조회 경로가 없다 — `spec.md` "알려진 제약"에 기재, 소급 백필은 Exclusions 6번으로 범위 밖 처리.
- **R-I (검증되지 않은 전제가 근본 조치의 근거로 쓰인 재발 패턴, v1.3.0 신규 교훈)**: v1.2.0의 D4가 "Daily Review는 항상 노트를 동반한다"를 검증 없이 R4 확장의 근거로 썼다가 ND-A로 거짓임이 드러났다 — ND2(D4의 최초 트리거) 자체도 "동일 결함 패턴이 인접 명제로 이동한 것"이라는 지적을 받았다. 교훈: 근본 원인을 막는 조치를 설계할 때, 그 조치가 실제로 근본 원인 **전체**를 덮는지(부분집합만 덮는 건 아닌지)를 코드 추적으로 재확인한다 — "통로 하나를 막았다"와 "모든 통로를 막았다"는 다른 주장이다.

---

## mx_plan

대상 파일: `backend/order/purchase_order_views.py`.

**사전 상태(이 세션에서 실측, `research.md` §1-8)**: `@MX:ANCHOR` 5개(`:14, :1049, :1365, :4005, :4345`) — `.moai/config/sections/mx.yaml`의 `anchor_per_file: 3`을 이미 2개 초과. `@MX:WARN` 7개(`:638, :1045, :1468, :3046, :3146, :3318, :3989`) — `warn_per_file: 5`를 이미 2개 초과. `:4005`의 ANCHOR는 `_process_force_outbound_rows`(함수 정의 `:4021`)에 부착되어 있다 — `OutboundForceProcessView`(실제 위치 `:4199`, 별개 클래스)로 귀속시킨 것은 v1.0.0의 오기였다(D8, `research.md` §1-8에서 정정).

**결정**:

- 신규 `LineItemConfirmView`에 `@MX:ANCHOR`를 **추가하지 않는다** — 두 가지 독립적인 이유가 있다. (1) fan_in=1(이 URL 라우트만 호출)로 `fan_in_anchor: 3` 문턱값 미달, 파일 예산과 무관하게 애초에 ANCHOR 대상이 아니다. (2) 설령 fan_in이 3 이상이었더라도 파일이 이미 한도를 초과한 상태라 추가할 수 없다.
- `@MX:WARN`도 **추가하지 않는다** — `select_for_update()` + 원자적 트랜잭션 패턴은 `ConfirmOrderView`의 WARN(`:1045-1046`)과 동형의 위험이지만, 파일이 이미 `warn_per_file` 한도를 2개 초과했다. 신규 WARN을 더하는 대신 아래 NOTE 안에 이 위험을 문서화한다.
- `@MX:NOTE` **1개** 추가 — `LineItemConfirmView` 클래스 독스트링 바로 아래. 내용: (a) `select_for_update()`/원자적 트랜잭션이 `ConfirmOrderView`와 동형의 락 경합 위험을 갖는다는 사실(WARN 대신 NOTE로 문서화하는 이유 포함), (b) 에러 응답 바디가 `{"detail": ...}`가 아니라 `{"error": ...}`인 이유(URL 패밀리 컨벤션, `research.md` §1-7), (c) `PurchaseOrder.quantity`와 발주서 목록의 `net_quantity` 표시값이 `damaged_exchange` 행에서 다를 수 있다는 기존 제약(R-B) — `spec.md`의 "알려진 제약" 절을 직접 인용하는 형태로 단순화.
- `M2b`가 `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`에 추가하는 `other_publisher` 거부 분기는 기존 `damaged_exchange` 거부 분기 바로 옆에 두므로 별도의 신규 MX 태그는 불필요하다 — 기존 독스트링(`:2496-2497`, `:2550-2551`)의 "damaged_exchange" 언급에 "other_publisher"를 나란히 추가하는 정도로 충분하다(둘 다 태그가 아니라 일반 독스트링 문장).
- `M2b`가 `UploadDailyReviewView`의 CS 분기(`:1780-1817`)에 추가하는 메모 공란 기본 노트 로직(REQ-LCONF-309)도 신규 MX 태그가 필요하지 않다 — 조건 분기 1개를 좁히는 수준의 변경이고, 그 함수 자체는 이미 별도 ANCHOR/WARN 후보가 아니다(fan_in·복잡도 변화 없음). `UploadDailyReviewView` 클래스 독스트링(`:1443-1463` 부근)에 REQ-LCONF-309를 언급하는 한 문장만 추가한다.
- 기존 5개 ANCHOR/7개 WARN/2개 강등 NOTE는 이 SPEC에서 손대지 않는다 — 범위 밖(Scope Discipline).
- **후속 과제(이 SPEC 범위 밖)**: 파일이 이미 ANCHOR 2개·WARN 2개 초과 상태라는 사실은 별도의 "MX 태그 정리" 작업으로 다뤄야 한다 — 이 SPEC에서 겸사겸사 정리하지 않는다(Drive-by 리팩터 금지, Scope Discipline).

---

## 파일 목록

| 경로 | 구분 | 비고 |
|------|------|------|
| `backend/order/purchase_order_views.py` | MODIFY | `LineItemConfirmView` 신설(NEW 클래스), `UnorderedItemsView.get()` 축소 + 독스트링(`:323-328`) 갱신, `EXCLUDED_PURCHASE_STATUSES` 축소 + `ExcludedItemsView` 독스트링(`:414-427`) 갱신, `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`에 `other_publisher` 거부 분기 추가(M2b), `UploadDailyReviewView`의 타출판사 분기(`:1805` 부근)에 메모 공란 시 기본 노트 생성 로직 추가(M2b, REQ-LCONF-309, v1.3.0 신규) |
| `backend/order/urls.py` | MODIFY | 신규 라우트 1개 등록 |
| `backend/order/tests/test_spec_025.py` | NEW | R1 전항 커버(5종 부적격 상태 parametrize, 401+정적 인증 케이스, 20자 경계값, mock-spy 재계산 검증, 동시성 검증 분할(012a/012b) 포함) |
| `backend/order/tests/test_spec_018.py` | MODIFY | `:57`(튜플 축소), `:183, :439, :474`(기대값 반전), `:320, :516`(모듈러 인덱싱 수정 — **필수, 안 하면 IndexError**), `:64`(쿼리 핀 3→2), `:542-543, :550`(파급 재확인) — 총 7개 참조 지점 + 상수 갱신 1건 |
| `backend/order/tests/test_purchase_orders.py` | MODIFY | `:300-313`/`:315-325` auto_distributor 단정 2건 재작성 또는 삭제+흡수, `:5` 헤더 주석 갱신(M2), `:2306-2319` `test_patch_all_six_choices`를 5개 선택값으로 축소 + `test_patch_other_publisher_rejected`(단건) 신설 + bulk 버전 신설(M2b) |
| `backend/order/tests/test_daily_review_upload.py` | **MODIFY (v1.3.0 신규 대상)** | 신규 테스트 3건(AC-LCONF-308a 메모 공란/308b 메모 있음/308c 대조군) — `test_spec_024.py`/기존 케이스는 무수정(위 §M2b 근거 참조) |
| `frontend/src/services/purchaseOrderApi.ts` | MODIFY | `UnorderedItem` 타입 축소, `confirmLineItem` 신설(M3), `PURCHASE_STATUS_OPTIONS`에서 `other_publisher` 제거·`PURCHASE_STATUS_LABELS`는 유지(M2b) |
| `frontend/src/services/purchaseOrderApi.test.ts` | **MODIFY (v1.2.0 신규 대상)** | `:23-35` 6개→5개 옵션 갱신, `other_publisher` 배제 케이스 신설(`damaged_exchange` `:16-21` 패턴), `PURCHASE_STATUS_LABELS`에 `other_publisher` 유지 케이스 신설(`:43-45` 패턴) |
| `frontend/src/hooks/usePurchaseOrderQueries.ts` | MODIFY | `useConfirmLineItem` 신설 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` | MODIFY | 열 제거/추가, 모달 통합, stopPropagation(M4). `PURCHASE_STATUS_OPTIONS` 소스 변경이 4개 렌더 사이트(`:207,294,344,495`)에 자동 전파되므로 이 파일 자체의 코드 변경은 불필요(M2b) |
| `frontend/src/pages/PurchaseOrders/tabs/LineItemConfirmModal.tsx` | NEW | 발주처리 모달 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.test.tsx` | MODIFY | `:170, :328, :356` 픽스처 + 신규 테스트(모달, stopPropagation, 열 수 8), `other_publisher` select 옵션을 기대하는 기존 픽스처가 있다면 갱신 |
| `frontend/src/pages/PurchaseOrders/tabs/LineItemConfirmModal.test.tsx` | NEW | 모달 단위 테스트 |

**무변경 확인(이 세션에서 코드 대조, 회귀 걱정 없음)**: `test_purchase_order_models.py:315-324,448-459`, `test_spec_012.py:250-262`(전부 `LineItem.objects.create()`/`_make_line_item()` 직접 ORM 호출, PATCH 엔드포인트 미경유), `test_purchase_orders.py:2236-2253`(동일 사유), `test_spec_024.py`의 타출판사 관련 전체(모든 픽스처가 Status 셀에 비공백 값을 명시하고 노트 존재를 단정하는 코드가 없음, 이 세션에서 `grep`으로 재확인 — REQ-LCONF-309 적용 후에도 무수정 통과).

**회귀 검증 대상(무수정, 재실행만)**: `backend/order/tests/test_auto_dist.py`(`auto_select_distributor`/`resolve_publisher_distributor` 참조 40건), `backend/order/tests/test_spec_024.py`(`DistributorVendorRule` 관련 참조 **10건** — `:13,:30,:89,:108,:129,:162,:186,:210,:228,:246`, ND3 정정), `VendorRulesTab.tsx` 관련 프론트 테스트, `DistributorVendorRuleListCreateView`/`DistributorVendorRuleDeleteView` 백엔드 테스트 — `acceptance.md` AC-LCONF-204가 이 스위트들의 통과를 요구한다. `test_daily_review_upload.py`는 회귀 검증 대상이 아니라 위 §M2b에 명시한 대로 신규 테스트 3건이 **추가**되는 MODIFY 대상이다(혼동 방지를 위해 별도 파일 목록 행으로 분리했다).
