---
id: SPEC-PURCHASE-ORDER-011
document: spec-compact
version: 1.3.1
status: draft
updated: 2026-08-14
---

# SPEC-PURCHASE-ORDER-011 압축 요약 — 파손 교환 신청 페이지

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(구현 계획), `acceptance.md`(Given/When/Then).

## REQ 목록 (요약)

- REQ-DEX-001 — `LineItem.damaged_quantity` 필드(기본값 0) 신규 추가
- REQ-DEX-002/003 — `/outbound`·`/rack-number`와 독립된 신규 페이지 + 사이드바 메뉴 항목
- REQ-DEX-004 — ISBN(=`LineItem.sku`) 정확 일치 검색만 허용(부분/icontains 금지)
- REQ-DEX-005/005a — 미출고 정의(`logistics_status != "shipped"` AND `purchase_status != "order_cancelled"`) 재사용, 이미 `damaged_exchange`인 행도 배지로 포함
- REQ-DEX-006/006a/006b — 표시 컬럼(주문번호/주문 수량/오늘 출고 가능 여부 as-is/전체 출고 수량=부모 Order의 추적 가능·비취소 LineItem만 합산, 결정 B; `shipped_quantity`와 무관함을 명시), `ready_to_ship` 재계산 금지, 취소·미추적 행은 합산에서 제외(006b는 시스템 주어로 정정, v1.3.0 D19)
- REQ-DEX-007 — 매칭 없으면 빈 결과(오류 아님)
- REQ-DEX-008 — 행별 파손 수량 입력(기본값 1, 범위 1..quantity)
- REQ-DEX-009/009a/009b — 제출 시 `purchase_status→damaged_exchange`, `damaged_quantity` 저장, Order 집계 재계산; 범위 밖/quantity=null이면 거부; 재접수는 덮어쓰기(누적 아님)
- REQ-DEX-009c/009d — **[MODIFY], 결정 E**: 공유 함수 `_recompute_order_aggregates`에 `damaged_exchange` 단락 추가 — `cs_required`와 동일하게 `ready_to_ship=False` 강제(기존 `all(received/in_stock)` 판정보다 우선); `status`를 **도출하는 규칙**은 무변경이나 `status`/`ready_to_ship` 컬럼은 항상 같은 UPDATE로 함께 쓰인다(v1.3.0 D16 정정). fan-in 8→9로 확장, 이번 페이지와 무관한 기존 8개 호출자·`OrderDetailPage.tsx` 배지·`OrderResyncView`(v1.3.0 D15 추가)에도 영향. REQUIREMENTS에서 file:line 인용을 제거하고 행위적으로 재서술(v1.3.0 D18, 정확한 위치는 plan.md)
- REQ-DEX-010 — `LineItemNote`(note_type="파손/교환", assignee="발주", **author=접수자**) 자동 생성, 수량 정보 포함
- REQ-DEX-011 — `logistics_status`/`shipped_quantity` 무변경
- REQ-DEX-012/012a — `UnorderedItemsView` 재발주 수량이 `damaged_exchange` 행에 한해 `damaged_quantity` 기준(환불 차감·0-스킵 규칙 유지)으로 보정, 비대상 행은 무변경
- REQ-DEX-012b/012c — 다른 5개 조회 지점(업체 자료 비교/Daily Review 다운로드/Daily Review 업로드 확정/발주 파일 생성/업체 비교 목록)은 무변경, 5곳이 균일 패턴을 공유하지 않음을 명시; `VendorComparisonView`의 커버리지는 PO-미연결 행에 한정(v1.3.0 D21); `ConfirmOrderView`는 quantity를 요청 바디에서 받으므로 구조적으로 별도 취급. REQUIREMENTS의 file:line 인용은 plan.md로 이관(v1.3.0 D18)
- **REQ-DEX-013/013a — [NEW], 결정 F, v1.3.0 신규(D13)**: 1회성 백필 마이그레이션 — 배포 전부터 `damaged_exchange`였던 기존 Order의 stale `ready_to_ship=True`를 새 규칙으로 재계산(`0033_backfill_order_ready_to_ship.py` 선례 재사용); `damaged_exchange`가 없는 다른 Order는 불변

## 인수 기준 목록 (요약)

