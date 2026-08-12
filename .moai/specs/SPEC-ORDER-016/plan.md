---
id: SPEC-ORDER-016
document: plan
version: 1.0.5
status: completed
updated: 2026-08-12
---

# 구현 계획 — SPEC-ORDER-016 강제 출고 처리

`spec.md`의 요구사항(REQ-FORCE-001~025)을 구현하기 위한 작업 분해, 파일별 변경 계획, 기술적 접근,
리스크와 완화책, MX 태그 계획을 정리한다. 근거 자료는 `research.md`(파일:라인 인용 포함)를, 확정
스코프는 `interview.md`를 참조한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을
재진술하지 않고 REQ ID로 참조한다.

v1.0.4 변경: 사용자 스코프 변경으로 **강제 경로에만 행 단위 잠금**이 추가되었다(REQ-FORCE-025,
설계 결정 O). 기술적 접근 M2에 잠금 단계를 5번으로 삽입하고 이후 번호를 밀었으며, R8을 "해소됨 +
잔여 격차 2건"으로 재작성, R20 신설, mx_plan에 잠금 구간 `@MX:NOTE`를 추가하고 기존 `@MX:WARN`을
잔여 격차용으로 재정의, AC-FORCE-023의 동시성 테스트 기법을 신설 절에 지정했다(해당 디렉터리에
선례가 없음을 확인). 정상 경로는 변경하지 않으며 그 확인을 M4 조건에 넣었다.

v1.0.3 변경: plan-auditor iteration 3의 major 2건만 반영했다(사용자 결정, minor F3~F10 보류).
F1 — 음수·0·판독불가 행 제거를 **그룹화 이전** 단계로 명시하고 살아남은 행이 없는 대상은 그룹을
만들지 않도록 기술적 접근 M2-3/M2-4와 R19를 갱신. F2 — 결과 슬롯 통째 대체를 **병합 규칙**으로
교체해 기술적 접근 M5-7, 프론트 파일 계획, R18을 갱신.

v1.0.2 변경: plan-auditor iteration 2의 N3(응답 스키마가 기존 클라이언트 타입보다 좁음)·N4(실행 후
상태 모호)·N10(설계 결정 L 도입 후 stale read 실패 모드 미갱신)·N11(도달 불가능한 `purchase_status`
라벨 맵)·N13(경로 오기)을 반영했고, N12 통합으로 `spec.md`에서 옮겨온 구현 지시 3건(클라이언트 타입
optional 지정, 테스트 훅 유지, 섹션 시각적 일관성)을 이 문서에 흡수했다. 요구사항 번호가 001~024로
재부여되었으므로 본문의 REQ 참조를 전부 갱신했다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M1 (High) — 후보 조회 구현**: 주문 식별자 목록을 한 요청으로 받아 주문별 반영 가능 품목 목록을
  반환하는 읽기 전용 조회. 커버 REQ: 003, 004, 005, 006, 017.
- **M2 (High) — 강제 반영 구현**: 사전 게이트(REQ-FORCE-002) → total 불변식 및 그룹화 이전 제거(011)
  → 대상별 합산(008) → **대상 행 잠금(025)** → 한도 판정(009/010) → 반영·전이 → 응답 구성(016).
  쓰기 대상 3필드 제한(013)과 원자성(014) 포함.
  커버 REQ: 002, 007~014, 016, 017, 025.
- **M3 (High) — 백엔드 테스트**: `test_spec_016.py` 신규 작성. AC-FORCE-002~014, 016~018, 023 커버
  (023은 아래 "동시성 테스트 기법" 절이 지정한 방식을 따른다).
- **M4 (High) — 기존 백엔드 계약 회귀 확인**: `test_spec_015.py` 전량 재실행(REQ-FORCE-018).
  `_process_outbound_rows`에 잠금이 추가되지 않았음을 diff로 확인한다(설계 결정 O).
- **M5 (Medium) — 프론트엔드 구현**: 서비스 함수·타입, 후보 조회 쿼리 훅 + 강제 실행 뮤테이션,
  매칭 실패 섹션 전용 컴포넌트, 선택 상태·피커·일괄 실행·결과 대체 배선, 한국어 라벨 매핑.
  커버 REQ: 001, 003(요청 횟수), 015, 019~024.
