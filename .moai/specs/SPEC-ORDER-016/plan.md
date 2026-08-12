---
id: SPEC-ORDER-016
document: plan
version: 1.0.3
status: draft
updated: 2026-08-12
---

# 구현 계획 — SPEC-ORDER-016 강제 출고 처리

`spec.md`의 요구사항(REQ-FORCE-001~024)을 구현하기 위한 작업 분해, 파일별 변경 계획, 기술적 접근,
리스크와 완화책, MX 태그 계획을 정리한다. 근거 자료는 `research.md`(파일:라인 인용 포함)를, 확정
스코프는 `interview.md`를 참조한다.

[HARD] 규범 진술의 단일 출처는 `spec.md`다. 이 문서는 그것을 **어떻게** 구현할지만 다루며, 요구사항을
재진술하지 않고 REQ ID로 참조한다.

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
  → 대상별 합산(008) → 한도 판정(009/010) → 반영·전이 → 응답 구성(016). 쓰기 대상 3필드 제한(013)과
  원자성(014) 포함.
  커버 REQ: 002, 007~014, 016, 017.
- **M3 (High) — 백엔드 테스트**: `test_spec_016.py` 신규 작성. AC-FORCE-002~014, 016~018 커버.
- **M4 (High) — 기존 백엔드 계약 회귀 확인**: `test_spec_015.py` 전량 재실행(REQ-FORCE-018).
- **M5 (Medium) — 프론트엔드 구현**: 서비스 함수·타입, 후보 조회 쿼리 훅 + 강제 실행 뮤테이션,
  매칭 실패 섹션 전용 컴포넌트, 선택 상태·피커·일괄 실행·결과 대체 배선, 한국어 라벨 매핑.
  커버 REQ: 001, 003(요청 횟수), 015, 019~024.
