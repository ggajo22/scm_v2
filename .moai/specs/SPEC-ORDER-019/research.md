---
id: SPEC-ORDER-019
document: research
version: 1.0.2
status: completed
updated: 2026-08-13
---

# 조사 — SPEC-ORDER-019 Daily Review 업로드 배포처 행 메모 유실

이 문서의 모든 `file:line` 인용은 **이 세션에서 해당 파일을 직접 읽어 확인**했다. 기준 커밋은
`9f1f82b`이며, 선행 SPEC 문서(특히 SPEC-ORDER-018)의 인용을 재사용하지 않았다 —
SPEC-ORDER-016 v1.0.5와 SPEC-ORDER-018 v1.0.3이 기록한 허구 인용 / 줄 번호 표류 사고를
반복하지 않기 위한 조치다.

---

## 1. 결함의 정확한 위치

### 1.1 세 갈래 분기와 메모 처리

`UploadDailyReviewView`(`backend/order/purchase_order_views.py:1370`)의 본문 루프
(`:1622`)는 각 `(주문명, sku)` 행을 세 갈래 중 하나로 보낸다. 행의 메모 값은 루프 진입 직후
`:1632`에서 한 번 읽힌다.

```
:1631    distributor_code = item["distributor"]
:1632    note = item.get("note")
:1633    note_type = item.get("note_type")
```

| 분기 | 조건 | 위치 | `note` 사용 | `LineItemNote` 생성 |
|---|---|---|---|---|
| CS | `note_type and not distributor_code`(`:1644`) | `:1644-1662` | 가드 `:1650` | **예** — `:1652-1660`, `assignee="CS"`(`:1658`), `note_type=note_type`(`:1657`) |
| 창고 | `is_warehouse`(`:1671-1675`) | `:1675-1717` | 위치 해석 `:1678` + 가드 `:1705` | **예** — `:1710-1717`, `assignee`는 `:1708`에서 위치로 결정 |
| 배포처(비창고) | 위 둘 다 아님 | **`:1719-1756`** | **없음** | **아니오** |

배포처 분기(`:1719-1756`)의 본문을 전부 읽었다. `note` 식별자가 **한 번도 등장하지
않는다.** 이 분기가 쓰는 것은 단가 해석(`:1727-1740`), LineItem 필드 3종
(`:1742-1749` — `confirmed_distributor`, `confirmed_price`, 그리고 `damaged_exchange`일 때만
`purchase_status`), 그리고 PurchaseOrder 그룹 누적(`:1756`)뿐이다.

즉 `:1632`에서 파싱된 값은 이 분기에 진입한 행에 대해 **조용히 버려진다.** 예외도, 경고도,
`errors` 항목(`:1439`)도 남지 않는다.

### 1.2 배치 삽입 지점

`pending_notes` 리스트는 `:1592-1595`에서 선언되고, 루프 종료 후 `:1804-1807`에서 단 한 번의
`bulk_create()`로 비워진다.

```
:1804    # REQ-PO9-005: single bulk_create() for every LineItemNote
:1805    # collected across the CS and warehouse branches.
:1806    if pending_notes:
:1807        LineItemNote.objects.bulk_create(pending_notes)
```

`:1805`의 주석이 현재 상태를 정확히 서술한다 — "CS와 창고 분기에서 수집된". 이 SPEC은 여기에
세 번째 분기를 더한다. 따라서 **주석 `:1804-1805`도 갱신 대상**이다.

### 1.3 메모 값의 출처 — 파일 형식에 따라 다르다

`parse_daily_review_excel`(`backend/order/excel_utils.py`)은 두 형식을 자동 판별한다
(`:779-799`). 판별 키는 SKU 열 이름이다 — `:803`의
`is_new_template = sku_header_name == "Lineitem sku"`.

메모 열은 형식마다 다르다:

```
:822    if is_new_template:
:823        note_idx = header.index("Status") if "Status" in header else None
:824    else:
:825        note_idx = header.index("메모") if "메모" in header else None
```

- **신규 외부 템플릿**(`Lineitem sku`): 메모 출처는 **`Status` 열**
- **레거시 자체 생성 형식**(`ISBN`): 메모 출처는 **`메모` 열**(`_DAILY_REVIEW_HEADERS` `:624-635`에 정의)

