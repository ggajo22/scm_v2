---
id: SPEC-ORDER-019
version: 1.0.2
status: completed
created_at: 2026-08-13
updated: 2026-08-13
author: ggajo
priority: High
issue_number: 0
labels: [order, daily-review, upload, line-item-note, data-loss]
---

# Daily Review 업로드 배포처 행 메모 유실 — 세 분기 중 하나만 메모를 버린다

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-13 | ggajo | 최초 작성. `UploadDailyReviewView`의 세 행 처리 분기 중 배포처(비창고) 분기만 행의 메모를 `LineItemNote`로 남기지 않는 결함을 다룬다. 운영 DB 실측(`research.md` §2): 이 분기를 통과한 LineItem 9,963건 중 어떤 노트든 가진 것은 12건. 확정한 설계 결정 5건 — assignee는 `발주`(`ConfirmOrderView:1144` 선례이자 프론트엔드 무변경 조건), `note_type`은 모델 기본값 `""`(전수 조사 결과 `LineItemNote.note_type`을 읽어 `purchase_status`를 유도하는 경로가 **없음**), 공백 가드는 CS 분기의 `if note is not None`(`:1650`) 그대로, 쓰기는 기존 `pending_notes`(`:1595`) → 단일 `bulk_create`(`:1806-1807`)에 편입, 멱등성은 `_reorder_candidate_filter`(`:107-110`)로부터 **상속**(신규 dedup 없음). 모든 `file:line` 인용은 `research.md`가 이 세션에서 직접 재검증했다 — SPEC-ORDER-016 v1.0.5 / SPEC-ORDER-018 v1.0.3이 기록한 허구 인용·줄 표류 사고를 반복하지 않기 위해 선행 SPEC의 인용을 재사용하지 않았다. 미해결 조사 1건(과거 템플릿 파일의 배포처 행 메모 기재율)은 `research.md` §9에 방법과 판정 기준까지 명시해 등록했다. |
| 1.0.1 | 2026-08-13 | ggajo | v1.0.0이 남긴 **미해결 조사 1건을 해소**했다. `G:\내 드라이브\...\02_최종공유\`의 2026년 `Daily Order Review Template` **198개 파일**을 `parse_daily_review_excel`로 직접 스캔한 결과(`research.md` §9.0): 배포처 분기 대상 행 **56,637건 중 메모 보유 1,172건(2.1%), 228종**. 판정은 **"자유 텍스트 지배 → 설계 그대로 배포"**이며 상투어 필터링 요구사항은 추가하지 않는다. §8.1이 제기했던 "실제 파일도 `\"정상\"` 같은 상투어를 담아 저가치 노트가 대량 생성된다"는 우려는 **전수 검색 결과 출현 0건으로 기각**됐다(§9.0.1) — 픽스처만의 관행이었다. 상위 값은 `품절이지만 북센 시도`(464) / `주문판매`(280) / `품절이지만 교보 시도`(132)로, 발주 담당자의 판단 근거 기록이다. 유실 규모는 2026년분만 1,172건으로 현존 `LineItemNote` 총계 355건의 **3.3배**다. 요구사항·인수 기준·설계 결정은 **변경 없음**(스캔 결과가 기존 설계를 확인했을 뿐이다). 배포 전 게이트는 이로써 남아 있지 않다. |
| 1.0.2 | 2026-08-13 | ggajo | **구현 완료**(커밋 `7b9f494`). 프로덕션 변경은 계획대로 배포처 분기 1곳 — `purchase_order_views.py:1775-1784`의 10줄과 배치 주석 갱신(`:1839-1842`)뿐이며, 쿼리 증가는 0(기존 `pending_notes` → 단일 `bulk_create` `:1843-1844`에 편입). 부수적으로 **frontmatter 정정**: v1.0.1 행을 추가할 때 frontmatter의 `version`이 `1.0.0`에 머물러 HISTORY와 어긋나 있던 것을 이 행에서 `1.0.2`로 일괄 정합화했다. **계획 대비 발산 6건.** (1) **T3를 단일 테스트 메서드로 병합** — 초안은 AC-MEMO-003을 두 메서드로 쪼갰는데 그중 하나가 RED에서 **통과**했다. `acceptance.md:122-127`이 이미 명시하듯 (a)/(b)는 되돌린 코드에서도 성립하고 반전 판별력은 (c)에만 있다. 두 절반을 한 시나리오로 묶어야 RED가 단위로 성립하므로 `test_spec_019.py:238`의 `test_absent_memo_column_is_inert_while_a_present_one_still_creates_the_note` 하나로 합쳤다 — 세 절 (a)/(b)/(c)는 전부 그대로 단정한다. (2) **AC-MEMO-009 (c)의 대조군 단정 조정** — AC 문언 그대로면 `content="아가페"`, `note_type="타출판사"`인 대조군 노트가 `?publisher=other` 응답에도 남아 있어야 하는데 이는 **충족 불가능**하다: `views.py:324`의 `other` 분기가 `.exclude(content__in=["아가페", "성서유니온"])`이므로 아가페 노트는 그 버킷에 애초에 들어가지 않는다. 구현은 대조군을 AC대로 만들되, **누출 부재는 `?publisher=other`에**(`test_spec_019.py:764-769`), **대조군 존재는 `?publisher=agape`에**(`:773-777`) 단정한다 — "내보내기가 늘 빈 응답"이라는 가짜 통과를 막는다는 AC의 의도는 그대로 지킨다. (3) **(c)를 원시 응답 바이트 검색이 아니라 xlsx 셀 파싱으로 검증** — `.xlsx`는 deflate 압축 zip이라 원시 substring 검색은 **실제 누출에서도 통과**한다. `_excel_strings`(`test_spec_019.py:701-709`)로 워크북을 열어 셀 값 집합을 만들어 대조한다. (4) **T7 대조군에 별도 SKU 사용** — 같은 SKU를 재사용하면 두 번째 `PurchaseOrder`가 생겨 AC (d)의 "PO 정확히 1건" 단정이 이 SPEC과 무관한 이유로 깨진다. 대조군은 `S19-MULTIN`/`#M007N`(`:565-571`)으로 분리했다. (5) **테스트 픽스처 네임스페이스화** — 공유 원격 MySQL 테스트 DB에서 `test_daily_review_upload.py`와 충돌하지 않도록 SKU는 `S19-` 접두, 주문명은 `#M0xx` 대역을 쓴다. AC의 리터럴 `sku="SKU-BLANK"`는 `"S19-BLANK"`(`:174`)가 됐고 **단정 내용은 무변경**이다. (6) **REFACTOR는 의도적 무변경** — `plan.md` 리스크 R1의 판단대로다. 공통 노트 생성 헬퍼를 추출하려면 CS·창고 분기를 손대야 해 REQ-MEMO-013과 Exclusions를 위반한다. **줄 번호 표류 없음** — 이 SPEC의 인용은 기준 커밋 `9f1f82b`에서 채취했고 구현 직전 파일과 **정확히 일치**했다(`:93` `_reorder_candidate_filter`, `:107-110` 본체, `:1144` `ConfirmOrderView`의 `assignee="발주"`, `:1370` `UploadDailyReviewView`, `:1595` `pending_notes`, `:1632` `note = item.get("note")`, `:1650` CS 공백 가드, `:1708` 창고 assignee 유도, `:1719`/`:1756` 배포처 분기 양끝, `:1804-1807` 배치 주석·`bulk_create` 전량 재확인). SPEC-ORDER-018 v1.0.3이 겪은 표류가 이번에는 발생하지 않았다. 구현으로 삽입점(`:1751`) 아래가 **+37줄** 밀렸으므로, 이 문서의 인용은 **구현 이전 좌표**로 읽어야 한다. |