- **M6 (Medium) — 프론트엔드 테스트 + 회귀**: AC-FORCE-001, 003, 015, 019~022 커버. 기존 3개 테스트
  파일 + 공유 결과 섹션 컴포넌트의 4개 외부 호출부 테스트 전량 통과 확인.
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
| **EXISTING** | **`frontend/src/components/ResultSection.tsx`** | **변경하지 않는다**(설계 결정 M). 행 계약이 `cells: string[]`(`:8-27`)이라 체크박스·피커를 담을 수 없고, 출고 페이지 외부에 4개 호출부(`InboundPage/index.tsx:176`, `:194`, `:211`, `PurchaseOrders/tabs/DailyReviewTab.tsx:153`)가 있어 시그니처 변경 시 무관한 화면과 그 테스트가 전부 회귀 대상이 된다. 성공·수량초과 섹션은 계속 이 컴포넌트가 렌더한다. |
| NEW | `frontend/src/pages/OutboundPage/` 하위 매칭 실패 섹션 컴포넌트 | 매칭 실패 섹션 전용 렌더링 + 행별 선택 컨트롤 + 대상 선택 피커(REQ-FORCE-019~021). **구현 지시**: (a) 기존 공유 컴포넌트의 마크업을 참조해 섹션 제목·건수 표기·톤 클래스·컬럼 헤더 구성을 동일하게 재현하되 그 컴포넌트를 import하거나 수정하지 않는다. (b) 기존 테스트 훅 `data-testid="outbound-unmatched"`(`OutboundPage/index.tsx:148`)를 그대로 유지한다 — `index.test.tsx:218-223`이 이 훅으로 섹션을 찾는다. colocate 테스트 파일 동반. |
| NEW | `frontend/src/pages/OutboundPage/` 하위 라벨 매핑 모듈 | `logistics_status` 코드값 → 한국어 라벨 `Record`(`InboundPage/index.tsx:30-32` 방식). 매칭 실패 사유 라벨은 기존 `UNMATCHED_REASON_LABELS`를 재사용한다. **`purchase_status` 라벨 맵은 만들지 않는다** — 취소 품목은 후보에서 제외되고(REQ-FORCE-005) 후보 응답에 `purchase_status`가 실리지 않으므로(REQ-FORCE-006) 이 값은 섹션에 도달하지 않는다. |
| MODIFY | `frontend/src/pages/OutboundPage/index.tsx` | 매칭 실패 섹션 렌더링을 신규 전용 컴포넌트로 교체(성공·수량초과는 공유 컴포넌트 유지), 자격 판정·선택 상태(로컬 `useState`, 설계 결정 H)·후보 조회 배선·일괄 실행 컨트롤 연결. 강제 실행 성공 시 **기존 `result` 슬롯(`:31-33`)을 병합 결과로 `setResult`하고 선택 상태를 비운다**(REQ-FORCE-024, 설계 결정 N) — 슬롯 구조와 갱신 방식은 두 기존 제출 경로(`:42`, `:52`)와 같고, 넘기는 값만 응답 원본이 아니라 병합 결과다. **`export function OutboundPage` 명명과 폴더+`index.tsx` 모듈 해석을 유지해야 한다**(`router/index.tsx:129-135`, @MX:ANCHOR `OutboundPage/index.tsx:24-28`). |
| MODIFY | `frontend/src/pages/OutboundPage/index.test.tsx` | 신규 AC 테스트 추가. 최상위 `describe('OutboundPage — SPEC-ORDER-016', ...)` 아래 `describe('AC-FORCE-0NN: <한국어 시나리오>', ...)` 관례(`:76, 81, 154, 268, 317`). 기존 snake_case 금지 테스트(`:218-223`)는 수정하지 않고 그대로 통과해야 한다. |
| MODIFY | `frontend/src/services/outboundApi.test.ts` | 신규 함수의 요청 URL·payload·응답 매핑 테스트 추가. 기존 `ALL_UNMATCHED_REASONS` 5개 assert(`:67`)는 변경하지 않는다. |
| MODIFY | `frontend/src/hooks/useOutboundQueries.test.tsx` | 신규 훅 테스트 추가. `renderHook` + 로컬 `QueryClientProvider`(`retry: false`) 관례(`:36-41`). |
| EXISTING | `frontend/src/pages/InboundPage/index.tsx`, `frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx` | 변경 없음. 공유 컴포넌트 외부 호출부이므로 **회귀 검증 대상**으로만 다룬다. |
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
5. **한도 판정 및 반영**: `quantity`가 NULL이면 용량 0(SPEC-ORDER-015 설계 결정 B 승계). 초과 시
   미반영 + 대상 단위 `quantity_exceeded` 1건. 통과 시 `shipped_quantity` 증가, `shipped_at` 갱신,
   임계 도달 시 `logistics_status` 전이. 쓰기는 `bulk_update`로 일괄 수행하며, 이 세 필드 외에는
   어떤 필드도 쓰지 않는다(REQ-FORCE-013) — 주문 집계 재계산 함수도 호출하지 않으며, 이 "호출하지
   않음"은 `test_spec_013.py:383-399`, `:842-851`의 선례(`patch(...)` + `assert_not_called()`)와
   동일한 방식으로 테스트에 pin한다.
6. **원자성**: 요청 전체를 `transaction.atomic()`으로 감싼다(REQ-FORCE-014). 고장 주입 테스트는
   `test_spec_015.py:452`의 중간 실패 롤백 테스트와 같은 방식으로 작성한다.
