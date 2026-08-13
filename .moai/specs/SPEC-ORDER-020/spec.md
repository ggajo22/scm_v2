---
id: SPEC-ORDER-020
version: 1.0.2
status: draft
created_at: 2026-08-13
updated: 2026-08-13
author: ggajo
priority: Medium
issue_number: 0
labels: [order, line-item-note, frontend, ux]
---

# 미해결 품목 메모 — 같은 주문의 노트가 목록 전체에 흩어져 담당자가 놓친다

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-13 | ggajo | 최초 작성. 사용자 요청("미해결 품목 노트 보여줄 때 같은 주문번호는 같이 보여주는 방법이 있을까?")을 반영해 `LineItemNotesPage`(`frontend/src/pages/LineItemNotesPage.tsx`)의 미해결 품목 메모 목록에 주문번호 그룹화를 도입한다. 확정된 사용자 결정 3건 — (1) 표현은 주문번호 그룹 카드이며 기존 `NoteCard`는 그룹 내부 행으로 무수정 유지, (2) 그룹 범위는 현재 탭 한정(`filterNotes` 결과에만 적용, 탭별 건수 불변), (3) 그룹 단위 일괄 해결 버튼 없음. 모든 `file:line` 인용은 이 세션에서 직접 재검증했다 — SPEC-ORDER-016 v1.0.5 / SPEC-ORDER-018 v1.0.3~1.0.4가 기록한 허구 인용·판별력 없는 인수 기준 사고를 반복하지 않기 위해 선행 SPEC의 인용을 재사용하지 않았다. 프론트엔드 전용 변경이다 — 백엔드 시리얼라이저가 이미 `order_id`(`backend/order/serializers.py:86`)와 `order_name`(`:85`)을 내려주고, 프론트엔드 타입도 이미 그 두 필드를 갖고 있음(`frontend/src/types/order.ts:103-110`)을 확인했으므로 API·모델·마이그레이션 변경이 필요 없다. |
| 1.0.1 | 2026-08-13 | ggajo | plan-auditor 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-020-review-1.md`, iteration 1, FAIL, 0.78) 반영. **블로킹 결함 3건 해소**: D1 — `acceptance.md` AC-GROUP-001 픽스처가 "노트 4건"이라 쓰고 실제로는 3건만 나열해 자기모순이었던 것을 "3건"으로 정정. `spec.md` 원래 문구는 처음부터 "one order has two eligible notes and the other has one"(= 3건)으로 일관되어 있었다 — `spec-compact.md`의 AC-001 요약 행은 실제로 "2주문(한쪽 2건)" → "2주문(한쪽 2건, 한쪽 1건, 총 3건)"으로 문구 자체를 손질했다(의미상 모순은 없었으나 텍스트는 변경됨 — 문구가 처음부터 그대로였다는 이전 서술은 부정확했다, 리뷰 2차 N4). D2 — AC-GROUP-007 픽스처가 한 주문의 노트 2건에 서로 다른 `line_item_id`를 부여하지 않아 `filterNotes`의 LineItem당 최신 1건 집계(`LineItemNotesPage.tsx:38-46`)에 걸려 Then(1차)의 "노트 2건 포함"이 원천적으로 성립 불가능했던 결함을 다른 다건 픽스처들(AC-001/003/004/006/008)과 동일하게 서로 다른 `line_item_id`·`id`·`created_at`을 명시해 해소 — 이 절이 AC-GROUP-007의 유일한 판별력 원천이었으므로 중대했다. D3 — `plan.md`가 "`useCreateLineItemNote`/`useLineItemNotes`를 모킹하지 않아도 되는 이유"로 "실제 훅을 호출하지만 렌더되지 않는 조건부 분기 안에 있다"고 서술했으나, `vi.mock(path, factory)`는 모듈 전체를 대체하므로 그 경로로는 실제 훅에 결코 도달할 수 없고 팩토리가 누락한 export는 접근 시 `No "X" export is defined on the mock` 예외가 난다 — 결론(이 SPEC의 T1~T8 범위에서는 모킹하지 않아도 안전하다)은 우연히 맞았을 뿐이므로 근거를 정정했다. **`created_at` 동률(tie-break) 처리 명시**: REQ-GROUP-005(그룹 정렬)·REQ-GROUP-006(그룹 내부 정렬) 각각에 `id` 내림차순 2차 정렬 키를 추가했다 — SPEC-ORDER-019가 도입한 Daily Review 일괄 노트 생성(`bulk_create`, 그 SPEC `plan.md` 참조)으로 같은 주문의 여러 노트가 동일한 `created_at`을 가질 수 있고, SPEC-ORDER-018 v1.0.3 D1이 `"pk"` tie-break 부재로 이미 같은 계열의 결함을 겪었다. 이를 검증하는 AC-GROUP-009(그룹 정렬 동률)·AC-GROUP-010(그룹 내부 정렬 동률)을 신규 추가했다. **그 외 D4~D12 전부 반영**: D4(REQ-GROUP-014를 "시스템이 주어인" Ubiquitous 문장으로 재작성 — process 제약이 아니라 시스템 구현 산출물에 대한 서술로 전환), D5·D12(REQ-GROUP-013의 EARS 레이블을 Unwanted → Ubiquitous로, AC-GROUP-001/002/003/004/005/007/008의 레이블을 Ubiquitous → State-Driven으로 정정 — Ubiquitous·Unwanted 모두 "If/then" 형태의 전제조건 없이 성립해야 하는데 이 여덟 AC는 전부 "Given …"으로 시작하는 상태 전제를 갖고 있었다. AC-GROUP-006만 "when … shall"의 진짜 Event-Driven 구조라 원래부터 올바른 라벨이었다), D6(AC-GROUP-007의 "correctly"/"올바르게" 형용사를 제거하고 구체적 단정으로 대체), D7(REQ-GROUP-013 검증을 특정 라벨("전체 해결" 등) 부재 확인 대신 그룹 스코프 안 해결 컨트롤 개수와 노트 개수의 일치 확인으로 강화 — 다른 라벨의 벌크 버튼도 잡아낸다), D9(`acceptance.md` 픽스처 표기에 `note_type`/`is_resolved` 명시적 안전값을 추가 — `note_type`이 `LineItemNotesPage.tsx:41`에서 타출판사 제외 판별에 쓰이는 하중값임에도 "임의 값"으로 방치되어 있었다), D10(AC-GROUP-005/006의 "mutation" 서술 중 이 SPEC 자체의 제약(`NoteCard` 무수정) 아래서는 실현 불가능한 것을 실현 가능한 것으로 교체 — AC-005는 그룹 스코프 오염, AC-006은 빈 그룹 잔존만 남긴다), D11(AC-GROUP-001 (c)의 "예: 동일한 역할/테스트 훅 속성"이라는 예시적·비구속적 표현을 그룹801과 동일한 단일 조회 헬퍼 재사용이라는 구속력 있는 검증 방식으로 교체)까지 전부 반영했다. |
| 1.0.2 | 2026-08-13 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-020-review-2.md`, iteration 2, FAIL, 0.86) 반영. 1차 블로킹 3건(D1/D2/D3)은 감사자가 독립 재검증으로 실제 해소를 확인했고 인용 75건도 허구·드리프트 0건이므로 그대로 두었다. **블로킹 1건 해소**: N1 — AC-GROUP-005가 스스로 명시한 mutation("그룹이 `tabNotes` 전체를 순회")을 실제로는 잡지 못했다. `NoteCard:244`가 노트마다 고유한 주문번호 텍스트를 그리므로, 그룹1102가 그룹1101의 노트까지 잘못 포함해도 `within(그룹1102).getByText('#G1102')`는 여전히 정확히 1개를 반환하고 `navigate('/orders/1102')`(`:241`)가 정상 실행되어 기존 Then 절이 전부 통과해 버린다 — `acceptance.md`의 "둘 이상의 후보 반환"·`spec.md`의 "wrong target" 서술은 사실이 아니었다. 조치: (a) 두 문서의 mutation 서술을 "클릭·이동 자체는 정상 동작하며 실제로 깨지는 것은 그룹 컨테이너 안의 주문번호 컨트롤 **개수**"라고 정정했다. (b) 그룹1101·그룹1102 각각의 컨테이너 안에서 주문번호 컨트롤 개수가 정확히 1개임을 단정하는 Then 절을 신규 추가했다 — 조회는 AC-GROUP-001 (d)와 동일한 방식(해결 버튼이 아닌 버튼의 개수를 세는 방식, 텍스트 매칭에 의존하지 않음)으로 구속력 있게 명시해 테스트 작성자의 정규식 선택에 좌우되지 않게 했다(1차 D11과 동일 계열 위험 차단). **권장 6건 반영**: N2(AC-GROUP-009/010 픽스처를 `id` 순서와 `order_id`/`line_item_id` 순서가 어긋나도록 재배치 — `order_id desc`나 `line_item_id desc` tie-break로는 더 이상 통과할 수 없다), N3(REQ-GROUP-013 검증에 페이지 스코프 절 추가 — 그룹 밖 툴바에 벌크 버튼이 있어도 전체 해결 컨트롤 수가 전체 노트 수를 초과해 잡힌다), N4(HISTORY의 AC-GROUP-008 이전 라벨 오기를 "Unwanted"에서 "Ubiquitous"로 정정, spec-compact.md 무변경 주장을 완화), N5(REQ-GROUP-005/006의 라벨을 "Ubiquitous primary clause; tie-break clause is State-Driven — compound"로 명시해 AC에 적용한 것과 같은 기준을 스스로도 지키도록 정정 — 번호 재부여 없이 라벨만 교정), N6(tie-break 근거에 `LineItemNoteUnresolvedListView.get_queryset()`이 `-created_at` 단일 키로만 정렬한다는 검증 가능한 근거(`views.py:278-282`)를 `bulk_create` 근거와 함께 병기, `created_at`의 ISO 8601 속성이 `types/order.ts:99`가 아니라 DRF 직렬화에서 온다는 점을 정정), N7(`line_item_id` 9601/9602가 AC-GROUP-005와 AC-GROUP-007에 중복 사용되던 것을 AC-GROUP-007을 9801/9802로 옮겨 분리)까지 전부 반영했다. |