---

## 문제 정의

`UploadDailyReviewView`(`backend/order/purchase_order_views.py:1370`, `POST
/api/purchase-orders/upload-daily-review/`, `urls.py:66`)는 업로드된 Daily Review 엑셀의 각
`(주문명, sku)` 행을 세 갈래로 보낸다. 행의 메모 값은 루프 진입 직후 `:1632`에서
`note = item.get("note")`로 **한 번** 읽힌다.

| 분기 | 트리거 | 위치 | 메모를 저장하는가 |
|---|---|---|---|
| CS | `선택`이 CS 계열 값(주문취소/주문보류/CS필요/타출판사/파손·교환) | `:1644-1662` | **예** — `assignee="CS"`(`:1658`), `note_type=note_type`(`:1657`) |
| 창고 | `선택`이 창고 코드로 해석됨 | `:1675-1717` | **예** — `assignee`는 위치로 결정(`:1708`) |
| **배포처(비창고)** | `선택`이 실제 배포처(BOOXEN/교보/YES24/처음교육 등) | **`:1719-1756`** | **아니오 — `note`를 읽지도 않는다** |

배포처 분기의 본문 38줄(`:1719-1756`) 어디에도 `note` 식별자가 등장하지 않는다. `:1632`에서
파싱된 값은 이 분기에 들어온 행에 대해 **조용히 버려진다.** 예외도, `errors`
항목(`:1439`)도, 어떤 흔적도 남지 않는다.

**확인된 실제 사례**: 파일 `Daily Order Review Template 20260713.xlsx`의 한 행 —
`Name=#35961`, `sku=9788936479497`, `선택=BOOXEN`, 메모 `"품절이지만 북센 시도"`. 업로드 후
그 LineItem에 `LineItemNote`는 존재하지 않는다. 담당자는 기록을 남겼다고 믿고, 시스템은
버렸다.

**규모**(운영 DB 실측 2026-08-13, `research.md` §2): `confirmed_distributor`가 설정되어 있고
창고 코드가 아닌 LineItem — 즉 이 분기를 통과한 것 — 은 **9,963건**(kyobo 4,887 / booxen
4,822 / yes24 243 / 기타 11)이다. **그중 어떤 형태로든 `LineItemNote`를 가진 것은 12건.**
대조군으로 시스템 전체의 `LineItemNote`는 355건이다(CS 216 / 한국창고 56 / 발주 42 /
미국창고 34 / 타출판사 7).

기재율은 DB로는 알 수 없어(버려진 값은 어디에도 없다) 과거 템플릿 파일을 직접 스캔했다
— **완료, `research.md` §9.0**. 2026년 템플릿 198개 파일에서 배포처 분기 대상 행 56,637건 중
메모가 있는 행은 **1,172건(2.1%), 228종**이다. 즉 2026년분만 1,172건의 판단 기록이 유실됐고,
이는 현존 `LineItemNote` 총계 355건의 **3.3배**다.

**같은 개념을 이미 저장하는 선례가 있다.** `ConfirmOrderView`(`:982`)는 배포처 확정에
딸린 메모를 `assignee="발주"`, `note_type` 미지정(→ `""`), `author=None`으로 저장한다
(`:1140-1145`). 이 계약은 `test_purchase_orders.py:1412-1470` 3건이 고정한다. 다만
`ConfirmOrderView`는 죽은 코드다 — 유일한 프론트엔드 진입점이었을 `ConfirmOrderTab.tsx:7`이
어디에서도 import되지 않는다. **따라서 이 SPEC은 그것을 명명·의미 선례로만 인용하며 변경
대상으로 삼지 않는다.**

