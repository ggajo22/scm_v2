# SPEC-ORDER-012 Research

Phase 1B Deep Research, produced during planning (manager-spec). DO NOT implement code from
this document — planning input only.

This research shares the same codebase audit context as `SPEC-ORDER-011`(LineItem 물류 상태 추적)과
`SPEC-PURCHASE-ORDER-010`(파손/교환 재발주 큐)의 조사 세션과 이어지는 후속 조사다. 모든 라인 번호는
2026-08-09 기준 재검증 완료.

## Feature being planned

`Order.ready_to_ship` — Order 레벨 "지금 고객에게 출고해도 되는가" 판정을 위한 신규 필드. 기존
`Order.status`(SPEC-ORDER-011, 물류 파이프라인 진행 단계 집계)와는 완전히 독립된 별도 차원이다 — 같은
Order가 동시에 `status="received"`이면서 `ready_to_ship=False`(CS 대기 아이템 존재)일 수 있다.

## 1. `_recompute_order_status()` 현재 구현 (확장 대상)

`backend/order/purchase_order_views.py:117-158`:

```python
def _recompute_order_status(order_ids) -> None:
    order_id_list = list(order_ids)
    if not order_id_list:
        return

    statuses_by_order: dict[int, set[str]] = defaultdict(set)
    for order_id, logistics_status in LineItem.objects.filter(
        order_id__in=order_id_list, sku__isnull=False
    ).values_list("order_id", "logistics_status"):
        statuses_by_order[order_id].add(logistics_status)

    status_field = CharField(max_length=50, null=True)
    whens = []
    for order_id in order_id_list:
        statuses = statuses_by_order.get(order_id)
        if not statuses:
            new_status = None
        elif len(statuses) == 1:
            new_status = next(iter(statuses))
        else:
            new_status = "partial"
        whens.append(When(id=order_id, then=Value(new_status, output_field=status_field)))

    Order.objects.filter(id__in=order_id_list).update(
        status=Case(*whens, default=Value(None, output_field=status_field), output_field=status_field)
    )
```

2-쿼리 설계(SELECT 1회 그룹핑 + `Case/When` UPDATE 1회), `sku__isnull=False`로 추적 가능 LineItem만
대상. 함수 위 `@MX:NOTE` 주석(110-116행)은 fan-in 4(업로드 2개 + PATCH 2개)를 이유로 `@MX:ANCHOR` 승격을
보류한다고 명시 — 이 SPEC이 fan-in을 4→8로 늘리므로 해당 주석도 갱신 대상.

`ready_to_ship` 계산에는 같은 LineItem 집합의 `purchase_status`가 추가로 필요할 뿐이므로,
`values_list("order_id", "logistics_status")`에 `"purchase_status"` 컬럼 하나를 추가하고 같은
`.update()` 호출에 `ready_to_ship=Case(...)` 절을 하나 더 추가하면 **쿼리 수 증가 없이(SELECT 1회 +
UPDATE 1회 그대로)** 확장 가능함을 확인했다. 별도 헬퍼로 분리하면 동일 LineItem을 재조회하게 되어
비효율적이므로 기존 함수 확장이 정답이다.

**리네이밍**: 사용자 승인 완료 — `_recompute_order_status` → `_recompute_order_aggregates`. 순수
기계적 리네임(동작 변경 없음)이지만 SPEC-ORDER-011 산출물(호출부 4곳 + docstring + `@MX:NOTE` 주석)을
건드리는 cross-SPEC 수정이다.

## 2. `_apply_logistics_transition()` — 참고용, 변경 없음

`backend/order/purchase_order_views.py:161-206`. 업로드 2개(`UploadVendorShipmentView`/
`UploadWarehouseReceiptView`)가 공유하는 헬퍼. `affected_order_ids`를 이미 로드된 LineItem
인스턴스에서 수집(추가 쿼리 0) — 이 SPEC은 이 함수를 직접 건드리지 않는다. 호출부(아래 4곳)에서
재계산 함수 이름만 바뀐다.

