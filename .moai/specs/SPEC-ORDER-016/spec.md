---
id: SPEC-ORDER-016
version: 1.0.4
status: draft
created_at: 2026-08-12
updated: 2026-08-12
author: ggajo
priority: High
issue_number: 18
labels: [order, logistics, outbound, force]
---

# 강제 출고 처리 — SKU 불일치 행의 대상 지정 출고 반영

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-12 | ggajo | 최초 작성 — 사용자 인터뷰 2라운드(`interview.md`)로 확정된 스코프(매칭 실패 섹션 한정 노출, `line_item_not_found` 사유만 강제 대상, 대상 LineItem 사용자 명시 지정, 행별 체크박스 + 일괄 실행, 수량 한도 유지, 신규 컬럼·이력 테이블 없음)를 EARS 형식으로 formalize. SPEC-ORDER-015가 구현한 출고 처리를 확장하며, 그 요구사항 계열(REQ-OUTBOUND-\*)은 재사용하지 않고 신규 `REQ-FORCE-*` 계열을 사용한다. 설계 결정 A~H는 `research.md`가 파일:라인 인용과 함께 확정한 제약에서 도출했으며, 그 조사 내용을 본 문서에 재복제하지 않는다. frontmatter는 SPEC-ORDER-015 v1.0.1의 MP-3 수정 결과에 따라 `created`가 아닌 `created_at`을 사용한다. |
| 1.0.1 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 1, FAIL, 0.62) 후속 정리 — critical 1건 + major 6건 + minor 8건 수정. **D1(critical)**: `total == 0` 행이 `line_item_not_found`로 보고되어 강제 대상이 될 수 있던 결함 수정(자격 조건에 양수 수량 추가, 강제 경로의 0은 `invalid_total` 거부, REQ의 "non-positive rejection" 오기 정정, 설계 결정 I 신설). **D4**: 동일 대상 지정 행의 합산 규칙 신설(설계 결정 K). **D3**: 대상 소유권 검증 후 요청 전체 HTTP 400(설계 결정 L). **D2**: 자격 판정을 프론트엔드 책임으로 재정의(설계 결정 J). **D5**: 공유 결과 섹션 컴포넌트 무변경 + 매칭 실패 섹션 전용 컴포넌트 분리(설계 결정 M). **D6**: 품질 게이트 레이어 분리. **D7**: 렌더링 금지 범위를 상태·사유 코드값으로 축소. minor D8~D15: 응답 항목 스키마 명시, 019/019a 관할 계층 명시, EARS 순도 정리, `Traces:` 문서 간 정렬, AC-FORCE-001 재작성, disclaimer 완화, 고장 주입 방식 명시, tie-break를 최저 `pk`로 정정. REQ 33→39, AC 34→40. |
| 1.0.2 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 2, FAIL, 0.76) 후속 정리 — iteration 1의 15개 결함은 전부 종결 확인되었고(critical D1 수정은 소스 대조로 사실 정확성까지 검증됨), 그 수정이 파생시킨 신규 결함 4건과 구조적 과잉 명세 1건을 해소했다. **N1**: AC-FORCE-001이 "다른 사유 코드 행은 반영에 도달하지 않는다"고 단언해 설계 결정 J(그런 행도 대상만 유효하면 반영된다)와 정면 충돌했고, 사유 코드가 payload에 없어 선언된 `[BE]` 레이어에서 검증 불가능했다 — 자격 판정을 순수 프론트엔드 관측(자격 행에만 컨트롤이 렌더된다)으로 재정의하고 `[FE]`로 재배치, 서버 측 사유 게이트를 암시하는 문구 전면 삭제. **N2**: 합산된 **matched** 항목의 입도와 필드값이 미정의였고(병합 행은 SKU가 서로 다름), AC의 행 단위 보고 서술이 REQ의 대상 단위 보고와 모순 — 응답을 **지정 대상 단위**로 확정하고 병합 항목의 `sku`는 **대상 LineItem 자신의 `sku`**, `total`은 합산량, `name`은 소유권 검증으로 단일하게 결정됨을 명시. "합산 수량"을 1개 행 경우까지 정의. **N3**: 명시한 항목 스키마가 기존 클라이언트 타입(`outboundApi.ts:37-65`이 `shipped_quantity`/`quantity`/`logistics_status`를 필수로 선언)보다 좁아, plan.md가 지시한 기존 뮤테이션 팩토리 재사용과 타입이 어긋났다 — 강제 응답은 **기존 3분류 응답 계약을 필드까지 그대로 재사용**하는 것으로 확정. **N4**: 실행 후 상태가 모호해 처리된 행을 재차 강제할 수 있는 해석이 존재 — 성공 시 강제 응답이 기존 결과 표시 슬롯을 **대체**하도록 확정(두 기존 제출 경로와 동일). **N12(구조)**: 39 REQ / 40 AC는 두 엔드포인트와 UI 섹션 하나에 대한 과잉 명세이며 3~4중 중복이 이번 회차의 N1·N2·N10을 만든 원인 — **24 REQ / 22 AC로 통합**(상세는 아래 "v1.0.2 통합 내역"). minor N5~N11/N13/N14: 주문 미해석 케이스를 게이트에 추가, 구조 오류 행 판정을 게이트에 편입, 빈 요청 동작 확정, "우회하는 규칙 하나뿐"을 두 개의 실제 편차 열거로 교체, 접합절 분리, 도달 불가능한 `purchase_status` 라벨링 요구 삭제, 후속 과제 2·R8에 배치 전체 400 실패 모드 반영, `useOrders.ts` 경로 정정, 설계 결정 L의 근거를 클라이언트 동기화 실패 논거로 재정립. 알파벳 접미사 체계를 폐지하고 001~024 연속 번호로 재부여. |

| 1.0.3 | 2026-08-12 | ggajo | plan-auditor 리뷰(iteration 3, FAIL, 0.80, max_iterations 도달) 이후 사용자가 **major 2건만 수정하고 minor 8건(F3~F10)은 의도적으로 보류**하기로 결정 — 이번 수정 이후 plan-auditor 재실행 불필요. **F1(major)**: 어떤 대상의 모든 행이 REQ-FORCE-011로 제외되면 그 대상의 합산 수량이 0이 되고, 그 0이 REQ-FORCE-009의 조건절을 만족해 **쓰기를 강제**하는 구멍이 있었다 — `shipped_at`이 찍히고, `quantity`가 null(용량 0)이거나 이미 완료된 대상에서는 `0 >= 0`이 성립해 `logistics_status="shipped"`까지 전이되어, REQ-FORCE-007이 승계하지 않는다고 선언한 0 수량 완료 동작이 옆문으로 재진입했다. AC-FORCE-006("L3를 전혀 변경하지 않는다")·AC-FORCE-011("LA와 LB는 무변경")이 자기 픽스처로 이 모순을 이미 구성하고 있었다. 수정: 제외를 **그룹화 이전**에 수행함을 REQ-FORCE-011과 REQ-FORCE-008 본문에 명시(정상 경로가 `:2865-2898`에서 행을 거부한 뒤 `:2900-2901`의 합산에 도달하지 않는 것과 동일한 순서), 살아남은 행이 없는 대상은 **그룹 자체가 형성되지 않아** 판정·쓰기·보고 어디에도 등장하지 않음을 규범화, 그리고 "자격이 양수 수량을 요구하고 비양수·판독불가 행은 그룹화 이전에 제거되므로 평가되는 모든 그룹의 합산 수량은 최소 1이며 0은 구조적으로 도달 불가"라는 불변식을 REQ-FORCE-008에 명시. REQ-FORCE-009의 트리거는 이 불변식을 참조하도록 문구를 조정했고, AC-FORCE-006/011은 "그룹이 만들어지지만 아무것도 쓰지 않는다"가 아니라 "그룹이 만들어지지 않는다"를 주장하도록 재작성하면서 AC-FORCE-011 픽스처에 `quantity=null` 대상과 이미 완전 출고된 대상 두 변형을 추가해 `0 >= 0` 전이 경로를 테스트로 봉쇄했다. **F2(major)**: 결과 슬롯 통째 대체가 담당자가 **선택하지 않은** 자격 행과 이번 실행이 방금 만들어낸 수량초과 항목까지 기록 없이 지웠다(5건 중 2건 처리 시 나머지 3건 소실). 수정: REQ-FORCE-024를 병합 규칙(제출한 행만 `(주문 식별자, sku)` 키로 제거 / 미제출 행 유지 및 선택 가능 / 강제 응답의 성공·수량초과 항목을 대응 목록에 추가 / 세 건수 재계산 / 선택 리셋)으로 재작성하고, 설계 결정 N에 기각한 대안 2건과 수용된 대가를 기록, AC-FORCE-022를 3행 픽스처에서 네 결과(처리된 행 소멸 / 미선택 행 잔존 및 선택 가능 / 수량초과 항목 가시 / 건수 일치)를 모두 주장하도록 재작성. **보류(사용자 결정)**: F3(REQ-FORCE-007의 "exactly two deviations" — 구조 오류 행의 400 처리가 세 번째 편차), F4(EARS 단일 패턴 순도 — 3회 반복 지적된 정체 결함), F5(AC-FORCE-001의 "five rows" 오기), F6(AC-FORCE-005가 REQ-FORCE-006의 속성 집합 미주장), F7(REQ-FORCE-015의 "entire set" vs REQ-FORCE-023), F8("structurally malformed" 미정의), F9(읽기 전용성·시각적 일관성·임계 미달 무변경의 검증 부재), F10(인용 범위 시작점 off-by-one 3건). 이들은 구현을 차단하지 않는 minor 항목으로 판단되어 이번 범위에서 다루지 않는다. REQ/AC 개수와 번호는 변경 없음(24 REQ / 22 AC). |

