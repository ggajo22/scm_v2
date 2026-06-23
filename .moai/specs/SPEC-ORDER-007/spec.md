---
id: SPEC-ORDER-007
title: 발주 확정 화면 — 상태·발주처·메모 편집
status: draft
created: 2026-06-23
updated: 2026-06-23
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 버전  | 날짜       | 변경 내용           | 작성자 |
|-------|------------|---------------------|--------|
| 1.0.0 | 2026-06-23 | 최초 작성           | ggajo  |

---

## 문제 정의

현재 발주 확정 화면(ConfirmOrderTab)은 SKU별 수량과 단가만 편집할 수 있다. 담당자는 발주 처리 과정에서 발주처를 변경하거나 발주 상태를 조정해야 할 때, 별도의 화면이나 API를 사용해야 한다. 또한 SKU별 메모를 남길 수 있는 기능 자체가 존재하지 않아 처리 이력 관리가 어렵다.

핵심 문제:
- 발주 확정 시 발주처(distributor)를 수정하려면 별도 작업이 필요하다.
- 발주 상태(purchase_status)를 발주 확정과 동시에 설정할 수 없다.
- SKU별 메모를 저장할 필드가 데이터베이스에 존재하지 않는다.

---

## 솔루션 개요

ConfirmOrderTab의 각 SKU 행에 발주처 텍스트 입력, 발주 상태 드롭다운, 메모 입력란을 추가한다. 세 필드 모두 "발주 확정" 버튼 클릭 시 기존 수량·단가와 함께 서버로 전송되어 DB에 한 번에 저장된다. 백엔드는 `LineItem` 모델에 `note` 필드를 추가하고, `ConfirmOrderView`가 기존 `distributor`와 함께 `purchase_status`, `note`를 수신·저장하도록 확장한다.

---

## 요구사항

### LineItem note 필드 추가

**REQ-CON-001** (Ubiquitous)
`LineItem` 모델은 `note = models.TextField(null=True, blank=True)` 필드를 포함해야 한다.

**REQ-CON-002** (Ubiquitous)
`note` 필드 추가를 위한 Django 마이그레이션 파일 `0015_lineitem_add_note.py`가 존재해야 한다.

**REQ-CON-003** (Ubiquitous)
`LineItem` serializer는 `note` 필드를 읽기·쓰기 가능한 필드로 노출해야 한다.

---

### 발주처 편집

**REQ-CON-010** (Ubiquitous)
`ConfirmItem` TypeScript 인터페이스는 `distributor: string` 필드를 포함해야 한다.

**REQ-CON-011** (Ubiquitous)
`ConfirmOrderTab`의 각 SKU 행은 발주처를 입력할 수 있는 텍스트 입력란을 표시해야 하며, 해당 SKU의 현재 `confirmed_distributor` 값으로 초기화되어야 한다.

**REQ-CON-012** (Ubiquitous)
`ConfirmOrderView`는 요청 본문의 각 항목에서 `distributor` 값을 수신하여 해당 SKU의 `LineItem.confirmed_distributor` 필드를 업데이트해야 한다.

**REQ-CON-013** (Unwanted)
발주처 값이 빈 문자열인 경우, `ConfirmOrderView`는 400 Bad Request를 반환해야 한다.

---

### 발주 상태 편집

**REQ-CON-020** (Ubiquitous)
`ConfirmItem` TypeScript 인터페이스는 `purchase_status?: string` 필드를 포함해야 한다.

**REQ-CON-021** (Ubiquitous)
`ConfirmOrderTab`의 각 SKU 행은 `PURCHASE_STATUS_OPTIONS`를 선택지로 하는 드롭다운을 표시해야 하며, 해당 SKU의 현재 `purchase_status` 값으로 초기화되어야 한다.

**REQ-CON-022** (Ubiquitous)
`ConfirmOrderView`는 요청 본문의 각 항목에서 `purchase_status` 값을 수신하여 해당 SKU의 모든 `LineItem`의 `purchase_status` 필드를 업데이트해야 한다.

**REQ-CON-023** (Ubiquitous)
`purchase_status` 값이 요청 본문에 포함되지 않은 경우, 기존 `purchase_status` 값을 유지하고 변경하지 않아야 한다.

---

### 메모 편집

**REQ-CON-030** (Ubiquitous)
`ConfirmItem` TypeScript 인터페이스는 `note?: string | null` 필드를 포함해야 한다.

**REQ-CON-031** (Ubiquitous)
`ConfirmOrderTab`의 각 SKU 행은 메모를 입력할 수 있는 텍스트 입력란을 표시해야 하며, placeholder는 "메모 입력..."이어야 한다.

**REQ-CON-032** (Ubiquitous)
`ConfirmOrderView`는 요청 본문의 각 항목에서 `note` 값을 수신하여 해당 SKU의 모든 `LineItem`의 `note` 필드를 업데이트해야 한다.

**REQ-CON-033** (Ubiquitous)
`note` 값이 빈 문자열이거나 요청 본문에 포함되지 않은 경우, 기존 `note` 값을 유지하고 변경하지 않아야 한다.

**REQ-CON-034** (Ubiquitous)
`note` 값으로 명시적 `null`이 전송된 경우, 해당 SKU의 모든 `LineItem`의 `note` 필드를 `null`로 초기화해야 한다.

---

### UI/UX

**REQ-CON-040** (Ubiquitous)
`ConfirmOrderTab`의 테이블 컬럼 순서는 다음과 같아야 한다: SKU | 발주처 | 발주상태 | 수량 | 단가 | 메모. 기존 수량·단가 컬럼은 제거하지 않고 유지한다.

