# SPEC-ORDER-014 태스크 분해 (TDD)

개발 방법론: **TDD (RED-GREEN-REFACTOR)** — `quality.yaml` `development_mode: tdd`,
`min_coverage_per_commit: 80%`, 목표 커버리지 85%+.

각 TASK는 단일 RED-GREEN-REFACTOR 사이클로 완결 가능한 최소 단위다. `plan.md`의 M1-M5
마일스톤을 파일 단위 원자적 태스크로 재편했다(M1+M2 → TASK-001, M3 → TASK-002/005,
M4 → TASK-003, M5 → 각 컴포넌트 태스크에 흡수). 신규 파일은 `plan.md`가 명시한 파일
목록을 벗어나지 않는다 — router/Sidebar 수정 없음(plan.md 확인 결과 라우터는
`@/pages/RackNumberPage` 별칭이 `index.tsx`로 자동 해석되므로 무수정, Sidebar는
SPEC-ORDER-013에서 이미 `/rack-number` 항목이 등록되어 있으므로 무수정).

## 태스크 목록

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|---------------|----------------|--------|
| TASK-001 | 백엔드 집계 엔드포인트 `LineItemRackNumberSummaryView` — 미출고 필터 정의/고정 적용/우회 파라미터 무시, 전체 주문 교차 조회, `rack_number` 그룹핑(미지정 버킷 포함), `total_quantity` 합산(null→0), 그룹별 LineItem 상세 5필드, `shipped` 전량 제외, 페이지네이션 미적용 단일 payload. `UnorderedItemsView` 패턴 재사용(별도 시리얼라이저 없이 plain dict 응답). urls.py에 `LineItemRackNumberSummaryView`를 알파벳 순으로 등록. T1~T10(필터/그룹핑/합산/필드/제외/무페이지네이션/파라미터 무시/빈 응답/인증) 순차 RED-GREEN | REQ-RACKSUM-001, 002, 002a, 003, 004, 004a, 005, 006, 007, 008 | 없음 | `backend/order/purchase_order_views.py` [MODIFY]; `backend/order/urls.py` [MODIFY]; `backend/order/tests/test_spec_014.py` [NEW] | pending |
| TASK-002 | `SearchTab` 추출 — **회귀 전용 태스크, 동작 변경 0%**. `RackNumberPage.tsx`를 `RackNumberPage/tabs/SearchTab.tsx`로 이동하고 export 컴포넌트명만 `RackNumberPage` → `SearchTab`으로 변경(내부 상태/핸들러/서브컴포넌트 무변경). `RackNumberPage.test.tsx`를 `SearchTab.test.tsx`로 이동하고 import 경로 + `render()` 호출 대상만 치환, 기존 15개 테스트의 단언은 문자 하나도 수정하지 않는다. RED: 새 경로로 이동하기 전 `SearchTab.test.tsx`가 모듈 부재로 실패함을 확인. GREEN: 파일 이동 + export명 변경만으로 15개 테스트 전부 통과. REFACTOR: 생략(동작 변경 금지 원칙, Enforce Simplicity/Scope Discipline) | REQ-RACKSUM-009a | 없음 (TASK-001과 병렬 실행 가능) | `frontend/src/pages/RackNumberPage.tsx` → `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx` [MOVE]; `frontend/src/pages/RackNumberPage.test.tsx` → `frontend/src/pages/RackNumberPage/tabs/SearchTab.test.tsx` [MOVE] | pending |
| TASK-003 | 프론트엔드 서비스 함수 `getRackNumberSummary()` + 타입 3종(`RackNumberSummaryLineItem`/`RackNumberSummaryGroup`/`RackNumberSummaryResponse`) + 읽기 전용 쿼리 훅 `useRackNumberSummary()`(TanStack Query `useQuery`, `queryKey: ['rack-number-summary']`, 탭 마운트 시 자동 요청 — `enabled` 플래그 불필요). 기존 뮤테이션 훅(`useUpdateLineItemRackNumber` 등)은 무변경, 캐시 무효화 연결 없음(Enforce Simplicity, plan.md M4 명시적 판단) | REQ-RACKSUM-010(데이터 계약 부분) | TASK-001 (백엔드 응답 스키마 확정 필요) | `frontend/src/services/rackNumberApi.ts` [MODIFY]; `frontend/src/hooks/useRackNumberQueries.ts` [MODIFY] | pending |
| TASK-004 | `SummaryTab` 컴포넌트 — `useRackNumberSummary()`로 그룹 목록 렌더링, 그룹 헤더(`rack_number` 또는 "미지정" 라벨 + `총 {total_quantity}권`), 미지정 그룹을 named 그룹과 시각적으로 구분되는 라벨로 렌더링, 그룹 내 LineItem 행(주문번호 — null이면 "-", SKU, 도서명, 수량, 물류상태 라벨 — `purchaseOrderApi.ts`의 `LOGISTICS_STATUS_OPTIONS`를 `OrderDetailPage.tsx`의 `LOGISTICS_STATUS_LABELS` 패턴으로 로컬 변환해 재사용), `groups.length === 0`일 때 빈 상태 메시지(빈 테이블 미렌더링), 체크박스/입력창/버튼 등 편집 엘리먼트 전무, 어떤 클릭도 PATCH/업로드 요청을 트리거하지 않음. 로딩 중 `role="status"` 스켈레톤(기존 `UnorderedItemsTab` 패턴 재사용) | REQ-RACKSUM-010(렌더링 부분), 011, 011a, 012, 013, 014, 015 | TASK-003 (훅을 mock하여 테스트) | `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx` [NEW]; `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` [NEW] | pending |
| TASK-005 | 탭 셸 `RackNumberPage/index.tsx` — `PurchaseOrders/index.tsx`와 동일한 `role="tablist"`/`role="tabpanel"` 상태 기반 탭 스위처 패턴, `TabValue = 'search' \| 'summary'`, 기본 활성 탭 `useState<TabValue>('search')`(SPEC-ORDER-013 기존 테스트 회귀 방지의 필수 조건), `renderTab()`으로 `<SearchTab />`/`<SummaryTab />` 전환. **named export는 반드시 `RackNumberPage`를 유지**해야 함 — `router/index.tsx:118`이 `const { RackNumberPage } = await import('@/pages/RackNumberPage')`로 구조분해하므로, 다른 이름으로 export하면 라우팅이 즉시 깨짐(빌드로 검증) | REQ-RACKSUM-009, 009b, 010(활성화 트리거 부분) | TASK-002 (SearchTab 존재), TASK-004 (SummaryTab 존재) | `frontend/src/pages/RackNumberPage/index.tsx` [NEW]; `frontend/src/pages/RackNumberPage/index.test.tsx` [NEW] | pending |
| TASK-006 | 최종 검증 게이트(신규 프로덕션 코드 없음, REQ 매핑 없는 품질 게이트 태스크) — `npm run build` 성공 확인(폴더+`index.tsx` 전환에 따른 `@/pages/RackNumberPage` 별칭 모듈 해석 리스크 검증), `SearchTab.tsx`/`SearchTab.test.tsx` diff가 "이동 + 이름 변경"만으로 구성되어 있는지 코드 리뷰(REQ-RACKSUM-009a 회귀 방지 핵심 증거), 기존 SPEC-ORDER-013 프론트엔드 테스트 15개 + SPEC-ORDER-011/012/013 백엔드 테스트 스위트(`test_spec_011.py`/`012`/`013`) 전부 무변경 통과 확인, ruff/black·ESLint/Prettier 통과 | 해당 없음(Definition of Done / 품질 게이트) | TASK-001, TASK-002, TASK-003, TASK-004, TASK-005 | 없음(코드 변경 없음, 검증만 수행) | pending |

