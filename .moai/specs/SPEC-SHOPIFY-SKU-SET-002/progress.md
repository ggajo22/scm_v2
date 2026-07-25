# SPEC-SHOPIFY-SKU-SET-002 진행 상황 (Progress Log)

방법론: TDD (RED-GREEN-REFACTOR), brownfield 강화 (기존 코드 직접 읽은 뒤 실패 테스트 작성)

## Phase 1 — 스키마 변경 (T-001) — done

- `LineItem.Meta.unique_together` → `[("order", "shopify_line_item_id", "sku")]`
- 마이그레이션 `0025_lineitem_unique_together_with_sku.py` 생성 (AlterUniqueTogether)
- RED: `TestLineItemUniqueTogetherWithSku` 2개 테스트 작성, 마이그레이션 적용 전 1개 실패 확인
  (동일 shopify_line_item_id + 다른 sku 저장 시 구 제약 위반)
- GREEN: 모델 변경 + 마이그레이션 생성 후 2개 테스트 통과
- AC-001-1, AC-001-2 검증 완료. AC-001-3(마이그레이션 순서)는 Phase 4에서 dependencies로 재확인.

## Phase 2 — 싱크 파이프라인 번들-인식형 전개 (T-002, T-005) — done

- `_sync_single_order()`에 `bundle_map` 1회 로드 + 번들-인식형 `update_or_create` 루프 추가
- 비번들 경로는 100% 기존과 동일(lookup: order+shopify_line_item_id, sku는 defaults) 유지
- 번들 경로는 lookup에 sku=member_isbn 포함(REQ-SKUSET2-003 명시 코드와 일치)
- RED: `test_shopify_orders.py`에 8개 신규 테스트 추가, 6개 실패(번들 전개 미구현) + 2개 통과
  (회귀-안전 케이스는 이미 기존 코드로도 통과 — 예상된 동작) 확인
- GREEN: 구현 후 8개 모두 통과. 전체 `test_shopify_orders.py` 22/22 통과
- REFACTOR: 라인 길이 정리(ruff baseline 대비 신규 위반 0건), 헬퍼 `_make_bundle_mapping` 도입
- AC-003-1, AC-003-2, AC-003-3, AC-004-1, AC-004-2, AC-005-1 + 엣지 케이스(quantity=0, sku=None) 검증

## Phase 3 — 화면/발주 뷰 정리 (되돌리기) (T-003, T-006 일부) — done

- `UnorderedItemsView.get()`: `bundle_map`/`expanded` 블록 완전 제거, `results` 직접 반환
- `GenerateOrderFileView.post()`: `member_to_bundle`/`requested_underlying`/`underlying_found_map`
  역방향 매핑 로직 완전 제거, spec.md REQ-SKUSET2-009 명시 코드로 정확히 복원
- `ShopifySkuSetMapping` import를 `purchase_order_views.py`에서 제거(더 이상 미사용 확인)
- `models.py`의 `ShopifySkuSetMapping` `@MX:REASON` fan-in 주석을
  `_sync_single_order`로 갱신(UnorderedItemsView는 더 이상 fan-in 소스 아님)
- RED: `TestUnorderedItemsView`에 2개, `TestGenerateOrderFileView`에 AC-009-2(소스 검사) 1개 추가
  → 2개 실패(is_bundle_member 필드 존재, ShopifySkuSetMapping 참조 존재) 확인
