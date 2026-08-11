# Research: SPEC-ORDER-015 출고 처리 (한국 창고 → 미국 창고 이동)

## 1. 배경 및 용어 정의

- 이번 기능의 "출고"는 **한국 창고 → 미국 창고 이동**을 의미하며, Shopify의 "고객에게 배송 완료(fulfillment)"와는 다른 개념이다.
- `order/models.py`의 `LineItem.fulfillment_status`(168행)는 Shopify 동기화 전용 필드로, `shopify_orders.py`(137행, 220행)에서 Shopify API 응답을 그대로 저장한다. 이번 기능과 무관.

## 2. 기존 물류 파이프라인 — 재사용 대상

`order/models.py` 모듈 레벨 `LOGISTICS_STATUS_CHOICES`(8-14행):

```
not_shipped        → 미입고
shipment_confirmed → 입고예정
received           → 입고
outbound_scheduled → 출고예정
shipped            → 출고
```

- `LineItem.logistics_status`(193-197행)가 이 파이프라인 상태를 저장하는 필드. SPEC-ORDER-011에서 도입.
- 이미 구현된 업로드 기능:
  - `UploadVendorShipmentView`(`order/purchase_order_views.py:1711`) — 벤더 출고 확인 → `shipment_confirmed`
  - `UploadWarehouseReceiptView`(`order/purchase_order_views.py:1776`) — 한국 창고 입고 확인 → `received`
  - 파서: `parse_vendor_shipment_excel`, `parse_warehouse_receipt_excel` (`order/excel_utils.py:1088`, `1096`)
- **공백(Gap)**: `outbound_scheduled → shipped` 전이(한국→미국 창고 출고)를 처리하는 업로드/입력 기능이 아직 없음. 이번 SPEC-ORDER-015가 이 공백을 채운다.
- 사용자 확인: 이번 기능은 **어떤 logistics_status에서도** 출고 처리를 허용한다 (outbound_scheduled 상태만 강제하지 않음 — 현장 운영 유연성 우선).

## 3. 데이터 모델 — LineItem 관련 필드

`order/models.py` `LineItem`(141-203행):

- `order`(FK), `sku`(164행, CharField), `quantity`(165행, IntegerField)
- `fulfillment_status`(168행) — Shopify 전용, 무관
- `location`(171행), `rack_number`(178행, SPEC-ORDER-013)
- `purchase_status`(179-183행), `logistics_status`(193-197행, 재사용 대상)
- `unique_together = [("order", "shopify_line_item_id", "sku")]`(203행)

**신규 필드 (사용자 확정)**:
- `shipped_quantity` — IntegerField, default=0. 누적 출고 수량.
- `shipped_at` — DateTimeField, null=True, blank=True. 최근 출고 처리 일시.

**상태 전이 규칙 (사용자 확정)**:
- 입력 수량을 `shipped_quantity`에 누적.
- `shipped_quantity + 입력수량 > quantity` → 스킵 + "수량초과" 오류로 별도 표시 (반영하지 않음).
- 반영 후 `shipped_quantity >= quantity` → `logistics_status = "shipped"`로 자동 전이.
- 이미 완전 출고된 항목(shipped_quantity >= quantity)에 추가 입력이 들어오면 잔여수량이 0이므로 자연히 "수량초과"로 스킵됨 (별도 완료-스킵 분기 불필요).

## 4. Order 모델 — 매칭 키

`order/models.py` `Order`(30-100행):

- `order_number`(36행, IntegerField) — **매칭에 사용하지 않음**. SPEC-ORDER-013 히스토리(v1.3.0)에서 수동입력 "EB" 접두사 주문 등 실사용 검증 중 부정확함이 확인되어 폐기된 매칭 기준.
- `name`(37행, CharField(50)) — Shopify 주문 표시명(`"#37349"` 형식, `#` 포함 원본 보존). **매칭 기준 필드**.

**매칭 로직 (SPEC-ORDER-013 패턴 재사용)**:
- 입력 `Name`(예: `#37349`) → `Order.objects.filter(name=order_name).first()`
- 매칭된 Order → `LineItem.objects.filter(order=order, sku=sku)`
- Order 또는 LineItem 매칭 실패 → 스킵 + "매칭 실패"로 별도 표시

## 5. 참고 구현 — SPEC-ORDER-013 (렉번호 관리) 재사용 패턴

파일: `order/purchase_order_views.py`, `order/excel_utils.py`, `order/serializers.py`, `order/urls.py`

