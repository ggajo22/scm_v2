---
id: SPEC-PURCHASE-ORDER-009
version: 1.1.0
status: planned
created: 2026-07-26
updated: 2026-07-27
author: ggajo
priority: High
issue_number: ~
---

# Daily Review 업로드 N+1 쿼리 제거 (대용량 파일 성능 최적화)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-07-26 | ggajo | 최초 작성 |
| 1.1.0 | 2026-07-27 | ggajo | 픽스 사이클 2: REQ-PO9-007(`PurchaseOrder` 배치 생성) 구현 완료. 실제 파일 재측정 결과 120초/795쿼리 → 3.50초/14쿼리로 목표(초 단위) 달성. REQ-PO9-001 코드 스니펫에서 `unique_fields` 제거(MySQL `NotSupportedError` 회피, 픽스 사이클 1 구현과 일치). 쿼리 수 상한 회귀 테스트 픽스처(`_make_bulk_daily_review_fixture`)가 PO 생성 분기 행 수를 `total_rows`에 비례하도록 수정(기존에는 3행 고정이라 이 분기의 배칭 효과가 테스트에서 측정되지 않았음). |

---

## 문제 정의

SPEC-PURCHASE-ORDER-008(커밋 `ce694c5`, `aca0999`)에서 `UploadDailyReviewView.post()`(`backend/order/purchase_order_views.py:967`)가 업로드된 모든 행에 대해 `선택` 값 유무·인식 여부와 무관하게 `BooxenData`/`KyoboData`/`Yes24Data`를 동기화하도록 변경되었다(REQ-PO8-014). 이 변경은 SPEC-008 개발 단계에서 57행 규모의 소형 테스트 픽스처로만 검증되었다.

배포 후 사용자가 실제 프로덕션 파일(`Daily Order Review Template 20260725.xlsx`, 약 400~450개 SKU)로 업로드를 시도한 결과 처리 시간이 극도로 길다는 문제가 보고되었다.

### 확인된 원인 진단 (실제 dev DB 대상 실측, `transaction.set_rollback(True)`로 롤백하여 데이터 영향 없음 — 아래 수치는 검증된 사실로 간주하고 재측정하지 않는다)

- 약 400개 SKU 규모의 실제 파일 1회 업로드에 **1447초(약 24분)**가 소요됨(`django.test.RequestFactory` + `force_authenticate`로 `UploadDailyReviewView.as_view()`를 실제 MySQL dev DB에 대해 직접 호출, `transaction.atomic()` + `transaction.set_rollback(True)`로 측정).
- 근본 원인: `UploadDailyReviewView.post()`의 SKU 순회 루프(`for sku, item in sku_map.items():`, `purchase_order_views.py:1011`)가 SKU 1개당 배칭 없이 다수의 개별 동기 DB 왕복을 발생시킴:
  - `BooxenData.objects.update_or_create(sku=sku, defaults=booxen_defaults)` (1041번째 줄) — 내부적으로 SELECT 후 INSERT/UPDATE (≈2쿼리)
  - `Yes24Data.objects.update_or_create(...)` (1048번째 줄) — ≈2쿼리
  - `KyoboData.objects.update_or_create(...)` (1068번째 줄) — ≈2쿼리
  - `LineItem.objects.filter(sku=sku, purchase_status="unordered").exclude(purchase_orders__isnull=False).select_for_update()`을 `list(...)`로 즉시 평가(1070-1074번째 줄) — SKU마다 1쿼리(SKU 간 배칭 없음)
  - 분기(창고/CS노트/비창고 PO 생성)에 따라 추가로: `WarehouseStock` filter+update(1124-1130번째 줄), `LineItem.bulk_update()`(SKU별로 개별 호출, 전체 요청 단위로 배칭되지 않음), `LineItemNote.objects.create(...)`가 LineItem별로 개별 호출됨(1092-1098번째 줄 CS 분기, 1142-1147번째 줄 창고 분기 — `bulk_create`가 아님)
  - 순효과: SKU당 약 8~15개의 개별 DB 쿼리 × 약 400개 SKU ≈ 3,000~6,000회의 순차적 AWS RDS MySQL 왕복이 단일 HTTP 요청/트랜잭션 내에서 발생 — 이것이 약 24분 실행 시간의 전체 원인이며 전형적인 N+1 쿼리 패턴이다.