## 3. write path 전수 확인 (프로덕션 코드, 테스트/마이그레이션 제외)

`grep -n 'purchase_status\s*=\|purchase_status='` 전수 검사 결과, 프로덕션 코드에서 `purchase_status`를
쓰는 지점은 정확히 아래 4개 뷰/6개 대입문으로 귀결된다(그 외 매치는 전부 필터 조건문이거나 테스트/
마이그레이션 파일):

### 3.1 기존 4개 `logistics_status` write path (이미 recompute 호출 중 — 함수명만 교체)

| # | 클래스 | 클래스 라인 | recompute 호출 라인 |
|---|---|---|---|
| 1 | `UploadVendorShipmentView.post()` | 1647 | 1697 |
| 2 | `UploadWarehouseReceiptView.post()` | 1712 | 1764 |
| 3 | `LineItemLogisticsStatusUpdateView.patch()` | 1876 | 1909 |
| 4 | `LineItemLogisticsStatusBulkUpdateView.patch()` | 1920 | 1967 (order_ids 캡처는 1963, `.update()` 이전) |

### 3.2 신규 연결 대상 4개 `purchase_status` write path (recompute 호출 전무 — 신규 연결 필요)

| # | 클래스/분기 | 클래스 라인 | write 라인 | 비고 |
|---|---|---|---|---|
| 5 | `ConfirmOrderView.post()` | 804 | 963 (`bulk_update(unordered_lis, update_fields)`) | damaged_exchange 자동 리셋 933-939, 명시적 override 942-946 — 둘 다 이 bulk_update 이전에 반영됨. 여러 SKU를 하나의 `for item in items:` 루프+`transaction.atomic()`(837행) 안에서 처리 |
| 6 | `LineItemStatusUpdateView.patch()` | 1787 | 1811-1812 (`li.save(update_fields=["purchase_status"])`) | 단건, `transaction.atomic()` 래핑 없음(기존 로직 그대로) |
| 7 | `LineItemBulkStatusUpdateView.patch()` | 1828 | 1860 (`existing.update(purchase_status=...)`) | `.update()`는 영향받은 인스턴스를 반환하지 않으므로 order_ids는 호출 **이전**에 캡처해야 함(패턴 4와 동일) |
| 8 | `UploadDailyReviewView.post()` — 3개 분기 | 1178 | CS 분기 write 1551-1552, 창고/`in_stock` 분기 write 1553-1556, 비창고(PO생성) 분기 write 1557-1564 | 세 분기 모두 `transaction.atomic()`(1244행) 안에서 실행되며, 각 분기가 만든 `cs_status_updates`/`warehouse_li_updates`/`nonwarehouse_li_updates` 리스트(이미 메모리에 로드된 LineItem 인스턴스)에서 `order_id`를 합쳐 업로드당 1회만 recompute 가능(추가 쿼리 없음) |

패턴 5(`ConfirmOrderView`)와 패턴 8(`UploadDailyReviewView`)은 한 요청 안에서 여러 SKU/여러 분기를
처리하므로, recompute 호출은 **루프/각 분기 종료 후 한 번만** — 요청당 O(1) 추가 쿼리쌍이며 SKU
개수와 무관하다(N+1 재도입 없음, REQ-LOGI-010 선례 그대로 적용 가능함을 확인).

## 4. 모델 필드 현황

`backend/order/models.py`:

- `LOGISTICS_STATUS_CHOICES`(모듈 레벨, 8-14행) — `LineItem.logistics_status`와 `Order.status`가 공유.
- `Order` 클래스: 30-91행. `status` 필드: 48-53행(`CharField(max_length=50, null=True, blank=True,
  choices=LOGISTICS_STATUS_CHOICES + [("partial", "부분입고")])`, 명시적 `default` 없음 — 신규 행은
  NULL). `note_resolved` 필드(63행) — `BooleanField(default=False)`, non-null 선례(대안 검토용).