7. **응답 구성**: 기존 3분류 응답 계약을 필드까지 그대로 재사용한다(REQ-FORCE-016). matched /
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
| R8 | 락 부재로 인한 stale read 창 확대(@MX:WARN `:2802-2809`) | 두 가지 실패 모드가 있다 | (a) `shipped_quantity`만 낡은 경우 → 해당 대상만 `quantity_exceeded`가 되는 안전 실패이며 같은 요청의 다른 대상은 정상 반영된다. (b) 대상이 조회 이후 `order_cancelled`가 되었거나 `sku`를 잃은 경우 → 사전 게이트에 걸려 **요청 전체가 HTTP 400으로 거부**되어 함께 제출한 유효한 행들도 모두 반영되지 않는다(설계 결정 L). 일괄 실행 사용자에게 (b)는 체감이 크게 다르므로 에러 토스트만으로 끝내지 말고 담당자가 결과를 다시 조회해 재시도해야 함을 인지시킨다. 락 도입·부분 반영 정책은 후속 과제 2 |
| R9 | 한 주문에 동일 SKU LineItem 복수 존재 가능(`models.py:235`) | 피커에서 제목·SKU만으로 구분 불가 | 후보의 표시 키를 안정적 식별자로 삼는다(REQ-FORCE-006) |
| R10 | `unmatched` 항목에 `line_item_id`가 없음(`:2954-2980`) | 선택 상태 키 부재 | `(주문 식별자, sku)` 쌍을 선택 키로 사용(설계 결정 G) |
| R11 | 주문 집계 미갱신이라는 선행 불일치 | 강제 경로만 고치면 두 경로가 서로 다른 부수효과를 냄 | 현행 동작 답습(설계 결정 E). REQ-FORCE-013으로 규범화하고 spy로 pin |
| R12 | `OutboundPage` named export + 폴더 모듈 해석에 라우터가 의존(@MX:ANCHOR `index.tsx:24-28`) | 컴포넌트 분할 중 export 형태를 바꾸면 `/outbound` 라우트가 깨짐 | 진입점 파일과 export 이름 유지, 신규 컴포넌트는 형제 파일로 배치 |
| R13 | 공유 결과 섹션 컴포넌트의 행 계약이 `cells: string[]`이며 외부 호출부 4곳 존재 | 시그니처 확장 시 무관한 두 화면과 그 테스트가 회귀 대상 | 공유 컴포넌트를 수정하지 않고 매칭 실패 섹션만 전용 컴포넌트로 분리(설계 결정 M). 4개 외부 호출부 테스트를 M6 회귀 대상으로 명시 |
| R14 | 0 수량 행이 `line_item_not_found`로 보고되어 강제 대상이 될 수 있음(`:2969-2980`이 `:2999`보다 먼저 실행) | 임의 대상의 `shipped_quantity`를 `quantity`까지 채우는 미요구 동작 | 자격 조건에 양수 수량 포함(REQ-FORCE-001), 서버에서도 0을 `invalid_total`로 거부(REQ-FORCE-011). 미국창고 대상에 0을 넣는 케이스를 M3 필수 포함 |
| R15 | 두 매칭 실패 행이 같은 대상을 지정하면 각각은 한도를 통과하고 합산은 초과 | "수량 한도 우회 없음" 배제 조항 무력화 | 대상 식별자 기준 합산 후 1회 판정(REQ-FORCE-008). 개별 통과·합산 초과 시나리오를 M3 필수 포함 |
| R16 | 대상이 다른 주문 소속이면 정상 경로가 금지하는 교차 주문 SKU 차용이 강제 경로로 재현됨 | 무관한 주문의 품목에 출고 수량이 기록됨 | 게이트에서 소유권 검증 후 요청 전체 400(REQ-FORCE-002). 교차 주문 지정과 주문 미해석 케이스를 M3 필수 포함 |
| R17 (신규) | 강제 응답이 기존 클라이언트 타입보다 좁으면 재사용 경로가 깨짐 — `OutboundMatchedItem`(`outboundApi.ts:37-47`)은 `shipped_quantity`/`quantity`/`logistics_status`를 필수로 선언하고 `OutboundPage/index.tsx:141-142`, `:176`이 이를 읽는다 | 기존 뮤테이션 팩토리·렌더링 경로 재사용 불가, `tsc` 실패 | 강제 응답은 기존 3분류 계약을 **필드까지 그대로** 반환한다(REQ-FORCE-016). M3에 필드 존재 검증 테스트를 두고, 프론트는 신규 응답 타입을 만들지 않는다 |
| R18 | 강제 실행 후 결과 갱신 방식에 따라 두 가지 상반된 손상이 생긴다 | 덧붙이기: 같은 행을 반복 반영해 실물 1회 출고가 여러 번 기록됨 / 통째 대체: 미선택 자격 행과 방금 생긴 수량초과 항목이 기록 없이 소실됨 | 병합 규칙을 적용한다(REQ-FORCE-024, 설계 결정 N) — 제출한 행만 제거하고 나머지는 유지하며 응답 항목은 각 목록에 추가한다. 슬롯 구조는 그대로이고 병합 함수 하나만 추가된다 |
| R19 (신규) | 어떤 대상의 행이 전부 `invalid_total`로 제거된 뒤 빈 그룹이 합산 수량 0으로 다음 단계에 전달되면, `0`이 한도 판정을 통과해 `shipped_at`이 찍히고 용량 0·이미 완료 대상에서는 `0 >= 0`으로 `"shipped"`까지 전이됨 | REQ-FORCE-007이 승계하지 않는다고 선언한 0 수량 완료 동작이 재진입하고 AC-FORCE-006/011이 깨짐 | 제거를 그룹화 이전에 수행하고 살아남은 행이 없는 대상은 그룹을 만들지 않는다(REQ-FORCE-008/011). `quantity=null` 대상과 이미 완전 출고된 대상에 0 수량 행만 보내는 케이스를 M3 필수 포함(AC-FORCE-011 (e)(f)) |

