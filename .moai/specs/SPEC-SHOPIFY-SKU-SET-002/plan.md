# SPEC-SHOPIFY-SKU-SET-002 구현 계획 (Implementation Plan)

---

## 기술 접근 방향

### 백엔드

- **스키마**: `backend/order/models.py`의 `LineItem.Meta.unique_together` 변경 +
  `AlterUniqueTogether` 마이그레이션(`0025_*.py`)
- **싱크 파이프라인**: `backend/order/shopify_orders.py`의 `_sync_single_order()` 내
  `LineItem.objects.update_or_create()` 루프를 번들-인식형으로 재작성
- **백필**: Django 데이터 마이그레이션(`0026_*.py`, `RunPython`)으로 기존 미발주 번들 LineItem
  전개
- **뷰 정리**: `backend/order/purchase_order_views.py`에서 `UnorderedItemsView`의 화면 시점
  전개 로직 제거, `GenerateOrderFileView`의 역방향 매핑 되돌리기
- **개발 방법론**: `.moai/config/sections/quality.yaml`의 `development_mode: tdd`를 따라
  RED-GREEN-REFACTOR로 진행(브라운필드 강화 — 기존 동작을 먼저 읽고 이해한 뒤 실패 테스트 작성)

### 프론트엔드

- 변경 없음(research.md §6 검증 — `is_bundle_member`/`bundle_sku` 필드를 참조하는 프론트엔드
  코드가 존재하지 않음)

### 마이그레이션 순서 (필수)

```
0025_lineitem_unique_together_with_sku.py (스키마)
        ↓ (반드시 먼저 적용)
0026_backfill_bundle_lineitems.py (데이터, RunPython)
```

스키마 마이그레이션이 먼저 적용되지 않으면 백필이 동일 `shopify_line_item_id`를 공유하는 N개
행을 생성할 때 구 제약(`order`, `shopify_line_item_id`) 위반으로 실패한다.

---

## 구현 단계

### Phase 1 — 스키마 변경 [Priority: High]

대상 파일:
- `backend/order/models.py` — `LineItem.Meta.unique_together` 수정 (REQ-SKUSET2-001)
- `backend/order/migrations/0025_*.py` (신규) — `AlterUniqueTogether` (REQ-SKUSET2-002)

작업 내용:
1. `LineItem.Meta.unique_together`를 `[("order", "shopify_line_item_id", "sku")]`로 변경
2. `python manage.py makemigrations order` 실행하여 스키마 마이그레이션 생성
3. 로컬(SQLite)과 스테이징(MySQL 8.0) 양쪽에서 마이그레이션 적용 검증

완료 조건:
- 마이그레이션 적용 후 동일 `(order, shopify_line_item_id)`에 서로 다른 `sku` 값을 가진 복수
  `LineItem` 행 저장 성공
- 완전히 동일한 `(order, shopify_line_item_id, sku)` 조합 저장 시도 시 `IntegrityError` 발생
  (회귀 테스트로 확인)

---

### Phase 2 — 싱크 파이프라인 번들-인식형 전개 [Priority: High]

대상 파일:
- `backend/order/shopify_orders.py` — `_sync_single_order()` 수정 (REQ-SKUSET2-003)

작업 내용:
1. 함수 진입 시 `ShopifySkuSetMapping` 전체를 1회 쿼리로 로드하여 `bundle_map: dict[str,
   list[str]]`(bundle_sku → sort_order 순 member_isbn 목록) 구성
2. 기존 `for li in order_data.get("line_items", []):` 루프 내부에서:
   - `li.get("sku")`가 `bundle_map`에 없으면 기존과 동일하게 단일 `update_or_create` 호출
   - 있으면 `bundle_map[li["sku"]]`의 각 `member_isbn`에 대해
     `update_or_create(order=order_obj, shopify_line_item_id=li["id"], sku=member_isbn,
     defaults={나머지 필드는 li에서 그대로 복사})` 반복 호출
3. `incoming_shopify_ids.add(li["id"])`는 라인 아이템당 1회만 호출(번들이든 아니든 동일하게
   유지 — 이미 `shopify_line_item_id` 단위이므로 변경 불필요)
