---
id: SPEC-ORDER-020
document: plan
version: 1.0.2
status: draft
updated: 2026-08-13
---

# 구현 계획 — SPEC-ORDER-020 미해결 품목 메모 주문번호 그룹화

`spec.md`의 요구사항(REQ-GROUP-001~014)을 구현하기 위한 작업 분해, 파일별 변경 계획, TDD 사이클, 리스크와 완화책, MX 태그 계획을
정리한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을 재진술하지 않고 REQ ID로
참조한다.

**개발 방법론**: TDD (RED-GREEN-REFACTOR). `.moai/config/sections/quality.yaml`의 `development_mode: "tdd"`(`:4`),
`test_first_required: true`(`:43`), `min_coverage_per_commit: 80`(`:46`)에 따른다. 브라운필드 변경이므로 각 RED 단계 전에
대상 코드를 먼저 읽는 사전 단계를 거친다(`.claude/rules/moai/workflow/workflow-modes.md`의 Brownfield Enhancement 절).

**이 SPEC의 특이점**: 프로덕션 코드 변경이 `LineItemNotesPage.tsx`의 렌더링부(`:400-411`) 교체 한 곳뿐이다. `filterNotes`도
`NoteCard`도 훅도 백엔드도 무수정이다. 또한 이 페이지의 **첫 테스트 파일**을 만드는 작업이라, 테스트 인프라(모킹 관례)를 이번에
확립한다.

---

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M0 (High) — 베이스라인 확인**: `frontend/src/pages/LineItemNotesPage.tsx`(전체 414줄)와
  `frontend/src/pages/OrderDetailPage.test.tsx`(모킹·렌더 헬퍼 관례)를 다시 읽고, 기존 프론트엔드 테스트 스위트
  (`OrderDetailPage.test.tsx`, `DashboardPage.test.tsx`, `ForbiddenPage.test.tsx`)가 현재 통과 상태인지 확인한다. 이 SPEC
  이전부터 실패하던 것과 이 SPEC이 깬 것을 구분하는 기준이 된다.

- **M1 (High) — 인수 기준 계약 테스트 선작성 (RED)**: `frontend/src/pages/LineItemNotesPage.test.tsx`를 신규 작성한다.
  T1~T10이 `acceptance.md`의 AC-GROUP-001~010에 대응한다(REQ-GROUP-005/006의 `created_at` 동률 처리를 검증하는
  AC-GROUP-009/010이 T9/T10). **T1~T6, T8~T10은 현재 코드(그룹 컨테이너가 없는 평평한 렌더링)에서 반드시 실패해야
  한다** — 그룹 컨테이너를 조회하는 시점에 실패하므로 판별력이 자연히 성립한다. T7(빈 상태)은 그룹이 있는 절과 없는
  절을 함께 검증하므로, 그룹이 있는 절에서 실패한다(`spec.md` ACCEPTANCE CRITERIA의 AC-GROUP-007 판별력 주석 참조).
  T6의 1차 단정(형제 노트가 살아남는다)은 `NoteCard` 무수정 설계에서 자동으로 성립하는 성질이라 별도의 mutation 없이도
  그룹 컨테이너 부재로 되돌림 실패가 성립한다(`acceptance.md` AC-GROUP-006 판별력 주석 참조). 실패하지 않는 테스트가
  있다면 판별력이 없다는 뜻이므로 다시 쓴다.

- **M2 (High) — 그룹화 구현 (GREEN)**: `LineItemNotesPage.tsx`의 `:400-411`을 `tabNotes`를 `order_id`로 묶어 그룹 컨테이너
  단위로 렌더링하도록 교체한다. `filterNotes`(`:35-49`), `countByTab`(`:344`), `NoteCard`(`:216-302`)는 **한 글자도
  건드리지 않는다.**

- **M3 (Medium) — REFACTOR**: 그룹화 로직(정렬 2단계 — 그룹 정렬, 그룹 내부 정렬 — 각각 `created_at` 내림차순 + `id`
  내림차순 동률 처리)의 가독성을 다듬는다. `countByTab`이 여전히 `filterNotes(...).length`를 쓰고 그룹 수를 세지
  않는지 재확인한다(REQ-GROUP-007 회귀 방지).

- **M4 (Medium) — 회귀 확인**: 기존 프론트엔드 테스트 스위트 전량 재실행, 타출판사 엑셀 다운로드 블록(`:371-392`)과 로딩/에러
  상태(`:325-341`)가 수동으로도 정상 동작하는지 확인한다. `git diff --stat backend/`가 비어 있는지 확인한다(REQ-GROUP-014).

