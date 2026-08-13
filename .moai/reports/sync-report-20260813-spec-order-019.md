---
title: "SPEC-ORDER-019 동기화 보고서"
spec: SPEC-ORDER-019
phase: SYNC
date: 2026-08-13
commit: 7b9f494
---

# SPEC-ORDER-019 동기화 보고서

## 개요

**SPEC**: SPEC-ORDER-019 Daily Review 업로드 배포처 행 메모 유실
**구현 완료 날짜**: 2026-08-13
**동기화 날짜**: 2026-08-13
**구현 커밋**: 7b9f4944da84be65949af6b962a88c8c1f23cb91
**동기화 상태**: 완료 (발산 6건 — 전부 테스트 측, 프로덕션 코드는 계획과 일치)

이 SPEC은 **백엔드 전용**이다. 프론트엔드 변경은 0건이며(설계 결정 E), 신규 엔드포인트도
신규 화면도 없다. 따라서 이 보고서에는 프론트엔드 절이 없다.

---

## 1. 계획 대비 발산 분석

### 파일 변경 현황

| 변경 유형 | 파일 | 계획 여부 | 비고 |
|----------|------|---------|------|
| MODIFY | `backend/order/purchase_order_views.py` | 계획됨 | 기능 10줄 + `@MX:NOTE` 2건 + 배치 주석 갱신 |
| NEW | `backend/order/tests/test_spec_019.py` | 계획됨 | 777줄, 9개 테스트 (T1~T9) |
| NEW | `.moai/specs/SPEC-ORDER-019/*` | 계획됨 | spec / spec-compact / plan / acceptance / research |

프로덕션 파일은 **1개**다. 모델·마이그레이션·`excel_utils.py`·프론트엔드 전량 무변경으로
`spec.md` 범위표의 `[EXISTING]` 선언이 전부 지켜졌다.

### 발산 6건 (전부 테스트 측)

`spec.md` HISTORY v1.0.2에 동일 내용이 기록돼 있다.

1. **T3를 단일 테스트 메서드로 병합.** 초안은 AC-MEMO-003을 두 메서드로 분리했는데 그중
   하나가 RED에서 **통과**했다. `acceptance.md:122-127`이 이미 "(a)/(b)만으로는 되돌린 코드도
   통과하므로 (c) 없이는 판별력이 없다"고 명시한다. 두 절반을 한 시나리오로 묶어야 RED가
   단위로 성립하므로 `test_spec_019.py:238`
   (`test_absent_memo_column_is_inert_while_a_present_one_still_creates_the_note`) 하나로
   합쳤다. 세 절 (a)/(b)/(c)는 전부 그대로 단정한다.

2. **AC-MEMO-009 (c)의 대조군 단정 조정.** AC 문언(`acceptance.md:298-300`, `:315-316`)은
   `content="아가페"` / `note_type="타출판사"`인 대조군 노트를 만든 뒤 그것이
   `?publisher=other` 응답에 **그대로 존재**한다고 단정한다. 이는 **충족 불가능**하다 —
   `backend/order/views.py:324`의 `other` 분기가
   `.exclude(content__in=["아가페", "성서유니온"])`이므로 아가페 노트는 그 버킷에 애초에
   들어가지 않는다. 구현은 대조군을 AC대로 생성하되, **누출 부재는 `?publisher=other`에**
   (`test_spec_019.py:764-769`), **대조군 존재는 `?publisher=agape`에**(`:773-777`) 단정한다.
   "내보내기가 늘 빈 응답을 준다"는 가짜 통과를 막는다는 AC의 의도(`acceptance.md:324`)는
   그대로 지켜진다.

3. **(c)를 원시 응답 바이트 검색이 아니라 xlsx 셀 파싱으로 검증.** `.xlsx`는 deflate 압축
   zip이므로 원시 substring 검색은 **실제 누출이 있어도 통과**한다. `_excel_strings`
   (`test_spec_019.py:701-709`)가 워크북을 열어 전 셀 값을 문자열 집합으로 만들고 그 집합에
   대해 대조한다.

4. **T7 대조군에 별도 SKU 사용.** 같은 SKU를 재사용하면 두 번째 `PurchaseOrder`가 생겨
   AC-MEMO-007 (d)의 "PO 정확히 1건" 단정이 이 SPEC과 무관한 이유로 깨진다. 대조군은
   `S19-MULTIN` / `#M007N`(`test_spec_019.py:565-571`)으로 분리했고, 본 시나리오는
   `S19-MULTI`(`:550-551`)를 쓴다.