4. stale-LineItem 삭제 로직(181-184번째 줄)은 수정하지 않음(REQ-SKUSET2-004)
5. `sync_store()`의 `existing_line_item_locs` 사전 로드 로직은 수정하지 않음(REQ-SKUSET2-005)

완료 조건:
- 번들 SKU 라인 아이템 싱크 시 구성 ISBN 수만큼 `LineItem` 생성, 각 행의 `quantity`가 원본과
  동일
- 일반 SKU 싱크는 기존과 100% 동일하게 동작(회귀)
- `ShopifySkuSetMapping` 조회가 주문 처리당 1회로 제한됨 확인

---

### Phase 3 — 화면/발주 뷰 정리 (되돌리기) [Priority: High]

대상 파일:
- `backend/order/purchase_order_views.py` — `UnorderedItemsView.get()` (REQ-SKUSET2-007,
  REQ-SKUSET2-008), `GenerateOrderFileView.post()` (REQ-SKUSET2-009)

작업 내용:
1. `UnorderedItemsView.get()`에서 131-152번째 줄의 `bundle_map`/`expanded` 블록 전체 삭제,
   `return Response({"count": len(results), "results": results})`로 되돌림
2. `GenerateOrderFileView.post()`에서 196-248번째 줄의 `member_to_bundle`/
   `requested_underlying`/`underlying_found_map` 역방향 매핑 로직 전체 삭제, spec.md
   REQ-SKUSET2-009에 명시된 단순 직접 조회로 되돌림
3. `ShopifySkuSetMapping` import는 `purchase_order_views.py`에서 더 이상 사용되지 않으면 제거
   (import 정리는 실제 코드에서 다른 참조가 없는지 확인 후 진행)

완료 조건:
- `UnorderedItemsView` 응답에 `is_bundle_member`/`bundle_sku` 필드가 더 이상 존재하지 않음
- `GenerateOrderFileView`가 (싱크 시점 전개로 이미 ISBN 단위인) `LineItem`을 직접 SKU로 조회하여
  정상 응답
- 기존 비번들 회귀 테스트 전부 통과

---

### Phase 4 — 데이터 백필 마이그레이션 [Priority: High]

대상 파일:
- `backend/order/migrations/0026_*.py` (신규, `RunPython`) — REQ-SKUSET2-011, REQ-SKUSET2-012

작업 내용:
1. `purchase_status="unordered"`, `purchase_orders__isnull=True`, `sku__in=<현재 등록된
   bundle_sku 목록>`인 `LineItem` 조회
2. 각 대상 행에 대해:
   - `ShopifySkuSetMapping.objects.filter(bundle_sku=li.sku).order_by("sort_order")`로 구성
     ISBN 목록 조회
   - 첫 번째 `member_isbn`: 원본 행의 `sku` 필드를 UPDATE(PK/노트 보존)
   - 나머지 `member_isbn`: 원본 행의 다른 필드를 복사한 신규 `LineItem` 생성(`order`,
     `shopify_line_item_id` 동일, `sku`만 다름)
3. 마이그레이션 데이터 조회 시 히스토리컬 모델(`apps.get_model("order", "LineItem")`,
   `apps.get_model("order", "ShopifySkuSetMapping")`) 사용(Django 데이터 마이그레이션 표준
   관행)
4. `reverse_code`는 `migrations.RunPython.noop`으로 지정하고, 완전한 역백필이 정보 손실로 인해
   불가능함을 마이그레이션 docstring에 명시

완료 조건:
- 마이그레이션 적용 후 `unordered` 상태이며 `sku`가 `bundle_sku`인 `LineItem`이 0건
- 백필된 각 그룹의 총 구성 ISBN 행 수가 해당 번들의 `member_isbn` 개수와 일치
- 이미 `PurchaseOrder`에 연결된 `LineItem`은 백필 전후로 변경 없음(스냅샷 비교 테스트)

---

### Phase 5 — 테스트 정리 및 신규 작성 [Priority: High]

대상 파일:
- `backend/order/tests/test_shopify_sku_set.py` — `TestUnorderedItemsBundleExpansion` 제거/재작성
  (REQ-SKUSET2-013)