- **M5 (Low) — MX 태그 적용 + 문서 동기화**: 아래 MX 태그 계획을 적용하고, `spec.md`/`plan.md`/`acceptance.md`/
  `spec-compact.md`의 `status`를 갱신하며 구현 중 발견한 발산을 `spec.md` HISTORY에 기록한다.

의존 관계: M0 → M1 → M2 → M3 → M4 → M5.

---

## 파일별 변경 계획

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `frontend/src/pages/LineItemNotesPage.tsx`(`:400-411`) | `tabNotes.map(note => <NoteCard .../>)` 평면 렌더링을 `order_id` 기준 그룹 렌더링으로 교체. 그룹화 입력은 `tabNotes`(`:313`, `filterNotes(data, activeTab)`의 결과)이며 `filterNotes` 자체는 호출 지점(`:313`)과 정의(`:35-49`) 모두 무수정. 그룹 컨테이너는 테스트가 안정적으로 조회할 수 있도록 그룹마다 식별 가능한 마커(예: 테스트 훅 속성)를 갖는 것을 권장한다 — 인수 기준 전량이 그룹 컨테이너를 통한 조회에 의존하기 때문이다. 그룹 헤더는 정보 표시 전용(주문번호 + 건수)이며 별도 클릭 핸들러를 두지 않는다(`spec.md` 명시적 가정 6). |
| NEW | `frontend/src/pages/LineItemNotesPage.test.tsx` | `OrderDetailPage.test.tsx`(`frontend/src/pages/OrderDetailPage.test.tsx:1-33` 관례 — vitest + React Testing Library, `vi.mock`으로 훅 모킹, `QueryClientProvider` + `MemoryRouter`로 렌더)를 복제한다. `vi.mock('@/features/order/hooks/useLineItemNotes', factory)`는 **모듈 전체를 대체**한다 — 팩토리가 반환하는 객체에 없는 export는 실제 훅으로 폴백되지 않으며, 코드가 그 export를 실제로 참조/호출하는 시점에(임포트 시점이 아니라) Vitest가 `No "X" export is defined on the mock. Did you forget to return it from "vi.mock" factory?` 예외를 던진다. `LineItemNotesPage.tsx`가 이 모듈에서 임포트하는 export는 6개다 — `LINE_ITEM_NOTES_QUERY_KEY`(`:3`), `useUnresolvedLineItemNotes`/`useResolveLineItemNote`/`useCreateLineItemNote`/`useLineItemNotes`/`downloadLineItemNotesExcel`(`:5-11`). T1~T10 중 어떤 시나리오도 `NoteCard`를 펼쳐 `InlineNoteForm`을 열거나(`useCreateLineItemNote`/`useLineItemNotes` 호출 경로) 타출판사 엑셀 버튼을 클릭하지 않으므로(`downloadLineItemNotesExcel`/`LINE_ITEM_NOTES_QUERY_KEY` 호출 경로), 팩토리에서 `useUnresolvedLineItemNotes`와 `useResolveLineItemNote`만 반환하고 나머지 4개를 생략해도 T1~T10은 예외 없이 통과한다 — 다만 이는 **이 SPEC의 테스트 범위가 그 코드 경로에 닿지 않기 때문에** 안전한 것이지, 팩토리에서 export를 생략하는 것이 일반적으로 안전하다는 뜻은 아니다. 이후 이 페이지에 카드 펼침·인라인폼·엑셀 내보내기를 다루는 시나리오를 추가하는 테스트 작성자는 그 경로가 참조하는 export까지 팩토리를 확장해야 한다. 모듈 docstring 대신 파일 상단 주석에 `Coverage targets: T1~T10` 및 AC 매핑을 남긴다. |
| EXISTING (무수정) | `filterNotes`(`:35-49`), `countByTab`(`:344`), 탭 목록(`:343`), `NoteCard`(`:216-302`), `NoteHistory`(`:54-98`), `InlineNoteForm`(`:103-211`), 로딩/에러 상태(`:325-341`), 타출판사 다운로드 블록(`:371-392`) | `spec.md` Exclusions. |
| EXISTING (무수정) | `frontend/src/features/order/hooks/useLineItemNotes.ts` 전량 | `LINE_ITEM_NOTES_QUERY_KEY`(`:7`), `useUnresolvedLineItemNotes`(`:61-69`), `useResolveLineItemNote`의 낙관적 제거(`:41-47`) — 그룹은 이 훅이 갱신하는 flat 캐시의 렌더 시점 파생물이므로 훅을 건드릴 필요가 없다(REQ-GROUP-010/011의 근거). |
| EXISTING (무수정) | `frontend/src/types/order.ts`의 `LineItemNoteUnresolved`(`:103-110`) | `order_id`/`order_name`이 이미 있다. |
| EXISTING (무수정) | `backend/order/views.py`(`LineItemNoteUnresolvedListView` `:269-282`), `backend/order/serializers.py`(`LineItemNoteUnresolvedSerializer` `:79-97`), `backend/order/urls.py:160`, `backend/order/models.py`(`LineItemNote` `:238-289`) | `spec.md` REQ-GROUP-014. `git diff --stat backend/`가 비어 있어야 한다. |

