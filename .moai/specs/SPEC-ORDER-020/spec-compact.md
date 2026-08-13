---
id: SPEC-ORDER-020
document: spec-compact
version: 1.0.2
status: draft
updated: 2026-08-13
---

# SPEC-ORDER-020 압축 요약 — 미해결 품목 메모 주문번호 그룹화

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(TDD 구현 계획), `acceptance.md`(Given/When/Then + 판별력 명시). 이
SPEC은 백엔드를 변경하지 않으므로 `research.md`는 없다 — 근거 인용은 `spec.md` 본문에 직접 남긴다(이 세션에서 직접
재검증).

## 문제

사용자 요청: "미해결 품목 노트 보여줄 때 같은 주문번호는 같이 보여주는 방법이 있을까?"

`LineItemNotesPage`(`frontend/src/pages/LineItemNotesPage.tsx:306-414`)는 `filterNotes(data, activeTab)`(`:35-49`,
호출 `:313`)가 만든 탭별 목록을 `:400-411`에서 평평하게 한 줄씩 렌더링한다. 같은 주문(`order_id`)의 노트가 목록 안에서
서로 인접하지 않고 흩어질 수 있어, CS/발주 담당자가 한 고객 주문의 미해결 노트를 전부 찾으려면 목록 전체를 훑어야 하고
하나를 놓치기 쉽다.

그룹화에 필요한 데이터는 이미 응답에 있다 — `LineItemNoteUnresolvedSerializer`(`backend/order/serializers.py:79-97`)가
`order_id`(`:86`)와 `order_name`(`:85`)을 이미 내려주고, 프론트엔드 타입 `LineItemNoteUnresolved`(`frontend/src/types/order.ts:103-110`)
도 이미 두 필드를 갖고 있다. 기존 `NoteCard`(`:216-302`)도 이미 각 행에 주문번호 버튼(`:240-245`, `order_name ?? 주문
#{order_id}` 폴백)을 그린다. **사용되지 않은 것은 화면의 렌더링 방식뿐이다.**

## 솔루션

`filterNotes`의 출력(`tabNotes`)을 `order_id`로 묶어 그룹 컨테이너 단위로 렌더링한다. 기존 `NoteCard`는 무수정으로 그룹
안의 행이 된다. 프로덕션 코드 변경은 `LineItemNotesPage.tsx:400-411`(교체) 한 곳뿐이다.

| 항목 | 결정 |
|---|---|
| 그룹화 시점 | `filterNotes(data, tab)`의 출력(`tabNotes`)에만 적용 — 필터 자체는 무수정 |
| 그룹 키 | `order_id`(non-null, `types/order.ts:108`) |
| 그룹 표시 | `order_name ?? 주문 #{order_id}` — `NoteCard:244`와 동일 폴백 |
| 그룹 정렬 | 그룹 내 최신 노트의 `created_at` 내림차순, 동률이면 그 노트의 `id` 내림차순(2차 키) |
| 그룹 내부 정렬 | `created_at` 내림차순, 동률이면 `id` 내림차순(2차 키) — 확정적 근거는 `views.py:277-282`의 `-created_at` 단일 키 정렬(2차 키 없음), 개연적 근거는 SPEC-ORDER-019 일괄 노트 생성 |
| 1건짜리 그룹 | 다건 그룹과 동일한 컨테이너 구조로 렌더링(레이아웃 튐 방지) |
| 그룹 헤더 상호작용 | 정보 표시 전용(주문번호+건수) — 클릭 컨트롤 아님, 새 내비게이션 진입점 없음 |
| 일괄 해결 | 없음 — 해결은 계속 노트 단위 |
| `NoteCard` | 무수정, 그룹 안의 행으로 재사용(중복 주문번호 표시 허용) |
| 백엔드 | 무변경 — API·모델·마이그레이션 없음 |

## 확정된 사용자 결정

1. 표현 = 주문번호 그룹 카드(기존 `NoteCard`는 그룹 안의 행으로 유지)
2. 그룹 범위 = 현재 탭 한정(`filterNotes` 결과에만 적용, 탭별 건수 불변)
3. 그룹 단위 일괄 해결 없음

## REQ 목록 (요약, REQ-GROUP-001~014)

**모듈 1 — 그룹 구성**: 001 주문별 그룹 컨테이너 / 002 탭 필터 이후에만 적용 / 003 헤더에 주문번호+건수 / 004 1건 그룹도 동일 구조

**모듈 2 — 정렬**: 005 그룹은 최신 노트 기준 내림차순(동률 시 `id` 내림차순) / 006 그룹 내부는 `created_at` 내림차순
(동률 시 `id` 내림차순)

**모듈 3 — 탭 스코프·건수**: 007 탭 카운트는 노트 수 기준(그룹 수 아님) / 008 다른 담당자 노트를 그룹에 끌어오지 않음

**모듈 4 — 상호작용 불변**: 009 내비게이션·해결 컨트롤 무변경 / 010 노트 해결 시 그 행만 제거 / 011 그룹의 마지막 노트
해결 시 그룹 컨테이너 제거

