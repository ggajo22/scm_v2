---
id: SPEC-ORDER-020
document: acceptance
version: 1.0.2
status: draft
updated: 2026-08-13
---

# 인수 기준 — SPEC-ORDER-020 미해결 품목 메모 주문번호 그룹화

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의 AC-GROUP-XXX / REQ-GROUP-XXX ID를 인용해
상호 추적된다.

[HARD] 각 시나리오의 `Traces:` 목록은 `spec.md` ACCEPTANCE CRITERIA 절의 동일 AC 항목이 선언한 것과 완전히 일치한다. 어느
한쪽을 수정할 때 반드시 함께 갱신한다.

[HARD] **판별력 요건.** 이 SPEC의 핵심 산출물은 "그룹 컨테이너"라는 새로운 DOM 구조 자체이므로, 아래 시나리오 대부분은
조회를 그룹 컨테이너를 **통해서**(`within(그룹 컨테이너)` 패턴) 수행한다 — 그룹이 아직 없는 현재(미구현) 코드에서는 그
조회 자체가 대상을 찾지 못해 실패하므로, 별도의 mutation 없이도 "구현을 되돌리면 실패한다"가 성립한다. 두 가지 명시적
예외가 있다 — (1) AC-GROUP-007의 빈 상태 절(그룹이 원천적으로 존재하지 않는 경우를 다루므로), (2) AC-GROUP-006의 첫
번째 단정(형제 노트가 살아남는다는 것은 `NoteCard` 무수정 설계에서 자동으로 성립하므로 독립적인 mutation이 없다). 두
경우 모두 판별력 한계를 해당 절에 명시했다. 이 프로젝트는 판별력 없는 인수 기준으로 이미 두 번 손해를 봤다
(SPEC-ORDER-018 v1.0.3/v1.0.4).

**검증 레이어**: 전량 `[FE]` — `frontend/src/pages/LineItemNotesPage.test.tsx`의 vitest + React Testing Library
시나리오다. 이 SPEC은 백엔드를 변경하지 않으므로(`spec.md` REQ-GROUP-014) `[BE]` 시나리오가 없다.

**공통 렌더 헬퍼**: `frontend/src/pages/OrderDetailPage.test.tsx:20-33`의 `renderPage()` 패턴을 복제한다 —
`QueryClient({ defaultOptions: { queries: { retry: false } } })` + `QueryClientProvider` + `MemoryRouter`. 훅은
`vi.mock('@/features/order/hooks/useLineItemNotes', ...)`으로 `useUnresolvedLineItemNotes`와 `useResolveLineItemNote`를
모킹한다(`OrderDetailPage.test.tsx:15-18` 관례).

**노트 픽스처 표기**: 아래 시나리오는 `LineItemNoteUnresolved`(`frontend/src/types/order.ts:103-110`) 형태의 객체를
`{id, order_id, order_name, line_item_id, assignee, note_type, content, created_at, is_resolved}` 필드로 표기한다. 각 시나리오
본문에서 값을 명시하지 않은 노트는 다음 안전 기본값을 쓴다 — **`note_type: ""`**(빈 문자열 — `"타출판사"`를 주면
`filterNotes`가 CS/발주 탭 집계에서 그 노트를 제외하므로(`LineItemNotesPage.tsx:41`) 픽스처가 조용히 깨진다. 이 필드는
임의 값을 허용하지 않는다), **`is_resolved: false`**(미해결 목록에 나타나야 하므로). `author_username`, `line_item_sku`,
`line_item_title`, `confirmed_distributor`만 임의 값 또는 `null`로 채운다. `created_at`은 정렬을 다루지 않는 시나리오에서도
값을 생략하지 않는다 — 서로 다른 값을 명시적으로 부여해 픽스처를 일관되게 유지한다.

---

## 그룹 구성

### AC-GROUP-001 — 같은 주문의 노트가 하나의 그룹 컨테이너로 묶인다 `[FE]`

Traces: REQ-GROUP-001, REQ-GROUP-002, REQ-GROUP-003, REQ-GROUP-004, REQ-GROUP-013