---

## 기술적 접근

### 그룹화 (M2)

1. **입력**: `tabNotes`(`LineItemNotesPage.tsx:313`) — `filterNotes(data, activeTab)`의 결과. 이미 활성 탭 스코프로
   걸러진 배열이다(REQ-GROUP-002).
2. **그룹 키**: 각 노트의 `order_id`. `types/order.ts:108`에서 `number`(non-null)이므로 폴백이 필요 없다.
3. **그룹 정렬**: 각 그룹의 노트 중 `created_at`이 가장 큰 값을 그 그룹의 1차 정렬 키로 삼아 내림차순 정렬한다. **동률
   처리(2차 키)**: 두 그룹의 최신 노트 `created_at`이 동일하면 그 최신 노트의 `id`를 2차 키로 삼아 내림차순 정렬한다
   (REQ-GROUP-005, AC-GROUP-002/AC-GROUP-009가 판별). `id`는 모든 노트가 갖는 고유 정수이므로(`types/order.ts:93-101`의
   `LineItemNote.id`를 `LineItemNoteUnresolved`가 상속) 2차 키에서 다시 동률이 날 수 없다 — 3차 키는 불필요하다.
4. **그룹 내부 정렬**: 그룹 안의 노트를 `created_at` 내림차순으로, 동률이면 `id` 내림차순으로 정렬한다(REQ-GROUP-006,
   AC-GROUP-003/AC-GROUP-010이 판별). **동률의 근거는 두 가지다.** (가능성) SPEC-ORDER-019가 도입한 Daily Review
   일괄 노트 생성(`purchase_order_views.py`의 `bulk_create` — 그 SPEC의 `plan.md` "기술적 접근" 참조)은 같은 요청
   안에서 만들어진 여러 `LineItemNote`가 동일한 `created_at`을 가질 수 있는 경로다 — `created_at`은
   `auto_now_add=True`(`backend/order/models.py:272`)이고 `bulk_create`가 객체마다 별도로 `timezone.now()`를
   호출하므로 동일 마이크로초 값은 가능하지만 체계적이지는 않다. **(확정) 더 직접적인 근거는 조회 자체에 있다** —
   `LineItemNoteUnresolvedListView.get_queryset()`(`backend/order/views.py:277-282`)이 `order_by("-created_at")`
   단일 키로만 정렬하고(`:281`) 2차 키가 없으므로, 동일한 `created_at`을 가진 행들 사이의 DB 반환 순서는 노트가
   어떻게 만들어졌는지와 무관하게 애초에 비결정적이다 — 이것이 REQ-GROUP-005/006에 프론트엔드 2차 키가 필요한
   이유를 백엔드 변경 없이도 검증 가능하게 만든다. 두 정렬 모두 **동일한 비교 함수**를 재사용하면 그룹 정렬과 그룹
   내부 정렬의 동률 처리가 어긋날 위험이 없다 — `created_at`은 `types/order.ts:99`에서 `string` 타입으로만 선언되어
   있고 그 값이 ISO 8601 형식이라는 성질은 타입 선언이 아니라 DRF `DateTimeField` 직렬화가 만드는 런타임 성질이다.
   그 성질에 의존해 문자열 비교(`>`, `<`)만으로 시간 순서가 정확히 정렬된다(예: `(a, b) => a.created_at !== b.created_at
   ? (a.created_at > b.created_at ? -1 : 1) : b.id - a.id`). 이 프로젝트의 `frontend/package.json`에는 date-fns/dayjs
   등 날짜 라이브러리가 없으므로 신규 의존성을 끌어들이지 않는다.
