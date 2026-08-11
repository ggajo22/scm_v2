---
id: SPEC-ORDER-015
document: acceptance
version: 1.0.2
status: draft
updated: 2026-08-10
---

# 인수 기준 — SPEC-ORDER-015 출고 처리

Given/When/Then 형태의 실행 가능한 테스트 시나리오. 각 시나리오는 `spec.md`의
AC-OUTBOUND-XXX/REQ-OUTBOUND-XXX ID를 인용해 상호 추적된다.

## 정상 경로 시나리오

### AC-OUTBOUND-001 — 정상 매칭 및 부분 출고 반영

Traces: REQ-OUTBOUND-003, REQ-OUTBOUND-004, REQ-OUTBOUND-008

- **Given**: `Order.name="#37349"`의 LineItem이 `sku="ISBN001"`, `quantity=10`,
  `shipped_quantity=0`으로 존재한다.
- **When**: `{name: "#37349", sku: "ISBN001", total: 4}` 행을 출고 처리 요청으로 제출한다.
- **Then**: 해당 LineItem의 `shipped_quantity=4`가 되고 `shipped_at`이 요청 처리 시각으로
  갱신된다. `4 < 10`이므로 `logistics_status`는 변경되지 않는다. 응답의 matched 리스트에
  해당 행이 포함된다.

### AC-OUTBOUND-002 — 두 번의 별도 요청에 걸친 부분 출고 누적 → 완전 출고 전이 (부분 출고 across 2 uploads)

Traces: REQ-OUTBOUND-008, REQ-OUTBOUND-010, REQ-OUTBOUND-010a

- **Given**: AC-OUTBOUND-001 처리 후 `shipped_quantity=4`, `quantity=10`인 LineItem이 존재한다.
- **When**: 별도의 두 번째 출고 처리 요청에서 `{name: "#37349", sku: "ISBN001", total: 6}` 행을
  제출한다.
- **Then**: `shipped_quantity=10`(4+6)이 되고, `10 >= quantity(10)`이므로 `logistics_status`가
  `"shipped"`로 자동 전이된다. `shipped_at`은 두 번째 요청의 처리 시각으로 갱신된다.

## 예외/엣지 케이스 시나리오

### AC-OUTBOUND-003 — 수량초과 거부 (반영하지 않음)

Traces: REQ-OUTBOUND-009

- **Given**: `quantity=10`, `shipped_quantity=8`인 LineItem이 존재한다.
- **When**: `{name: "#37349", sku: "ISBN001", total: 5}` 행을 제출한다(`8+5=13 > 10`).
- **Then**: 해당 LineItem의 `shipped_quantity`와 `shipped_at`은 변경되지 않는다.
  `logistics_status`도 변경되지 않는다. 해당 행은 "수량초과" 리스트에 현재
  `shipped_quantity=8`, `quantity=10`, 요청 `total=5` 정보와 함께 포함된다.

### AC-OUTBOUND-004 — 매칭 실패 (존재하지 않는 주문명)

Traces: REQ-OUTBOUND-005

- **Given**: `Order.name="#99999"`가 시스템에 존재하지 않는다.
- **When**: `{name: "#99999", sku: "ISBN001", total: 3}` 행을 제출한다.
- **Then**: 어떤 LineItem도 수정되지 않는다. 해당 행은 "매칭 실패" 리스트에 포함된다.

### AC-OUTBOUND-004a — 매칭 실패 (주문은 존재하나 SKU 불일치)

Traces: REQ-OUTBOUND-005

- **Given**: `Order.name="#37349"`는 존재하지만 그 주문에 `sku="ISBN999"`인 LineItem이 없다.
- **When**: `{name: "#37349", sku: "ISBN999", total: 2}` 행을 제출한다.
- **Then**: 어떤 LineItem도 수정되지 않는다. 해당 행은 "매칭 실패" 리스트에 포함된다.

### AC-OUTBOUND-005 — 동일 요청 내 중복 행 합산 (duplicate row within same upload)

Traces: REQ-OUTBOUND-007

