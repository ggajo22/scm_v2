---
id: SPEC-ORDER-019
document: acceptance
version: 1.0.0
status: draft
updated: 2026-08-13
---

# 인수 기준 — SPEC-ORDER-019 Daily Review 업로드 배포처 행 메모 유실

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의
AC-MEMO-XXX / REQ-MEMO-XXX ID를 인용해 상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` ACCEPTANCE CRITERIA 절의 동일 AC 항목이
선언한 것과 완전히 일치한다. 어느 한쪽을 수정할 때 반드시 함께 갱신한다.

[HARD] **판별력 요건.** 각 시나리오는 `판별력:` 절에서 자신을 깨뜨리는 구체적 mutation을
명시한다. 모든 시나리오는 **최소한 "구현을 되돌리면 실패한다"를 만족**한다 — 현재
무수정 코드에 대해 통과하는 시나리오는 이 문서에 하나도 없다. 이 프로젝트는
판별력 없는 인수 기준으로 이미 두 번 손해를 봤다(SPEC-ORDER-018 v1.0.3/v1.0.4).

**검증 레이어**: 전량 `[BE]` — `backend/order/tests/test_spec_019.py`의 pytest 시나리오다.
이 SPEC은 프론트엔드를 변경하지 않으므로(`spec.md` 설계 결정 E) `[FE]` 시나리오가 없다.
AC-MEMO-009가 표시 경로를 다루지만, 검증 지점은 프론트엔드가 소비하는 **API 응답**이다.

**공통 픽스처 관례**: `user` / `auth_client` 픽스처와 `_make_order` / `_make_line_item`
헬퍼는 `backend/order/tests/test_daily_review_upload.py:42-44`, `:47-52`, `:55-58`,
`:61-74`를 그대로 복제한다. URL 상수 `UPLOAD_DAILY_URL`은 같은 파일 `:28`의 값을 쓴다.

**엑셀 빌더**: 신규 템플릿은 `_make_new_template_excel`(`:743-822`) 형태를 복제한다 —
행 dict의 키는 `sku` / `status`(= 메모 열) / `selected`(= '선택' 열) / `order_name` /
`bs_price` 등(`:792-812`). 레거시 형식은 `_make_daily_review_excel`(`:77-` , 헤더 `:85-94`,
메모 열 `:106`) 형태를 복제한다. **메모 열이 아예 없는 파일**은 `:2349-2353`처럼 헤더를
직접 조립해 만든다.

**쿼리 수 측정**: `from django.test.utils import CaptureQueriesContext`
(`test_daily_review_upload.py:2128-2129`), 사용례 `:2138`.

**전 필드 스냅샷 + 노트 수 대조 관례**: `backend/order/tests/test_spec_018.py:197-216`.

---

## 노트 생성 — 핵심 계약

### AC-MEMO-001 — 배포처 행의 메모가 정확히 1건의 발주 노트가 된다 `[BE]`

Traces: REQ-MEMO-001, REQ-MEMO-002, REQ-MEMO-003, REQ-MEMO-004, REQ-MEMO-005, REQ-MEMO-006

- **Given**: `_make_order(shopify_order_id=..., name="#M001")` 아래에
  `_make_line_item(order, sku="9788936479497", quantity=1, shopify_line_item_id=1)`을 만든다.
  이 LineItem은 기본 상태이므로 `purchase_status="unordered"`이고 `PurchaseOrder`에 연결되어
  있지 않아 `_reorder_candidate_filter`(`purchase_order_views.py:107-110`)를 통과한다.
  신규 템플릿 파일을 만든다 — 행 1건:
  `{"order_name": "#M001", "sku": "9788936479497", "selected": "BOOXEN",
  "status": "품절이지만 북센 시도", "bs_price": 9000}`.
- **When**: `auth_client`로 `UPLOAD_DAILY_URL`에 multipart POST 한다.
- **Then**: HTTP 201이며
  - (a) `LineItemNote.objects.filter(line_item=li).count() == 1`
  - (b) 그 노트의 `content == "품절이지만 북센 시도"` — **문자 단위로 완전히 동일**하다.
    배포처명(`BOOXEN`/`booxen`)이 앞뒤에 붙지 않았고 잘리지도 않았다(REQ-MEMO-002).
  - (c) `assignee == "발주"`(REQ-MEMO-003). `"CS"`도 `"한국창고"`도 `"미국창고"`도 아니다.
  - (d) `note_type == ""`(REQ-MEMO-004).
  - (e) `author is None`(REQ-MEMO-005).
  - (f) `is_resolved is False`(REQ-MEMO-006).
- **판별력**: 구현을 되돌리면 (a)가 `0 == 1`로 실패한다 — 현재 무수정 코드에서 이 시나리오는
  실패한다. (c)를 모델 기본값에 맡기면 `"CS"`가 되어(`models.py:277`) 실패한다.
  (d)를 CS 분기(`:1657`)처럼 `note_type=note_type`으로 복사하면 배포처 행의 `note_type`이
  `None`이라 실패하거나 값이 새어 들어와 실패한다.

### AC-MEMO-002 — 공백만 있는 메모는 노트를 만들지 않는다 `[BE]`

Traces: REQ-MEMO-007

- **Given**: Order 1개(`name="#M002"`) 아래에 LineItem 2건 —
  `li_blank`(`sku="SKU-BLANK"`, `shopify_line_item_id=1`),
  `li_real`(`sku="SKU-REAL"`, `shopify_line_item_id=2`). 둘 다 `unordered`이고 PO 미연결.
  신규 템플릿 파일에 행 2건:
  - `{"order_name": "#M002", "sku": "SKU-BLANK", "selected": "BOOXEN", "status": "   ",
    "bs_price": 9000}` — **공백 3칸**
  - `{"order_name": "#M002", "sku": "SKU-REAL", "selected": "BOOXEN", "status": "재고 확인 요청",
    "bs_price": 9000}`
- **When**: `auth_client`로 `UPLOAD_DAILY_URL`에 POST 한다.
- **Then**: HTTP 201이며
  - (a) `LineItemNote.objects.count()`가 정확히 **1**이다.
  - (b) 그 1건의 `line_item_id == li_real.pk`이고 `content == "재고 확인 요청"`.
  - (c) `LineItemNote.objects.filter(line_item=li_blank).exists()`가 **False**다.
  - (d) 두 행 모두 확정됐다 — `li_blank.confirmed_distributor == "booxen"`이고
    `PurchaseOrder.objects.filter(sku="SKU-BLANK").exists()`가 True다. 즉 메모가 없다는
    이유로 행이 스킵된 것이 **아니다**.
- **판별력**: 두 방향 모두 잡는다.
  - 가드(`if note is not None`, CS 분기 `:1650` 형태)를 빠뜨리면 (a)가 `2 == 1`로 실패한다.
    `_str_or_none`(`excel_utils.py:704-705`)이 `"   "`를 `None`으로 바꾸므로 가드 없는
    구현은 `content=None`으로 `TextField` 삽입을 시도해 IntegrityError로 실패하거나,
    `note or ""`로 감싼 구현은 빈 노트를 만들어 실패한다.
  - 구현을 되돌리면 (a)가 `0 == 1`로 실패한다.
  - (d)는 "메모 없으면 행 전체를 건너뛰는" 잘못된 구현을 잡는다.

### AC-MEMO-003 — 메모 열이 없는 파일은 회귀하지 않는다 `[BE]`

Traces: REQ-MEMO-008

- **Given**: 두 부분으로 나눈다.
  - **(부분 1)** Order `#M003A` + LineItem `sku="SKU-NOCOL"`. `_make_daily_review_excel`을
    쓰지 **않고** `openpyxl`로 직접 헤더를 조립한다(`test_daily_review_upload.py:2349-2353`
    관례) — `["주문번호", "ISBN", "선택"]` 3열만, **`"메모"` 열 없음**. 데이터 행:
    `["#M003A", "SKU-NOCOL", "북센"]`. 이 헤더는 `ISBN`과 `선택`을 모두 갖추므로
    `parse_daily_review_excel`의 판별(`excel_utils.py:784-791`)을 통과하고
    `is_new_template`은 False가 된다(`:803`) → `note_idx`는 `header.index("메모")`가 아니라
    `None`이 된다(`:825`).
  - **(부분 2)** Order `#M003B` + LineItem `sku="SKU-HASCOL"`. `_make_daily_review_excel`
    (`:77-`, 메모 열 포함) 형태로 행 1건:
    `{"order_name": "#M003B", "isbn": "SKU-HASCOL", "selected": "북센", "note": "레거시 메모"}`.
