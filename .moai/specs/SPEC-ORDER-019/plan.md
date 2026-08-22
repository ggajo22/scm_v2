---
id: SPEC-ORDER-019
document: plan
version: 1.0.2
status: completed
updated: 2026-08-13
---

# 구현 계획 — SPEC-ORDER-019 Daily Review 업로드 배포처 행 메모 유실

`spec.md`의 요구사항(REQ-MEMO-001~018)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD
사이클, 리스크와 완화책, MX 태그 계획을 정리한다. 근거 자료는 `research.md`(`file:line` 인용
전량 재검증)를 참조한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며,
요구사항을 재진술하지 않고 REQ ID로 참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의
`development_mode: "tdd"`(`:4`), `test_first_required: true`(`:43`),
`min_coverage_per_commit: 80`(`:46`)에 따른다. 기존 코드 위에 얹는 브라운필드 변경이므로 각
RED 단계 전에 대상 코드를 먼저 읽는 사전 단계를 거친다
(`.claude/rules/moai/workflow/workflow-modes.md`의 Brownfield Enhancement 절).

**이 SPEC의 특이점**: 프로덕션 코드 변경이 `purchase_order_views.py`의 한 분기 안 약 10줄과
주석 2줄이 전부다. 작업량의 대부분은 **테스트와 조사**에 있으며, 그것이 의도다 —
이 결함은 "코드를 못 써서" 생긴 것이 아니라 "세 분기 중 하나만 빠뜨렸는데 아무도 그것을
단정하지 않아서" 생겼다.

---

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 회귀 베이스라인 고정 (RED가 아닌 GREEN 확인)**: 어떤 코드도 쓰기 전에
  `backend/order/tests/test_daily_review_upload.py` **전량**을 실행해 현재 통과 상태를
  기록한다. 특히 `TestUploadDailyReviewQueryCountCeiling`(`:2111-2169`)의 실제 쿼리 수를
  숫자로 기록해 둔다 — AC-MEMO-004의 절대 상한이 그 숫자에 기대기 때문이다.
  **이 단계에서 실패가 나오면 그것은 이 SPEC과 무관한 선행 문제이며, 진행 전에 격리해야
  한다.** 작업 트리에 미커밋 변경이 있고 원격 MySQL 테스트 DB를 다른 세션과 공유하므로
  무관한 실패가 실재한다(리스크 R5).

- ~~**M1 — 조사 착수**~~ **완료 (2026-08-13)**: `research.md` §9.0에 결과 기록. 2026년 템플릿
  198개 파일, 배포처 행 56,637건 중 메모 보유 1,172건(2.1%), 228종, 상투어 0건.
  판정은 **"자유 텍스트 지배" → 그대로 진행**이며, 상투어 필터링 요구사항은 추가하지 않는다.
  배포 전 게이트로 남길 항목이 없다.

- **M2 (High) — 노트 생성 계약 테스트 선작성 (RED)**: `backend/order/tests/test_spec_019.py`를
  신규 작성한다. 작성 범위: T1(생성 계약 6필드, AC-MEMO-001), T2(공백 메모, AC-MEMO-002),
  T3(메모 열 부재 + 레거시 메모 열 존재, AC-MEMO-003).
  **세 테스트 모두 현재 코드에서 실패해야 한다** — 실패하지 않으면 그 테스트는 판별력이
  없으므로 다시 쓴다.

- **M3 (High) — 구현 (GREEN)**: `purchase_order_views.py`의 배포처 분기(`:1719-1756`)에
  노트 append를 추가하고 주석 `:1804-1805`를 갱신한다. 커버 REQ: 001~008, 013(무변경 유지).
  **CS 분기(`:1644-1662`)와 창고 분기(`:1675-1717`)는 한 글자도 건드리지 않는다.**

