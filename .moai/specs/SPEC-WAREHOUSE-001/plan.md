# SPEC-WAREHOUSE-001 구현 계획

> 본 문서는 회고적(retrospective) SPEC으로, 이미 구현이 완료된 상태를 기록한다.

---

## 구현 완료 항목

### Priority High — 백엔드

| 항목 | 파일 | 상태 |
|------|------|------|
| WarehouseStock 모델 | `order/models.py` | 완료 |
| 피벗 목록 조회 뷰 | `order/warehouse_views.py` | 완료 |
| 단건 Upsert 뷰 | `order/warehouse_views.py` | 완료 |
| 일괄 Bulk Upsert 뷰 | `order/warehouse_views.py` | 완료 |
| 단건 삭제 뷰 | `order/warehouse_views.py` | 완료 |
| URL 라우팅 등록 | `order/urls.py` | 완료 |
| 단위 테스트 (11개) | `order/tests/test_warehouse.py` | 완료, 전체 통과 |

### Priority High — 프론트엔드

| 항목 | 파일 | 상태 |
|------|------|------|
| API 클라이언트 및 TypeScript 타입 | `src/services/warehouseApi.ts` | 완료 |
| TanStack Query v5 훅 | `src/hooks/useWarehouseQueries.ts` | 완료 |
| 창고 재고 페이지 | `src/pages/WarehouseStockPage.tsx` | 완료 |
| 사이드바 네비게이션 추가 | (사이드바 컴포넌트) | 완료 |
| 라우터 `/warehouse` 등록 | (라우터 설정) | 완료 |

---

## 기술 접근 방식

### 백엔드

- **피벗 집계**: `WarehouseStock.objects.filter(...)` 단일 쿼리 후 Python dict로 isbn 기준 피벗 변환. ORM 수준에서 N+1 없이 처리.
- **Upsert**: Django `update_or_create(defaults={"quantity": quantity}, isbn=isbn, location=location)` 패턴 사용.
- **인증**: `JWTAuthentication` + `IsAuthenticated` permission class 적용.
- **DB 테이블**: `orders_warehousestock` (기존 `orders_` prefix 일관성 유지).

### 프론트엔드

- **상태 관리**: TanStack Query v5 훅(`useWarehouseStock`, `useUpsertWarehouseStock`, `useBulkUpsertWarehouseStock`, `useDeleteWarehouseStock`)으로 서버 상태 관리.
- **피벗 테이블**: API 응답이 이미 피벗 형태이므로 클라이언트 집계 없이 직접 렌더링.
- **일괄 등록 파싱**: textarea 입력을 줄 단위로 파싱 (`ISBN 위치 수량` 포맷).
- **번들 최적화**: React.lazy + Suspense로 `/warehouse` 페이지 코드 스플리팅.

---

## 위험 요소 및 완화 방안

| 위험 | 완화 방안 |
|------|-----------|
| 피벗 응답 스키마가 위치 종류에 종속 | 위치는 `LOCATION_CHOICES`로 고정 관리. 변경 시 API 스키마도 함께 업데이트 |
| 일괄 등록 중 일부 항목 실패 | 현재 구현은 전체 처리 후 결과 반환. 부분 실패 롤백은 미구현 (제외 사항 아님, 향후 개선 여지) |
| unique_together 제약 위반 | Upsert 패턴으로 중복 삽입 방지. DB 제약이 최후 안전망으로 작동 |

---

## 향후 개선 검토 항목 (현재 SPEC 범위 외)

- 재고 변경 이력 추적 (감사 로그)
- 재고 임계값 알림
- Shopify 주문 연동 자동 재고 차감
- 위치 동적 추가 기능