## MX 태그 계획 (mx_plan)

| 대상 | 태그 | 내용 |
|---|---|---|
| 강제 반영 진입점(신규) | `@MX:ANCHOR` | 정상 출고 경로와 **공유해야 하는 불변식 계약**의 유일한 보관처다 — 대상별 합산, 수량 한도, 음수·0·판독불가 거부, `shipped_quantity` 불감소, 임계 전이, 쓰기 대상 3필드 제한, 원자성. fan_in은 1로 프로젝트의 fan_in>=3 기준에는 미달하지만 ANCHOR의 목적인 "불변식 계약 고정"에 해당하므로 부여한다. 계약 본문에 "기존 경로와의 편차는 매칭 단계 대체와 0 수량 미승계 두 가지뿐"을 명시(REQ-FORCE-007) |
| 사전 게이트 구간 | `@MX:NOTE` | 대상 위반을 행 단위 강등이 아니라 요청 전체 HTTP 400으로 처리하는 이유(피커가 유효 대상만 제시하므로 무효 대상은 클라이언트 동기화 실패 신호)와, 주문 미해석 시 소유권 검사를 건너뛰면 안 되는 이유를 기록(설계 결정 L) |
| 락 없는 갱신 구간 | `@MX:WARN` + `@MX:REASON` | 대상 행 잠금이 없고 강제 경로는 stale read 창이 더 넓다. REASON에 두 실패 모드(대상만 초과 보고 / 게이트에서 배치 전체 400)를 함께 기록하고, 같은 파일에 `select_for_update()`를 쓰는 경로(`:247`)가 공존한다는 사실을 참조로 남긴다 |
| 집계 재계산 미호출 지점 | `@MX:NOTE` | 주문 단위 집계를 갱신하지 않는 것은 의도적 결정이며 정상 출고 경로와의 동작 일치를 위한 것임을 기록. 입고 처리 경로는 호출한다는 대조 사실과 후속 과제 1을 남겨 이후 독자가 버그로 오인해 추가하지 않게 한다(설계 결정 E) |
| 0 수량 거부 지점 | `@MX:NOTE` | 정상 경로가 0을 매칭 이후 판정해 미국창고 완료 신호로 쓰는 것과 달리 강제 경로는 `invalid_total`로 거부한다는 의도적 분기를 기록 — 완료 신호 판정이 매칭된 LineItem의 `confirmed_distributor`에 의존하기 때문(설계 결정 I) |
| 후보 조회 뷰의 주문 해석 구간 | `@MX:NOTE` | `Order.name`이 유일하지 않으며 최저 `pk` 선점이 정상 경로 및 대상 게이트와 반드시 일치해야 하는 이유를 기록(설계 결정 B) |
| 후보 조회 뷰의 제외 필터 구간 | `@MX:NOTE` | `order_cancelled` 제외와 `sku is NULL` 제외의 서로 다른 근거를 기록 — 전자는 물류 대상 아님, 후자는 집계가 trackable 품목만 세어 "유령 출고"가 되는 것을 막기 위함(설계 결정 D) |
| `OutboundPage/index.tsx:24-28`의 기존 `@MX:ANCHOR` | 유지 | 변경하지 않는다. 컴포넌트 분할 시에도 export 이름과 모듈 해석 형태를 보존(R12) |
| 매칭 실패 섹션 전용 컴포넌트(신규) | `@MX:NOTE` | 공유 컴포넌트를 재사용하지 않고 분리한 이유(`cells: string[]` 계약으로는 체크박스·피커 표현 불가 + 외부 호출부 4곳 회귀 위험)와 시각적 일관성 제약을 기록(설계 결정 M) |
| 프론트 선택 상태 선언부 | `@MX:NOTE` | 선택 키가 `(주문 식별자, sku)`인 이유, 로컬 상태를 쓰는 이유, **서버 합산·응답 키는 대상 식별자로 다르다**는 사실을 기록(설계 결정 G/H/K) |
| 신규 테스트 파일 | 태그 없음 | 테스트 코드에는 MX 태그를 부여하지 않는다(기존 관례) |