- `LineItem.PURCHASE_STATUS_CHOICES`(136-147행): `unordered/on_hold/order_cancelled/other_publisher/
  cs_required/in_stock/damaged_exchange` 7값. `purchase_status` 필드(163-167행),
  `logistics_status` 필드(177-181행).

## 5. `ready_to_ship` 계산 규칙 — 사용자 확정, 재구성

추적 가능(`sku not null`) LineItem 집합에 대해:

1. `purchase_status="order_cancelled"`인 LineItem → 판정에서 완전히 제외.
2. 제외 후 남은 LineItem이 0개 → `None`(미설정) — `Order.status`의 "추적 가능 LineItem 0개면 미설정"
   선례(REQ-LOGI-008)를 그대로 따름.
3. 남은 LineItem 중 하나 이상이 `purchase_status="cs_required"` → `False`(다른 조건 무관, hard stop).
4. 그 외 — 남은 모든 LineItem이 각각 `logistics_status="received"` **또는**
   `purchase_status="in_stock"`을 만족해야 `True`; 하나라도 불만족이면 `False`. (`other_publisher`,
   `damaged_exchange`, `unordered`, `on_hold`, `in_stock`은 모두 이 일반 규칙에 속함 — 별도 특례 불필요.)

Python 의사코드(같은 order_id 그룹 내에서 `_recompute_order_aggregates`의 기존 `status` 집계 루프와
나란히 실행 가능, 같은 SELECT 결과 재사용):

```python
non_cancelled = [it for it in items if it.purchase_status != "order_cancelled"]
if not non_cancelled:
    ready_to_ship = None
elif any(it.purchase_status == "cs_required" for it in non_cancelled):
    ready_to_ship = False
else:
    ready_to_ship = all(
        it.logistics_status == "received" or it.purchase_status == "in_stock"
        for it in non_cancelled
    )
```

## 6. 마이그레이션 관례 재확인

최신 마이그레이션: `0031_backfill_order_status.py`(2026-08-09 기준). 다음 번호는 `0032`부터 — Run
단계 착수 직전 재검증 필요(SPEC-ORDER-011/SPEC-PURCHASE-ORDER-010 모두 계획 시점 번호가 실제 구현
시점에 밀린 선례 있음).

- `0030_lineitem_logistics_status_alter_order_status.py`: `AddField`(LineItem.logistics_status,
  `default="not_shipped"`) + `AlterField`(Order.status, choices 추가만) — 단일 마이그레이션에
  두 개의 관련 스키마 변경을 묶은 선례.
- `0031_backfill_order_status.py`: `RunPython(backfill_order_status, migrations.RunPython.noop)` —
  historical model(`apps.get_model`) 사용, 2-쿼리 알고리즘을 뷰 코드와 별개로 재구현(마이그레이션은
  향후 리팩터링될 수 있는 뷰 코드를 import하면 안 됨), `reverse_code`는 `noop`(사유: 신규 필드의
  진짜 이전 값이 없어 이론상 "전부 NULL로 되돌리기"가 가능하지만, 프로젝트 일관성을 위해 기존
  `0026`/`0031`의 `noop` 관례를 유지).

`Order.ready_to_ship`도 동일하게 스키마 마이그레이션(`AddField`)과 백필(`RunPython`)을 분리한다 —
`0032_order_ready_to_ship.py` + `0033_backfill_order_ready_to_ship.py` (번호는 Run 단계에서 재검증).

## 7. Shopify 동기화 제외 — 코드 변경 불필요, 문서화만 필요

`backend/order/shopify_orders.py`:

