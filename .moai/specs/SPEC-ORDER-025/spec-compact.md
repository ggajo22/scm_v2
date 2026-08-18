# SPEC-ORDER-025 — Compact Summary

## 무엇을 만드는가

미발주 현황 화면(`UnorderedItemsTab.tsx`)에 4가지 변경:

1. **[NEW]** 각 행에 "발주처리" 버튼 → 모달에서 확정 발주처(드롭다운 6종 + 자유 텍스트) + 확정 단가(선택)를 입력해 그 LineItem 1건만 발주처리. 신규 백엔드 엔드포인트 `POST /api/purchase-orders/line-items/<pk>/confirm/`가 `PurchaseOrder(status="confirmed")`를 생성하고 M2M 연결한다.
2. **[MODIFY]** "자동 추천 발주처" 컬럼 및 백엔드 `auto_distributor`/`rule_map` 제거.
3. **[MODIFY]** 보류/제외 품목 뷰에서 `other_publisher`(타출판사) 제외 — `EXCLUDED_PURCHASE_STATUSES`를 3개 값으로 축소.
4. **[MODIFY, v1.2.0 신규]** `other_publisher` 수동 지정 통로 차단 — `PURCHASE_STATUS_OPTIONS`에서 제거(라벨 맵은 유지), `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`가 damaged_exchange와 동일하게 400 거부.
5. **[MODIFY, v1.3.0 신규]** Daily Review 업로드의 타출판사 분기가 메모/Status 셀 공란이어도 항상 노트를 생성하도록 좁게 수정(REQ-LCONF-309) — v1.2.0판은 "Daily Review는 항상 노트를 동반한다"고 전제했으나 실제로는 조건부였음이 밝혀져(plan-audit ND-A) 이 항목으로 정정·보완했다. 다른 3개 CS 유형(주문취소/주문보류/CS필요)은 영향받지 않는다.

## 핵심 결정

- 처리 그레인은 LineItem 1건(SKU 전체 아님) — 기존 `ConfirmOrderView`(SKU 그레인)는 재사용 불가, 신규 엔드포인트 필요.
- 신규 PurchaseOrder는 `status="confirmed"`(`UploadDailyReviewView` 선례, `ConfirmOrderView`의 `"pending"`과 다름) — 담당자 직접 입력 = 확정된 응답이므로.
- `PurchaseOrder.quantity`는 화면에 표시된 순수량(환불 차감, damaged_exchange는 damaged_quantity 기반)을 요청 시점에 재계산해 기록.
- 창고(warehouse_korea/ca/nj)는 드롭다운에서 의도적으로 제외 — 재고 차감은 Daily Review 업로드 경로에서만.
- 에러 응답은 `{"error": ...}` 키 사용(같은 URL 패밀리인 `LineItemStatusUpdateView` 컨벤션, `ConfirmOrderView`의 `{"detail": ...}`가 아님).
- distributor 자유 텍스트는 20자 제한(`PurchaseOrder.distributor` 필드 한도) — 초과 시 400.
- **(v1.2.0/v1.3.0)** `other_publisher`는 이 SPEC 이후 Daily Review 업로드로만 생성될 수 있다(v1.2.0, REQ-LCONF-304~307). 그런데 그 업로드 경로 자체도 메모/Status 셀이 공란이면 노트 없이 `other_publisher`만 기록하는 조건부 동작이었다(v1.3.0에서 코드 추적으로 발견, plan-audit ND-A) — REQ-LCONF-309를 추가해 타출판사 분기에서만 공란이어도 기본 문구로 노트를 생성하도록 고쳐, 두 사각지대(수동 지정 통로 + 메모 공란 업로드)를 모두 닫았다.

## 무엇을 만들지 않는가 (요약, 전체는 spec.md Exclusions)