5. **표시**: 그룹 헤더에 `order_name ?? \`주문 #${order_id}\`` (`NoteCard:244`와 동일 폴백 규칙)와 그룹 내 노트 건수를
   표시한다(REQ-GROUP-003). 노트 1건짜리 그룹도 다건 그룹과 동일한 컨테이너 구조를 쓴다(REQ-GROUP-004) — 그룹801과
   그룹802를 같은 조회 헬퍼로 찾을 수 있어야 한다(AC-GROUP-001 (c)).
6. **행**: 그룹 안에서 기존 `NoteCard`를 그대로 렌더링한다 — props(`note`, `onResolve`, `isResolving`, `showAddForm`,
   `currentTabAssignee`)는 오늘과 동일하게 전달하며, 각 그룹은 **자신의 노트 배열만** 순회한다(다른 그룹의 배열이나
   `tabNotes` 전체를 순회하지 않는다 — AC-GROUP-005 (b)의 그룹별 컨트롤 개수 대조, AC-GROUP-001 (d), AC-GROUP-004
   (a), AC-GROUP-008이 함께 판별한다). 클릭·내비게이션 자체(AC-GROUP-005 (a))는 `NoteCard`가 무수정이라 이 버그가
   있어도 정상 동작하므로 판별하지 못한다는 점에 유의 — 개수 대조가 유일한 판별 수단이다.
7. **카운트 배지**: `countByTab`(`:344`)은 `filterNotes(data, tab).length`를 그대로 쓴다 — 그룹 수(`Object.keys(...).length`
   등)로 바꾸지 **않는다**(REQ-GROUP-007, AC-GROUP-004가 판별).

**구현자를 위한 이름 제안(강제 아님)**: 그룹화 로직을 순수 함수(예: `groupNotesByOrder(notes)` 형태)로 분리하면 위 단계들을
테스트하기 쉬워진다. 함수명·형태는 구현자 재량이며 `spec.md`는 이를 규정하지 않는다.

**하지 말 것**:
- 그룹 헤더에 `onClick`을 달아 새로운 내비게이션 진입점을 만들기 — `spec.md` 명시적 가정 6 위반.
- 그룹 레벨 "전체 해결" 컨트롤 추가(라벨을 무엇으로 짓든) — REQ-GROUP-013 위반, AC-GROUP-001 (d)의 컨트롤 개수 대조가 판별.
  페이지 레벨(툴바 등, 어느 그룹 스코프에도 속하지 않는) 벌크 해결 컨트롤도 동일하게 금지 — AC-GROUP-001 (e)의 페이지
  전체 컨트롤 총합 대조가 판별한다(그룹 스코프 대조만으로는 잡히지 않는다).
- `filterNotes`를 그룹화 로직 안으로 인라인하거나 수정 — REQ-GROUP-002 위반.
- `NoteCard`의 주문번호 버튼(`:240-245`)을 그룹 존재 여부에 따라 조건부로 숨기기 — `NoteCard` 무수정 제약 위반(`spec.md`
  명시적 가정 6).
- `countByTab`을 그룹 배열 길이로 재계산 — REQ-GROUP-007 위반, AC-GROUP-004가 판별.
- `created_at`만으로 정렬하고 동률 처리를 생략 — 안정 정렬이 우연히 도착 순서를 유지해 정상처럼 보일 수 있으나
  REQ-GROUP-005/006 위반이며 AC-GROUP-009/010이 판별.

### 테스트 (M1)

- **T1**(AC-GROUP-001): 두 주문(한쪽 2건, 한쪽 1건, 총 3건)을 모킹 데이터로 구성. 2건짜리 주문의 그룹 컨테이너 안에 두
  노트 콘텐츠가 모두 있는지 `within(그룹 컨테이너)`로 확인. 1건짜리 주문도 **그룹801을 찾은 것과 동일한 조회
  헬퍼**(`order_id`만 바꿔 재사용)로 그룹 컨테이너를 찾을 수 있는지 확인 — 그룹801 전용 셀렉터를 쓰지 않는다. 그룹
  헤더에 주문번호 + 건수 텍스트 확인. 각 그룹 스코프 안의 해결 컨트롤 개수가 그 그룹의 노트 개수와 정확히 같은지
  (라벨 문구가 아니라 **개수**로) 확인. **추가로** 그룹 스코프가 아니라 **페이지 전체**에서 해결 컨트롤 총 개수를
  세어 탭의 전체 노트 개수(3)와 정확히 같은지 확인 — 그룹 밖(툴바 등)의 벌크 컨트롤은 그룹별 대조만으로는 잡히지
  않으므로 이 페이지 스코프 대조가 별도로 필요하다.