- `_sync_single_order()`의 `Order.objects.update_or_create()` defaults 딕셔너리(126-142행 부근)에는
  이미 `"status"` 키가 없다(SPEC-ORDER-011 REQ-LOGI-011에서 제거됨, 138-141행에 그 사유를 설명하는
  주석 존재). `ready_to_ship`은 애초에 존재한 적 없는 신규 필드이므로 **아무 코드 변경 없이도
  자동으로 제외됨** — `status`처럼 "제거해야 할 기존 라인"이 없다.
- LineItem `common_defaults`(206-208행 부근)도 동일 — `purchase_status`/`logistics_status`가 이미
  제외되어 있고, 새 컬럼은 애초에 LineItem에 속하지 않으므로(Order 필드) 무관.
- **그럼에도** 138-141행의 기존 주석 블록에 `ready_to_ship`도 함께 제외 대상임을 명시하는 한 줄을
  추가해 REQ-LOGI-011 선례처럼 의도를 문서화한다(순수 주석 추가, 동작 변경 없음) — 회귀 테스트로
  뒷받침(REQ-RTS-006).

## 8. 프론트엔드 뱃지 선례

`frontend/src/pages/OrderDetailPage.tsx`: 기존 뱃지 2개 확인 —

- `fulfillment_status`(파란색, 219-227행, `data-badge-header="배송 상태"`).
- `Order.status`(보라색, 231-239행, `data-badge-header="입고출고 현황"`, `{data.status && (...)}`로
  null일 때 미노출).

`ready_to_ship` 뱃지는 세 번째 뱃지로 추가 — 헤더 텍스트("출고가능" 등)가 위 두 개와 단어 겹침 없이,
배경색도 구분(예: 초록/에메랄드 계열). **v1.4.0 갱신**: evaluator-active Phase 2.8a 검증에서 최초
구현이 `false`/`null`을 UI에서 동일하게 미노출 처리해 SPEC 문구(AC-RTS-008은 `null`만 미노출 규정)와
어긋남을 발견 — 사용자 결정으로 `false`도 독자적인 뱃지(빨강 계열, "출고불가")로 표시하도록 변경(결정 F,
spec.md 참조). `null`만 계속 미노출.

`backend/order/serializers.py`: `OrderDetailSerializer.Meta.fields`에 `"status"` 노출 지점 162행 —
`ready_to_ship`도 같은 자리에 추가. `OrderListSerializer`(목록 화면)에는 추가하지 않음 — 뱃지는
Order 상세 화면에만 필요(REQ-RTS-008 범위).

`frontend/src/types/order.ts`: `OrderDetail` 인터페이스의 `status: string | null`(200행) 옆에
`ready_to_ship: boolean | null` 타입 추가 예정.

`backend/order/views.py`: `OrderDetailView`는 `RetrieveAPIView`(GET 전용, 31행) — Order 모델에
대한 범용 쓰기 엔드포인트가 없음을 확인, `ready_to_ship`을 계산 전용 필드로 노출해도 우발적 쓰기
경로 없음(결정 E 근거).

## 9. 결론 / Run 단계 권장 사항

1. `_recompute_order_aggregates()`로 `_recompute_order_status()`를 리네임하며 `purchase_status`
   컬럼 추가 SELECT + `ready_to_ship=Case(...)` 절 추가 UPDATE로 확장 — 쿼리 수 불변.
2. 8개 write path 모두에서 이 함수를 호출(4개는 이름만 교체, 4개는 신규 연결) — N+1 방지 전략은
   3.2절의 "요청당 1회" 원칙을 각 write path에 적용.
3. 마이그레이션 2개(`AddField` + `RunPython` 백필), `noop` reverse, 번호는 Run 단계 직전 재검증.
4. `shopify_orders.py`는 주석 1줄 추가 + 회귀 테스트만 필요, 기능 코드 변경 없음.
5. 프론트엔드는 뱃지 1개 + 타입 1개 + 시리얼라이저 필드 1개 — REQ-LOGI-013 선례를 그대로 재사용.