---

## 문제 정의

`LineItemNotesPage`(`frontend/src/pages/LineItemNotesPage.tsx:306-414`)는 `useUnresolvedLineItemNotes()`(`:309`, 훅 정의
`frontend/src/features/order/hooks/useLineItemNotes.ts:61-69`)로 미해결 품목 노트 전량을 받아 `filterNotes(data, activeTab)`(`:313`, 함수 정의 `:35-49`)로 탭별
목록(`tabNotes`)을 만들고, 그 결과를 `<div className="space-y-2">`(`:400`) 아래 `tabNotes.map(note => <NoteCard .../>)`(`:401-410`)로
**평평하게 한 줄씩** 렌더링한다.

`filterNotes`는 정렬 기준을 노트의 생성 시각(사실상 원본 배열 순서)에 둘 뿐 `order_id`는 전혀 고려하지 않는다 — 타출판사 탭은 `note_type === '타출판사'`
필터만 적용(`:36`), CS/발주 탭은 `line_item_id`별 최신 노트 1건만 남기는 Map 집계(`:38-46`) 후 `assignee === tab`으로 거른다(`:48`). 그
결과 같은 주문(`order_id`)에 속한 여러 품목의 노트가 목록 안에서 서로 인접하지 않고 흩어질 수 있다 — 예를 들어 한 고객의 주문에 CS 미해결 노트가
3건 달려 있어도, 그 사이사이에 다른 주문의 노트가 끼어 있으면 CS 담당자는 목록 전체를 훑어야 그 3건을 전부 찾을 수 있고 하나를 놓치기 쉽다.