## 솔루션 개요

배포처 분기가 나머지 두 분기와 **동일한 방식으로** 행의 메모를 `LineItemNote`로 남긴다.

1. **쓰기는 기존 배치 경로에 편입한다.** 신규 쿼리 0건. `pending_notes`(`:1595`)에 append하면
   이미 존재하는 단일 `bulk_create`(`:1806-1807`)가 함께 처리한다.
2. **공백 가드는 CS 분기 것을 그대로 쓴다.** `if note is not None`(`:1650`) 한 줄이
   "빈 메모로 빈 노트를 만들지 않는다"와 "메모 열 없는 레거시 파일이 회귀하지 않는다"를
   동시에 만족한다 — `_str_or_none`(`excel_utils.py:701-705`)과
   `_cell`(`:694-698`)이 세 경우(열 부재/빈 셀/공백만)를 전부 `None`으로 수렴시키기 때문이다.
3. **`assignee`는 `발주`.** 설계 결정 A.
4. **`note_type`은 모델 기본값 `""`.** 설계 결정 B.
5. **멱등성은 상속한다.** 신규 dedup 로직 없음. 설계 결정 C.
6. **모델 변경·마이그레이션 없음. 프론트엔드 변경 없음.** 설계 결정 A가 프론트엔드
   무변경을 성립시킨다(설계 결정 E).

요구사항 본문(EARS)은 관측 가능한 동작(WHAT)만 규정한다. "설계 결정" 절은 각 판단의 근거가
된 기존 코드·테스트·실측을 `file:line`으로 인용한다 — 구현 지시가 아니라 결정을 검증 가능하게
만드는 증거다. 구현 순서는 `plan.md`를, 조사 전문은 `research.md`를 참조한다.

## 범위 — 델타

브라운필드 결함 수정이다. 신규 엔드포인트도, 신규 화면도 없다.

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `UploadDailyReviewView`의 배포처 분기(`purchase_order_views.py:1719-1756`) | `note`가 있을 때 `pending_notes`에 `LineItemNote`를 append. 이 SPEC의 프로덕션 코드 변경은 **사실상 이것 하나**다. |
| [MODIFY] | 주석 `:1804-1805` | "collected across the CS and warehouse branches" → 세 분기로 갱신. |
| [EXISTING] | CS 분기(`:1644-1662`), 창고 분기(`:1675-1717`) | **한 글자도 바꾸지 않는다**(REQ-MEMO-013). |
| [EXISTING] | `_reorder_candidate_filter`(`:93`, 본체 `:107-110`)와 4개 호출부 | 무수정. 멱등성이 여기서 상속되므로 특히 그렇다(설계 결정 C). |
| [EXISTING] | `pending_notes`(`:1595`), `bulk_create`(`:1806-1807`) | 구조 무변경 — append 대상만 늘어난다. |
| [EXISTING] | 배포처 분기의 기존 쓰기(`:1727-1749`), PO 생성·연결(`:1848-1888`) | 무변경(REQ-MEMO-014). |
| [EXISTING] | `LineItem` / `LineItemNote` / `PurchaseOrder` 모델 | 신규 필드·마이그레이션·`choices` 값 없음(REQ-MEMO-016). |
| [EXISTING] | `ConfirmOrderView`(`:982`, 노트 생성 `:1134-1147`) | **무변경.** 죽은 코드이며 선례로만 인용한다. |
| [EXISTING] | `excel_utils.py`의 파싱 전량 | 무변경. 메모는 이미 올바르게 파싱된다(`:879`). |
| [EXISTING] | 프론트엔드 전량 | 무변경(설계 결정 E). |
| [NEW] | `backend/order/tests/test_spec_019.py` | 생성·미생성·배치·멱등·격리·표시 경로 테스트. |

## 설계 결정

### 결정 A — `assignee`는 `발주`

`LineItemNote.ASSIGNEE_CHOICES`(`backend/order/models.py:242-247`)는 정확히 4개다 —
`CS`, `발주`, `한국창고`, `미국창고`. 이 중 셋은 이미 임자가 있다: `CS`는 CS 분기(`:1658`),
`한국창고`/`미국창고`는 창고 분기(`:1708`). 남는 것은 `발주` 하나이고, 그것이 마침
**의미상으로도 맞다** — 배포처 확정은 발주 업무다.

세 갈래 근거:

1. **선례.** `ConfirmOrderView:1144`가 개념적으로 동일한 것(배포처 확정에 딸린 메모)에
   `assignee="발주"`를 쓴다. 이 계약은 `test_purchase_orders.py:1412-1430`이 고정한다.
2. **프론트엔드 무변경.** `LineItemNotesPage.tsx:343`의 탭 목록이
   `['CS', '발주', '타출판사']`이고 `:48`이 `.filter((n) => n.assignee === tab)`로 나눈다.
   `발주` 노트는 **아무 코드 변경 없이** 발주 탭에 나타난다(설계 결정 E).
3. **오분류 방지.** 모델 기본값을 그대로 두면 `assignee="CS"`가 된다
   (`models.py:277`). 그러면 발주 메모 수천 건이 CS 담당자의 미해결 큐(현재 216건)에
   섞인다.

**기각한 대안** — 새 assignee 값(`배포처` 등) 추가. `models.py:242-247`의 `choices`를
바꾸는 것은 마이그레이션을 유발하고(REQ-MEMO-016 위반),
`LineItemNotesPage.tsx:24-29`(`ASSIGNEE_COLORS`)·`:31`·`:33`·`:343`과
`types/order.ts:86-91`을 전부 고쳐야 해 프론트엔드 무변경 조건을 깬다. 덧붙여
`research.md` §2.4가 발견했듯 이 저장소에는 이미 `choices`에 없는
`assignee="타출판사"` 7건이 실재한다 — 값을 늘리는 방향은 이미 한 번 사고를 냈다.