| 1.0.4 | 2026-08-12 | ggajo | 사용자 스코프 변경 — 보류했던 리스크를 재검토한 뒤 **강제 경로에 한해 행 단위 락을 도입**하기로 결정. 근거: (1) 이 기능의 확정 스코프가 "수량 한도 초과 불가"(Q6)를 하드 룰로 정했는데, 락이 없으면 같은 LineItem을 겨냥한 두 강제 요청이 같은 낡은 `shipped_quantity`를 읽고 각자 한도 검사를 통과해 합계가 `quantity`를 넘긴다 — 오용이 아니라 평범한 동시 사용으로 확정 규칙이 깨진다. (2) 강제 경로의 stale read 창은 구조적으로 더 넓다: 정상 경로는 한 요청 안에서 읽기·판정·쓰기가 연달아 일어나지만, 강제 경로는 후보 조회 → 담당자의 대상 선택 → 실행 사이에 사람의 판단이 끼어들어 한도 검사가 읽는 값이 수 초~수 분 낡을 수 있다. (3) 선례가 같은 모듈에 이미 있다(`_apply_logistics_transition`의 `select_for_update()`, `purchase_order_views.py:247`) — 한 파일에 두 관례가 이미 공존하므로 새 패턴이 아니다. (4) 비용이 낮다: 기존 대상 행 SELECT에 잠금을 붙이는 것이라 쿼리가 추가되지 않는다. 변경 내용 — REQ-FORCE-025 신설(모듈 3), AC-FORCE-023 신설(`[BE]`, 동시 실행 2건이 합산으로 한도를 넘기지 못함을 검증), Exclusions의 "동시성 락 도입 없음" 항목을 "강제 경로에 한정" 항목으로 교체, 후속 과제 2를 정상 경로 잔여 격차로 축소, 설계 결정 O 신설. **정상 경로(`_process_outbound_rows`)는 변경하지 않으며 두 경로의 락 관례 통일은 여전히 범위 밖이다.** 아울러 사용자 결정에 따라 후속 과제 1(주문 집계 미갱신)은 정상·강제 두 경로를 **함께** 다루는 별도 SPEC에서 처리함을 명시했다. REQ 24→25, AC 22→23, 모듈 수 5 유지. |

### v1.0.2 통합 내역 (N12)

| 삭제/병합된 v1.0.1 항목 | 처리 | 사유 |
|---|---|---|
| REQ-FORCE-001a, 001b | REQ-FORCE-019(렌더링 규칙)에 흡수 | 둘 다 "비자격 행에는 컨트롤이 없다"의 부분집합이었다. 자격 정의(REQ-FORCE-001) 하나와 렌더링 규칙 하나로 충분하다 |
| REQ-FORCE-003 | REQ-FORCE-002(게이트)에 흡수 | "대상을 실어야 한다"는 "대상이 없으면 거부한다"를 넘는 검증 가능한 내용이 없었다 |
| REQ-FORCE-002a, 025 | Exclusions 항목으로만 유지 | 전적으로 "아무것도 바뀌지 않는다" 진술이며 Exclusions가 이미 규범이다 |
| REQ-FORCE-010b (임계 미달 시 상태 무변경) | REQ-FORCE-009의 조건절 + 인수 시나리오로 흡수 | "임계 도달 시 전이한다"가 미달 시 변경을 허용하지 않는다 |
| REQ-FORCE-013a, 014 | REQ-FORCE-013(쓰기 대상 제한)으로 통합 | "신규 LineItem 없음", "sku/title/quantity 불변", "Order 집계 불변"을 "이 세 필드 외에는 아무것도 쓰지 않는다" 하나로 표현하는 편이 더 강하고 단일 테스트로 검증된다 |
| REQ-FORCE-008의 정렬 결정성 | REQ-FORCE-006(후보 응답 계약)으로 이동 | 정렬은 응답 형태의 일부이지 읽기 전용성과 다른 사안이다 |
| REQ-FORCE-008의 읽기 전용성 | Exclusions 항목으로 이동 | |
| REQ-FORCE-019a | `plan.md`로 이동 | TypeScript optional 지정 지시는 구현 계획 사항이다 |
| REQ-FORCE-020b의 테스트 훅 유지 조항 | `plan.md`로 이동 | `data-testid` 속성 지정은 구현 지시다 |
| REQ-FORCE-020b의 시각적 일관성 조항 | 설계 결정 M + `plan.md`로 이동 | |
| REQ-FORCE-012의 미국창고 완료 신호 미적용 조항 | REQ-FORCE-007의 편차 열거로 이동 | 조건절에 접합된 무조건 의무였다(N7) |
| 순수 재진술 AC 12건 | 삭제 | AC는 요구사항이 이미 문장으로 말하지 않은 **관측 가능한 결과**를 제시해야 한다. 남긴 22개 AC는 각각 구체 픽스처 조건·경계값·차등 비교를 담으며, 일부는 2개 REQ를 함께 검증한다 |

---

## 문제 정의

SPEC-ORDER-015가 제공하는 `/outbound` 출고 처리는 제출된 행을 `matched` / `unmatched` /
`quantity_exceeded` 3분류로 반환한다. 이 중 `unmatched`(매칭 실패)의 대다수는 "주문은 정확히
찾았지만 그 주문 안에 입력한 SKU를 가진 품목이 없다"는 상황(사유 코드
`line_item_not_found`)이다.

현장에서는 이 상황이 데이터 오류가 아니라 **정상적인 운영 현실**인 경우가 많다. 출고 목록의
SKU와 주문에 기록된 SKU가 서로 다른 표기를 쓰거나(번들/세트 구성, 개정판 교체, SKU 미기입),
실물은 분명히 그 주문의 특정 품목으로 나갔는데 자동 매칭만 실패하는 것이다. 현재는 이런 행을
반영할 수단이 전혀 없어 담당자가 주문 상세 화면을 따로 열어 수작업으로 처리해야 하며, 그
경로는 출고 수량 누적/상태 전이 규칙을 거치지 않는다.

동시에, 이 "강제" 기능은 잘못 설계하면 SPEC-ORDER-015가 명시적으로 배제한 기능(출고
취소/되돌리기, 수량 한도 우회)을 뒷문으로 재도입할 수 있다. 따라서 이 SPEC의 핵심은 "무엇을
우회하는가"가 아니라 **"무엇을 절대 우회하지 않는가"**를 규정하는 데 있다.

## 솔루션 개요

1. 출고 처리 결과의 매칭 실패 섹션에서, 사유가 `line_item_not_found`이면서 요청 수량이 0보다
   큰 행에 한해 강제 출고 처리를 제공한다. 그 외 사유 코드, 0 이하 수량 행, 수량초과 섹션은
   기존 동작 그대로 유지된다.
2. 강제 대상 행마다 담당자가 **해당 주문의 품목 목록에서 반영 대상을 직접 고른다.** 자동
   추론·대체 규칙·신규 품목 생성은 존재하지 않으며, 주문의 원본 구성은 변경되지 않는다.
3. 피커에 표시할 후보 목록은 여러 주문분을 **한 번의 요청으로** 받아오는 읽기 전용 조회로
   조달한다(설계 결정 A).
4. 강제 실행은 행별 선택 + 단일 일괄 실행이며, 선택된 모든 행이 한 번의 요청으로 전송된다.
   성공하면 그 결과가 기존 결과 표시를 대체한다.
5. 강제 경로는 기존 출고 경로와 **정확히 두 가지**만 다르다 — (a) `(order, sku)` 매칭 단계가
   사용자 지정으로 대체되고, (b) 매칭 이후의 0 수량 처리(미국창고 완료 신호)를 승계하지
   않는다. 그 밖의 규칙(음수·판독불가 사전 거부, 키 기준 합산, 수량 한도, `shipped_quantity`
   불감소, 임계 전이, 원자성)은 전부 동일하게 적용된다.
6. 신규 모델 컬럼·마이그레이션·감사 로그 테이블은 없다. 기록되는 필드는 기존
   `shipped_quantity` / `shipped_at` / `logistics_status` 뿐이다.

요구사항 본문(EARS)은 관찰 가능한 동작(WHAT)과 계약만 규정한다. 아래 "설계 결정" 절은 각
판단의 **근거가 된 기존 코드·테스트**를 `file:line`으로 인용한다 — 이는 결정을 검증 가능하게
만드는 증거이며 구현 지시가 아니다. 구현 순서, 재사용 대상 패턴, 신규 코드의 배치는
`plan.md`를, 조사 전문은 `research.md`를 참조한다.

## 범위 — 델타