**같은 주문임을 식별할 데이터는 이미 응답에 있다.** `LineItemNoteUnresolvedListView`(`backend/order/views.py:269-282`)가
`filter(is_resolved=False)`(`:279`)로 전량을 반환하면, `LineItemNoteUnresolvedSerializer`(`backend/order/serializers.py:79-97`)가
`order_id`(`:86`, `source="line_item.order.id"`)와 `order_name`(`:85`, `source="line_item.order.name"`, `default=None`)을 이미
직렬화해 내려준다(`Meta.fields`에 포함, `:94-97`). 프론트엔드 타입 `LineItemNoteUnresolved`(`frontend/src/types/order.ts:103-110`)도 두 필드를
이미 갖고 있다. **단 하나 사용되지 않고 있는 것은 이 화면의 렌더링 방식뿐이다.**

기존 `NoteCard`(`:216-302`)는 각 행 헤더에 이미 주문번호 버튼을 그린다 — `note.order_name ?? \`주문 #${note.order_id}\`` (`:244`)를
표시하고 클릭 시 `navigate(\`/orders/${note.order_id}\`)`(`:241`)로 이동한다. 이 버튼과 폴백 규칙 자체는 이 SPEC이 그대로 재사용한다.

## 솔루션 개요

1. **그룹화는 탭 필터 결과에만 적용한다.** `filterNotes(data, activeTab)`가 만든 `tabNotes`(`:313`)를 입력으로 삼아 `order_id`별로
   묶는다. `filterNotes` 자체는 무수정이므로 탭별 건수(`countByTab`, `:344`)는 오늘과 동일하게 유지된다.
2. **그룹 키는 `order_id`, 표시는 `order_name` 폴백 규칙을 그대로 따른다.** `order_name ?? \`주문 #${order_id}\`` — `NoteCard:244`와
   동일한 규칙을 그룹 헤더에도 적용한다.
3. **그룹 정렬은 그룹 내 최신 노트의 `created_at` 내림차순.** 그룹 내부 정렬은 `created_at` 내림차순. 오늘 사용자가 보던 "최신이 위"라는
   체감을 그룹 레벨에서도 보존한다.