두 경우 모두 `:879`의 `note = _str_or_none(_cell(row, note_idx))`로 수렴하고,
결과 dict의 `"note"` 키(`:911`)로 뷰에 전달된다. **따라서 이 SPEC의 요구사항은 열 이름이
아니라 `:1632`가 읽는 `note` 값에 결속되어야 한다** — 그래야 두 형식에 동시에 유효하다.

### 1.4 `note`가 취할 수 있는 값의 집합 (공백 처리의 근거)

```
:694  def _cell(row: tuple, idx: int | None):
:696      if idx is None or len(row) <= idx:
:697          return None
:698      return row[idx]

:701  def _str_or_none(value) -> str | None:
:702      if value is None:
:703          return None
:704      text = str(value).strip()
:705      return text or None
```

이 두 함수를 합치면 `note`의 값 집합은 **정확히 `None` 또는 비어 있지 않은 strip된
문자열**이다. 세 경우가 모두 `None`으로 수렴한다:

1. 메모 열이 파일에 아예 없다 → `note_idx is None` → `_cell` `:696-697` → `None`
2. 셀이 비어 있다 → `_str_or_none` `:702-703` → `None`
3. 셀이 공백만 있다 → `_str_or_none` `:704-705`의 `text or None` → `None`

**결론**: CS 분기의 `if note is not None`(`:1650`) 한 줄이 "공백 메모로 빈 노트를 만들지
않는다"(제약 2)와 "메모 열 없는 레거시 파일이 회귀하지 않는다"(제약 3)를 **동시에** 만족한다.
별도 가드가 필요 없다.

---

## 2. 규모 — 운영 DB 실측 (2026-08-13)

`config.settings.local` 접속으로 직접 측정했다.

### 2.1 배포처 분기를 통과한 LineItem

`confirmed_distributor`가 설정되어 있고 창고 코드가 아닌 LineItem:

| `confirmed_distributor` | 건수 |
|---|---|
| `kyobo` | 4,887 |
| `booxen` | 4,822 |
| `yes24` | 243 |
| `check_required` | 6 |
| `agape` | 4 |
| `sungseoyunion` | 1 |
| **합계** | **9,963** |

### 2.2 그중 노트를 가진 것

`notes__isnull=False`인 것을 `distinct()`로 세면 **12건**이다.

9,963건이 메모를 버리는 분기를 통과했고, 그중 어떤 형태로든 노트를 가진 것은 12건 —
그리고 그 12건조차 이 분기가 만든 것이 아니라 수동 입력(`views.py:251-266`) 또는
`ConfirmOrderView`(`:1140-1145`)에서 온 것으로 보인다.

### 2.3 전체 `LineItemNote` 분포 (대조군)

| `assignee` | 건수 | 출처 |
|---|---|---|
| `CS` | 216 | CS 분기(`:1652-1660`) + 수동 입력 |
| `한국창고` | 56 | 창고 분기(`:1710-1717`, `loc == "korea"`) |
| `발주` | 42 | `ConfirmOrderView`(`:1144`) + 수동 입력 |
| `미국창고` | 34 | 창고 분기(`loc != "korea"`) |
| `타출판사` | 7 | **`ASSIGNEE_CHOICES`에 없는 값** — 아래 참조 |
| **합계** | **355** |

`note_type` 분포: `""` 127 / `타출판사` 80 / `주문취소` 79 / `CS필요` 49 / `주문보류` 14 /
`CS요청` 4 / `발주제외` 2.

**규모 대비**: 시스템 전체 노트가 355건인데, 메모를 버리는 분기를 통과한 LineItem은
9,963건이다. 배포처 행의 메모 기재율이 단 3%라 해도 약 300건 — **현존 노트 코퍼스 전체와
맞먹는 양이 유실됐다는 뜻**이다. 다만 실제 기재율은 이 데이터로는 알 수 없다(§5 참조).

### 2.4 부수 발견 — `assignee="타출판사"` 7건

`LineItemNote.ASSIGNEE_CHOICES`(`backend/order/models.py:242-247`)는
`CS` / `발주` / `한국창고` / `미국창고` 4개뿐이다. Django의 `choices`는 DB 수준 제약이 아니므로
`타출판사`가 저장될 수 있었다. 프론트엔드
`ASSIGNEE_COLORS`(`frontend/src/pages/LineItemNotesPage.tsx:24-29`)에도 없어
`:71`의 `?? 'bg-gray-100 ...'` 폴백으로 렌더링된다.