이 SPEC은 기존 기능 위에 얹는 브라운필드 변경이다. 동작 단위 델타는 다음과 같다.

| 마커 | 대상 동작 | 내용 |
|---|---|---|
| [EXISTING] | 출고 처리 3분류 판정·반영 로직 | 변경 없음. 강제 경로가 이 로직의 불변식을 상속한다(REQ-FORCE-007). |
| [EXISTING] | 출고 처리 엔드포인트 2개의 요청·응답 계약 | 변경 없음. 후보 목록을 그 응답에 동봉하지 않는다(설계 결정 A, REQ-FORCE-018). |
| [EXISTING] | 3분류 응답의 항목 필드 구성 | 변경 없음. 강제 응답이 이 계약을 그대로 재사용한다(REQ-FORCE-016). |
| [EXISTING] | `quantity_exceeded` 섹션, 결과 섹션 공유 렌더링 컴포넌트, `/outbound` 라우팅·사이드바 | 변경 없음(Exclusions). |
| [EXISTING] | 물류 상태 enum, 매칭 실패 사유 코드 5종 | 신규 값 추가 없음. |
| [NEW] | 강제 후보 목록 배치 조회 | 주문 식별자 목록을 한 요청으로 받아 주문별 반영 가능 품목 목록을 반환하는 읽기 전용 조회(REQ-FORCE-003~006). |
| [NEW] | 강제 출고 반영 | 대상 LineItem이 명시된 행 목록을 한 요청으로 받아, 사전 게이트를 통과한 뒤 대상별 합산으로 출고 수량을 누적하는 처리(REQ-FORCE-002, 007~018). |
| [NEW] | 매칭 실패 섹션 전용 렌더링 컴포넌트 | 선택 컨트롤 + 대상 선택기를 담을 수 있는 전용 컴포넌트(설계 결정 M, REQ-FORCE-019~021). |
| [MODIFY] | 출고 페이지의 매칭 실패 섹션 배선 | 자격 판정, 선택 상태, 일괄 실행, 결과 대체를 페이지에 연결한다(REQ-FORCE-022~024). |

파일 단위 변경 대상과 마커는 `plan.md`에 정리되어 있다.

## 설계 결정

### 결정 A — 후보 목록은 별도 배치 엔드포인트로 조달한다

피커가 필요로 하는 "주문별 품목 목록"을 기존 출고 처리 응답의 `unmatched` payload에 동봉하는
방식은 채택하지 않는다. 두 가지 확정된 제약 때문이다.

첫째, 기존 쿼리 카운트 테스트(`backend/order/tests/test_spec_015.py:1143-1153`)가 출고 처리
전체를 `<= 6`(10그룹 전부 매칭) / `<= 4`(전부 매칭 실패)로 고정하고 있으며 현재 실측 여유는
각각 1쿼리뿐이다. 처리 함수 안에서 후보를 함께 조회하면 그 경계에 정확히 닿는다.

둘째, `test_both_endpoints_return_identical_results_for_equivalent_input`
(`test_spec_015.py:746`)은 두 엔드포인트의 `unmatched` 리스트를 **딕셔너리 전체 동등성**으로
비교한다. 비결정적 값이 섞이면 즉시 깨진다.

따라서 후보 조회는 **주문 식별자 목록을 한 요청으로 받는 읽기 전용 조회**로 분리한다. 원격 DB
왕복 비용(요청당 약 130ms, `backend/order/purchase_order_views.py:2790-2801`)을 고려할 때 행
단위·주문 단위로 개별 요청을 보내는 방식은 명시적 안티패턴이며 Exclusions에 포함한다.

### 결정 B — 주문 해석은 정상 경로와 동일한 tie-break를 쓴다

`Order.name`은 유일하지 않다(유일 제약은 `(shopify_order_id, store_type)`). 정상 출고 경로는
동명 주문 충돌을 `pk` 오름차순 선점으로 해소한다(`purchase_order_views.py:2912-2925`, 테스트
`test_spec_015.py:1166-1199`). 여기서 "oldest"는 생성 일시가 아니라 **최저 `pk`**를 뜻한다 —
백필·임포트된 주문에서는 두 순서가 일치하지 않을 수 있다.

후보 조회가 다른 tie-break를 쓰면 **피커가 A주문의 품목을 보여주고 실제 기록은 B주문에 남는**
불일치가 발생한다. 후보 조회와 대상 소유권 검증(결정 L)은 동일한 규칙을 쓴다(REQ-FORCE-004).

### 결정 C — 강제 경로도 total 불변식을 그대로 적용한다

음수 total은 정상 경로에서 그룹화 이전 단계에 행 단위로 거부되며, 판독 실패로 강등된 값도 같은
지점에서 거부된다(`purchase_order_views.py:2865-2898`, 테스트 `test_spec_015.py:932-1021`,
`:1524-1637`). `shipped_quantity`는 어떤 경우에도 감소하지 않는다.

강제 경로가 이 검증을 건너뛰면, SPEC-ORDER-015가 Exclusions로 명시 배제한 **출고
취소/되돌리기(undo)** 기능이 "강제 처리에 음수를 넣는" 형태로 되살아난다. 실제로
SPEC-ORDER-015는 구현 단계에서 정확히 이 결함(Defect 1)을 발견해 수정한 이력이 있다. 따라서
강제 경로는 이 검증들을 정상 경로와 동일한 판정 결과가 나오도록 적용한다(REQ-FORCE-011,
REQ-FORCE-012). `total == 0`의 처리는 정상 경로와 갈라지므로 결정 I에서 별도로 다룬다.

### 결정 D — 강제 대상에서 제외할 LineItem 조건

| 조건 | 처리 | 근거 |
|---|---|---|
| `purchase_status == "order_cancelled"` | **후보에서 제외 + 게이트에서 거부** | 취소 품목은 물류 대상이 아니다. 기존 두 곳이 일관되게 배제한다(`purchase_order_views.py:2689`, `:176`). |
| `sku is NULL` | **후보에서 제외 + 게이트에서 거부** | 주문 집계는 trackable(`sku__isnull=False`) 품목만 센다(`:155-157`). 이런 행에 `logistics_status="shipped"`를 쓰면 집계에 절대 반영되지 않는 "유령 출고"가 된다. |
| `quantity is NULL` | 후보에 포함하되 **잔여 용량 없음으로 표시** | 용량이 0으로 취급되어(`:2984-2985`) 모든 양수 요청이 `quantity_exceeded`가 된다. 하드 제외 대신 표시해 담당자의 헛수고를 막는다. |
| `shipped_quantity >= quantity` | 후보에 포함하되 **잔여 용량 없음으로 표시** | 정상 경로도 이를 차단하지 않고 `quantity_exceeded`로 보고한다(`:3039-3051`). 동일한 관측 가능 동작을 유지한다. |

주의: `purchase_status`는 기존 LineItem 상세 직렬화 계약에 없다
(`backend/order/serializers.py:110-123`). 따라서 제외 판정은 서버에서 수행되어야 하며, 이
값은 후보 응답에도 실리지 않는다 — 프론트가 렌더할 일이 없으므로 라벨 매핑 대상도 아니다.

### 결정 E — 주문 단위 집계 재계산은 호출하지 않는다 (기존 동작 답습)

현행 출고 처리는 `logistics_status`를 `"shipped"`로 기록하면서도 `_recompute_order_aggregates`를
호출하지 않는다(`purchase_order_views.py:2810-3101`). 자매 함수인 입고 처리 경로는 호출한다
(`:2137-2145`, `:2212`). 즉 **선행 불일치가 존재하며, 어떤 테스트로도 pin되어 있지 않다.**

이 SPEC은 그 불일치를 **의도적으로 답습한다.** 강제 경로만 집계를 갱신하면 "같은 LineItem에 같은
결과를 남기는 두 경로가 서로 다른 부수효과를 낸다"는 더 나쁜 비일관성이 생기고, 정상 경로까지
함께 고치면 쿼리 카운트 상한을 넘겨 T8 상수 조정이 동반된다. 이 답습은 REQ-FORCE-013(쓰기 대상
제한)으로 규범화된다. 해소는 후속 과제 1로 기록한다.

### 결정 F — 추가 권한 게이트를 두지 않는다

`backend/order/**`의 모든 엔드포인트는 예외 없이 JWT 인증 + 인증 사용자 허용 조합을 쓴다
(`research.md` §8). 되돌리기 어려운 기존 동작(대량 발주 확정, 부수효과가 있는 내보내기)에도 추가
게이트가 없다. 강제 출고에만 별도 권한을 두면 코드베이스 최초 사례가 되고 기존 인증 테스트
관례와 별개의 새 테스트 축이 생긴다(REQ-FORCE-017).

### 결정 G — 선택 상태 키는 `(주문 식별자, sku)` 쌍

매칭 실패 항목은 `line_item_id`를 갖지 않는다(`purchase_order_views.py:2954-2980`) — 매칭 성공과
수량초과 항목만 갖는다(`:3031`, `:3045`). 그러나 강제 자격이 있는 행은 반드시 그룹 루프에서
생성되며, 그 루프에서 `(주문 식별자, sku)` 쌍은 구성상 유일하다. 배열 인덱스 기반 키는 정렬·필터
변경 시 선택이 옮겨가므로 쓰지 않는다. **서버 측 합산 키와 응답 키는 이 쌍이 아니라 지정된 대상
LineItem 식별자**임에 유의한다(결정 K).