4. **노트 1건짜리 그룹도 다건 그룹과 동일한 컨테이너로 렌더링한다.** 레이아웃이 튀지 않도록 하되, 헤더는 시각적으로 가볍게 유지한다.
5. **기존 `NoteCard`는 무수정으로 그룹 내부 행으로 재사용한다.** 펼침/접힘, 이력(`NoteHistory`), 인라인 노트 추가(`InlineNoteForm`), 해결
   버튼 등 기존 상호작용은 전부 그대로 둔다 — `NoteCard`를 건드리지 않는 것 자체가 이 동작들의 보존을 보증한다.
6. **그룹 단위 일괄 해결 버튼은 만들지 않는다.** 해결은 오늘처럼 노트 단위로만 이루어진다.
7. **백엔드·API·모델·마이그레이션 변경 없음.** 필요한 필드가 이미 응답에 있다(위 문제 정의 참조).

## 범위 — 델타

브라운필드 UX 개편이다. 신규 엔드포인트도, 신규 화면도, 신규 백엔드 코드도 없다.

| 마커 | 대상 | 내용 |
|---|---|---|
| [MODIFY] | `LineItemNotesPage`(`frontend/src/pages/LineItemNotesPage.tsx`)의 렌더링부(`:400-411`) | 평평한 `tabNotes.map`을 `order_id` 기준 그룹 렌더링으로 교체. 이 SPEC의 프로덕션 코드 변경은 사실상 이 파일 하나다. |
| [EXISTING] | `filterNotes`(`:35-49`) | **무수정.** 그룹화는 이 함수의 출력을 입력으로 받을 뿐 이 함수를 바꾸지 않는다(REQ-GROUP-002). |
| [EXISTING] | `NoteCard`(`:216-302`)와 그 안의 `NoteHistory`(`:54-98`)·`InlineNoteForm`(`:103-211`) | **무수정.** 그룹 안의 행으로 그대로 재사용한다. |
| [EXISTING] | `countByTab`(`:344`), 탭 목록(`:343`), 로딩/에러 상태(`:325-341`), 타출판사 엑셀 다운로드 블록(`:371-392`) | 무수정. |
| [EXISTING] | `frontend/src/features/order/hooks/useLineItemNotes.ts` 전량 — `useUnresolvedLineItemNotes`(`:61-69`), `useResolveLineItemNote`(`:35-59`, 낙관적 제거 `:41-47`) | 무수정. 그룹은 이 훅이 관리하는 flat 캐시의 렌더 시점 파생물이므로 훅을 건드릴 필요가 없다. |
| [EXISTING] | `frontend/src/types/order.ts`의 `LineItemNoteUnresolved`(`:103-110`) | 무수정. `order_id`/`order_name`이 이미 있다. |
| [EXISTING] | `backend/order/views.py`(`LineItemNoteUnresolvedListView` `:269-282`), `backend/order/serializers.py`(`LineItemNoteUnresolvedSerializer` `:79-97`), `backend/order/urls.py:160`, `backend/order/models.py`(`LineItemNote` `:238-289`) | **전부 무수정.** 이 SPEC은 백엔드를 전혀 건드리지 않는다(REQ-GROUP-014). |
| [NEW] | `frontend/src/pages/LineItemNotesPage.test.tsx` | 이 페이지의 첫 테스트 파일. `OrderDetailPage.test.tsx`(`frontend/src/pages/OrderDetailPage.test.tsx`) 관례를 따른다. |

## 확정된 사용자 결정

1. **표현 = 주문번호 그룹 카드.** 같은 주문의 노트를 하나의 그룹 컨테이너로 감싸고, 헤더에 주문번호와 그 그룹의 노트 건수를 표시한다. 기존
   `NoteCard`는 그룹 안의 행으로 유지된다.
2. **그룹 범위 = 현재 탭 한정.** 그룹화는 이미 `filterNotes(notes, tab)`을 통과한 노트에 대해서만 동작한다. 다른 담당자/다른 탭의 노트를
   끌어오지 않는다. 탭별 건수는 오늘과 동일해야 한다.
3. **그룹 단위 일괄 해결 없음.** 그룹 레벨의 "전체 해결" 버튼은 추가하지 않는다. 해결은 계속 노트 단위로 기존 해결 버튼을 통해서만
   이루어진다.

## 명시적 가정

1. 그룹화는 CS·발주·타출판사 세 탭 모두에 동일하게 적용된다.
2. 그룹 정렬: 그룹 내 최신 노트의 `created_at` 내림차순 — 오늘 사용자가 보는 순서(최신 우선)를 그룹 레벨에서도 보존한다.
3. 그룹 내부 정렬: `created_at` 내림차순.
4. 노트 1건짜리 그룹도 다건 그룹과 동일한 그룹 컨테이너로 렌더링한다(레이아웃 튐 방지). 다만 헤더는 시각적으로 가볍게 유지한다.
5. 그룹 키는 `order_id`(안정적인 정수 — `types/order.ts:108`에서 `null`을 허용하지 않는다), 표시는 `order_name`이며 `null`이면
   `주문 #{order_id}`로 폴백한다(`NoteCard:244`와 동일 규칙).