**이 SPEC의 범위 밖이다.** 다만 "assignee 값을 새로 만들지 않는다"는 결정(설계 결정 A)의
반대 사례로서 기록해 둔다 — 이미 한 번 일어난 일이다.

---

## 3. 선례 — `ConfirmOrderView`

`ConfirmOrderView`(`backend/order/purchase_order_views.py:982`)는 개념적으로 같은 것을
이미 저장한다.

```
:1134    # REQ-CON-032/033/034: handle note field — migrated to LineItemNote (SPEC-ORDER-010)
:1135    if note_key_present:
:1136        note_raw = item["note"]
:1137        if note_raw is not None and note_raw != "":
:1138            # REQ-CON-032: non-empty string → create LineItemNote
:1139            for li in unordered_lis:
:1140                LineItemNote.objects.create(
:1141                    line_item=li,
:1142                    content=note_raw,
:1143                    author=None,
:1144                    assignee="발주",
:1145                )
:1146        # REQ-CON-033: empty string "" → skip
:1147        # REQ-CON-034: null → no longer clears (field removed from LineItem)
```

읽어낼 수 있는 것 네 가지:

1. `assignee="발주"`(`:1144`) — 배포처 확정에 딸린 메모의 담당자는 발주다.
2. `note_type`을 **넘기지 않는다** → 모델 기본값 `""`(`models.py:283-284`)이 된다.
3. `author=None`(`:1143`) — 업로드/일괄 경로는 작성자를 남기지 않는다.
4. 빈 문자열은 노트를 만들지 않는다(`:1137`, 주석 `:1146`).

이 계약은 테스트로 고정돼 있다 —
`backend/order/tests/test_purchase_orders.py:1412-1430`(비어 있지 않으면 생성),
`:1432-1450`(`""`이면 미생성), `:1452-1470`(`None`이면 미생성).

**단, `ConfirmOrderView`는 죽은 코드다.** 유일한 프론트엔드 진입점이었을
`ConfirmOrderTab.tsx:7`은 어디에서도 import되지 않는다(`frontend/src`
전수 grep 결과 자기 자신과 `purchaseOrderApi.test.ts:6`의 주석 언급뿐). 따라서 이 SPEC은
`ConfirmOrderView`를 **명명·의미 선례로만 인용하며 변경 대상으로 삼지 않는다.**

또한 `:1140-1145`는 행마다 `create()`를 호출하는 **비배치** 형태다 — 이것은 따라하지
않는다(§4).

---

## 4. 배치 쓰기 제약의 근거

### 4.1 현재 구조

`UploadDailyReviewView`는 SPEC-PURCHASE-ORDER-009(REQ-PO9-005~007)에서 쿼리 수를 행 수와
무관한 상수로 만드는 개편을 이미 거쳤다. 루프는 쓰기를 하지 않고 리스트에 모으기만 한다:

- `pending_notes`(`:1595`) → `bulk_create` 1회(`:1806-1807`)
- `cs_status_updates`(`:1600`) → `bulk_update` 1회(`:1811-1812`)
- `warehouse_li_updates`(`:1601`) → `bulk_update` 1회(`:1813-1816`)
- `nonwarehouse_li_updates`(`:1602`) → `bulk_update` 1회(`:1817-1824`)
- `warehouse_stock_entries`(`:1607`) → 단일 `Case/When` update(`:1779-1802`)
- `po_group_lineitems`(`:1620`) → `po_creates`(`:1848-1864`) → `bulk_create` + M2M through 배치(`:1866-1888`)

**신규 분기가 `pending_notes`에 append하면 쿼리가 단 하나도 늘지 않는다.** `bulk_create`는
이미 호출되고 있고, `if pending_notes:` 가드(`:1806`) 덕분에 지금까지 CS/창고 행이 없는
업로드에서는 아예 실행되지 않았을 뿐이다.

### 4.2 기존 쿼리 수 상한 테스트와 그 사각지대

`backend/order/tests/test_daily_review_upload.py:2111-2169`의
`TestUploadDailyReviewQueryCountCeiling`이 상한을 고정한다.

- `:2138` `CaptureQueriesContext`로 감싼다(import는 `:2128-2129`)
- `:2160` 300행에서 `assert query_count < 35`
- `:2162-2169` 300행 대 500행 비교로 선형 증가를 배제