### 결정 H — 프론트 선택 상태는 화면 로컬 상태로 관리한다

동일 성격의 선례인 렉번호 검색 탭이 선택 상태를 전역 스토어가 아닌 화면 로컬 상태로 관리하며, 새
조회 결과가 도착하면 선택을 리셋한다(`frontend/src/pages/RackNumberPage/tabs/SearchTab.tsx:28`,
`:64`). `/outbound`는 단일 화면이므로 동일한 관례를 따른다.

### 결정 I — `total == 0` 행은 강제 대상이 아니다

정상 경로는 `total < 0`을 그룹화 이전에 거부하고(`purchase_order_views.py:2885-2898` — 주석이
"0은 여기서 거부되지 않는다"고 명시; 판독 불가 값도 `:2865-2874`에서 함께 거부된다), `0`은
**매칭 이후에** 판정한다: 매칭된 LineItem의 `confirmed_distributor`가 미국 창고가 아니면
`invalid_total`(`:2999-3009`), 미국 창고이면 `shipped_quantity = max(shipped_quantity, quantity)`
+ `logistics_status="shipped"`로 채우는 완료 신호(`:3010-3037`, SPEC-ORDER-015 설계 결정 D)다.

이 완료 신호 판정은 **매칭에 성공한 LineItem의 `confirmed_distributor`에 의존**한다. 매칭에
실패한 행에는 그 판정 근거가 되는 LineItem이 없다. 게다가 후보 판정 분기(`:2969-2980`)가 0
분기(`:2999`)보다 **먼저** 실행되므로, `total = 0`이면서 SKU가 매칭되지 않는 행은 실제로
`line_item_not_found`로 보고되어 강제 대상이 될 수 있었다.

이를 사용자 지정 대상으로 확장하면 "담당자가 임의로 고른 품목의 `shipped_quantity`를 주문 수량까지
한 번에 채우는" 동작이 되며, 이는 인터뷰에서 요구된 적 없는 신규 비즈니스 규칙이다. 따라서
`total == 0` 행은 자격에서 제외하고(REQ-FORCE-001), 강제 요청에 실려 오면 음수·판독불가와 동일하게
`invalid_total`로 거부한다(REQ-FORCE-011). 이는 신규 사유 코드를 만들지 않으며, 정상 경로가
비-미국창고 품목의 0에 내리는 판정과 같은 코드다. 미국창고 완료 신호는 기존 정상 경로에서 계속
정상 동작한다.

### 결정 J — 자격 판정은 프론트엔드 책임이고 서버 계약은 좁다

강제 요청 payload는 주문 식별자, sku, 요청 수량, 지정 대상 식별자를 싣는다. 여기에는 그 행이 직전
출고 처리에서 **어떤 사유로** 매칭 실패했는지에 대한 기록이 없다.

`order_not_found`, `invalid_row`, `invalid_total`은 payload만으로 재도출할 수 있다. 그러나
`multiple_line_items`는 `(order, sku)`가 2건 이상에 매칭됐다는 뜻이므로(`:2969-2980`), 서버가 이를
재판별하려면 **강제 경로가 우회한다고 선언한 바로 그 `(order, sku)` 매칭을 다시 실행해야 한다.**

따라서 자격 판정은 **UI가 무엇에 컨트롤을 렌더하고 무엇을 요청에 싣는가**의 문제로 정의한다
(REQ-FORCE-001, REQ-FORCE-019, REQ-FORCE-023). 서버는 사유 코드를 재도출하지 않으며, 계약은
"게이트(REQ-FORCE-002)를 통과한 요청에 대해, 지정된 대상별로 합산된 수량을 total 불변식과 수량
한도 안에서 반영한다"로 좁힌다.

이것이 안전한 이유는 데이터 무결성을 실제로 지키는 가드가 사유 코드 재판별이 아니라 **소유권
검증과 수량 한도**이기 때문이다. 사유가 무엇이든, 반영은 "해당 주문에 속하고 제외 조건에 걸리지
않으며 한도 안에 있는, 담당자가 명시적으로 고른 LineItem"에만 일어난다 — 강제 경로가 원래 하는
일과 정확히 동일하며 어떤 불변식도 깨지 않는다. 따라서 **서버가 비-`line_item_not_found` 행을
거부한다고 규정하는 요구사항은 이 SPEC에 존재하지 않으며, 그렇게 읽히는 인수 기준도 두지 않는다.**

### 결정 K — 응답과 합산의 키는 지정된 대상 LineItem이다

정상 경로는 같은 키를 공유하는 행들의 수량을 **한도 판정 이전에** 합산한다
(`purchase_order_views.py:2900-2901`, SPEC-ORDER-015 설계 결정 C). 이 합산이 있어야 배치 단위의
한도 검사가 건전하다.

강제 경로에서는 서로 다른 두 매칭 실패 행(서로 다른 SKU이므로 선택 키도 다름 — 결정 G)이 **같은
LineItem을 대상으로 지정하는 것이 정당하게 가능하다.** 각 행을 요청 이전 `shipped_quantity` 기준
으로 따로 판정하면 두 행 모두 한도를 통과한 뒤 합산 결과가 `quantity`를 넘어, "수량 한도 우회 없음"
배제 조항이 무력화된다.

따라서 합산 키는 `(주문 식별자, sku)`가 아니라 **지정된 대상 LineItem 식별자**이며, 판정·반영·보고가
모두 대상 단위로 1회씩 일어난다(REQ-FORCE-008). 여기서 파생되는 보고 형태 문제 — 병합된 행들은
SKU가 서로 다르므로 어느 `sku`를 실을지 — 는 다음과 같이 결정한다(REQ-FORCE-016):

- `line_item_id`: 지정된 대상
- `name`: 그 행들의 주문 이름. 게이트가 모든 대상을 "행의 주문 식별자가 해석한 Order"에 대해
  검증하므로(REQ-FORCE-002), 하나의 대상에 병합된 행들은 필연적으로 같은 `name`을 가진다
- `sku`: **대상 LineItem 자신의 `sku`**. 요청 행들의 `sku`가 서로 다를 때 결정적인 유일한 선택이며,
  담당자가 실제로 반영한 품목을 가리킨다는 점에서도 옳다
- `total`: 합산된 수량
- 나머지 필드: 기존 3분류 응답 계약이 각 카테고리에 대해 이미 정의한 그대로

### 결정 L — 대상 게이트 위반은 요청 전체를 HTTP 400으로 거부한다

피커는 애초에 유효한 대상만 제시한다. 따라서 무효한 대상이나 구조가 깨진 행이 서버에 도착했다는
것은 **행 단위 업무 결과가 아니라 클라이언트가 서버 상태와 어긋났다는 신호**다(예: 후보 조회 이후
해당 품목이 취소되었거나, 화면이 오래된 상태로 남아 있는 경우). 이런 입력에 대해 일부만 반영하면
담당자는 "무엇이 반영되고 무엇이 반영되지 않았는지"를 화면에서 재구성해야 하는데, 그 판단 근거인
후보 목록 자체가 이미 낡은 상태다. 요청 전체가 단일 원자적 트랜잭션인 이상 전량 거부가 부분 반영
보다 단순하고 안전하다.

이 형태는 기존 bulk 계열 엔드포인트가 잘못된 입력에 `400 {"error": ...}`를 반환하는 관례와 동일
하다(`purchase_order_views.py:2316-2319`, `:2416-2420`, `:2526-2530`). 부수적으로, 이 SPEC이 신규
매칭 실패 사유 코드를 만들지 않는다는 방침과도 맞아떨어진다 — 다만 그 방침은 이 결정의 **결과**
이지 근거가 아니다.

**수용된 대가**: 6행짜리 배치에서 대상 하나가 낡으면 나머지 5행도 반영되지 않는다. 담당자는 결과
화면을 다시 조회한 뒤 재실행해야 한다. 인터뷰(Q3)는 일괄 실행 단위만 확정했을 뿐 부분 실패
정책을 다루지 않았으므로, 이 대가는 후속 과제 2에 실패 모드로 함께 기록한다.

### 결정 M — 매칭 실패 섹션은 전용 컴포넌트로 렌더하고 공유 컴포넌트는 손대지 않는다

현재 세 결과 섹션은 모두 하나의 공유 컴포넌트가 렌더하며, 그 행 계약은 `cells: string[]`이다
(`frontend/src/components/ResultSection.tsx:8-27`) — 각 셀은 순수 텍스트로 출력되므로 체크박스나
대상 선택기를 담을 수 없다. 이 컴포넌트에는 출고 페이지 외부에 4개의 호출부가 존재한다
(`frontend/src/pages/InboundPage/index.tsx:176`, `:194`, `:211`,
`frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx:153`).

따라서 공유 컴포넌트의 시그니처는 **변경하지 않는다.** 매칭 실패 섹션만 출고 페이지 하위의 전용
컴포넌트로 분리하고, 성공·수량초과 섹션은 계속 공유 컴포넌트가 렌더한다. 전용 컴포넌트는 기존
섹션의 시각적 처리(제목, 건수 표기, 톤, 컬럼 헤더)와 기존 테스트 훅을 재현해야 하며, 그 구현
지시는 `plan.md`에 있다.