- **When**: 두 파일을 각각 `UPLOAD_DAILY_URL`에 POST 한다.
- **Then**:
  - (a) 부분 1: HTTP 201, `LineItemNote.objects.filter(line_item=li_nocol).exists()`가
    **False**다.
  - (b) 부분 1: 그럼에도 행은 확정됐다 — `li_nocol.confirmed_distributor == "booxen"`이고
    `PurchaseOrder.objects.filter(sku="SKU-NOCOL").exists()`가 True이며 응답의
    `confirmed_count`가 1, `errors`가 비어 있다.
  - (c) 부분 2: `LineItemNote.objects.filter(line_item=li_hascol).count() == 1`이고
    그 `content == "레거시 메모"`, `assignee == "발주"`.
- **판별력**:
  - 부재 열 가드 없이 `item["note"]`로 접근하거나 `note`를 무조건 저장하는 구현은
    (a)에서 실패한다.
  - 구현을 되돌리면 (c)가 `0 == 1`로 실패한다 — **이 절이 이 시나리오의 반전 판별력이다.**
    (a)/(b)만으로는 되돌린 코드도 통과하므로 (c) 없이는 판별력이 없다.
  - (b)는 "메모 열이 없으면 파일 전체를 거부"하는 과잉 구현을 잡는다.