- **M4 (High) — 배치·멱등 테스트 (RED→GREEN)**: T4(대량 메모 쿼리 상한, AC-MEMO-004),
  T5(재업로드 멱등, AC-MEMO-005)를 추가한다.
  T5는 **M3가 올바르면 코드 수정 없이 즉시 통과해야 한다** — 멱등성은 상속되는 성질이므로
  (`spec.md` 설계 결정 C) 실패한다면 M3가 후보 필터 경로를 건드렸다는 뜻이다.
  T4는 M3가 배치를 지켰는지 판별한다 — 행별 `create()`로 구현했다면 여기서 걸린다.

- **M5 (Medium) — 격리·부수효과 테스트 (RED→GREEN, 코드 변경 없이 GREEN이어야 함)**:
  T6(세 분기 3건 격리, AC-MEMO-006), T7(LineItem당 1건 + PO 집계 불변, AC-MEMO-007),
  T8(메모 유무 대조 스냅샷 + 마이그레이션 게이트, AC-MEMO-008)을 추가한다.
  T6의 CS/창고 절과 T7의 PO 절, T8의 (a)~(c)는 **기존 동작의 특성화**이므로 추가 구현 없이
  통과해야 한다. 통과하지 않으면 M3가 범위를 넘었다는 뜻이다.

- **M6 (Medium) — 표시 경로 테스트 (RED→GREEN, 코드 변경 없이 GREEN이어야 함)**:
  T9(미해결 목록 포함 + 타출판사 내보내기 미포함, AC-MEMO-009). `spec.md` 설계 결정 E가
  주장하는 "프론트엔드 변경 0"을 API 수준에서 증명한다. 백엔드 추가 구현 없이 통과해야 한다.

- **M7 (Low) — REFACTOR + 문서 동기화**: 세 분기의 노트 생성이 이제 구조적으로 유사해졌으므로
  공통 헬퍼 추출을 **검토**하되 리스크 R1의 판단에 따른다. `spec.md`/`plan.md`/
  `acceptance.md`/`spec-compact.md`의 `status`를 갱신하고 구현 중 발견한 발산을 `spec.md`
  HISTORY에 기록한다.

