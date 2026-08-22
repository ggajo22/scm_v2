---
id: SPEC-PURCHASE-ORDER-011
document: spec-compact
version: 1.7.0
status: completed
updated: 2026-08-20
---

# SPEC-PURCHASE-ORDER-011 압축 요약 — 파손 교환 신청 페이지

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(구현 계획), `acceptance.md`(Given/When/Then).

> **현행 규칙 요약 (v1.7.0)**: 파손 접수는 `purchase_status="damaged_exchange"` + `damaged_quantity` 저장에 더해, `logistics_status`를 `not_shipped`로 되돌리고 `received_quantity`에서 파손 수량을 차감한다. `_recompute_order_aggregates`의 `damaged_exchange`/`cs_required` 단락은 v1.6.0에서 **삭제**됐다 — 아래 REQ/AC-DEX-009c 항목은 이력 보존용이며 현행이 아니다.

## REQ 목록 (요약)

- REQ-DEX-001 — `LineItem.damaged_quantity` 필드(기본값 0) 신규 추가
- REQ-DEX-002/003 — `/outbound`·`/rack-number`와 독립된 신규 페이지 + 사이드바 메뉴 항목
- REQ-DEX-004 — ISBN(=`LineItem.sku`) 정확 일치 검색만 허용(부분/icontains 금지)
- REQ-DEX-005/005a — 미출고 정의(`logistics_status != "shipped"` AND `purchase_status != "order_cancelled"`) 재사용, 이미 `damaged_exchange`인 행도 배지로 포함
- REQ-DEX-006/006a/006b — 표시 컬럼(주문번호/주문 수량/오늘 출고 가능 여부 as-is/전체 출고 수량=부모 Order의 추적 가능·비취소 LineItem만 합산, 결정 B; `shipped_quantity`와 무관함을 명시), `ready_to_ship` 재계산 금지, 취소·미추적 행은 합산에서 제외(006b는 시스템 주어로 정정, v1.3.0 D19)
- REQ-DEX-007 — 매칭 없으면 빈 결과(오류 아님)
- **REQ-DEX-017/017a/018 — 결정 H, v1.5.0 신규(PR 오픈 후 추가 요청)**: 검색 결과 행에 기존 필드 `LineItem.rack_number`(SPEC-ORDER-013 REQ-RACK-001)를 읽기 전용으로 노출(신규 쿼리 없음), 이 페이지는 그 값을 쓰지 않음(017a), 빈 값은 SPEC-ORDER-014 관례를 따라 "미지정"으로 렌더링(018)
- REQ-DEX-008 — 행별 파손 수량 입력(기본값 1, 범위 1..quantity)
- REQ-DEX-009/009a/009b — 제출 시 `purchase_status→damaged_exchange`, `damaged_quantity` 저장, Order 집계 재계산; 범위 밖/quantity=null이면 거부; 재접수는 덮어쓰기(누적 아님)
- ~~REQ-DEX-009c/009d~~ — **SUPERSEDED v1.6.0(단락 삭제, 구현 롤백)**. 원문: **[MODIFY], 결정 E**: 공유 함수 `_recompute_order_aggregates`에 `damaged_exchange` 단락 추가 — `cs_required`와 동일하게 `ready_to_ship=False` 강제(기존 `all(received/in_stock)` 판정보다 우선); `status`를 **도출하는 규칙**은 무변경이나 `status`/`ready_to_ship` 컬럼은 항상 같은 UPDATE로 함께 쓰인다(v1.3.0 D16 정정). fan-in 8→9로 확장, 이번 페이지와 무관한 기존 8개 호출자·`OrderDetailPage.tsx` 배지·`OrderResyncView`(v1.3.0 D15 추가)에도 영향. REQUIREMENTS에서 file:line 인용을 제거하고 행위적으로 재서술(v1.3.0 D18, 정확한 위치는 plan.md)
- REQ-DEX-010 — `LineItemNote`(note_type="파손/교환", assignee="발주", **author=접수자**) 자동 생성, 수량 정보 포함
- REQ-DEX-011 — **v1.7.0 반전**: 접수 시 `logistics_status="not_shipped"` 전환 + `received_quantity`를 파손 수량만큼 차감(`[0, quantity]` 클램프). 구 문구 "무변경"은 폐기
- REQ-DEX-011a — 재접수는 직전 차감분을 복원한 뒤 새 값을 차감(REQ-DEX-009b 덮어쓰기 시맨틱의 `received_quantity` 확장, 이중 차감 방지)
- REQ-DEX-011b — `shipped_quantity`/`shipped_at`/`received_at`은 무변경
- **REQ-DEX-013b — v1.7.0 신규**: 1회성 백필 마이그레이션 `0045`가 기존 `damaged_exchange` 행에 위 규칙을 소급 적용하고 그 부모 Order 집계를 현행 규칙(환불 차감 포함, 단락 없음)으로 재계산. `0040`은 삭제된 단락 규칙을 담고 있어 선례로 재사용하지 않음
- REQ-DEX-012/012a — `UnorderedItemsView` 재발주 수량이 `damaged_exchange` 행에 한해 `damaged_quantity` 기준(환불 차감·0-스킵 규칙 유지)으로 보정, 비대상 행은 무변경
- REQ-DEX-012b/012c — 다른 5개 조회 지점(업체 자료 비교/Daily Review 다운로드/Daily Review 업로드 확정/발주 파일 생성/업체 비교 목록)은 무변경, 5곳이 균일 패턴을 공유하지 않음을 명시; `VendorComparisonView`의 커버리지는 PO-미연결 행에 한정(v1.3.0 D21); `ConfirmOrderView`는 quantity를 요청 바디에서 받으므로 구조적으로 별도 취급. REQUIREMENTS의 file:line 인용은 plan.md로 이관(v1.3.0 D18)
- **REQ-DEX-013/013a — [NEW], 결정 F, v1.3.0 신규(D13)**: 1회성 백필 마이그레이션 — 배포 전부터 `damaged_exchange`였던 기존 Order의 stale `ready_to_ship=True`를 새 규칙으로 재계산(`0033_backfill_order_ready_to_ship.py` 선례 재사용); `damaged_exchange`가 없는 다른 Order는 불변
- **REQ-DEX-014/014a — [MODIFY], 결정 G, v1.4.0 신규(Run 단계에서 발견)**: 단건/일괄 상태 변경 API가 `purchase_status="damaged_exchange"`를 HTTP 400으로 거부(일괄은 전체 배치 거부, 부분 반영 없음); 다른 값은 계속 정상 동작
- **REQ-DEX-015 — [MODIFY], 결정 G, v1.4.0 신규, SPEC-PURCHASE-ORDER-010 REQ-DMG-003 대체**: Daily Review 엑셀 `선택="파손/교환"` 행은 `purchase_status` 미변경 + 노트 미생성 + `errors`에 `reason="damaged_exchange_requires_dedicated_page"` 보고 + `skipped_count` 반영
- **REQ-DEX-016/016a — 결정 G, v1.4.0 신규**: 프론트엔드 `PURCHASE_STATUS_OPTIONS`에서 `damaged_exchange` 제외(`PURCHASE_STATUS_LABELS`에는 유지), 이미 그 상태인 행은 발주 관리 화면에서 비활성 `<option>`으로 표시