## 배치 쓰기

### AC-MEMO-004 — 메모를 가진 배포처 행이 대량이어도 쿼리 수가 상수로 유지된다 `[BE]`

Traces: REQ-MEMO-009, REQ-MEMO-010

- **Given**: `test_daily_review_upload.py:2036-2108`의 `_make_bulk_daily_review_fixture`와
  같은 구조의 픽스처를 만들되 **결정적 차이 하나**를 둔다 — PO 분기로 가는 행의
  `status`를 `""`(`:2083`)가 아니라 **행마다 다른 비어 있지 않은 문자열**
  (예: `f"메모-{i}"`)로 채운다. 기존 픽스처의 이 공백값 때문에 현행 상한 테스트
  (`:2146-2160`)는 이 분기를 전혀 측정하지 못한다(`research.md` §4.2).
  LineItem 시딩은 `:2117-2125`의 `_seed_actionable_line_items` 형태를 따른다.
- **When**: 300행 파일과 500행 파일을 각각 `CaptureQueriesContext`
  (`:2128-2129`, 사용례 `:2138`)로 감싸 `auth_client`로 POST 한다.
- **Then**:
  - (a) 두 요청 모두 HTTP 201이며 `confirmed_count`가 각 파일의 actionable 행 수와 같다.
  - (b) 300행 요청의 쿼리 수가 **정확히 상수 `UPLOAD_QUERY_CEILING`(= 35) 미만**이다 —
    자기 자신과의 비교가 아니라 고정된 절대값이며, 기존 테스트 `:2160`이 쓰는 것과 같은 값이다.
  - (c) 500행 요청의 쿼리 수도 같은 절대 상한 미만이며, 300행 대비 증가분이
    소수의 상수(기존 `:2162-2169`가 쓰는 판정 폭) 이내다.
  - (d) 생성된 `LineItemNote` 수가 PO 분기로 간 행이 해석한 LineItem 수와 **정확히 같다**
    (0이 아니다). 각 노트의 `assignee`가 `"발주"`다.
- **판별력**:
  - 행별 `LineItemNote.objects.create()`로 구현하면 (b)가 `335 < 35`류로 실패한다 —
    300행 중 PO 분기 행 수만큼 INSERT가 늘어난다. 이것이 **이 SPEC의 배치 제약을 실제로
    강제하는 유일한 시나리오**다.
  - 구현을 되돌리면 (d)가 `0 == N`으로 실패한다.
  - (b)를 상대 비교(300행 대 500행 동등성)로만 쓰면 판별력이 사라진다 — 두 측정 모두에
    비용이 들어가 상쇄되기 때문이다(SPEC-ORDER-018 v1.0.4가 같은 함정을 실측으로 확인했다).
    그래서 **절대값**을 단정한다.
  - **상수 재도출**: `UPLOAD_QUERY_CEILING`이 다른 SPEC 때문에 정당하게 바뀌었다면,
    기존 `:2160`의 값과 함께 갱신한다. 두 곳이 서로 다른 값을 쓰면 안 된다.

## 재업로드