### 결정 B — `note_type`은 모델 기본값 `""`로 남긴다

제약 조건은 "`_NOTE_TYPE_STATUS_MAP`이 `note_type`을 `purchase_status`로 매핑하므로 새
값에 부작용이 있을 수 있다"였다. `note_type`을 읽는 **모든** 지점을 전수 조사했다
(`research.md` §6).

**핵심 사실: `LineItemNote.note_type`을 DB에서 읽어 `purchase_status`를 유도하는 코드
경로는 존재하지 않는다.** `_NOTE_TYPE_STATUS_MAP`(`excel_utils.py:614-622`)이 읽히는 곳은
두 군데뿐이고 둘 다 **파싱 측**이다 — `excel_utils.py:876`이 `'선택'` 열 라벨을 맵의 키와
대조하고, `purchase_order_views.py:1646`이 그렇게 얻은 **로컬 변수** `note_type`으로
`purchase_status`를 정한다. 저장된 노트 행을 되읽는 경로가 아니다.

`LineItemNote.note_type`을 실제로 소비하는 곳은 셋뿐이다:

| 위치 | 동작 | `""`일 때 |
|---|---|---|
| `backend/order/views.py:314` | 타출판사 엑셀 내보내기가 `note_type="타출판사"`만 추린다 | 포함되지 않음 — 안전 |
| `LineItemNotesPage.tsx:36`, `:41` | `'타출판사'`면 타출판사 탭으로 라우팅하고 CS/발주 집계에서 제외 | 해당 없음 — 발주 탭으로 정상 진입 |
| `LineItemNotesPage.tsx:77`, `:255`, `OrderDetailPage.tsx:638` | truthy일 때만 배지 표시 | 배지 없음 |

따라서 **`""`는 완전히 무해하다.**

**기각한 대안 1** — `"타출판사"`. `views.py:314`의 엑셀 내보내기에 발주 메모가 조용히
섞이고 `LineItemNotesPage.tsx:36`이 타출판사 탭으로 보낸다. 실제 피해가 나는 유일한 값이다.

**기각한 대안 2** — `"발주요청"` / `"발주제외"`. 서버 측으로는 무해하다(위 표의 셋 중
어디에도 걸리지 않는다). 그러나 이 두 값은
`ASSIGNEE_NOTE_TYPES.발주`(`frontend/src/types/order.ts:88`)가 **수동 입력 UI에서 담당자의
의도를 표현하려고** 만든 것이다. 엑셀 행의 자유 텍스트에는 그 의도가 없다. 임의로
`"발주요청"`을 붙이면 담당자가 명시적으로 선택한 것과 시스템이 추론한 것을 구별할 수 없게
된다.

**선례 일치**: `ConfirmOrderView:1140-1145`도 `note_type`을 넘기지 않아 `""`가 된다
(`models.py:283-284`). CS 분기가 `note_type`을 쓰는 것(`:1657`)은 **그 행의 `'선택'` 값
자체가 노트 타입이기 때문**이다 — 배포처 행의 `'선택'`은 배포처명이므로 대응물이 없다.

### 결정 C — 멱등성은 상속하며 새 dedup 로직을 만들지 않는다

제약 조건은 "중복을 막거나, 허용한다고 명시하되 **기존 동작을 확인한 뒤** 쓸 것"이었다.
확인 결과는 다음과 같다(`research.md` §5).

후보 집합은 `:1585-1590`이 `_reorder_candidate_filter`(`:93`)로 만든다:

```
:107    queryset.filter(Q(purchase_status="unordered") | Q(purchase_status="damaged_exchange"))
:109    .exclude(purchase_status="unordered", purchase_orders__isnull=False)
```

후보가 없으면 행은 `:1637-1639`에서 즉시 스킵된다.

| 분기 | 1차 업로드가 남기는 상태 | 2차에서 후보로 잡히는가 |
|---|---|---|
| CS | `purchase_status`가 CS 계열로 바뀜(`:1646-1648`) | 아니오 |
| 창고 | `purchase_status="in_stock"`(`:1702`) | 아니오 |
| **배포처** | `unordered`로 남되 **PurchaseOrder에 M2M 연결됨**(`:1848-1888`) | **아니오** — `:109`의 `.exclude(..., purchase_orders__isnull=False)` |

즉 **같은 파일을 두 번 올려도 세 분기 모두 2차에서는 행 자체가 스킵되어 노트가 늘지
않는다.** CS·창고 분기가 오늘 중복을 만들지 않는 이유와 정확히 같은 이유이며, 신규 분기는
그 성질을 **구조적으로 상속**한다. 별도 dedup 로직은 불필요하고, 넣으면 세 분기의 대칭성이
깨진다.

**명시하는 한계 3가지:**

1. **내용 기반 중복 제거가 아니다.** 담당자가 메모를 고쳐 재업로드해도 행이 스킵되므로 두
   번째 노트도, 기존 노트의 갱신도 없다. 수정은 품목 노트 화면(`views.py:251-266`)에서 한다.
2. **강제되지 않고 상속된다.** 누군가 `_reorder_candidate_filter`를 넓히면 중복이 조용히
   생긴다. SPEC-ORDER-018 설계 결정 A가 정확히 그 확장을 막으려 했던 것이며, 이
   SPEC은 그 위험을 테스트로 고정한다(AC-MEMO-005).
3. **같은 SKU의 새 LineItem은 자기 노트를 받는다.** 이는 중복이 아니라 정확한 동작이다 —
   노트는 LineItem에 달린다(`models.py:261-263`).