**사각지대**: 픽스처 `_make_bulk_daily_review_fixture`(`:2036-2108`)에서 PO 분기로 가는
행들은 `:2083`에서 `{"sku": sku, "selected": selected, "status": ""}` — **`status`가 빈
문자열**이다. 즉 `note`가 `None`이라 노트가 하나도 만들어지지 않는다. CS 행(`:2071`)과 필러
행(`:2099`)도 마찬가지로 `status: ""`이고, 창고 행(`:2076`)만 위치 문자열을 넣는다.

따라서 이 테스트는 **메모를 가진 배포처 행이 대량으로 있을 때의 쿼리 수를 전혀 측정하지
않는다.** 신규 분기를 행별 `create()`로 구현해도 이 테스트는 통과한다.
→ 메모를 가진 PO 행으로 채운 별도 상한 테스트가 필요하다(인수 기준 AC-MEMO-004).

---

## 5. 멱등성 — 현재 동작의 실측 분석

제약 6은 "중복을 막거나, 중복을 허용한다고 명시하되 **기존 동작을 확인한 뒤** 쓸 것"을
요구한다. 기존 동작을 코드로 추적했다.

### 5.1 후보 집합을 만드는 쿼리

```
:1585    for li in (
:1586        _reorder_candidate_filter(
:1587            LineItem.objects.filter(sku__in=all_skus, order_id__in=order_ids)
:1588        ).select_for_update()
:1589    ):
:1590        lineitems_by_key[(li.order_id, li.sku)].append(li)
```

`_reorder_candidate_filter`(`:93`) 본문:

```
:107    return (
:108        queryset.filter(Q(purchase_status="unordered") | Q(purchase_status="damaged_exchange"))
:109        .exclude(purchase_status="unordered", purchase_orders__isnull=False)
:110    )
```

행이 후보를 하나도 못 얻으면 루프는 즉시 건너뛴다:

```
:1637    if not unordered_lis:
:1638        skipped_count += 1
:1639        continue
```

### 5.2 세 분기가 각자 재진입을 차단하는 방식

| 분기 | 1차 업로드가 남기는 상태 | 2차 업로드에서 `:107-110`을 통과하는가 |
|---|---|---|
| CS | `purchase_status` = `order_cancelled`/`on_hold`/`cs_required`/`other_publisher`/`damaged_exchange` (`:1646-1648`) | `damaged_exchange`를 제외하면 **아니오** — `:108`의 두 값 중 어느 것도 아니다 |
| 창고 | `purchase_status = "in_stock"`(`:1702`) | **아니오** — `:108` 불통과 |
| 배포처 | `purchase_status`는 `unordered`로 남거나 `damaged_exchange`→`unordered`로 리셋(`:1748-1749`), **그리고 PurchaseOrder에 M2M 연결**(`:1848-1888`) | **아니오** — `:109`의 `.exclude(purchase_status="unordered", purchase_orders__isnull=False)`에 걸린다 |

**결론**: 같은 파일을 두 번 올려도 세 분기 모두 2차에서는 `:1637-1639`로 빠져 노트가
추가되지 않는다. 이는 **신규 dedup 로직 없이 기존 자격 필터로부터 상속되는 성질**이다.

**한계(명시 필요)**:

- 이것은 내용 기반 중복 제거가 **아니다**. 담당자가 메모를 고쳐 재업로드해도 행 자체가
  스킵되므로 두 번째 노트도, 갱신도 없다.
- `damaged_exchange` CS 행은 `:108`을 통과하므로 재처리될 수 있다 — 다만 그것은 CS 분기의
  기존 동작이며 이 SPEC이 만드는 것이 아니다.
- 이 성질은 **강제되지 않고 상속된다.** 누군가 나중에 `_reorder_candidate_filter`를 넓히면
  (SPEC-ORDER-018 설계 결정 A가 정확히 그것을 막으려 했다) 중복이 조용히 생긴다.
  → 테스트로 고정해야 한다(AC-MEMO-005).

---

## 6. `note_type` 값 선택의 부작용 전수 조사

제약 5는 `_NOTE_TYPE_STATUS_MAP`이 `note_type`을 `purchase_status`로 매핑하므로 새 값에
부작용이 있을 수 있다고 지적한다. `note_type`을 읽는 **모든** 지점을 전수 grep으로
확인했다.