- `backend/order/tests/test_purchase_orders.py` — `TestGenerateOrderFileView`의 3개 번들 테스트
  재작성 (REQ-SKUSET2-013)
- `backend/order/tests/test_shopify_orders.py` — 신규 싱크 파이프라인 번들 테스트 추가
  (REQ-SKUSET2-014)
- `backend/order/tests/test_order_resync.py` — 재동기화 엣지 케이스 회귀 테스트 추가 (권장,
  REQ-SKUSET2-015)

작업 내용:

**백엔드 (`pytest`, RED-GREEN-REFACTOR)**:
1. RED: `_sync_single_order`가 번들 SKU를 구성 ISBN으로 전개하도록 기대하는 실패 테스트 작성
2. GREEN: Phase 2 구현으로 테스트 통과
3. REFACTOR: 중복 로직 정리, `_sync_single_order` 가독성 개선(과도한 추상화 지양)
4. `TestUnorderedItemsBundleExpansion` 제거 또는 "싱크 후 상태 확인" 테스트로 전환
5. `TestGenerateOrderFileView`의 3개 번들 테스트를 "이미 전개된 LineItem" 픽스처 기반으로 재작성
6. stale-LineItem 삭제, 위치 캐시 최적화 회귀 테스트 추가
7. 백필 마이그레이션 테스트(가능하면 `django.test.migrations` 헬퍼 또는 별도 스크립트 검증)

완료 조건:
- 전체 `backend/order/tests/` 스위트 통과
- 신규/변경 코드 커버리지 85% 이상
- `test_auto_dist.py`, `test_shopify_sku_set.py`의 CRUD 테스트(전개와 무관한 부분) 무변경 통과

---

## 리스크 및 완화 방안

| 리스크 | 영향 | 완화 방안 |
|--------|------|-----------|
| 스키마 마이그레이션이 백필 마이그레이션보다 먼저 적용되지 않음(순서 오류) | 높음 — 백필 실패 또는 제약 위반 | 두 마이그레이션의 `dependencies`를 명시적으로 연결, 배포 스크립트에서 순차 적용 강제 |
| 백필 도중 프로세스가 중단되어 일부 번들만 전개된 상태로 남음 | 중 — 데이터 일관성 저하 | 백필 로직을 개별 `LineItem` 단위로 idempotent하게 작성(이미 전개된 행은 재탐지되지 않도록 `sku`가 더 이상 `bundle_sku`가 아니므로 자연히 재실행 시 스킵됨) |
| 재동기화 시 매핑 변경으로 고아 구성원 행 발생(REQ-SKUSET2-010) | 낮음~중 — 의도적으로 미해결 | Exclusions에 명시, 향후 별도 SPEC으로 필요 시 대응 |
| 환불 계산의 "코드 변경 없이 자동 성립" 가정이 깨지는 경우(수량을 구성원별로 나눠 저장하는 실수) | 높음 — 재무 인접 로직 오류 | REQ-SKUSET2-003/006에 "미분할 원본 수량 그대로 복사"를 명시적 요구사항으로 못박음, 회귀 테스트로 고정 |
| MySQL 프로덕션 마이그레이션 적용 시 대량 `LineItem` 테이블에 대한 `AlterUniqueTogether` 잠금/성능 영향 | 중 | 스테이징 환경에서 사전 검증, 트래픽이 적은 시간대 배포 권장(운영 절차는 Run 단계에서 manager-git/expert-devops와 조율) |

---

## 구현 순서 요약

```
Phase 1 (스키마) → Phase 2 (싱크 파이프라인) → Phase 3 (뷰 정리) → Phase 4 (백필) → Phase 5 (테스트)
```

Phase 1은 Phase 4(백필)의 선행 조건이므로 반드시 먼저 적용.
Phase 2와 Phase 3은 서로 독립적이며 병렬 진행 가능(단, 둘 다 Phase 1 이후).
Phase 4는 Phase 1 완료 후 아무 때나 가능하지만, Phase 2/3과 함께 검증하는 것을 권장(백필 결과가
정리된 뷰/파이프라인과 일관되게 동작하는지 확인).
Phase 5는 각 Phase 구현과 동시에(TDD 원칙에 따라 테스트 우선) 진행.