**모듈 5 — 빈 상태**: 012 기존 빈 상태 메시지 유지, 팬텀 그룹 없음

**모듈 6 — 금지·스코프**: 013 그룹 단위 일괄 해결 컨트롤 없음 / 014 백엔드 변경 없음

## Acceptance Criteria (요약)

10개 인수 기준이 13개 요구사항을 직접 커버하고, 나머지 1개(REQ-GROUP-014)는 `plan.md`의 `git diff --stat backend/` 게이트로
커버한다. 대부분의 조회가 그룹 컨테이너를 통해서(`within` 패턴) 이루어지므로 되돌린(그룹 없는) 코드에서는 조회 자체가
실패해 판별력이 성립한다.

| AC | 요지 | 반전 판별(구현 되돌림 시) |
|---|---|---|
| AC-GROUP-001 | 2주문(한쪽 2건, 한쪽 1건, 총 3건) → 같은 주문 노트가 한 그룹에 DOM-포함, 헤더에 주문번호+건수, 1건 그룹도 동일 조회 헬퍼로 발견 가능, 그룹 스코프 안 해결 컨트롤 개수 = 노트 개수, **페이지 전체** 해결 컨트롤 총합 = 탭 전체 노트 개수 | 그룹 컨테이너 자체가 없어 조회 실패 |
| AC-GROUP-002 | 도착 순서를 시간 순서와 어긋나게 한 단일 노트 주문 3개 → 그룹은 최신 노트 기준 내림차순 렌더 | 그룹 헤더 자체가 없음 |
| AC-GROUP-003 | 한 주문 2건, 도착 순서는 오래된 것 먼저 → 그룹 내부는 최신이 위 | 그룹 컨테이너 자체가 없음 |
| AC-GROUP-004 | 2주문 총 4건 → 그룹 안 행 합계 4 + 탭 카운트 "(4)"(그룹 수 "(2)" 아님) | 그룹 컨테이너 자체가 없어 합산 불가 |
| AC-GROUP-005 | 단일 노트 주문 2개, 각 그룹 안에서 주문번호 컨트롤 클릭 → 각자의 order_id로 이동, **각 그룹 컨테이너 안 "해결 아닌 버튼" 개수 = 1** | 그룹 컨테이너 안에서 컨트롤 조회 자체가 실패(클릭·이동 단정만으로는 "그룹이 tabNotes 전체를 순회" mutation을 못 잡음 — 컨트롤 개수 단정이 실제 판별 수단) |
| AC-GROUP-006 | 한 주문 2건 → 1건 해결 시 그 행만 제거(그룹 유지), 마지막 1건 해결 시 그룹 컨테이너 자체가 사라짐 | 그룹 컨테이너 자체가 없어 조회 실패(1차 단정은 `NoteCard` 무수정 설계에서 자동 성립, 독립 mutation은 2차의 빈 그룹 잔존뿐) |
| AC-GROUP-007 | CS 탭(그룹 1개, 서로 다른 line_item_id 노트 2건) → 발주 탭(노트 0건) 전환 시 기존 빈 상태 메시지 + 그룹 없음 | CS 탭 절이 그룹 부재로 실패(빈 상태 절 단독은 되돌림에서도 통과 — 판별력은 팬텀 그룹 mutation에 한정, 명시함) |
| AC-GROUP-008 | 한 주문에 CS 노트 1건 + 발주 노트 1건 → CS 탭 그룹은 CS 노트 1건만 포함(건수 1) | 그룹 컨테이너 자체가 없어 건수 조회 불가 |
| AC-GROUP-009 | `created_at` 동일·`id`만 다른 단일 노트 주문 2개, **`id` 순서를 `order_id`/`line_item_id` 순서와도 반대로 배치**, 도착 순서도 기대값과 반대 → 그룹은 `id` 내림차순 | 그룹 헤더 자체가 없음(동률 미처리 시 안정 정렬이 도착 순서를 유지해 실패, `order_id`/`line_item_id` desc tie-break로도 실패) |
| AC-GROUP-010 | `created_at` 동일·`id`만 다른 한 주문 2건, **높은 `id`가 더 낮은 `line_item_id`를 갖도록 배치**, 도착 순서도 기대값과 반대 → 그룹 내부는 `id` 내림차순 | 그룹 컨테이너 자체가 없음(동률 미처리 시 도착 순서 유지로 실패, `line_item_id` desc tie-break로도 실패) |