- **T2**(AC-GROUP-002): 단일 노트 주문 3개, `created_at`이 서로 다르고 모킹 배열의 도착 순서가 시간 순서와 어긋나도록 구성
  (예: 오래된 것 → 최신 것 → 중간 것 순으로 배열). 렌더된 그룹 헤더들의 DOM 순서가 최신 우선인지 확인.
- **T3**(AC-GROUP-003): 한 주문 안에 서로 다른 품목의 노트 2건, 도착 순서는 오래된 것이 먼저. 그룹 안에서 최신 노트가
  먼저(위) 렌더링되는지 확인.
- **T4**(AC-GROUP-004): 두 주문에 걸쳐 노트 총 N건을 구성. 그룹 컨테이너들 안의 노트 행 총합이 N인지, 탭 라벨의 카운트도
  N인지(그룹 수가 아니라) 확인.
- **T5**(AC-GROUP-005): 단일 노트 주문 2개. 각 그룹 컨테이너 **안에서** 주문번호 컨트롤을 찾아 클릭 — mock된 `useNavigate`
  (또는 `MemoryRouter` + 라우트 렌더링으로 실제 이동 확인, `OrderDetailPage.test.tsx`처럼 `react-router-dom`을 부분
  모킹하거나 `MemoryRouter`의 현재 경로를 확인하는 방식 중 하나를 택한다) 호출 인자/이동 경로가 각 노트의 `order_id`와
  일치하는지 확인. **이 클릭·이동 확인만으로는 "그룹이 `tabNotes` 전체를 순회하는" 버그를 잡지 못한다** —
  `NoteCard`가 무수정이라 노트별 텍스트/내비게이션 배선이 항상 정확하기 때문이다(정정된 `spec.md` AC-GROUP-005
  참조). 따라서 **각 그룹 컨테이너 안에서 해결 버튼이 아닌 버튼(주문번호 컨트롤)의 개수가 정확히 1개인지도 함께
  확인한다** — 이 개수 대조가 이 AC의 실제 판별 수단이다. 조회 방식은 AC-GROUP-001의 해결 컨트롤 개수 대조와
  동일한 원리(라벨 텍스트 매칭이 아니라 제외법 개수 세기)로 통일한다.
- **T6**(AC-GROUP-006): 한 주문에 노트 2건. `useResolveLineItemNote`의 `mutate`를 스파이로 모킹하고, 첫 노트의 해결 버튼
  클릭 후 캐시 갱신을 재현(모킹된 훅이 상태를 관리하거나, `useUnresolvedLineItemNotes`의 모킹 반환값을 리렌더 사이에
  바꾸는 방식으로 재현) — 그룹 컨테이너가 남아 있고 두 번째 노트만 남았는지 확인. 두 번째(마지막) 노트도 해결한 뒤 그
  그룹 컨테이너가 문서에서 완전히 사라졌는지 확인.
- **T7**(AC-GROUP-007): CS 탭에 노트 2건(그룹 1개, **서로 다른 `line_item_id`** — 같으면 `filterNotes`의 LineItem당
  최신 1건 집계에 걸려 1건짜리 그룹이 되어 아래 단정이 성립하지 않는다), 발주 탭에는 노트 0건이 되도록 구성. CS 탭이
  활성일 때 그룹 컨테이너가 정확히 노트 2건을 포함하는지 확인 후, 발주 탭으로 전환해 기존 빈 상태 메시지(`:396`의
  "미해결 품목 메모가 없습니다.")가 보이고 그룹 컨테이너가 전혀 없는지 확인.
- **T8**(AC-GROUP-008): 한 주문에 노트 2건 — 하나는 활성 탭의 담당자, 다른 하나는 다른 담당자. 활성 탭의 그룹이 정확히
  1건만 포함하는지(건수 1, DOM에 다른 담당자 노트의 콘텐츠 없음) 확인.
- **T9**(AC-GROUP-009): 단일 노트 주문 2개, `created_at`이 **동일**하고 `id`만 다르며, **`id` 순서가 `order_id`/
  `line_item_id` 순서와 반대**가 되도록 배치한다(더 높은 `id`를 가진 노트가 더 낮은 `order_id`/`line_item_id`를
  갖는다) — `order_id desc`나 `line_item_id desc`로 동률을 처리하는 오구현도 이 픽스처에서 걸리도록 하기 위함이다
  (REQ-GROUP-005가 명시한 키는 `id`뿐이다). 모킹 배열의 도착 순서도 기대 결과와 어긋나게 구성한다. 렌더된 그룹
  헤더의 DOM 순서가 `id` 내림차순인지 확인 — 동률 처리 없이 안정 정렬에만 의존하는 구현, `order_id`/`line_item_id`로
  동률을 처리하는 구현 양쪽 다 이 단정에서 걸린다.
