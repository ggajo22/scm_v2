---
id: SPEC-ORDER-016
document: spec-compact
version: 1.0.3
status: draft
updated: 2026-08-12
---

# SPEC-ORDER-016 압축 요약 — 강제 출고 처리

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(구현 계획), `acceptance.md`(Given/When/Then),
`research.md`(코드베이스 조사 근거), `interview.md`(확정 스코프).

v1.0.2에서 요구사항을 39개에서 24개로 통합하고 001~024 연속 번호로 재부여했다(알파벳 접미사 폐지).

## REQ 목록 (요약)

**모듈 1 — 강제 대상 자격과 입력 게이트**

- REQ-FORCE-001 — 자격: 사유 `line_item_not_found` **이면서** 요청 수량 > 0인 표시 행. 그 밖의 모든
  표시 행은 비자격
- REQ-FORCE-002 — 사전 게이트: 구조 오류 행 / 대상 미지정 / 존재하지 않는 대상 / 주문 미해석 /
  타 주문 소속 대상 / `order_cancelled` 대상 / `sku=null` 대상 중 하나라도 있으면 **요청 전체
  HTTP 400**, 어떤 대체 규칙으로도 대상을 추론하지 않음

**모듈 2 — 후보 목록 조회**

- REQ-FORCE-003 — 주문 식별자 집합 전체를 요청 1회로 조회. 빈 집합은 오류가 아니라 빈 결과
- REQ-FORCE-004 — 주문 해석(후보 조회 + 대상 게이트 공통): `Order.name` 정확 일치, 동명 충돌 시
  **최저 `pk`**
- REQ-FORCE-005 — `purchase_status="order_cancelled"` 및 `sku is NULL` 후보 제외
- REQ-FORCE-006 — 후보 응답: 결정적 정렬 + 후보별 안정적 식별자 · 도서명 · `sku` · `quantity` ·
  `shipped_quantity` · `logistics_status` · 잔여 용량 없음 표시(`quantity` NULL 또는 이미 완전 출고)

**모듈 3 — 강제 반영 불변식**

- REQ-FORCE-007 — 기존 경로와의 편차는 **정확히 두 가지**: `(order, sku)` 매칭 단계 대체 + 매칭
  이후 0 수량 처리 미승계. 그 외(음수·판독불가 사전 거부, 키 기준 합산, 수량 한도, 불감소, 임계
  전이, 원자성)는 동일 적용
- REQ-FORCE-008 — 게이트 통과 후 **REQ-FORCE-011로 제외된 행을 먼저 제거**하고, 살아남은 행만
  **지정 대상 식별자 기준**으로 그룹핑·합산(1개 행 그룹은 그 행의 수량), 대상당 판정·보고 1회.
  **살아남은 행이 없는 대상은 그룹 미형성 → 판정·쓰기·보고 어디에도 등장하지 않음.** 자격이 양수
  수량만 허용하고 비양수·판독불가 행이 그룹화 이전에 제거되므로 **평가되는 모든 그룹의 합산 수량은
  최소 1이며 0은 구조적으로 도달 불가**
- REQ-FORCE-009 — 그룹의 합산 수량(최소 1)이 한도 내면 `shipped_quantity` 증가 + `shipped_at` 갱신
  + 임계 도달 시 `"shipped"` 전이
- REQ-FORCE-010 — 한도 초과 시 대상 무변경 + 대상 단위 `quantity_exceeded` 보고(`null quantity`는
  용량 0)
- REQ-FORCE-011 — 음수 · **0** · 판독불가 수량 행은 **그룹화 이전에 제거**되어 어떤 대상의 합산에도
  기여하지 않음 + `invalid_total` 보고, 무변경
- REQ-FORCE-012 — `shipped_quantity` 불감소
- REQ-FORCE-013 — 쓰기 대상은 대상 LineItem의 `shipped_quantity` / `shipped_at` /
  `logistics_status` 3개뿐. LineItem 생성·삭제 없음, 다른 LineItem 필드 불변, `Order.status` /
  `ready_to_ship` 포함 어떤 Order 필드도 쓰지 않음(정상 경로 동작 답습)
- REQ-FORCE-014 — 요청 전체 단일 원자적 트랜잭션

**모듈 4 — 실행 단위 · 응답 계약 · 인증 · 기존 계약 보존**

- REQ-FORCE-015 — 선택된 전 행을 요청 1회로 처리
- REQ-FORCE-016 — **기존 3분류 응답 계약을 필드까지 그대로 재사용**(matched: `name`/`sku`/`total`/
  `line_item_id`/`shipped_quantity`/`quantity`/`logistics_status`, quantity_exceeded: 동일하되
  `logistics_status` 자리에 `reason`, unmatched: `name`/`sku`/`total`/`reason`). matched와
  quantity_exceeded 항목은 **대상 단위 1건**이며 `sku`는 **대상 LineItem 자신의 값**, `total`은 합산
  수량
- REQ-FORCE-017 — 기존 order 도메인과 동일한 인증 관례, 추가 권한 게이트 없음
- REQ-FORCE-018 — 기존 출고 엔드포인트 2개의 서버 측 계약 · 쿼리 수 무변경, 후보 목록 미동봉