6. **`NoteCard`(그 안의 주문번호 버튼 `:240-245`, 담당자/유형 배지 `:246-259`, 잘린 본문 `:260`, 해결 버튼 `:266-272` 포함)는
   무수정으로 유지된다.** 확정된 사용자 결정 1이 "기존 `NoteCard`는 그룹 안의 행으로 유지된다"고 명시했으므로, 그룹 헤더의 주문번호
   표시와 개별 노트 행의 기존 주문번호 버튼이 함께 나타나는 시각적 중복을 허용한다. 그룹 헤더 자체는 클릭 가능한 내비게이션 컨트롤이
   아니라 정보 표시(주문번호 + 건수)로 한정한다 — 새 내비게이션 진입점을 만들지 않는다. 중복 제거는 이 SPEC의 범위가 아니다(후속 과제).
7. 프론트엔드 전용 변경이다. 시리얼라이저가 이미 `order_id`(`serializers.py:86`)와 `order_name`(`:85`)을 내려주므로 API·모델·
   마이그레이션 변경이 필요 없다.

---

## 요구사항 (EARS)

요구사항은 6개 모듈, REQ-GROUP-001부터 REQ-GROUP-014까지 연속 번호로 구성된다. "활성 탭의 노트"는 `filterNotes(data, activeTab)`의
출력(`tabNotes`)을 뜻한다.

### 모듈 1 — 그룹 구성

**REQ-GROUP-001** (Ubiquitous): The system shall group the notes rendered in the active tab by the order (`order_id`) each note's
line item belongs to, wrapping every note that shares an `order_id` within a single group container.

**REQ-GROUP-002** (Ubiquitous): The system shall build groups exclusively from the notes that already pass the existing per-tab
filter output, and shall not modify or bypass that filter to do so.

**REQ-GROUP-003** (Ubiquitous): The system shall display, for every group, the order's display identifier and the count of notes
contained within that group.

**REQ-GROUP-004** (Ubiquitous): The system shall render a group that contains exactly one note using the same group-container
structure as a group that contains multiple notes.

### 모듈 2 — 그룹·그룹 내부 정렬

**REQ-GROUP-005** (Ubiquitous primary clause; tie-break clause is State-Driven — compound): The system shall order the rendered
groups by the `created_at` value of the newest note within each group, most recent first; **while** two or more groups' newest
notes share an identical `created_at` value, the system shall break the tie by the `id` of those newest notes, higher `id`
first.

**REQ-GROUP-006** (Ubiquitous primary clause; tie-break clause is State-Driven — compound): The system shall order the notes
within a group by `created_at`, most recent first; **while** two or more notes within the same group share an identical
`created_at` value, the system shall break the tie by `id`, higher `id` first.

### 모듈 3 — 탭 스코프·건수 보존

**REQ-GROUP-007** (Ubiquitous): The system shall compute the count displayed next to each tab label from the same set of notes
the existing per-tab filter produces, unaffected by how those notes are subsequently grouped for display.

**REQ-GROUP-008** (Unwanted): If a note belongs to an assignee scope outside the active tab, then the system shall not include
that note in any group rendered on the active tab, even when that note shares an `order_id` with a note that does belong to the
active tab.

### 모듈 4 — 상호작용 불변

**REQ-GROUP-009** (Ubiquitous): The system shall preserve each note's existing order-detail navigation control and resolve
control — same destination, same target note — unchanged after wrapping notes into order groups.

**REQ-GROUP-010** (Event-Driven): When a user resolves a note, the system shall remove only that note's row from its group,
leaving every other note in that group, and every other group, unaffected.

**REQ-GROUP-011** (Event-Driven): When resolving a note leaves its group with zero remaining notes, the system shall remove that
group's container from the display.

### 모듈 5 — 빈 상태

**REQ-GROUP-012** (Ubiquitous): The system shall continue to display the existing empty-state message when the active tab's
filtered note set is empty, and shall render no group container in that state.

### 모듈 6 — 금지 사항 및 스코프 경계

**REQ-GROUP-013** (Ubiquitous): The system shall not provide a control that resolves more than one note in a single user action.

**REQ-GROUP-014** (Ubiquitous): The system shall implement every requirement in this SPEC without adding or changing any backend
endpoint, serializer field, database model, or migration.

---

## ACCEPTANCE CRITERIA