- **T10**(AC-GROUP-010): 한 주문 안에 서로 다른 품목의 노트 2건, `created_at`이 **동일**하고 `id`만 다르며, **더 높은
  `id`를 가진 노트가 더 낮은 `line_item_id`를 갖도록** 배치한다(`line_item_id desc` tie-break 오구현도 잡기 위함).
  도착 순서는 낮은 `id`가 먼저. 그룹 안에서 높은 `id`의 노트가 위에 렌더링되는지 확인 — 도착 순서 유지형 오구현과
  `line_item_id desc` tie-break형 오구현 둘 다 이 단정에서 걸린다.

**공통 렌더 헬퍼**: `OrderDetailPage.test.tsx:20-33`의 `renderPage()` 패턴 — `QueryClient({ defaultOptions: { queries: {
retry: false } } })` + `QueryClientProvider` + `MemoryRouter`. 라우트는 `/line-item-notes` 단일 경로로 충분하다(주문
상세로의 내비게이션은 T5에서 이동 목적지만 확인하면 되므로 대상 라우트를 실제로 마운트할 필요는 없다).

---

## 리스크 분석 및 완화책

| ID | 리스크 | 완화책 |
|---|---|---|
| R1 | 그룹 컨테이너가 `NoteCard` 내부의 기존 클릭 핸들러(펼침/접힘 토글 `:236-237`, 주문번호 버튼의 `stopPropagation` `:241`)와 이벤트가 충돌해 클릭을 가로챈다 | 그룹 컨테이너 자체에는 클릭 핸들러를 두지 않는다(`spec.md` 명시적 가정 6) — 정보 표시 전용이므로 이벤트 버블링 경로에 새 핸들러가 끼어들 여지가 없다. |
| R2 | `countByTab`이 `filterNotes(...).length` 대신 그룹 수를 세도록 구현된다 | T4(AC-GROUP-004)가 노트 총합과 탭 라벨 카운트를 함께 단정해 판별한다. |
| R3 | 그룹·그룹 내부 정렬을 만들지 않고 원본 배열 순서(도착 순서)에 의존한다 | T2/T3(AC-GROUP-002/003)가 도착 순서와 기대 순서를 의도적으로 어긋나게 설계해 판별한다. |
| R4 | 마지막 노트를 해결한 뒤에도 빈 그룹 껍데기가 DOM에 남는다 | T6(AC-GROUP-006)이 그룹 컨테이너의 완전한 부재를 단정한다. |
| R5 | 이 페이지의 첫 테스트 파일이라 모킹 관례가 이번에 새로 확립된다 — `vi.mock` 팩토리가 모듈 전체를 대체한다는 사실(D3, 파일별 변경 계획의 `LineItemNotesPage.test.tsx` 행 참조)을 오해하면 팩토리가 누락한 export에 접근하는 다른 시나리오를 추가할 때 예외가 난다 | `OrderDetailPage.test.tsx`의 기존 관례를 그대로 따르고(M1 상단 "공통 렌더 헬퍼" 참조), 팩토리가 어떤 export를 생략해도 되는지는 "그 경로에 어떤 시나리오도 닿지 않기 때문"이라는 조건과 함께 명시한다(파일별 변경 계획 참조) — 이후 카드 펼침·엑셀 내보내기 시나리오를 추가하는 사람이 팩토리를 확장해야 함을 알 수 있게 한다. |
| R6 | 탭 필터 적용 **이전**(raw `data`)에 `order_id`로 묶어버리면 다른 담당자의 노트가 그룹 건수에 섞인다 | T8(AC-GROUP-008)이 이를 판별한다 — 그룹화는 반드시 `tabNotes`(필터 이후)에 적용해야 한다(REQ-GROUP-002). |
| R7 | `created_at`만으로 정렬해 동률(같은 타임스탬프) 노트의 순서가 비결정적이 된다 — `LineItemNoteUnresolvedListView.get_queryset()`(`views.py:277-282`)이 `-created_at` 단일 키로만 정렬해(`:281`) 동률 행의 DB 반환 순서가 애초에 비결정적이고, SPEC-ORDER-019가 도입한 Daily Review 일괄 노트 생성(`bulk_create`)도 동일 `created_at`이 발생할 수 있는 경로다. SPEC-ORDER-018 v1.0.3 D1이 `"pk"` tie-break 부재로 이미 같은 계열의 결함을 겪었다 | REQ-GROUP-005/006에 `id` 내림차순 2차 키를 명시했고, T9/T10(AC-GROUP-009/010)이 도착 순서를 기대값과 반대로 배치**하고 `id` 순서를 `order_id`/`line_item_id` 순서와도 반대로 배치**해 동률 처리 누락뿐 아니라 `order_id`/`line_item_id` 기준의 오구현(REQ가 명시한 키가 아님)도 판별한다. |
| R8 | AC-GROUP-005가 스스로 명시한 mutation(그룹이 `tabNotes` 전체를 순회)을 클릭·내비게이션 단정만으로는 잡지 못한다 — `NoteCard`가 무수정이라 텍스트 기반 조회는 여전히 정확한 노트를 찾아 정상 이동하기 때문이다 | T5에 그룹 스코프 안 "해결이 아닌 버튼" 개수 대조를 추가했다(AC-GROUP-005 (b)) — 클릭·이동 확인(a)은 회귀 방지용으로 유지하되 이 mutation의 판별은 (b)가 전담한다. |