- 진단 중 관찰된 2차 위험: SKU 순회 루프 전체가 `select_for_update()` 호출을 포함한 단일 `transaction.atomic()` 블록(1010번째 줄) 내에서 실행되므로, 약 24분 동안 `LineItem` 행 락이 유지된다. 같은 `LineItem` 행을 건드리는 다른 동시 요청(예: 다른 관리자의 작업, 재시도된 업로드)은 이 락에 막혀 MySQL의 `innodb_lock_wait_timeout`(기본 50초)을 초과할 수 있으며, 실제로 반복 진단 과정에서 `(1205, 'Lock wait timeout exceeded; try restarting transaction')` 오류가 직접 관찰되었다. 이 락 지속시간 위험은 쿼리 배칭으로 트랜잭션 실행 시간을 단축하는 것으로 자연스럽게 함께 해소되어야 한다.
- SPEC-PURCHASE-ORDER-008에는 업로드 규모/성능을 다루는 인수 조건이 전혀 없었다 — 테스트 픽스처가 57행 이하 소형 파일만 사용했기 때문에, 이 N+1 패턴은 그 SPEC의 TDD 사이클이나 evaluator-active 검토 중 한 번도 실측 규모로 노출되지 않았다. 이 SPEC-009는 그 공백을 메우기 위해 존재한다.

---

## 솔루션 개요

`UploadDailyReviewView.post()`의 SKU 순회 루프를 쿼리 배칭으로 리팩터링하여 N+1 패턴을 제거한다. SPEC-PURCHASE-ORDER-005/006/007/008이 정의한 모든 관찰 가능한 동작(응답 값, 생성/갱신되는 레코드, `선택` 값 처리 분기)은 완전히 동일하게 유지하며, 오직 DB에 그 결과를 "어떻게" 쓰는지(순차 개별 쿼리 → 배칭된 쿼리)만 변경하는 순수 성능 리팩터링이다.

- **벤더 테이블 upsert 배칭**: SKU별 개별 `update_or_create()` 호출을 Django 4.1+의 `Model.objects.bulk_create(objs, update_conflicts=True, unique_fields=["sku"], update_fields=[...])`(MySQL에서 단일 `INSERT ... ON DUPLICATE KEY UPDATE`로 컴파일됨)로 대체한다. `bulk_create(update_conflicts=True)`는 배치 내 모든 객체가 동일한 `update_fields` 집합을 가져야 하므로, SPEC-008 Bug-1-fix(행마다 실제 존재하는 컬럼만 upsert defaults에 포함)를 보존하기 위해 행을 필드 집합(사실상 레거시 형식/신 템플릿 형식 2가지)별로 그룹화한 뒤 그룹당 1회씩 배치 upsert를 수행한다.
- **LineItem 조회 배칭**: SKU별 개별 필터 쿼리를 업로드 전체 SKU에 대한 단일 `filter(sku__in=all_skus, ...)` 쿼리로 대체하고, 결과를 SKU별로 Python에서 그룹화한다.
- **LineItemNote 생성 배칭**: CS/창고 분기의 개별 `create()` 호출을 전체 SKU에 걸쳐 수집한 뒤 단일 `bulk_create()`로 대체한다.
- **WarehouseStock/PurchaseOrder**: 정확성(특히 행별 현재 수량에 의존하는 floor-at-0 계산, M2M `line_items` 연결)을 먼저 검증한 뒤, 안전하게 배칭 가능한 경우에만 배칭을 적용한다.
- 위 배칭의 자연스러운 결과로 `transaction.atomic()` 블록의 실행 시간이 초 단위로 단축되어 락 지속시간 위험도 함께 해소된다.
- 신규 회귀 가드: 300~500행 합성 픽스처로 총 쿼리 수 상한을 검증하는 테스트를 추가하여, 이 N+1 패턴이 향후 재발하지 않도록 방지한다.

---

## 범위

### 포함

- `backend/order/purchase_order_views.py`: `UploadDailyReviewView.post()`의 SKU 순회 루프 — 벤더 테이블(`BooxenData`/`KyoboData`/`Yes24Data`) 배치 upsert, `LineItem` 배치 조회, `LineItemNote` 배치 생성, `WarehouseStock`/`PurchaseOrder` 배칭 검토·적용
- `backend/order/tests/test_daily_review_upload.py`: 300~500행 합성 픽스처 기반 쿼리 수 상한 회귀 테스트 추가, 배칭 후에도 기존 동작이 동일함을 검증하는 보강 테스트(필요 시) 추가