### AC-MEMO-005 — 같은 파일을 두 번 올려도 노트는 1건이다 `[BE]`

Traces: REQ-MEMO-011, REQ-MEMO-012

- **Given**: Order `#M005` + LineItem `sku="SKU-IDEM"`(`unordered`, PO 미연결).
  신규 템플릿 행 1건:
  `{"order_name": "#M005", "sku": "SKU-IDEM", "selected": "BOOXEN", "status": "중복 확인용 메모",
  "bs_price": 9000}`. **동일한 `file_bytes`를 재사용**한다(두 번 만들지 않는다).
- **When**: 같은 바이트를 `io.BytesIO`로 두 번 감싸 `UPLOAD_DAILY_URL`에 연속 2회 POST 한다.
- **Then**:
  - (a) 1차 응답이 HTTP 201이고 `confirmed_count == 1`, `skipped_count == 0`.
  - (b) 1차 직후 `LineItemNote.objects.filter(line_item=li).count() == 1`.
  - (c) 2차 응답이 HTTP 201이고 `confirmed_count == 0`, **`skipped_count == 1`** —
    1차가 만든 `PurchaseOrder` 연결 때문에 `_reorder_candidate_filter`
    (`purchase_order_views.py:109`의
    `.exclude(purchase_status="unordered", purchase_orders__isnull=False)`)가 이 LineItem을
    후보에서 빼고, 행은 `:1637-1639`에서 스킵된다.
  - (d) 2차 직후에도 `LineItemNote.objects.filter(line_item=li).count() == 1`이며
    그 노트의 `pk`가 1차 직후에 기록해 둔 `pk`와 **동일**하다(새로 만들고 지운 것이 아니다).
  - (e) `PurchaseOrder.objects.filter(sku="SKU-IDEM").count() == 1`.
- **판별력**:
  - `_reorder_candidate_filter`가 넓어져 이 LineItem이 2차에도 후보가 되면 (c)의
    `skipped_count == 1`과 (d)의 `count == 1`이 동시에 실패한다. 멱등성은 **강제되지 않고
    상속되는** 성질이므로(`spec.md` 설계 결정 C) 이 잠금장치가 없으면 나중에 조용히 깨진다.
  - 구현을 되돌리면 (b)가 `0 == 1`로 실패한다.
  - (c)의 `skipped_count` 단정은 "2차에도 확정 처리는 되지만 노트만 안 만든다"는 잘못된
    멱등성 구현(내용 비교 dedup 등)을 잡는다 — `spec.md` REQ-MEMO-012가 금지하는 형태다.

## 분기 격리

### AC-MEMO-006 — 세 분기가 한 업로드 안에서 각자의 assignee로 정확히 3건을 만든다 `[BE]`

Traces: REQ-MEMO-013

- **Given**: Order `#M006` 아래에 LineItem 3건, 전부 `unordered` + PO 미연결 —
  `li_cs`(`sku="SKU-CS"`), `li_wh`(`sku="SKU-WH"`), `li_dist`(`sku="SKU-DIST"`).
  `li_wh`를 위해 `WarehouseStock.objects.create(isbn="SKU-WH", location="korea", quantity=100)`
  를 만든다(`test_daily_review_upload.py:2125` 관례).
  신규 템플릿 행 3건, **각각 서로 다른 메모**:
  - `{"order_name": "#M006", "sku": "SKU-CS", "selected": "주문취소", "status": "CS 쪽 메모"}`
  - `{"order_name": "#M006", "sku": "SKU-WH", "selected": "재고", "status": "한국재고"}`
  - `{"order_name": "#M006", "sku": "SKU-DIST", "selected": "BOOXEN", "status": "배포처 쪽 메모",
    "bs_price": 9000}`
- **When**: `auth_client`로 `UPLOAD_DAILY_URL`에 POST 한다.
- **Then**: HTTP 201이며 `LineItemNote.objects.count()`가 정확히 **3**이고
  - (a) `li_cs`의 노트 — `content == "CS 쪽 메모"`, `assignee == "CS"`,
    `note_type == "주문취소"`. `li_cs.purchase_status == "order_cancelled"`
    (`_NOTE_TYPE_STATUS_MAP` `excel_utils.py:615`).
  - (b) `li_wh`의 노트 — `content == "한국재고"`, `assignee == "한국창고"`,
    `note_type == ""`. `li_wh.purchase_status == "in_stock"`.
    (창고 분기는 `status` 값을 위치 해석에도 쓰고 노트 본문에도 그대로 쓴다 —
    `purchase_order_views.py:1678`과 `:1713`.)
  - (c) `li_dist`의 노트 — `content == "배포처 쪽 메모"`, `assignee == "발주"`,
    `note_type == ""`. `li_dist.confirmed_distributor == "booxen"`.
  - (d) 세 노트의 `line_item_id`가 서로 다르다.
