# 인수 기준 — SPEC-PURCHASE-ORDER-004

## 개요

아래의 Given-When-Then 시나리오가 모두 통과해야 구현 완료로 간주한다.

---

## 시나리오 1 — 기본 필드: 신규 LineItem에 purchase_status 기본값 적용

**Given** Django 마이그레이션이 적용된 상태이고, 새로운 `LineItem` 레코드가 `purchase_status` 지정 없이 생성될 때

**When** 해당 `LineItem`을 DB에서 조회하면

**Then** `purchase_status` 값이 `'unordered'`이다.

---

## 시나리오 2 — 기존 데이터 백필: 마이그레이션 후 기존 레코드 확인

**Given** 마이그레이션 적용 전에 이미 존재하는 `LineItem` 레코드들이 있을 때

**When** 마이그레이션이 실행되면

**Then** 기존 `LineItem` 레코드들의 `purchase_status`는 모두 `'unordered'`이다.

---

## 시나리오 3 — 미발주 목록 필터 보강: purchase_status가 unordered인 항목만 포함

**Given** DB에 다음 `LineItem`들이 존재한다:
- `LineItem A`: PO 미연결, `purchase_status='unordered'`
- `LineItem B`: PO 미연결, `purchase_status='on_hold'`
- `LineItem C`: PO 연결됨, `purchase_status='unordered'`

**When** 인증된 사용자가 `GET /api/purchase-orders/unordered/`를 호출하면

**Then** 응답에 `LineItem A`만 포함되고, `LineItem B`(상태 보류)와 `LineItem C`(PO 연결)는 포함되지 않는다.

---

## 시나리오 4 — 미발주 목록 응답에 purchase_status 필드 포함

**Given** PO 미연결이고 `purchase_status='unordered'`인 `LineItem`이 존재할 때

**When** 인증된 사용자가 `GET /api/purchase-orders/unordered/`를 호출하면

**Then** 응답의 각 항목에 `purchase_status` 필드가 포함되고 값은 `'unordered'`이다.

---

## 시나리오 5 — 단건 상태 변경: 유효한 status 코드로 업데이트

**Given** `id=42`인 `LineItem`이 존재하고 `purchase_status='unordered'`인 상태에서

**When** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/42/status/`에 `{"purchase_status": "on_hold"}` 를 전송하면

**Then** HTTP 200이 반환되고, DB에서 해당 `LineItem`의 `purchase_status`가 `'on_hold'`로 변경된다.

---

## 시나리오 6 — 단건 상태 변경: 존재하지 않는 id

**Given** `id=9999`인 `LineItem`이 DB에 존재하지 않을 때

**When** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/9999/status/`를 호출하면

**Then** HTTP 404가 반환된다.

---

## 시나리오 7 — 단건 상태 변경: 유효하지 않은 status 코드

**Given** `id=42`인 `LineItem`이 존재할 때

**When** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/42/status/`에 `{"purchase_status": "invalid_code"}` 를 전송하면

**Then** HTTP 400이 반환되고, 오류 메시지에 유효하지 않은 값임을 명시한다.

---

## 시나리오 8 — 단건 상태 변경: 미인증 요청

**Given** JWT 토큰 없이 요청이 들어올 때

**When** `PATCH /api/purchase-orders/line-items/42/status/`를 호출하면

**Then** HTTP 401이 반환된다.

---

## 시나리오 9 — 다건 상태 일괄 변경: 유효한 ids와 status

**Given** `id=10, 11, 12`인 `LineItem`들이 모두 `purchase_status='unordered'`인 상태에서

**When** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/bulk-status/`에 `{"ids": [10, 11, 12], "purchase_status": "order_cancelled"}` 를 전송하면

**Then** HTTP 200이 반환되고, 세 `LineItem` 모두 `purchase_status='order_cancelled'`로 변경되며, 응답에 `updated_count: 3`이 포함된다.

---

## 시나리오 10 — 다건 상태 일괄 변경: 일부 ids 미존재

**Given** DB에 `id=10, 11`은 존재하지만 `id=99`는 존재하지 않을 때

**When** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/bulk-status/`에 `{"ids": [10, 11, 99], "purchase_status": "cs_required"}` 를 전송하면

**Then** HTTP 200이 반환되고, `id=10, 11`의 `purchase_status`가 `'cs_required'`로 변경되며, 응답에 `missing_ids: [99]`가 포함된다.

---

## 시나리오 11 — 다건 상태 일괄 변경: 빈 ids 목록

**Given** 인증된 사용자가 `PATCH /api/purchase-orders/line-items/bulk-status/`에 `{"ids": [], "purchase_status": "in_stock"}` 를 전송할 때

**When** 요청이 처리되면

**Then** HTTP 400이 반환된다.

---

## 시나리오 12 — 프론트엔드: 인라인 상태 변경 후 행 제거

**Given** 미발주 현황 탭에 `LineItem A`(`purchase_status='unordered'`)가 표시되어 있을 때

**When** 사용자가 `LineItem A` 행의 드롭다운에서 `'주문보류'`를 선택하면

**Then** API 호출이 성공하고, `LineItem A` 행이 목록에서 즉시 사라진다.

---

## 시나리오 13 — 프론트엔드: 다건 선택 후 일괄 상태 변경

**Given** 미발주 현황 탭에서 사용자가 두 개의 행을 체크박스로 선택했을 때

**When** 일괄 상태 변경 UI에서 `'재고'`를 선택하고 확인하면

**Then** 두 `LineItem`에 대해 bulk-status API가 호출되고, 성공 후 두 행이 목록에서 제거된다.

---

## 엣지 케이스

| 케이스 | 기대 동작 |
|--------|----------|
| `purchase_status` 변경 후 다시 `'unordered'`로 복원 | 단건 PATCH 성공, 해당 항목이 미발주 탭에 다시 나타남 |
| PO에 연결된 `LineItem`의 `purchase_status`를 `'unordered'`로 변경 | API 성공, 단 미발주 탭에는 표시되지 않음 (PO 연결 조건) |
| 동일 `LineItem`에 대한 동시 다중 PATCH 요청 | Django ORM `update()` 사용으로 마지막 요청의 값이 적용됨 |
| 마이그레이션 전 `purchase_status` 컬럼 접근 | 마이그레이션 미적용 시 OperationalError 발생 — 마이그레이션 선적용 필수 |
| Shopify 동기화 시 `purchase_status` 값 덮어쓰기 | 동기화 로직에서 `purchase_status` 필드를 갱신하지 않으므로 값이 유지됨 |

---

## Definition of Done

- [ ] REQ-PO4-001 ~ REQ-PO4-010 모든 요구사항이 구현되었다.
- [ ] 위 시나리오 1~13이 테스트(수동 또는 자동)로 검증되었다.
- [ ] MySQL 8.0에서 마이그레이션이 오류 없이 실행된다.
- [ ] 기존 `PurchaseOrder` ↔ `LineItem` M2M 관계 동작이 변경되지 않았다.
- [ ] 미인증 요청에 HTTP 401이 반환된다.
- [ ] `ruff` 린터 오류가 없다.
- [ ] 프론트엔드 TypeScript 컴파일 오류가 없다.
- [ ] 코드 리뷰 후 master 브랜치에 머지 완료.