5. **테스트 픽스처 네임스페이스화.** 공유 원격 MySQL 테스트 DB에서
   `test_daily_review_upload.py`와 충돌하지 않도록 SKU는 `S19-` 접두, 주문명은 `#M0xx`
   대역을 쓴다. AC의 리터럴 `sku="SKU-BLANK"`는 `"S19-BLANK"`
   (`test_spec_019.py:174`)가 됐다. **단정 내용은 무변경**이다.

6. **REFACTOR는 의도적 무변경.** `plan.md` 리스크 R1의 판단대로다 — 공통 노트 생성 헬퍼를
   추출하려면 CS·창고 분기를 수정해야 하고, 이는 REQ-MEMO-013과 `spec.md` Exclusions를
   위반한다. R1은 "추출하지 않는 쪽을 기본값으로 한다"를 명시적으로 정해 두었다.

### 인용 줄 번호 표류 — 없음

이 SPEC의 `file:line` 인용은 기준 커밋 `9f1f82b`에서 채취됐고, 구현 직전 파일과 **정확히
일치**함을 이 동기화 세션에서 재확인했다. 확인한 지점:
`:93` `_reorder_candidate_filter` / `:107-110` 필터 본체 / `:1144` `ConfirmOrderView`의
`assignee="발주"` / `:1370` `UploadDailyReviewView` / `:1595` `pending_notes` /
`:1632` `note = item.get("note")` / `:1650` CS 분기 공백 가드 / `:1708` 창고 assignee 유도 /
`:1719`·`:1756` 배포처 분기 양끝 / `:1804-1807` 배치 주석과 `bulk_create`.

SPEC-ORDER-018 v1.0.3이 겪은 최대 +439줄 표류가 이번에는 재발하지 않았다.

**단, 구현 이후로는** 삽입점(`:1751`) 아래가 **+37줄** 밀렸다. SPEC 문서의 인용은 **구현 이전
좌표**로 읽어야 한다. 이 보고서의 인용은 전부 **현재 작업 트리 기준**이다.

---

## 2. 구현 검증

### 2.1 프로덕션 diff

배포처(비창고) 분기 안, 기존 `nonwarehouse_li_updates.extend(unordered_lis)` 바로 뒤에
**기능 10줄**이 들어갔다 — `purchase_order_views.py:1775-1784`:

- `if note is not None:` (CS 분기 `:1650`과 동일한 공백 가드)
- `for li in unordered_lis:` (설계 결정 D — LineItem당 1건, 행당 1건이 아님)
- `pending_notes.append(LineItemNote(line_item=li, content=note, author=None, assignee="발주"))`

`note_type`은 **전달하지 않는다**(설계 결정 B → 모델 기본값 `""`).

그 위에 `@MX:NOTE` 2건(`:1752-1766` REQ-MEMO-001..006, `:1767-1774` REQ-MEMO-011/012)이
붙었다. `plan.md`의 MX 태그 계획이 지정한 정확히 그 2건이다.

**배치 주석 갱신** — `:1839-1842`. 기존 "collected across the CS and warehouse branches"가
"CS, warehouse and non-warehouse (distributor) branches — SPEC-ORDER-019 REQ-MEMO-009/010
added the third one without adding a query."로 바뀌었다.

**쿼리 증가 0.** 신규 노트는 기존 `pending_notes` 리스트(`:1595`)에 append될 뿐이고, 소비는
루프 밖의 기존 단일 `LineItemNote.objects.bulk_create(pending_notes)`(`:1843-1844`)가 그대로
담당한다. 새 `create()`도, 새 `bulk_create()`도 없다.

### 2.2 테스트

**파일**: `backend/order/tests/test_spec_019.py` (777줄, 9개 테스트)

| 테스트 | 클래스 | 검증 AC | 위치 |
|---|---|---|---|
| T1 | `TestDistributorRowMemoBecomesPurchasingNote` | AC-MEMO-001 | `:123` |
| T2 | `TestBlankMemoCreatesNoNote` | AC-MEMO-002 | `:167` |
| T3 | `TestMissingMemoColumnDoesNotRegress` | AC-MEMO-003 | `:217` |
| T4 | `TestMemoBearingBulkUploadStaysUnderQueryCeiling` | AC-MEMO-004 | `:347` |
| T5 | `TestReuploadKeepsSingleNote` | AC-MEMO-005 | `:420` |
| T6 | `TestThreeBranchesEachKeepTheirOwnAssignee` | AC-MEMO-006 | `:471` |
| T7 | `TestOneRowManyLineItemsGetsOneNoteEach` | AC-MEMO-007 | `:545` |
| T8 | `TestMemoPresenceChangesNothingElse` | AC-MEMO-008 | `:609` |
| T9 | `TestNewNoteIsVisibleButNeverExported` | AC-MEMO-009 | `:713` |