## 인수 기준 목록 (요약)

spec.md ACCEPTANCE CRITERIA 섹션 기준 총 38개 항목(AC-DEX-001~018 + 004a/005a/005b/005c/009a/009b/009c/012a~012f/013a/014a/014b/015a/017a/018a), REQ-DEX 32개 항목(001~018 기본 계열 18개, 결번 없음 + 접미사 14개: 005a/006a/006b/009a/009b/009c/009d/012a/012b/012c/013a/014a/016a/017a) 전량 1:1+ traceability 확보. (v1.4.0: Run 단계에서 발견된 결함 — plan-audit 3라운드 모두 놓침 — 을 결정 G로 반영, REQ-DEX-014/014a/015/016/016a + AC-DEX-014/014a/014b/015/015a/016/016a 신설. v1.5.0: PR 오픈 후 사용자가 요청한 렉번호 읽기 전용 노출을 결정 H로 반영, REQ-DEX-017/017a/018 + AC-DEX-017/017a/018/018a 신설. 코드는 이미 구현·커밋·테스트되어 있고 이 개정은 문서를 그에 맞춘다.)

- AC-DEX-001 — `damaged_quantity` 필드 존재/기본값, 마이그레이션 무손실
- AC-DEX-002 — 독립 페이지 + 사이드바 진입점(SPEC-ORDER-015 수준의 검증 가능한 import 배제 조건)
- AC-DEX-003 — 부분 일치 미매칭(정확 일치만 허용) 확인
- AC-DEX-004/004a — 미출고 필터 정확성 + damaged_exchange 행 포함·배지
- AC-DEX-005/005a — "전체 출고 수량" 추적 가능·비취소 행만 합산 확인(취소 행 100·sku-null 행 50을 포함한 4행 픽스처) + ready_to_ship null 보존
- AC-DEX-005b — 취소·미추적 행이 "전체 출고 수량" 합산에서 실제로 제외됨을 별도 확인
- AC-DEX-005c — null quantity → 0 취급 확인 — **v1.3.0 D20 재작성**: 전원 null 픽스처로 교체(기존 mixed-null 픽스처는 SQL `SUM`이 NULL을 무시해 무판별력이었음)
- AC-DEX-006 — ready_to_ship 읽기 전용(재계산 금지) 확인, 올바른 참조 대상(`_recompute_order_aggregates`)으로 정정
- AC-DEX-007 — 매칭 없음 → 빈 결과(오류 아님)
- **AC-DEX-017 — v1.5.0 신규, 결정 H**: 동일 SKU 2건(rack_number="B-12"/"") 검색 시 저장된 값 그대로 각각 정확히 반환됨을 확인(하드코딩·오필드·항상-미배정 폴백 구현 판별)
- **AC-DEX-017a — v1.5.0 신규, 결정 H**: 검색 요청 처리 후에도 rack_number가 요청 이전 값 그대로임을 확인(쓰기 없음)
- **AC-DEX-018/018a — v1.5.0 신규, 결정 H**: 프론트엔드가 저장된 rack_number를 렌더링(018) / 빈 값은 "미지정"으로 렌더링(018a) 확인
- AC-DEX-008 — 기본값 1 + 서버측 필수 검증
- AC-DEX-009 — 정상 접수 시 damaged_quantity≠quantity 및 ready_to_ship 재계산(원인은 damaged_exchange 단락, logistics_status 불변) — 미호출/미수정 양쪽 다 잡아내는 판별력 확보
- AC-DEX-009a — 범위 밖 거부
- AC-DEX-009b — 재접수 덮어쓰기 확인
- ~~AC-DEX-009c~~ — **SUPERSEDED v1.6.0**(단락 삭제, 현행 코드에서는 이 픽스처가 `True`를 내는 것이 정상). 원문: 집계 단락 자체의 단위 수준 검증 — **v1.3.0 D14 재작성**: damaged_exchange 행의 `logistics_status`를 `"received"`로 고정(기존 `"not_shipped"` 픽스처는 신규 단락 없이도 이미 False가 나와 무판별력이었음); status는 "규칙 불변"으로 정정(D16)
- AC-DEX-010 — 메모 자동 생성(수량·**author** 정보 포함) 정확히 1건
- AC-DEX-011 — **v1.7.0 재작성**: `outbound_scheduled`/`recv=8`/`ship=2` 행에 파손 `4` 접수 → `not_shipped`/`recv=4`, `shipped_quantity=2`·`shipped_at=null`은 불변(초기 상태를 `not_shipped`로 두면 판별력이 없어지므로 다른 값으로 고정)
- **AC-DEX-011a — v1.7.0 신규**: `recv=0` 행에 파손 `3` → `recv=0`(음수 아님), 전환은 그대로 적용
- **AC-DEX-011b — v1.7.0 신규**: `recv=5`에 `3` 접수(→`2`) 후 `2`로 정정 재접수 → `recv=3`(`0` 아님)
- **AC-DEX-011c — v1.7.0 신규, 이 개정의 판별 기준**: 파손 접수된 `quantity=1` 행에 교환본 입고 업로드 1건 → `quantity_exceeded_count=0`, `recv=1`/`received` 복귀. `received_quantity`를 차감하지 않는 구현은 `_process_warehouse_receipt_rows`의 `recv + 건수 > quantity` 가드에 걸려 영구 거부됨(다른 AC는 필드 값만 보므로 이 경로를 못 잡음)
- AC-DEX-012/012a — 재발주 수량이 damaged_quantity 기준(환불 차감 적용) 확인
- AC-DEX-012b — 0-스킵 규칙이 damaged_quantity 기준으로 적용됨 확인, `quantity=10` 명시로 판별력 확보
- AC-DEX-012c — unordered 행 회귀 없음
- AC-DEX-012d — 4개 조회 지점(RunComparisonView/DailyReviewExcelView/UploadDailyReviewView/GenerateOrderFileView) quantity 기준 유지 확인
- AC-DEX-012e — VendorComparisonView quantity 기준 유지 확인 — **v1.3.0 D21 재작성**: PO-미연결(`purchase_orders__isnull=True`) 픽스처로 고정(연결 여부 미고정 시 정상 구현도 실패할 수 있었음); PO-연결 케이스는 Exclusions로 이관. **v1.3.1 D23 재작성**: 이 뷰는 수량을 응답에 내보내지 않으므로 블랙박스 단언이 불가능 — 내부 맵 `qty_by_sku`(`purchase_order_views.py:744-750`)에 대한 화이트박스 단언으로 변경
- AC-DEX-012f — ConfirmOrderView는 요청 바디 quantity를 그대로 사용, LineItem 필드를 읽지 않음 확인
- **AC-DEX-013b — v1.7.0 신규**: `0045` 백필이 `damaged_exchange` 행을 `not_shipped`/차감된 `recv`로 보정하고 부모 Order 집계를 재계산 / 무관한 Order는 불변. 부분 입고(`qty=5,dmg=2,recv=5`→`recv=3`)와 환불 정합(전량 환불된 형제 행은 두 집계에서 제외 → `status="not_shipped"`)도 함께 고정
- **AC-DEX-013/013a — v1.3.0 신규(D13)**: 백필 마이그레이션이 기존 damaged_exchange Order의 stale True→False로 갱신 / 무관한 다른 Order는 불변. **v1.3.1 D24 판별력 보강**: 013의 damaged_exchange 행을 `logistics_status="received"`로 고정(미고정 시 0033을 그대로 베낀 마이그레이션도 통과), 013a의 두 번째 Order에 `sku` not null 고정(미고정 시 백필 스코프 밖이라 기준이 공허)
- **AC-DEX-014/014a — v1.4.0 신규, 결정 G**: 단건/일괄 상태 변경 API가 `damaged_exchange`를 HTTP 400으로 거부(일괄은 전체 배치, 부분 반영 없음) 확인
- **AC-DEX-014b — v1.4.0 신규, 결정 G**: 다른 `purchase_status` 값은 두 엔드포인트에서 계속 정상 동작(REQ-DEX-014의 범위가 값 하나로 한정됨을 확인하는 회귀 방지 기준)
- **AC-DEX-015 — v1.4.0 신규, 결정 G**: Daily Review 엑셀 `선택="파손/교환"` 행이 `errors`+`skipped_count`로 명시 거부되고 `purchase_status`/`damaged_quantity`/노트 생성이 전부 무변경임을 확인
- **AC-DEX-015a — v1.4.0 신규, 결정 G**: 거부된 선택이 PurchaseOrder를 생성하지 않음을 별도 확인
- **AC-DEX-016 — v1.4.0 신규, 결정 G**: `PURCHASE_STATUS_OPTIONS`에 `damaged_exchange` 부재 + `PURCHASE_STATUS_LABELS`에 라벨 존재 확인
- **AC-DEX-016a — v1.4.0 신규, 결정 G**: 이미 `damaged_exchange`인 행이 발주 관리 화면에서 비활성 옵션으로 렌더링됨을 확인