- 창고재고 자동 차감 (범위 밖, Daily Review 업로드 경로 유지)
- 일괄(bulk) 발주처리 (LineItem 1건만)
- `ConfirmOrderView` 로직 변경 (무변경) / `UploadDailyReviewView`는 REQ-LCONF-309가 규정하는 좁은 예외(타출판사 분기의 노트 생성 조건) 외 무변경(v1.4.0 정정 — ND-F, 위 5번 항목·`spec.md` Exclusions 3번과 정합)
- `DistributorVendorRule` CRUD/발주처 규칙 설정 탭 변경 (무변경, 소비처만 제거)
- `on_hold`/`order_cancelled`/`cs_required` 노출 범위 변경 (무변경, `other_publisher`만 제거)
- 레거시(수동 PATCH 지정 또는 메모 공란 Daily Review 업로드로 생성된) `other_publisher` 행의 소급 백필 (범위 밖 — "알려진 제약" 참조, v1.4.0 정정 — ND-F, `spec.md` Exclusions 6번과 정합)
- `LineItem.PURCHASE_STATUS_CHOICES`(모델 필드)에서 `other_publisher` 제거 (PATCH 엔드포인트 쓰기만 막음, Daily Review는 여전히 이 값을 써야 함)

## 영향 파일

백엔드: `purchase_order_views.py`(신규 뷰 + 4곳 축소/확장 + 독스트링 2곳 갱신), `urls.py`(라우트 1개), `test_spec_025.py`(신규), `test_spec_018.py`(**7개 참조 지점**), `test_purchase_orders.py`(auto_distributor 단정 2건 + `test_patch_all_six_choices`→5개 + `other_publisher` 거부 테스트 신설 2건), `test_daily_review_upload.py`(**v1.3.0 신규 [MODIFY] 대상** — 신규 테스트 3건, `test_spec_024.py`는 이 세션에서 재확인한 결과 무수정).
프론트엔드: `purchaseOrderApi.ts`(`UnorderedItem` 타입 축소 + `confirmLineItem` 신설 + `PURCHASE_STATUS_OPTIONS`에서 `other_publisher` 제거), `purchaseOrderApi.test.ts`(**v1.2.0 신규 [MODIFY] 대상**), `usePurchaseOrderQueries.ts`, `UnorderedItemsTab.tsx`, `LineItemConfirmModal.tsx`(신규), 관련 테스트 2개.

`GET /unordered/`의 쿼리 수는 `rule_map` 제거로 3(`test_spec_018.py:64` 기존 핀)에서 **정확히 2**로 감소한다(대수적으로 도출된 값, `acceptance.md` AC-LCONF-205로 고정).

## 알려진 제약(요약, 전체는 spec.md "알려진 제약")

- `damaged_exchange` 행을 발주처리하면 `PurchaseOrder.quantity`(damaged_quantity 기반, 예 3)와 발주서 목록의 `net_quantity` 표시값(`_attach_net_quantity`, 항상 원본 quantity 기반, 예 10)이 다르게 보일 수 있다 — `ConfirmOrderView`도 이미 갖고 있는 기존 제약이며 이 SPEC은 고치지 않는다.
- **(v1.2.0/v1.3.0)** 이 SPEC 이전에 (수동 PATCH 지정 또는 메모 공란 Daily Review 업로드로) 생성되어 노트가 없는 레거시 `other_publisher` 행은 R4 적용 후 주문상세 화면에서만 조회 가능하다(소급 백필 범위 밖).
- **(v1.2.0)** 신규 드롭다운 값 `yes24`는 `OrderDetailPage.tsx`의 `DISTRIBUTOR_LABELS`에 없어 주문상세에서 원시 문자열로 표시된다(라벨 보완은 범위 밖).

## 문서

- 상세 요구사항(EARS): `spec.md`
- 구현 계획/마일스톤/mx_plan: `plan.md`
- Given-When-Then 인수 기준: `acceptance.md`
- 코드베이스 근거/검증 내역: `research.md`