- **판별력**:
  - 구현을 되돌리면 총 노트 수가 `2 != 3`으로 실패한다.
  - 신규 분기에 `assignee="CS"`(모델 기본값)를 쓰면 (c)가 실패한다.
  - 신규 분기가 CS 분기의 `note_type=note_type`(`:1657`)을 복사하면 (c)의
    `note_type == ""`이 실패한다.
  - CS/창고 분기를 건드리면 (a)/(b)가 실패한다 — 이것이 REQ-MEMO-013의 회귀 잠금이다.

### AC-MEMO-007 — 한 행이 여러 LineItem을 해석하면 LineItem마다 노트가 생긴다 `[BE]`

Traces: REQ-MEMO-001, REQ-MEMO-014, REQ-MEMO-015

- **Given**: Order `#M007` 아래에 **같은 SKU** `"SKU-MULTI"`인 LineItem 2건 —
  `li_a`(`quantity=2`, `shopify_line_item_id=1`), `li_b`(`quantity=3`,
  `shopify_line_item_id=2`). 둘 다 `unordered` + PO 미연결. 이 둘은
  `lineitems_by_key[(order.id, "SKU-MULTI")]`(`purchase_order_views.py:1582-1590`)에 함께
  담긴다. 신규 템플릿 행 **1건**:
  `{"order_name": "#M007", "sku": "SKU-MULTI", "selected": "BOOXEN", "status": "묶음 메모",
  "bs_price": 9000}`.
  대조군으로 동일 픽스처를 다른 Order(`#M007N`)에 만들고 `status: ""`인 파일도 준비한다.
- **When**: 두 파일을 각각 POST 한다.
- **Then**:
  - (a) 메모 있는 쪽: `LineItemNote.objects.filter(line_item__in=[li_a, li_b]).count() == 2`.
  - (b) 두 노트의 `line_item_id` 집합이 정확히 `{li_a.pk, li_b.pk}`다 — 한쪽에 2건이
    몰려 있지 않다.
  - (c) 두 노트 모두 `content == "묶음 메모"`, `assignee == "발주"`.
  - (d) `PurchaseOrder.objects.filter(sku="SKU-MULTI")`가 정확히 1건이고 그
    `quantity == 5`(2+3)이며 `po.line_items.all()` 집합이 `{li_a, li_b}`다
    (`:1848-1864`의 그룹 합산이 그대로 동작한다).
  - (e) 메모 있는 쪽과 대조군의 응답 `confirmed_count` / `skipped_count`가 서로 **동일**하다.
- **판별력**:
  - `unordered_lis[0]`에만 노트를 붙이는 구현은 (a)가 `1 == 2`로 실패한다. 기존 두 분기가
    `for li in unordered_lis:`로 순회하는 관례(CS `:1651`, 창고 `:1709`)를 따르지 않은 경우다.
  - 구현을 되돌리면 (a)가 `0 == 2`로 실패한다.
  - (d)는 노트 추가가 PO 그룹 누적(`:1756`)을 건드리지 않았음을 고정한다.
  - (e)는 노트 경로가 카운터에 영향을 주지 않았음을 고정한다(REQ-MEMO-015).

## 부수효과 부재

### AC-MEMO-008 — 메모 유무가 노트 외의 어떤 것도 바꾸지 않는다 `[BE]`

Traces: REQ-MEMO-014, REQ-MEMO-015, REQ-MEMO-016

- **Given**: 동일한 구성의 Order/LineItem 세트를 두 벌 만든다(`#M008A`, `#M008B`) —
  각각 배포처 행 3건에 대응하는 LineItem 3건, 전부 `unordered` + PO 미연결, `title`과
  `quantity`를 채운다. 파일도 두 개 — 두 파일은 `status` 열 값(`""` vs 실제 메모)과
  `order_name`/`sku` 접두사를 제외하면 완전히 동일하다.
