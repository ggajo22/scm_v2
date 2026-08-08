# SPEC-ORDER-012 구현 계획

## 기술 접근

브라운필드 변경. 기존 `order` 앱(`backend/order/`)의 모델·뷰·동기화 로직을 확장한다. 새 앱/모듈은
만들지 않는다. 아래 [NEW]/[MODIFY] 마커는 CLAUDE.md 브라운필드 규칙에 따른 표기다. 개발 방법론은
`quality.yaml`의 `development_mode: tdd`(RED-GREEN-REFACTOR) — 기존 write path에 recompute 호출을
추가하는 브라운필드 변경이므로 RED 이전에 각 write path의 현재 동작을 이해하는 사전 단계를 거친다
(workflow-modes.md "Brownfield Enhancement" 절 참조).

## 마일스톤 (우선순위 기반, 시간 추정 없음)

### M1 — 데이터 모델 (Priority: High)

- [MODIFY] `backend/order/models.py`
  - `Order`에 `ready_to_ship` 필드 추가: `models.BooleanField(null=True, blank=True)` — `status`
    필드(48-53행)와 동일하게 명시적 `default` 없이 null 허용, 3상태(REQ-RTS-001).
  - 필드 선언 옆에 `status`(42-47행 주석 패턴을 미러링)와 마찬가지로, 계산 전용 필드이며
    Shopify 동기화 대상이 아님(REQ-RTS-005)을 설명하는 주석 추가.
- [NEW] 마이그레이션(다음 번호부터 순차 부여, 계획 시점 기준 `0032`부터 — **Run 단계 착수 직전
  최신 마이그레이션 상태 재검증 필수**, SPEC-ORDER-011/SPEC-PURCHASE-ORDER-010 모두 계획 시점
  번호가 실제 구현 시점에 밀린 선례 있음):
  - `0032_order_ready_to_ship.py` — `AddField`, `0030_lineitem_logistics_status_alter_order_status.py`
    스타일 준수(단일 AddField, choices 없음).
  - `0033_backfill_order_ready_to_ship.py` — `RunPython`, `0031_backfill_order_status.py` 관례
    (historical model, `noop` reverse, 상단 주석으로 알고리즘 설명) 준수. REQ-RTS-006.
    알고리즘은 `research.md` 5절의 의사코드를 historical model(`apps.get_model`) 위에서
    재구현 — 뷰 코드(`_recompute_order_aggregates`)를 import하지 않는다(0031과 동일 사유:
    마이그레이션은 향후 리팩터링될 수 있는 뷰 코드에 의존하면 안 됨).

### M2 — 재계산 헬퍼 함수 확장 및 리네임 (Priority: High)

참조 구현: `backend/order/purchase_order_views.py:117-158`(`_recompute_order_status`, 리네임 대상).

- [MODIFY] `backend/order/purchase_order_views.py`
  - 함수명 `_recompute_order_status` → `_recompute_order_aggregates`(전체 파일 내 모든 참조 포함).
  - SELECT의 `values_list("order_id", "logistics_status")`에 `"purchase_status"` 컬럼 추가.
  - `Order.objects.filter(...).update(...)` 호출에 `ready_to_ship=Case(*ready_when, ...)` 절 추가
    (기존 `status=Case(...)` 절과 나란히, 같은 `.update()` 호출 — 추가 쿼리 없음, REQ-RTS-004a).
  - `ready_to_ship` 계산 로직은 `research.md` 5절 의사코드를 그대로 구현(REQ-RTS-002).
  - 함수 docstring 및 위 `@MX:NOTE` 주석(110-116행)을 갱신 — fan-in이 4→8로 늘어남을 반영.
  - 이 함수를 호출하는 기존 4곳(1697/1764/1909/1967행)의 호출 이름을
    `_recompute_order_aggregates`로 일괄 교체(동작 변경 없음, REQ-RTS-003).

### M3 — 신규 4개 write path에 재계산 연결 (Priority: High)

참조 구현(정확한 현재 라인은 `research.md` 3.2절 표 참조):

- [MODIFY] `ConfirmOrderView.post()`(804행): `for item in items:` 루프 전체에서 각 SKU의
  `unordered_lis`의 `order_id`를 누적하는 `set`을 루프 시작 전에 초기화, 루프 종료 후(여전히
  837행 `transaction.atomic()` 블록 안에서) `_recompute_order_aggregates(affected_order_ids)`
  1회 호출. 요청당 SKU 개수와 무관하게 O(1) 추가 쿼리쌍(REQ-RTS-003a/004/004a).
- [MODIFY] `LineItemStatusUpdateView.patch()`(1787행): `LineItemLogisticsStatusUpdateView`(1876행)와
  동일한 패턴 — `save()` 직후 `_recompute_order_aggregates([li.order_id])` 추가.
- [MODIFY] `LineItemBulkStatusUpdateView.patch()`(1828행): `LineItemLogisticsStatusBulkUpdateView`
  (1920행)와 동일한 패턴 — `.update()` **호출 전**에
  `affected_order_ids = list(existing.values_list("order_id", flat=True).distinct())`로 캡처,
  `.update()` 후 `_recompute_order_aggregates(affected_order_ids)` 호출(`.update()`는 영향받은
  인스턴스를 반환하지 않으므로 순서가 중요).
