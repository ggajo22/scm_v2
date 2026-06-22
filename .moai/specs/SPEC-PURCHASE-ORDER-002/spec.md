---
id: SPEC-PURCHASE-ORDER-002
version: 1.0.0
status: completed
created: 2026-06-22
updated: 2026-06-22
author: ggajo
priority: Low
issue_number: ~
---

# 발주 미발주 현황 탭 — 선택 항목 총 수량 표시

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-22 | ggajo | 최초 작성 |

---

## 문제 정의

미발주 현황 탭에서 SKU를 체크박스로 선택하면 현재 "N건 선택됨"만 표시된다.  
관리자 입장에서는 선택된 SKU의 **총 발주 수량**이 얼마인지를 즉시 파악해야 발주 규모를 확인할 수 있으나, 현재 화면은 행 개수만 보여주어 수량 합계를 별도로 계산해야 한다.

---

## 솔루션 개요

선택된 SKU들의 `quantity` 필드 합계를 계산하여 "수량 XX개 선택됨"을 기존 "N건 선택됨" 옆에 함께 표시한다.

---

## 범위

- **포함**: `UnorderedItemsTab` 컴포넌트 — 선택 상태 표시 영역
- **제외**: 다른 탭 (VendorFileUploadTab, ConfirmOrderTab, PurchaseOrderHistoryTab 등)

---

## 요구사항 (EARS 형식)

### REQ-PO2-001 — 총 수량 합계 계산

**When** 사용자가 미발주 현황 탭에서 하나 이상의 SKU를 체크하면  
**The system shall** 선택된 SKU의 `quantity` 값을 모두 합산하여 총 수량을 계산한다.

### REQ-PO2-002 — 선택 상태 텍스트 표시

**When** 선택된 SKU가 1개 이상이면  
**The system shall** "N건 선택됨 / 수량 M개 선택됨" 형식으로 표시한다.  
(N = 선택된 행 수, M = 선택된 SKU들의 수량 합계)

### REQ-PO2-003 — 선택 없을 때 기본 메시지

**When** 선택된 SKU가 없으면  
**The system shall** 기존과 동일하게 "항목을 선택하세요"를 표시한다.

---

## 인수 조건

| # | 조건 | 기대 결과 |
|---|------|-----------|
| AC-01 | SKU 2개 선택 (quantity: 50, 30) | "2건 선택됨 / 수량 80개 선택됨" |
| AC-02 | SKU 1개 선택 (quantity: 100) | "1건 선택됨 / 수량 100개 선택됨" |
| AC-03 | 전체 선택 | "N건 선택됨 / 수량 M개 선택됨" (전체 합산) |
| AC-04 | 선택 해제 후 0건 | "항목을 선택하세요" |

---

## 기술 설계

### 변경 파일

- `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`

### 구현 방법

현재 `checkedRowCount` 계산 아래에 `selectedQuantityTotal`을 추가한다.

```tsx
const checkedRowCount = data?.results.filter((item) => selectedSkus.includes(item.sku)).length ?? 0
const selectedQuantityTotal = data?.results
  .filter((item) => selectedSkus.includes(item.sku))
  .reduce((sum, item) => sum + item.quantity, 0) ?? 0
```

표시 텍스트 변경:

```tsx
// Before
{checkedRowCount > 0 ? `${checkedRowCount}건 선택됨` : '항목을 선택하세요'}

// After
{checkedRowCount > 0
  ? `${checkedRowCount}건 선택됨 / 수량 ${selectedQuantityTotal}개 선택됨`
  : '항목을 선택하세요'}
```

---

## 영향 분석

- 백엔드 변경 없음 (이미 `quantity` 필드가 API 응답에 포함됨)
- 상태 관리 변경 없음 (`usePurchaseOrderStore` 수정 불필요)
- 변경 파일 1개, 추가 코드 ~3줄
