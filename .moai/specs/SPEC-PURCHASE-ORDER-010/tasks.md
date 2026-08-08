## Task Decomposition
SPEC: SPEC-PURCHASE-ORDER-010

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|--------------|---------------|--------|
| T1 | `LineItem.PURCHASE_STATUS_CHOICES` + `LineItemNote.NOTE_TYPE_CHOICES`에 `damaged_exchange`/"파손/교환" 추가, 마이그레이션 0029 생성 | REQ-DMG-001, 004, 007 | - | backend/order/models.py, backend/order/migrations/0029_*.py, backend/order/tests/test_purchase_order_models.py | completed |
| T2 | `_NOTE_TYPE_STATUS_MAP`에 파손/교환 매핑 추가, Daily Review 자동 반영 + 기존 PATCH API 신규값 수용 검증 | REQ-DMG-002, 003, 004 | T1 | backend/order/excel_utils.py, backend/order/tests/test_daily_review_upload.py, test_purchase_orders.py | completed |
| T3 | 4개 공통 패턴 읽기측 쿼리(UnorderedItemsView/RunComparisonView/DailyReviewExcelView/UploadDailyReviewView) 예외 처리 | REQ-DMG-005 | T1 | backend/order/purchase_order_views.py, backend/order/tests/test_purchase_orders.py, test_daily_review_upload.py | completed (실제 파일: test_list_view.py 대신 test_purchase_orders.py 사용 — 아래 divergence 참조) |
| T4 | ConfirmOrderView 전용(패턴 B) 읽기측 예외 처리 | REQ-DMG-005B | T1 | backend/order/purchase_order_views.py, backend/order/tests/test_purchase_orders.py | completed |
| T5 | ConfirmOrderView.post() 쓰기측 자동 리셋 + 명시적 override 우선순위 + 배치범위 격리 | REQ-DMG-006 | T4 | backend/order/purchase_order_views.py, backend/order/tests/test_purchase_orders.py | completed |
| T6 | UploadDailyReviewView 비창고 분기 쓰기측 자동 리셋 + 배치범위 격리 + CS/창고 분기 상호작용 회귀 | REQ-DMG-006 | T3 | backend/order/purchase_order_views.py, backend/order/tests/test_daily_review_upload.py | completed |
| T7 | 하위호환/회귀 스위트 — GenerateOrderFileView 예외 처리 추가(원래 계획 수정, 아래 divergence 참조), 기존 unordered 흐름 회귀 없음, 마이그레이션 후 기존 레코드 무변경 | REQ-DMG-008 | T1,T3,T4,T5,T6 | backend/order/purchase_order_views.py, backend/order/tests/test_purchase_orders.py, test_purchase_order_models.py | completed (evaluator-active Phase 2.8a FAIL 반영 — REQ-DMG-008 "무변경" 가정이 틀렸음을 realistic fixture로 재현 후 수정) |
| T8 | SPEC-ORDER-011 독립성 재확인 (코드 리뷰, 데이터/쿼리 접점 없음) | DoD | T1-T7 | (리뷰 전용) | completed — `logistics_status` 필드가 코드베이스 전체에 존재하지 않음을 grep으로 확인(SPEC-ORDER-011 미구현 상태), 데이터/쿼리 접점 없음 |
| T9 | 프론트엔드 `PURCHASE_STATUS_OPTIONS`에 파손/교환 항목 추가 | 범위-포함 | - | frontend/src/services/purchaseOrderApi.ts, purchaseOrderApi.test.ts | completed |

이 파일은 git-tracked이며 구현 진행에 따라 상태가 갱신된다. Drift Guard(Phase 2A/2B)가 planned_files 컬럼을 참조한다.

## 설계 결정 / 리스크 (Phase 1에서 확정, manager-tdd 전달용)

- Choices 값: `PURCHASE_STATUS_CHOICES`에 `("damaged_exchange", "파손/교환")`; `NOTE_TYPE_CHOICES`에 `("파손/교환", "파손/교환")` (기존 스타일 일치)
- 마이그레이션 0029: `AlterField` 2개를 단일 파일에 (0012 컨벤션 재사용)
- 읽기측 5곳 모두 Q-object 조합, `.exclude(purchase_orders__isnull=False)` 유지 + `Q(purchase_status="damaged_exchange")` OR 결합
- **리스크**: M2M(`purchase_orders`) OR 조건 결합 시 중복 행 가능성 — `.distinct()` 필요 여부 구현 중 검증
- 쓰기측 리셋 순서: 자동 리셋 → 명시적 override(REQ-CON-022)가 마지막에 덮어씀
- 신규 signal/hook 인프라 금지 — 기존 bulk_update의 update_fields 리스트 확장만 사용

## Phase 2.8a 평가 반영 (evaluator-active FAIL → 수정 완료)

- **발견**: `GenerateOrderFileView.post()`(`purchase_order_views.py` ~219-221)이 `.exclude(purchase_orders__isnull=False)`를 그대로 유지 — damaged_exchange LineItem은 현실적으로 원래 발주에 이미 연결된 상태(파손/교환의 전제 자체가 "이미 발주했던 것")이므로, 이 쿼리가 그 SKU 전체를 "미확인 SKU"로 거부하고 배치 전체의 파일 생성을 막음. REQ-DMG-008/AC-DMG-008의 "코드 변경 불필요" 가정이 틀렸음이 evaluator의 realistic fixture 재현 테스트로 확인됨.
- **수정**: 동일 지점에 `_reorder_candidate_filter()`와 동일한 패턴의 예외 처리 추가 — `.exclude(Q(purchase_orders__isnull=False) & ~Q(purchase_status="damaged_exchange"))`. `_reorder_candidate_filter()` 자체를 재사용하지 않은 이유: 이 뷰의 베이스 필터가 `sku__in=requested`이지 `purchase_status__in=[...]`가 아니며, 애초에 purchase_status로 후보를 제한한 적이 없었기 때문(인라인 유지가 더 정확).
- **테스트**: `test_linked_damaged_exchange_sku_included_in_generated_file`(realistic fixture — 원래 PO에 연결된 상태에서 damaged_exchange로 전환) 추가, 기존 `test_unlinked_damaged_exchange_sku_included_in_generated_file`은 회귀 케이스로 유지, `test_non_damaged_exchange_linked_sku_still_rejected_as_unknown` 추가(예외가 damaged_exchange에만 한정됨을 확인). "코드 변경 없음"을 주장하던 잘못된 단언 테스트(`test_generate_order_file_view_source_unmodified_no_purchase_status_filter`)는 제거.