## 변경 대상 파일

**백엔드**: `backend/order/models.py`(MODIFY, `damaged_quantity` 필드; `rack_number`는 SPEC-ORDER-013 기존 필드로 무변경) · `backend/order/migrations/00XX_lineitem_damaged_quantity.py`(NEW) · `backend/order/purchase_order_views.py`(MODIFY — 검색 뷰 NEW(`DamagedExchangeSearchView`, v1.5.0에서 `rack_number` 응답 필드 추가), 접수 뷰 NEW, `UnorderedItemsView.get()` MODIFY, `_recompute_order_aggregates` MODIFY [DELTA] — fan-in 8→9, `ready_to_ship`만 신규 규칙·`status` 규칙은 무변경(컬럼은 계속 함께 쓰임), `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView` MODIFY — `damaged_exchange` 거부, `UploadDailyReviewView` MODIFY — `blocked_reason` 보고) · `backend/order/excel_utils.py`(**MODIFY, v1.4.0 신규 — `_NOTE_TYPE_STATUS_MAP`에서 `"파손/교환"` 제거, `_BLOCKED_SELECTED_LABELS` 신설**) · `backend/order/migrations/00XX_backfill_ready_to_ship_damaged_exchange.py`(**NEW, v1.3.0 신규 — REQ-DEX-013, `0033` 선례 재사용**) · `backend/order/urls.py`(MODIFY)