- **Given**: `useUnresolvedLineItemNotes`가 다음 노트 3건을 반환하도록 모킹한다 — 전부 `assignee: "CS"`, `is_resolved: false`.
  - `{id: 1, order_id: 801, order_name: "#D801", line_item_id: 9201, content: "첫 메모", created_at: "2026-08-12T10:00:00Z"}`
  - `{id: 2, order_id: 801, order_name: "#D801", line_item_id: 9202, content: "둘째 메모", created_at: "2026-08-12T11:00:00Z"}`
  - `{id: 3, order_id: 802, order_name: "#D802", line_item_id: 9203, content: "단일 메모", created_at: "2026-08-11T09:00:00Z"}`
  - (order_id 801에 2건, order_id 802에 1건 — line_item_id가 모두 달라 `filterNotes`의 Map 집계가 아무것도 접지 않는다)
- **When**: 페이지를 CS 탭(기본 활성 탭)으로 렌더링한다. 그룹801을 조회할 때 쓰는 것과 **동일한 단일 조회
  헬퍼**(`order_id`만 인자로 받는 형태 — 예: `getGroupContainer(orderId)`)로 그룹802도 조회한다. 그룹마다 특화된
  별도 셀렉터를 쓰지 않는다.
- **Then**:
  - (a) order_id 801의 그룹 컨테이너 **안에서** "첫 메모"와 "둘째 메모"가 모두 발견된다(`within(그룹801)` 조회) — 페이지
    전체에서가 아니라 그 컨테이너 스코프 안에서다.
  - (b) 그룹801의 헤더에 "#D801"과 노트 건수 "2"가 표시된다.
  - (c) 그룹802를 802용 인자만 바꾼 **동일한 조회 헬퍼**로 찾았을 때 컨테이너가 발견된다 — 그룹801에만 있는 특수
    처리(예: "노트가 2건 이상일 때만 wrapper를 씌운다") 때문에 헬퍼가 그룹801에서만 통하고 그룹802에서는 통하지
    않는 구현은 이 단정에서 실패한다. 그 컨테이너의 헤더에 "#D802"와 건수 "1"이 표시된다.
  - (d) 그룹801 스코프 안의 해결 관련 컨트롤(접근 가능한 이름에 "해결"을 포함하는 버튼) 개수가 정확히 그 그룹의 노트
    개수와 같다 — **2개**(노트당 1개씩). 그룹802 스코프 안의 해결 컨트롤 개수는 **1개**다. 이 개수 대조는 특정
    라벨("전체 해결" 등)의 부재를 확인하는 것이 아니라 컨트롤 총수를 노트 수와 직접 비교하므로, 다른 이름의 벌크
    컨트롤(예: "일괄 해결", "선택 해결", 아이콘 전용 버튼)도 개수 불일치로 잡아낸다.
  - (e) **페이지 전체**(어느 한 그룹 스코프가 아니라 렌더링된 문서 전체)에서 해결 관련 컨트롤(접근 가능한 이름에
    "해결"을 포함하는 버튼)의 총 개수가 이 탭의 전체 노트 개수(**3**)와 정확히 같다. 이 단정은 (d)와 달리 그룹
    컨테이너 스코프로 조회를 좁히지 않는다 — 그룹 밖(툴바·페이지 헤더 등)에 별도의 벌크 해결 컨트롤이 있어도
    (d)의 그룹별 개수는 여전히 2/1로 정상처럼 보일 수 있으므로, 이 페이지 스코프 단정이 그 경우를 별도로 잡는다.
- **판별력**: 현재(그룹 없는 평면 렌더링) 코드에서 (a)의 `within(그룹801)` 조회는 그룹801 컨테이너 자체를 찾지 못해
  실패한다 — 구현을 되돌리면 반드시 실패한다. 그룹 레벨 벌크 해결 버튼을 추가하면 (d)의 개수 대조가 실패한다(그룹801의
  해결 컨트롤이 2가 아니라 3이 된다) — 어떤 라벨을 쓰든 개수가 늘어나므로 라벨 문구에 의존하지 않는다. 그룹 밖(툴바
  등)에 벌크 해결 버튼을 추가하면 (d)는 통과해도 (e)의 페이지 전체 총합이 3이 아니라 4가 되어 실패한다. 노트
  1건짜리 주문을 그룹 컨테이너 없이 맨 행으로 렌더링하면 (c)의 동일 헬퍼 조회가 실패한다.