## 요구사항 커버리지 매트릭스

REQ-RACKSUM-001~015 및 하위 접미사(002a/004a/009a/009b/011a) 전체 20개 항목이 1개 이상의
TASK에 매핑됨을 검증했다.

| REQ ID | 매핑 TASK | REQ ID | 매핑 TASK | REQ ID | 매핑 TASK |
|--------|-----------|--------|-----------|--------|-----------|
| REQ-RACKSUM-001 | TASK-001 | REQ-RACKSUM-007 | TASK-001 | REQ-RACKSUM-011 | TASK-004 |
| REQ-RACKSUM-002 | TASK-001 | REQ-RACKSUM-008 | TASK-001 | REQ-RACKSUM-011a | TASK-004 |
| REQ-RACKSUM-002a | TASK-001 | REQ-RACKSUM-009 | TASK-005 | REQ-RACKSUM-012 | TASK-004 |
| REQ-RACKSUM-003 | TASK-001 | REQ-RACKSUM-009a | TASK-002 | REQ-RACKSUM-013 | TASK-004 |
| REQ-RACKSUM-004 | TASK-001 | REQ-RACKSUM-009b | TASK-005 | REQ-RACKSUM-014 | TASK-004 |
| REQ-RACKSUM-004a | TASK-001 | REQ-RACKSUM-010 | TASK-003, TASK-004, TASK-005 | REQ-RACKSUM-015 | TASK-004 |
| REQ-RACKSUM-005 | TASK-001 | | | | |
| REQ-RACKSUM-006 | TASK-001 | | | | |

