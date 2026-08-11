---
id: SPEC-ORDER-015
document: spec-compact
version: 1.0.2
status: draft
updated: 2026-08-10
---

# SPEC-ORDER-015 압축 요약 — 출고 처리

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(구현 계획), `acceptance.md`(Given/When/Then),
`research.md`(코드베이스 조사 근거).

## REQ 목록 (요약)

- REQ-OUTBOUND-001/002/002a — `LineItem.shipped_quantity`(default 0), `shipped_at`(nullable) 필드 추가
- REQ-OUTBOUND-003/003a — `Order.name` 정확 일치 매칭(`order_number` 사용 금지, 별도 Unwanted 항목으로 분리)
- REQ-OUTBOUND-004/005/005a — `(order, sku)` 매칭, 0건/2건 이상 → 매칭 실패로 스킵(설계 결정 A)
- REQ-OUTBOUND-006 — 현재 `logistics_status` 무관하게 처리 대상 허용
- REQ-OUTBOUND-007 — 동일 요청 내 중복 행(같은 order+sku)은 합산 후 1회 판정(설계 결정 C)
- REQ-OUTBOUND-008/009 — 잔여 용량 초과 시 미반영+"수량초과" 보고, null quantity는 0 취급(설계 결정 B)
- REQ-OUTBOUND-010/010a — 반영 후 `shipped_quantity >= quantity`면 `logistics_status="shipped"` 전이
- REQ-OUTBOUND-011/013 — 수동 입력/Excel 업로드 둘 다 동일 로직 원자적 적용
- REQ-OUTBOUND-012/012a — Excel 헤더 자동탐색, 실패 시 HTTP 422
- REQ-OUTBOUND-014 — 응답은 matched/unmatched/quantity_exceeded 3분류 count+리스트
- REQ-OUTBOUND-015~018 — 신규 독립 프론트엔드 페이지(수동입력+Excel업로드+결과시각화+리셋), 사이드바 항목
- REQ-OUTBOUND-019 — `rack_number`/`fulfillment_status`/`book.Info.qty`/`WarehouseStock` 무변경

## 인수 기준 목록 (요약)

spec.md ACCEPTANCE CRITERIA 섹션 기준 총 23개 항목(AC-OUTBOUND-001~020 + 004a/009a/010a),
REQ-OUTBOUND 24개 항목(001~019 + 002a/003a/005a/010a/012a) 전량 1:1+ traceability 확보
(2026-08-10, plan-auditor D2 대응. AC-OUTBOUND-009/009a 분리는 D7 대응, 2026-08-10).

- AC-OUTBOUND-001 — 정상 매칭·부분 반영
- AC-OUTBOUND-002 — 2회 요청 누적 → 완전 출고 전이
- AC-OUTBOUND-003 — 수량초과 거부
- AC-OUTBOUND-004/004a — 매칭 실패(주문 없음/SKU 없음)
- AC-OUTBOUND-005/005a — 동일 요청 내 중복 행 합산(정상/초과)
- AC-OUTBOUND-006 — 복수 매칭 시 매칭 실패
- AC-OUTBOUND-007 — Excel 헤더 인식 실패 → 422
- AC-OUTBOUND-008 — 타 도메인/기존 페이지 무영향 회귀
- AC-OUTBOUND-009 — 데이터 모델 필드(shipped_quantity 기본값 0 / shipped_at nullable) 존재
- AC-OUTBOUND-009a — 미처리 LineItem의 `shipped_at` null 유지
- AC-OUTBOUND-010/010a — `Order.name` 매칭 사용 / `order_number` 미사용
- AC-OUTBOUND-011 — Order+SKU 필터 기반 LineItem 매칭 시도
- AC-OUTBOUND-012 — 현재 `logistics_status` 무관 처리 대상 허용
- AC-OUTBOUND-013 — 미달 시 `logistics_status` 무변경
- AC-OUTBOUND-014 — 두 엔드포인트(수동입력/Excel) 원자적 처리
- AC-OUTBOUND-015 — Excel 헤더 별칭 파싱 성공 경로
- AC-OUTBOUND-016 — 3분류 응답 계약(count+리스트)
- AC-OUTBOUND-017 — 독립 페이지 + 사이드바 진입점
- AC-OUTBOUND-018 — 수동입력 폼 + Excel 업로드 컨트롤 동시 노출
- AC-OUTBOUND-019 — 결과 3섹션 시각화
- AC-OUTBOUND-020 — 리셋 컨트롤 동작

## 변경 대상 파일

**백엔드**: `backend/order/models.py`(MODIFY) · `backend/order/migrations/0035_lineitem_add_shipped_fields.py`(NEW) ·
`backend/order/excel_utils.py`(MODIFY, `parse_outbound_excel`) ·
`backend/order/purchase_order_views.py`(MODIFY, `_process_outbound_rows` + `OutboundProcessView` + `UploadOutboundView`) ·
`backend/order/urls.py`(MODIFY) · `backend/order/serializers.py`(MODIFY, 선택)

**프론트엔드**: `frontend/src/pages/OutboundPage/index.tsx`(NEW) ·
`frontend/src/services/outboundApi.ts`(NEW) · `frontend/src/hooks/useOutboundQueries.ts`(NEW) ·
`frontend/src/router/index.tsx`(MODIFY) · `frontend/src/components/Sidebar.tsx`(MODIFY)

## Exclusions

- `book.Info.qty` 변경 없음
- `order.WarehouseStock` 변경 없음
- `LineItem.fulfillment_status` 변경 없음
- `LOGISTICS_STATUS_CHOICES` 신규 enum 값 추가 없음
- `Order.order_number` 매칭 사용 안 함
- 복수 LineItem 매칭 시 수량 분배 로직 미구현(매칭 실패로 스킵)
- 출고 취소/되돌리기(undo) 기능 없음
- 결과 Excel/CSV 내보내기(export) 없음
- 기존 `/rack-number` 페이지(SPEC-ORDER-013/014) 변경 없음