### 결정 D — 노트는 행당 1건이 아니라 LineItem당 1건이다

하나의 `(주문명, sku)` 쌍이 여러 LineItem으로 해석될 수 있다 —
`lineitems_by_key`(`:1582`)가 `list`를 값으로 갖는 `defaultdict`이고 `:1590`이 append한다.
기존 두 분기는 모두 `for li in unordered_lis:`로 순회하며 LineItem마다 노트를 만든다
(CS `:1651-1660`, 창고 `:1709-1717`). `ConfirmOrderView:1139-1145`도 같다.

신규 분기도 같은 관례를 따른다. 대안(그룹당 1건, 예컨대 `unordered_lis[0]`에만 부착)은
LineItem 단위로 조회되는 품목 노트 화면(`views.py:259-261`이
`filter(line_item_id=...)`)에서 형제 품목의 노트가 보이지 않는 결과를 낳는다.

### 결정 E — 프론트엔드 변경 0

결정 A의 결과로 표시 경로가 이미 완결된다. 끝까지 추적한 경로(`research.md` §7):

`LineItemNoteUnresolvedListView`(`backend/order/views.py:269-282`)가
`filter(is_resolved=False)`(`:279`)로 미해결 노트를 assignee 구분 없이 전량 반환
→ `LineItemNoteUnresolvedSerializer`(`serializers.py:79-97`)가 `assignee`·`note_type`·
`line_item_id`를 포함해 직렬화(`:95-96`)
→ `LineItemNotesPage`(`LineItemNotesPage.tsx:306`)가 수신(`:309`)
→ `filterNotes`(`:35-49`)가 `:48`의 `assignee === tab`으로 발주 탭에 배치.

`is_resolved`는 모델 기본값 `False`(`models.py:273`)이므로 새 노트는 미해결로 생성되어
그 목록에 들어간다.

**알려진 부수효과(수용, 기존 특성)**: `filterNotes`는 CS/발주 탭에 대해 LineItem당 **가장
최신 노트 1건만** 보여준다(`:38-46`, tie-break는 `:43`의 `note.id > existing.id`). 따라서 새
발주 노트가 같은 LineItem의 기존 미해결 CS 노트를 CS 탭에서 가릴 수 있다.

도달 가능성: 업로드가 만든 CS 노트 뒤에 배포처 노트가 오는 순서는 **불가능**하다 — CS
분기가 `purchase_status`를 바꿔(`:1646-1648`) 그 LineItem을 후보 필터 밖으로 내보내기
때문이다(결정 C의 표). 그러나 **수동 입력 CS 노트**(`views.py:251-266`)를 `unordered`
품목에 달아 둔 뒤 Daily Review로 배포처를 확정하면 발생한다.

이는 새로 생기는 성질이 **아니다** — 창고 분기가 만드는 노트(`:1710-1717`)가 오늘 이미
똑같이 CS 노트를 가린다. 기존 특성으로 문서화하고 후속 과제 2로 등록한다.

### 결정 F — 요구사항은 열 이름이 아니라 파싱된 값에 결속한다

메모의 출처 열은 파일 형식에 따라 다르다(`excel_utils.py:822-825`) — 신규 외부 템플릿은
`Status` 열, 레거시 자체 생성 형식은 `메모` 열이며 판별 키는 `:803`의
`is_new_template = sku_header_name == "Lineitem sku"`다. 두 경로 모두 `:879`의
`note = _str_or_none(_cell(row, note_idx))`로 수렴하고 결과 dict의 `"note"` 키(`:911`)로
전달된다.

따라서 이 SPEC의 요구사항은 **`:1632`가 읽는 `note` 값**에 결속한다. 열 이름을 요구사항에
쓰면 두 형식 중 하나에서만 성립하는 규정이 된다.

**주의 사항(범위 밖이지만 명시)**: 신규 템플릿의 `Status` 열은 **과부하되어 있다** —
`선택="재고"`인 행에서는 창고 위치 해석자로 쓰이고(`:1678`,
`_WAREHOUSE_NOTE_LOCATION_MAP` `:1450-1454`), 그 외 행에서는 자유 텍스트다. 기존 테스트
픽스처가 배포처 행의 `Status`에 `"정상"` 같은 상투어를 넣는다는 점이
(`test_daily_review_upload.py:1325`, `:1350`, `:2207` 등) 실제 파일에서도 상투어가 들어
있을 가능성을 시사했다.

**실측으로 기각됨**(`research.md` §9.0.1). 2026년 템플릿 198개 파일의 배포처 행 메모에서
`"정상"`·`"재고"`·`"normal"`·`"OK"`·`"-"` 전수 검색 결과 **출현 0건**이다. `"정상"`은 테스트
픽스처만의 관행이며 운영 파일의 성격이 아니다. 실제 상위 값은 `"품절이지만 북센 시도"`(464),
`"주문판매"`(280), `"품절이지만 교보 시도"`(132) — 행마다 다른 판단 근거 기록이다.
**따라서 상투어 필터링 요구사항은 추가하지 않는다.**

---

## 요구사항 (EARS)

요구사항은 6개 모듈, REQ-MEMO-001부터 REQ-MEMO-018까지 연속 번호로 구성된다. "배포처 행"은
`'선택'` 값이 창고가 아닌 실제 배포처로 해석된 행을, "행의 메모"는 그 행에 대해 파서가
산출한 메모 값(설계 결정 F)을 뜻한다.

### 모듈 1 — 배포처 행 메모의 영속화 (핵심)

**REQ-MEMO-001** (Event-Driven): When an uploaded daily-review row resolves to a
non-warehouse distributor and that row carries a non-empty memo, the system shall persist that
memo as a line-item note on every LineItem the row resolves to.

