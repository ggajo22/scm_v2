## Task Decomposition
SPEC: SPEC-PURCHASE-ORDER-008

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T-001 | `KyoboData.list_price` 필드 추가 + 마이그레이션 생성 | REQ-PO8-017 | - | backend/order/models.py, backend/order/migrations/0028_kyobodata_list_price.py | pending |
| T-002 | `parse_daily_review_excel()` 헤더 자동 탐지(구 1행/신 3행 공통 로직) + SKU 컬럼 이중 지원(`ISBN`/`Lineitem sku`) + 범례 컬럼 오분류 방지(이름 기반 인덱싱) | REQ-PO8-001, REQ-PO8-002, REQ-PO8-003 | - | backend/order/excel_utils.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-003 | 신 템플릿 벤더 공급가(`BOOXEN 공급가`/`교보 공급가`/`YES24 공급가` → `bs_price`/`ky_price`/`yes24_price`) 파싱 + 메모/노트 소스 컬럼 전환(구형식 `메모` ↔ 신형식 `Status`) | REQ-PO8-004, REQ-PO8-005 | T-002 | backend/order/excel_utils.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-004 | `_DISTRIBUTOR_LABEL_MAP`에 `YES24`→`yes24`, `재고`→`warehouse`(신규 범용 코드) 매핑 추가 + 기존 8개 매핑(처음교육/아가페/성서유니온/재고(한국)/재고(CA)/재고(NJ) 포함) 하위 호환 회귀 테스트 | REQ-PO8-006, REQ-PO8-007, REQ-PO8-012 | T-002 | backend/order/excel_utils.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-005 | `UploadDailyReviewView` 창고 재고 분기: `distributor_code == "warehouse"`(신 템플릿)를 `_WAREHOUSE_LOCATION_MAP` 처리 흐름에 편입 + `Status` 값(`한국재고`/`Fullerton재고`/`NJ재고`) 기반 위치 판별 + 미인식 Status 스킵(`skipped_count` 증가) | REQ-PO8-008 | T-003, T-004 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-006 | 창고 분기 `LineItemNote.assignee`를 판별된 위치 기반으로 결정(`korea`→"한국창고", `ca`/`nj`→"미국창고"), 구형식 `warehouse_ca`/`warehouse_nj` 분기의 기존 하드코딩 버그도 함께 수정 | REQ-PO8-009 | T-005 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-007 | `distributor_code == "yes24"` 발주 확정 분기 추가(단가 우선순위: 파싱된 `yes24_price` → `Yes24Data.price` 폴백, booxen/kyobo와 동일 PO 생성 경로 재사용) + 미인식 선택값(`total`/`합계`/`check`) 스킵이 신 템플릿에서도 유지되는지 회귀 검증 | REQ-PO8-010, REQ-PO8-011 | T-003, T-004 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-008 | Part A 회귀 게이트: 기존 `test_daily_review_upload.py` 전체(SPEC-PURCHASE-ORDER-005/007 케이스 포함) 무변경 통과 확인 | REQ-PO8-013 | T-002, T-003, T-004, T-005, T-006, T-007 | backend/order/tests/test_daily_review_upload.py (읽기 전용 회귀 실행) | pending |
| T-009 | Part B 벤더 upsert 배선: SKU 순회 루프마다 선택 값 유무·인식 여부와 무관하게 `BooxenData`/`Yes24Data`를 `update_or_create()`로 upsert(`UploadVendorFileView.post()`의 기존 defaults-dict 패턴을 그대로 재사용, 신규 헬퍼 함수 추출 없이 인라인 적용), `Yes24Data.list_price`는 defaults에서 명시적으로 제외 | REQ-PO8-014, REQ-PO8-015, REQ-PO8-018 | T-001, T-003, T-008 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | pending |
| T-010 | Part B `KyoboData` 필드 매핑(`교보 재고상태`→`available`, `교보 상품상태`→`status` 구분 유지, `ordered_qty`/`total_price`는 defaults 제외) + `list_price` 조건부 포함(`교보 정가` 컬럼 존재 시에만 defaults에 포함, 없으면 기존 값 유지) | REQ-PO8-016, REQ-PO8-017 | T-009 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | pending |

Planned files column is used by the Drift Guard to detect scope drift.