- **M6 (Medium) — 프론트엔드 테스트 + 회귀**: AC-FORCE-001, 003, 015, 019~022 커버. 기존 3개 테스트
  파일 및 프론트엔드 전체 스위트 통과 확인(v1.0.5 정정 — "공유 결과 섹션 컴포넌트의 4개 외부
  호출부"는 존재하지 않는다).
- **M7 (Low) — 문서 동기화**: `product.md` 갱신, SPEC 상태 전이, HISTORY 갱신.

의존 관계: M1 → M2 → M3 → M4, M2 → M5 → M6.

## 파일별 변경 계획

### 백엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/purchase_order_views.py` | 후보 배치 조회 뷰(가칭 `OutboundForceCandidateView`)와 강제 반영 뷰(가칭 `OutboundForceProcessView`) 신설. 후보 조회는 `LineItemRackNumberSummaryView`(`:2671-2728`)를 크로스-오더 읽기 전용 뷰 구조 선례로, `_process_outbound_rows`의 `name__in` 배치 조회 + 파이썬 그룹핑(`:2919-2945`)을 배치 구현 선례로 삼는다. 강제 반영은 `_process_outbound_rows`(`:2810-3101`)의 판정·전이·`bulk_update` 구간을 참조하되 **정상 경로의 쿼리 수와 응답 계약은 건드리지 않는다**(REQ-FORCE-018). 0 수량 완료 신호 분기(`:2999-3037`)는 재사용하지 않는다(REQ-FORCE-007). |
| MODIFY | `backend/order/urls.py` | 라우트 2건 등록. `bulk-*` 계열과 동일하게 `<int:pk>/` 패턴보다 **먼저** 등록한다(기존 주석: `urls.py:70`, `:73`, `:84`). 기존 출고 경로 명명 관례를 따른다. |
| EXISTING | `backend/order/serializers.py` | 변경하지 않는다. `LineItemDetailSerializer`(`:110-123`)에 `purchase_status`가 없어 후보 payload로 재사용할 수 없고, 여기에 필드를 추가하면 주문 상세 응답 계약이 함께 바뀐다. 후보 응답은 REQ-FORCE-006이 정한 필드만 담아 별도로 구성한다. |
| EXISTING | `backend/order/models.py` | 변경 없음. 신규 컬럼·마이그레이션 없음. `Order.name` 인덱스(`:100-110`)가 이미 존재해 배치 조회 성능 전제는 충족되어 있다. |
| NEW | `backend/order/tests/test_spec_016.py` | 모듈 docstring에 `"""SPEC-ORDER-016: 강제 출고 처리 (TDD)."""` + `Coverage targets:` T1~Tn과 각 T의 REQ/AC 매핑(`test_spec_015.py:1-24` 관례). 모듈 상단 `_make_order()` / `_make_line_item()` 팩토리, `# ---` 섹션 배너, 모듈 레벨 URL 상수, `user` / `auth_client` / `anon_client` fixture(username 접두 `spec016_`). |
| EXISTING | `backend/order/tests/test_spec_015.py` | 변경하지 않는다. 무수정 전량 통과가 M4의 완료 조건이다. |

### 프론트엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `frontend/src/services/outboundApi.ts` | 후보 조회 함수 + 강제 실행 함수 + 후보 타입 추가. **강제 실행 함수의 반환 타입은 기존 `OutboundProcessResponse`를 그대로 사용한다**(REQ-FORCE-016) — 서버가 같은 계약을 반환하므로 신규 응답 타입을 만들지 않는다. 기존 `OutboundUnmatchedItem`/`OutboundMatchedItem`/`OutboundQuantityExceededItem`(`:37-65`)은 수정하지 않는다. 불가피하게 기존 항목 타입에 필드를 추가해야 한다면 반드시 optional(`?`)로 선언한다 — 필수 필드는 `index.test.tsx:31-38` / `outboundApi.test.ts:33-36`의 리터럴 fixture를 컴파일 실패시킨다. `OutboundUnmatchedReason` union은 변경하지 않는다(`outboundApi.test.ts:67`이 정확히 5개임을 assert). 강제 실행 함수는 HTTP 400을 rejection으로 표면화한다. |
| MODIFY | `frontend/src/hooks/useOutboundQueries.ts` | 후보 조회 `useQuery` + 강제 실행 뮤테이션. 뮤테이션은 기존 `useOutboundMutation` 팩토리(`:20-35`)를 그대로 재사용한다 — 이 팩토리는 `Promise<OutboundProcessResponse>`를 요구하므로 REQ-FORCE-016의 "기존 계약 전체 재사용"과 정합한다. `ORDER_DETAIL_QUERY_KEY` prefix 무효화(`:28`), 고정 한국어 에러 문구(`:31-33`), 성공 토스트 `buildOutboundSummary`(`:14-16`) 관례를 승계한다. 쿼리 키는 문자열 리터럴 배열 + 파라미터 형태로 두되, 파라미터 없는 예(`useRackNumberQueries.ts:76-81`)가 아니라 파라미터 있는 예(`frontend/src/features/order/hooks/useOrders.ts:11`, `queryKey: [...ORDERS_QUERY_KEY, params]`)를 따른다. 훅 위 `// REQ-FORCE-XXX:` 주석. |
| **EXISTING** | **`ResultSection`** (`frontend/src/pages/OutboundPage/index.tsx` 내부의 비-export 로컬 함수) | **변경하지 않는다**(설계 결정 M). 행 계약이 `cells: string[]`이라 체크박스·피커를 담을 수 없다. 성공·수량초과 섹션은 계속 이 함수가 렌더한다. **v1.0.5 정정**: v1.0.4까지 이 컴포넌트를 `frontend/src/components/ResultSection.tsx` 파일이며 외부 호출부 4곳을 가진다고 서술했으나 그런 파일도 호출부도 존재하지 않는다 — 무변경 결론은 `cells: string[]` 제약만으로 유효하다. |
| NEW | `frontend/src/pages/OutboundPage/` 하위 매칭 실패 섹션 컴포넌트 | 매칭 실패 섹션 전용 렌더링 + 행별 선택 컨트롤 + 대상 선택 피커(REQ-FORCE-019~021). **구현 지시**: (a) 기존 공유 컴포넌트의 마크업을 참조해 섹션 제목·건수 표기·톤 클래스·컬럼 헤더 구성을 동일하게 재현하되 그 컴포넌트를 import하거나 수정하지 않는다. (b) 기존 테스트 훅 `data-testid="outbound-unmatched"`(`OutboundPage/index.tsx:148`)를 그대로 유지한다 — `index.test.tsx:218-223`이 이 훅으로 섹션을 찾는다. colocate 테스트 파일 동반. |
| NEW | `frontend/src/pages/OutboundPage/` 하위 라벨 매핑 모듈 | `logistics_status` 코드값 → 한국어 라벨 `Record`(`OrderDetailPage.tsx:52` / `RackNumberPage/tabs/SummaryTab.tsx:12`의 `LOGISTICS_STATUS_LABELS` 방식). 매칭 실패 사유 라벨은 기존 `UNMATCHED_REASON_LABELS`를 재사용한다. **`purchase_status` 라벨 맵은 만들지 않는다** — 취소 품목은 후보에서 제외되고(REQ-FORCE-005) 후보 응답에 `purchase_status`가 실리지 않으므로(REQ-FORCE-006) 이 값은 섹션에 도달하지 않는다. |
| MODIFY | `frontend/src/pages/OutboundPage/index.tsx` | 매칭 실패 섹션 렌더링을 신규 전용 컴포넌트로 교체(성공·수량초과는 공유 컴포넌트 유지), 자격 판정·선택 상태(로컬 `useState`, 설계 결정 H)·후보 조회 배선·일괄 실행 컨트롤 연결. 강제 실행 성공 시 **기존 `result` 슬롯(`:31-33`)을 병합 결과로 `setResult`하고 선택 상태를 비운다**(REQ-FORCE-024, 설계 결정 N) — 슬롯 구조와 갱신 방식은 두 기존 제출 경로(`:42`, `:52`)와 같고, 넘기는 값만 응답 원본이 아니라 병합 결과다. **`export function OutboundPage` 명명과 폴더+`index.tsx` 모듈 해석을 유지해야 한다**(`router/index.tsx:129-135`, @MX:ANCHOR `OutboundPage/index.tsx:24-28`). |
| MODIFY | `frontend/src/pages/OutboundPage/index.test.tsx` | 신규 AC 테스트 추가. 최상위 `describe('OutboundPage — SPEC-ORDER-016', ...)` 아래 `describe('AC-FORCE-0NN: <한국어 시나리오>', ...)` 관례(`:76, 81, 154, 268, 317`). 기존 snake_case 금지 테스트(`:218-223`)는 수정하지 않고 그대로 통과해야 한다. |
| MODIFY | `frontend/src/services/outboundApi.test.ts` | 신규 함수의 요청 URL·payload·응답 매핑 테스트 추가. 기존 `ALL_UNMATCHED_REASONS` 5개 assert(`:67`)는 변경하지 않는다. |
| MODIFY | `frontend/src/hooks/useOutboundQueries.test.tsx` | 신규 훅 테스트 추가. `renderHook` + 로컬 `QueryClientProvider`(`retry: false`) 관례(`:36-41`). |
| EXISTING | `frontend/src/router/index.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/types/order.ts` | 변경 없음. `Sidebar.test.tsx:173-194`가 현재 메뉴 구성을 pin한다. `LineItemDetail`(`types/order.ts:112-136`)은 후보 타입으로 재사용하지 않는다. |

## 기술적 접근

### 후보 조회 (M1)

1. **요청 계약**: 주문 식별자 목록 1개. 빈 목록은 오류가 아니라 빈 결과다(REQ-FORCE-003).
2. **주문 해석**: `Order.objects.filter(name__in=[...])`를 `pk` 오름차순 정렬 후 이름당 최초 1건만
   채택 — 정상 경로(`:2912-2925`)와 동일(REQ-FORCE-004). 정렬 생략 시 MySQL 반환 순서에 따라 피커와
   기록 대상이 어긋난다. 생성 일시 기준 정렬은 백필 주문에서 `pk` 순서와 어긋나므로 쓰지 않는다.
3. **후보 수집**: 채택된 주문 id 집합으로 LineItem을 한 번에 조회하고 파이썬에서 주문별 그룹핑
   (`:2919-2945` 패턴). 조회 단계에서 `purchase_status="order_cancelled"`와 `sku__isnull=True`를
   제외한다(REQ-FORCE-005).
4. **응답**: REQ-FORCE-006이 정한 필드 + 잔여 용량 표시. 정렬은 결정적이어야 한다(`pk` 오름차순 등
   안정적 기준). 이 조회는 어떤 쓰기도 수행하지 않는다.
5. **쿼리 예산**: 별도 엔드포인트이므로 기존 T8 상한과 무관하다. 주문 조회 1회 + 품목 조회 1회의
   고정 쿼리 수를 목표로 하며 주문 수에 비례해 늘어나서는 안 된다.

### 강제 반영 (M2)

1. **입력 계약**: 행마다 주문 식별자, sku(표시·보고용), 요청 수량, 대상 LineItem 식별자. 서버는 그
   행의 원래 매칭 실패 사유를 재도출하지 않는다(설계 결정 J).
2. **사전 게이트 (요청 전체 판정, 쓰기 이전)**: REQ-FORCE-002의 7개 위반 조건 중 하나라도 있으면
   요청 전체를 HTTP 400으로 거부한다. 구현상 주의점:
   - 행 형태 검증을 게이트의 첫 단계로 둔다 — 정상 경로가 `invalid_row`로 강등하는 것과 달리 강제
     경로는 400으로 거부한다(신규 사유 코드를 만들지 않기 위함).
   - 주문 이름 집합과 대상 id 집합을 각각 한 번씩 조회해 판정한다. 행 수에 비례한 쿼리를 만들지
     않는다.
   - 주문 해석은 후보 조회와 동일한 최저 `pk` 규칙(REQ-FORCE-004). 해석 결과가 없으면 그 행은 소유권
     검증을 통과할 수 없으므로 위반으로 처리한다 — `resolved_order`가 `None`일 때 검사를 건너뛰는
     구현은 교차 주문 쓰기를 열어주므로 금지한다.
3. **total 불변식 (행 단위, 그룹화 이전)**: 음수·0·판독불가 행을 `invalid_total`로 보고하고 그
   행을 **그룹화 단계에 도달하기 전에 목록에서 제거**한다(REQ-FORCE-011). 정상 경로가
   `:2865-2898`에서 행을 거부한 뒤 `:2900-2901`의 합산에 도달하지 않는 것과 같은 순서다. 이 단계를
   한도 판정 뒤로 미루면 음수 입력이 한도 검사를 통과해 `shipped_quantity`를 감소시키는
   SPEC-ORDER-015 Defect 1이 재현된다.
4. **대상별 합산**: 합산 키는 지정된 대상 식별자(REQ-FORCE-008)이며, 그룹은 3단계를 통과한 행만으로
   구성한다. 서로 다른 두 매칭 실패 행이 같은 대상을 지정하는 것은 정당한 입력이며 오류가 아니다.
   1개 행만 있는 대상의 합산 수량은 그 행의 수량이다. **어떤 대상의 행이 전부 제거되면 그 대상의
   그룹을 만들지 않는다** — 빈 그룹을 합산 수량 0으로 만들어 다음 단계에 넘기면 `0`이 한도 판정을
   통과해 `shipped_at`이 찍히고, 용량이 0이거나 이미 채워진 대상에서는 `0 >= 0`이 성립해
   `"shipped"`까지 전이된다(iteration 3 F1). 결과적으로 5단계에 도달하는 모든 그룹의 합산 수량은
   최소 1이다.
5. **대상 행 잠금 (한도 판정 직전)**: 그룹이 확정된 뒤, 요청 트랜잭션 안에서 지정된 대상
   LineItem들을 `select_for_update()`로 잠근 상태로 다시 읽고 **그 값으로 한도를 판정한다**
   (REQ-FORCE-025, 설계 결정 O). 선례는 같은 파일의 `_apply_logistics_transition`
   (`purchase_order_views.py:247`)이다. 구현 시 주의점:
   - 잠금은 **기존 대상 조회 SELECT에 붙인다** — 별도 쿼리를 추가하지 않는다. 게이트 단계에서 이미
     대상 행을 읽으므로, 그 조회를 잠금 조회로 승격하거나 판정 직전에 한 번만 잠금 조회하도록
     구성한다. 어느 쪽이든 요청당 쿼리 수는 늘지 않아야 한다.
   - 잠금 순서를 **대상 id 오름차순으로 고정**해 여러 대상을 잠글 때 요청 간 교착이 생기지 않게
     한다.
   - 한도 판정은 반드시 잠금 이후에 읽은 값 기준이어야 한다. 게이트에서 읽은 값을 재사용하면 잠금이
     있어도 낡은 값으로 판정하게 되어 REQ-FORCE-025가 무의미해진다.
   - **`_process_outbound_rows`에는 잠금을 추가하지 않는다** — 정상 경로 무변경은 Exclusions 항목이자
     M4 회귀 조건이다.
6. **한도 판정 및 반영**: `quantity`가 NULL이면 용량 0(SPEC-ORDER-015 설계 결정 B 승계). 초과 시
   미반영 + 대상 단위 `quantity_exceeded` 1건. 통과 시 `shipped_quantity` 증가, `shipped_at` 갱신,
   임계 도달 시 `logistics_status` 전이. 쓰기는 `bulk_update`로 일괄 수행하며, 이 세 필드 외에는
   어떤 필드도 쓰지 않는다(REQ-FORCE-013) — 주문 집계 재계산 함수도 호출하지 않으며, 이 "호출하지
   않음"은 `test_spec_013.py:383-399`, `:842-851`의 선례(`patch(...)` + `assert_not_called()`)와
   동일한 방식으로 테스트에 pin한다.
7. **원자성**: 요청 전체를 `transaction.atomic()`으로 감싼다(REQ-FORCE-014) — 5단계의 잠금은 이
   트랜잭션 안에서만 유효하므로 두 요구사항은 함께 성립한다. 고장 주입 테스트는
   `test_spec_015.py:452`의 중간 실패 롤백 테스트와 같은 방식으로 작성한다.
8. **응답 구성**: 기존 3분류 응답 계약을 필드까지 그대로 재사용한다(REQ-FORCE-016). matched /
   quantity_exceeded 항목은 **대상 단위 1건**이며, `sku`는 대상 LineItem 자신의 값, `total`은 합산
   수량, `shipped_quantity`/`quantity`/`logistics_status`/`reason`은 정상 경로 항목 구성
   (`:3026-3036`, `:3040-3050`)과 동일한 의미로 채운다. `invalid_total` 행은 정상 경로의 unmatched
   항목 구성(`:2954-2980`)과 동일하게 행 단위로 보고한다.

### 프론트엔드 (M5)

1. **자격 판정**: `reason === "line_item_not_found"` **그리고** 요청 수량 > 0인 행에만 컨트롤을
   렌더한다(REQ-FORCE-001/019). 전적으로 클라이언트 책임이다(설계 결정 J).
2. **섹션 컴포넌트 분리**: 매칭 실패 섹션만 신규 전용 컴포넌트로 렌더하고 성공·수량초과는 공유
   컴포넌트를 그대로 쓴다(설계 결정 M).
3. **선택 키**: `(주문 식별자, sku)` 쌍(설계 결정 G). 인덱스 기반 키는 쓰지 않는다. 기존 행
   key(`OutboundPage/index.tsx:154`의 `${name}-${sku}-${index}`)는 렌더 key이며 선택 상태 키와
   별개다. **서버 측 합산·응답 키는 이와 다르다**(대상 식별자, 설계 결정 K).
4. **선택 상태**: 화면 로컬 `useState`, 새 결과 도착 시 리셋(`SearchTab.tsx:28`, `:64` 관례).
5. **후보 조달**: 매칭 실패 결과가 확정된 시점에 자격 행들의 주문 식별자를 모아 **한 번** 조회한다
   (REQ-FORCE-003). 행마다 또는 피커를 열 때마다 요청하지 않는다.
6. **라벨링**: `logistics_status`와 매칭 실패 사유 **코드값**만 한국어 라벨로 변환한다
   (REQ-FORCE-021). 원값 렌더는 `index.test.tsx:218-223`을 즉시 실패시킨다. SKU·도서명 등 데이터
   값은 변환하지 않는다. 체크박스 `aria-label`은 `textContent`에 포함되지 않아 안전하며
   `SearchTab.tsx:243-249`의 관례를 따른다.
7. **실행과 결과 병합**: 실행 컨트롤은 자격·선택·대상 지정이 모두 충족된 행이 1건 이상일 때만
   활성화하고(REQ-FORCE-022), payload에는 그 행들만 담는다(REQ-FORCE-023). 성공 시 기존 결과 슬롯을
   강제 응답으로 통째 덮어쓰지 않고 **병합한 새 결과 객체로 교체**한다(REQ-FORCE-024, 설계 결정 N):
   (a) 제출한 행을 `(주문 식별자, sku)` 키로 `unmatched` 목록에서 제거, (b) 미제출 행은 그대로 유지,
   (c) 강제 응답의 `matched`·`quantity_exceeded` 항목을 각 목록 뒤에 추가, (d) 세 `*_count`를 결과
   목록 길이로 재계산, (e) 선택 상태 초기화. 슬롯 자체는 여전히 `setResult` 한 번으로 갱신되므로
   기존 단일 슬롯 구조(`OutboundPage/index.tsx:31-33`)는 그대로다 — 달라지는 것은 넘기는 값이
   응답 원본이 아니라 병합 결과라는 점뿐이다. 통째 대체가 미선택 행과 방금 생긴 수량초과 항목까지
   지우는 문제는 설계 결정 N에 기록되어 있다. HTTP 400은 기존 고정 한국어 에러 토스트 관례
   (`useOutboundQueries.ts:31-33`)로 표면화하며, 부분 반영이 없으므로 결과 슬롯을 갱신하지 않는다.

### 동시성 테스트 기법 (AC-FORCE-023)

`backend/order/tests/` 전체를 확인한 결과 **동시성 테스트 선례가 없다** — `transaction=True`,
`TransactionTestCase`, `threading`, `select_for_update` 중 어느 것도 등장하지 않는다. 따라서 이
SPEC이 관례를 새로 세운다. 열어 두지 않고 다음 기법을 지정한다.

1. **동작 검증 (주 테스트)**: `@pytest.mark.django_db(transaction=True)`로 실제 커밋이 일어나게
   하고, 두 스레드가 **각자의 DB 커넥션**으로 강제 요청 A·B를 실행한다. 두 스레드가 한도 검사
   직전까지 도달한 뒤 진행하도록 `threading.Barrier(2)`로 동기화해 "둘 다 낡은 값을 읽는" 상황을
   재현한다. 각 스레드는 `finally`에서 `django.db.connection.close()`를 호출해 커넥션을 반납해야
   한다. 검증: 성공 1건 + `quantity_exceeded` 1건, 최종 `shipped_quantity == 6`,
   `shipped_quantity <= quantity`가 항상 성립.
2. **결정적 보조 검증**: 테스트 DB가 공유 원격 MySQL이라 `transaction=True` 테스트는 테이블
   TRUNCATE를 동반해 느리고 다른 실행과 간섭할 수 있다. 따라서 1번과 별개로,
   `CaptureQueriesContext`(이미 `test_spec_015.py`의 T8 쿼리 카운트 테스트가 쓰는 도구)로 대상 조회
   쿼리에 `FOR UPDATE`가 포함되는지 확인하는 빠른 테스트를 함께 둔다. 잠금이 실수로 제거되면 이
   테스트가 먼저 실패하므로 1번이 간헐적으로 스킵되어도 회귀가 감지된다.
3. **격리**: 1번 테스트에는 전용 pytest 마커를 붙여 필요 시 선택·제외할 수 있게 하고, 그 마커를
   `pytest.ini`/`pyproject.toml`에 등록한다. 원격 공유 DB 특성상 이 테스트를 다른 pytest 프로세스와
   **동시에 실행하지 않는다**.
4. **쿼리 예산**: 잠금은 기존 대상 조회에 붙이므로 강제 요청의 쿼리 수가 늘지 않아야 한다. 필요하면
   T8과 같은 방식의 쿼리 카운트 테스트를 강제 엔드포인트에도 하나 둔다.

## 리스크 분석 및 완화책

| # | 리스크 | 영향 | 완화책 |
|---|---|---|---|
| R1 | T8 쿼리 예산 여유가 1쿼리뿐(`test_spec_015.py:1143-1153`) | 정상 경로에 쿼리를 하나라도 추가하면 즉시 실패 | 후보 조회를 별도 엔드포인트로 완전 분리(설계 결정 A). 정상 처리 함수 본문에 조회를 추가하지 않는다. M4에서 T8 4건 무수정 통과 확인 |
| R2 | 두 엔드포인트 응답 딕셔너리 전체 동등성 테스트(`:746`) | `unmatched` 항목에 비결정적 값이 섞이면 실패 | `unmatched` payload를 변경하지 않는다(REQ-FORCE-018) |
| R3 | 매칭 실패 섹션 snake_case 금지 정규식(`index.test.tsx:218-223`) | 상태 원값을 렌더하면 즉시 실패 | 상태·사유 코드값만 한국어 라벨로 매핑. SKU·도서명은 변환 대상이 아니며(REQ-FORCE-021 범위) 현재 결과 표가 이미 `sku`를 원본 그대로 렌더한다 |
| R4 | 기존 항목 타입에 필수 필드 추가 시 fixture 컴파일 실패(`index.test.tsx:31-38`, `outboundApi.test.ts:33-36`) | `tsc` 실패로 프론트 빌드 중단 | 기존 항목 타입을 수정하지 않는 것이 1순위. 불가피하면 optional(`?`)로만 추가 |
| R5 | `Order.name` 비유일 + tie-break 불일치 | 피커가 보여준 주문과 기록 주문이 어긋남 | 후보 조회와 대상 게이트 모두 최저 `pk` 규칙 사용(REQ-FORCE-004). `pk` 순서와 생성 일시 순서를 어긋나게 만든 동명 주문 시나리오를 M3에 포함 |
| R6 | 음수/판독불가 total 불변식이 두껍게 pin됨(`:932-1021`, `:1524-1637`) | 강제 경로가 별도 구현이 되면 검증 누락 → 배제된 undo 재도입 | 검증 순서를 정상 경로와 동일하게 고정(기술적 접근 M2-3), 음수·0·판독불가 케이스를 M3 필수 포함(AC-FORCE-011) |
| R7 | `purchase_status`가 LineItem 상세 직렬화 계약에 없음(`serializers.py:110-123`) | 프론트에서 취소 품목을 걸러낼 수 없음 | 제외를 **백엔드 조회 시점과 게이트 양쪽**에서 수행(REQ-FORCE-005, 002). 기존 serializer는 변경하지 않고, 이 값을 후보 응답에도 싣지 않는다 |
| R8 | 후보 조회와 실행 사이에 사람의 판단이 끼어들어 stale read 창이 정상 경로보다 넓다 | 낡은 `shipped_quantity`로 한도를 판정하면 동시 실행 2건이 합산으로 `quantity`를 넘길 수 있다 | **v1.0.4에서 강제 경로에 행 단위 잠금을 도입해 이 경합을 해소했다**(REQ-FORCE-025, 설계 결정 O) — 한도 판정은 잠금 이후 읽은 값 기준이므로 두 요청이 같은 낡은 값을 보고 둘 다 통과하는 경로가 사라진다. 잔여 격차 2건은 후속 과제 2다: (a) **정상 경로에는 여전히 잠금이 없어**(@MX:WARN `:2802-2809`) 정상↔정상, 정상↔강제 동시 처리는 보호되지 않는다. (b) 대상이 조회 이후 `order_cancelled`가 되었거나 `sku`를 잃은 경우는 잠금과 무관하게 사전 게이트에 걸려 **요청 전체가 HTTP 400으로 거부**되므로(설계 결정 L) 함께 제출한 유효한 행들도 반영되지 않는다 — 에러 토스트만으로 끝내지 말고 담당자가 결과를 다시 조회해 재시도해야 함을 인지시킨다 |
| R9 | 한 주문에 동일 SKU LineItem 복수 존재 가능(`models.py:235`) | 피커에서 제목·SKU만으로 구분 불가 | 후보의 표시 키를 안정적 식별자로 삼는다(REQ-FORCE-006) |
| R10 | `unmatched` 항목에 `line_item_id`가 없음(`:2954-2980`) | 선택 상태 키 부재 | `(주문 식별자, sku)` 쌍을 선택 키로 사용(설계 결정 G) |
| R11 | 주문 집계 미갱신이라는 선행 불일치 | 강제 경로만 고치면 두 경로가 서로 다른 부수효과를 냄 | 현행 동작 답습(설계 결정 E). REQ-FORCE-013으로 규범화하고 spy로 pin |
| R12 | `OutboundPage` named export + 폴더 모듈 해석에 라우터가 의존(@MX:ANCHOR `index.tsx:24-28`) | 컴포넌트 분할 중 export 형태를 바꾸면 `/outbound` 라우트가 깨짐 | 진입점 파일과 export 이름 유지, 신규 컴포넌트는 형제 파일로 배치 |
| R13 | 공유 결과 섹션 컴포넌트(`ResultSection`)의 행 계약이 `cells: string[]`이며 같은 페이지의 성공·수량초과 섹션 2곳이 소비 | 시그니처 확장 시 그 두 섹션과 기존 테스트가 회귀 대상 | 공유 컴포넌트를 수정하지 않고 매칭 실패 섹션만 전용 컴포넌트로 분리(설계 결정 M). **v1.0.5 정정**: 이전 판은 "외부 호출부 4곳"이라 했으나 그런 호출부는 존재하지 않는다 — 회귀 범위는 프론트엔드 전체 스위트로 대체 |
| R14 | 0 수량 행이 `line_item_not_found`로 보고되어 강제 대상이 될 수 있음(`:2969-2980`이 `:2999`보다 먼저 실행) | 임의 대상의 `shipped_quantity`를 `quantity`까지 채우는 미요구 동작 | 자격 조건에 양수 수량 포함(REQ-FORCE-001), 서버에서도 0을 `invalid_total`로 거부(REQ-FORCE-011). 미국창고 대상에 0을 넣는 케이스를 M3 필수 포함 |
| R15 | 두 매칭 실패 행이 같은 대상을 지정하면 각각은 한도를 통과하고 합산은 초과 | "수량 한도 우회 없음" 배제 조항 무력화 | 대상 식별자 기준 합산 후 1회 판정(REQ-FORCE-008). 개별 통과·합산 초과 시나리오를 M3 필수 포함 |
| R16 | 대상이 다른 주문 소속이면 정상 경로가 금지하는 교차 주문 SKU 차용이 강제 경로로 재현됨 | 무관한 주문의 품목에 출고 수량이 기록됨 | 게이트에서 소유권 검증 후 요청 전체 400(REQ-FORCE-002). 교차 주문 지정과 주문 미해석 케이스를 M3 필수 포함 |
| R17 (신규) | 강제 응답이 기존 클라이언트 타입보다 좁으면 재사용 경로가 깨짐 — `OutboundMatchedItem`(`outboundApi.ts:37-47`)은 `shipped_quantity`/`quantity`/`logistics_status`를 필수로 선언하고 `OutboundPage/index.tsx:141-142`, `:176`이 이를 읽는다 | 기존 뮤테이션 팩토리·렌더링 경로 재사용 불가, `tsc` 실패 | 강제 응답은 기존 3분류 계약을 **필드까지 그대로** 반환한다(REQ-FORCE-016). M3에 필드 존재 검증 테스트를 두고, 프론트는 신규 응답 타입을 만들지 않는다 |
| R18 | 강제 실행 후 결과 갱신 방식에 따라 두 가지 상반된 손상이 생긴다 | 덧붙이기: 같은 행을 반복 반영해 실물 1회 출고가 여러 번 기록됨 / 통째 대체: 미선택 자격 행과 방금 생긴 수량초과 항목이 기록 없이 소실됨 | 병합 규칙을 적용한다(REQ-FORCE-024, 설계 결정 N) — 제출한 행만 제거하고 나머지는 유지하며 응답 항목은 각 목록에 추가한다. 슬롯 구조는 그대로이고 병합 함수 하나만 추가된다 |
| R19 (신규) | 어떤 대상의 행이 전부 `invalid_total`로 제거된 뒤 빈 그룹이 합산 수량 0으로 다음 단계에 전달되면, `0`이 한도 판정을 통과해 `shipped_at`이 찍히고 용량 0·이미 완료 대상에서는 `0 >= 0`으로 `"shipped"`까지 전이됨 | REQ-FORCE-007이 승계하지 않는다고 선언한 0 수량 완료 동작이 재진입하고 AC-FORCE-006/011이 깨짐 | 제거를 그룹화 이전에 수행하고 살아남은 행이 없는 대상은 그룹을 만들지 않는다(REQ-FORCE-008/011). `quantity=null` 대상과 이미 완전 출고된 대상에 0 수량 행만 보내는 케이스를 M3 필수 포함(AC-FORCE-011 (e)(f)) |
| R20 (신규) | 강제 경로에만 잠금을 넣으면 같은 파일 안에서 자매 경로와 관례가 갈린다 | 이후 독자가 불일치를 버그로 오인해 정상 경로에 잠금을 추가하거나, 반대로 강제 경로의 잠금을 제거할 수 있다 | 잠금 지점에 `@MX:NOTE`로 의도적 분기임과 그 근거(확정 스코프 Q6의 하드 룰 + 사람의 판단이 끼어드는 넓은 stale 창)를 남기고, 정상 경로 통일은 후속 과제 2임을 함께 기록한다. 정상 경로 무변경을 M4 회귀 조건과 DoD 체크 항목으로 고정한다 |

## MX 태그 계획 (mx_plan)

| 대상 | 태그 | 내용 |
|---|---|---|
| 강제 반영 진입점(신규) | `@MX:ANCHOR` | 정상 출고 경로와 **공유해야 하는 불변식 계약**의 유일한 보관처다 — 대상별 합산, 수량 한도, 음수·0·판독불가 거부, `shipped_quantity` 불감소, 임계 전이, 쓰기 대상 3필드 제한, 원자성. fan_in은 1로 프로젝트의 fan_in>=3 기준에는 미달하지만 ANCHOR의 목적인 "불변식 계약 고정"에 해당하므로 부여한다. 계약 본문에 "기존 경로와의 편차는 매칭 단계 대체와 0 수량 미승계 두 가지뿐"을 명시(REQ-FORCE-007) |
| 대상 행 잠금 구간(신규) | `@MX:NOTE` | **자매 함수와의 의도적 분기**를 기록한다 — 강제 경로는 `select_for_update()`로 대상을 잠근 뒤 그 값으로 한도를 판정하지만(REQ-FORCE-025), `_process_outbound_rows`는 잠금 없이 그대로 둔다. 근거: 확정 스코프 Q6가 "수량 한도 초과 불가"를 하드 룰로 정했고, 강제 경로는 후보 조회 → 담당자 선택 → 실행 사이에 사람의 판단이 끼어들어 stale 창이 구조적으로 넓다. 같은 파일의 `_apply_logistics_transition`(`:247`)이 이미 같은 관례를 쓴다는 점, 정상 경로 통일이 후속 과제 2라는 점, 잠금 순서를 대상 id 오름차순으로 고정해 교착을 피한다는 점을 함께 남겨 이후 독자가 불일치를 버그로 오인하지 않게 한다(R20) |
| 사전 게이트 구간 | `@MX:NOTE` | 대상 위반을 행 단위 강등이 아니라 요청 전체 HTTP 400으로 처리하는 이유(피커가 유효 대상만 제시하므로 무효 대상은 클라이언트 동기화 실패 신호)와, 주문 미해석 시 소유권 검사를 건너뛰면 안 되는 이유를 기록(설계 결정 L) |
| 잔여 stale read 구간 | `@MX:WARN` + `@MX:REASON` | 대상 행 잠금(REQ-FORCE-025)이 해소하지 **못하는** 부분을 명시한다 — 대상이 후보 조회 이후 `order_cancelled`가 되거나 `sku`를 잃으면 사전 게이트에 걸려 배치 전체가 400으로 거부되며, 이는 잠금과 무관하다. 정상 경로는 여전히 잠금이 없어 정상↔정상·정상↔강제 동시 처리가 보호되지 않는다는 사실도 REASON에 남기고 후속 과제 2를 참조로 건다 |
| 집계 재계산 미호출 지점 | `@MX:NOTE` | 주문 단위 집계를 갱신하지 않는 것은 의도적 결정이며 정상 출고 경로와의 동작 일치를 위한 것임을 기록. 입고 처리 경로는 호출한다는 대조 사실과 후속 과제 1을 남겨 이후 독자가 버그로 오인해 추가하지 않게 한다(설계 결정 E) |
| 0 수량 거부 지점 | `@MX:NOTE` | 정상 경로가 0을 매칭 이후 판정해 미국창고 완료 신호로 쓰는 것과 달리 강제 경로는 `invalid_total`로 거부한다는 의도적 분기를 기록 — 완료 신호 판정이 매칭된 LineItem의 `confirmed_distributor`에 의존하기 때문(설계 결정 I) |
| 후보 조회 뷰의 주문 해석 구간 | `@MX:NOTE` | `Order.name`이 유일하지 않으며 최저 `pk` 선점이 정상 경로 및 대상 게이트와 반드시 일치해야 하는 이유를 기록(설계 결정 B) |
| 후보 조회 뷰의 제외 필터 구간 | `@MX:NOTE` | `order_cancelled` 제외와 `sku is NULL` 제외의 서로 다른 근거를 기록 — 전자는 물류 대상 아님, 후자는 집계가 trackable 품목만 세어 "유령 출고"가 되는 것을 막기 위함(설계 결정 D) |
| `OutboundPage/index.tsx:24-28`의 기존 `@MX:ANCHOR` | 유지 | 변경하지 않는다. 컴포넌트 분할 시에도 export 이름과 모듈 해석 형태를 보존(R12) |
| 매칭 실패 섹션 전용 컴포넌트(신규) | `@MX:NOTE` | 공유 컴포넌트를 재사용하지 않고 분리한 이유(`cells: string[]` 계약으로는 체크박스·피커를 표현할 수 없고, 그 계약을 넓히면 같은 페이지의 성공·수량초과 섹션이 회귀 대상이 됨)와 시각적 일관성 제약을 기록(설계 결정 M) |
| 프론트 선택 상태 선언부 | `@MX:NOTE` | 선택 키가 `(주문 식별자, sku)`인 이유, 로컬 상태를 쓰는 이유, **서버 합산·응답 키는 대상 식별자로 다르다**는 사실을 기록(설계 결정 G/H/K) |
| 신규 테스트 파일 | 태그 없음 | 테스트 코드에는 MX 태그를 부여하지 않는다(기존 관례) |

구현(run) 단계에서 위 태그를 실제 코드에 부여하고, 실제 fan_in과 구조가 계획과 달라지면 이 표를
갱신한다.

## 완료 조건 (Definition of Ready → Done 게이트)

레이어별로 분리한다. 항목별 REQ/AC 배정은 `acceptance.md`의 품질 게이트 절이 단일 출처이며, 이
문서는 그것을 반복하지 않는다.

**백엔드**: `test_spec_016.py`가 `acceptance.md` 백엔드 게이트가 열거한 REQ 전량에 최소 1개 테스트를
매핑. `test_spec_015.py` 전량 무수정 통과. `makemigrations --check` 무변경. ruff **신규 에러 0**.

**프론트엔드**: colocate 테스트가 `acceptance.md` 프론트엔드 게이트가 열거한 REQ 전량에 최소 1개
테스트를 매핑. 기존 3개 테스트 파일 전량 통과. `tsc` / eslint **신규 에러 0**.

> **v1.0.5 정정.** (a) "공유 결과 섹션 컴포넌트 외부 호출부(`InboundPage` 3, `DailyReviewTab` 1)
> 통과" 항목을 삭제했다 — 그 호출부는 존재하지 않는다(설계 결정 M 정정 참조). (b) `ruff` /
> `tsc` / `eslint` "0 에러"를 "신규 에러 0"으로 고쳤다 — 이 저장소에는 이 SPEC과 무관한 기존
> 에러 베이스라인이 있어(ruff: `order/urls.py` E501 16건 등, tsc: `BookDetailPage.tsx` ·
> `ConfirmOrderTab.tsx` 등) 절대 0은 달성 불가능하며, 달성 가능한 기준은 이번 변경 파일에
> 에러를 추가하지 않는 것이다.

**공통**: `spec.md` Exclusions 21개 항목 전수 확인 — 특히 신규 컬럼·감사 테이블·권한 클래스·라우팅
변경·신규 사유 코드·공유 컴포넌트 시그니처 변경·부분 반영 경로가 diff에 존재하지 않을 것.

## 관련 참조 구현

- `backend/order/purchase_order_views.py:2810-3101` — 정상 출고 처리 로직. 강제 경로가 승계할 판정
  순서와 불변식의 원본. `:2999-3037`(0 수량 완료 신호)만 승계 대상이 아니다.
- `backend/order/purchase_order_views.py:2865-2901` — 음수·판독불가 거부 지점과 그룹 합산 지점.
- `backend/order/purchase_order_views.py:2912-2945` — `name__in` 배치 조회 + 최저 `pk` 선점 + 파이썬
  그룹핑.
- `backend/order/purchase_order_views.py:3026-3036`, `:3040-3050`, `:2954-2980` — 3분류 응답의 항목
  필드 구성. 강제 응답이 그대로 재사용한다.
- `backend/order/purchase_order_views.py:2671-2728` — 크로스-오더 읽기 전용 뷰 구조 선례.
- `backend/order/purchase_order_views.py:2316-2319`, `:2416-2420`, `:2526-2530` — 잘못된 입력에 대한
  `400 {"error": ...}` 관례.
- `backend/order/purchase_order_views.py:123-195` — 주문 단위 집계 재계산 함수. 호출하지 않는다.
- `backend/order/purchase_order_views.py:247` — `_apply_logistics_transition`의 `select_for_update()`.
  강제 경로 대상 행 잠금(REQ-FORCE-025)의 직접 선례이며, 이 파일에 잠금 관례가 이미 존재함을 보여
  주는 근거다.
- `backend/order/tests/test_spec_015.py:452` — 중간 실패 롤백(원자성) 테스트 선례.
- `backend/order/tests/test_spec_013.py:383-399`, `:842-851` — "호출하지 않음"을 spy로 pin하는 선례.
- `frontend/src/services/outboundApi.ts:37-76` — 3분류 응답의 클라이언트 타입. 강제 실행 함수가
  `OutboundProcessResponse`를 그대로 반환한다.
- `frontend/src/hooks/useOutboundQueries.ts:14-16`, `:20-35` — 뮤테이션 팩토리, 무효화 키, 토스트
  관례.
- `frontend/src/pages/OutboundPage/index.tsx:31-33`, `:42`, `:52` — 단일 결과 슬롯과 두 제출 경로의
  갱신 패턴. 강제 실행도 같은 슬롯을 같은 방식으로 갱신하되 넘기는 값이 병합 결과다(설계 결정 N).
- `frontend/src/pages/OutboundPage/index.tsx`의 `ResultSection` 로컬 함수 — 결과 섹션의 행 계약
  (`cells: string[]`). 참조만 하고 수정하지 않는다.
- `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx:28, :57, :64, :68-87, :155, :177-183,
  :243-249` — 로컬 선택 상태, 전체 선택, 일괄 적용, 선택 리셋, `aria-label` 관례.
- `frontend/src/pages/OrderDetailPage.tsx:52`, `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx:12`
  — 코드값 → 한국어 라벨 매핑(`LOGISTICS_STATUS_LABELS`) 관례.
- `frontend/src/features/order/hooks/useOrders.ts:11` — 파라미터를 포함한 쿼리 키 관례.
