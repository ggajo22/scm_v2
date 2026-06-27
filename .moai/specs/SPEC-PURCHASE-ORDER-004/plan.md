# 구현 계획 — SPEC-PURCHASE-ORDER-004

## 개요

`LineItem` 모델에 `purchase_status` 필드를 추가하고, 미발주 현황 탭에서 인라인/다건 상태 변경을 지원한다.

총 3개 레이어(백엔드 모델/마이그레이션, 백엔드 API, 프론트엔드 UI)로 구성되며, 레이어 간 의존성에 따라 순차 진행한다.

---

## 마일스톤

### M1 — 백엔드: 모델 및 마이그레이션 (Priority: High)

**목표**: `LineItem.purchase_status` 필드를 DB에 반영한다.

**작업 목록**:
1. `backend/order/models.py` — `PURCHASE_STATUS_CHOICES` 상수 정의 및 `LineItem`에 `purchase_status` 필드 추가
2. Django 마이그레이션 생성 (`python manage.py makemigrations order`)
3. 마이그레이션 파일 검토: MySQL 8.0 호환 DDL인지 확인 (`VARCHAR(20) NOT NULL DEFAULT 'unordered'`)
4. 로컬 DB에 마이그레이션 적용 및 기존 레코드 `purchase_status` 값 확인

**완료 기준**:
- `orders_line_item` 테이블에 `purchase_status` 컬럼이 존재한다.
- 기존 `LineItem` 레코드의 `purchase_status`가 모두 `'unordered'`이다.

---

### M2 — 백엔드: API 엔드포인트 (Priority: High)

**목표**: 단건/다건 상태 변경 엔드포인트를 구현하고, 미발주 목록 필터를 보강한다.

**작업 목록**:
1. `UnorderedItemsView.get()` — `purchase_status="unordered"` 필터 조건 추가 및 응답에 `purchase_status` 필드 포함
2. `LineItemStatusView` 신규 구현 — `PATCH /api/purchase-orders/line-items/{id}/status/`
3. `LineItemBulkStatusView` 신규 구현 — `PATCH /api/purchase-orders/line-items/bulk-status/`
4. `backend/order/urls.py` — 두 엔드포인트 URL 패턴 등록
5. 입력 유효성 검증: `purchase_status` 코드가 `PURCHASE_STATUS_CHOICES`에 존재하는지 확인
6. 인증 미들웨어 적용 (`JWTAuthentication`, `IsAuthenticated`)

**완료 기준**:
- `GET /api/purchase-orders/unordered/` 응답에 `purchase_status` 필드가 포함된다.
- `purchase_status='unordered'`가 아닌 `LineItem`은 미발주 목록에 나타나지 않는다.
- `PATCH .../line-items/{id}/status/` 호출 후 DB 값이 변경된다.
- `PATCH .../line-items/bulk-status/` 호출 후 지정한 모든 유효 `LineItem`의 상태가 변경된다.
- 미인증 요청 → HTTP 401, 잘못된 status 코드 → HTTP 400, 존재하지 않는 id → HTTP 404.

---

### M3 — 프론트엔드: UI 변경 (Priority: High)

**목표**: 미발주 현황 탭에서 `purchase_status` 표시 및 인라인/다건 변경 UI를 추가한다.

**작업 목록**:
1. `frontend/src/api/purchaseOrders.ts` (또는 동등 API 파일) — 단건/다건 상태 변경 API 함수 추가
2. `UnorderedItemsTab.tsx` — `purchase_status` 한국어 레이블 컬럼 추가
3. `UnorderedItemsTab.tsx` — 각 행의 `purchase_status` 드롭다운(Select) 컴포넌트 추가
   - 드롭다운 변경 시 단건 PATCH 호출
   - `unordered`가 아닌 값으로 변경 시 해당 행을 목록에서 즉시 제거
4. `UnorderedItemsTab.tsx` — 체크박스 선택 후 일괄 상태 변경 버튼/드롭다운 추가
   - 다건 PATCH 호출 후 `unordered`가 아닌 항목 제거

**완료 기준**:
- 미발주 탭 각 행에 `purchase_status` 컬럼과 드롭다운이 표시된다.
- 드롭다운 변경 후 API 호출이 성공하면 행이 즉시 갱신된다.
- 여러 행 선택 후 일괄 변경이 동작한다.

---

## 기술적 위험 및 대응

| 위험 | 설명 | 대응 방안 |
|------|------|----------|
| 마이그레이션 충돌 | 진행 중인 다른 브랜치와 마이그레이션 충돌 | M1 완료 후 즉시 master 기준으로 rebase |
| 필터 변경으로 인한 기존 데이터 영향 | 기존 `LineItem` 중 `purchase_status`가 `unordered`가 아닌 경우 미발주 탭에서 사라짐 | 마이그레이션 기본값을 `unordered`로 설정하여 기존 데이터 영향 없음을 보장 |
| bulk update 원자성 | 일부 id만 업데이트되는 경우 부분 실패 | `update()` ORM 사용 — 트랜잭션 내 일괄 처리, 누락 id는 응답에 포함 |
| 프론트엔드 낙관적 업데이트 | API 실패 시 UI 상태 불일치 | API 성공 확인 후 UI 업데이트, 실패 시 원래 상태로 롤백 |

---

## 의존성 순서

```
M1 (모델/마이그레이션) → M2 (API) → M3 (프론트엔드)
```

M2는 M1이 완료(필드 존재)되어야 구현 가능하고, M3는 M2 API가 완료되어야 실제 연동 가능하다.

---

## 변경 파일 요약

| 파일 | 마일스톤 | 변경 유형 |
|------|----------|----------|
| `backend/order/models.py` | M1 | 수정 |
| `backend/order/migrations/XXXX_add_purchase_status_to_lineitem.py` | M1 | 신규 생성 |
| `backend/order/purchase_order_views.py` | M2 | 수정 |
| `backend/order/urls.py` | M2 | 수정 |
| `frontend/src/api/purchaseOrders.ts` | M3 | 수정 |
| `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx` | M3 | 수정 |