### 결정 N — 강제 실행 성공 시 결과 표시를 병합 규칙으로 갱신한다

출고 페이지는 두 제출 경로(수동 입력·Excel 업로드)가 공유하는 **결과 슬롯 하나**를 가지며, 각
경로의 성공 시 그 슬롯을 새 응답으로 덮어쓴다(`frontend/src/pages/OutboundPage/index.tsx:31-33`,
`:42`, `:52`; SPEC-ORDER-015 REQ-OUTBOUND-018).

강제 실행은 그 슬롯을 갱신하되 **통째로 덮어쓰지 않고 병합 규칙**을 적용한다(REQ-FORCE-024):
처리된 행은 매칭 실패 목록에서 제거하고, 선택되지 않은 행은 그대로 남기며, 강제 응답의 성공·
수량초과 항목은 대응하는 목록에 덧붙이고, 세 카테고리 건수를 결과 목록에서 다시 계산한다.

**기각한 대안 1 — 통째 대체.** 처리된 행이 사라진다는 목적은 달성하지만, 담당자가 **선택하지
않은** 자격 행들과 이번 강제 실행이 방금 만들어낸 수량초과 항목까지 함께 화면에서 지운다.
5건 중 2건만 강제 처리한 담당자는 나머지 3건을 아무 기록 없이 잃고, 한도를 넘겨 반려된 건도
재지정할 기회 없이 사라진다. 복구하려면 출고 처리를 처음부터 다시 실행하는 수밖에 없다.

**기각한 대안 2 — 기존 결과 옆에 덧붙이기.** 이 경우 선택만 초기화되고 처리된 행과 그 대상
지정이 목록에 남아, 담당자가 같은 행을 같은 대상에 반복 반영할 수 있다 — 실물은 한 번 나갔는데
4 + 6으로 두 번 반영해 `quantity`를 채우는 식이다. 수량 한도는 피해를 제한할 뿐 막지 못한다.

병합 규칙은 대안 1의 보호 효과(처리된 행은 사라지고 재제출 불가)를 그대로 유지하면서 대안 2의
결함을 피하고, 동시에 담당자가 아직 처리하지 않은 작업 항목을 화면에 남긴다. 제거의 키는 선택
상태와 같은 `(주문 식별자, sku)` 쌍(결정 G)이므로 별도의 처리 완료 표식을 도입할 필요가 없다.

**수용된 대가**: 강제 실행 직후의 화면은 한 번의 출고 처리 응답을 그대로 옮긴 것이 아니라 서버
응답 두 건을 병합한 상태다. 즉 표시되는 세 목록은 클라이언트가 계산한 값이며, 같은 입력으로 출고
처리를 다시 실행했을 때의 서버 응답과 일치하지 않을 수 있다. 이는 화면 상태에 한정된 차이이며
저장된 데이터에는 영향이 없다.

### 결정 O — 강제 경로에만 행 단위 락을 도입한다

이 기능의 확정 스코프는 "수량 한도 초과 불가"(인터뷰 Q6)를 하드 룰로 정했다. 그런데 락이 없으면
같은 LineItem을 겨냥한 두 강제 요청이 **같은 낡은 `shipped_quantity`를 읽고 각자 한도 검사를
통과**한 뒤 둘 다 반영되어 합계가 `quantity`를 넘긴다. 오용이나 경합 유도가 아니라 두 담당자가
평범하게 동시에 실행하는 것만으로 확정 규칙이 깨지는 것이다.

강제 경로의 stale read 창은 정상 경로보다 **구조적으로** 넓다. 정상 경로는 한 요청 안에서 읽기·
판정·쓰기가 연달아 일어난다. 강제 경로는 후보 조회 → 담당자의 대상 선택 → 실행 사이에 사람의
판단이 끼어들므로, 한도 검사가 읽는 값이 수 초에서 수 분까지 낡을 수 있다. 같은 위험이라도 노출
시간이 다르다.

선례는 이미 같은 모듈 안에 있다 — `_apply_logistics_transition`이 `select_for_update()`를 쓴다
(`backend/order/purchase_order_views.py:247`). 즉 이 파일에는 락을 쓰는 관례와 쓰지 않는 관례가
이미 공존하며, 강제 경로에 락을 두는 것은 새 패턴의 도입이 아니라 기존 두 관례 중 하나를 고르는
일이다. 비용도 낮다: 대상 행을 읽는 기존 SELECT에 잠금을 붙이는 형태이므로 요청당 쿼리 수가
늘지 않는다(REQ-FORCE-018의 예산 논의와 무관하다).

**정상 경로는 바꾸지 않는다.** `_process_outbound_rows`의 락 없는 동작은 그대로 두며, 두 경로의
관례를 통일할지는 코드베이스 전역 결정이므로 후속 과제 2로 남긴다. 한 SPEC 안에서 두 경로를 함께
건드리면 정상 경로의 회귀 위험(쿼리 카운트 상한, 기존 테스트 스위트)을 이 기능의 주제와 무관하게
떠안게 된다.

**수용된 대가**: 같은 LineItem을 겨냥한 강제 요청들이 직렬화되므로 경합 시 두 번째 요청은 첫
번째가 커밋될 때까지 대기한다. 강제 실행은 담당자가 명시적으로 누르는 저빈도 동작이고 잠기는
범위가 지정 대상 행으로 한정되므로 실사용 지연은 무시할 수준으로 판단한다. 정상 경로와 강제 경로가
같은 LineItem을 동시에 건드리는 경우, 락을 쥐지 않는 정상 경로 쪽은 여전히 보호되지 않는다 —
이 잔여 격차도 후속 과제 2에 포함된다.

## 요구사항 (EARS)

**번호 규칙**: `REQ-FORCE-001`부터 `REQ-FORCE-025`까지 연속 번호이며 결번·중복·알파벳 접미사가
없다. v1.0.1까지 사용하던 접미사 체계는 v1.0.2 통합에서 폐지했다. 요구사항은 5개 모듈로
구성된다. v1.0.4에서 추가된 REQ-FORCE-025는 성격상 모듈 3(강제 반영 불변식)에 속하므로 그 모듈
끝에 배치했다 — 번호는 연속이지만 문서상 등장 순서는 모듈 4·5보다 뒤가 아니라 앞이며, 기존
요구사항을 재번호하지 않기 위한 선택이다.

### 모듈 1 — 강제 대상 자격과 입력 게이트

**REQ-FORCE-001** (State-Driven): While an outbound result row is displayed under the unmatched
category with reason `line_item_not_found` and with a requested quantity strictly greater than
zero, the system shall treat that row as eligible for force outbound processing; every other
displayed row shall be ineligible.

**REQ-FORCE-002** (Unwanted): If any row of a force outbound request is structurally malformed,
carries no designated target LineItem identifier, or designates a target that does not exist,
whose order identifier resolves to no Order, that belongs to an Order other than the one its
order identifier resolves to under REQ-FORCE-004, whose `purchase_status` is `order_cancelled`,
or whose `sku` is `null`, then the system shall reject the entire request with HTTP 400 without
modifying any LineItem, and the system shall NOT substitute or infer a target by any fallback
rule (empty-SKU substitution, sequential distribution across unshipped items,
single-candidate auto-selection, or otherwise).

### 모듈 2 — 후보 목록 조회

**REQ-FORCE-003** (Event-Driven): When the client requests force-outbound candidates for a set of
order identifiers, the system shall accept the entire set in a single request and shall return the
candidate list for every requested identifier in that one response, regardless of how many
identifiers the set contains; for an empty set the system shall return an empty result rather than
an error.

**REQ-FORCE-004** (Event-Driven): When the system resolves an order identifier to an Order — during
candidate lookup or during the target gate of REQ-FORCE-002 — the system shall use exact
`Order.name` equality and shall resolve same-name collisions by selecting the matching Order with
the lowest `pk`, reproducing the rule the existing outbound processing path applies.

**REQ-FORCE-005** (Unwanted): If a LineItem belonging to a requested order has `purchase_status`
equal to `order_cancelled`, or has a `null` `sku`, then the system shall exclude that LineItem from
the returned candidate list.

**REQ-FORCE-006** (Ubiquitous): The system shall return each order's candidates in a deterministic
order, carrying for every candidate a stable identifier, book title, `sku`, ordered `quantity`,
current `shipped_quantity`, current `logistics_status`, and an indicator that is set when the
candidate's ordered `quantity` is `null` or its `shipped_quantity` has reached that `quantity`.

### 모듈 3 — 강제 반영 불변식

**REQ-FORCE-007** (Ubiquitous): The system shall deviate from the existing outbound processing path
in exactly two respects when applying a force outbound request — the `(order, sku)` matching step is
replaced by the operator's explicit target designation, and the existing path's post-match handling
of a zero amount is not inherited. Every other rule of the existing path shall apply identically:
per-row rejection of negative and unreadable amounts before summation, summation of rows sharing a
key before the capacity check, the quantity limit, non-decreasing shipped quantity, the threshold
status transition, and atomicity.

