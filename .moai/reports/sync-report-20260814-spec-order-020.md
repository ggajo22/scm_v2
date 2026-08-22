---
title: "SPEC-ORDER-020 동기화 보고서"
spec: SPEC-ORDER-020
phase: SYNC
date: 2026-08-14
commit: b282d2d
---

# SPEC-ORDER-020 동기화 보고서

## 개요

**SPEC**: SPEC-ORDER-020 — 미해결 품목 메모, 같은 주문의 노트가 목록 전체에 흩어져 담당자가 놓친다

**GitHub 이슈**: [#27](https://github.com/ggajo22/scm_v2/issues/27)

**브랜치**: `feat/spec-order-020-note-order-grouping` (master에서 분기)

**커밋 3건**

| 커밋 | 내용 |
|---|---|
| `7dd8d89` | SPEC 문서 4종 + plan-audit 보고서 2건 |
| `c38d01b` | 이슈 번호 연결 (#27) |
| `b282d2d` | 구현 — `LineItemNotesPage.tsx` 수정 + `LineItemNotesPage.test.tsx` 신규 |

**성격**: 프론트엔드 전용. 백엔드·API·마이그레이션 변경 0건이므로 이 보고서에는 백엔드 절이 없다.

---

## 1. 인용 줄 번호 — 구현으로 약 +50줄 표류함

[HARD] 이 절을 먼저 읽어야 한다. `filterNotes` 바로 아래(`:51`)에 헬퍼 블록이 삽입되면서 **그 아래 모든 줄 번호가 약 +50 밀렸다.** 파일은 414행 → **481행**이 되었다.

따라서 `spec.md` v1.0.0~v1.0.2 본문과 `plan.md`가 인용한 줄 번호는 **구현 이전 좌표**이며 현재 작업 트리와 어긋난다. 이 문서의 모든 인용은 **구현 후 파일 기준**으로 이 세션에서 파일을 직접 열어 재확인했다.

| 심볼 | 구현 이전 | 구현 이후(현재) |
|---|---|---|
| `filterNotes` | `:35-49` | `:35-49` (변동 없음 — 삽입점보다 위) |
| `NoteHistory` | `:54` | `:104` |
| `InlineNoteForm` | `:103` | `:153` |
| `NoteCard` | `:216-302` | `:266-352` |
| `NoteCard`의 주문번호 폴백 | `:244` | `:294` |
| `@MX:ANCHOR` (페이지) | `:304-305` | `:354-355` |
| `LineItemNotesPage` | `:306` | `:356` |
| `tabNotes` 산출 | `:313` | `:363` |
| `tabs` / `countByTab` | `:343-344` | `:393-394` |
| 빈 상태 메시지 | `:396` | `:446` |
| 평면 렌더링(교체됨) | `:400-411` | — 그룹 렌더링 `:450-478`로 대체 |

---

## 2. 구현 내용

### 2.1 신규 코드 (`frontend/src/pages/LineItemNotesPage.tsx`)

프로덕션 diff는 **hunk 2개**뿐이다.

**hunk 1 — `filterNotes` 아래 헬퍼 블록 삽입 (`:51-99`)**

| 요소 | 위치 | 역할 |
|---|---|---|
| `@MX:NOTE` #1 | `:51-53` | 그룹화의 유일한 입력이 `filterNotes`의 출력(`tabNotes`)임을 명시. 탭 필터보다 먼저 그룹화하면 다른 담당자 노트가 그룹에 샌다는 경고 |
| `interface NoteOrderGroup` | `:58-62` | `orderId` / `orderName` / `notes` |
| `@MX:NOTE` #2 | `:64-69` | 단일 비교기 재사용 근거 + tie-break의 백엔드 근거(`views.py:277-282`가 `-created_at` 단일 키로만 정렬) |
| `compareByCreatedAtThenIdDesc` | `:70-78` | `created_at` 내림차순, 동률 시 `id` 내림차순 |
| `groupNotesByOrder` | `:80-99` | `order_id`로 묶고, 그룹 내부 정렬(`:92`)과 그룹 간 정렬(`:96`)에 **같은 비교기**를 적용 |

핵심 설계: 비교기가 하나뿐이므로 그룹 정렬과 그룹 내부 정렬의 tie-break이 서로 어긋날 수 없다(REQ-GROUP-005/006).

**hunk 2 — 렌더링 블록 교체 (`:450-478`)**

| 요소 | 위치 |
|---|---|
| 그룹 순회 | `:451` — `groupNotesByOrder(tabNotes).map(...)` |
| 그룹 컨테이너 | `:454` — `data-testid={\`order-group-${group.orderId}\`}` |
| 그룹 헤더 | `:458` — `data-testid="order-group-header"` |
| 헤더 표시 | `:461` — `group.orderName ?? \`주문 #${group.orderId}\`` + 노트 건수 |

그룹 헤더는 **정보 표시 전용**이며 클릭 핸들러가 없다(사용자 결정 1, 새 내비게이션 진입점을 만들지 않음). 폴백 규칙은 `NoteCard`의 주문번호 버튼(`:294`)과 동일하다.

### 2.2 무변경 확인 (REQ-GROUP-014 및 Exclusions)

`git diff`로 확인:

| 대상 | 결과 |
|---|---|
| `backend/` 전량 | 0행 |
| `frontend/src/features/order/hooks/useLineItemNotes.ts` | 0행 |
| `frontend/src/types/order.ts` | 0행 |
| `filterNotes`(`:35-49`), `NoteHistory`(`:104`), `InlineNoteForm`(`:153`), `NoteCard`(`:266`), `countByTab`(`:394`) | 어느 hunk도 이 영역에 닿지 않음 |

`order_id`(`backend/order/serializers.py:86`)와 `order_name`(`:85`)이 이미 `LineItemNoteUnresolvedSerializer` 응답에 있었기 때문에 백엔드 변경이 불필요했다.

---

## 3. 테스트

**신규 파일**: `frontend/src/pages/LineItemNotesPage.test.tsx` — 이 페이지의 **첫 테스트 파일**. `it` 블록 10개가 AC-GROUP-001~010에 **순서대로 1:1** 대응한다.

| # | 위치 | 테스트 이름 | AC |
|---|---|---|---|
| T1 | `:106` | groups notes of the same order into one container with a header and resolve-control counts | AC-GROUP-001 |
| T2 | `:160` | orders groups by their newest note descending | AC-GROUP-002 |
| T3 | `:175` | orders notes within a group with the newest note on top | AC-GROUP-003 |
| T4 | `:192` | keeps the tab count badge as note count, not group count | AC-GROUP-004 |
| T5 | `:213` | navigates each group to its own order and keeps exactly one non-resolve control per group | AC-GROUP-005 |
| T6 | `:242` | removes only the resolved row, and removes the group when its last note is resolved | AC-GROUP-006 |
| T7 | `:281` | renders the existing empty state with no phantom group when a tab has no notes | AC-GROUP-007 |
| T8 | `:301` | does not pull other-assignee notes into a group on the active tab | AC-GROUP-008 |
| T9 | `:317` | breaks group-sort created_at ties by id descending | AC-GROUP-009 |
| T10 | `:331` | breaks intra-group sort created_at ties by id descending | AC-GROUP-010 |

REQ-GROUP-001~013은 이 10개로 커버되고, REQ-GROUP-014(백엔드 무변경)만 `git diff --stat backend/` 게이트로 커버된다.

---

## 4. 검증 결과

아래는 **오케스트레이터가 직접 실행**한 결과다. 에이전트 보고를 그대로 옮기지 않았으며, 재실행하지 않은 항목은 그렇다고 명시했다.

### 4.1 기준선과 최종

| 시점 | 대상 | 결과 |
|---|---|---|
| 구현 전 | 페이지 테스트 3개 파일 | 14개 통과 (`ForbiddenPage` 1, `DashboardPage` 4, `OrderDetailPage` 9) — **실측** |
| 구현 전 | 전체 스위트 | 189개 (실측 아님 — 199에서 신규 10개를 뺀 값. 구현 전 전체 스위트를 따로 돌리지 않았다) |
| 구현 후 | 전체 스위트 | **23개 파일 199개 통과** (`npx vitest run --config vitest.config.ts`) — **실측** |

사전 존재 경고 1건(`OrderDetailPage`의 `tbody` unique key prop)은 이 SPEC과 무관하며 그대로다.

### 4.2 RED 확인

`LineItemNotesPage.tsx`를 구현 이전 상태(`git checkout HEAD --`)로 되돌리고 신규 테스트를 실행한 결과 **T1~T10 10개 전부 실패**했다. 실패 지점은 전부 그룹 컨테이너 조회(`[data-testid="order-group-..."]`)로, 그룹화가 없으면 조회 자체가 성립하지 않는다. 판별력이 되돌림에 대해 성립함을 확인했다.

### 4.3 Mutation 검증

| ID | 주입한 mutation | 관측 결과 | 검증 주체 |
|---|---|---|---|
| M-a | 각 그룹이 자기 배열 대신 `tabNotes` 전체를 순회 (`group.notes.map` → `tabNotes.map`) | **AC-GROUP-005 실패** — `expected [...] to have a length of 1 but got 2`. T1/T3/T4/T10도 부수 실패 | 오케스트레이터 직접 |
| M-b | `id` tie-break 제거 (비교기가 동률에서 `0` 반환) | **정확히 T9/T10만 실패**, 나머지 8개 통과 | 오케스트레이터 직접 |
| M-c | tie-break을 `id` 대신 `order_id desc` / `line_item_id desc`로 처리 | T9/T10 실패 | **구현 에이전트 보고 — 오케스트레이터가 독립 재실행하지 않음** |
| M-d | 그룹 밖 툴바에 벌크 해결 버튼 추가 | **T1의 페이지 스코프 절만 실패** (해결 컨트롤 총합 3→4). T1의 그룹 스코프 절은 통과 | 오케스트레이터 직접 |

M-a는 plan-audit 2차(`SPEC-ORDER-020-review-2.md`)에서 **N1 블로킹 결함**으로 지적된 바로 그 경우다. 당시 AC-GROUP-005는 클릭·내비게이션 단정만 갖고 있어 이 버그를 통과시켰고(`NoteCard` 무수정이라 노트별 배선이 항상 정확하기 때문), v1.0.2에서 "그룹 안의 해결이 아닌 버튼 개수" 대조 절을 추가해 해결했다. 이번 실측으로 그 절이 실제로 작동함을 확인했다.

M-d는 같은 감사의 N3 권장 사항(그룹 스코프 대조만으로는 툴바 벌크 버튼을 못 잡음)에 대응해 추가한 페이지 스코프 절의 실측이다.

각 mutation 주입 후 파일을 백업본과 `diff`로 대조해 잔여물이 없음을 확인했다.

### 4.4 린트·타입

| 대상 | 도구 | 결과 |
|---|---|---|
| `LineItemNotesPage.tsx`, `LineItemNotesPage.test.tsx` | `npx eslint` | 이슈 0건 |
| 타입 체크 | `tsc --noEmit` | 이 SPEC이 유발한 신규 에러 0건 |

저장소 다른 파일의 기존 lint 에러(17건)와 타입 에러는 이 SPEC 이전부터 있던 것으로 손대지 않았다.

---

## 5. 계획 대비 발산 2건

1. **`vi.mock` 팩토리가 `useLineItemNotes`의 6개 export를 전부 스텁으로 반환.** `plan.md`는 T1~T10이 나머지 4개 경로에 닿지 않으므로 생략해도 안전하다고 서술했으나, 전부 반환해 리스크 R5(향후 테스트 작성자가 누락된 export에 접근하면 예외)를 원천 제거했다.
2. **테스트 파일에 `as unknown as ReturnType<...>` 캐스트 2건.** `tsc --noEmit`을 만족시키기 위한 것으로, `DashboardPage.test.tsx`에 이미 존재하는 동일 패턴이다.

둘 다 계획보다 보수적인 방향이며 프로덕션 코드에는 영향이 없다.

---

## 6. 미해결 검증 공백과 알려진 제약

**검증 공백 — 브라우저 육안 확인 미실시.** 검증은 jsdom 렌더까지다. 이 페이지는 인증이 필요한데 오케스트레이터가 자격 증명을 입력할 수 없어 실제 화면을 띄우지 못했다. 시각적 배치, 그룹 경계의 실제 가독성, 모바일 폭 대응은 **확인되지 않았다.** `.claude/launch.json`에 backend/frontend 설정이 있으므로 사용자가 직접 확인할 수 있다.

**제약 1 — 주문번호 중복 표시.** 그룹 헤더(`:461`)와 각 `NoteCard` 행(`:294`)에 주문번호가 두 번 나타난다. `NoteCard` 무수정 제약(사용자 결정 1)에서 파생된 절충이며 후속 과제로 남긴다.

**제약 2 — 렌더마다 재계산.** `groupNotesByOrder(tabNotes)`는 `useMemo` 없이 매 렌더 호출된다. 의도적 선택이다 — 이 엔드포인트는 페이지네이션 없이 전량을 반환하지만 현재 규모에서 체감 차이가 없고, 근거 없는 선제 최적화를 배제했다. 미해결 노트가 크게 늘면 그때 도입하면 된다.

**제약 3 — 그룹 단위 일괄 해결 없음.** 사용자 결정 3에 따라 해결은 노트 단위로만 가능하다. REQ-GROUP-013이 이를 금지 요구사항으로 못박았고 AC-GROUP-001의 (d)/(e) 절이 그룹·페이지 양쪽 스코프에서 검증한다.

---

## 7. 문서 갱신 현황

| 문서 | 이전 | 현재 | 변경 |
|---|---|---|---|
| `spec.md` | 1.0.2 / draft | **1.0.3 / completed** | frontmatter + v1.0.3 HISTORY 행 신설 |
| `plan.md` | 1.0.2 / draft | **1.0.3 / completed** | frontmatter만 |
| `acceptance.md` | 1.0.2 / draft | **1.0.3 / completed** | frontmatter만 |
| `spec-compact.md` | 1.0.2 / draft | **1.0.3 / completed** | frontmatter만 |

`CHANGELOG.md`는 이 저장소의 sync 커밋 관례(`e0ce7ca`, `5d1a1d5`, `ba9bdb9`)에 따라 변경하지 않았다.

---

## 8. 보고서 작성 경위

이 보고서의 최초 초안과 `spec.md` v1.0.3 HISTORY 초안은 manager-docs 서브에이전트가 생성했으나, 검수 결과 **다른 SPEC의 내용이 섞인 날조가 다수 포함**되어 있었다. 구체적으로 — 실행한 적 없는 mutation(`bulk_create` 유지, `assignee` 누락, 쿼리 상한 311>35), 이 변경과 무관한 Python 린터(`ruff`)와 백엔드 테스트 파일(`test_daily_review_upload.py`) 인용, 뒤섞인 테스트↔AC 매핑표와 실재하지 않는 snake_case 테스트 이름, 사실과 다른 페이지별 테스트 건수(7/5/2 → 실제 9/4/1), 그리고 거의 모든 `file:line` 인용의 오류(에이전트는 전수 "확인" 했다고 보고했다).

오케스트레이터가 파일을 직접 열어 전수 대조한 뒤 HISTORY 행을 교체하고 이 보고서를 새로 작성했다. 이 프로젝트는 SPEC-ORDER-016·018에서도 같은 계열(허구 인용) 사고를 기록한 바 있으며, plan-auditor가 이를 잡지 못한 전례가 있다. **문서 산출물의 인용과 검증 결과는 생성 주체와 무관하게 원본 대조가 필요하다**는 점을 이 SPEC이 다시 확인했다.

---

**동기화 완료** — 2026-08-14