- **Given**: `quantity=10`, `shipped_quantity=0`인 LineItem이 존재한다.
- **When**: 동일 요청(하나의 Excel 업로드 또는 하나의 수동 입력 제출) 안에
  `{name: "#37349", sku: "ISBN001", total: 3}`과 `{name: "#37349", sku: "ISBN001", total: 4}`
  두 행이 함께 제출된다.
- **Then**: 두 값이 먼저 7로 합산된 뒤 1회 판정되어 `shipped_quantity=7`로 반영된다. 응답의
  matched 리스트에는 병합된 결과 1건만 나타나며, 행별로 2건이 각각 나타나지 않는다.

### AC-OUTBOUND-005a — 동일 요청 내 중복 행 합산이 한도를 초과하는 경우

Traces: REQ-OUTBOUND-007, REQ-OUTBOUND-009

- **Given**: `quantity=10`, `shipped_quantity=0`인 LineItem이 존재한다.
- **When**: 동일 요청 안에 `total: 6`과 `total: 5`인 두 행(합산 11 > 10)이 제출된다.
- **Then**: 합산 후 판정에서 초과가 감지되어 `shipped_quantity`가 변경되지 않는다. "수량초과"
  리스트에 병합된 결과 1건이 포함되며, 행별로 2건이 각각 나타나지 않는다.

### AC-OUTBOUND-006 — 복수 매칭(동일 SKU 중복 LineItem) 시 매칭 실패 처리

Traces: REQ-OUTBOUND-005a

- **Given**: `Order.name="#37349"`에 동일 `sku="ISBN001"`을 가진 LineItem이 2건 존재한다
  (SPEC-SHOPIFY-SKU-SET-002 번들 확장 시나리오).
- **When**: `{name: "#37349", sku: "ISBN001", total: 3}` 행을 제출한다.
- **Then**: 어느 LineItem도 수정되지 않는다. 해당 행은 "매칭 실패" 리스트에 포함된다(분배 규칙
  없음, 설계 결정 A).

### AC-OUTBOUND-007 — Excel 헤더 인식 실패

Traces: REQ-OUTBOUND-012a

- **Given**: 업로드된 `.xlsx` 파일의 헤더 행에 `Name`/`Lineitem sku`/`Total` 중 하나 이상이
  별칭 목록과 매칭되지 않는다.
- **When**: 해당 파일을 Excel 업로드 엔드포인트에 제출한다.
- **Then**: HTTP 422 응답을 받는다. 어떤 LineItem도 수정되지 않는다.

### AC-OUTBOUND-008 — 기존 렉번호 페이지/타 도메인 데이터 무영향 회귀 확인

Traces: REQ-OUTBOUND-019

- **Given**: `/rack-number` 페이지, `book.Info.qty`, `order.WarehouseStock`,
  `LineItem.fulfillment_status`가 기존 상태로 존재한다.
- **When**: 성공/매칭실패/수량초과가 혼합된 출고 처리 요청을 제출한다(어떤 결과 조합이든).
- **Then**: `LineItem.rack_number`, `LineItem.fulfillment_status`, `book.Info.qty`,
  `order.WarehouseStock` 레코드는 요청 전후로 값이 동일하다. SPEC-ORDER-013/014 기존 테스트
  스위트가 모두 그대로 통과한다.

## 데이터 모델 · 매칭 로직 · 상태 전이 시나리오

이 절은 plan-auditor 리뷰(iteration 1) D2 대응으로 `spec.md`에 추가된 AC-OUTBOUND-009~013에
대응한다.

### AC-OUTBOUND-009 — 데이터 모델 필드 존재 및 기본값

Traces: REQ-OUTBOUND-001, REQ-OUTBOUND-002

- **Given**: 신규 생성된 LineItem 레코드다.
- **When**: 해당 LineItem을 조회한다.
- **Then**: `shipped_quantity` 필드가 존재하며 기본값 `0`을 가진다. `shipped_at` 필드가 존재하며
  nullable이다.

### AC-OUTBOUND-009a — 미처리 LineItem의 `shipped_at` null 유지

Traces: REQ-OUTBOUND-002a

- **Given**: 어떤 LineItem이 아직 어떤 출고 처리 이벤트에도 영향을 받지 않았다.
- **When**: 해당 LineItem을 조회한다.
- **Then**: `shipped_at=null`이다.