spec.md ACCEPTANCE CRITERIA 섹션 기준 총 27개 항목(AC-DEX-001~013 + 004a/005a/005b/005c/009a/009b/009c/012a~012f), REQ-DEX 24개 항목(001~013 기본 계열 13개, 결번 없음 + 접미사 11개: 005a/006a/006b/009a/009b/009c/009d/012a/012b/012c/013a) 전량 1:1+ traceability 확보. (v1.3.0: plan-auditor iteration 2 FAIL 대응 — D13/D14/D15/D16/D17/D18/D19/D20/D21/D22 수정, REQ-DEX-013/013a + AC-DEX-013/013a 신설, AC-DEX-005c/009c/012e 픽스처 판별력 확보)

- AC-DEX-001 — `damaged_quantity` 필드 존재/기본값, 마이그레이션 무손실
- AC-DEX-002 — 독립 페이지 + 사이드바 진입점(SPEC-ORDER-015 수준의 검증 가능한 import 배제 조건)
- AC-DEX-003 — 부분 일치 미매칭(정확 일치만 허용) 확인
- AC-DEX-004/004a — 미출고 필터 정확성 + damaged_exchange 행 포함·배지
- AC-DEX-005/005a — "전체 출고 수량" 추적 가능·비취소 행만 합산 확인(취소 행 100·sku-null 행 50을 포함한 4행 픽스처) + ready_to_ship null 보존
- AC-DEX-005b — 취소·미추적 행이 "전체 출고 수량" 합산에서 실제로 제외됨을 별도 확인
- AC-DEX-005c — null quantity → 0 취급 확인 — **v1.3.0 D20 재작성**: 전원 null 픽스처로 교체(기존 mixed-null 픽스처는 SQL `SUM`이 NULL을 무시해 무판별력이었음)
- AC-DEX-006 — ready_to_ship 읽기 전용(재계산 금지) 확인, 올바른 참조 대상(`_recompute_order_aggregates`)으로 정정
- AC-DEX-007 — 매칭 없음 → 빈 결과(오류 아님)
- AC-DEX-008 — 기본값 1 + 서버측 필수 검증
- AC-DEX-009 — 정상 접수 시 damaged_quantity≠quantity 및 ready_to_ship 재계산(원인은 damaged_exchange 단락, logistics_status 불변) — 미호출/미수정 양쪽 다 잡아내는 판별력 확보
- AC-DEX-009a — 범위 밖 거부
- AC-DEX-009b — 재접수 덮어쓰기 확인
- AC-DEX-009c — 집계 단락 자체의 단위 수준 검증 — **v1.3.0 D14 재작성**: damaged_exchange 행의 `logistics_status`를 `"received"`로 고정(기존 `"not_shipped"` 픽스처는 신규 단락 없이도 이미 False가 나와 무판별력이었음); status는 "규칙 불변"으로 정정(D16)
- AC-DEX-010 — 메모 자동 생성(수량·**author** 정보 포함) 정확히 1건
- AC-DEX-011 — logistics_status/shipped_quantity 무변경
- AC-DEX-012/012a — 재발주 수량이 damaged_quantity 기준(환불 차감 적용) 확인
- AC-DEX-012b — 0-스킵 규칙이 damaged_quantity 기준으로 적용됨 확인, `quantity=10` 명시로 판별력 확보
- AC-DEX-012c — unordered 행 회귀 없음
- AC-DEX-012d — 4개 조회 지점(RunComparisonView/DailyReviewExcelView/UploadDailyReviewView/GenerateOrderFileView) quantity 기준 유지 확인
- AC-DEX-012e — VendorComparisonView quantity 기준 유지 확인 — **v1.3.0 D21 재작성**: PO-미연결(`purchase_orders__isnull=True`) 픽스처로 고정(연결 여부 미고정 시 정상 구현도 실패할 수 있었음); PO-연결 케이스는 Exclusions로 이관. **v1.3.1 D23 재작성**: 이 뷰는 수량을 응답에 내보내지 않으므로 블랙박스 단언이 불가능 — 내부 맵 `qty_by_sku`(`purchase_order_views.py:744-750`)에 대한 화이트박스 단언으로 변경
- AC-DEX-012f — ConfirmOrderView는 요청 바디 quantity를 그대로 사용, LineItem 필드를 읽지 않음 확인
- **AC-DEX-013/013a — v1.3.0 신규(D13)**: 백필 마이그레이션이 기존 damaged_exchange Order의 stale True→False로 갱신 / 무관한 다른 Order는 불변. **v1.3.1 D24 판별력 보강**: 013의 damaged_exchange 행을 `logistics_status="received"`로 고정(미고정 시 0033을 그대로 베낀 마이그레이션도 통과), 013a의 두 번째 Order에 `sku` not null 고정(미고정 시 백필 스코프 밖이라 기준이 공허)