**프론트엔드**: `frontend/src/pages/DamagedExchangePage/index.tsx`(NEW; **v1.5.0 신규 — 렉번호 컬럼 + "미지정" 폴백 렌더링 추가**) · `frontend/src/services/damagedExchangeApi.ts`(NEW; **v1.5.0 신규 — `DamagedExchangeSearchResultRow`에 `rack_number: string` 필드 추가**) · `frontend/src/hooks/useDamagedExchangeQueries.ts`(NEW) · `frontend/src/router/index.tsx`(MODIFY) · `frontend/src/components/Sidebar.tsx`(MODIFY) · `frontend/src/services/purchaseOrderApi.ts`(**MODIFY, v1.4.0 신규 — `PURCHASE_STATUS_OPTIONS`에서 `damaged_exchange` 제외, `PURCHASE_STATUS_LABELS` 신설**) · `frontend/src/pages/PurchaseOrders/tabs/UnorderedItemsTab.tsx`(**MODIFY, v1.4.0 신규 — 비활성 옵션 조건부 렌더링**)

**특성화 테스트(선행 조건, v1.3.0에서 D22 정정)**: 신규 작성이 아니라 `backend/order/tests/test_spec_012.py`의 `TestRecomputeOrderAggregatesReadyToShip`(9개 테스트, 기존 3분기 전부 커버)가 `damaged_exchange` 단락 추가 전후로 그대로 통과하는지 확인.