[HARD] 각 인수 기준은 **판별력**을 갖는다 — 구현이 되돌려지거나 stub되면 반드시 실패한다. 그룹 컨테이너의 존재 자체가 이 SPEC의 핵심
산출물이므로, 대부분의 시나리오는 조회를 그룹 컨테이너를 통해서(`within` 패턴) 수행한다 — 그룹이 아직 없는(미구현) 코드에서는 그 조회
자체가 실패하므로 별도 mutation 없이도 판별력이 성립한다. 각 항목은 자신을 깨뜨리는 mutation을 한 줄로 명시한다. 실행 가능한
Given/When/Then 시나리오는 `acceptance.md`에 있으며 동일한 `Traces:` 목록을 인용한다.

**AC-GROUP-001** (State-Driven) — Traces: REQ-GROUP-001, REQ-GROUP-002, REQ-GROUP-003, REQ-GROUP-004, REQ-GROUP-013. Given two
orders in the active tab where one order has two eligible notes and the other has one, the system shall render the two-note
order's notes inside one shared group container, render the one-note order using the same group-container structure, label each
group with its order identifier and its note count, expose a number of resolve controls within each group that equals that
group's note count (never more), and expose a page-level total number of resolve controls across all groups that equals the
active tab's total note count (never more) — so that a bulk-resolve control placed outside every group container, not just
inside one, is also caught.
*Mutation that breaks it*: reverting to the flat list — the two-note order's notes are not DOM-contained within a shared group
element, so the containment query finds no such element. Adding a group-level "resolve all" control breaks the per-group count.
Adding a page-level or toolbar-level "resolve all" control outside every group breaks the page-level total instead — the
per-group counts alone would not catch it.

**AC-GROUP-002** (State-Driven) — Traces: REQ-GROUP-005. Given three single-note orders whose notes arrive in an order that does
not match their `created_at` ranking, the system shall render their groups sorted by each group's newest note, most recent
first.
*Mutation that breaks it*: grouping without sorting (preserving arrival order) — the rendered group sequence matches arrival
order instead of the newest-first order. Reversion also breaks it — no group elements exist to sequence.

**AC-GROUP-003** (State-Driven) — Traces: REQ-GROUP-006. Given one order with two notes on different line items that arrive with
the older note first, the system shall render the newer note above the older note inside that order's group.
*Mutation that breaks it*: grouping without an intra-group sort — the notes render in arrival order (older first) instead of
newest first. Reversion also breaks it — no group container exists to inspect.

**AC-GROUP-004** (State-Driven) — Traces: REQ-GROUP-007. Given a tab whose notes span two orders with a known total note count,
the system shall render that many individual note rows across the tab's group containers, while the tab label's count matches
that same total, not the number of groups.
*Mutation that breaks it*: computing the tab count from the number of groups instead of the number of notes — the label shows a
smaller number than the actual note total. Reversion also breaks it — no group containers exist to sum rows from.

**AC-GROUP-005** (State-Driven) — Traces: REQ-GROUP-009. Given two single-note orders each in its own group, the system shall
navigate to each order's detail view when that order's group's note row's order-identifier control is activated, matching the
`order_id` of the note the control belongs to, and shall render within each group's container exactly as many
order-identifier controls as that group's note count — never more.
*Mutation that breaks it*: a grouping implementation that maps over the full `tabNotes` array inside each group's render instead
of that group's own filtered notes (e.g., forgetting to scope the inner map to the group) — the count of order-identifier
controls inside a group container exceeds that group's note count (group 1102 would contain two instead of one). The
click-and-navigate assertions alone do *not* catch this mutation: `NoteCard:244` renders each note's own order text and
`NoteCard:241` still calls `navigate` with that note's own `order_id`, so a query for a specific order string
(e.g., `"#G1102"`) still resolves to exactly one match even when the group wrongly contains an extra row from another order —
the click still fires and still navigates correctly. The control-count clause is this AC's own discriminator for that
mutation; it is also caught incidentally by AC-GROUP-001 (d) and AC-GROUP-004 (a), but this AC no longer depends on that.
Reversion also breaks it — the control is queried from within a group container that does not exist.

**AC-GROUP-006** (Event-Driven) — Traces: REQ-GROUP-009, REQ-GROUP-010, REQ-GROUP-011. Given one order's group holding two
notes, when the first note is resolved the system shall remove only that note's row and leave the group container with the
second note still present; when the second (last) note in that group is then resolved, the system shall remove the group
container itself from the document.
*Mutation that breaks it*: leaving an empty group container in place after its last note is resolved. Reversion also breaks it —
no group container exists to query in the first place. (The first clause — resolving one note leaves its sibling note's row
untouched — follows directly from `NoteCard` remaining unmodified and bound to its own `note` prop per 명시적 가정 6; no
independent adversarial mutation targets that clause alone, though a regression there would still be caught since both clauses
share the same group-container lookup.)