9개 AC ↔ 9개 테스트가 1:1이며, `acceptance.md`의 DoD 표(`:330-340`)와 일치한다.
18개 REQ 전부가 커버된다(`spec.md` Traceability 검증표).

**결과**: `9 passed in 275.30s`.

**RED 확인**: 9건 전부 **무수정 코드에서 실패**함을 구현 전에 관측했다(발산 1의 계기가 바로
그 관측이다 — T3 초안의 한 절반이 RED에서 통과해 시나리오를 병합했다).

### 2.3 판별력(mutation) 검증

구현 에이전트가 수행한 3종:

| # | 주입한 mutation | 결과 |
|---|---|---|
| 1 | 배치 append 대신 **행별 `create()`** | AC-MEMO-004 실패 — 쿼리 **311건**, 상한 35(`test_spec_019.py:67` `UPLOAD_QUERY_CEILING`) 초과 |
| 2 | `assignee="발주"` **누락**(모델 기본값에 위임) | AC-MEMO-001·AC-MEMO-006 실패 — `'CS' != '발주'` |
| 3 | `unordered_lis[0]`에만 **1건 부착** | AC-MEMO-007 실패 |

**독립 재검증 1종** (오케스트레이터가 별도로 수행):

| 주입한 mutation | 결과 |
|---|---|
| 가드 무력화 — `if note is not None` → `if False` | AC-MEMO-001 실패(노트 0건), AC-MEMO-006 실패(`2 != 3`) |
| 원복 | 두 테스트 모두 통과 |

즉 인수 기준은 "되돌리면 반드시 실패한다"는 `spec.md`의 [HARD] 판별력 요건을 실측으로
만족한다.

### 2.4 회귀

**`backend/order/tests/test_daily_review_upload.py` — 95 passed in 583.27s, 실패 0.**
쿼리 상한 클래스와 주문 간 동일 SKU 클래스를 포함한 전량이다.

이는 `research.md` §8의 예측을 확인한다. §8.1(`research.md:413-427`)이 지적했듯
기존 픽스처 다수가 배포처 행 `status`에 `"정상"`을 넣고 있어 **구현 후 이 픽스처들은
`content="정상"`인 발주 노트를 만들게 된다.** 그럼에도 깨지지 않은 이유는 §8
(`research.md:409-411`)이 미리 밝힌 그대로다 — 기존 노트 단정이 전부
`LineItemNote.objects.get(line_item=li)` 형태로 **특정 LineItem에 스코프**되어 있어 다른
LineItem에 노트가 늘어도 영향받지 않는다. 배포처 행을 대상으로 노트를 단정하는 기존 테스트는
하나도 없다.

### 2.5 린트

| 대상 | 결과 |
|---|---|
| `backend/order/purchase_order_views.py` | **15 errors — 변경 전과 동일, 신규 0건** |
| `backend/order/tests/test_spec_019.py` | **All checks passed** |

변경 전(`7b9f494~1`) 버전을 동일한 프로젝트 설정(`backend/pyproject.toml`)으로 `ruff check`한
결과가 **같은 15건, 같은 줄 번호**다. 내역은 E501(12) / I001(1) / F401(1) / F841(1)이며 최대
줄 번호가 `:1305`로, 이 SPEC의 삽입점(`:1751`)보다 위에 있는 **기존 부채**다.

### 2.6 설계 결정 검증

| 결정 | 내용 | 검증 |
|------|------|------|
| A | `assignee="발주"` | `:1782` — T1/T6이 고정 |
| B | `note_type`은 모델 기본값 `""` | `LineItemNote(...)` 인자에 `note_type` **없음**(`:1778-1783`) — T9가 `views.py:314`의 내보내기 필터를 통과하지 않음을 확인 |
| C | 멱등성은 `_reorder_candidate_filter`에서 상속, 신규 dedup 없음 | 필터 무변경(`:93`, `:107-110`) — T5가 재업로드 시 노트 1건 유지를 고정 |
| D | 노트는 행당 1건이 아니라 LineItem당 1건 | `for li in unordered_lis:`(`:1776`) — T7이 고정 |
| E | 프론트엔드 변경 0 | 커밋 `7b9f494`에 프론트엔드 파일 **0개** — T9가 API 응답 수준에서 표시 경로를 확인 |
| F | 요구사항은 열 이름이 아니라 파싱된 `note` 값에 결속 | `excel_utils.py` 무변경 — T3이 메모 열 부재/존재 양쪽을 고정 |