### 제외

- `backend/order/excel_utils.py`의 `parse_daily_review_excel()` 변경 — 파싱 자체는 병목으로 측정되지 않았다(openpyxl로 450행을 파싱하는 것은 빠르며, 24분은 전적으로 뷰의 DB 쓰기 루프에 기인한다)
- SPEC-005/006/007/008이 정의한 업무 로직, 필드 매핑, `선택` 값 처리 분기 변경 — 이 SPEC은 오직 쓰기 방식(배칭 여부)만 바꾸며 무엇을 쓰는지는 절대 바꾸지 않는다
- 인프라 변경(RDS 인스턴스 사이징, 커넥션 풀링 설정 등) — 이 SPEC은 순수 애플리케이션 코드 쿼리 패턴 수정이다

---

## 요구사항

### 벤더 테이블 upsert 배칭

### REQ-PO9-001 — `BooxenData`/`KyoboData`/`Yes24Data` 배치 upsert

When `UploadDailyReviewView.post()`가 업로드된 전체 행의 벤더 테이블 upsert를 수행할 때, the system shall SKU마다 개별 `update_or_create()`를 호출하는 대신 `BooxenData`/`KyoboData`/`Yes24Data` 각 테이블에 대해 `Model.objects.bulk_create(objs, update_conflicts=True, update_fields=[...])`를 사용해 배치 upsert해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py` (`UploadDailyReviewView.post()`, 현재 1028-1068번째 줄 — SKU 순회 루프 내 3개 `update_or_create()` 호출)
- 목표: 약 400개 SKU × 3개 테이블 × 2쿼리(≈2400쿼리)를 테이블당 소수의 쿼리(그룹 수에 비례, SKU 수와 무관)로 축소
- **구현 시 주의(픽스 사이클 1에서 확인)**: `unique_fields=["sku"]`는 `bulk_create()`에 전달하면 안 된다. 이 프로젝트의 DB 백엔드는 MySQL이며, MySQL의 네이티브 `INSERT ... ON DUPLICATE KEY UPDATE`는 충돌하는 유니크 제약을 별도 지정 없이 자동으로 대상으로 삼는다. Django의 MySQL 백엔드는 `supports_update_conflicts_with_target = False`를 보고하므로, 여기에 `unique_fields`를 전달하면 런타임에 `NotSupportedError`가 발생한다. 실제 구현(`_batch_upsert_vendor_data()`, `backend/order/purchase_order_views.py`)은 `unique_fields`를 생략하여 이 문제를 회피했다.

---

### REQ-PO9-002 — 필드 집합별 그룹화로 Bug-1-fix(레거시 필드 보존) 유지

While 업로드된 행들의 실제 존재 소스 컬럼 구성이 서로 다른 동안(레거시 형식 vs 신 템플릿 형식), the system shall `bulk_create(update_conflicts=True, ...)` 호출 전에 각 행을 자신의 실제 존재 필드 집합에 따라 그룹화하고, 그룹별로 별도의 `update_fields`를 지정한 배치 upsert를 각각 수행해야 한다.

- `bulk_create(update_conflicts=True)`는 한 번의 호출에 속한 모든 객체가 동일한 `update_fields` 집합을 가져야 하므로(Django 제약), 서로 다른 필드 집합을 가진 행을 하나의 배치에 섞어 넣을 수 없다
- 실무상 필드 집합 그룹은 소수(레거시 형식 — 벤더 컬럼 없음, 신 템플릿 형식 — 벤더 컬럼 모두 존재)이므로 행 단위가 아닌 그룹 단위 배치가 되어야 한다
- 이 그룹화는 SPEC-PURCHASE-ORDER-008의 Bug-1-fix(값이 실제로 파싱된 필드만 upsert defaults에 포함하여, 레거시 형식 업로드가 존재하지 않는 신 템플릿 컬럼 값으로 기존 벤더 데이터를 None/False로 덮어쓰지 않는 보장)를 정확히 재현해야 한다

---

### REQ-PO9-003 — 레거시 벤더 데이터 무손실 회귀 테스트 무변경 통과 (Unwanted Behavior)

If REQ-PO9-001/002의 벤더 upsert 배칭이 적용되면, then the system shall NOT `test_daily_review_upload.py`의 `TestUploadLegacyFormatPreservesVendorData.test_legacy_upload_does_not_wipe_existing_booxen_and_kyobo_data`(SPEC-PURCHASE-ORDER-008 Bug-1 회귀 테스트)를 수정해야 하며, 이 테스트는 코드 변경 없이 그대로 통과해야 한다.

---

### LineItem 조회 및 LineItemNote 생성 배칭

### REQ-PO9-004 — `LineItem` 조회를 SKU 전체 단일 쿼리로 배칭

When `UploadDailyReviewView.post()`가 업로드된 SKU들에 대응하는 미발주 `LineItem`을 조회할 때, the system shall SKU마다 개별 `LineItem.objects.filter(sku=sku, ...)` 쿼리를 실행하는 대신, 업로드된 전체 SKU 목록에 대해 `LineItem.objects.filter(sku__in=all_skus, purchase_status="unordered").exclude(purchase_orders__isnull=False).select_for_update()`를 단 1회 실행하고, 그 결과를 SKU별로 Python에서 그룹화(예: `sku`로 정렬 후 `itertools.groupby`, 또는 `collections.defaultdict(list)`)하여 이후 로직에서 SKU별 그룹을 사용해야 한다.

- 대상 파일: `backend/order/purchase_order_views.py` (`UploadDailyReviewView.post()`, 현재 1070-1074번째 줄)
- 그룹화 이후 각 SKU에 대한 다운스트림 처리(CS 분기/창고 분기/비창고 PO 생성 분기)는 기존과 동일한 방식으로 해당 SKU 그룹의 `LineItem` 목록을 사용해야 한다

---

### REQ-PO9-005 — `LineItemNote` 배치 생성

When CS 분기(`note_type` 존재, 현재 1090-1098번째 줄) 또는 창고 분기(현재 1141-1147번째 줄)에서 `LineItemNote`를 생성할 때, the system shall 개별 `LineItemNote.objects.create()` 호출 대신, 업로드 전체 SKU에 걸쳐 생성할 `LineItemNote` 객체를 리스트로 수집한 뒤 트랜잭션 내에서 단일 `LineItemNote.objects.bulk_create([...])` 호출로 일괄 삽입해야 한다.

- CS 분기와 창고 분기 모두에서 생성되는 노트를 동일한 수집 리스트에 모아 최종적으로 한 번(또는 분기별로 각 한 번)의 `bulk_create()`로 삽입해도 무방하다
- `content`/`assignee`/`note_type`/`line_item` 등 개별 필드 값은 기존 개별 `create()` 호출과 완전히 동일해야 한다(REQ-PO9-011 참조)

---

### WarehouseStock 및 PurchaseOrder 배칭 검토

### REQ-PO9-006 — `WarehouseStock` 갱신 방식 검증 후 조건부 최적화

When 창고 분기의 `WarehouseStock` 재고 차감 로직(현재 1124-1130번째 줄, SKU/location별 `filter(...).update(...)` + floor-at-0 `Case/When`)을 최적화할 때, the system shall 이 계산이 각 `WarehouseStock` 행 자신의 현재 수량에만 의존하는지(행 간 독립적인지) 먼저 검증해야 한다.

Where 검증 결과 각 행이 자신의 수량만 참조함이 확인되는 경우, the system shall 업로드에 포함된 창고 분기 대상 SKU 전체를 아우르는 단일 `bulk_update()` 또는 단일 `Case/When` 쿼리로 통합해야 한다.

Where 통합이 정확성을 해칠 위험이 있다고 판단되는 경우(예: 동일 SKU/location 조합이 한 업로드 내에서 중복 처리될 가능성), the system shall 기존 SKU별 개별 `update()` 방식을 유지해도 무방하며, 그 판단 근거를 커밋 메시지 또는 구현 기록에 남겨야 한다.

---

### REQ-PO9-007 — `PurchaseOrder` 생성 배치화 검토 (낮은 우선순위)

Where 비창고 분기의 `PurchaseOrder` 생성(현재 1175-1182번째 줄)을 `bulk_create()`로 배치화하는 것이 M2M(`line_items`) 연결 처리와 충돌 없이 가능한 경우, the system shall `PurchaseOrder.objects.bulk_create()`와 through 모델을 이용한 M2M 배치 삽입으로 SKU별 개별 `create()` + `po.line_items.add()` 호출을 대체해야 한다.

Where 이 배치화가 M2M 관계 처리를 과도하게 복잡하게 만들거나 위험을 수반하는 경우, the system shall 기존 SKU별 `PurchaseOrder.objects.create()` + `po.line_items.add(*unordered_lis)` 방식을 유지해도 무방하다(REQ-PO9-001~005가 전체 쿼리 수 절감의 핵심이므로 이 항목은 상대적으로 낮은 우선순위로 취급한다).

**구현 기록(픽스 사이클 2)**: 픽스 사이클 1 이후 실제 프로덕션 파일 재측정 결과, 이 항목이 "낮은 우선순위"로 보류했던 비창고 PO 생성 분기가 실제로는 전체 행의 약 98%(447행 중 439행)를 차지하는 지배적 경로임이 확인되어(REQ-PO9-009 구현 기록 참조), 배치화를 완료했다.

- **PK 조회 방식 실증(우선 확인 필요)**: 이 프로젝트의 실제 MySQL 백엔드(Django 5.1.6)에서 `PurchaseOrder.objects.bulk_create(objs)` 호출 후 다중 객체 배치에 대해 `.pk`가 채워지는지 직접 검증(트랜잭션 롤백 처리한 일회성 테스트)한 결과, **`.pk`는 채워지지 않았다**(전부 `None`). Django의 MySQL 백엔드가 `can_return_rows_from_bulk_insert`를 지원하지 않기 때문이다.
- **채택한 폴백 전략**: ID 매칭 휴리스틱 대신, `bulk_create()` 직전 시각(`t_before`)을 기록한 뒤 `PurchaseOrder.objects.filter(sku__in=이번 배치 SKU 목록, created_at__gte=t_before)`로 재조회하여 SKU별로 매칭한다. `sku_map`이 이미 SKU 기준으로 행을 중복 제거하므로(이 SPEC 상단 로직, `post()` 최상단) 한 번의 업로드 호출에서 이 분기가 SKU당 최대 1개의 `PurchaseOrder`만 생성한다는 불변식이 성립하며(코드 검토로 확인), 이로써 이 재조회가 SKU당 정확히 1행을 반환하는 것이 사실상 보장된다. 동일 SKU가 이 좁은 시간창에서 2개 이상 매칭되는 극히 드문 동시성 경쟁 상황에서는 가장 최근에 삽입된(최대 pk) 행을 선택한다.
- M2M `line_items` 연결은 `PurchaseOrder.line_items.through.objects.bulk_create()`로 through 테이블에 직접 배치 삽입하여, SKU별 `.add()` 호출을 제거했다.
- 대상 파일: `backend/order/purchase_order_views.py` (`UploadDailyReviewView.post()`, REQ-PO9-007 관련 주석 참조).

---

### 성능 목표 및 락 지속시간

### REQ-PO9-008 — 트랜잭션 락 지속 시간 단축 (별도 락 전략 변경 없이 달성)

While `UploadDailyReviewView.post()`의 SKU 순회 루프가 `transaction.atomic()` 블록(현재 1010번째 줄) 내에서 `select_for_update()`로 `LineItem` 행 락을 보유하는 동안, the system shall REQ-PO9-001~005의 쿼리 배칭 결과로 해당 트랜잭션의 전체 실행 시간이 분 단위에서 초 단위로 단축되어야 하며, 이는 별도의 잠금 전략(락 범위 축소, 낙관적 락 전환 등) 변경 없이 쿼리 수 감소만으로 달성되어야 한다.

---

### REQ-PO9-009 — 대용량 실사용 파일 처리 시간 목표 (Ubiquitous)

The system shall 약 400~450개 SKU 규모의 실사용 Daily Review 파일 업로드를, 진단 단계에서 측정된 기존 처리 시간(약 1447초/24분) 대비 현저히 짧은 시간(목표: 초 단위) 내에 처리해야 한다.

**구현 기록(픽스 사이클 2, 실측 근거)**: REQ-PO9-001~006(픽스 사이클 1)만 적용된 시점에서는 실제 프로덕션 파일(447행, 400 유니크 SKU, 그중 439행(≈98%)이 비창고 PO 생성 분기) 재측정 결과 120초/795쿼리로, 여전히 목표(초 단위)에 못 미쳤다 — 원인은 REQ-PO9-007이 낮은 우선순위로 보류했던 `PurchaseOrder` 생성 분기가 실제로는 지배적 경로였기 때문이다. 픽스 사이클 2에서 REQ-PO9-007의 `PurchaseOrder` 배치 생성(`bulk_create()` + through 테이블 `bulk_create()`)을 완료한 뒤 동일 실제 파일로 재측정한 결과 **3.50초/14쿼리**(`django.test.RequestFactory` + `force_authenticate` + `transaction.atomic()`/`transaction.set_rollback(True)`로 측정, 영구 쓰기 없음)로 목표를 달성했다. "초 단위" 표현은 이 실측치로 근거가 확인되었으므로 그대로 유지한다.

---

### 성능 회귀 가드

### REQ-PO9-010 — 쿼리 수 상한 회귀 테스트 (신규)

The system shall `backend/order/tests/test_daily_review_upload.py`에 300~500행 규모의 합성 Daily Review 업로드 픽스처(기존 `_make_new_template_excel()` 헬퍼 재사용 또는 이에 준하는 대량 행 생성 헬퍼)를 사용하여, `django.test.utils.CaptureQueriesContext`(또는 이와 동등한 쿼리 카운트 검증 메커니즘)로 `UploadDailyReviewView.post()` 처리 중 실행된 Django 쿼리 수를 측정하고, 그 수가 업로드된 SKU 수와 무관하게 고정된 작은 상한(가이드라인: 30개 미만) 이하임을 검증하는 신규 테스트를 추가해야 한다.

- 이 테스트는 이번 리팩터링이 놓친 경우를 포함해 향후 이 뷰에 다시 N+1 패턴이 도입되는 것을 방지하는 회귀 가드다 — SPEC-PURCHASE-ORDER-008이 갖추지 못했던 바로 그 공백을 메운다
- 쿼리 수는 SKU 수(300 vs 500)에 따라 유의미하게 증가해서는 안 되며(선형 증가 시 실패), 그룹 수·분기 종류 등 상수 요인에만 비례해야 한다

---

### 기존 동작 무변경 보장 (Unwanted Behavior)

### REQ-PO9-011 — 관찰 가능한 응답·레코드 값 무변경 (핵심 제약)

If 이 SPEC-009의 쿼리 배칭 리팩터링이 적용되면, then the system shall NOT `UploadDailyReviewView`가 반환하는 응답 값(`confirmed_count`, `skipped_count`, `errors`, `confirmed_by_distributor`), 생성·갱신되는 `PurchaseOrder`/`LineItem`/`LineItemNote`/`WarehouseStock`/`BooxenData`/`KyoboData`/`Yes24Data` 레코드의 필드 값, 또는 `선택` 값 처리·CS 분기·창고 분기·YES24 발주 확정 분기의 판별 로직을 SPEC-PURCHASE-ORDER-005/006/007/008이 정의한 기존 동작과 다르게 변경해야 한다.

---

### REQ-PO9-012 — 기존 회귀 테스트 스위트 73건 무변경 통과 (핵심 하위 호환성 게이트)

If 이 SPEC-009의 구현이 완료되면, then the system shall NOT `backend/order/tests/test_daily_review_upload.py`에 정의된 기존 73개 테스트 케이스(SPEC-PURCHASE-ORDER-005/006/007/008 관련 케이스 포함)의 테스트 코드나 통과 여부를 변경해야 한다. REQ-PO9-010의 신규 성능 테스트는 이 파일에 추가되지만, 기존 73개 테스트는 단 한 줄도 수정되지 않은 채 그대로 통과해야 한다.

---

### REQ-PO9-013 — `excel_utils.py` 파싱 로직 무변경 (Unwanted Behavior)

If 이 SPEC-009가 구현되면, then the system shall NOT `backend/order/excel_utils.py`의 `parse_daily_review_excel()` 또는 그 밖의 파싱 관련 함수를 수정해야 한다 — 이 SPEC은 오직 `UploadDailyReviewView.post()`의 DB 쓰기 패턴만을 대상으로 한다.

---

## 구현 범위 (수정·생성 대상 파일)

| 파일 | 변경 유형 | 변경 내용 요약 |
|------|-----------|----------------|
| `backend/order/purchase_order_views.py` | 수정 | `UploadDailyReviewView.post()` SKU 순회 루프 리팩터링 — 벤더 테이블(`BooxenData`/`KyoboData`/`Yes24Data`) 필드 집합별 그룹 배치 upsert, `LineItem` 단일 `filter(sku__in=...)` 조회 후 SKU별 그룹화, `LineItemNote` `bulk_create()`, `WarehouseStock`/`PurchaseOrder` 배칭 검증 후 조건부 적용 |
| `backend/order/tests/test_daily_review_upload.py` | 수정 | 300~500행 합성 픽스처 기반 쿼리 수 상한 회귀 테스트(REQ-PO9-010) 추가; 기존 73개 테스트는 무변경 유지 |

---

## 제외 범위 (What NOT to Build)

- `backend/order/excel_utils.py`의 `parse_daily_review_excel()` 변경 — 파싱은 병목이 아니며(openpyxl로 450행 파싱은 빠름), 24분은 전적으로 뷰의 DB 쓰기 루프에서 발생한다
- SPEC-005/006/007/008이 정의한 업무 로직·필드 매핑·`선택` 값 처리 분기 변경 — 이 SPEC은 오직 배칭 여부(HOW)만 바꾸고 무엇을 쓰는지(WHAT)는 절대 바꾸지 않는다
- 인프라 변경(RDS 인스턴스 사이징, 커넥션 풀링 설정, MySQL `innodb_lock_wait_timeout` 값 조정 등) — 순수 애플리케이션 코드 쿼리 패턴 수정만 다룬다
- 별도의 잠금 전략 변경(낙관적 락 전환, 락 범위 축소를 위한 트랜잭션 분할 등) — REQ-PO9-008에 따라 락 지속시간 단축은 쿼리 배칭의 자연스러운 결과로만 달성한다

---

## 인수 조건

### AC-001 — 쿼리 수 상한 회귀 테스트 통과 (핵심 신규 게이트)

**Given** 300~500행 규모의 합성 Daily Review 업로드 픽스처(다양한 `선택` 값·벤더 컬럼 조합, 레거시/신 템플릿 혼합 가능)가 준비되어 있을 때
**When** `UploadDailyReviewView.post()` 호출을 `CaptureQueriesContext`로 감싸 실행하면
**Then** 실행된 총 Django 쿼리 수가 업로드된 SKU 수(300개 vs 500개)와 무관하게 고정된 작은 상한(30개 미만) 이하이어야 한다

---

### AC-002 — 레거시 형식 업로드 시 기존 벤더 데이터 보존 (Bug-1-fix, 배칭 후에도 무손실)

**Given** SKU `X`에 대해 기존 `BooxenData(sku=X, stock=50, status="정상", ...)`/`KyoboData(sku=X, status="정상", publisher="테스트출판사", ...)`가 존재하고, 신 템플릿 전용 컬럼(`BOOXEN 재고수량` 등)이 헤더에 전혀 없는 레거시 형식 파일을 업로드할 때
**When** 필드 집합별로 그룹화된 배치 upsert(REQ-PO9-001/002)가 실행되면
**Then** 기존 `BooxenData(sku=X)`/`KyoboData(sku=X)`의 필드 값이 None/False로 덮어써지지 않고 그대로 유지되어야 한다(`test_legacy_upload_does_not_wipe_existing_booxen_and_kyobo_data`가 코드 변경 없이 통과)

---

### AC-003 — LineItem 배치 조회 후 SKU별 그룹화 정확성

**Given** 서로 다른 SKU를 가진 다수의 미발주 `LineItem`이 존재하는 업로드 파일일 때
**When** 배치화된 `LineItem.objects.filter(sku__in=all_skus, ...)` 단일 쿼리 실행 후 SKU별로 그룹화되면
**Then** 그룹화 결과가 기존 SKU별 개별 쿼리 방식과 동일한 `LineItem` 집합을 SKU별로 반환해야 한다(레코드 누락·중복 없음)

---

### AC-004 — LineItemNote 배치 생성 결과가 개별 create()와 동일

**Given** CS 분기와 창고 분기에 걸쳐 여러 SKU의 `LineItemNote`가 생성되어야 하는 업로드 파일일 때
**When** `LineItemNote.objects.bulk_create()`로 일괄 삽입되면
**Then** 생성된 `LineItemNote` 레코드 수와 각 레코드의 `content`/`assignee`/`note_type`/`line_item` 값이 기존 개별 `create()` 방식과 완전히 동일해야 한다

---

### AC-005 — 트랜잭션 락 지속 시간 단축 검증

**Given** 300~500행 규모의 합성 업로드 파일일 때
**When** 리팩터링된 `UploadDailyReviewView.post()`를 실행하면
**Then** `transaction.atomic()` 블록의 전체 실행 시간이 초 단위(테스트 환경 기준 수 초~수십 초 이내)로 완료되어야 하며, 진단 단계에서 측정된 기존 처리 시간(1447초) 대비 현저히 짧아야 한다

**실사용 파일 실측 근거(픽스 사이클 2)**: 실제 프로덕션 파일(447행, 400 유니크 SKU, PO 생성 분기 439행)로 재측정한 결과 3.50초/14쿼리로 완료됨(1447초 대비 약 413배, 픽스 사이클 1의 120초/795쿼리 대비 약 34배 개선) — REQ-PO9-009 구현 기록 참조.

---

### AC-006 — WarehouseStock 갱신 정확성 유지 (배칭 여부와 무관)

**Given** 동일 `location`에 서로 다른 현재 수량을 가진 다수의 `WarehouseStock` 행이 창고 분기 대상 SKU로 존재할 때
**When** REQ-PO9-006에 따라 최적화되었거나(또는 검증 후 기존 방식이 유지된) `WarehouseStock` 갱신 로직이 실행되면
**Then** 각 행의 차감 결과가 자기 자신의 원래 수량 기준 floor-at-0 계산과 정확히 일치해야 한다(다른 행의 수량에 영향받지 않음)

---

### AC-007 — 기존 SPEC-005/006/007/008 회귀 테스트 스위트 73건 전체 무변경 통과 (핵심 하위 호환성 게이트)

**Given** 이 SPEC-009의 구현이 완료된 상태일 때
**When** `backend/order/tests/test_daily_review_upload.py`의 기존 73개 테스트 케이스(SPEC-PURCHASE-ORDER-005/006/007/008 관련 케이스 포함)를 실행하면
**Then** 모든 기존 테스트가 코드 수정 없이 그대로 통과해야 하며, 이 SPEC의 쿼리 배칭 리팩터링으로 인한 어떠한 회귀도 없어야 한다

---

### AC-008 — PurchaseOrder 생성 방식과 무관하게 M2M 연결 정확성 유지

**Given** 비창고 분기에서 여러 SKU에 대해 `PurchaseOrder`가 생성되어야 하는 업로드 파일일 때
**When** (REQ-PO9-007에 따라 배치화되었거나 기존 방식이 유지된) `PurchaseOrder` 생성 로직이 실행되면
**Then** 각 `PurchaseOrder`의 `line_items` M2M 관계가 해당 SKU에 속한 정확한 `LineItem` 집합과 일치해야 한다

---

## 관련 SPEC

- SPEC-PURCHASE-ORDER-005: 창고재고 차감 로직(`_WAREHOUSE_LOCATION_MAP`, `WarehouseStock` 차감 쿼리, `confirmed_by_distributor` 응답)의 기반이 되는 SPEC. 이 SPEC-009는 그 로직의 관찰 가능한 결과는 그대로 유지한 채 쿼리 실행 방식만 최적화한다.
- SPEC-PURCHASE-ORDER-006: `Yes24Data` 모델, `list_price` 필드를 도입한 SPEC. 이 SPEC-009의 배칭도 `Yes24Data.list_price`를 defaults에서 계속 제외해야 한다(SPEC-006 보호, 기존 REQ-PO8-018 제약 승계).
- SPEC-PURCHASE-ORDER-007: YES24 발주 파일 생성 SPEC. 이 SPEC-009와 직접적인 코드 경로 중복은 없다.
- SPEC-PURCHASE-ORDER-008: 이 SPEC-009의 직접적인 트리거가 된 선행 SPEC — Part B(전체 행 벤더 데이터 upsert, REQ-PO8-014~018)를 도입했으며, 소규모 픽스처(≤57행)로만 검증되어 실사용 규모(≈400행)에서의 N+1 성능 문제가 노출되지 않았다. SPEC-009는 SPEC-008이 도입한 로직의 "무엇을 쓰는가"는 전혀 바꾸지 않고 "어떻게 쓰는가"만 배칭으로 전환한다.