- **When**: 두 파일을 각각 POST 한다. 각 요청 후 해당 세트의
  `LineItem.objects.filter(...).order_by("pk").values()`와
  `PurchaseOrder.objects.filter(...).order_by("pk").values()`를 뜬다
  (`test_spec_018.py:197` 관례).
- **Then**:
  - (a) 두 응답의 `confirmed_count`, `skipped_count`, `errors`가 서로 동일하고,
    `confirmed_by_distributor`의 배포처별 항목 수도 동일하다(REQ-MEMO-015).
  - (b) 두 세트의 LineItem 스냅샷이 pk·order_id·sku를 제외한 **모든 필드에서 동일**하다 —
    특히 `confirmed_distributor`, `confirmed_price`, `purchase_status`,
    `logistics_status`, `rack_number`(REQ-MEMO-014).
  - (c) 두 세트의 PurchaseOrder 스냅샷이 pk·sku·`created_at`을 제외한 모든 필드에서
    동일하다 — 특히 `distributor`, `quantity`, `unit_price`, `status`.
  - (d) 메모 있는 세트의 `LineItemNote` 수가 3, 메모 없는 세트가 0이다.
  - (e) `python manage.py makemigrations --check --dry-run`이 변경 없음을 보고한다
    (REQ-MEMO-016). `git diff`에 `backend/order/models.py` 변경이 없고
    `backend/order/migrations/`에 신규 파일이 없다.
- **판별력**:
  - 노트 경로가 `confirmed_count`/`skipped_count`를 건드리면 (a)가 실패한다.
  - 노트 생성을 위해 `continue`를 넣거나 흐름을 바꿔 PO 그룹 누적(`:1756`)이나 카운터
    증가(`:1758-1762`)를 건너뛰면 (b)/(c)가 실패한다.
  - 구현을 되돌리면 (d)가 `0 == 3`으로 실패한다 — **이 절이 이 시나리오의 반전 판별력이다.**
    (a)~(c)만으로는 되돌린 코드도 통과한다.
  - (e)는 `ASSIGNEE_CHOICES`/`NOTE_TYPE_CHOICES`(`models.py:242-247`, `:249-259`)에 값을
    추가한 구현을 잡는다.

## 표시 경로

### AC-MEMO-009 — 새 노트가 미해결 목록에 나타나고 타출판사 내보내기에는 섞이지 않는다 `[BE]`

Traces: REQ-MEMO-017, REQ-MEMO-018

- **Given**: Order `#M009`(`name="#M009"`) + LineItem
  `sku="SKU-SHOW"`, `title="표시 확인용 도서"`(`unordered`, PO 미연결).
  대조군으로 `note_type="타출판사"`, `content="아가페"`, `is_resolved=False`인
  `LineItemNote`를 다른 LineItem에 하나 직접 만들어 둔다 — 내보내기가 원래 무엇을
  반환하는지 고정하기 위해서다.
  신규 템플릿 행 1건:
  `{"order_name": "#M009", "sku": "SKU-SHOW", "selected": "BOOXEN", "status": "표시 확인 메모",
  "bs_price": 9000}`.
- **When**: `UPLOAD_DAILY_URL`에 POST 한 뒤, `auth_client`로
  (1) `GET /api/orders/line-item-notes/`(`backend/order/views.py:269`)와
  (2) `GET /api/orders/line-item-notes/export/?publisher=other`(`:298`, `:310-324`)를 호출한다.
- **Then**:
  - (a) (1)이 HTTP 200이며 응답 목록에 새 노트가 **포함**된다 — `content == "표시 확인 메모"`,
    `assignee == "발주"`, `is_resolved is False`인 항목이 정확히 1건이다
    (`LineItemNoteUnresolvedListView`의 `filter(is_resolved=False)` `:279`).
  - (b) 그 항목이 `order_name == "#M009"`, `line_item_sku == "SKU-SHOW"`,
    `line_item_title == "표시 확인용 도서"`, `line_item_id == li.pk`를 담고 있다
    (`LineItemNoteUnresolvedSerializer` `serializers.py:94-97`). 즉 담당자가 어느 주문의 어느
    품목인지 식별할 수 있으며 **프론트엔드 변경이 필요 없다**.
  - (c) (2)의 응답 바이트에 `"표시 확인 메모"`도 `"SKU-SHOW"`도 등장하지 않는다.
    대조군의 `"아가페"` 노트는 그대로 존재한다(내보내기 자체는 정상 동작한다).