## 그룹·그룹 내부 정렬

### AC-GROUP-002 — 그룹은 그룹 내 최신 노트 기준 내림차순으로 배치된다 `[FE]`

Traces: REQ-GROUP-005

- **Given**: 단일 노트 주문 3개, `assignee: "발주"`, 서로 다른 `line_item_id`. **모킹 배열의 도착 순서를 시간 순서와
  일부러 어긋나게 구성**한다 — 배열 순서: [오래된 것, 가장 최신, 중간].
  - 배열[0] `{id: 11, order_id: 601, order_name: "#B601", line_item_id: 9301, created_at: "2026-08-10T09:00:00Z"}` (가장 오래됨)
  - 배열[1] `{id: 12, order_id: 602, order_name: "#B602", line_item_id: 9302, created_at: "2026-08-12T09:00:00Z"}` (가장 최신)
  - 배열[2] `{id: 13, order_id: 603, order_name: "#B603", line_item_id: 9303, created_at: "2026-08-11T09:00:00Z"}` (중간)
- **When**: 발주 탭을 활성화해 렌더링한다.
- **Then**: 렌더된 그룹 헤더들의 DOM 순서(위에서 아래)가 "#B602"(최신) → "#B603"(중간) → "#B601"(가장 오래됨)이다 — 즉
  모킹 배열의 도착 순서([601, 602, 603])와 다르다.