### 6.1 백엔드

| 위치 | 무엇을 하는가 | `LineItemNote.note_type`을 읽는가 |
|---|---|---|
| `excel_utils.py:614-622` | `_NOTE_TYPE_STATUS_MAP` 정의 | — |
| `excel_utils.py:875-877` | `selected_label`이 맵의 키면 `note_type` 변수에 담는다 | **아니오** — '선택' 열 라벨을 읽는다 |
| `excel_utils.py:910` | 파싱 결과 dict에 `note_type` 키로 넣는다 | 아니오 |
| `purchase_order_views.py:1633` | 그 dict에서 꺼낸다 | 아니오 |
| `purchase_order_views.py:1644` | CS 분기 조건 | 아니오 |
| `purchase_order_views.py:1646` | `_NOTE_TYPE_STATUS_MAP[note_type]` → `purchase_status` | **아니오 — 파싱된 '선택' 라벨이지 DB의 노트 행이 아니다** |
| `purchase_order_views.py:1657` | 노트에 **쓴다** | 쓰기 |
| `serializers.py:75`, `:95` | 직렬화 통과 | 읽기(무해) |
| `views.py:314` | `filter(is_resolved=False, note_type="타출판사")` — 타출판사 엑셀 내보내기 | **읽기 — 유일한 의미 있는 소비자** |

### 6.2 프론트엔드

| 위치 | 무엇을 하는가 |
|---|---|
| `LineItemNotesPage.tsx:36` | `note_type === '타출판사'`면 타출판사 탭으로 라우팅 |
| `LineItemNotesPage.tsx:41` | 타출판사 노트를 CS/발주 탭 집계에서 제외 |
| `LineItemNotesPage.tsx:77`, `:255` | 값이 있으면 배지로 표시 |
| `OrderDetailPage.tsx:638-640` | 값이 있으면 배지로 표시 |
| `types/order.ts:88` | `ASSIGNEE_NOTE_TYPES.발주 = ['발주요청', '발주제외']` — 수동 입력 UI의 선택지 |

### 6.3 결론

**`LineItemNote.note_type`을 DB에서 읽어 `purchase_status`를 유도하는 코드 경로는 존재하지
않는다.** `_NOTE_TYPE_STATUS_MAP`은 파싱 측에서 '선택' 열 라벨에만 적용된다. 따라서:

- `note_type=""` → **완전히 무해**. 표시 배지도 뜨지 않는다(`:77`의 truthy 가드).
- `note_type="타출판사"` → **위험**. `views.py:314`의 엑셀 내보내기에 조용히 섞이고
  `LineItemNotesPage.tsx:36`이 타출판사 탭으로 보낸다.
- `note_type="발주요청"`/`"발주제외"` → 서버 측 무해하지만, 이 값들은 수동 입력 UI가 담당자의
  **의도**를 표현하려고 만든 값이다(`types/order.ts:88`). 엑셀 행에는 그 의도가 없다.

---

## 7. 표시 경로 — 프론트엔드 추가 작업이 필요한가

범위 제약: "오늘 이미 표시되는 노트를 표시하는 데 필요한 것 이상의 프론트엔드 작업 없음".

`assignee="발주"`를 택하면 **프론트엔드 변경이 0이다.** 경로를 끝까지 추적했다:

1. `LineItemNoteUnresolvedListView`(`backend/order/views.py:269-282`)가
   `filter(is_resolved=False)`(`:279`)로 미해결 노트 전량을 반환한다 — assignee 필터 없음.
2. `LineItemNoteUnresolvedSerializer`(`serializers.py:79-97`)가 `assignee`, `note_type`,
   `line_item_id`를 포함해 내려준다(`:95-96`).
3. `LineItemNotesPage`(`frontend/src/pages/LineItemNotesPage.tsx:306`)가 그것을 받아
   (`:309`) `filterNotes`(`:35-49`)로 탭별로 나눈다.
4. 탭 목록은 `:343`의 `['CS', '발주', '타출판사']`, 필터는 `:48`의
   `.filter((n) => n.assignee === tab)`.

→ `assignee="발주"`, `note_type=""`인 노트는 **발주 탭에 자동으로 나타난다.**

### 7.1 부수 발견 — `filterNotes`의 "LineItem당 최신 1건" 규칙