- **판별력**:
  - `note_type`을 `"타출판사"`로 설정한 구현은 (c)가 실패한다 —
    `views.py:314`의 `filter(is_resolved=False, note_type="타출판사")`에 걸려 발주 메모가
    출판사용 엑셀에 새어 나간다. 이것이 `spec.md` 설계 결정 B가 기각한 유일한 실피해 값이다.
  - 구현을 되돌리면 (a)가 실패한다(항목 0건).
  - (b)는 `assignee`가 `LineItemNotesPage.tsx:48`의 `assignee === tab` 필터를 통과하는지
    API 수준에서 확인한다 — `"발주"`가 아니면 `:343`의 세 탭 중 어디에도 뜨지 않는다.
  - (c)의 대조군은 "내보내기가 항상 빈 응답을 준다"는 가짜 통과를 막는다.

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 테스트 번호 | 검증 대상 REQ |
|---|---|---|---|
| AC-MEMO-001 `[BE]` | `test_spec_019.py` | T1 | 001, 002, 003, 004, 005, 006 |
| AC-MEMO-002 `[BE]` | `test_spec_019.py` | T2 | 007 |
| AC-MEMO-003 `[BE]` | `test_spec_019.py` | T3 | 008 |
| AC-MEMO-004 `[BE]` | `test_spec_019.py` | T4 | 009, 010 |
| AC-MEMO-005 `[BE]` | `test_spec_019.py` | T5 | 011, 012 |
| AC-MEMO-006 `[BE]` | `test_spec_019.py` | T6 | 013 |
| AC-MEMO-007 `[BE]` | `test_spec_019.py` | T7 | 001, 014, 015 |
| AC-MEMO-008 `[BE]` | `test_spec_019.py` | T8 | 014, 015, 016 |
| AC-MEMO-009 `[BE]` | `test_spec_019.py` | T9 | 017, 018 |

시나리오로 검증하지 않는 요구사항: **없다.** REQ-MEMO-016은 AC-MEMO-008 (e)가 부분적으로
다루되, `makemigrations --check` 게이트는 `plan.md` 완료 조건에서 CI 수준으로도 확인한다.

**추가 회귀 게이트**(신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `backend/order/tests/test_daily_review_upload.py` **전량** — 특히
  - `TestUploadDailyReviewQueryCountCeiling`(`:2111-2169`) — 상한 `< 35`(`:2160`)가 그대로
    통과해야 한다
  - CS 노트 테스트(`:1067-1091`, `:1135-1143`)
  - 창고 노트 테스트(`:517-534`, `:1404-1454`, `:1475-1533`)
  - 교차 주문 동일 SKU(`:2254-2339`)
- `backend/order/tests/test_purchase_orders.py` 전량 — 특히 `ConfirmOrderView` 노트 계약
  3건(`:1412-1430`, `:1432-1450`, `:1452-1470`). 이 SPEC은 `ConfirmOrderView`를 건드리지
  않으므로 무조건 통과해야 한다.
- `backend/order/tests/test_line_item_notes.py` 전량
- `backend/order/tests/test_spec_018.py` 전량 — `_reorder_candidate_filter` 회귀 감시선

**주의 — 기존 픽스처의 부수 변화(테스트 실패 아님)**: `test_daily_review_upload.py`에는
배포처 행의 `status`에 `"정상"` 등 비어 있지 않은 값을 넣는 픽스처가 다수 있다
(`:838`, `:862`, `:916-917`, `:935`, `:1325`, `:1350`, `:1370`, `:1392`, `:2207`).
구현 후 이 픽스처들은 `content="정상"`인 발주 노트를 만들게 된다. **그중 어떤 테스트도 노트
수를 단정하지 않으므로 실패하지 않는다**(`research.md` §8에서 전수 확인 — 기존 노트 단정은
전부 `LineItemNote.objects.get(line_item=li)` 형태로 특정 LineItem에 스코프되어 있다).
이 픽스처 관행이 실제 파일의 성격을 반영하는지가 `research.md` §9의 스캔 대상이었고,
**결과는 반영하지 않는다**(§9.0.1) — 운영 파일 198개의 배포처 행 메모에서 `"정상"`류
상투어는 0건이다. 픽스처만의 관행이며, 저가치 노트 대량 생성 시나리오는 성립하지 않는다.