---

## MX 태그 계획 (mx_plan)

| 태그 | 위치 | 내용 |
|---|---|---|
| `@MX:NOTE` (신규) | 그룹화 로직 정의부 인근 (`LineItemNotesPage.tsx`, `filterNotes` 아래 신규 코드) | 그룹화는 `filterNotes`(`:35-49`)의 출력(`tabNotes`)에만 적용되며, 그룹 정렬은 그룹 내 최신 `note.created_at` 기준 내림차순 + `id` 내림차순 동률 처리라는 사실 — `LineItemNoteUnresolvedListView.get_queryset()`(`backend/order/views.py:277-282`)이 `-created_at` 단일 키로만 정렬해 동률 행의 순서가 애초에 비결정적이라는 근거와, SPEC-ORDER-019의 일괄 노트 생성이 동일 `created_at`을 만들 수 있다는 근거(REQ-GROUP-005/006)를 함께 포함. `countByTab`(`:344`)이 `filterNotes(...).length`를 그대로 쓰므로 그룹 수와 노트 수를 혼동하면 안 된다는 경고도 포함. |
| `@MX:NOTE` (신규) | `filterNotes` 함수(`:35`) 정의부 인근 | 이 함수의 출력이 이제 그룹화 로직의 입력이 된다는 컨텍스트. `filterNotes` 자체의 동작(타출판사 필터, LineItem당 최신 1건 집계)은 이 SPEC과 무관하게 무수정임을 명시. |
| 검토 후 무변경 | `LineItemNotesPage.tsx:304-305`의 `@MX:ANCHOR` | fan-in 사유(router, Sidebar, `useUnresolvedLineItemNotes` 훅)는 그룹화와 무관 — 갱신 불필요. |
| 검토 후 무변경 | `useLineItemNotes.ts:33-34`의 `@MX:WARN` (`useResolveLineItemNote`) | 낙관적 캐시 제거 로직은 무수정. 그룹은 이 훅이 갱신하는 flat 데이터의 렌더 시점 파생물이므로, 노트가 캐시에서 제거되면 그룹도 자동으로 갱신된다는 것이 REQ-GROUP-010/011이 성립하는 근거 — 이 사실을 신규 `@MX:NOTE`(위 항목)에서 교차 참조한다. |

`code_comments: en` 설정(`.moai/config/sections/language.yaml`)에 따라 모든 태그 본문은 **영어**로 작성한다.

---

## 완료 조건 (Definition of Ready → Done 게이트)

**Ready (구현 시작 전)**

- [ ] M0 확인 — `LineItemNotesPage.tsx` 전체와 `OrderDetailPage.test.tsx`의 모킹·렌더 헬퍼 관례를 재확인했다
- [ ] 기존 프론트엔드 테스트 스위트의 현재 통과 상태를 기록했다

**Done (구현)**

- [ ] `LineItemNotesPage.test.tsx` T1~T10 전량 통과
- [ ] T1~T6, T8~T10이 그룹 컨테이너가 없는(되돌린) 상태에서 **실패함**을 확인했다(T6의 1차 단정은 `NoteCard` 무수정
      설계에서 그룹 컨테이너 부재로 자연히 실패하며, 별도의 mutation 주입은 2차 단정의 "빈 그룹 잔존" 케이스에만
      적용한다 — `acceptance.md` AC-GROUP-006 판별력 주석 참조)