```
:38    // Group by line_item_id; pick latest note (highest id) per line item
:39    const latestByLineItem = new Map<number, LineItemNoteUnresolved>()
:40    for (const note of notes) {
:41      if (note.note_type === '타출판사') continue
:42      const existing = latestByLineItem.get(note.line_item_id)
:43      if (!existing || note.id > existing.id) {
:44        latestByLineItem.set(note.line_item_id, note)
:45      }
:46    }
:48    return Array.from(latestByLineItem.values()).filter((n) => n.assignee === tab)
```

CS/발주 탭은 LineItem당 **가장 최신 노트 1건만** 보여준다. 따라서 새 발주 노트가 같은
LineItem의 기존 미해결 CS 노트를 **CS 탭에서 가릴 수 있다.**

도달 가능성 분석:

- 업로드가 만든 CS 노트 → 이후 배포처 노트: **불가능.** CS 분기가 `purchase_status`를
  바꿔(`:1646-1648`) 그 LineItem을 `_reorder_candidate_filter`(`:107-110`) 밖으로 내보내므로
  배포처 분기에 다시 도달하지 못한다(§5.2).
- 수동 입력 CS 노트(`views.py:251-266`) → 이후 배포처 업로드: **가능.** `unordered`인
  LineItem에 CS 노트를 수동으로 달아 둔 뒤 Daily Review로 배포처를 확정하면 발생한다.

**이 성질은 새로 생기는 것이 아니다.** 창고 노트도 오늘 똑같이 CS 노트를 가린다
(`:1710-1717`이 만드는 `한국창고`/`미국창고` 노트가 `:43`의 최신 우선 규칙을 그대로 탄다).
따라서 기존 특성으로 문서화하고 후속 과제로 등록한다.

---

## 8. 기존 테스트에 대한 영향 분석

`test_daily_review_upload.py`의 `LineItemNote` 단정을 전수 확인했다.

| 위치 | 대상 분기 | 영향 |
|---|---|---|
| `:517-534` | 창고(`selected: "재고"`) | 없음 |
| `:1067-1091` | CS(`selected: "주문취소"`) | 없음 |
| `:1135-1143` | CS(`파손/교환`) | 없음 |
| `:1404-1454` | 창고 위치 해석 | 없음 |
| `:1475-1533` | 창고 legacy 코드 | 없음 |

모두 `LineItemNote.objects.get(line_item=li)` 형태로 **특정 LineItem에 스코프**되어 있어,
다른 LineItem에 노트가 늘어도 깨지지 않는다. 배포처 행을 대상으로 노트를 단정하는 기존
테스트는 **하나도 없다** — 당연히, 지금은 생기지 않으니까.

### 8.1 그러나 — 배포처 행에 비어 있지 않은 `status`를 넣는 기존 픽스처가 다수 있다

| 위치 | 행 |
|---|---|
| `:838` | `{"sku": ..., "selected": "BOOXEN", "status": "정상"}` |
| `:862` | `{"selected": "BOOXEN", "status": "한국재고"}` |
| `:916-917` | `{"selected": "BOOXEN", "status": "정상"}` ×2 |
| `:935` | `{"selected": "BOOXEN", "status": "정상", ...}` |
| `:1325` | `{"selected": "BOOXEN", "status": "정상", ...}` |
| `:1350` | `{"selected": "BOOXEN", "status": "정상", "bs_price": 9000}` |
| `:1370`, `:1392` | `{"selected": "YES24", "status": "정상", ...}` |
| `:2207` | 120행 × `{"selected": distributor, "status": "정상"}` |

구현 후 이 픽스처들은 **`content="정상"`인 발주 노트를 만들게 된다.** 위 표의 어떤
테스트도 노트 수를 단정하지 않으므로 **테스트는 깨지지 않는다.** 그러나 이것은 중요한 신호다:

`Status` 열은 신규 템플릿에서 **과부하된 열**이다. `선택="재고"`인 행에서는 창고 위치
해석자로 쓰이고(`:1678`, `_WAREHOUSE_NOTE_LOCATION_MAP` `:1450-1454`), 그 외 행에서는 자유
텍스트다. 테스트 작성자가 배포처 행의 `Status`에 "정상" 같은 상투어를 넣었다는 것은,
**실제 파일에서도 그 열이 메모가 아닌 상투적 상태값을 담고 있을 가능성**을 시사한다.