- `LineItemBulkRackNumberUpdateView`(2112-2148행) — 수동 일괄 입력 PATCH 패턴 (LineItem id 리스트 기반이 아니라, 이번 SPEC은 (order_name, sku, total) 리스트 기반이므로 매칭 로직은 `UploadRackNumberView`가 더 가까운 선례).
- `UploadRackNumberView`(2151-2254행) — Excel 업로드 전체 패턴:
  - 엑셀 행 → `(order_name, sku)` 튜플로 last-row-wins dedup (2193-2200행)
  - `Order.objects.filter(name=order_name).first()` (2231행)
  - `LineItem.objects.filter(order=order, sku=sku)` 매칭되는 모든 LineItem 일괄 업데이트 (2237-2243행)
  - `matched_count`/`skipped_count` 응답 분리
- `parse_rack_number_excel`(`order/excel_utils.py:994-1083`) — 헤더 자동탐색 패턴:
  - `openpyxl.load_workbook(..., data_only=True)`
  - 헤더 행(`rows[0]`)을 소문자화 후 별칭 리스트에 대해 대소문자 무시 substring 매칭
  - 못 찾으면 `ValueError` → 뷰에서 HTTP 422 변환
- `LineItemDetailSerializer.Meta.fields`(`order/serializers.py:108-118`) — 신규 필드(`shipped_quantity`, `shipped_at`) 노출 시 이 시리얼라이저에 추가하는 패턴 참고.
- URL 등록(`order/urls.py:71-96`) — bulk/특수 경로를 `<int:pk>` 패턴보다 먼저 등록하는 관례 준수 필요.

## 6. 참고 구현 — SPEC-ORDER-014 (렉번호 요약) — 결과 시각화 패턴

- 읽기 전용 GET 집계 뷰 패턴(`LineItemRackNumberSummaryView`, `purchase_order_views.py:2272`)은 이번 SPEC에는 직접 해당 없으나, 결과 응답에 `order.name`(order_number 아님)을 노출하는 관례(2313행)는 동일 적용.

## 7. 엑셀 업로드 공통 인프라

- 라이브러리: `openpyxl`(주력), `xlrd`(구 xls, 벤더용) — `order/excel_utils.py:8-13`.
- 헤더 자동탐색 공통 패턴: `rows[0]`을 `str(h).strip().lower()` 정규화 → 별칭 리스트 substring 매칭(대소문자 무시) → 실패 시 `ValueError` → 422.
- 사용자 입력 컬럼: `Name`(주문번호), `Lineitem sku`(SKU), `Total`(수량) — 헤더 별칭 예: `["name", "주문번호"]`, `["sku", "lineitem sku"]`, `["total", "수량"]`.

## 8. UI 참고 — SPEC-ORDER-013 렉번호 관리 페이지

- 신규 독립 페이지, 사이드바 메뉴 항목 추가(MapPin 아이콘 등 도메인에 맞는 아이콘).
- 수동 텍스트/표 입력 폼 + Excel 파일 업로드 UI + 처리 결과 시각화(성공/스킵/실패 구분, 색상 구분 섹션).
- "다시 처리하기" 버튼으로 폼 초기화 후 연속 작업 지원 (SPEC-FAST-LISTING-ADD-001, SPEC-INVEN-ADD-001과 동일 UX 관례).

## 9. book 앱 재고 모델 — 이번 SPEC과 무관 확인

- `book.Info.qty`(45행) — 단일 재고 수량, 창고 구분 없음. 이번 SPEC은 `order.LineItem` 레벨 상태/수량만 다루므로 `book` 앱 모델은 변경하지 않음.
- `order.WarehouseStock`(425-445행, location: korea/ca/nj) — 발주 확정 시 차감되는 별도 재고 흐름(구매 확정 로직). 이번 "출고 처리"와는 다른 기존 기능이며 변경하지 않음. (향후 확장 여지로만 문서화)

## 10. SPEC 넘버링

- `.moai/specs/` 전체 스캔 결과 SPEC-ORDER-001~014 사용 중, 015 미사용 확인.
- 도메인: `order` 앱의 `LineItem` 모델 확장 + 신규 페이지이므로 **SPEC-ORDER-015**로 결정.

## 11. 사용자 확정 요구사항 요약 (인터뷰 2라운드)

1. LineItem에 출고 상태/일시 기록 (재고 수량 증감은 다루지 않음, book 앱 미변경)
2. 매칭 실패 항목은 스킵하고 결과에 별도 표시
3. 중복 처리 시: 수량 비교로 판단 — 부분 출고는 수량 누적 합산, 수량초과는 스킵+오류 표시
4. 신규 독립 페이지 (기존 "렉번호 관리" 페이지와 동일한 UX 패턴)
5. 기존 `logistics_status` 파이프라인 재사용, 마지막 단계(`→shipped`) 처리
6. 신규 필드: `shipped_quantity`(누적), `shipped_at`(최근 처리 일시)
7. 수량초과 시 스킵 + "수량초과" 오류로 별도 표시 (반영하지 않음)
8. 처리 대상 제한 없음 — 모든 logistics_status에서 출고 처리 가능