- [MODIFY] `UploadDailyReviewView.post()`(1178행): 기존 `cs_status_updates` / `warehouse_li_updates`
  / `nonwarehouse_li_updates` 세 리스트(1368-1370행에 선언, 이미 메모리에 로드된 LineItem 인스턴스)에서
  `order_id`를 합쳐(`{li.order_id for li in cs_status_updates + warehouse_li_updates +
  nonwarehouse_li_updates}`) 세 분기의 `bulk_update()` 호출(1551-1564행)이 모두 끝난 뒤,
  1244행 `transaction.atomic()` 블록이 끝나기 전에 `_recompute_order_aggregates(affected_order_ids)`
  1회 호출. 업로드 내 SKU 개수와 무관하게 O(1) 추가 쿼리쌍.

### M4 — Shopify 동기화 제외 문서화 (Priority: Medium)

- [MODIFY] `backend/order/shopify_orders.py`: `_sync_single_order()`의 `Order.objects.
  update_or_create()` defaults 딕셔너리 근처 138-141행 기존 주석 블록("SPEC-ORDER-011 REQ-LOGI-011:
  status intentionally excluded...")에 `ready_to_ship`도 함께 제외 대상임을 명시하는 한 줄 추가.
  기능 코드 변경 없음(신규 필드는 애초에 defaults 딕셔너리에 없으므로 이미 제외된 상태) — 순수
  문서화 + 회귀 테스트(REQ-RTS-005).

### M5 — API 노출 및 프론트엔드 (Priority: Medium)

- [MODIFY] `backend/order/serializers.py`: `OrderDetailSerializer.Meta.fields`(148-163행)에
  `"status"`(162행) 옆에 `"ready_to_ship"` 추가. `OrderListSerializer`는 변경하지 않음(뱃지는
  상세 화면 전용, REQ-RTS-007 범위).
- [MODIFY] `frontend/src/types/order.ts`: `OrderDetail` 인터페이스에 `status: string | null`(200행)
  옆에 `ready_to_ship: boolean | null` 추가.
- [MODIFY] `frontend/src/pages/OrderDetailPage.tsx`: 기존 두 뱃지(파란색 `fulfillment_status`
  219-227행, 보라색 `Order.status` 231-239행) 옆에 세 번째 뱃지 추가 — 헤더 텍스트("출고가능" 등,
  기존 두 헤더와 단어 겹침 없음), 배경색 구분(예: 초록/에메랄드 계열),
  `{data.ready_to_ship && (...)}` 패턴으로 null/False 모두 미노출(REQ-RTS-007/008).

## 리스크

- **마이그레이션 번호 충돌**: 계획 시점(`0032`/`0033`) 이후 다른 SPEC이 병렬로 구현되며 번호를
  선점할 수 있음 — Run 단계 착수 시 최신 마이그레이션 상태 재확인 필수(SPEC-ORDER-011/
  SPEC-PURCHASE-ORDER-010 모두 실제로 겪은 문제).
- **N+1 회귀**: `ConfirmOrderView`/`UploadDailyReviewView`에서 재계산 호출을 루프 안(요청당 여러 번)에
  잘못 배치하면 SPEC-PURCHASE-ORDER-009에서 해결한 것과 동일한 성능 문제가 재발할 수 있음 — M3에서
  "루프/분기 종료 후 요청당 1회" 배치를 반드시 검증(쿼리 수 상한 회귀 테스트 필수).
- **cross-SPEC 리네임 충돌**: `_recompute_order_aggregates`로의 리네임이 SPEC-ORDER-011의
  `test_spec_011.py`가 함수명을 직접 참조하는 테스트를 포함하고 있다면 함께 갱신 필요 — Run 단계
  착수 시 `grep -rn "_recompute_order_status" backend/` 로 참조 전수 확인(테스트 포함) 후 일괄 교체.
- **damaged_exchange/other_publisher 회귀 리스크**: `ConfirmOrderView`의 damaged_exchange 자동
  리셋(933-939행)과 명시적 override(942-946행)가 최종 `bulk_update`(963행) 이전에 이미 반영되므로,
  재계산 호출이 그 이후에 위치하기만 하면 최신 상태를 정확히 읽음 — 순서 실수(재계산을
  `bulk_update` 이전에 배치)를 막기 위한 테스트 필요.

## 참조 구현

- 재계산 헬퍼(리네임/확장 대상): `backend/order/purchase_order_views.py:117-158`
- 기존 4개 `logistics_status` write path: 1647/1697, 1712/1764, 1876/1909, 1920/1967행
- 신규 4개 `purchase_status` write path: `ConfirmOrderView` 804/963행,
  `LineItemStatusUpdateView` 1787/1811행, `LineItemBulkStatusUpdateView` 1828/1860행,
  `UploadDailyReviewView` 1178/1551-1564행
- 마이그레이션 선례: `0030_lineitem_logistics_status_alter_order_status.py`,
  `0031_backfill_order_status.py`
- N+1 방지 선례: SPEC-PURCHASE-ORDER-009 전체, SPEC-ORDER-011 REQ-LOGI-010
- 뱃지 UI 선례: `frontend/src/pages/OrderDetailPage.tsx:219-239`(REQ-LOGI-013 구현)
- 테스트 파일 명명: `test_spec_011.py` 선례를 따라 `backend/order/tests/test_spec_012.py` 신설 권장
  (쿼리 수 상한 회귀 테스트 포함, `CaptureQueriesContext` 선례 재사용)