→ 이것이 §9의 조사가 필요한 이유다.

---

## 9. 과거 템플릿 파일 스캔 — 완료 (2026-08-13)

> **상태: 해결됨.** 아래 "실행 결과"가 판정 기준에 답한다. 결론은 **설계 그대로 진행**이며,
> 상투어 필터링 REQ는 추가하지 않는다. 배포 전 blocker는 해소되었다.

### 9.0 실행 결과

스캔 대상: `G:\내 드라이브\김씨네\발주프로세스\05_김씨네\02_최종공유\`의
`Daily Order Review Template 2026*.xlsx` **198개 파일**.
방법은 §9.1의 1~4단계를 그대로 적용했다(`parse_daily_review_excel`을 직접 호출하여
헤더 판별·열 해석·`_str_or_none` 규칙이 운영 코드와 완전히 동일하도록 했다).

| 항목 | 값 |
|---|---|
| 배포처 분기 대상 행(창고·CS 제외) | 56,637 |
| 그중 메모가 비어 있지 않은 행 | **1,172 (2.1%)** |
| 서로 다른 메모 값 | **228종** |

빈도 상위 값:

| 건수 | 메모 값 |
|---|---|
| 464 | 품절이지만 북센 시도 |
| 280 | 주문판매 |
| 132 | 품절이지만 교보 시도 |
| 18 | 교보 절판 |
| 9 | 절판 가능성 있음 |
| 7 | 품절이지만 북센 시도 / 절판 가능성 있음 |
| 7 | 교보 품절 |
| 5 | 예치금 |
| 4 | 5/12 출고예정 |
| 3 | 품절이지만 북센 시도 / 안들어오면 CS요청 세트 품절 → 단권 주문 |

### 9.0.1 §8.1 우려에 대한 판정 — 기각

`"정상"`, `"재고"`, `"normal"`, `"OK"`, `"-"` 등 상투어 후보를 배포처 행 메모에서 전수
검색한 결과 **출현 0건**이다. `test_daily_review_upload.py:1325`/`:1350`/`:2207` 픽스처가
배포처 행 `Status`에 `"정상"`을 넣는 것은 **테스트 픽스처만의 관행**이며 실제 운영 파일의
성격이 아니다. §8.1이 제기한 "저가치 노트 대량 생성" 시나리오는 실측으로 성립하지 않는다.

### 9.0.2 §2 규모 추정의 갱신

§2는 유실률을 알 수 없어 "기재율 3%면 현존 코퍼스 전체와 맞먹는다"는 조건부 서술에
그쳤다. 이제 실측치로 대체한다: **기재율 2.1%, 2026년분만 1,172건 유실.**
현존 `LineItemNote` 총계 355건의 **3.3배**에 해당한다. 상위 3개 값(876건, 전체의 75%)이
모두 "품절이지만 어디에 시도" 계열 — 발주 담당자의 판단 근거 기록으로, 정확히 이 SPEC이
복원하려는 정보다.

### 9.1 방법 (재현용, 원안 유지)

**질문**: 실제 Daily Review 업로드 파일에서 배포처 행이 메모를 담는 빈도와, 그 값의 성격은?

**왜 DB로 답할 수 없는가**: 배포처 행의 메모는 어디에도 저장되지 않는다 — 그것이 이 결함의
정의다. §2의 9,963건은 "메모를 버리는 분기를 통과한 행 수"일 뿐 "메모를 가졌던 행 수"가
아니다.

**왜 이 저장소로 답할 수 없는가**: `.xlsx` 템플릿 파일이 저장소에 없다(전수 `find` 확인).
코드가 참조하는 실제 파일명은 커밋 메시지와 주석에만 남아 있다 —
`test_daily_review_upload.py:2238`이 `Daily Order Review Template 20260810.xlsx`를,
사용자 보고가 `Daily Order Review Template 20260713.xlsx`를 지목한다.

**방법** (담당자가 보관 중인 파일에 대해 실행):

1. 각 파일에서 `parse_daily_review_excel`과 동일한 헤더 판별을 적용한다
   (`excel_utils.py:779-803`).
2. `선택` 열 값이 `_DISTRIBUTOR_LABEL_MAP`(`:598-611`)의 키이면서 창고 코드가 아닌 행만
   추린다 — 이것이 배포처 분기 대상이다.
3. 그 행들의 메모 셀(신규: `Status`, 레거시: `메모`)에 `_str_or_none` 규칙(`:701-705`)을
   적용해 `None`이 아닌 비율을 낸다.
4. `None`이 아닌 값들의 **빈도 상위 20개**를 뽑는다.

**판정 기준**:

- 상위 값이 `"품절이지만 북센 시도"`처럼 **행마다 다른 자유 텍스트**라면 → 설계 그대로 진행.
  기재율이 곧 유실률이다.
- 상위 값이 `"정상"`처럼 **소수의 상투어에 집중**되어 있다면 → 저가치 노트가 대량 생성된다.
  이 경우 §8.1의 우려가 현실이며, 상투어 필터링 여부를 별도 결정으로 다뤄야 한다.
  **그 결정은 이 SPEC의 요구사항을 바꾸지 않고 추가할 수 있다**(새 REQ 1건) — 따라서 구현
  착수를 막는 blocker는 아니지만, 배포 전에는 답이 나와 있어야 한다.
  → **실행 결과는 전자(자유 텍스트 지배)였다. §9.0 참조.**

---

## 10. 테스트 작성 관례 (`test_daily_review_upload.py`)

| 요소 | 위치 |
|---|---|
| URL 상수 | `:28` `UPLOAD_DAILY_URL = "/api/purchase-orders/upload-daily-review/"` |
| 콘텐츠 타입 상수 | `:32-34` |
| `user` 픽스처 | `:42-44` |
| `auth_client` 픽스처 (JWT) | `:47-52` |
| `_make_order` | `:55-58` (기본 `name="#8001"`) |
| `_make_line_item` | `:61-74` |
| 레거시 형식 빌더 | `:77-` (`_make_daily_review_excel`, 헤더 `:85-94`, 메모 열 `:106`) |
| 신규 템플릿 빌더 | `:743-822` (`_make_new_template_excel`, 헤더 `:763-772`, `Status` `:794`, `선택` `:795`) |
| 헤더 없는 최소 파일 직접 조립 | `:2349-2353` |
| 쿼리 수 측정 | `:2128-2129` (`CaptureQueriesContext` import), `:2138` (사용) |
| 대량 픽스처 | `:2036-2108` (`_make_bulk_daily_review_fixture`) |
| 전 필드 스냅샷 + 노트 수 대조 관례 | `backend/order/tests/test_spec_018.py:197-216` |

`_make_new_template_excel`의 행 dict 키: `sku`, `status`, `selected`, `order_name`,
`bs_price`/`ky_price`/`yes24_price` 등(`:792-812`).

---

## 11. 인용 검증 요약

이 문서가 인용한 파일과 확인 방식:

| 파일 | 확인 방식 |
|---|---|
| `backend/order/purchase_order_views.py` (4,061줄) | `:84-123`, `:1100-1169`, `:1370-1444`, `:1560-1829`, `:1829-1888` 직접 read |
| `backend/order/models.py` (544줄) | `:238-307` 직접 read |
| `backend/order/excel_utils.py` (1,229줄) | `:588-611`, `:600-639`, `:694-723`, `:760-804`, `:820-929` 직접 read |
| `backend/order/views.py` | `:245-324` 직접 read |
| `backend/order/serializers.py` | `:60-104` 직접 read |
| `backend/order/urls.py` | `:66` grep 확인 |
| `backend/order/tests/test_daily_review_upload.py` (2,360줄) | `:1-110`, `:720-822`, `:1310-1370`, `:2040-2169`, `:2190-2359` 직접 read + `LineItemNote`/`"status"` 전수 grep |
| `backend/order/tests/test_purchase_orders.py` | `:1408-1475` 직접 read |
| `backend/order/tests/test_spec_018.py` | `:196-216` 직접 read |
| `frontend/src/pages/LineItemNotesPage.tsx` | `:20-75`, `:304-363` 직접 read + grep |
| `frontend/src/types/order.ts` | `:86-101` 직접 read |
| `frontend/src/pages/PurchaseOrders/tabs/ConfirmOrderTab.tsx` | `:7` grep + 전수 import 검색 |
| 운영 DB | `config.settings.local` 접속 후 ORM 집계 2회 (2026-08-13) |
| 커밋 `48fac8a` | `git log --oneline` 확인 — "fix(order): 주문 간 SKU 충돌 안전성 수정 및 입고 처리 개편 (#16)" |