AC-RACKSUM-004b/007a(교차 주문 다건 그룹핑, 부분 출고 주문)는 REQ-RACKSUM-004/007의 세부
시나리오이며 TASK-001의 T2/T6a 테스트 범위에 이미 포함된다(SPEC-ORDER-013 tasks.md와 동일한
AC 세분화 관례).

## 실행 순서(의존성 그래프)

```
TASK-001 (백엔드 집계 엔드포인트, 독립)          TASK-002 (SearchTab 추출, 독립 — TASK-001과 병렬)
      │                                                   │
      ▼                                                   │
TASK-003 (서비스+훅, 백엔드 계약 확정 필요)                 │
      │                                                   │
      ▼                                                   │
TASK-004 (SummaryTab, 훅 mock 필요)                        │
      │                                                   │
      └───────────────────┬───────────────────────────────┘
                           ▼
                  TASK-005 (탭 셸 index.tsx, SearchTab+SummaryTab 둘 다 필요)
                           │
                           ▼
                  TASK-006 (빌드+회귀 검증 게이트, 전체 태스크 완료 후)
```

TASK-001과 TASK-002는 서로 파일이 겹치지 않으므로(백엔드 vs 프론트엔드 이동) 병렬 착수
가능하다. TASK-006은 모든 프로덕션 코드 변경이 완료된 뒤 마지막에 실행하는 순수 검증
게이트로, `plan.md`의 "모듈 해석 리스크"·"기존 15개 테스트 회귀" 리스크 항목을 직접
소거한다.

## 범위 경계 확인 (Exclusions 재확인)

다음 항목은 어떤 TASK에도 포함되지 않는다 — 구현 중 우발적으로 추가되지 않도록 코드 리뷰
시 명시적으로 확인할 것:

- Tab2 편집 UI(체크박스/일괄 적용/인라인 편집) — TASK-004에서 오히려 "부재를 검증"하는
  테스트만 존재해야 한다(REQ-RACKSUM-014/015).
- 미출고 필터 토글/파라미터 — TASK-001에서 쿼리 파라미터를 아예 읽지 않는 방식으로 구현,
  방어 코드 자체가 불필요(REQ-RACKSUM-002a).
- 페이지네이션 — TASK-001에서 `PageNumberPagination` 미사용 확인(REQ-RACKSUM-008).
- `rack_number` 기준 추가 검색/정렬 UI, Excel/CSV 내보내기 — 어떤 TASK에도 계획되어 있지
  않음.
- Tab1(SearchTab) 로직 변경 — TASK-002는 이동+이름변경만 허용, REFACTOR 단계 생략.
- Tab1↔Tab2 캐시 무효화 연결 — TASK-003에서 명시적으로 배제(Enforce Simplicity).
- router/index.tsx, Sidebar.tsx 수정 — plan.md 확인 결과 둘 다 무수정 대상.