**REQ-MEMO-002** (Ubiquitous): The system shall store the memo exactly as the parser produced
it, with no truncation, prefixing, suffixing, or substitution of the distributor name or any
other value.

**REQ-MEMO-003** (Ubiquitous): The system shall assign such a note to the purchasing role —
the same assignee value the existing single-item confirmation path already uses for a memo
attached to a distributor confirmation — and shall assign it to neither the CS role nor either
warehouse role.

**REQ-MEMO-004** (Ubiquitous): The system shall leave such a note's type at the model's default
empty value, and shall introduce no distributor-specific note-type value.

**REQ-MEMO-005** (Ubiquitous): The system shall record no author on such a note, matching the
two branches that already create notes during this upload.

**REQ-MEMO-006** (Ubiquitous): The system shall create such a note in the unresolved state.

### 모듈 2 — 메모가 없는 경우 (빈 노트 방지)

**REQ-MEMO-007** (Unwanted): If a distributor row's memo is absent, empty, or consists only of
whitespace, then the system shall create no note for that row.

**REQ-MEMO-008** (Ubiquitous): The system shall continue to process distributor rows from a
file format that carries no memo column at all exactly as it does today — confirming the row
and creating no note — without raising an error and without recording a skip.

### 모듈 3 — 배치 쓰기 (성능 제약)

**REQ-MEMO-009** (Ubiquitous): The system shall write every note this branch produces through
the same single batched insert that already serves the other two branches, and shall issue no
per-row insert.

**REQ-MEMO-010** (Ubiquitous): The total number of database queries one daily-review upload
issues shall remain bounded by a fixed constant that does not grow with the number of
memo-bearing distributor rows in the file.

### 모듈 4 — 재업로드 (멱등성)

**REQ-MEMO-011** (Event-Driven): When the same daily-review file is uploaded a second time with
no intervening change to the affected LineItems, the system shall leave the note count of every
one of those LineItems unchanged.

**REQ-MEMO-012** (Ubiquitous): The system shall introduce no content-based or uniqueness-based
deduplication for these notes; a LineItem that becomes eligible for confirmation again shall
receive a note again.

### 모듈 5 — 기존 동작 불변 (회귀 방지)

**REQ-MEMO-013** (Ubiquitous): The system shall leave the CS branch's and the warehouse
branch's note behaviour unchanged — the memo they store, the assignee they record, and the note
type they record shall all be exactly what they are today.

**REQ-MEMO-014** (Ubiquitous): The system shall produce the same purchase-order rows, the same
purchase-order-to-LineItem links, and the same confirmed-distributor and confirmed-price values
for a distributor row whether or not that row carries a memo.

**REQ-MEMO-015** (Ubiquitous): The upload's response — its confirmed count, its skipped count,
its per-distributor confirmation summary, and its error list — shall be unchanged by the
presence or absence of a memo on a distributor row.

**REQ-MEMO-016** (Unwanted): If this SPEC is implemented, then no new model field, database
migration, purchase-status value, note-type value, or assignee value shall be introduced.

### 모듈 6 — 표시 경로

**REQ-MEMO-017** (Ubiquitous): A note created by this branch shall appear in the existing
unresolved line-item note listing, carrying enough context for the operator to identify the
order and the item, without any change to the frontend.

**REQ-MEMO-018** (Unwanted): If a note is created by this branch, then it shall not appear in
the other-publisher Excel export.

---

## ACCEPTANCE CRITERIA

[HARD] 각 인수 기준은 **판별력**을 갖는다 — 구현이 되돌려지거나 stub되면 반드시 실패한다.
각 항목은 자신을 깨뜨리는 mutation을 한 줄로 명시한다. 실행 가능한 Given/When/Then 시나리오는
`acceptance.md`에 있으며 동일한 `Traces:` 목록을 인용한다.

**AC-MEMO-001** (Event-Driven) — Traces: REQ-MEMO-001, REQ-MEMO-002, REQ-MEMO-003,
REQ-MEMO-004, REQ-MEMO-005, REQ-MEMO-006. When a file containing one distributor row with a
non-empty memo is uploaded against a matching eligible LineItem, the system shall create exactly
one note on that LineItem whose content equals the memo string character for character, whose
assignee is the purchasing role, whose note type is empty, whose author is null, and whose
resolved flag is false.
*Mutation that breaks it*: reverting the branch — zero notes instead of one.

**AC-MEMO-002** (Unwanted) — Traces: REQ-MEMO-007. If one upload contains two distributor rows
for two different eligible LineItems — one whose memo cell is whitespace only, one whose memo is
a real string — then the system shall create exactly one note in total, attached to the second
LineItem, and none on the first.
*Mutation that breaks it*: dropping the blank guard — two notes, the first with empty content.
Also breaks under reversion — zero notes.

**AC-MEMO-003** (Ubiquitous) — Traces: REQ-MEMO-008. Given a legacy-format file whose header
carries no memo column at all, uploading a distributor row from it shall create the
purchase order and set the LineItem's confirmed distributor as it does today, and shall create
no note; and uploading a legacy-format file that does carry a populated memo column shall create
one note for the same row shape.
*Mutation that breaks it*: reading the memo without the absent-column guard — the first half
raises or writes an empty note. Also breaks under reversion — the second half yields zero notes.

**AC-MEMO-004** (Ubiquitous) — Traces: REQ-MEMO-009, REQ-MEMO-010. Given one upload whose
distributor rows all carry distinct non-empty memos, the system shall create one note per
resolved LineItem and shall issue a total query count below the same fixed absolute ceiling the
existing scale test asserts, with the count for a larger file exceeding the count for a smaller
one by no more than a small constant.
*Mutation that breaks it*: a per-row insert instead of appending to the shared batch — the
query count grows with row count and crosses the ceiling. Also breaks under reversion — the
per-LineItem note count is zero.