의존 관계: M0 → M2 → M3 → M4. M3 → M5 → M6. M1은 전 구간 병렬(배포 전 완료 필요).
M7은 M2~M6 완료 후.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/purchase_order_views.py` (배포처 분기 `:1719-1756`) | `note`가 `None`이 아닐 때 `unordered_lis`를 순회하며 `pending_notes`(`:1595`)에 `LineItemNote`를 append. 형태는 **CS 분기 `:1650-1660`을 그대로 따르되** `note_type` 인자를 넘기지 않고 `assignee="발주"`를 쓴다. 위치는 분기 안 어디든 무방하나 `nonwarehouse_li_updates.extend(...)`(`:1750`) 직후가 CS/창고 분기의 배치(필드 갱신 다음에 노트)와 대칭이다. **`_reorder_candidate_filter`(`:93`)도, `pending_notes` 선언·`bulk_create`(`:1806-1807`)의 구조도 건드리지 않는다.** |
| MODIFY | `backend/order/purchase_order_views.py:1804-1805` (주석) | "collected across the CS and warehouse branches" → 세 분기를 반영하도록 갱신. 이 주석이 현재 코드의 사실을 서술하고 있으므로 방치하면 곧바로 거짓이 된다. |
| NEW | `backend/order/tests/test_spec_019.py` | 모듈 docstring에 `Coverage targets:` T1~T9와 REQ/AC 매핑을 적는다(`test_daily_review_upload.py:1-13`, `:720-740` 관례). URL 상수는 `:28`의 `UPLOAD_DAILY_URL` 값을 재정의한다. 픽스처 `user`/`auth_client`는 `:42-44`/`:47-52`를, 헬퍼 `_make_order`/`_make_line_item`은 `:55-58`/`:61-74`를 복제한다(공용 `backend/conftest.py`는 이 형태를 제공하지 않으므로 스위트마다 자체 정의가 이 저장소의 관례다). 엑셀 빌더는 `_make_new_template_excel`(`:743-822`)과 `_make_daily_review_excel`(`:77-`)을 복제하고, 메모 열 없는 파일은 `:2349-2353`처럼 직접 조립한다. 쿼리 수 측정은 `CaptureQueriesContext`(import `:2128-2129`, 사용 `:2138`). |
| EXISTING (무수정, 회귀 확인만) | `backend/order/tests/test_daily_review_upload.py` | 전량 무수정 통과가 M3~M6의 완료 조건. 특히 `:2111-2169`의 쿼리 상한. |
| EXISTING (변경 없음) | `purchase_order_views.py`의 CS 분기 `:1644-1662`, 창고 분기 `:1675-1717`, `_reorder_candidate_filter` `:93-110`, `pending_notes` `:1595`, `bulk_create` `:1806-1807`, `bulk_update` 3종 `:1811-1824`, PO 생성·연결 `:1848-1888`, `ConfirmOrderView` `:982-1165` | `spec.md` Exclusions. |
| EXISTING (변경 없음) | `backend/order/models.py`, `backend/order/excel_utils.py`, `backend/order/serializers.py`, `backend/order/views.py`, `backend/order/urls.py` | 신규 필드·마이그레이션·`choices` 값·파싱 변경·엔드포인트 없음. |
| EXISTING (변경 없음) | `frontend/` 전량 | `spec.md` 설계 결정 E. `git diff --stat frontend/`가 비어야 한다. |

---

## 기술적 접근

### 구현 (M3)

배포처 분기의 `else:` 블록(`:1719`) 안에서, 기존 필드 갱신 루프(`:1742-1749`)와
`nonwarehouse_li_updates.extend(unordered_lis)`(`:1750`) 다음에 다음을 삽입한다.

1. **가드**: `if note is not None:` — CS 분기 `:1650`과 **동일한 형태**. 이 한 줄이 세 경우를
   전부 처리한다(`research.md` §1.4): 메모 열 부재(`_cell` `excel_utils.py:696-697` → `None`),
   빈 셀(`_str_or_none` `:702-703` → `None`), 공백만(`:704-705`의 `text or None` → `None`).
   `note.strip()`을 다시 부르거나 `if note:`로 바꾸지 **않는다** — 파서가 이미 strip했고,
   `if note:`는 의미상 동일하지만 CS 분기와 형태가 달라져 세 분기의 대칭이 깨진다.
2. **순회**: `for li in unordered_lis:` — 설계 결정 D. CS `:1651`, 창고 `:1709`와 동일.
3. **append**: `pending_notes.append(LineItemNote(line_item=li, content=note, author=None,
   assignee="발주"))`.
   - `note_type`을 **넘기지 않는다** → 모델 기본값 `""`(`models.py:283-284`). 설계 결정 B.
   - `is_resolved`도 넘기지 않는다 → 기본값 `False`(`models.py:273`). REQ-MEMO-006.
   - `LineItemNote`는 이미 이 파일에 import되어 있다(CS 분기 `:1653`, 창고 분기 `:1711`,
     `ConfirmOrderView` `:1140`이 사용 중) — 신규 import 불필요.
4. **`bulk_create` 무변경**: `:1806`의 `if pending_notes:` 가드가 이미 있으므로 리스트가
   비어 있으면 쿼리가 발생하지 않는다. 배포처 노트가 생기면 **기존 그 한 번의 호출에 함께
   실려 나간다** — 쿼리 증가 0(REQ-MEMO-009/010).

주석 `:1804-1805`도 함께 갱신한다.

**하지 말 것**:
- `LineItemNote.objects.create()` — `ConfirmOrderView:1140-1145`가 쓰는 형태이지만
  REQ-MEMO-009 위반이며 T4가 잡는다.
- `assignee`를 생략해 모델 기본값(`"CS"`, `models.py:277`)에 맡기기 — T1 (c)와 T6 (c)가 잡는다.
- `note_type=note_type` 복사 — 배포처 행에서 `note_type`은 `None`이다
  (`excel_utils.py:875-877`이 `'선택'`이 `_NOTE_TYPE_STATUS_MAP`의 키일 때만 설정한다).
  T1 (d)와 T6 (c)가 잡는다.
- `content=note or ""` — 가드를 무력화한다. T2가 잡는다.
- 배포처명을 본문에 섞기(`f"[{distributor_code}] {note}"` 등) — REQ-MEMO-002 위반, T1 (b)가
  문자 단위 비교로 잡는다.

### 테스트 (M2, M4~M6)

- **T1~T3**(M2): 단일 행 시나리오. `_make_new_template_excel` 복제본으로 만든다.
  T3의 부분 1은 `openpyxl`로 `["주문번호", "ISBN", "선택"]` 3열 헤더를 직접 조립한다 —
  `ISBN`과 `선택`이 모두 있어야 `parse_daily_review_excel`의 헤더 판별
  (`excel_utils.py:784-791`)을 통과하고, `Lineitem sku`가 없으므로 `is_new_template`이
  False가 되어(`:803`) `note_idx`가 `header.index("메모")` 경로로 가는데 `"메모"`가 없어
  `None`이 된다(`:825`).
- **T4**(M4): `_make_bulk_daily_review_fixture`(`:2036-2108`) 복제본에서 **PO 분기 행의
  `status`를 `""`(`:2083`)가 아니라 행마다 다른 문자열로** 채운다. 이것이 기존 상한 테스트의
  사각지대를 메운다(`research.md` §4.2). LineItem 시딩은 `:2117-2125` 형태.
  상한 상수는 M0에서 기록한 실측값과 기존 `:2160`의 `35`를 대조해 정한다.
- **T5**(M4): **동일한 `file_bytes`를 재사용**한다(두 번 만들지 않는다). `io.BytesIO`로 두 번
  감싸고 각각 `.name`을 설정한다 — Django 테스트 클라이언트가 파일 객체를 소비하므로
  같은 객체를 재사용하면 두 번째 요청이 빈 파일을 받는다.
- **T6**(M5): 창고 행은 `WarehouseStock` 선행 생성이 필요하다(`:2125` 관례). `selected: "재고"`
  + `status: "한국재고"` 조합이 `_WAREHOUSE_NOTE_LOCATION_MAP`(`:1450-1454`)을 통해
  `loc="korea"` → `assignee="한국창고"`(`:1708`)로 간다.
- **T8**(M5): 스냅샷 비교는 `.order_by("pk").values()` 형태(`test_spec_018.py:197`). 두 세트가
  서로 다른 pk/sku를 갖도록 만들었으므로 비교 시 그 키들을 제외한다.
- **T9**(M6): 엔드포인트 경로는 `backend/order/views.py:269`(미해결 목록)와 `:298`(내보내기).
  실제 URL은 `backend/order/urls.py`에서 확인해 상수로 정의한다.

### 배포 전 게이트 (M1) — 해소됨

`research.md` §9.0의 스캔이 완료되어 판정은 **"자유 텍스트가 지배적 → 그대로 배포"**다.
상투어 필터링 요구사항은 추가하지 않는다. 남은 배포 전 게이트는 없다.

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | 세 분기의 노트 생성이 구조적으로 유사해져 M7에서 공통 헬퍼로 추출하고 싶어진다 | **추출하지 않는 쪽을 기본값으로 한다.** 세 분기는 `assignee` 결정 방식이 서로 다르다 — CS는 상수(`:1658`), 창고는 위치에서 유도(`:1708`), 배포처는 상수. `note_type`도 CS만 값을 갖는다(`:1657`). 헬퍼로 묶으면 인자 3개짜리 함수가 되어 인라인보다 읽기 어렵다. 무엇보다 **CS/창고 분기를 수정하게 되어** `spec.md` Exclusions와 REQ-MEMO-013을 위반한다. M7에서 추출을 제안하려면 CS/창고 분기 무수정을 유지하는 방법을 먼저 제시해야 한다. |
| R2 | 구현자가 `ConfirmOrderView:1140-1145`를 선례로 삼아 행별 `create()`를 쓴다 | `spec.md`가 그것을 명시적으로 기각하고(Exclusions), T4(AC-MEMO-004)가 절대 쿼리 상한으로 판별한다. M2에서 T4를 **먼저 작성하지는 않지만** M4가 M3 직후에 오도록 배치했다. `plan.md`의 "하지 말 것" 목록에도 명시했다. |
| R3 | 기존 픽스처가 배포처 행 `status`에 `"정상"`을 넣어 두어(`test_daily_review_upload.py:1325`, `:1350`, `:2207` 등) 구현 후 예상치 못한 노트가 대량 생성된다 | **테스트는 깨지지 않는다** — `research.md` §8이 전수 확인했다. 기존 노트 단정은 전부 `LineItemNote.objects.get(line_item=li)` 형태로 특정 LineItem에 스코프되어 있다. 다만 이것이 실제 파일에서도 상투어가 들어 있을 신호이므로 M1의 조사로 답한다. |
| R4 | `note_type`을 잘못 채워 발주 메모가 타출판사 엑셀 내보내기에 새어 나간다 | T9(AC-MEMO-009 (c))가 `views.py:314`의 필터를 통과하는지 응답 바이트 수준에서 확인한다. 대조군 노트를 함께 두어 "내보내기가 항상 비어 있다"는 가짜 통과도 막는다. |
| R5 | 원격 MySQL 테스트 DB를 공유하는 다른 세션과 pytest가 동시에 돌아 무관한 실패가 섞인다 | 프로젝트 기존 관례 — pytest를 동시 실행하지 않는다. M0의 베이스라인 기록이 "이 SPEC 이전부터 실패하던 것"과 "이 SPEC이 깬 것"을 구분하는 기준이 된다. 현재 작업 트리에 미커밋 변경이 있어 무관한 실패 가능성이 실재한다. |
| R6 | T5(멱등)가 `file_bytes`가 아니라 파일 객체를 재사용해 2차 요청이 빈 파일을 받고, 그 결과가 "멱등성 확인"으로 오독된다 | `plan.md` 기술적 접근 T5 항목에 명시했다. 2차 응답의 `skipped_count == 1` 단정이 이를 판별한다 — 빈 파일이면 파싱 단계에서 422가 나거나(`:1415-1416`) `skipped_count`가 0이 된다. |
| R7 | 멱등성이 `_reorder_candidate_filter`에서 **상속**되는 성질이라, 이후 다른 SPEC이 그 필터를 넓히면 중복이 조용히 생긴다 | T5(AC-MEMO-005)가 잠금장치다. 추가로 신규 코드에 `@MX:NOTE`를 달아 이 의존을 명시한다(MX 태그 계획 참조). SPEC-ORDER-018 설계 결정 A가 같은 필터를 넓히지 않기로 이미 결정했으므로 방향은 일치한다. |
| ~~R8~~ | ~~M1의 조사 결과가 늦어져 배포가 막힌다~~ | **소멸 (2026-08-13)**. 조사 완료(`research.md` §9.0), 상투어 0건으로 위험 자체가 성립하지 않는다. |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | 배포처 분기의 노트 append 바로 위 (`purchase_order_views.py:1750` 인근) | 이 분기의 노트가 `assignee="발주"`이고 `note_type`을 비워 두는 이유 — `ConfirmOrderView`의 선례(`:1144`)를 따르며, `note_type`을 채우면 `views.py:314`의 타출판사 엑셀 내보내기에 새어 나갈 수 있다는 사실(`spec.md` 설계 결정 A/B). 이 태그가 없으면 이후 누군가 "일관성"을 명목으로 CS 분기의 `note_type=note_type`(`:1657`)을 복사할 수 있다. |
| `@MX:NOTE` (신규) | 같은 위치 또는 `pending_notes` 선언부(`:1592-1595`) 인근 | 이 분기의 멱등성이 `_reorder_candidate_filter`(`:107-110`)의 `.exclude(purchase_status="unordered", purchase_orders__isnull=False)`에서 **상속**되며 신규 dedup 로직이 없다는 사실(`spec.md` 설계 결정 C). 그 필터가 넓어지면 중복 노트가 조용히 생긴다는 경고를 포함한다. |
| 갱신 | `purchase_order_views.py:1804-1805`의 일반 주석 | "CS and warehouse branches" → 세 분기. MX 태그는 아니지만 사실을 서술하는 주석이므로 갱신 대상이다. |
| 검토 후 무변경 | `purchase_order_views.py:86-92`의 `@MX:NOTE` (`_reorder_candidate_filter` fan-in == 4) | 이 SPEC은 호출부를 늘리지 않으므로 갱신 불필요. 신규 코드가 이 헬퍼를 호출하면 이 태그를 고쳐야 한다는 사실 자체가 설계 위반의 신호다. |
| 검토 후 무변경 | `purchase_order_views.py:113-122`의 `@MX:NOTE` (`_recompute_order_aggregates` fan-in == 8) | 신규 호출부 없음. |
| 검토 후 무변경 | `purchase_order_views.py:1395-1398`의 `@MX:WARN` (`UploadDailyReviewView` 분기 복잡도) | 경고가 여전히 유효하다. 이 SPEC이 분기 수를 늘리지는 않고 기존 분기 안에 조건 1개를 더하므로, 문구 수정 없이 유지한다. |
| 검토 후 무변경 | `backend/order/models.py:239-240`의 `@MX:ANCHOR` (`LineItemNote` fan-in) | fan-in 서술("LineItemNoteListCreateView, LineItemNoteUnresolvedListView, LineItemNoteResolveView")은 조회 뷰 기준이다. 이 SPEC은 생성 지점을 늘리지만 조회 뷰를 늘리지 않으므로 무변경. |
| 검토 후 무변경 | `frontend/src/pages/LineItemNotesPage.tsx:304-305`의 `@MX:ANCHOR` | 프론트엔드 무변경(설계 결정 E). |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문과
갱신되는 주석은 **영어**로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 베이스라인 기록 — `test_daily_review_upload.py` 전량의 현재 통과 여부와
      `TestUploadDailyReviewQueryCountCeiling`의 실측 쿼리 수가 기록되어 있다
- [ ] `spec.md`의 설계 결정 A~F가 검토되었다
- [ ] `research.md` §9의 조사가 담당자에게 요청되었다 (완료는 배포 전까지)

**Done (구현)**

- [ ] `test_spec_019.py` T1~T9 전량 통과
- [ ] T1~T3, T5의 각 시나리오가 **구현을 되돌린 상태에서 실패함**을 mutation으로 확인했다
      (`acceptance.md`의 `판별력:` 절이 지정한 mutation을 실제로 주입)
- [ ] T4가 행별 `LineItemNote.objects.create()` mutation에서 **실패함**을 확인했다
- [ ] T5가 `_reorder_candidate_filter` 확장 mutation에서 **실패함**을 확인했다
- [ ] T9가 `note_type="타출판사"` mutation에서 **실패함**을 확인했다
- [ ] `test_daily_review_upload.py` 전량 **무수정** 통과 (REQ-MEMO-013)
- [ ] `test_purchase_orders.py` 전량 통과 (특히 `ConfirmOrderView` 노트 계약 `:1412-1470`)
- [ ] `test_line_item_notes.py`, `test_spec_018.py` 전량 통과
- [ ] `git diff`에 CS 분기(`:1644-1662`)와 창고 분기(`:1675-1717`)의 변경이 **없다**
      (REQ-MEMO-013)
- [ ] `git diff`에 `_reorder_candidate_filter`(`:93-110`)의 변경이 **없다** (설계 결정 C)
- [ ] `git diff`에 `ConfirmOrderView`(`:982-1165`)의 변경이 **없다** (Exclusions)
- [ ] `git diff --stat frontend/`가 **비어 있다** (설계 결정 E)
- [ ] `backend/order/migrations/`에 신규 파일이 **없다**, `models.py` diff가 **없다**
      (REQ-MEMO-016)
- [ ] `python manage.py makemigrations --check --dry-run`이 변경 없음을 보고한다 (REQ-MEMO-016)
- [ ] 주석 `:1804-1805`가 세 분기를 반영하도록 갱신되었다
- [ ] `ruff check` 신규 에러 0 (기존 베이스라인 대비 — 이 저장소에는 이 SPEC과 무관한 기존
      에러가 있어 절대 0은 달성 불가능하다)

**Done (배포 전)**

- [x] `research.md` §9의 조사가 완료되었고 판정이 기록되었다 — **자유 텍스트 지배**(2026-08-13)
- [x] 상투어 지배가 아니므로 필터링 요구사항 추가는 불필요 — 배포 전 게이트 없음

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`/`spec-compact.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001, 002, 003, 004, 005, 006 | T1 |
| 001 (다중 LineItem 경로) | T7 |
| 003, 004 (분기 격리) | T6 |
| 007 | T2 |
| 008 | T3 |
| 009, 010 | T4 |
| 011, 012 | T5 |
| 013 | T6 + `test_daily_review_upload.py` 전량 + diff 게이트 |
| 014, 015 | T7, T8 |
| 016 | T8 (e) + `makemigrations --check` + `models.py` diff 게이트 |
| 017, 018 | T9 |

---

## 관련 참조 구현

- **노트 생성의 형태(가드 + 순회 + append)**: `backend/order/purchase_order_views.py:1650`
  (가드), `:1651` (순회), `:1652-1660` (append) — CS 분기
- **동일 형태의 두 번째 사례**: `:1705` (가드), `:1709` (순회), `:1710-1717` (append) —
  창고 분기. `assignee`가 `:1708`에서 유도되는 점만 다르다
- **`assignee="발주"` + `note_type` 미지정의 선례**: `:1140-1145` (`ConfirmOrderView`),
  계약 고정 테스트 `backend/order/tests/test_purchase_orders.py:1412-1430`, `:1432-1450`,
  `:1452-1470`
- **배치 수집·삽입 구조**: `:1592-1595` (`pending_notes` 선언),
  `:1804-1807` (`bulk_create`, 가드 `:1806`)
- **멱등성의 출처**: `:93` (`_reorder_candidate_filter`), 본체 `:107-110`,
  후보 쿼리 `:1585-1590`, 스킵 경로 `:1637-1639`
- **손대지 않을 지점**: CS 분기 `:1644-1662`, 창고 분기 `:1675-1717`,
  PO 그룹 누적 `:1756`, PO 생성·연결 `:1848-1888`, 카운터 `:1758-1762`
- **메모 파싱**: `backend/order/excel_utils.py:822-825` (열 선택), `:879` (값 산출),
  `:911` (결과 키), `:694-698` (`_cell`), `:701-705` (`_str_or_none`), `:803`
  (`is_new_template`)
- **`note_type` 소비자 전량**: `backend/order/views.py:314` (타출판사 내보내기),
  `frontend/src/pages/LineItemNotesPage.tsx:36`, `:41` (탭 라우팅)
- **표시 경로**: `backend/order/views.py:269-282` (미해결 목록, 필터 `:279`),
  `backend/order/serializers.py:79-97` (필드 `:94-97`),
  `frontend/src/pages/LineItemNotesPage.tsx:35-49` (탭 분배, `:48`), `:343` (탭 목록)
- **모델 기본값**: `backend/order/models.py:242-247` (`ASSIGNEE_CHOICES`),
  `:249-259` (`NOTE_TYPE_CHOICES`), `:273` (`is_resolved` 기본 False),
  `:277` (`assignee` 기본 `"CS"`), `:283-284` (`note_type` 기본 `""`)
- **테스트 스위트 관례**: `backend/order/tests/test_daily_review_upload.py:1-13` (docstring),
  `:28` (URL 상수), `:42-52` (픽스처), `:55-74` (헬퍼), `:77-` / `:743-822` (엑셀 빌더),
  `:2036-2108` (대량 픽스처), `:2117-2125` (시딩), `:2128-2129` / `:2138`
  (`CaptureQueriesContext`), `:2160` (절대 상한), `:2349-2353` (헤더 직접 조립);
  `backend/order/tests/test_spec_018.py:197-216` (스냅샷 + 노트 수 대조)