**AC-GROUP-007** (State-Driven) — Traces: REQ-GROUP-012. Given a fixture where the active tab has notes forming at least one
group and a second tab has zero eligible notes, the system shall render the populated tab's group container holding all of its
notes, and upon switching to the empty tab shall show the existing empty-state message and render no group container at all.
*Mutation that breaks it*: rendering a phantom empty group wrapper when the filtered note set is empty (e.g., mis-checking
`groups.length` on an object keyed by nothing) — a group container is found where none should exist. The populated-tab clause
also breaks under reversion — no group container exists for it either. (The empty-tab clause alone would pass on unmodified
code, since the empty-state message already exists today; discriminating power for that clause rests solely on the phantom-group
mutation, which is stated explicitly here for transparency.)

**AC-GROUP-008** (State-Driven) — Traces: REQ-GROUP-002, REQ-GROUP-008. Given one order with one note assigned to the active tab's
role and a second note on the same order assigned to a different role, the system shall render that order's group on the active
tab containing exactly the one note that belongs to the active tab, with a note count of one, not two.
*Mutation that breaks it*: grouping the raw unresolved-note list by `order_id` before applying the per-tab filter, instead of
after — the group's displayed count includes the other tab's note. Reversion also breaks it — no group container exists to
query the count from.

**AC-GROUP-009** (State-Driven) — Traces: REQ-GROUP-005. Given two single-note orders whose notes share an identical
`created_at` value but different `id`s, and whose arrival order in the mocked data does not match `id` order, the system shall
render the group whose newest note has the higher `id` first.
*Mutation that breaks it*: sorting by `created_at` alone with no tie-break — a stable sort preserves arrival order for equal
keys, so the rendered sequence matches arrival order instead of the `id`-descending order, which this scenario deliberately
makes different from arrival order. Reversion also breaks it — no group elements exist to sequence.

**AC-GROUP-010** (State-Driven) — Traces: REQ-GROUP-006. Given one order with two notes on different line items that share an
identical `created_at` value but different `id`s, and whose arrival order does not match `id` order, the system shall render the
note with the higher `id` above the note with the lower `id` inside that order's group.
*Mutation that breaks it*: sorting by `created_at` alone with no tie-break — a stable sort preserves arrival order for equal
keys, so the lower-`id` note would remain on top, contradicting the expected `id`-descending order this scenario deliberately
arranges to differ from arrival order. Reversion also breaks it — no group container exists to inspect.

### Traceability 검증표

| REQ | 커버하는 AC |
|---|---|
| REQ-GROUP-001 | AC-GROUP-001 |
| REQ-GROUP-002 | AC-GROUP-001, AC-GROUP-008 |
| REQ-GROUP-003 | AC-GROUP-001 |
| REQ-GROUP-004 | AC-GROUP-001 |
| REQ-GROUP-005 | AC-GROUP-002, AC-GROUP-009 |
| REQ-GROUP-006 | AC-GROUP-003, AC-GROUP-010 |
| REQ-GROUP-007 | AC-GROUP-004 |
| REQ-GROUP-008 | AC-GROUP-008 |
| REQ-GROUP-009 | AC-GROUP-005, AC-GROUP-006 |
| REQ-GROUP-010 | AC-GROUP-006 |
| REQ-GROUP-011 | AC-GROUP-006 |
| REQ-GROUP-012 | AC-GROUP-007 |
| REQ-GROUP-013 | AC-GROUP-001 |
| REQ-GROUP-014 | `plan.md` 완료 조건의 `git diff --stat backend/` 게이트 (런타임 AC 없음 — 프론트엔드 전용 스코프 제약이므로 diff 검증으로 충족) |

14개 요구사항 중 13개가 10개 인수 기준으로 직접 커버된다. 나머지 1개(REQ-GROUP-014)는 스코프 제약이며 `plan.md`의 빌드/diff 게이트로
검증한다.

---

## Exclusions (What NOT to Build)

- **백엔드/API/시리얼라이저/DB 변경 없음.** `order_id`/`order_name`이 이미 응답에 있다(`serializers.py:85-86`, `:94-97`). 신규
  엔드포인트, 신규 쿼리 파라미터, 신규 필드를 추가하지 않는다.
- **그룹 단위 일괄 해결 없음.** "전체 해결" 같은 그룹 레벨 컨트롤을 만들지 않는다(확정된 사용자 결정 3, REQ-GROUP-013).
- **탭 간 노트 집계 없음.** 그룹화는 활성 탭의 `filterNotes` 출력에만 적용되며, 다른 탭/다른 담당자의 노트를 끌어오지 않는다(확정된
  사용자 결정 2, REQ-GROUP-008).