**모듈 5 — 프론트엔드**

- REQ-FORCE-019 — 자격 행에만 선택 컨트롤 + 대상 지정 컨트롤 렌더(정확히 자격 행에만)
- REQ-FORCE-020 — 피커는 후보의 속성 + 잔여 용량 표시를 노출
- REQ-FORCE-021 — 매칭 실패 섹션의 `logistics_status` · 매칭 실패 사유 **코드값**은 한국어 라벨로
  렌더(SKU · 도서명 등 데이터 값은 대상 아님)
- REQ-FORCE-022 — 자격 · 선택 · 대상 지정을 모두 만족하는 행이 없으면 일괄 실행 컨트롤 비활성
- REQ-FORCE-023 — 요청에는 자격 · 선택 · 대상 지정을 모두 만족하는 행만 포함
- REQ-FORCE-024 — 실행 성공 시 표시 결과를 **병합 규칙**으로 재계산 + 선택 리셋: 제출한 행만
  `(주문 식별자, sku)` 키로 매칭 실패 목록에서 제거(재제출 불가) / 미제출 행은 유지되고 계속 선택
  가능 / 강제 응답의 성공·수량초과 항목을 각 목록에 추가 / 세 건수 재계산

## 인수 기준 목록 (요약)

`spec.md` ACCEPTANCE CRITERIA 기준 총 22개(AC-FORCE-001~022). REQ 24개 전량이 최소 1개 AC에
대응하며(traceability 검증표 포함), 6개 AC가 2~3개 REQ를 함께 검증한다. `acceptance.md`의 `Traces:`
목록과 검증 레이어 표기는 `spec.md`와 완전히 일치한다.

- AC-FORCE-001 `[FE]` — 5행 픽스처(자격 1 + 비자격 4)에서 컨트롤이 자격 행에만, 전체 선택도 그 행만
- AC-FORCE-002 `[BE]` — 게이트 위반 7종 각각이 요청 전체 400, 함께 제출한 유효 행도 미반영
- AC-FORCE-003 `[BE][FE]` — 5개 주문 후보를 1회 왕복으로 / 빈 집합은 빈 결과 + 무쓰기
- AC-FORCE-004 `[BE]` — `pk` 순서와 생성 순서를 어긋나게 한 동명 주문에서 최저 `pk` 선점
- AC-FORCE-005 `[BE]` — 5건 픽스처에서 취소·NULL SKU 제외, 용량 없음 2건 표시, 재조회 시 동일 순서
- AC-FORCE-006 `[BE]` — 두 경로 결과 동일성 + 미국창고 0 수량에서만 갈리는 유일한 편차(강제 경로는
  그룹 미형성으로 무변경 · 어느 목록에도 미등장)
- AC-FORCE-007 `[BE]` — 동일 대상 2행(6+5)이 개별 통과·합산 초과 → 무변경 + 병합 초과 항목 1건
- AC-FORCE-008 `[BE]` — 동일 대상 2행(4+6) 성공 → 1회 증가 + `"shipped"` + matched 1건, `sku`는
  대상 자신의 값, `total`은 10
- AC-FORCE-009 `[BE]` — 임계 미달 단일 행: 증가 + `shipped_at` 갱신 + 상태 불변
- AC-FORCE-010 `[BE]` — `quantity=null` 대상 양수 요청 → 무변경 + 수량초과
- AC-FORCE-011 `[BE]` — `-5` / `0` / 판독불가 / 미국창고 대상 `0` / **`quantity=null` 대상 `0`** /
  **이미 완전 출고된 대상 `0`** 여섯 행 전부 `invalid_total`, 네 대상 모두 `shipped_at`·
  `logistics_status` 포함 무변경이며 matched·quantity_exceeded 어느 목록에도 미등장(`0 >= 0` 전이
  경로 봉쇄), 음수는 같은 대상의 합산에서 제외되어 상쇄 불가
- AC-FORCE-012 `[BE]` — 혼합 결과 요청을 순서 바꿔 반복해도 `shipped_quantity` 불감소
- AC-FORCE-013 `[BE]` — 필드 단위 diff가 3개 필드로 한정, Order 집계 불변, 재계산 spy 미호출
- AC-FORCE-014 `[BE]` — 다중 대상 배치 중간 예외 주입 시 전량 롤백
- AC-FORCE-015 `[FE]` — 6행 선택 중 대상 지정 4행만, 요청 1회
- AC-FORCE-016 `[BE]` — 기존 응답 계약을 좁히지도 넓히지도 않음, 기존 렌더링 경로가 그대로 소비
- AC-FORCE-017 `[BE]` — 미인증 거부, 인증만으로 충분
- AC-FORCE-018 `[BE]` — 기존 엔드포인트 payload · 쿼리 수 무변경 회귀
- AC-FORCE-019 `[FE]` — 피커 후보 3건의 속성 + 완전 출고 후보의 용량 없음 표시
- AC-FORCE-020 `[FE]` — 상태 · 사유 코드값 미노출, 언더스코어 포함 `sku`는 원본 유지
- AC-FORCE-021 `[FE]` — 대상 미지정 시 비활성, 1건 지정 즉시 활성
- AC-FORCE-022 `[FE]` — 3행 중 2행 제출 시 네 결과: 제출한 2행 사라짐 / 미선택 1행 잔존 및 선택
  가능 / 성공·수량초과 항목이 각 섹션에 표시 / 세 건수가 표시 목록 길이와 일치. 선택 비움, 리로드
  없음

