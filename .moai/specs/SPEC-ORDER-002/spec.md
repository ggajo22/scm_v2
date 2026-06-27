---
id: SPEC-ORDER-002
version: 1.1.0
status: completed
created: 2026-06-21
updated: 2026-06-21
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-21 | ggajo | 최초 작성 — 주문관리 검색 기능 SPEC 초안 |
| 1.1.0 | 2026-06-21 | MoAI | sync — 구현 완료 처리, REQ-OS-012 구현 노트 추가 |

---

## 문제 정의

`SPEC-ORDER-001`에서 구현된 주문 목록 페이지(`/orders`)는 스토어·결제상태·배송상태·날짜 범위 필터를 제공하지만, **특정 주문번호나 ISBN으로 직접 검색하는 수단이 없다**.

관리자가 특정 주문(예: "#1234")이나 특정 도서(예: ISBN 9791234567890)가 포함된 주문을 조회하려면 현재 페이지 전체를 육안으로 스캔하거나 Shopify 어드민으로 이탈해야 한다. 이는 다음과 같은 운영 비효율을 초래한다:

- 고객 문의(특정 주문 확인) 대응 시간 증가
- 특정 도서 주문 현황 파악 불가
- 수백 건 이상의 주문 목록에서 수동 탐색 필요

---

## 솔루션 개요

기존 `GET /api/orders/` 엔드포인트에 `search` 쿼리 파라미터를 추가하고, 프론트엔드 주문 목록 페이지에 검색 입력 필드를 추가한다.

**백엔드 자동 판별 로직**:
- 입력값에서 선행 `"#"` 제거 후 숫자이면 → `order_number` exact match + `name` icontains
- 나머지 10~13자리 숫자이면 → 추가로 `line_items__sku` exact match (ISBN)
- 일반 fallback: `name__icontains` 항상 포함

단일 입력 필드로 주문번호와 ISBN을 자동 구분하므로, 별도 검색 유형 선택 UI는 불필요하다.

기존 `OrderListView.get_queryset()`에 약 12줄을 추가하는 것으로 구현이 완료되며, 기존 필터(store_type, financial_status 등)와 AND 결합이 유지된다.

---

## 요구사항

### 백엔드 검색 파라미터

**REQ-OS-001** (Event-Driven)
**When** `GET /api/orders/`에 `search` 파라미터가 제공되면, the 시스템 **shall** `name__icontains` 조건을 기본으로 포함하고, 입력값에서 선행 `"#"`을 제거한 결과가 숫자인 경우 `order_number` exact match(integer) 조건을 OR로 추가하여 쿼리셋을 필터링한다.

**REQ-OS-002** (Event-Driven)
**When** `search` 파라미터에서 선행 `"#"` 제거 후 자릿수가 10~13자리이고 모두 숫자인 경우, the 시스템 **shall** `line_items__sku` exact match 조건을 OR로 추가한다.

**REQ-OS-003** (Ubiquitous)
The 시스템 **shall** `search` 파라미터 적용 시 `distinct()`를 호출하여 `line_items` JOIN으로 인한 중복 레코드를 제거한다.

**REQ-OS-004** (Ubiquitous)
The `search` 필터 **shall** 기존 필터 파라미터(`store_type`, `financial_status`, `fulfillment_status`, `date_from`, `date_to`)와 AND로 결합된다.

**REQ-OS-005** (Unwanted Behavior)
**If** `search` 파라미터가 빈 문자열이거나 공백만 포함된 경우, **then** the 시스템 **shall** 검색 필터를 적용하지 않고 전체 주문을 반환한다.

---

### 프론트엔드 검색 UI

**REQ-OS-010** (Ubiquitous)
The 주문 목록 페이지의 필터 영역 **shall** 기존 드롭다운·날짜 입력 필드와 같은 행에 단일 텍스트 검색 입력 필드를 포함한다.

**REQ-OS-011** (Ubiquitous)
The 검색 입력 필드 **shall** `placeholder="주문번호 또는 ISBN"` 텍스트를 표시하여 사용 방법을 안내한다.

**REQ-OS-012** (Event-Driven)
**When** 검색 입력 필드에 텍스트를 입력하면, the 시스템 **shall** 마지막 입력으로부터 300ms 후에 자동으로 검색 API를 호출한다(debounce).

**REQ-OS-013** (Event-Driven)
**When** 검색 입력 필드에서 Enter 키를 누르면, the 시스템 **shall** debounce 대기 없이 즉시 검색 API를 호출한다.

**REQ-OS-014** (Event-Driven)
**When** 검색어를 지워 빈 문자열이 되면, the 시스템 **shall** 즉시 전체 주문 목록을 재조회한다.

**REQ-OS-015** (Ubiquitous)
The `OrderListParams` 타입 **shall** `search?: string` 필드를 포함한다.

**REQ-OS-016** (Ubiquitous)
The `useOrders` 훅 **shall** `params.search`가 존재할 경우 `searchParams`에 `search` 키를 추가하여 API 호출 시 전달한다.

---

### 검색 결과 없음 처리

**REQ-OS-020** (State-Driven)
**While** 검색 결과가 0건인 경우, the 주문 목록 테이블 **shall** 데이터 행 대신 "검색 결과가 없습니다" 메시지를 표시한다.

---

## 제외 사항 (What NOT to Build)

- **고객명·이메일·상품명 검색**: 이 SPEC은 주문번호와 ISBN(sku) 검색만 대상으로 한다. 다른 필드 검색은 별도 SPEC으로 처리한다.
- **저장된 검색어·검색 히스토리**: 검색어 저장 또는 자동완성 기능은 이 SPEC의 범위가 아니다.
- **검색 결과 하이라이팅**: 검색어가 포함된 텍스트를 강조 표시하는 기능은 구현하지 않는다.
- **전문 검색(Full-text search) 엔진**: Elasticsearch, PostgreSQL FTS 등은 도입하지 않는다. Django ORM `Q` 객체를 사용한 단순 필터링으로 구현한다.
- **새 DB 마이그레이션**: 기존 모델 변경이 없으므로 마이그레이션 파일을 추가하지 않는다.
- **새 API 엔드포인트**: 기존 `GET /api/orders/`에 파라미터만 추가하며 신규 엔드포인트는 생성하지 않는다.

---

## 구현 노트 (Implementation Notes)

> 이 섹션은 /moai sync 단계에서 실제 구현과 SPEC의 차이를 기록합니다.

### 구현 완료 (2026-06-21)

**구현된 요구사항**: REQ-OS-001, REQ-OS-002, REQ-OS-003, REQ-OS-004, REQ-OS-005, REQ-OS-010, REQ-OS-011, REQ-OS-013, REQ-OS-014, REQ-OS-015, REQ-OS-016, REQ-OS-020

**수정된 요구사항**:
- **REQ-OS-012** (300ms debounce): 디바운스 대신 Enter 키 트리거 방식으로 구현함. 이유: 추가 npm 패키지 없이 동일한 UX 목표(의도치 않은 실시간 API 호출 방지)를 달성할 수 있었음. REQ-OS-013(Enter 즉시 검색)은 동일하게 구현됨. 후속 필요 시 `useDebounce` 훅 추가로 개선 가능.

**기술 결정**:
- 백엔드: `Q` 객체 OR 결합 + `distinct()` — LineItem JOIN으로 인한 중복 방지
- 프론트엔드: 로컬 state(`searchInput`) 분리 — 타이핑 중 즉각적인 UI 반응, Enter 시에만 params 업데이트
- 신규 테스트 7개 추가 (전체 161개 통과)