- **목록의 페이지네이션·가상화 없음.** `pagination_class = None`(`views.py:275`)인 기존 API 계약을 그대로 쓰며, 프론트엔드에도
  무한 스크롤·가상 리스트를 도입하지 않는다.
- **타출판사 엑셀 내보내기 흐름 변경 없음.** `downloadLineItemNotesExcel`(`useLineItemNotes.ts:71-84`)과 다운로드 버튼
  블록(`LineItemNotesPage.tsx:371-392`)은 무수정이다.
- **`NoteCard`·`NoteHistory`·`InlineNoteForm` 내부 로직 변경 없음.** 그룹 안의 행으로 그대로 재사용한다(명시적 가정 6).
- **`filterNotes`의 "LineItem당 최신 1건" 규칙 변경 없음.** SPEC-ORDER-019 후속 과제 2가 이미 등록해 둔 별개의 논의이며, 이
  SPEC은 그 규칙의 출력을 있는 그대로 그룹화할 뿐 규칙 자체를 재검토하지 않는다.
- **그룹 컨테이너에 클릭 내비게이션을 추가하지 않는다.** 그룹 헤더는 정보 표시(주문번호 + 건수)로 한정한다(명시적 가정 6).
- **주문번호 중복 표시 제거 없음.** 그룹 헤더와 개별 `NoteCard` 행 양쪽에 주문번호가 함께 보이는 것을 이 SPEC은 그대로 둔다(명시적
  가정 6, 후속 과제로 등록).

## 후속 과제

1. **그룹 헤더·개별 행의 주문번호 중복 표시 정리.** 명시적 가정 6이 허용한 절충이다. `NoteCard`의 주문번호 버튼(`:240-245`)을
   그룹 안에서는 생략하는 리팩터링은 `NoteCard`를 그룹 유무에 따라 분기시켜야 해 이 SPEC의 "NoteCard 무수정" 제약과 충돌한다 —
   별도 SPEC에서 다룬다.
2. **그룹 헤더 자체에 접기/펼치기 기능을 둘지 검토.** 이 SPEC은 그룹을 항상 펼친 상태로만 렌더링한다. 한 주문에 노트가 매우 많은
   경우(운영 데이터 기준 흔치 않음)의 화면 길이는 범위 밖이다.
3. **`filterNotes`의 "LineItem당 최신 1건" 규칙 재검토**(SPEC-ORDER-019 후속 과제 2에서 이미 등록). 이 SPEC과는 독립적이지만
   같은 함수를 다루므로 함께 검토할 여지가 있다.

## 관련 SPEC

- **SPEC-ORDER-010** — `LineItemNote` 모델(`models.py:238-289`)과 노트 API(`views.py:251-296`) 도입. 이 SPEC이 그룹화하는
  데이터의 출처다.
- **SPEC-ORDER-019** — Daily Review 업로드가 배포처 행 메모를 `assignee="발주"`로 `LineItemNote`에 저장하도록 확장(구현 완료,
  커밋 `7b9f494`). 그 SPEC의 설계 결정 E가 `filterNotes`의 "LineItem당 최신 1건" 규칙과 표시 경로 전체(`views.py:269-282` →
  `serializers.py:79-97` → `LineItemNotesPage.tsx:35-49`)를 추적해 문서화했으며, 이 SPEC은 그 경로의 출력(`tabNotes`)을
  입력으로 그대로 사용한다. 그 SPEC의 후속 과제 2("LineItem당 최신 1건" 규칙 재검토)는 이 SPEC과 별개로 남아 있다. 그
  SPEC이 도입한 Daily Review 일괄 노트 생성(`bulk_create`)은 이 SPEC의 REQ-GROUP-005/006 `id` tie-break가 대응하는
  동일 `created_at` 발생의 개연적 원인이다(`created_at`은 `auto_now_add=True`이며 `bulk_create`가 객체마다 별도로
  `timezone.now()`를 호출하므로 동일 마이크로초 값은 "가능하지만 체계적이지는 않다"). **더 직접적으로 검증 가능한
  근거는 조회 자체에 있다** — `LineItemNoteUnresolvedListView.get_queryset()`(`views.py:277-282`)이
  `order_by("-created_at")` 단일 키로만 정렬하고(`:281`) 2차 키가 없으므로, 동일한 `created_at`을 가진 행들의
  DB 반환 순서는 애초에 비결정적이다 — 노트가 어떻게 만들어졌는지와 무관하게, 이 정렬 자체가 tie-break 없이는
  안정성을 보장하지 않는다.
- **SPEC-ORDER-018** — v1.0.3 D1이 `"pk"` tie-break 부재로 정렬 단정이 비결정적이 되는 결함을 겪은 선례. 이 SPEC의
  REQ-GROUP-005/006 `id` tie-break는 그 교훈을 사전에 적용한 것이다.