- **판별력**: 그룹화를 만들되 정렬 단계를 생략하고 도착 순서(또는 `filterNotes`가 만드는 Map 삽입 순서 — 이 시나리오에서는
  도착 순서와 동일하다)를 그대로 쓰면 렌더 순서가 [#B601, #B602, #B603]이 되어 기대값과 어긋나 실패한다. 구현을
  되돌리면 그룹 헤더 자체가 존재하지 않으므로 DOM 순서를 비교할 대상이 없어 실패한다.

### AC-GROUP-003 — 그룹 내부는 최신 노트가 위에 온다 `[FE]`

Traces: REQ-GROUP-006

- **Given**: 한 주문(order_id 701, order_name "#C701") 안에 서로 다른 품목의 노트 2건, `assignee: "발주"`. 배열 순서는
  오래된 것이 먼저.
  - 배열[0] `{id: 21, order_id: 701, order_name: "#C701", line_item_id: 9101, content: "먼저 남긴 메모", created_at: "2026-08-10T09:00:00Z"}`
  - 배열[1] `{id: 22, order_id: 701, order_name: "#C701", line_item_id: 9102, content: "나중에 남긴 메모", created_at: "2026-08-11T09:00:00Z"}`
- **When**: 발주 탭을 활성화해 렌더링한다.
- **Then**: 그룹701 컨테이너 **안에서** "나중에 남긴 메모"가 "먼저 남긴 메모"보다 DOM 상 앞선다(위에 렌더링된다).
- **판별력**: 그룹 안에서 배열 도착 순서를 그대로 렌더링하면(정렬하지 않으면) "먼저 남긴 메모"가 위에 오게 되어
  실패한다. 구현을 되돌리면 그룹701 컨테이너 자체가 없어 조회가 실패한다.

### AC-GROUP-009 — 그룹 정렬의 `created_at` 동률은 `id` 내림차순으로 깨진다 `[FE]`

Traces: REQ-GROUP-005

- **Given**: 단일 노트 주문 2개, `assignee: "발주"`, 서로 다른 `line_item_id`, **동일한 `created_at`**이지만 `id`는
  다르다. SPEC-ORDER-019가 도입한 Daily Review 일괄 노트 생성(`bulk_create`)에서 같은 배치의 노트들이 동일한
  타임스탬프를 가질 수 있는 상황을 재현한다. **`id` 순서를 `order_id`/`line_item_id` 순서와 일부러 반대로
  배치**한다 — 더 높은 `id`를 갖는 노트가 더 **낮은** `order_id`/`line_item_id`를 갖도록 해서, `id` 대신
  `order_id desc`나 `line_item_id desc`로 동률을 처리하는 구현도 걸리게 한다. 모킹 배열의 도착 순서도 기대하는
  정렬 결과와 어긋나게 구성한다.
  - 배열[0] `{id: 91, order_id: 1602, order_name: "#L1602", line_item_id: 9902, created_at: "2026-08-12T09:00:00Z"}` (낮은 id, 높은 order_id/line_item_id)
  - 배열[1] `{id: 92, order_id: 1601, order_name: "#L1601", line_item_id: 9901, created_at: "2026-08-12T09:00:00Z"}` (동일 시각, 높은 id, 낮은 order_id/line_item_id)
- **When**: 발주 탭을 활성화해 렌더링한다.
- **Then**: 렌더된 그룹 헤더들의 DOM 순서(위에서 아래)가 "#L1601"(id=92, 더 높은 id) → "#L1602"(id=91, 더 낮은
  id)이다 — 모킹 배열의 도착 순서([#L1602, #L1601])와도 반대이고, `order_id`나 `line_item_id`를 내림차순으로 쓴
  결과("#L1602"가 먼저, `order_id`/`line_item_id` 모두 1602/9902 쪽이 더 크므로)와도 반대다.
- **판별력**: `created_at`만으로 정렬하고 동률 처리(2차 키)를 두지 않으면, 두 그룹의 정렬 키가 동일하므로 안정
  정렬(stable sort)은 도착 순서 [#L1602, #L1601]를 그대로 유지해 실패한다. `id` 대신 `order_id` 내림차순이나
  `line_item_id` 내림차순으로 동률을 처리하는 구현도 "#L1602"(더 큰 `order_id`/`line_item_id`)를 먼저 렌더링해
  실패한다 — 오직 REQ-GROUP-005가 명시한 `id` 내림차순 구현만 "#L1601"을 먼저 렌더링해 통과한다. 구현을 되돌리면
  그룹 헤더 자체가 존재하지 않아 실패한다.

### AC-GROUP-010 — 그룹 내부 정렬의 `created_at` 동률은 `id` 내림차순으로 깨진다 `[FE]`

Traces: REQ-GROUP-006

- **Given**: 한 주문(order_id 1701, order_name "#M1701") 안에 서로 다른 품목의 노트 2건, `assignee: "발주"`, **동일한
  `created_at`**이지만 `id`는 다르다. **더 높은 `id`를 갖는 노트가 더 낮은 `line_item_id`를 갖도록** 배치해서,
  `id` 대신 `line_item_id desc`로 동률을 처리하는 구현도 걸리게 한다. 배열 순서는 낮은 id가 먼저.
  - 배열[0] `{id: 101, order_id: 1701, order_name: "#M1701", line_item_id: 10002, content: "메모 A", created_at: "2026-08-12T09:00:00Z"}` (낮은 id, 높은 line_item_id)
  - 배열[1] `{id: 102, order_id: 1701, order_name: "#M1701", line_item_id: 10001, content: "메모 B", created_at: "2026-08-12T09:00:00Z"}` (동일 시각, 높은 id, 낮은 line_item_id)
- **When**: 발주 탭을 활성화해 렌더링한다.
- **Then**: 그룹1701 컨테이너 **안에서** "메모 B"(id=102, 높은 id, `line_item_id` 10001로 더 낮음)가 "메모 A"(id=101,
  낮은 id, `line_item_id` 10002로 더 높음)보다 DOM 상 앞선다(위에 렌더링된다) — 배열 도착 순서와도 반대이고,
  `line_item_id`를 내림차순으로 쓴 결과("메모 A"가 먼저, `line_item_id` 10002가 더 크므로)와도 반대다.
- **판별력**: `created_at`만으로 정렬하고 동률 처리를 두지 않으면 안정 정렬이 도착 순서("메모 A"가 위)를 그대로
  유지해 실패한다. `id` 대신 `line_item_id` 내림차순으로 동률을 처리하는 구현도 "메모 A"(더 큰 `line_item_id`
  10002)를 먼저 렌더링해 실패한다 — 오직 REQ-GROUP-006이 명시한 `id` 내림차순 구현만 "메모 B"를 먼저 렌더링해
  통과한다. 구현을 되돌리면 그룹1701 컨테이너 자체가 없어 조회가 실패한다.

## 탭 스코프·건수 보존

### AC-GROUP-004 — 탭 카운트는 그룹 수가 아니라 노트 수를 반영한다 `[FE]`

Traces: REQ-GROUP-007

- **Given**: CS 탭에 노트 4건, 전부 `assignee: "CS"`, 서로 다른 `line_item_id`.
  - `{id: 61, order_id: 901, order_name: "#E901", line_item_id: 9401, created_at: "2026-08-12T09:00:00Z"}`
  - `{id: 62, order_id: 901, order_name: "#E901", line_item_id: 9402, created_at: "2026-08-12T10:00:00Z"}`
  - `{id: 63, order_id: 902, order_name: "#E902", line_item_id: 9403, created_at: "2026-08-11T09:00:00Z"}`
  - `{id: 64, order_id: 902, order_name: "#E902", line_item_id: 9404, created_at: "2026-08-11T10:00:00Z"}`
  - (order_id 901에 2건, order_id 902에 2건 — 이 시나리오는 그룹 순서를 단정하지 않으므로 `created_at` 값 자체는
    임의로 달라도 무방하지만, 픽스처 일관성을 위해 서로 다른 값을 명시한다.)
- **When**: CS 탭을 활성화해 렌더링한다.
- **Then**:
  - (a) 두 그룹 컨테이너(901, 902) 안에 렌더된 개별 노트 행의 총합이 정확히 **4**다(그룹별 2건씩).
  - (b) CS 탭 라벨의 카운트 배지가 **"(4)"** 다 — 그룹 수인 "(2)"가 아니다.
- **판별력**: `countByTab`을 `filterNotes(...).length` 대신 그룹 배열의 길이(`Object.keys(grouped).length` 등)로
  계산하면 (b)가 "(2)"로 나와 실패한다. 구현을 되돌리면 그룹 컨테이너 자체가 없어 (a)의 합산 대상을 찾지 못해 실패한다.

### AC-GROUP-008 — 그룹은 활성 탭의 노트만 포함한다(다른 담당자 노트를 끌어오지 않는다) `[FE]`

Traces: REQ-GROUP-002, REQ-GROUP-008

- **Given**: 한 주문(order_id 1001, order_name "#F1001")에 노트 2건 — 서로 다른 담당자.
  - `{id: 31, order_id: 1001, order_name: "#F1001", line_item_id: 9501, assignee: "CS", content: "CS 노트", created_at: "2026-08-12T09:00:00Z"}`
  - `{id: 32, order_id: 1001, order_name: "#F1001", line_item_id: 9502, assignee: "발주", content: "발주 노트", created_at: "2026-08-12T10:00:00Z"}`
- **When**: CS 탭을 활성화해 렌더링한다.
- **Then**: order_id 1001의 그룹 컨테이너가 정확히 **1건**의 노트만 포함하며(건수 표시 "1"), 그 안의 콘텐츠는 "CS 노트"뿐
  이다 — "발주 노트"는 CS 탭의 어느 그룹에도 나타나지 않는다.
- **판별력**: `filterNotes`가 적용되기 **전**의 원본 목록을 `order_id`로 먼저 묶고 그 다음에 탭 필터를 적용하면(순서가
  뒤바뀌면) 그룹1001의 건수가 2가 되고 "발주 노트"도 그룹 안에 나타나 실패한다. 구현을 되돌리면 그룹 컨테이너 자체가
  없어 건수를 조회할 대상이 없어 실패한다.

## 상호작용 불변

### AC-GROUP-005 — 그룹 안에서도 주문 상세 내비게이션이 각 노트의 주문으로 정확히 이동한다 `[FE]`

Traces: REQ-GROUP-009

- **Given**: 단일 노트 주문 2개, `assignee: "발주"`, 서로 다른 `line_item_id`.
  - `{id: 41, order_id: 1101, order_name: "#G1101", line_item_id: 9601, created_at: "2026-08-12T09:00:00Z"}`
  - `{id: 42, order_id: 1102, order_name: "#G1102", line_item_id: 9602, created_at: "2026-08-12T10:00:00Z"}`
- **When**: 발주 탭을 활성화해 렌더링한 뒤, 그룹1102 컨테이너 **안에서** 주문번호 컨트롤("#G1102")을 클릭하고, 이어서
  그룹1101 컨테이너 **안에서** 주문번호 컨트롤("#G1101")을 클릭한다.
- **Then**:
  - (a) 첫 클릭은 `/orders/1102`로의 이동을 유발하고, 두 번째 클릭은 `/orders/1101`로의 이동을 유발한다 — 각각
    클릭한 컨트롤이 속한 그룹의 `order_id`와 정확히 일치한다.
  - (b) 그룹1101 컨테이너 **안에서** 해결 버튼(접근 가능한 이름에 "해결"을 포함)이 **아닌** 버튼의 개수가 정확히
    **1개**다(주문번호 컨트롤 1개). 그룹1102 컨테이너 안에서도 동일하게 정확히 **1개**다. 이 조회는 AC-GROUP-001
    (d)와 같은 방식 — 특정 주문번호 텍스트와 매칭하는 것이 아니라 "해결"이 아닌 버튼의 **개수**를 세는 방식이며,
    구속력 있게 이 방식으로 고정한다(테스트 작성자가 다른 조회 방식을 임의로 선택하지 않는다).
- **판별력**: (b)가 이 AC 자신의 판별력 근거다 — 그룹화 로직이 각 그룹 자신의 노트 배열이 아니라 `tabNotes` 전체(또는
  이웃 그룹의 배열)를 순회하도록 구현하면, 그룹1102 컨테이너 안에 그룹1101의 노트까지 함께 렌더링되어 "해결이 아닌
  버튼" 개수가 1이 아니라 2가 되므로 (b)가 실패한다. **(a)만으로는 이 mutation을 잡지 못한다** — `NoteCard`가
  무수정이므로(`spec.md` 명시적 가정 6) 각 노트 행은 여전히 자신의 `note` prop에서 `order_id`를 읽어
  `navigate(\`/orders/${note.order_id}\`)`(`NoteCard:241`)를 정확히 호출하고, `NoteCard:244`가 노트마다 고유한
  주문번호 텍스트("#G1102" 등)를 그리므로 텍스트로 컨트롤을 찾는 조회는 그룹1102가 그룹1101의 노트까지 잘못
  포함해도 여전히 정확히 1개만 찾아 클릭이 정상적으로 `/orders/1102`로 이동한다 — 즉 (a)는 이 특정 mutation에
  대해서는 판별력이 없고, 정상적인 내비게이션 배선이 유지된다는 별개의 회귀 방지 용도로만 남는다. (참고: 이
  mutation은 AC-GROUP-001 (d)(그룹801의 해결 컨트롤 개수가 3이 됨)와 AC-GROUP-004 (a)(총 노트 행 합계가 8이 됨)에서도
  부수적으로 잡히지만, 그것은 다른 AC의 효과이지 이 AC 자신의 판별력이 아니었다 — (b)를 추가해 이 AC 스스로
  판별력을 갖도록 했다.) 구현을 되돌리면(그룹 컨테이너가 없으면) (a)/(b) 모두 그룹 컨테이너 자체를 찾지 못해
  실패한다.

### AC-GROUP-006 — 노트를 해결하면 그 행만 사라지고, 그룹의 마지막 노트를 해결하면 그룹 자체가 사라진다 `[FE]`

Traces: REQ-GROUP-009, REQ-GROUP-010, REQ-GROUP-011

- **Given**: 한 주문(order_id 1201, order_name "#H1201")에 노트 2건, `assignee: "CS"`, 서로 다른 `line_item_id`.
  - `{id: 51, order_id: 1201, order_name: "#H1201", line_item_id: 9701, content: "먼저 해결될 메모", created_at: "2026-08-12T09:00:00Z"}`
  - `{id: 52, order_id: 1201, order_name: "#H1201", line_item_id: 9702, content: "나중에 해결될 메모", created_at: "2026-08-12T10:00:00Z"}`
  `useResolveLineItemNote`를 모킹해 `mutate(noteId)` 호출 시 `useUnresolvedLineItemNotes`가 반환하는 목록에서 해당
  `id`를 제거한 상태로 리렌더되도록 재현한다(`useLineItemNotes.ts:41-47`의 실제 낙관적 캐시 갱신을 테스트 더블로
  흉내낸다).
- **When (1차)**: 그룹1201 컨테이너 **안에서** id=51 노트의 해결 버튼을 클릭한다.
- **Then (1차)**: 그룹1201 컨테이너는 여전히 존재하며, 그 안에 "나중에 해결될 메모"(id=52)만 남아 있고 "먼저 해결될
  메모"(id=51)는 더 이상 없다.
- **When (2차)**: 같은 그룹1201 컨테이너 **안에서** 남은 id=52 노트의 해결 버튼을 클릭한다.
- **Then (2차)**: 그룹1201 컨테이너가 문서에서 **완전히 사라진다**(해당 그룹을 가리키는 조회가 더 이상 아무것도 찾지
  못한다) — 빈 그룹 껍데기가 남지 않는다.
- **판별력**: 마지막 노트를 해결한 뒤에도 빈 그룹 컨테이너를 남겨 두면 2차 단정이 실패한다 — 이것이 이 시나리오의
  독립적인 mutation이다. 1차 단정(형제 노트 id=52의 행이 그대로 남는다)은 `NoteCard`가 무수정이며 각자의 `note` prop에
  바인딩되어 있다는 설계(`spec.md` 명시적 가정 6)에서 자동으로 성립하는 성질이라 별도의 그럴듯한 구현 버그를 상정하기
  어렵다 — "노트 하나를 해결하면 그 그룹 전체가 사라진다"는 식의 구현은 그룹이 `tabNotes`에서 매 렌더마다 다시
  파생되는 이 설계(`plan.md` 기술적 접근 참조)에서는 나오지 않는 경로다. 다만 1차 단정도 그룹1201 컨테이너를 조회하는
  시점부터 시작하므로, 구현을 되돌리면(그룹 컨테이너가 없으면) 1차 단정에서부터 실패한다 — 이 시나리오 전체의
  판별력은 되돌림에 대해서는 1차 단정이, 빈 그룹 잔존에 대해서는 2차 단정이 각각 담당한다.

## 빈 상태

### AC-GROUP-007 — 그룹이 없는 탭은 기존 빈 상태를 그대로 보여주고 빈 그룹을 남기지 않는다 `[FE]`

Traces: REQ-GROUP-012

- **Given**: CS 탭에는 노트 2건이 한 주문(order_id 1301, order_name "#I1301")에 몰려 있어 그룹이 1개 만들어지고, 발주
  탭에는 이 픽스처에서 조건에 맞는 노트가 **0건**이 되도록 구성한다. 다른 다건 픽스처(AC-001/003/004/006/008)와
  동일하게 두 노트는 서로 다른 `line_item_id`를 가진다 — 그렇지 않으면 `filterNotes`의 LineItem당 최신 1건 집계
  (`LineItemNotesPage.tsx:38-46`)가 CS 탭에서도 둘을 하나로 접어 노트 1건짜리 그룹이 되어 버려 아래 (1차) 단정이
  성립할 수 없다.
  - `{id: 81, order_id: 1301, order_name: "#I1301", line_item_id: 9801, assignee: "CS", content: "먼저 남긴 CS 메모", created_at: "2026-08-12T09:00:00Z"}`
  - `{id: 82, order_id: 1301, order_name: "#I1301", line_item_id: 9802, assignee: "CS", content: "나중에 남긴 CS 메모", created_at: "2026-08-12T10:00:00Z"}`
  - (모든 노트의 `assignee`가 `"CS"`이므로 발주 탭에서는 조건에 맞는 노트가 0건이 된다. `note_type`은 기본값
    `""`이며 타출판사 탭과는 무관하다.)
- **When (1차)**: CS 탭(기본 활성)으로 렌더링한다.
- **Then (1차)**: order_id 1301의 그룹 컨테이너가 정확히 노트 2건(id=81, id=82)을 포함하며, 그 헤더에 "#I1301"과 건수
  "2"가 표시된다.
- **When (2차)**: 발주 탭으로 전환한다.
- **Then (2차)**: 기존 빈 상태 메시지 "미해결 품목 메모가 없습니다."(`LineItemNotesPage.tsx:396`)가 표시되고, 발주
  탭 영역에는 그룹 컨테이너가 **하나도** 렌더링되지 않는다(빈 그룹 래퍼조차 없다).
- **판별력**: 그룹화 로직이 빈 배열을 잘못 처리해(예: `groups.length === 0` 검사를 `Object.keys(groupedByOrderId)` 대신
  잘못된 값에 대해 수행해 빈 객체 1개짜리 그룹이 생기는 경우) 팬텀 그룹 컨테이너가 렌더링되면 (2차) 단정이 실패한다.
  1차 단정은 구현을 되돌리면(그룹 컨테이너가 없으면) 실패한다. **다만 2차 단정만 놓고 보면, 오늘 이미 존재하는 빈
  상태 분기(`:394-398`)가 이 SPEC 이전 코드에서도 동일하게 통과시킨다** — 즉 2차 단정 단독으로는 되돌린 코드에서도
  통과하며, 판별력은 오직 위에 서술한 "팬텀 빈 그룹" mutation에 대해서만 성립한다. 이 시나리오 전체가 되돌린 코드에서
  실패하는 것은 1차 단정 덕분이다.

---

## 품질 게이트 — Definition of Done 매핑

| AC | 테스트 파일 | 테스트 번호 | 검증 대상 REQ |
|---|---|---|---|
| AC-GROUP-001 `[FE]` | `LineItemNotesPage.test.tsx` | T1 | 001, 002, 003, 004, 013 |
| AC-GROUP-002 `[FE]` | `LineItemNotesPage.test.tsx` | T2 | 005 |
| AC-GROUP-003 `[FE]` | `LineItemNotesPage.test.tsx` | T3 | 006 |
| AC-GROUP-004 `[FE]` | `LineItemNotesPage.test.tsx` | T4 | 007 |
| AC-GROUP-005 `[FE]` | `LineItemNotesPage.test.tsx` | T5 | 009 |
| AC-GROUP-006 `[FE]` | `LineItemNotesPage.test.tsx` | T6 | 009, 010, 011 |
| AC-GROUP-007 `[FE]` | `LineItemNotesPage.test.tsx` | T7 | 012 |
| AC-GROUP-008 `[FE]` | `LineItemNotesPage.test.tsx` | T8 | 002, 008 |
| AC-GROUP-009 `[FE]` | `LineItemNotesPage.test.tsx` | T9 | 005 |
| AC-GROUP-010 `[FE]` | `LineItemNotesPage.test.tsx` | T10 | 006 |

시나리오로 검증하지 않는 요구사항: **REQ-GROUP-014**(백엔드 무변경) 하나뿐이며, `plan.md` 완료 조건의
`git diff --stat backend/` 게이트가 CI 수준으로 확인한다.

**추가 회귀 게이트**(신규 테스트가 아니라 기존 스위트의 무수정 통과):

- `frontend/src/pages/OrderDetailPage.test.tsx` 전량
- `frontend/src/pages/DashboardPage.test.tsx` 전량
- `frontend/src/pages/ForbiddenPage.test.tsx` 전량

이 세 파일은 이 SPEC이 건드리지 않는 페이지들이며, `LineItemNotesPage.tsx`가 공유 훅(`useLineItemNotes.ts`)이나 공유
타입(`types/order.ts`)을 통해 다른 페이지에 영향을 주지 않았음을 확인하는 용도다.