**핵심 mutation 판별**: 그룹 정렬 생략 → AC-002 실패 / 그룹 내부 정렬 생략 → AC-003 실패 / `countByTab`을 그룹 수로 계산
→ AC-004 실패 / 그룹 렌더가 자신의 노트 배열이 아니라 `tabNotes` 전체를 순회 → AC-005 (b) 컨트롤 개수 대조로 실패(클릭·
이동 단정 (a)로는 안 잡힘) / 빈 그룹 잔존 → AC-006 실패 / 탭 필터 이전에 그룹화 → AC-008 실패 / 빈 배열에 팬텀 그룹 렌더
→ AC-007 실패 / `created_at` 동률 처리(2차 키 `id`) 생략, 또는 `order_id`/`line_item_id` 기준 tie-break(REQ가 명시한
키가 아님) → AC-009·AC-010 실패 / 그룹 밖(페이지·툴바) 벌크 해결 컨트롤 → AC-001의 페이지 스코프 총합 대조로 실패.

## 파일 변경 대상

| 구분 | 파일 |
|---|---|
| MODIFY | `frontend/src/pages/LineItemNotesPage.tsx` — 평면 렌더링(`:400-411`)을 `order_id` 기준 그룹 렌더링으로 교체. **이것이 프로덕션 코드 변경의 전부** |
| NEW | `frontend/src/pages/LineItemNotesPage.test.tsx` — 이 페이지의 첫 테스트 파일, T1~T10(T9~T10은 `created_at` 동률 tie-break 검증) |
| EXISTING (무수정) | `filterNotes`(`:35-49`), `NoteCard`/`NoteHistory`/`InlineNoteForm`(`:54-302`), `countByTab`(`:344`), 탭 목록(`:343`), 타출판사 다운로드(`:371-392`), `useLineItemNotes.ts` 전량, `types/order.ts`, `backend/order/` 전량 |

## Exclusions (요약)

백엔드/API/시리얼라이저/DB 변경 없음 · 그룹 단위 일괄 해결 없음 · 탭 간 노트 집계 없음 · 목록 페이지네이션·가상화 없음 ·
타출판사 엑셀 내보내기 흐름 변경 없음 · `NoteCard`/`NoteHistory`/`InlineNoteForm` 내부 로직 변경 없음 · `filterNotes`의
"LineItem당 최신 1건" 규칙 변경 없음(SPEC-ORDER-019 후속 과제 2와 별개) · 그룹 컨테이너에 클릭 내비게이션 추가 없음 ·
주문번호 중복 표시 제거 없음(후속 과제로 등록)

## 후속 과제 (요약)

1. 그룹 헤더·개별 행의 주문번호 중복 표시 정리(별도 SPEC)
2. 그룹 헤더 접기/펼치기 기능 검토
3. `filterNotes`의 "LineItem당 최신 1건" 규칙 재검토(SPEC-ORDER-019 후속 과제 2, 이 SPEC과 독립)

## 참조 구현

- 그룹화 입력: `LineItemNotesPage.tsx:313`(`tabNotes`), `filterNotes` 정의 `:35-49`
- 그룹 헤더 폴백 규칙 선례: `NoteCard:244`
- 기존 내비게이션 선례: `NoteCard:240-245`(`stopPropagation` `:241`)
- 탭 카운트 배지: `:343-344`
- 평면 렌더링(교체 대상): `:400-411`
- 낙관적 해결 캐시 갱신: `useLineItemNotes.ts:35-59`, `onMutate` `:41-47`
- 데이터 출처: `backend/order/views.py:269-282`, `backend/order/serializers.py:79-97`(`order_id` `:86`, `order_name` `:85`)
- 정렬 동률 키: `frontend/src/types/order.ts:93-101`(`LineItemNote.id: number`)
- 동률의 확정적 근거: `backend/order/views.py:277-282`(`order_by("-created_at")` 단일 키, `:281`)
- 테스트 관례 원본: `frontend/src/pages/OrderDetailPage.test.tsx:1-33`, `:35-95`

## 관련 SPEC

- **SPEC-ORDER-010** — `LineItemNote` 모델·API 도입. 이 SPEC이 그룹화하는 데이터의 출처.
- **SPEC-ORDER-019** — Daily Review 업로드가 배포처 행 메모를 `assignee="발주"`로 저장하도록 확장(완료, 커밋
  `7b9f494`). 그 SPEC의 설계 결정 E가 이 화면의 표시 경로 전체를 추적해 문서화했으며, 이 SPEC은 그 경로의 출력을
  그대로 입력으로 쓴다. 후속 과제 2("LineItem당 최신 1건" 규칙 재검토)는 이 SPEC과 별개로 남아 있다. 그 SPEC이 도입한
  일괄 노트 생성(`bulk_create`)은 이 SPEC의 REQ-GROUP-005/006 `id` tie-break가 대응하는 동일 `created_at` 발생의
  개연적 원인이다(체계적이지는 않음) — 더 직접적인 근거는 `views.py:277-282`의 조회 자체가 `-created_at` 단일 키로만
  정렬한다는 사실이다.
- **SPEC-ORDER-018** — v1.0.3 D1이 `"pk"` tie-break 부재로 정렬 단정이 비결정적이 되는 결함을 겪은 선례. 이 SPEC의
  REQ-GROUP-005/006 `id` tie-break는 그 교훈을 사전에 적용한 것이다.