- [ ] T7의 "그룹이 있는 절"이 되돌린 상태에서 **실패함**을 확인했다(`acceptance.md` AC-GROUP-007 판별력 주석 참조)
- [ ] T9/T10이 `created_at` 동률 처리를 생략한(2차 키 없는) 구현에서 **실패함**을, 그리고 `order_id`/`line_item_id`
      내림차순으로 동률을 처리하는(`id`가 아닌) 구현에서도 **실패함**을 각각 mutation으로 확인했다
- [ ] T5가 "그룹이 `tabNotes` 전체를 순회" mutation에서 (b) 컨트롤 개수 대조로 **실패함**을 확인했다 — 클릭·이동
      단정 (a)만으로는 이 mutation이 통과해 버림을 재확인했다
- [ ] T1의 페이지 스코프 해결 컨트롤 총합 대조가 그룹 밖 벌크 컨트롤 mutation에서 **실패함**을 확인했다
- [ ] `git diff`에 `filterNotes`(`:35-49`) 변경이 **없다**
- [ ] `git diff`에 `NoteCard`/`NoteHistory`/`InlineNoteForm`(`:54-302`) 변경이 **없다**
- [ ] `git diff`에 `countByTab`(`:344`) 변경이 **없다**
- [ ] `git diff --stat backend/`가 **비어 있다** (REQ-GROUP-014)
- [ ] `git diff --stat frontend/src/features/order/hooks/useLineItemNotes.ts`가 **비어 있다**
- [ ] `git diff --stat frontend/src/types/order.ts`가 **비어 있다**
- [ ] 기존 프론트엔드 테스트 스위트(`OrderDetailPage.test.tsx`, `DashboardPage.test.tsx`, `ForbiddenPage.test.tsx`) 전량 무수정 통과
- [ ] ESLint/TypeScript 신규 에러 0 (기존 베이스라인 대비)

**Done (문서)**

- [ ] `spec.md`/`plan.md`/`acceptance.md`/`spec-compact.md`의 `status`가 갱신되었다
- [ ] 구현 중 발견한 계획 대비 발산이 `spec.md` HISTORY에 기록되었다

**REQ → 검증 수단 매핑**

| REQ | 검증 |
|---|---|
| 001, 003, 004, 013 | T1 |
| 002 | T1, T8 |
| 005 | T2, T9 |
| 006 | T3, T10 |
| 007 | T4 |
| 008 | T8 |
| 009 | T5, T6 |
| 010, 011 | T6 |
| 012 | T7 |
| 014 | `git diff --stat backend/` 게이트 |

---

## 관련 참조 구현

- **그룹화 입력**: `LineItemNotesPage.tsx:313`(`tabNotes`), `filterNotes` 정의 `:35-49`
- **그룹 헤더 폴백 규칙 선례**: `NoteCard:244`(`note.order_name ?? \`주문 #${note.order_id}\``)
- **기존 내비게이션 선례**: `NoteCard:240-245`(`navigate(\`/orders/${note.order_id}\`)`, `stopPropagation` `:241`)
- **탭 카운트 배지**: `:343-344`(`tabs`, `countByTab`)
- **평면 렌더링(교체 대상)**: `:400-411`
- **낙관적 해결 캐시 갱신**: `useLineItemNotes.ts:35-59`, 특히 `onMutate` `:41-47`
- **데이터 출처**: `backend/order/views.py:269-282`, `backend/order/serializers.py:79-97`(특히 `order_id` `:86`, `order_name` `:85`)
- **정렬 동률 키 `id`의 타입 출처**: `frontend/src/types/order.ts:93-101`(`LineItemNote.id: number`, `LineItemNoteUnresolved`가 상속)
- **동률의 확정적 근거**: `LineItemNoteUnresolvedListView.get_queryset()`(`backend/order/views.py:277-282`) — `order_by("-created_at")`(`:281`) 단일 키, 2차 키 없음. 동률 행의 DB 반환 순서가 애초에 비결정적임을 직접 증명한다
- **동률의 개연적 근거**: SPEC-ORDER-019의 Daily Review 업로드 배치 노트 생성(`backend/order/purchase_order_views.py`의 `bulk_create` 경로, 그 SPEC `plan.md` "기술적 접근" 참조) — 같은 요청 안의 여러 `LineItemNote`가 동일한 `created_at`을 가질 수 있는 경로(`models.py:272`의 `auto_now_add=True`, 체계적이지는 않음)
- **테스트 관례 원본**: `frontend/src/pages/OrderDetailPage.test.tsx:1-33`(모킹·렌더 헬퍼), `:35-95`(픽스처 빌더 패턴)