---

## 3. 규모 맥락 (이 수정이 되찾는 것)

`research.md` §9.0의 전수 스캔 결과:

- 2026년 `Daily Order Review Template` **198개 파일**
- 배포처 분기 대상 행 **56,637건** 중 메모 보유 **1,172건 (2.1%), 228종**
- 이는 현존 `LineItemNote` 총계 **355건의 3.3배** — 2026년분만으로 그렇다
- 상위 값: `품절이지만 북센 시도`(464) / `주문판매`(280) / `품절이지만 교보 시도`(132)

전부 발주 담당자의 판단 근거 기록이며, 예외도 `errors` 항목도 없이 조용히 버려지고 있었다.
`"정상"` 같은 상투어는 운영 파일에서 **0건**으로 확인됐다(§9.0.1) — 테스트 픽스처만의
관행이었으므로 상투어 필터링은 도입하지 않았다.

---

## 4. 문서 갱신 현황

### SPEC 문서 버전

| 문서 | 이전 | 현재 | 변경 |
|------|------|------|------|
| `spec.md` | 1.0.0 (frontmatter) / 1.0.1 (HISTORY) | **1.0.2** | frontmatter–HISTORY 불일치 정정 + v1.0.2 HISTORY 행 신설, `status: draft` → `completed` |
| `plan.md` | 1.0.0 | **1.0.2** | 헤더만 |
| `acceptance.md` | 1.0.0 | **1.0.2** | 헤더만 |
| `research.md` | 1.0.0 | **1.0.2** | 헤더만 |
| `spec-compact.md` | 1.0.0 | **1.0.2** | 헤더만 |

`spec.md`의 frontmatter는 `version: 1.0.0`인데 HISTORY에는 이미 1.0.1 행이 있는 **선행
불일치** 상태였다(v1.0.1은 템플릿 파일 스캔 블로커 해소 시 추가됐으나 frontmatter가 따라가지
않았다). 이번 동기화에서 HISTORY 기준으로 정합화했다.

### 프로젝트 문서

**`.moai/project/product.md` — 변경 없음.** 근거는 6절에 기록한다.

### 동기화 보고서

- `.moai/reports/sync-report-20260813-spec-order-019.md` — 본 보고서(신규)

---

## 5. 알려진 이슈 및 후속 과제

### `spec.md`에서 이월된 5건

1. ~~과거 템플릿 파일의 배포처 행 메모 기재율 조사~~ — **완료**(`research.md` §9.0).
   기재율 2.1%, 228종, 상투어 0건. 설계 그대로 진행 확정.
2. **`filterNotes`의 "LineItem당 최신 1건" 규칙 재검토**(설계 결정 E의 부수효과).
   `LineItemNotesPage.tsx:38-46`이 CS/발주 탭에서 LineItem당 최신 노트만 보여주므로 새 발주
   노트가 기존 미해결 CS 노트를 가릴 수 있다. **새로 생기는 문제는 아니다** — 창고 분기 노트가
   오늘 이미 같은 일을 한다. 다만 노트가 늘면 체감 빈도가 오른다.
3. **`assignee="타출판사"` 7건 정리**(`research.md` §2.4). `ASSIGNEE_CHOICES`에 없는 값이 DB에
   실재한다. 데이터 정정인지 `choices` 확장인지 결정 필요.
4. **`ConfirmOrderView` 처리 결정.** 죽은 코드이면서 이 SPEC의 의미 선례라는 모순된 위치.
   지운다면 설계 결정 A/B의 근거 인용을 `spec.md` 본문으로 옮겨야 한다.
5. **`Status` 열 과부하 해소**(설계 결정 F). 신규 템플릿에서 한 열이 창고 위치 해석자와 자유
   메모를 겸한다. 외부 템플릿이라 협의가 필요하다.

### 이번 동기화에서 추가되는 1건