**REQ-CON-041** (Ubiquitous)
메모 입력란은 최대 500자(max-length=500)로 제한되어야 한다.

**REQ-CON-042** (Unwanted)
발주처·발주상태·메모 변경은 "발주 확정" 버튼 클릭 전까지 DB에 저장되어서는 안 된다. 화면 내 상태(local state)로만 관리한다.

---

## 구현 범위

### 수정·생성 대상 파일

**Backend**

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `backend/order/models.py` | 수정 | `LineItem`에 `note = models.TextField(null=True, blank=True)` 추가 |
| `backend/order/migrations/0015_lineitem_add_note.py` | 신규 생성 | `note` 필드 추가 마이그레이션 |
| `backend/order/serializers.py` | 수정 | `LineItem` serializer에 `note` 필드 추가 |
| `backend/order/purchase_order_views.py` | 수정 | `ConfirmOrderView`에서 `note`, `purchase_status` 수신 및 처리 로직 추가 |

**Frontend**

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `frontend/src/services/purchaseOrderApi.ts` | 수정 | `ConfirmItem` 인터페이스에 `purchase_status?`, `note?` 필드 추가 |
| `frontend/src/pages/PurchaseOrders/tabs/ConfirmOrderTab.tsx` | 수정 | 각 행에 발주처 텍스트 입력, 발주상태 드롭다운, 메모 입력란 추가 |

**Tests**

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `backend/order/tests/test_purchase_order_confirm.py` | 신규 또는 확장 | `ConfirmOrderView`의 `note`, `purchase_status`, `distributor` 처리 시나리오 테스트 |

---

## 제외 범위 (What NOT to Build)

- 발주처·발주상태·메모를 "발주 확정" 버튼과 독립적으로 자동 저장(auto-save)하는 기능은 이번 범위에 포함하지 않는다.
- `PURCHASE_STATUS_OPTIONS`에 새로운 상태 값을 추가하는 것은 이번 범위에 포함하지 않는다.
- LineItem 개별 단위의 메모 조회·수정 전용 API 엔드포인트 신설은 이번 범위에 포함하지 않는다.
- 발주처 입력을 preset 드롭다운으로 전환하는 것은 이번 범위에 포함하지 않는다.

---

## 인수 조건

### AC-001: 발주처 변경 후 확정 저장

**Given** ConfirmOrderTab에서 특정 SKU의 발주처 입력란에 기존 값과 다른 값을 입력한 상태이고,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 해당 SKU의 `LineItem.confirmed_distributor`가 입력한 값으로 DB에 저장되어야 한다.

### AC-002: 발주처 빈 문자열 시 400 반환

**Given** 발주처 입력란이 비어 있는 상태로,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 서버가 400 Bad Request를 반환하고, DB는 변경되지 않아야 한다.

### AC-003: 발주 상태 선택 후 확정 저장

**Given** ConfirmOrderTab에서 특정 SKU의 발주 상태 드롭다운에서 "주문보류(on_hold)"를 선택한 상태이고,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 해당 SKU에 해당하는 모든 `LineItem.purchase_status`가 `on_hold`로 DB에 저장되어야 한다.

### AC-004: 발주 상태 미변경 시 기존 값 유지

**Given** ConfirmOrderTab에서 특정 SKU의 발주 상태 드롭다운을 변경하지 않은 상태이고,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 해당 SKU의 `LineItem.purchase_status`는 기존 값 그대로 유지되어야 한다.

### AC-005: 메모 입력 후 확정 저장

**Given** ConfirmOrderTab에서 특정 SKU의 메모 입력란에 500자 이하의 텍스트를 입력한 상태이고,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 해당 SKU에 해당하는 모든 `LineItem.note`가 입력한 텍스트로 DB에 저장되어야 한다.

### AC-006: 메모 null 전송 시 초기화

**Given** 기존에 메모가 저장된 SKU에 대해 `note: null`을 명시적으로 전송하면,
**When** `ConfirmOrderView`가 해당 요청을 처리하면,
**Then** 해당 SKU의 모든 `LineItem.note`가 `null`로 초기화되어야 한다.

### AC-007: 메모 미입력 시 기존 값 유지

**Given** 기존에 메모가 저장된 SKU에 대해 메모 입력란을 비워두거나 전송하지 않으면,
**When** "발주 확정" 버튼을 클릭하면,
**Then** 해당 SKU의 `LineItem.note`는 기존 값 그대로 유지되어야 한다.

### AC-008: 테이블 컬럼 순서 및 기존 컬럼 유지

**Given** ConfirmOrderTab이 렌더링된 상태에서,
**When** 화면을 확인하면,
**Then** 컬럼 순서가 SKU | 발주처 | 발주상태 | 수량 | 단가 | 메모 순이어야 하고, 수량·단가 컬럼이 모두 표시되어야 한다.

### AC-009: 메모 최대 길이 제한

**Given** 메모 입력란에 501자 이상의 텍스트를 입력하려 할 때,
**When** 입력을 시도하면,
**Then** 500자를 초과하는 문자는 입력되지 않아야 한다 (HTML `maxlength` 속성으로 제한).

### AC-010: 버튼 클릭 전 DB 무변경

**Given** ConfirmOrderTab에서 발주처·발주상태·메모를 변경한 상태이고,
**When** "발주 확정" 버튼을 클릭하지 않고 페이지를 새로고침하면,
**Then** 변경 내용이 DB에 저장되지 않고 초기 값으로 되돌아와야 한다.