## Exclusions

- `book.Info.qty`, `order.WarehouseStock` 변경 없음
- `LineItem.fulfillment_status` 변경 없음
- Shopify 동기화 경로 변경 없음
- 기존 `/outbound`(SPEC-ORDER-015), `/rack-number`(SPEC-ORDER-013/014) 페이지 동작 변경 없음
- 신규 `logistics_status`/`purchase_status` enum 값 추가 없음
- 파손 접수 대량/Excel 업로드 경로 없음(행 단위 단건만) — v1.4.0에서 기존 Daily Review 엑셀 업로드의 `선택="파손/교환"` 경로는 신규 대량 접수 기능이 아니라 **명시적으로 거부**되도록 수정되었다(REQ-DEX-015) — 이 Exclusions 항목과 모순되지 않는다.
- `Order.status`를 **도출하는 규칙** 변경 없음 — `Order.ready_to_ship`은 더 이상 Exclusion이 아니다. **v1.7.0 정정**: 다만 그 이유는 더 이상 REQ-DEX-009c(단락 추가, v1.6.0에서 삭제됨)가 아니라, REQ-DEX-011이 `logistics_status`를 바꿔 **입력 데이터**를 바꾸기 때문이다 — 집계 함수 자체는 이 SPEC이 손대지 않는다. 이 SPEC이 건드리지 않는 것은 `status`(물류 상태 집계, `logistics_status` 기반)를 계산하는 **규칙** 쪽이다 — 컬럼 자체는 `ready_to_ship`과 함께 매번 다시 쓰인다(D16).
- `RunComparisonView`/`DailyReviewExcelView`/`UploadDailyReviewView`/`GenerateOrderFileView`/`VendorComparisonView`의 수량 계산 변경 없음 — **알려진 의도적 공백**: 이 5곳도 동일한 결함을 잠재적으로 가지나 이번 SPEC 범위 밖(사용자 확정, 2026-08-14), 후속 SPEC 후보. `ConfirmOrderView`는 quantity를 요청 바디에서 받아 이 공백에 해당하지 않는 구조적으로 별도인 사례(REQ-DEX-012c).
- **(v1.3.0 신규, D21) `VendorComparisonView`의 PO-연결된 `damaged_exchange` 행** — 이 뷰는 PO-미연결 LineItem만 집계하며 `damaged_exchange` 링크 예외가 없다. 실무에서 흔할 PO-연결된 파손 품목은 이 뷰에서 `0`으로 보고되는 채로 남는다 — AC-DEX-012e는 PO-미연결 경우만 검증한다.
- **(v1.4.0 신규, 결정 G) `damaged_exchange ⇒ damaged_quantity >= 1` 불변식의 모델 레벨 강제** — REQ-DEX-014/015가 차단하는 3개 엔드포인트 레벨에서만 강제되며 `LineItem` 모델 자체(`clean()`/`save()` 오버라이드, DB 제약)에는 승격되지 않는다. **알려진 한계**: Django 관리자 액션/management command/스크립트 직접 ORM 조작 등 4번째 쓰기 경로가 추가되면 동일 결함이 재발할 수 있다 — 후속 SPEC 후보.
- **(v1.5.0 신규, 결정 H) `rack_number` 편집 기능** — 이 SPEC은 읽기 전용으로만 노출한다(REQ-DEX-017/018). 생성·수정은 SPEC-ORDER-013의 기존 엔드포인트 전용이며, 이 SPEC은 그중 어느 것도 새로 만들거나 변경하지 않는다(REQ-DEX-017a).
- `LineItemDetailSerializer` 등 기존 상세 화면에 `damaged_quantity` 노출 없음