6. **`purchase_order_views.py`의 @MX 태그 예산 초과 — 선행 조건.**

   | 태그 | 현재 | `.moai/config/sections/mx.yaml` 한도 |
   |---|---|---|
   | `@MX:NOTE` | 21 | 10 (`:177`) |
   | `@MX:WARN` | 8 | 5 (`:176`) |
   | `@MX:ANCHOR` | 7 | 3 (`:175`) |

   **이 SPEC이 만든 상태가 아니다.** 변경 전(`7b9f494~1`) 시점에 이미 NOTE 19 / WARN 8 /
   ANCHOR 7로 세 항목 모두 한도를 넘고 있었다. 이 SPEC은 `plan.md`가 지정한 정확히 2건의
   `@MX:NOTE`만 추가했다(NOTE 19 → 21). WARN·ANCHOR는 손대지 않았다.

   근본 원인은 파일 크기다(4,098줄, `mx.yaml`의 `line_count_warn: 500`(`:185`) 기준의 8배).
   태그 감축이 아니라 **파일 분할**이 해법이며, 이 SPEC의 범위 밖이다.

---

## 6. product.md 판정 — 항목 추가 없음

`.moai/project/product.md`의 "구현 완료 기능" 목록은 **사용자에게 새 능력을 제공한 SPEC**만
싣는다. 실제 선례가 이를 뒷받침한다:

| SPEC | 성격 | product.md |
|---|---|---|
| SPEC-ORDER-016 강제 출고 | 신규 엔드포인트 + 신규 UI | **있음** (§11) |
| SPEC-ORDER-018 보류/제외 복구 | 신규 엔드포인트 + 신규 UI | **있음** (§12) |
| SPEC-ORDER-017 렉번호 업로드 배치 처리 | 백엔드 전용, UI·엔드포인트 무변경 | **없음** |
| SPEC-ORDER-010 `LineItemNote` 모델·API 도입 | 백엔드 모델/API | **없음** |
| SPEC-PURCHASE-ORDER-008/009/010 | 백엔드 전용 | **없음** |

목록의 번호는 `0` ~ `12`로 이어지는데 SPEC-ORDER-017이 건너뛰어져 있다 — 백엔드 전용 변경은
싣지 않는다는 선례가 바로 직전 SPEC에서 확립됐다.

SPEC-ORDER-019는 그 범주에 정확히 들어간다:

- 신규 엔드포인트 **없음**
- 신규 화면 **없음**
- 프론트엔드 변경 **0줄** (설계 결정 E)
- 새 능력이 아니라 **기존 화면의 기존 탭**(품목 노트 페이지 `발주` 탭)이 원래 받았어야 할
  데이터를 이제 받는 것이다. 담당자 입장에서 새 조작은 없다.

따라서 product.md 항목을 만들면 목록의 편집 기준이 흐려진다. **추가하지 않는다.**

이 SPEC의 서술은 `spec.md`(문제 정의·설계 결정 6건)와 본 보고서에 남는다.

---

## 7. 최종 결론

### 구현 완료도

- 프로덕션 파일 1개, 기능 10줄, 쿼리 증가 0
- 18개 REQ 전부 커버, 9개 AC ↔ 9개 테스트 1:1
- 발산 6건 — 전부 테스트 측이며 `spec.md` HISTORY v1.0.2에 근거와 함께 기록됨
- 프로덕션 코드는 계획과 **완전 일치**

### 품질 게이트

| TRUST 5 | 판정 | 근거 |
|---|---|---|
| Tested | 통과 | 신규 9 passed, RED 선행 확인, mutation 3종 + 독립 재검증 1종, 회귀 95 passed |
| Readable | 통과 | `@MX:NOTE` 2건이 "왜 `발주`인지 / 왜 `note_type`을 안 넣는지 / 멱등성이 왜 상속인지"를 코드 옆에 남김 |
| Unified | 통과 | 세 분기가 동일한 `pending_notes` → `bulk_create` 관례를 공유 |
| Secured | 통과 | 신규 입력 경로·권한 변경 없음. `note_type=""`로 타출판사 내보내기 누출 차단(T9) |
| Trackable | 통과 | 커밋 `7b9f494`, SPEC/REQ/AC ID 전량 상호 추적 |

### 배포 준비도

- 모든 코드 변경 검증됨
- 신규 테스트 9건 + 회귀 95건 통과
- 린트 신규 에러 0
- 문서 동기화 완료 (SPEC 5개 → v1.0.2 / completed)
- 다음 단계: Git workflow (PR, review, merge)

---

**보고서 작성자**: manager-docs
**보고서 생성**: 2026-08-13
**근거 커밋**: 7b9f4944da84be65949af6b962a88c8c1f23cb91