**REQ-FORCE-008** (Event-Driven): When a force outbound request passes the gate of REQ-FORCE-002,
the system shall first remove every row excluded by REQ-FORCE-011, shall then group only the
surviving rows by designated target LineItem identifier, shall sum the requested quantities within
each group into that target's combined quantity — a group of one row yielding that row's quantity —
and shall then evaluate and report each grouped target exactly once. A target for which no row
survives forms no group, and the system shall neither evaluate nor write nor report such a target in
any response category. Because force eligibility admits only strictly positive quantities and every
non-positive or unreadable row is removed before grouping, every group the system evaluates carries
a combined quantity of at least 1 — a combined quantity of zero is unreachable by construction.

**REQ-FORCE-009** (Event-Driven): When the sum of a target LineItem's current `shipped_quantity` and
the combined quantity of its group — which is at least 1 per REQ-FORCE-008 — does not exceed that
LineItem's ordered `quantity`, treating a `null` `quantity` as `0`, the system shall increase that
LineItem's `shipped_quantity` by the combined quantity, shall set `shipped_at` to the processing
timestamp, and shall set `logistics_status` to `"shipped"` at the moment the resulting
`shipped_quantity` reaches or exceeds the ordered `quantity`.

**REQ-FORCE-010** (Unwanted): If applying a target's combined quantity would cause that LineItem's
`shipped_quantity` to exceed its ordered `quantity` — treating a `null` `quantity` as `0` — then the
system shall modify no field of that LineItem and shall report that target under the
quantity-exceeded category.

**REQ-FORCE-011** (Unwanted): If a force outbound row's requested quantity is negative, is zero, or
is a value that could not be genuinely read as a number, then the system shall remove that row
before the grouping step of REQ-FORCE-008 so that it contributes nothing to any target's combined
quantity, shall modify no LineItem on account of it, and shall report it under the unmatched
category with reason `invalid_total`.

**REQ-FORCE-012** (Ubiquitous): The system shall never decrease any LineItem's `shipped_quantity` as
a result of a force outbound operation — only increases and no-change outcomes are permitted.

**REQ-FORCE-013** (Ubiquitous): The system shall write no field other than the designated target
LineItems' `shipped_quantity`, `shipped_at`, and `logistics_status` while processing a force
outbound request — no LineItem shall be created or deleted, no other LineItem field shall change,
and no `Order` field including `Order.status` and `Order.ready_to_ship` shall be written, matching
the existing outbound processing path's current behavior (설계 결정 E).

**REQ-FORCE-014** (Ubiquitous): The system shall apply a single force outbound request within one
atomic transaction, so that no partially applied result can persist when processing fails mid-run.

**REQ-FORCE-025** (Event-Driven): When a force outbound request reaches the evaluation step, the
system shall acquire a row-level lock on every designated target LineItem inside the request's
transaction before evaluating the quantity limit, and shall make the capacity judgement of
REQ-FORCE-009 and REQ-FORCE-010 against the values read under that lock, so that two concurrent
force requests targeting the same LineItem cannot both pass the limit against the same pre-update
`shipped_quantity` (설계 결정 O).

### 모듈 4 — 실행 단위, 응답 계약, 기존 계약 보존

**REQ-FORCE-015** (Event-Driven): When the operator executes force processing for a set of selected
rows, the system shall transmit and process the entire set in a single request, regardless of how
many rows or how many distinct orders the set spans.

**REQ-FORCE-016** (Ubiquitous): The system shall return, for a force outbound request that passes
the gate of REQ-FORCE-002, the same three-category response contract the existing outbound
processing endpoints return — `matched`, `unmatched` and `quantity_exceeded` lists with their
counts, each item carrying every field the corresponding existing item already carries (`name`,
`sku`, `total`, `line_item_id`, `shipped_quantity`, `quantity` and `logistics_status` for a matched
item; the same with `reason` in place of `logistics_status` for a quantity-exceeded item; `name`,
`sku`, `total` and `reason` for an unmatched item) — so that the client can reuse its existing
result-rendering path unchanged. Matched and quantity-exceeded items shall be keyed one per
designated target LineItem rather than one per request row, with `line_item_id` naming that target,
`sku` taking the target LineItem's own `sku`, and `total` carrying the combined quantity
(설계 결정 K).

**REQ-FORCE-017** (Ubiquitous): The system shall protect the force outbound candidate lookup and the
force outbound processing operation with the same authentication and permission convention every
other endpoint in the order domain uses — an authenticated request is accepted and no additional
authorization gate is introduced (설계 결정 F).

**REQ-FORCE-018** (Ubiquitous): The system shall leave the server-side request and response
contracts of the two existing outbound processing endpoints unchanged, shall embed no candidate list
in their unmatched payload, and shall not increase the number of database queries those endpoints
issue (설계 결정 A).

### 모듈 5 — 프론트엔드

**REQ-FORCE-019** (State-Driven): While the outbound result view displays the unmatched section, the
system shall render a per-row selection control and a target-designation control on exactly the rows
that are eligible per REQ-FORCE-001.

**REQ-FORCE-020** (Event-Driven): When the operator opens the target-designation control for an
eligible row, the system shall display that row's order candidates with the attributes and the
no-remaining-capacity indicator of REQ-FORCE-006.

**REQ-FORCE-021** (Ubiquitous): The system shall render every `logistics_status` value and every
unmatched-reason value shown anywhere in the unmatched section as a human-readable Korean label
rather than its raw code value.

**REQ-FORCE-022** (State-Driven): While no displayed row is simultaneously eligible, selected and
carrying a designated target, the system shall keep the bulk force-execution control unavailable.

**REQ-FORCE-023** (Ubiquitous): The system shall include in a force execution request exactly those
displayed rows that are eligible, selected and carrying a designated target.

**REQ-FORCE-024** (Event-Driven): When a force execution succeeds, the system shall recompute the
displayed outbound result by removing from the displayed unmatched list every row it just submitted,
keyed by the same `(order identifier, sku)` pair the selection uses; by leaving every unmatched row
it did not submit displayed and still selectable; by appending the force response's matched and
quantity-exceeded items to the corresponding displayed lists; by recomputing all three displayed
category counts from the resulting lists; and by clearing the row selection state — so that a
processed row is no longer displayed or re-submittable, an unprocessed row remains available, and a
new run needs no page reload (설계 결정 N).

---

## ACCEPTANCE CRITERIA

각 인수 기준은 대응 요구사항이 문장으로 이미 말한 내용을 되풀이하지 않고, **구체적인 픽스처
조건·경계값·차등 비교**로 관측 가능한 결과를 제시한다. 하나의 인수 기준이 한 동작의 여러 측면을
규정하는 복수 요구사항을 함께 검증하는 경우가 있으며, 그 매핑은 아래 traceability 표에 있다.
실행 가능한 Given/When/Then 시나리오는 `acceptance.md`에 있고, 각 시나리오는 여기와 **동일한**
`Traces:` 목록과 검증 레이어 표기를 인용한다.

**AC-FORCE-001** (State-Driven) — Traces: REQ-FORCE-001, REQ-FORCE-019. While the unmatched section
displays five rows — `line_item_not_found` with quantity 4, `line_item_not_found` with quantity 0,
`order_not_found`, `multiple_line_items`, and one row from the quantity-exceeded section — the
system shall render a selection control and a target-designation control on the first row only, and
a select-all action shall select that row alone.

**AC-FORCE-002** (Unwanted) — Traces: REQ-FORCE-002. If a force request whose other rows are fully
valid contains one row that is malformed, omits its target, names a nonexistent target, names an
order identifier matching no Order, names a target belonging to a different Order, names an
`order_cancelled` target, or names a target with a `null` `sku`, then in each of those seven cases
the system shall respond with HTTP 400 and shall leave every LineItem in the request — including the
valid ones and the single candidate of an order that has exactly one — unmodified.

**AC-FORCE-003** (Event-Driven) — Traces: REQ-FORCE-003. When candidates are requested for five
distinct order identifiers, the system shall satisfy the request in one round trip with candidates
keyed to all five; when requested for an empty set, the system shall return an empty result and
write nothing.

**AC-FORCE-004** (Event-Driven) — Traces: REQ-FORCE-004. When two Orders share a `name` and the one
with the lower `pk` was created later, the system shall return candidates from the lower-`pk` Order
and shall land the subsequent force write on that same Order.

**AC-FORCE-005** (Ubiquitous) — Traces: REQ-FORCE-005, REQ-FORCE-006. For an order holding one
ordinary LineItem, one `order_cancelled` LineItem, one `null`-`sku` LineItem, one with `quantity`
`null` and one already fully shipped, the system shall return exactly three candidates — omitting the
cancelled and `null`-`sku` ones — shall set the no-remaining-capacity indicator on the last two, and
shall return the same ordering when the lookup is repeated.

**AC-FORCE-006** (Ubiquitous) — Traces: REQ-FORCE-007. Given two LineItems in identical initial
state, the system shall leave both in the same `shipped_quantity` and `logistics_status` when a
positive quantity within capacity is applied to one through the existing path by SKU match and to
the other through the force path by designation; and for a zero amount against a
`warehouse_ca`-confirmed target, where the existing path completes the item, the force path shall
form no group for that target and shall therefore leave it unmodified and absent from every response
category.