### AC-OUTBOUND-010 / AC-OUTBOUND-010a — `Order.name` 매칭, `order_number` 미사용

Traces: REQ-OUTBOUND-003, REQ-OUTBOUND-003a

- **Given**: `Order.name="#37349"`이고 `Order.order_number=37349`가 아닌 임의의 값(예: 다른 정수)으로
  설정된 Order가 존재한다.
- **When**: `{name: "#37349", sku: "ISBN001", total: 1}` 행을 제출한다.
- **Then**: 매칭은 `Order.name` 값만으로 성립하며, `Order.order_number` 값과의 일치 여부는 매칭
  결과에 어떠한 영향도 주지 않는다.

### AC-OUTBOUND-011 — Order+SKU 필터 기반 LineItem 매칭 시도

Traces: REQ-OUTBOUND-004

- **Given**: Order가 매칭되었고 그 Order에 `sku="ISBN001"`인 LineItem이 정확히 1건 존재한다.
- **When**: 해당 `sku`를 포함한 행을 제출한다.
- **Then**: 시스템은 매칭된 Order와 요청 `sku` 두 조건을 모두 사용해 LineItem을 조회하고, 해당
  LineItem 1건을 처리 대상으로 확정한다.

### AC-OUTBOUND-012 — 현재 `logistics_status` 무관 처리 허용

Traces: REQ-OUTBOUND-006

- **Given**: `logistics_status="not_shipped"`인 LineItem과 `logistics_status="received"`인
  LineItem이 각각 존재한다(둘 다 `outbound_scheduled`가 아님).
- **When**: 두 LineItem에 대해 각각 정상적인 출고 처리 행을 제출한다.
- **Then**: 두 LineItem 모두 현재 `logistics_status`와 무관하게 정상적으로 매칭·반영된다 —
  `outbound_scheduled` 상태만 허용하는 별도 제약은 존재하지 않는다.

### AC-OUTBOUND-013 — 임계값 미달 시 `logistics_status` 무변경

Traces: REQ-OUTBOUND-010a

- **Given**: `quantity=10`, `shipped_quantity=3`인 LineItem이 존재한다.
- **When**: `{total: 2}` 행을 제출한다(반영 후 `shipped_quantity=5 < 10`).
- **Then**: `shipped_quantity=5`로 갱신되지만 `logistics_status`는 이전 값 그대로 유지된다.

## 백엔드 API · 응답 계약 시나리오

이 절은 AC-OUTBOUND-014~016에 대응한다.

### AC-OUTBOUND-014 — 두 엔드포인트의 원자적 공용 처리

Traces: REQ-OUTBOUND-011, REQ-OUTBOUND-013

- **Given**: 매칭 성공 행 1건과 매칭 실패 행 1건이 섞인 요청을 준비한다.
- **When**: 이 요청을 (a) 수동 입력 엔드포인트와 (b) Excel 업로드 엔드포인트 각각에 동일한
  내용으로 제출한다.
- **Then**: 두 엔드포인트 모두 동일한 매칭/판정 결과(성공 1건, 매칭 실패 1건)를 반환하며, 각
  요청은 단일 트랜잭션으로 처리되어 부분 반영이 발생하지 않는다.

### AC-OUTBOUND-015 — Excel 헤더 별칭 파싱 성공 경로

Traces: REQ-OUTBOUND-012

- **Given**: 업로드 파일의 헤더가 `["주문번호", "Lineitem SKU", "수량"]`처럼 별칭 목록과
  대소문자 무시 substring으로 매칭되는 형태다(정확히 `Name`/`Lineitem sku`/`Total`이 아니어도 됨).
- **When**: 해당 파일을 업로드한다.
- **Then**: 헤더가 정상 인식되어 데이터 행 파싱이 성공하고, 이후 매칭/판정 로직이 정상 수행된다.

### AC-OUTBOUND-016 — 3분류 응답 계약

Traces: REQ-OUTBOUND-014

