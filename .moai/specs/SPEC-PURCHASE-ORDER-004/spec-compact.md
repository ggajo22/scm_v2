# SPEC-PURCHASE-ORDER-004 — 컴팩트 참조

LineItem별 발주 상태 관리 (`purchase_status` 필드 추가)

---

## 요구사항 요약 (EARS)

| ID | 유형 | 요약 |
|----|------|------|
| REQ-PO4-001 | Ubiquitous | `LineItem`은 `purchase_status` 필드를 가지며 6개 선택지(`unordered` / `on_hold` / `order_cancelled` / `other_publisher` / `cs_required` / `in_stock`) 중 하나, 기본값 `unordered` |
| REQ-PO4-002 | Event-Driven | 마이그레이션 실행 시, 기존 레코드 포함 `purchase_status`가 `'unordered'`로 초기화됨 |
| REQ-PO4-003 | Event-Driven | `GET /unordered/` — M2M 미연결 AND `purchase_status='unordered'` 두 조건 모두 만족하는 항목만 반환 |
| REQ-PO4-004 | Event-Driven | `GET /unordered/` 응답 각 항목에 `purchase_status` 필드 포함 |
| REQ-PO4-005 | Complex | `PATCH /line-items/{id}/status/` — 유효 값이면 HTTP 200, 미존재 id면 HTTP 404, 유효하지 않은 값이면 HTTP 400 |
| REQ-PO4-006 | Complex | `PATCH /line-items/bulk-status/` — 원자적 다건 업데이트, 빈 ids 또는 유효하지 않은 status면 HTTP 400, 누락 id는 응답에 명시 |
| REQ-PO4-007 | Ubiquitous | 두 PATCH 엔드포인트 모두 JWT 인증 필요, 미인증 시 HTTP 401 |
| REQ-PO4-008 | Event-Driven | 미발주 탭 렌더링 시 `purchase_status` 한국어 레이블 컬럼 표시 |
| REQ-PO4-009 | Event-Driven | 행 드롭다운 변경 시 단건 PATCH 호출, 비-unordered 상태로 변경 시 행 제거 |
| REQ-PO4-010 | Event-Driven | 다건 선택 후 일괄 변경 시 bulk-status PATCH 호출, 비-unordered 항목 행 제거 |

---

## 인수 기준 요약 (Given-When-Then)

| # | 시나리오 | 기대 결과 |
|---|----------|----------|
| 1 | 신규 LineItem 생성 (purchase_status 미지정) | `purchase_status='unordered'` |
| 2 | 마이그레이션 적용 후 기존 레코드 조회 | 모든 기존 레코드 `purchase_status='unordered'` |
| 3 | `GET /unordered/` — PO 미연결·unordered / PO 미연결·on_hold / PO 연결·unordered 혼재 | unordered·PO미연결 항목만 반환 |
| 4 | `GET /unordered/` 응답 항목 확인 | 각 항목에 `purchase_status` 필드 존재 |
| 5 | `PATCH /line-items/42/status/` 유효 값 | HTTP 200, DB 값 변경 |
| 6 | `PATCH /line-items/9999/status/` 미존재 id | HTTP 404 |
| 7 | `PATCH /line-items/42/status/` 유효하지 않은 코드 | HTTP 400 |
| 8 | 미인증 PATCH 요청 | HTTP 401 |
| 9 | `PATCH /bulk-status/` 3개 유효 ids | HTTP 200, 3건 변경, `updated_count: 3` |
| 10 | `PATCH /bulk-status/` 일부 ids 미존재 | HTTP 200, 존재하는 ids만 변경, `missing_ids` 반환 |
| 11 | `PATCH /bulk-status/` 빈 ids | HTTP 400 |
| 12 | 프론트 드롭다운으로 비-unordered 선택 | API 성공, 행 즉시 제거 |
| 13 | 프론트 다건 선택 → 일괄 변경 | bulk-status 호출 성공, 변경된 행 제거 |

---

## 핵심 제약

- MySQL 8.0 (AWS RDS) — PostgreSQL 전용 DDL 사용 금지
- 기존 `PurchaseOrder` ↔ `LineItem` M2M 관계 변경 없음
- Shopify 동기화 시 `purchase_status` 덮어쓰기 없음
- 변경 이력(audit log) 기능 미포함 (제외 범위)