**AC-FORCE-007** (Unwanted) — Traces: REQ-FORCE-008, REQ-FORCE-010. If one request carries two rows
with different SKUs designating the same target whose remaining capacity accommodates either row
alone but not their sum, then the system shall modify no field of that LineItem and shall report
exactly one quantity-exceeded item for it.

**AC-FORCE-008** (Event-Driven) — Traces: REQ-FORCE-008, REQ-FORCE-009, REQ-FORCE-016. When one
request carries two rows with different SKUs designating the same target whose remaining capacity
accommodates their sum and is exactly reached by it, the system shall raise that LineItem's
`shipped_quantity` by the sum exactly once, shall set `logistics_status` to `"shipped"`, and shall
report exactly one matched item whose `line_item_id` is the target, whose `sku` is the target
LineItem's own `sku` rather than either request row's, and whose `total` is the sum.

**AC-FORCE-009** (Event-Driven) — Traces: REQ-FORCE-009. When a single row applies a quantity that
leaves the target below its ordered `quantity`, the system shall increase `shipped_quantity` by that
amount, shall update `shipped_at`, and shall leave `logistics_status` at its previous value.

**AC-FORCE-010** (Unwanted) — Traces: REQ-FORCE-010. If a designated target's ordered `quantity` is
`null`, then the system shall leave it unmodified for any positive requested quantity and shall
report it under the quantity-exceeded category.

**AC-FORCE-011** (Unwanted) — Traces: REQ-FORCE-008, REQ-FORCE-011. If a request carries rows with
quantity `-5`, `0`, an unreadable value, `0` against a `warehouse_ca`-confirmed target, `0` against a
target whose ordered `quantity` is `null`, and `0` against an already fully shipped target, then the
system shall report all six with reason `invalid_total`, shall leave every one of those LineItems
unmodified — including no `shipped_at` stamp and no transition to `"shipped"` on the `null`-quantity
and already-complete targets, for which no group is formed — shall omit those targets from the
matched and quantity-exceeded lists entirely, and shall exclude those quantities from the combined
quantity of any target that another row in the same request also designates.

**AC-FORCE-012** (Ubiquitous) — Traces: REQ-FORCE-012. The system shall leave no LineItem with a
`shipped_quantity` below the value it held before any sequence of force requests mixing accepted,
quantity-exceeded and `invalid_total` outcomes.

**AC-FORCE-013** (Ubiquitous) — Traces: REQ-FORCE-013. After a force request that transitions a
target to `"shipped"`, the system shall show a field-level diff limited to that LineItem's
`shipped_quantity`, `shipped_at` and `logistics_status`, with the affected order's LineItem count and
every LineItem's `sku`, `title` and `quantity` unchanged, `Order.status` and `Order.ready_to_ship`
unchanged, and the order-aggregate recomputation routine never invoked.

**AC-FORCE-014** (Ubiquitous) — Traces: REQ-FORCE-014. The system shall leave every LineItem
unmodified when the force write step raises an exception partway through a multi-target batch,
verified by injecting that exception the way the existing outbound atomicity test does.

**AC-FORCE-015** (Event-Driven) — Traces: REQ-FORCE-015, REQ-FORCE-023. When the operator executes a
selection of six eligible rows spanning three orders of which two rows carry no designated target,
the system shall issue exactly one request containing exactly the four designated rows.

**AC-FORCE-016** (Ubiquitous) — Traces: REQ-FORCE-016. The system shall return a force response that
satisfies the existing outbound response contract without widening or narrowing it — three category
lists whose lengths equal their counts, with `shipped_quantity`, `quantity` and `logistics_status`
present on every matched item and `reason` present on every quantity-exceeded item — so that the
existing client result-rendering path consumes it without modification.

**AC-FORCE-017** (Ubiquitous) — Traces: REQ-FORCE-017. The system shall refuse an unauthenticated
request to either the candidate lookup or the force processing operation and shall accept an
authenticated one with no further role check.

**AC-FORCE-018** (Ubiquitous) — Traces: REQ-FORCE-018. The system shall return the same payload and
issue the same number of database queries from the two existing outbound endpoints as before this
SPEC, with their existing query-count bounds and cross-endpoint equality tests passing unmodified.

**AC-FORCE-019** (Event-Driven) — Traces: REQ-FORCE-020. When the operator opens an eligible row's
target-designation control for an order holding three candidates of which one is fully shipped, the
system shall list all three with title, `sku`, ordered quantity, shipped quantity and status, and
shall mark the fully shipped one as having no remaining capacity.

**AC-FORCE-020** (Ubiquitous) — Traces: REQ-FORCE-021. With the picker open and a row's failure
reason displayed, the system shall render no `logistics_status` or reason code value as text in the
unmatched section, while continuing to render `sku` and title values as stored.

**AC-FORCE-021** (State-Driven) — Traces: REQ-FORCE-022. While two eligible rows are selected and
neither carries a designated target, the system shall keep the bulk execution control unavailable,
and shall make it available as soon as one of them is designated.

**AC-FORCE-022** (Event-Driven) — Traces: REQ-FORCE-024. When a force execution over a displayed
unmatched list of three eligible rows submits two of them, of which one is accepted and one is
reported quantity-exceeded, the system shall no longer display either submitted row in the unmatched
section, shall still display the third row with its selection and target-designation controls
available, shall show the accepted row in the 성공 section and the quantity-exceeded row in the
수량초과 section, shall show all three category counts equal to the lengths of the lists as
displayed, and shall present an empty selection — without a page reload.

**AC-FORCE-023** (Event-Driven) — Traces: REQ-FORCE-025. When two force requests that designate the
same LineItem — whose ordered `quantity` is 10 and whose `shipped_quantity` is 0, each request asking
for 6 so that either alone fits and the two together do not — are executed concurrently, the system
shall apply exactly one of them and shall report the other under the quantity-exceeded category
against the first request's committed `shipped_quantity`, leaving that LineItem at
`shipped_quantity` 6 and never above its ordered `quantity`, for every interleaving of the two
requests.

### Traceability 검증표

| REQ | AC | REQ | AC |
|---|---|---|---|
| REQ-FORCE-001 | AC-FORCE-001 | REQ-FORCE-013 | AC-FORCE-013 |
| REQ-FORCE-002 | AC-FORCE-002 | REQ-FORCE-014 | AC-FORCE-014 |
| REQ-FORCE-003 | AC-FORCE-003 | REQ-FORCE-015 | AC-FORCE-015 |
| REQ-FORCE-004 | AC-FORCE-004 | REQ-FORCE-016 | AC-FORCE-008, AC-FORCE-016 |
| REQ-FORCE-005 | AC-FORCE-005 | REQ-FORCE-017 | AC-FORCE-017 |
| REQ-FORCE-006 | AC-FORCE-005 | REQ-FORCE-018 | AC-FORCE-018 |
| REQ-FORCE-007 | AC-FORCE-006 | REQ-FORCE-019 | AC-FORCE-001 |
| REQ-FORCE-008 | AC-FORCE-007, AC-FORCE-008, AC-FORCE-011 | REQ-FORCE-020 | AC-FORCE-019 |
| REQ-FORCE-009 | AC-FORCE-008, AC-FORCE-009 | REQ-FORCE-021 | AC-FORCE-020 |
| REQ-FORCE-010 | AC-FORCE-007, AC-FORCE-010 | REQ-FORCE-022 | AC-FORCE-021 |
| REQ-FORCE-011 | AC-FORCE-011 | REQ-FORCE-023 | AC-FORCE-015 |
| REQ-FORCE-012 | AC-FORCE-012 | REQ-FORCE-024 | AC-FORCE-022 |
| — | — | REQ-FORCE-025 | AC-FORCE-023 |

요구사항 25개 전량이 최소 1개의 인수 기준에 대응한다(25 REQ → 23 AC, 미커버 REQ 없음, 미정의
REQ를 가리키는 AC 없음). 6개 인수 기준(001, 005, 007, 008, 011, 015)이 한 동작의 여러 측면을
규정하는 2~3개 요구사항을 함께 검증하며, 3개 요구사항(009, 010, 016)은 정상·초과 두 방향을 각각
다루는 2개 인수 기준을, REQ-FORCE-008은 초과·성공·전량 거부 세 방향을 다루는 3개 인수 기준을
가진다.

---

## Exclusions (What NOT to Build)

- **수량 한도 우회 없음** — 강제는 `(order, sku)` 매칭만 우회한다. 한도 초과는 강제 경로에서도
  거부되며 `quantity_exceeded`로 보고된다(확정 스코프 Q6, REQ-FORCE-010).
- **자동 대상 추론 없음** — 빈 SKU 자동 반영, 미출고 품목 순차 분배, 후보가 1건일 때의 자동 선택
  등 어떤 대체 규칙도 구현하지 않는다(확정 스코프 Q5, REQ-FORCE-002).