구현(run) 단계에서 위 태그를 실제 코드에 부여하고, 실제 fan_in과 구조가 계획과 달라지면 이 표를
갱신한다.

## 완료 조건 (Definition of Ready → Done 게이트)

레이어별로 분리한다. 항목별 REQ/AC 배정은 `acceptance.md`의 품질 게이트 절이 단일 출처이며, 이
문서는 그것을 반복하지 않는다.

**백엔드**: `test_spec_016.py`가 `acceptance.md` 백엔드 게이트가 열거한 REQ 전량에 최소 1개 테스트를
매핑. `test_spec_015.py` 전량 무수정 통과. `makemigrations --check` 무변경. ruff 0 에러.

**프론트엔드**: colocate 테스트가 `acceptance.md` 프론트엔드 게이트가 열거한 REQ 전량에 최소 1개
테스트를 매핑. 기존 3개 테스트 파일 전량 통과. 공유 결과 섹션 컴포넌트 외부 호출부(`InboundPage` 3
호출부, `DailyReviewTab` 1 호출부) 및 그 테스트 전량 통과. `tsc` / eslint 0 에러.

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
- `backend/order/tests/test_spec_015.py:452` — 중간 실패 롤백(원자성) 테스트 선례.
- `backend/order/tests/test_spec_013.py:383-399`, `:842-851` — "호출하지 않음"을 spy로 pin하는 선례.
- `frontend/src/services/outboundApi.ts:37-76` — 3분류 응답의 클라이언트 타입. 강제 실행 함수가
  `OutboundProcessResponse`를 그대로 반환한다.
- `frontend/src/hooks/useOutboundQueries.ts:14-16`, `:20-35` — 뮤테이션 팩토리, 무효화 키, 토스트
  관례.
- `frontend/src/pages/OutboundPage/index.tsx:31-33`, `:42`, `:52` — 단일 결과 슬롯과 두 제출 경로의
  갱신 패턴. 강제 실행도 같은 슬롯을 같은 방식으로 갱신하되 넘기는 값이 병합 결과다(설계 결정 N).
- `frontend/src/components/ResultSection.tsx:8-27` — 공유 결과 섹션 컴포넌트의 행 계약. 참조만 하고
  수정하지 않는다.
- `frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx:28, :57, :64, :68-87, :155, :177-183,
  :243-249` — 로컬 선택 상태, 전체 선택, 일괄 적용, 선택 리셋, `aria-label` 관례.
- `frontend/src/pages/InboundPage/index.tsx:30-32` — 코드값 → 한국어 라벨 매핑 관례.
- `frontend/src/features/order/hooks/useOrders.ts:11` — 파라미터를 포함한 쿼리 키 관례.