## 변경 대상 파일

**백엔드**: `backend/order/purchase_order_views.py`(MODIFY, 후보 배치 조회 뷰 + 강제 반영 뷰 신설) ·
`backend/order/urls.py`(MODIFY, 라우트 2건 — `<int:pk>/` 보다 먼저 등록) ·
`backend/order/tests/test_spec_016.py`(NEW) ·
`backend/order/models.py`(EXISTING, 변경 없음 · 마이그레이션 없음) ·
`backend/order/serializers.py`(EXISTING, 변경 없음 — `purchase_status` 부재로 재사용 불가) ·
`backend/order/tests/test_spec_015.py`(EXISTING, 무수정 전량 통과가 완료 조건)

**프론트엔드**: `frontend/src/services/outboundApi.ts`(MODIFY — 강제 실행 함수는 기존
`OutboundProcessResponse`를 그대로 반환, 기존 항목 타입 무수정) ·
`frontend/src/hooks/useOutboundQueries.ts`(MODIFY, 기존 뮤테이션 팩토리 재사용) ·
**`frontend/src/components/ResultSection.tsx`(EXISTING, 변경 없음 — `cells: string[]` 계약 유지,
외부 호출부 4곳 보호, 설계 결정 M)** ·
`frontend/src/pages/OutboundPage/` 하위 매칭 실패 섹션 전용 컴포넌트(NEW, colocate 테스트 동반) ·
`frontend/src/pages/OutboundPage/` 하위 라벨 매핑 모듈(NEW, `logistics_status`만 — `purchase_status`
맵은 만들지 않음) ·
`frontend/src/pages/OutboundPage/index.tsx`(MODIFY, 결과 슬롯 대체 배선 + `export function
OutboundPage` 유지) ·
`frontend/src/pages/OutboundPage/index.test.tsx`(MODIFY) ·
`frontend/src/services/outboundApi.test.ts`(MODIFY) ·
`frontend/src/hooks/useOutboundQueries.test.tsx`(MODIFY) ·
**`frontend/src/pages/InboundPage/index.tsx`(EXISTING, 회귀 검증 대상 — 공유 컴포넌트 호출부 3곳)** ·
**`frontend/src/pages/PurchaseOrders/tabs/DailyReviewTab.tsx`(EXISTING, 회귀 검증 대상 — 호출부 1곳)** ·
`frontend/src/router/index.tsx` · `frontend/src/components/Sidebar.tsx` ·
`frontend/src/types/order.ts`(모두 EXISTING, 변경 없음)

## Exclusions

- 수량 한도 우회 없음 — 강제가 우회하는 것은 `(order, sku)` 매칭뿐
- 자동 대상 추론 없음(빈 SKU 자동 반영 · 순차 분배 · 단일 후보 자동 선택 전부 미구현)
- `total == 0` 강제 처리 없음 — 미국창고 완료 신호를 강제 경로로 확장하지 않음(설계 결정 I)
- 신규 LineItem 생성 · 삭제 없음, 주문 원본 구성 불변
- 신규 모델 컬럼 · 마이그레이션 없음
- 감사 로그 테이블 없음
- `multiple_line_items` / `invalid_total` / `order_not_found` / `invalid_row` 강제 처리 없음
- 서버의 매칭 실패 사유 재도출 없음 — 자격 판정은 UI 책임(설계 결정 J)
- `quantity_exceeded` 섹션 변경 없음
- 출고 취소/되돌리기(undo) 없음 — SPEC-ORDER-015 배제 조항 승계
- `_recompute_order_aggregates` 및 그 호출부 소스 수정 없음(런타임 미호출은 REQ-FORCE-013,
  선행 불일치 해소는 후속 과제 1)
- 후보 조회의 쓰기 없음
- 행 단위 · 주문 단위 개별 HTTP 요청 없음
- 추가 권한 게이트 없음
- 신규 매칭 실패 사유 코드 없음 — 대상 미지정 · 무효 · 타 주문 소속 · 구조 오류는 요청 전체 400
- 부분 반영 없음 — 게이트 미통과 요청은 전량 거부(설계 결정 L)
- 결과 섹션 공유 컴포넌트(`ResultSection`) 시그니처 변경 없음 — 외부 호출부 4곳 영향
- SKU · 도서명 등 데이터 값의 이스케이프 · 변환 없음 — 금지 대상은 상태 · 사유 코드값뿐
- 라우팅 · 사이드바 변경 없음, 페이지 모듈 진입점 계약 유지
- 동시성 락 도입 없음(후속 과제 2)
- 강제 처리 결과의 Excel/CSV 내보내기 없음