- **`total == 0` 강제 처리 없음 — 미국창고 완료 신호의 강제 경로 확장 없음** — 0 수량 행은 자격에서
  제외되며, 요청에 실려 오면 `invalid_total`로 거부된다. 완료 신호 판정이 의존하는
  `confirmed_distributor`는 매칭에 성공한 LineItem의 속성이므로 이를 사용자 지정 대상으로 확장하는
  것은 요구된 적 없는 신규 규칙이다(설계 결정 I). 기존 정상 경로의 완료 신호 동작은 그대로 유지된다.
- **신규 LineItem 생성·삭제 없음, 주문 원본 구성 불변** — 강제 처리는 대상의 세 필드 외에 아무것도
  쓰지 않는다(REQ-FORCE-013).
- **신규 모델 컬럼·마이그레이션 없음** — 기록되는 필드는 기존 `shipped_quantity` / `shipped_at` /
  `logistics_status` 뿐이다(확정 스코프 Q4).
- **감사 로그 테이블 없음** — 강제 처리 이력을 별도로 추적하는 모델·테이블을 만들지 않는다
  (확정 스코프 Q4).
- **`multiple_line_items` / `invalid_total` / `order_not_found` / `invalid_row` 강제 처리 없음** —
  강제 대상 사유는 `line_item_not_found` 하나뿐이며, 이 자격 판정은 UI가 수행한다(확정 스코프 Q2,
  REQ-FORCE-001/019/023, 설계 결정 J).
- **서버의 매칭 실패 사유 재도출 없음** — 강제 요청 처리 시 `(order, sku)` 매칭을 다시 실행해 사유
  코드를 재판별하지 않으며, 사유를 근거로 행을 거부하지 않는다. 데이터 무결성은 대상 게이트와 수량
  한도가 보장한다(설계 결정 J).
- **`quantity_exceeded` 섹션 변경 없음** — 강제 컨트롤은 매칭 실패 섹션에만 노출되며, 수량초과
  섹션의 표현과 동작은 SPEC-ORDER-015가 제공한 그대로다(확정 스코프 Q1).
- **출고 취소/되돌리기(undo) 없음** — `shipped_quantity` 감소나 `logistics_status` 역행은 강제
  경로로도 도달할 수 없다(설계 결정 C, REQ-FORCE-011/012).
- **`_recompute_order_aggregates` 및 그 호출부 수정 없음** — 이 함수의 소스는 변경하지 않는다. 강제
  경로가 이를 호출하지 않는다는 **런타임 동작**은 REQ-FORCE-013이 규범화하며, 출고 경로 전반의 선행
  불일치 해소는 후속 과제 1이다(설계 결정 E).
- **후보 조회의 쓰기 없음** — 후보 목록 조회는 어떤 Order·LineItem도 변경하지 않는 읽기 전용
  동작이다.
- **행 단위·주문 단위 개별 HTTP 요청 없음** — 후보 조회와 강제 실행 모두 요청 1회로 처리한다
  (설계 결정 A, REQ-FORCE-003/015).
- **추가 권한 게이트 없음** — 인증 사용자면 충분하며 별도 역할 검사나 2단계 승인을 도입하지 않는다
  (설계 결정 F, REQ-FORCE-017).
- **신규 매칭 실패 사유 코드 없음** — 기존 5종을 그대로 사용한다. 기존 코드로 표현할 수 없는 대상
  미지정·무효·타 주문 소속·구조 오류는 행 단위 보고가 아니라 요청 전체 HTTP 400으로 처리한다
  (설계 결정 L, REQ-FORCE-002).
- **부분 반영 없음** — 게이트를 통과하지 못한 요청은 전량 거부된다. 유효한 행만 골라 반영하는 동작은
  구현하지 않는다(설계 결정 L, REQ-FORCE-014).
- **결과 섹션 공유 컴포넌트 시그니처 변경 없음** — 이 컴포넌트는 출고 페이지 외부에 4개 호출부를
  가지므로, 시그니처를 확장하면 무관한 화면과 그 테스트가 전부 회귀 대상이 된다. 매칭 실패 섹션만
  전용 컴포넌트로 분리한다(설계 결정 M).
- **SKU·도서명 등 데이터 값의 이스케이프·변환 없음** — 렌더링 금지 대상은 상태·사유 **코드값**
  뿐이다. 현재 결과 표는 이미 `sku`를 원본 그대로 렌더하며 이 SPEC은 그 동작을 바꾸지 않는다
  (REQ-FORCE-021).
- **라우팅·사이드바 변경 없음** — `/outbound` 경로와 메뉴 항목은 그대로이며, 페이지 모듈의 named
  export와 폴더+index 해석도 유지된다.
- **정상 출고 경로의 락 도입 없음** — 행 단위 락은 **강제 경로에만** 도입한다(REQ-FORCE-025,
  설계 결정 O). `_process_outbound_rows`의 락 없는 동작은 그대로 두며 그 함수와 두 출고
  엔드포인트는 이 SPEC으로 변경되지 않는다. 두 경로의 락 관례 통일은 후속 과제 2다.
- **강제 처리 결과의 Excel/CSV 내보내기 없음** — 범위 밖이다.

## 후속 과제 (Out of Scope Follow-up)

이 SPEC이 의도적으로 해결하지 않고 기록만 남기는 항목이다. 각각 별도 SPEC 대상이다.

1. **출고 경로의 주문 집계 미갱신 해소** — 출고 처리는 `logistics_status`를 `"shipped"`로 기록하면서
   주문 단위 집계를 재계산하지 않는다. 자매 함수인 입고 처리 경로는 재계산한다. 이 SPEC은 정상
   경로와 강제 경로의 동작을 일치시키기 위해 현행 동작을 답습했다(설계 결정 E). **사용자 결정에 따라
   이 항목은 정상 경로와 강제 경로를 함께 다루는 별도 SPEC에서 처리한다** — 한쪽만 고치면 같은
   결과를 남기는 두 경로가 서로 다른 부수효과를 내므로 반드시 동시에 수정해야 하며, 기존 쿼리 카운트
   상한 조정이 동반된다.
2. **정상 출고 경로의 동시성 보호와 배치 전체 거부 실패 모드** — v1.0.4에서 **강제 경로에는** 행 단위
   락이 도입되어(REQ-FORCE-025, 설계 결정 O) 강제 요청끼리의 한도 초과 경합은 해소되었다. 남은 격차는
   두 가지다.
   (a) **정상 경로에는 여전히 잠금이 없다**(@MX:WARN `purchase_order_views.py:2802-2809`). 따라서
   정상 출고 요청 두 건이 같은 LineItem을 동시에 처리하는 경우, 그리고 정상 경로와 강제 경로가 같은
   LineItem을 동시에 건드리는 경우(강제 쪽만 잠금을 쥔다)는 보호되지 않는다. 두 경로의 락 관례를
   통일할지는 코드베이스 전역 결정이므로 별도 SPEC에서 다룬다.
   (b) 대상이 후보 조회 이후 `order_cancelled`가 되었거나 `sku`를 잃은 경우, 사전 게이트에 걸려
   **요청 전체가 HTTP 400으로 거부**되므로(설계 결정 L) 함께 제출된 다른 유효한 행들도 반영되지
   않는다. 이 실패 모드는 락으로 해소되지 않으며, 부분 반영 정책 도입 여부는 별도 SPEC의 판단이다.
3. **위험 동작에 대한 권한 모델** — 되돌리기 어려운 동작 전반에 대한 통일된 권한 정책은 코드베이스
   전역 결정이며 이 SPEC의 범위가 아니다(설계 결정 F).
4. **미국창고 완료 신호의 대상 지정 확장** — 매칭 실패한 0 수량 행을 사용자 지정 대상으로 완료
   처리하는 기능이 실제로 필요하다고 확인되면 별도 SPEC에서 다룬다(설계 결정 I).

## 관련 SPEC

- **SPEC-ORDER-015**: 이 SPEC이 확장하는 부모 SPEC. 출고 수량 누적, 3분류 응답과 그 항목 필드 구성,
  수량초과 판정, 음수/판독불가 거부, 동일 키 합산, `shipped_quantity` 불감소, 임계 전이, 미국창고
  0수량 완료 신호, 단일 결과 슬롯 UI를 확립했다. 이 SPEC은 완료 신호를 제외한 규칙을 변경 없이
  승계한다.
- **SPEC-ORDER-011**: `LineItem.logistics_status` 물류 파이프라인의 근원 SPEC. 강제 경로도 이
  파이프라인의 마지막 단계에 도달할 뿐 신규 상태 값을 추가하지 않는다.
- **SPEC-ORDER-013**: `Order.name` 기반 매칭(`order_number` 폐기) 관례의 선례. 강제 경로의 후보
  조회와 대상 게이트도 동일한 매칭 기준을 사용한다(설계 결정 B).
- **SPEC-ORDER-014**: 응답에서 주문 식별자로 `Order.name`을 노출하는 관례의 선례(참고용).
- **SPEC-SHOPIFY-SKU-SET-002**: 한 주문에 동일 SKU LineItem이 2건 이상 존재할 수 있는 근거. 후보
  목록에서 제목·SKU만으로는 행을 구분할 수 없어 안정적 식별자가 표시 키가 되어야 하는 이유이며
  (REQ-FORCE-006), `multiple_line_items` 사유가 강제 대상에서 제외되는 배경이다.