## 변경 대상 파일

**백엔드**: `backend/order/models.py`(MODIFY, `damaged_quantity` 필드) · `backend/order/migrations/00XX_lineitem_damaged_quantity.py`(NEW) · `backend/order/purchase_order_views.py`(MODIFY — 검색 뷰 NEW, 접수 뷰 NEW, `UnorderedItemsView.get()` MODIFY, `_recompute_order_aggregates` MODIFY [DELTA] — fan-in 8→9, `ready_to_ship`만 신규 규칙·`status` 규칙은 무변경(컬럼은 계속 함께 쓰임)) · `backend/order/migrations/00XX_backfill_ready_to_ship_damaged_exchange.py`(**NEW, v1.3.0 신규 — REQ-DEX-013, `0033` 선례 재사용**) · `backend/order/urls.py`(MODIFY)

**프론트엔드**: `frontend/src/pages/DamagedExchangePage/index.tsx`(NEW) · `frontend/src/services/damagedExchangeApi.ts`(NEW) · `frontend/src/hooks/useDamagedExchangeQueries.ts`(NEW) · `frontend/src/router/index.tsx`(MODIFY) · `frontend/src/components/Sidebar.tsx`(MODIFY)

**특성화 테스트(선행 조건, v1.3.0에서 D22 정정)**: 신규 작성이 아니라 `backend/order/tests/test_spec_012.py`의 `TestRecomputeOrderAggregatesReadyToShip`(9개 테스트, 기존 3분기 전부 커버)가 `damaged_exchange` 단락 추가 전후로 그대로 통과하는지 확인.

## Exclusions

- `book.Info.qty`, `order.WarehouseStock` 변경 없음
- `LineItem.fulfillment_status` 변경 없음
- Shopify 동기화 경로 변경 없음
- 기존 `/outbound`(SPEC-ORDER-015), `/rack-number`(SPEC-ORDER-013/014) 페이지 동작 변경 없음
- 신규 `logistics_status`/`purchase_status` enum 값 추가 없음
- 파손 접수 대량/Excel 업로드 경로 없음(행 단위 단건만)
- `Order.status`를 **도출하는 규칙** 변경 없음(REQ-DEX-009d) — `Order.ready_to_ship`은 더 이상 Exclusion이 아니다(REQ-DEX-009c가 그 계산 규칙을 의도적으로 수정하고, REQ-DEX-013이 기존 데이터를 백필한다). 이 SPEC이 건드리지 않는 것은 `status`(물류 상태 집계, `logistics_status` 기반)를 계산하는 **규칙** 쪽이다 — 컬럼 자체는 `ready_to_ship`과 함께 매번 다시 쓰인다(D16).
- `RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView`의 수량 계산 변경 없음 — **알려진 의도적 공백**: 이 5곳도 동일한 결함을 잠재적으로 가지나 이번 SPEC 범위 밖(사용자 확정, 2026-08-14), 후속 SPEC 후보. `ConfirmOrderView`는 quantity를 요청 바디에서 받아 이 공백에 해당하지 않는 구조적으로 별도인 사례(REQ-DEX-012c).
- **(v1.3.0 신규, D21) `VendorComparisonView`의 PO-연결된 `damaged_exchange` 행** — 이 뷰는 PO-미연결 LineItem만 집계하며 `damaged_exchange` 링크 예외가 없다. 실무에서 흔할 PO-연결된 파손 품목은 이 뷰에서 `0`으로 보고되는 채로 남는다 — AC-DEX-012e는 PO-미연결 경우만 검증한다.
- `LineItemDetailSerializer` 등 기존 상세 화면에 `damaged_quantity` 노출 없음