- GREEN: 코드 제거 후 25/25 통과(신규 테스트 포함 `TestUnorderedItemsView`+`TestGenerateOrderFileView`)
- `TestGenerateOrderFileView`의 커밋 6d2dfc4발 3개 테스트를 "이미 전개된 LineItem" 픽스처로 재작성
  (반드시 RED가 되진 않음 — 매핑이 없는 시나리오에서는 구코드도 identity-mapping으로 동작하여
  이미 정상 동작했기 때문. AC-009-2가 실질적 RED 테스트 역할을 함. spec.md의 "버그 시나리오가
  더 이상 발생할 수 없다" 설명과 일치)
- AC-007-1, AC-008-1, AC-009-1, AC-009-2 검증 완료

## test_shopify_sku_set.py 정리 (T-006) — done

- `order_with_bundle_lineitem` 픽스처 → `order_with_expanded_bundle_lineitems`로 교체
  (싱크 후 상태를 시뮬레이션하도록 2개 LineItem 행을 미리 생성)
- `TestUnorderedItemsBundleExpansion` → `TestUnorderedItemsSyncTimeExpansion`으로 재작성
  (is_bundle_member/bundle_sku 필드 부재 검증으로 전환)
- `bundle_mapping` 픽스처는 CRUD 테스트에서 계속 사용되므로 유지
- 전체 파일 28/28 통과

## Phase 4 — 데이터 백필 마이그레이션 (T-004) — done

- `0026_backfill_bundle_lineitems.py` 생성(`RunPython`, dependencies=[0025])
- 첫 번째(sort_order 최소) member_isbn은 원본 행 UPDATE(PK/노트 보존),
  나머지는 신규 LineItem 생성(quantity 등 필드 그대로 복사, 나누지 않음)
- `reverse_code = migrations.RunPython.noop` + 완전 역백필 불가 사유 docstring 명시
- 신규 테스트 파일 `test_backfill_bundle_lineitems_migration.py` 작성(6개 테스트,
  `MigrationLoader`로 실제 마이그레이션의 RunPython 연산을 직접 호출하는 방식 채택 —
  데이터 마이그레이션이라 스키마 변경이 없어 안전, MySQL 트랜잭션 내 DDL 이슈 회피)
- AC-011-1, AC-011-2, AC-011-3, AC-012-1 + 멱등성/노매핑 엣지 케이스 검증. 6/6 통과

## T-007 (권장) — 재동기화 엣지 케이스 회귀 테스트 — done

- `test_order_resync.py`에 매핑 변경 후 재동기화 시 "고아 행" 시나리오 회귀 테스트 1개 추가
- ISBN-A는 갱신, ISBN-C는 신규 생성, ISBN-B(제거된 매핑)는 자동 삭제되지 않고 잔존함을 확인
  (REQ-SKUSET2-010의 의도적 미해결 엣지 케이스를 코드로 고정)
- 10/10 통과 (기존 9개 + 신규 1개)

## Phase 6 — 전체 회귀 검증 (T-008) — done

관련 파일 전체를 한 배치로 실행(원본 지시대로 `test_warehouse.py`/`test_sync_view.py` 등
무관 파일은 제외):

```
order/tests/test_shopify_orders.py
order/tests/test_shopify_sku_set.py
order/tests/test_purchase_orders.py
order/tests/test_order_resync.py
order/tests/test_auto_dist.py
order/tests/test_purchase_order_models.py
order/tests/test_backfill_bundle_lineitems_migration.py
```

결과: **253 passed** (0 failed), 309.96초 (MySQL RDS 테스트 DB `test_gimssine_test` 대상 —
research.md가 가정한 SQLite와 실제로는 다름, `.env`의 `DB_ENGINE=mysql`이 우선 적용됨을
Phase 1 RED 단계에서 직접 확인함).

## 품질 게이트

- `ruff check`: 모든 수정/신규 파일에서 baseline 대비 신규 위반 **0건** 확인(전/후 카운트 diff로
  검증). `models.py`(3→2), `shopify_orders.py`(8→7), `purchase_order_views.py`(19→17)는 오히려
  개선(제거된 코드 덕분); 나머지 파일은 baseline과 동일. 신규 파일(`0025_*.py`, `0026_*.py`,
  `test_backfill_bundle_lineitems_migration.py`)은 위반 0건. 사전 존재하던 E501/I001은 수정
  범위 밖이라 그대로 둠(Scope Discipline).
- `ruff format --check`: 프로젝트 baseline 자체가 비정렬 상태(이 SPEC과 무관하게 사전 존재) —
  전체 파일 강제 재포맷은 하지 않음(DoD는 "ruff 린트 오류 없음"이며 포맷 강제가 아님).
- 커버리지: `--cov=order`로 측정. 전체 `order` 앱 대비 51%는 관련 없는 다른 테스트 파일
  (test_daily_review_upload.py 등)을 이 실행에 포함하지 않아 낮게 나온 값 — 파일 전체가 아니라
  **이 SPEC이 실제로 변경한 코드 라인**만 놓고 확인함:
  - `shopify_orders.py`: Missing 라인(13-18, 32, 65-75, 78-79, 97, 142, 152, 224, 257-258,
    268-326)이 모두 내가 수정한 범위(약 88-208번째 줄, bundle_map 로드 + 전개 루프) **밖**에
    있음 → 신규/변경 코드는 100% 커버됨(누락은 전부 `sync_store()`/`_build_fulfillment_location_data`
    등 미수정 함수).
  - `purchase_order_views.py`: Missing 라인(269, 363-514, 549-550, 601-612, 696, 731-738,
    827-941, 958-1107, 1223, 1258-1259)이 모두 `UploadVendorFileView`(245-350),
    `RunComparisonView`(351-521), `VendorComparisonView`(522-648), `ConfirmOrderView`(649-814),
    `DailyReviewExcelView`(815-943), `UploadDailyReviewView`(944-1117) 등 **미수정 클래스**
    범위 — 내가 수정한 `UnorderedItemsView`(70-141) + `GenerateOrderFileView`(142-244)에는
    누락 라인이 하나도 없음 → 100% 커버.
  - `models.py`: 97%, 누락 라인(270, 290, 312, 329, 363, 386, 405, 426)은 모두 다른 모델
    영역(내가 수정한 `LineItem.Meta`/`ShopifySkuSetMapping` 주석 라인은 코드 실행문이 아니므로
    측정 대상이 아님).
  - `0026_backfill_bundle_lineitems.py`: 95%(20문 중 19 커버), 누락 1줄(59번째,
    `if not member_isbns: continue`)은 단일 함수 호출 내에서는 도달 불가능한 방어 코드로
    문서화됨(§Phase 4 참고) — 의도적 gap.
  - 결론: DoD의 "신규/변경 코드 커버리지 85% 이상" 기준은 실질적으로 충족(변경된 코드 라인
    기준 100%에 근접, 유일한 gap은 문서화된 방어 코드 1줄).

## Phase 7 — evaluator-active thorough review 후속 조치 (post-review fixes) — done

evaluator-active의 thorough 리뷰에서 지적된 2건(Finding 1 critical, Finding 2 warning)을 처리.

### Finding 1 (critical): REQ-SKUSET2-006 헤드라인 주장에 대한 직접 테스트 부재

evaluator-active가 확인한 갭: 기존 환불 테스트는 모두 단일 행 시나리오였고, 기존 "2개 행이
동일 `shopify_line_item_id` 공유"(멀티행) 테스트에는 환불이 전혀 붙어있지 않았다. "번들-확장된
2개 이상의 LineItem 행 + 그 shopify_line_item_id에 대한 Refund 존재"라는 정확한 조합은 어디에도
직접 테스트되지 않았다(AC-006-1/AC-006-2가 문서에는 있었지만 실제 테스트로 구현되지 않음).

- `test_purchase_orders.py::TestUnorderedItemsView`에 2개 회귀 테스트 추가:
  - `test_pre_expanded_bundle_member_rows_with_partial_refund` (AC-006-1): 2개 행(quantity=4)이
    동일 `shopify_line_item_id`를 공유하고, 그 id에 대해 `Refund(quantity=1)`이 있을 때 두 행
    모두 독립적으로 `quantity=3`(4-1)으로 응답됨을 검증.
  - `test_pre_expanded_bundle_member_rows_fully_refunded_excluded` (AC-006-2): 동일 설정에서
    `Refund(quantity=4)`(전체 환불) → 두 행 모두 미발주 목록에서 제외됨을 검증.
- REQ-SKUSET2-006이 언급하는 6개 `Refund` OuterRef 서브쿼리 사이트 중 두 번째 사이트인
  `GenerateOrderFileView`도 동일한 갭(기존 2행 번들 테스트에 환불 미부착)을 가지고 있어,
  `TestGenerateOrderFileView`에도 동일 구조의 회귀 테스트 2개를 추가:
  - `test_pre_expanded_bundle_member_rows_partial_refund_in_excel` (AC-006-1 상당):
    Excel 생성 시 두 행 모두 net=3으로 각자의 행에 반영됨을 검증.
  - `test_pre_expanded_bundle_member_rows_fully_refunded_excel_unknown` (AC-006-2 상당): 전체
    환불 시 두 행 모두 `unknown_skus`에 포함됨(Excel에는 나타나지 않음)을 검증.
- 4개 테스트 모두 GREEN 상태로 즉시 통과(기존 로직 자체에는 버그가 없음을 evaluator-active가
  이미 코드 추적으로 확인했으므로, 이는 커버리지 갭을 메우는 회귀 테스트이지 버그 수정이 아님).

### Finding 2 (warning): OrderResyncView 트랜잭션 미보호

evaluator-active가 확인한 리스크: `backend/order/views.py`의 `OrderSyncView._sync_store_safe()`는
`sync_store()` 호출을 `transaction.atomic()`으로 감싸지만, `OrderResyncView.post()`는
`sync_single_order_from_shopify()` 호출에 트랜잭션 보호가 없었다. `_sync_single_order()`가 번들
라인 아이템 1건당 N개의 `LineItem.objects.update_or_create()`를 개별 호출하므로, 재동기화 중
크래시/네트워크 장애가 루프 중간에 발생하면 번들의 구성 ISBN 행 일부만 저장된 채 남을 수 있어
"N개 행은 항상 일관된 구성원 집합을 공유한다"는 불변조건(소멸 로직·환불 서브쿼리가 암묵적으로
의존)이 깨질 수 있음.

- `OrderResyncView.post()`의 `sync_single_order_from_shopify(...)` 호출을
  `transaction.atomic()`으로 감쌈(`OrderSyncView._sync_store_safe()`와 동일한 기존 패턴 재사용).
  위험 배경을 설명하는 주석 추가.
- 방어적 조치로, 크래시 주입 테스트는 작성하지 않음(요청 지시대로 — 과도한 노력 대비 효과 낮음).
  기존 `test_order_resync.py` 전체(10개, 신규 고아-행 회귀 테스트 포함)가 변경 없이 통과함을
  격리 실행으로 확인 — 성공 경로 동작에 변화 없음(투명한 래핑).
- `sync_single_order_from_shopify()`는 자체 트랜잭션/커밋을 수행하지 않고(네트워크 호출 →
  `_sync_single_order()` DB 쓰기 순서), 중첩 `transaction.atomic()`과 호환되지 않는 부수효과가
  없음을 소스 확인함. `OrderSyncView`가 이미 `sync_store()`(네트워크+DB 혼합 함수) 전체를
  `transaction.atomic()`으로 감싸는 동일 패턴이 프로덕션에서 이미 쓰이고 있어 선례와 일치.

### 검증 결과

- `pytest order/tests/test_purchase_orders.py`: 격리 실행 시 전체 통과(신규 4개 포함). 병렬로
  다른 스위트와 동시 실행 시 원격 MySQL RDS 테스트 DB(`test_gimssine_test`)를 공유하여
  `orders_yes24data` 테이블 누락/DB 미존재 오류가 발생함을 확인 — 이는 SPEC-002 변경과 무관한
  테스트 실행 환경상의 동시성 아티팩트이며(RDS 단일 인스턴스에 두 pytest 프로세스가 동시에
  스키마 생성/삭제를 수행), 순차(격리) 실행으로 재현되지 않음을 확인해 원인으로 확정.
- `pytest order/tests/test_order_resync.py`: 격리 실행 10/10 통과.
- `ruff check order/views.py order/tests/test_purchase_orders.py`: 기존 baseline과 동일한
  위반만 남아있음(I001 import 정렬, 사전 존재 E501 등 — 모두 이 변경 범위 밖의 기존 라인,
  신규 추가 코드에는 0건). Scope Discipline 준수.

## Phase 8 — 후속 버그 수정: title 데이터 버그 (commit e9a6f42) — done

별도 신규 SPEC 없이 이 SPEC의 직접적인 후속 버그로 처리(아키텍처 결정이 아닌 단순 버그 수정).

### 근본 원인

`_sync_single_order()`가 번들 Shopify 라인 아이템을 N개의 member-ISBN `LineItem` 행으로
전개할 때, `common_defaults`(번들 자신의 Shopify 표시 title, 예: "GITANMATH-F SET" 포함)를
Shopify 라인 아이템 1건당 1회만 생성한 뒤 이를 **모든** member 행에 그대로 복사하고
있었음 — 결과적으로 전개된 모든 행이 각자의 실제 도서 제목이 아니라 번들 제목을 갖게 됨.
두 화면에 영향:
- 주문 상세 페이지(`OrderDetailPage.tsx`)가 `LineItem.title`을 직접 표시
- 발주 관리 페이지(`PurchaseOrderHistoryTab.tsx`)가 `PurchaseOrder.title`(PO 확정 시점에
  `LineItem.title`에서 스냅샷된 값)을 표시 — 스냅샷이므로 싱크 파이프라인만 고쳐서는
  이미 생성된 PO는 고쳐지지 않아 별도 백필 필요.

### RED-GREEN-REFACTOR (reproduction-first)

- RED: `test_shopify_orders.py`에 3개 신규 테스트 추가
  (`test_sync_bundle_expands_with_real_book_titles`,
  `test_sync_bundle_member_title_none_when_isbn_not_in_catalog`,
  `test_sync_non_bundle_line_item_title_unaffected_by_title_fix`) — 앞의 2개가 정확한 이유로
  실패함을 확인(`title == "Test Book"`/번들 title, 기대값은 실제 도서 제목/`None`).
  기존 `test_sync_bundle_sku_expands_to_member_isbn_rows`의 `row.title == "Test Book"` 단언도
  버그를 정답으로 고정하고 있었으므로 `row.title is None`(해당 테스트의 ISBN-A/B는 Inven/Info
  미등록)으로 함께 수정.
- GREEN: `shopify_orders.py`에 `book.models.Inven` 임포트 + `_build_title_map()` 헬퍼
  (shopify_sku_set_views.py의 동일 패턴 재사용) 추가. `_sync_single_order()`에서 주문 내 모든
  번들 라인 아이템의 member ISBN을 먼저 수집한 뒤 **주문 1회당 1회**만 title_map을 배치 조회
  (기존 `bundle_map` 1회 로드와 동일한 N+1 방지 원칙), member 행 각각에
  `title_map.get(member_isbn)`(카탈로그에 없으면 `None`) 적용. 비번들 경로는 `common_defaults`를
  그대로 사용해 100% 영향 없음.
- 3개 신규 테스트 GREEN 전환 확인, 기존 `test_shopify_orders.py` 전체 회귀 없음.

### 데이터 백필 마이그레이션 — `0027_backfill_bundle_title_data.py`

0026과 별개(0026은 스키마 이후 행 분할, 0027은 그 분할된 행들에 남은 잘못된 title 데이터 정정).
`dependencies=[("order", "0026_backfill_bundle_lineitems")]`. 두 개의 `RunPython` 연산:

1. `backfill_lineitem_titles`: `ShopifySkuSetMapping`의 (bundle_sku, member_isbn) 쌍 전체를
   기준으로, `LineItem.objects.filter(sku=member_isbn, title=bundle_sku)`(버그로만 도달 가능한
   정밀 시그니처 — 이미 정상이거나 수동 수정된 행은 건드리지 않음)를 실제 도서 제목(없으면
   `None`)으로 갱신.
2. `backfill_purchase_order_titles`: 동일 시그니처로 `PurchaseOrder`를 갱신하되, `title`이
   NOT NULL이므로 카탈로그 미매치 시 `sku`(ISBN) 자체로 폴백
   (`purchase_order_views.py`의 `title = unordered_lis[0].title or sku` 관례와 동일).

`reverse_code = migrations.RunPython.noop`(양쪽 연산 모두) — 스키마가 아닌 데이터 정정이라
역백필이 의미 없음을 모듈 docstring에 명시(0026과 달리 PK/관계 정보 손실 위험은 없지만,
"버그로 인한 원상태"와 "그 이후 수동 재수정" 구분이 불가능해 원복 자체가 무의미).

### 신규 테스트 — `test_backfill_bundle_title_data_migration.py`

`MigrationLoader`로 두 `RunPython` 연산을 직접 호출하는 방식(0026 테스트와 동일 컨벤션).
11개 테스트: LineItem 정정(실제 제목/`None`), 정밀도(이미 정상인 행·무관 SKU·수동 수정된 행은
불변), PurchaseOrder 정정(실제 제목/ISBN 폴백, 절대 `None` 아님), 멱등성, `reverse_code`가
양쪽 연산 모두 `noop`인지, 매핑 자체가 없을 때 no-op인지.

### 품질 게이트

- `ruff check`: `shopify_orders.py`는 신규 임포트(`from book.models import Inven`)를 기존
  I001 위반 블록에 추가하면서 동일 블록에 대해 `--fix`(import 정렬)만 적용 —
  baseline 7건 → 7건(구성만 이동, 신규 위반 0건). `test_shopify_orders.py`는 baseline 7건과
  완전 동일(신규 테스트 코드에는 0건). 신규 파일(`0027_*.py`,
  `test_backfill_bundle_title_data_migration.py`)은 위반 0건.
- `ruff format`: 신규 파일(`0027_*.py`)에는 전체 적용. 기존 수정 파일(`shopify_orders.py`,
  `test_shopify_orders.py`)은 SPEC-002 선례와 동일하게 baseline 자체가 비정렬 상태라 전체
  재포맷은 강제하지 않음(변경 범위 밖 Scope Discipline).
- Scope: `backend/order/shopify_orders.py`, `backend/order/migrations/0027_*.py`,
  `backend/order/tests/test_shopify_orders.py`, `backend/order/tests/test_backfill_bundle_title_data_migration.py`,
  이 progress.md만 수정. 프론트엔드는 무변경(두 화면 모두 백엔드가 주는 title을 그대로
  렌더링하므로 프론트 로직 변경 불필요).

## 발견된 사실 (research.md 대비 차이)

- research.md는 pytest 실행 환경을 SQLite로 서술했으나, 실제로는 `.env`의
  `DB_ENGINE=django.db.backends.mysql` + `DB_NAME=gimssine_test`가 pytest.ini 기본값보다
  우선 적용되어 원격 MySQL RDS 테스트 DB(`test_gimssine_test`)를 사용함. 이는 태스크 지시문에서
  이미 "prior session"이 확인한 사실로 언급되어 있어 별도 STOP 없이 진행함.