- **Given**: 성공/매칭실패/수량초과가 각각 1건 이상씩 섞인 요청을 제출한다.
- **When**: 응답을 확인한다.
- **Then**: 응답에 matched/unmatched/quantity_exceeded 3개 카테고리가 각각 존재하며, 각 카테고리는
  count와 item 리스트를 모두 포함한다.

## 프론트엔드 시나리오

이 절은 AC-OUTBOUND-017~020에 대응한다.

### AC-OUTBOUND-017 — 독립 페이지 및 사이드바 진입점

Traces: REQ-OUTBOUND-015

- **Given**: 로그인한 관리자가 사이드바를 조회한다.
- **When**: "출고 처리" 메뉴 항목을 클릭한다.
- **Then**: `/outbound` 독립 페이지로 이동하며, `/rack-number` 페이지의 어떤 컴포넌트나 상태도
  공유하지 않는다.

### AC-OUTBOUND-018 — 수동 입력 폼 + Excel 업로드 컨트롤 동시 노출

Traces: REQ-OUTBOUND-016

- **Given**: 출고 처리 페이지에 진입한다.
- **When**: 페이지 초기 렌더링을 확인한다.
- **Then**: 수동 텍스트/표 입력 폼과 Excel 파일 업로드 컨트롤이 모두 화면에 표시된다.

### AC-OUTBOUND-019 — 결과 3섹션 시각화

Traces: REQ-OUTBOUND-017

- **Given**: 성공/매칭실패/수량초과가 섞인 처리 요청이 완료되었다.
- **When**: 결과 화면을 확인한다.
- **Then**: 성공/매칭 실패/수량초과 3개의 시각적으로 구분된 섹션이 각각 count와 item 목록과 함께
  렌더링된다.

### AC-OUTBOUND-020 — 리셋 컨트롤 동작

Traces: REQ-OUTBOUND-018

- **Given**: 결과 화면이 표시된 상태다.
- **When**: "다시 처리하기" 버튼을 클릭한다.
- **Then**: 입력 폼과 결과 화면이 초기 상태로 리셋되어, 페이지 새로고침 없이 연속으로 새 출고
  처리 요청을 제출할 수 있다.

## 품질 게이트 (Quality Gate)

- 백엔드 pytest: REQ-OUTBOUND-001~019 전 항목(하위 항목 002a/003a/005a/010a/012a 포함)에 대해
  최소 1개 이상의 테스트 매핑 (AC-OUTBOUND-001~020 및 하위 항목 004a/009a/010a 전량 포함).
- 프론트엔드 테스트: 수동 입력 폼 제출, Excel 업로드, 3분류 결과 렌더링, 폼 리셋 동작에 대한
  테스트 포함.
- 회귀 테스트: SPEC-ORDER-013(51 pytest + 15 프론트) / SPEC-ORDER-014(13 pytest + 26 프론트)
  기존 테스트 전량 통과.
- 마이그레이션: `0035_lineitem_add_shipped_fields.py` 적용 후 기존 데이터 손실/오류 없이
  `python manage.py migrate` 성공.
- Exclusions 위반 없음: `book.Info.qty`, `order.WarehouseStock`,
  `LineItem.fulfillment_status`, `LOGISTICS_STATUS_CHOICES` enum 값에 대한 변경이 diff에
  존재하지 않아야 한다.

## Definition of Done

- [ ] `LineItem.shipped_quantity`/`shipped_at` 필드 + 마이그레이션 적용 완료
- [ ] `OutboundProcessView`(수동입력), `UploadOutboundView`(Excel) 및 공용 처리 함수 구현 완료
- [ ] REQ-OUTBOUND-001~019 전 항목(하위 항목 포함) 및 AC-OUTBOUND-001~020(하위 항목
      004a/009a/010a 포함) 테스트 통과
- [ ] 신규 `/outbound` 프론트엔드 페이지 + 사이드바 메뉴 항목 구현 완료
- [ ] SPEC-ORDER-013/014 기존 테스트 스위트 회귀 없이 전량 통과
- [ ] `product.md` 기능 목록에 SPEC-ORDER-015 항목 추가(sync 단계)
- [ ] `spec.md` `status: draft → completed` 전이 및 HISTORY 갱신