**AC-MEMO-005** (Event-Driven) — Traces: REQ-MEMO-011, REQ-MEMO-012. When the identical file is
uploaded twice in a row, the affected LineItem shall hold exactly one note after the second
upload, and the second upload's response shall count that row as skipped rather than confirmed.
*Mutation that breaks it*: widening the reorder-candidate eligibility rule so the row is
processed again — two notes. Also breaks under reversion — zero notes after either upload.

**AC-MEMO-006** (Ubiquitous) — Traces: REQ-MEMO-013. Given one upload carrying one CS row, one
warehouse row, and one distributor row, each with its own distinct memo and each matching its
own eligible LineItem, the system shall create exactly three notes: the CS row's note assigned
to CS and carrying its purchase-status-derived note type, the warehouse row's note assigned to
the warehouse role its location implies and carrying an empty note type, and the distributor
row's note assigned to the purchasing role and carrying an empty note type.
*Mutation that breaks it*: giving the distributor note the CS assignee, or copying the CS
branch's note-type assignment into the new branch. Also breaks under reversion — two notes
instead of three.

**AC-MEMO-007** (Ubiquitous) — Traces: REQ-MEMO-001, REQ-MEMO-014, REQ-MEMO-015. Given one
order-name-and-SKU pair that resolves to two eligible LineItems and a single distributor row
carrying a memo for that pair, the system shall create one note per LineItem — two in total,
each attached to its own LineItem — while producing exactly one purchase order linked to both
LineItems with the combined quantity, and while reporting the same confirmed and skipped counts
a memo-free run of the same file reports.
*Mutation that breaks it*: attaching a single note to the first LineItem of the group — one
note instead of two. Also breaks under reversion — zero notes.

**AC-MEMO-008** (Ubiquitous) — Traces: REQ-MEMO-014, REQ-MEMO-015, REQ-MEMO-016. Given two
identical uploads that differ only in whether the distributor rows carry memos, every resulting
LineItem field, every resulting purchase-order field, and every field of the response body shall
be identical between the two runs, while the memo-bearing run alone produces notes; and the
migration state of the project shall report no pending changes.
*Mutation that breaks it*: the new note path altering the confirmed or skipped counters, or
short-circuiting the row before its purchase-order group is accumulated. Also breaks under
reversion — the memo-bearing run produces no notes.

**AC-MEMO-009** (Ubiquitous) — Traces: REQ-MEMO-017, REQ-MEMO-018. After an upload creates a
note for a distributor row, the unresolved line-item note listing shall include that note with
its order name, SKU, item title, assignee and resolved flag, and the other-publisher Excel
export shall not include it.
*Mutation that breaks it*: setting the note type to the other-publisher value — the note leaks
into the export. Also breaks under reversion — the note is absent from the listing.

### Traceability 검증표

| REQ | 커버하는 AC |
|---|---|
| REQ-MEMO-001 | AC-MEMO-001, AC-MEMO-007 |
| REQ-MEMO-002 | AC-MEMO-001 |
| REQ-MEMO-003 | AC-MEMO-001, AC-MEMO-006 |
| REQ-MEMO-004 | AC-MEMO-001, AC-MEMO-006 |
| REQ-MEMO-005 | AC-MEMO-001 |
| REQ-MEMO-006 | AC-MEMO-001 |
| REQ-MEMO-007 | AC-MEMO-002 |
| REQ-MEMO-008 | AC-MEMO-003 |
| REQ-MEMO-009 | AC-MEMO-004 |
| REQ-MEMO-010 | AC-MEMO-004 |
| REQ-MEMO-011 | AC-MEMO-005 |
| REQ-MEMO-012 | AC-MEMO-005 |
| REQ-MEMO-013 | AC-MEMO-006 |
| REQ-MEMO-014 | AC-MEMO-007, AC-MEMO-008 |
| REQ-MEMO-015 | AC-MEMO-007, AC-MEMO-008 |
| REQ-MEMO-016 | AC-MEMO-008 (+ `plan.md` 완료 조건의 마이그레이션 게이트) |
| REQ-MEMO-017 | AC-MEMO-009 |
| REQ-MEMO-018 | AC-MEMO-009 |

18개 요구사항이 9개 인수 기준으로 전부 커버된다. 커버되지 않는 요구사항은 없다.

---

## Exclusions (What NOT to Build)

- **과거 데이터 복구 없음.** 이미 유실된 메모는 되살리지 않는다. 원본 엑셀 파일에서
  역주입하는 스크립트도 만들지 않는다 — 어떤 행이 어떤 LineItem에 대응했는지 사후에
  결정론적으로 재현할 수 없고(`pair_map` `:1432`의 last-row-wins 포함), 검증할 방법도 없다.
- **`ConfirmOrderView`(`purchase_order_views.py:982`) 변경 없음.** 노트 생성부
  (`:1134-1147`) 포함. 죽은 코드이며(`ConfirmOrderTab.tsx:7`이 어디에서도 import되지 않음)
  이 SPEC에서는 명명·의미 선례로만 인용한다. 그것이 쓰는 행별
  `LineItemNote.objects.create()`(`:1140-1145`) 형태도 따라하지 않는다(설계 결정 C의 반대,
  REQ-MEMO-009).
- **`(order_name, sku)` 매칭 로직 변경 없음.** 커밋 `48fac8a`("주문 간 SKU 충돌 안전성
  수정 및 입고 처리 개편")에서 이미 수정됐다. `pair_map`(`:1432`),
  `orders_by_name`(`:1569-1573`), `lineitems_by_key`(`:1582-1590`) 전부 무수정.
- **`_reorder_candidate_filter`(`:93`, 본체 `:107-110`) 변경 없음.** 멱등성이 여기서
  상속되므로(설계 결정 C) 특히 그렇다.
- **CS 분기(`:1644-1662`)·창고 분기(`:1675-1717`) 변경 없음.**
- **프론트엔드 변경 없음.** 설계 결정 A/E가 이를 성립시킨다. 기존에 표시되지 않던 것을
  표시하는 작업은 하지 않는다.
- **모델 변경·마이그레이션 없음.** `ASSIGNEE_CHOICES`(`models.py:242-247`)·
  `NOTE_TYPE_CHOICES`(`:249-259`)에 값을 추가하지 않는다.
- **신규 dedup 로직 없음.** unique 제약도, 내용 비교도 넣지 않는다(설계 결정 C).
- **`excel_utils.py` 파싱 변경 없음.** 메모는 이미 올바르게 파싱된다(`:879`). 메모 출처 열
  선택 규칙(`:822-825`)도 손대지 않는다.
- **`errors`(`:1439`)·응답 형식 변경 없음.** 노트 생성 성공/실패를 응답에 보고하지 않는다.
- **상투어(예: `"정상"`) 필터링 없음.** `research.md` §9.0.1의 전수 스캔에서 실제 파일의
  배포처 행 메모에 상투어가 **0건**으로 확인되어, 필터링은 불필요한 것으로 확정됐다.
- **노트 자동 해결·기존 노트 갱신 없음.** 새 노트만 만든다.
- **감사 로그·이력 테이블 없음.**

## 후속 과제

1. ~~**과거 템플릿 파일의 배포처 행 메모 기재율 조사.**~~ **완료 (2026-08-13, `research.md` §9.0)**
   — 기재율 2.1%(1,172/56,637), 228종, 상투어 0건. 판정은 "자유 텍스트 지배" → 설계 그대로
   진행하며 필터링 요구사항은 추가하지 않는다. 배포 전 확인 항목이 아니다.
2. **`filterNotes`의 "LineItem당 최신 1건" 규칙 재검토**(설계 결정 E의 부수효과).
   `LineItemNotesPage.tsx:38-46`이 CS/발주 탭에서 LineItem당 최신 노트만 보여주므로 새 발주
   노트가 기존 미해결 CS 노트를 가릴 수 있다. 창고 노트가 오늘 이미 같은 일을 하므로 새로
   생기는 문제는 아니지만, 노트가 늘어나면 체감 빈도가 오른다.
3. **`assignee="타출판사"` 7건 정리**(`research.md` §2.4). `ASSIGNEE_CHOICES`에 없는 값이
   DB에 실재하며 `ASSIGNEE_COLORS` 폴백(`LineItemNotesPage.tsx:71`)으로 렌더링된다.
   데이터 정정인지 `choices` 확장인지 결정이 필요하다.
4. **`ConfirmOrderView` 처리 결정.** 죽은 코드이면서 이 SPEC의 의미 선례라는 모순된 위치에
   있다. 프론트엔드를 다시 잇든 코드를 지우든 결정이 필요하다 — 지운다면 이 SPEC의 설계 결정
   A/B의 근거 인용을 이 문서로 옮겨야 한다.
5. **`Status` 열 과부하 해소**(설계 결정 F). 신규 템플릿에서 한 열이 창고 위치 해석자와 자유
   메모를 겸한다. 템플릿에 별도 메모 열을 두는 편이 근본 해결이지만 외부 템플릿이라 협의가
   필요하다.

## 관련 SPEC

- **SPEC-PURCHASE-ORDER-008** — 신규 외부 템플릿 지원. 메모 출처 열 분기
  (`excel_utils.py:822-825`, REQ-PO8-005), 창고 위치의 `Status` 기반 해석
  (`purchase_order_views.py:1678`, REQ-PO8-008), 창고 노트 assignee 결정(`:1708`,
  REQ-PO8-009)의 출처. 설계 결정 F가 다루는 `Status` 열 과부하가 여기서 도입됐다.
- **SPEC-PURCHASE-ORDER-009** — 업로드 배치화(REQ-PO9-005~007). `pending_notes`(`:1595`) →
  단일 `bulk_create`(`:1806-1807`) 구조와 쿼리 수 상한 테스트
  (`test_daily_review_upload.py:2111-2169`)의 출처. 이 SPEC의 REQ-MEMO-009/010이 그 계약을
  이어받는다.
- **SPEC-PURCHASE-ORDER-010** — `damaged_exchange` 도입과
  `_reorder_candidate_filter`(`:93-110`)의 현재 형태. 설계 결정 C의 멱등성이 이 필터에서
  상속된다.
- **SPEC-ORDER-010** — `LineItemNote` 모델 도입(`models.py:238-289`)과 노트 API
  (`views.py:251-296`). `ConfirmOrderView`가 `note` 필드에서 `LineItemNote`로 이관된 것도
  이 SPEC이다(`purchase_order_views.py:1134`의 주석).
- **SPEC-ORDER-017** — 렉번호 엑셀 업로드 배치 처리. "업로드 경로는 처음부터 배치 쿼리로"
  라는 이 저장소의 확립된 선호의 최근 사례.
- **SPEC-ORDER-018** — 보류/제외 품목 복구. `_reorder_candidate_filter`를 넓히지 않는다는
  설계 결정 A가 이 SPEC의 멱등성 상속(설계 결정 C)이 성립하는 전제다. 또한 그 SPEC의
  v1.0.3/v1.0.4가 기록한 "판별력 없는 인수 기준" 사고가 이 SPEC의 AC 판별력 명시 방침의
  직접적 계기다.
