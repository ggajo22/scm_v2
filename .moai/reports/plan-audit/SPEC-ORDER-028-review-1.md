# SPEC Review Report: SPEC-ORDER-028

Iteration: 1/3
Verdict: **FAIL**
Overall Score: **0.55**

> M1 Context Isolation: SPEC 작성자의 추론 맥락은 무시했다(전달된 것도 없음). 판정은 `.moai/specs/SPEC-ORDER-028/{spec,plan,acceptance}.md` 세 파일과, 이 세션에서 직접 읽은 저장소 코드만을 근거로 한다. 프롬프트가 제공한 "확정된 설계 결정 3건"은 재론하지 않고, 그 결정이 **정확·완전하게 명세되었는지**만 감사했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — `REQ-RSW-001`~`REQ-RSW-028`, 선언 28건 / 고유 28건 / 중복 0건 / 결번 0건, 3자리 zero-padding 일관. 기계 검증: `grep -c "^\*\*REQ-RSW-" spec.md` = 28, `sort -u` = 28.
- **[FAIL] MP-2 EARS 형식 준수** — 아래 4가지가 동시에 성립한다.
  - `spec.md:193-194` **REQ-RSW-028**: "…확장을 **검토할 수 있다** — 이 SPEC은 이를 필수 요구사항으로 만들지 않는다". 규범성이 없는 문장이며 `spec.md:229`에서 "AC 없음 — 이 SPEC에서 구현하지 않음"으로 스스로 비구현을 선언한다. 요구사항 절에 들어갈 항목이 아니다(§8 또는 Exclusions 소속).
  - `spec.md:144-145` **REQ-RSW-015**: "Shopify가 종료/취소된 주문도 이 엔드포인트에서는 반환하므로 …**shall** 관측 가능해진다" — 시스템의 의무가 아니라 외부 API의 성질에 대한 주장이며, 가정 A3(`spec.md:69`)과 내용이 중복된다.
  - 조동사(shall/…해야 한다) 없이 평서형으로만 쓰인 REQ 9건: 003(`:103`), 005(`:109`), 006(`:112`), 007(`:117`), 008(`:120`), 009(`:123`), 012(`:132`), 017(`:153`), 023(`:175`), 027(`:191`).
  - `spec.md:131-132` **REQ-RSW-012**는 `When` + `while`을 한 문장에 혼합(Event-Driven 라벨과 불일치).
- **[PASS] MP-3 YAML frontmatter 유효성** — `spec.md:1-11`에 `id: SPEC-ORDER-028`, `version: 0.1.0`, `status: draft`, `created_at: 2026-08-19`, `priority: High`, `labels: [order, shopify, sync, resync, performance, backend]` 전부 존재, 타입 정합.
- **[N/A] MP-4 Section 22 언어 중립성** — 단일 언어(Python/Django) 프로젝트 SPEC. 자동 통과.

---

## Category Scores (rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.60 | 0.50–0.75 | 다수 요구사항이 **틀린 플랫폼 전제** 위에 서술됨(A4 `:70` PostgreSQL, C5 `:259` SQLite/PostgreSQL — 실제 DB는 MySQL). `REQ-RSW-022`(`:171-172`)의 "동작이 무변경이다"는 사실과 다름(D7) |
| Completeness | 0.65 | 0.50–0.75 | 섹션·frontmatter·Exclusions(11건) 구조는 완전(`:235-247`). 그러나 이 변경이 실제로 만들어내는 4개 실패 모드(D1~D4)에 대해 REQ·AC·위험 항목이 모두 없음 |
| Testability | 0.45 | 0.25–0.50 | AC-RSW-006 판별력 0(D5), AC-RSW-018 공허 통과 가능(D8), AC-RSW-026이 요구한 rate를 검증하지 않음(D9), 성능 목표 자체가 반증 불가(D10) |
| Traceability | 0.65 | 0.50–0.75 | 번호·매핑은 대체로 실재하나 `spec.md:208`(REQ-007→AC-001)은 해당 AC가 커맨드를 실행조차 하지 않음(D11), REQ-021 매핑이 두 문서 간 불일치(D22), DoD-only REQ 6건 중 REQ-RSW-020의 DoD 검사는 그 위반을 검출할 수 없음(D17) |

---

## 인용 검증 결과 (감사 우선순위 1)

**총 41개 `file:line` 인용을 전부 원본에서 열어 대조했다. 정확 39건, 근거 불충분 2건.**

정확한 인용(발췌): `shopify_orders.py:32-45`(fetch_all_open_orders) ✓, `:104` / `:104-331`(_sync_single_order 시작·끝) ✓, `:140-147`(status/ready_to_ship 제외 주석) ✓, `:159`(shopify_created_at ← created_at) ✓, `:191-196`(bundle_map) ✓, `:198-207`(title_map) ✓, `:209-224`(protected_sku_by_key) ✓, `:229-230`(purchase_status/logistics_status 제외 주석) ✓, `:256-270`/`:271-285`(번들/비번들 분기) ✓, `:291-304`(ShippingLine) ✓, `:306-329`(Refund) ✓, `:314`(`or [{}]`) ✓, `:334-352` ✓, `:355-461` ✓, `:420-428`(위치 재사용 단축 경로) ✓ / `models.py:30`, `:76`, `:77`, `:79`, `:80`, `:95-111`, `:182`, `:204-208`, `:228`, `:253`, `:320`, `:342`, `:565-603` 전부 ✓ / `views.py:99-156`, `:188-253`, `:203-223`, `:408` 전부 ✓ / `backfill_missing_orders.py:62-65`, `:131-149`, `:138-143` 전부 ✓ / `purchase_order_views.py:2392-2579` ✓ / `.moai/project/scheduled-jobs.md:16`("약 16초, 신규 0~2건") ✓ 및 §4 존재 ✓ / 최신 마이그레이션 `0044_lineitem_original_sku` ✓(→ `0045` 번호 타당) / `scripts/sync_orders.bat` 구조 미러링 주장 ✓(인터프리터 절대경로·PYTHONIOENCODING·로그·`exit /b %RC%` 모두 실물과 일치) / `sync_orders.py`의 "끝까지 순회 후 실패 집계 → CommandError" 계약 ✓ / `_sync_single_order` 기존 호출부 정확히 3곳(`shopify_orders.py:351`, `:430`, `backfill_missing_orders.py:138`) ✓ / acceptance.md §0.1이 참조한 `test_spec_014.py:34,38`·`test_spec_027.py:37,41`의 `_make_order`/`_make_line_item` 헬퍼 ✓ / 회귀 대상 테스트 파일 4종 전부 실재 ✓.

**인용이 주장을 뒷받침하지 못하는 2건 → D18에서 상술** (`spec.md:259`, `plan.md:386`의 `backend/config/settings/local.py:11`).

이 SPEC의 `file:line` 인용 품질 자체는 SPEC-ORDER-027 HISTORY의 교훈이 반영되어 **양호**하다. 문제는 인용의 정확성이 아니라, **인용하지 않은 코드 경로에 대한 미검증 가정**(D1~D4)에 있다.

---

## Defects Found

### CRITICAL

**D1. 제안된 차등 upsert는 이 프로젝트의 DB에서 실행 자체가 불가능하다 — `NotSupportedError`. 그리고 그 폭발 반경은 스위프가 아니라 5분 주기 프로덕션 동기화 전체다.**
`plan.md:336-338`(ShippingLine)와 `plan.md:376-378`(Refund)는 `bulk_create(update_conflicts=True, unique_fields=[...], update_fields=[...])`를 쓴다.
- 실제 DB는 **MySQL**이다: `backend/.env` → `DB_ENGINE=django.db.backends.mysql`, `DB_HOST=gimssine.c96se8scy765.us-west-2.rds.amazonaws.com`, `DB_PORT=3306`. `mysqlclient 2.2.7` 설치됨. `pytest.ini` → `DJANGO_SETTINGS_MODULE = config.settings.local`, 그리고 `config/settings/local.py`가 유일한 DATABASES 정의부다(다른 settings 모듈 없음).
- Django 5.1.6 `QuerySet._check_bulk_create_options`: `if unique_fields and not db_features.supports_update_conflicts_with_target: raise NotSupportedError(...)`. MySQL 백엔드는 `supports_update_conflicts = True`, **`supports_update_conflicts_with_target = False`**(이 세션에서 설치된 Django 소스로 직접 확인).
- 따라서 `unique_fields`를 넘기는 순간 **무조건** `NotSupportedError: This database backend does not support updating conflicts with specifying unique fields that can trigger the upsert.`
- 이 코드는 `_sync_single_order()` **내부**에 있다. 즉 4개 호출부 전부가 죽는다: `sync_store()`(5분 주기 프로덕션 동기화), `sync_single_order_from_shopify()`(수동 재동기화 버튼), `backfill_missing_orders`, 신규 스위프.
- **정정된 사실**: MySQL에서는 `unique_fields`를 **생략**해야 한다(`bulk_create(rows, update_conflicts=True, update_fields=[...])` → `ON DUPLICATE KEY UPDATE`, 모든 unique key에 대해 동작). 다만 이 형태는 D2의 NULL 문제를 해결하지 못한다.
- 이 오류는 `spec.md:259`(C5), `plan.md:386`(§1.5-C), `plan.md:520`(R9), `plan.md:455`(M4-4), `plan.md:571`·`:591`("실제 PostgreSQL로")까지 연쇄적으로 무효화한다. R9의 완화책("SQLite/PostgreSQL 양쪽 실행 확인")은 **실행되는 플랫폼이 둘 다 아니므로** 이 결함을 잡지 못한다.

**D2. header-only 환불 행(`or [{}]`, `line_item_id IS NULL`)이 스위프마다 무한 증식한다. 이를 잡는 AC가 없다.**
- `models.py:328` `line_item_id = models.BigIntegerField(null=True, blank=True)`, `models.py:342` unique_together `(order, shopify_refund_id, line_item_id)`.
- **현행**(`shopify_orders.py:306-329`): `.all().delete()` 후 `update_or_create(line_item_id=None, …)` → Django ORM이 `IS NULL`로 조회하므로 정확히 1행. 기존 회귀 테스트가 이를 고정하고 있다: `backend/order/tests/test_shopify_orders.py:765` `test_sync_keeps_header_only_row_for_refund_without_line_items` (`refunds.count() == 1`).
- **제안안**(`plan.md:364-379`): 차등 삭제는 `(refund_id, None) in incoming_refund_keys`가 참이라 이 행을 **보존**하고, 이어지는 upsert는 SQL unique 제약의 NULL 판별 규칙(NULL ≠ NULL) 때문에 **충돌로 인식되지 않아 새 행을 INSERT**한다. 스위프 1랩(약 2.8시간)마다 1행씩, 60일 윈도 동안 무한 누적.
- `REQ-RSW-026`(`spec.md:185-186`, "최종 상태는 기존 delete-and-recreate 방식과 동일해야 한다")의 직접 위반이다.
- 커버리지 공백: AC-RSW-021(`acceptance.md:361`)과 AC-RSW-022(`acceptance.md:376`)는 둘 다 **non-null** `line_item_id` 픽스처를 쓴다. 기존 스위트도 못 잡는다 — `:765` 테스트는 1회만 동기화하고, `:665` `test_resync_of_multi_item_refund_is_idempotent`는 2회 동기화하지만 non-null id만 쓴다.
- 수량 네팅 자체는 살아남는다(`serializers.py:180`이 `line_item_id is None`을 건너뛰고, SQL 서브쿼리는 `line_item_id=OuterRef("shopify_line_item_id")`로 조인 — `purchase_order_views.py:171-177`). 그러나 `Refund` 테이블 무한 증식 + REQ 위반은 그대로다. 이 저장소에는 이미 환불 행 손상 복구용 커맨드 `backend/order/management/commands/repair_refunds.py`가 존재한다(migration 0038 이전 결함) — 환불 쓰기 경로 변경의 위험 등급을 낮게 잡을 근거가 없다.

**D3. fulfillment API 실패 시 `Order.location`과 모든 `LineItem.location`이 조용히 "" 로 지워지고, 스위프는 그 주문을 성공으로 기록한다.**
- `shopify_orders.py:100-101`: `_build_fulfillment_location_data`는 **모든** 예외를 삼키고 `("", {})`를 반환한다(의도된 계약이며 `backend/order/tests/test_order_location.py:79` `test_build_fulfillment_location_returns_empty_on_error`가 이를 고정).
- `shopify_orders.py:165`: `"location": location_code`가 **무조건** Order defaults에 들어간다. `:242`: `"location": line_item_location_map.get(li["id"], "") if line_item_location_map else ""`.
- `sync_store()`는 기존 주문에 대해 이 경로를 아예 타지 않는다(`:420-428` 저장값 재사용). **REQ-RSW-013(`spec.md:136-137`)이 바로 그 보호막을 의도적으로 제거**하므로, 이것은 이 SPEC이 **새로 만들어내는** 노출이며, 대상 1,328건 × 랩당 1회 전량에 적용된다.
- 예외가 밖으로 나오지 않으므로 `plan.md:247`의 `except`에 걸리지 않는다 → `succeeded += 1`, `CommandError` 없음, 운영자에게 아무 신호도 가지 않는다.
- D14(0.5초 = 한도 정확히 소진, 429 처리 없음 — Exclusions #9 `spec.md:245`)와 결합하면 429가 곧바로 위치 전면 소거로 이어진다. `location`은 NJ/CA 창고 라우팅 값이다.
- REQ 없음, AC 없음, `plan.md:511-522` 위험표에 항목 없음. AC-RSW-014(`acceptance.md:245-256`)는 정상 경로만 검증한다.

**D4. 이 SPEC의 3대 명분 중 하나(번들 매핑 전파)는 실제로는 고아 중복 LineItem 행을 만든다. 저장소가 이미 알고 있고 테스트까지 있는 동작이다.**
- `spec.md:29`는 "번들 매핑을 추가해도 기존 주문은 재전개되지 않는다"를 스위프가 닫는다고 주장한다.
- 그러나 `_sync_single_order`의 번들 분기는 `sku=member_isbn`을 **조회 키**로 삼아 새 행을 만들고(`shopify_orders.py:265-269`), stale 행 삭제는 `shopify_line_item_id`만 기준으로 한다(`:287-289`). 기존 `sku=bundle_sku` 행은 같은 `shopify_line_item_id`를 가지므로 **삭제 대상에서 제외**되고, 변환되지도 않는다. 각 멤버 행은 **분할되지 않은 전량 수량**을 갖는다(`:246-249`).
- 저장소는 이 함정을 이미 알고 있었다: `backend/order/migrations/0026_backfill_bundle_lineitems.py:63-64`는 첫 멤버에 대해 원본 행을 **제자리 UPDATE** 하는 방식으로 우회했고(`li.sku = first_isbn; li.save(...)`), 주석 `:11-12`가 그 이유를 명시한다. 거울상 사례는 `backend/order/tests/test_order_resync.py:255-292`에 "accepted, intentionally-unresolved edge case"로 문서화되어 있다 — **수동·건별 재동기화라서 용인**된 것이다.
- SPEC-ORDER-028은 이를 1,328건 × 2.8시간 주기의 **무인 자동 작업**으로 바꾼다. 관련 REQ·AC·Exclusion·위험 항목이 전부 없다. 결과 상태는 `bundle_sku` 1행 + 멤버 N행이 모두 전량 수량을 들고 공존하는 것이며, 이 저장소의 수량 집계 규약(환불 차감 포함)에 직접적인 오염이다.

### MAJOR

**D5. AC-RSW-006은 자신이 잡는다고 선언한 변이를 이 프로젝트의 DB에서 전혀 잡지 못한다.**
`acceptance.md:132`: "`nulls_first=True`를 빠뜨린 변이(PostgreSQL 기본값 NULLS LAST)는 결과 순서를 [F, G]로 뒤집어 즉시 잡힌다."
- MySQL: `DatabaseFeatures.order_by_nulls_first = True`, `supports_order_by_nulls_modifier = False`(직접 확인). Django `OrderBy.as_sql`의 분기는 `nulls_first and not (not descending and order_by_nulls_first)` → `not (True and True)` = False → **템플릿을 추가하지 않는다**. 즉 `F("last_resynced_at").asc(nulls_first=True)`와 `.asc()`는 **바이트 단위로 동일한 SQL**로 컴파일된다(MySQL은 ASC에서 NULL을 먼저 정렬).
- `acceptance.md:33`은 AC-RSW-006을 M4의 **단독** 판별자로 지정했다. 실제로는 DESC 변이만 잡히고 `nulls_first` 누락 변이는 미커버다. 변이 M4는 사실상 커버되지 않는다.

**D6. REQ-RSW-002가 요구한 인덱스는 명세된 형태로는 요구된 정렬을 지원하지 못하며, 그 근거는 이 프로젝트가 쓰지 않는 DB를 대상으로 쓰였다.**
- `plan.md:29`/`:46-49`: `models.Index(fields=["last_resynced_at"])`. `plan.md:53`은 "플래너가 인덱스 순서대로 스캔하며 … 조기 종료(early termination)"라는 PostgreSQL 서술로 정당화한다.
- 대상 쿼리(`plan.md:82-90`)는 `shopify_created_at__gte`(자체 인덱스 존재, `models.py:99`) + `EXISTS` 서브쿼리 + `ORDER BY last_resynced_at`을 동시에 요구한다. 테이블 접근당 인덱스는 하나이므로, 정렬용 인덱스를 택하면 조건을 만족하는 40건이 모일 때까지 `orders_order` 전체(현재 3,883행, 증가 중)를 인덱스 순서로 훑으며 행마다 EXISTS를 평가해야 하고, 필터용 인덱스를 택하면 filesort가 된다. 어느 쪽도 `plan.md:53`이 약속한 조기 종료가 아니다.
- REQ-RSW-002(`spec.md:97-98`)의 목적("정렬 단계에서 전체 테이블 스캔에 의존하지 않도록")은 명세된 구현으로 달성되지 않는다. AC 없음, DoD는 `AddIndex` 존재 여부만 본다(`spec.md:203`) — 이 검사는 플랜이 인덱스를 안 쓰는 상황을 구조적으로 검출할 수 없다.

**D7. "sync_store()/backfill_missing_orders 동작 무변경"은 사실이 아니다.**
- `spec.md:171-172`(REQ-RSW-022) "…동작이 무변경이다", `spec.md:81`(D2), `spec.md:244`(Exclusions #8), `plan.md:499`/`:501`([EXISTING] **무변경**).
- 그러나 REQ-RSW-024/025는 `_sync_single_order()` **내부**의 환불/배송라인 쓰기 블록을 무조건적으로 교체한다. 기존 3개 호출부(`shopify_orders.py:351`, `:430`, `backfill_missing_orders.py:138`)가 전부 그 코드를 실행한다. 옵트인인 것은 `bundle_map`/`title_map` 파라미터화뿐이다.
- DoD(`acceptance.md:529`)는 `sync_store()`의 **소스 텍스트** 무변경만 확인한다 — 런타임 동작 변경을 검출하지 못한다. 그 결과 위험표에 "환불/배송라인 리팩터가 5분 주기 프로덕션 동기화를 깨뜨린다"는 항목이 없고, 이는 정확히 D1이 일으키는 사고다.

**D8. 보존(preservation) 계열 AC 017–022는 공허하게 통과할 수 있다.**
- AC-RSW-018(`acceptance.md:314`)의 Given은 LineItem을 `logistics_status="shipment_confirmed"`로 둔다. REQ-RSW-003(`spec.md:103`)은 `not_shipped` 라인아이템이 **최소 1건** 있어야 스위프 대상으로 본다. 이 픽스처 주문은 대상 조건을 만족하지 못하므로 커맨드가 아무 것도 처리하지 않고, "무변경" 단정은 정답 코드와 **모든 변이 코드에서 똑같이** 통과한다. 판별력 0.
- 동일한 구조적 위험이 AC-017/019/020/021/022에 있다: 어느 것도 픽스처가 REQ-RSW-003(+60일 창)을 만족한다고 명시하지 않고, 어느 것도 "그 주문이 실제로 스윕되었다"(예: `last_resynced_at` 전진, `_sync_single_order` 호출)를 단정하지 않는다.
- 변화(change) 계열 AC(014/015/016/023)는 같은 실수를 하면 시끄럽게 실패하므로 자기교정된다. 위험은 보존 계열에 집중된다.

**D9. AC-RSW-026은 REQ-RSW-014가 요구한 rate를 검증하지 않는다.**
- REQ-RSW-014(`spec.md:139-140`)는 API 호출 **사이마다** 최소 0.5초를 요구한다.
- AC-RSW-026(`acceptance.md:444`)은 6회 호출에 대해 "페이싱 훅이 **최소 2회 이상**" 호출되는지만 보고, 계산된 대기값이 0인 경우를 명시적으로 면책한다.
- 통과하는 변이: (a) 주문당 1회만 페이싱(호출률 2배 = 4 calls/sec, 훅 3회 → 통과), (b) 간격 상수를 0.05초로 변경(훅 호출 횟수 동일 → 통과). `acceptance.md:33`이 이를 M19의 단독 판별자로 선언했으나 실제로는 "페이싱 전면 삭제"만 잡는다.

**D10. 확정 결정 3번(per-order 비용 최적화)에 측정 가능한 요구사항도 AC도 없다.**
`spec.md:31`은 문제를 정량화한다(주문당 약 15쿼리, 약 2초). 그러나 목표치를 규정한 REQ가 없고(예: "주문당 쿼리 N개 이하"), 성능 관련 AC는 `ShopifySkuSetMapping` 조회 1회를 세는 AC-RSW-024 하나뿐이다. 호이스팅이 제거하는 것은 15개 중 2개다. 최적화 목표는 명세된 상태로는 반증 불가능하다.

**D11. REQ-RSW-007의 추적 대상 AC는 커맨드를 실행조차 하지 않는다.**
`spec.md:208`: REQ-RSW-007 → "AC-RSW-001(대표 — 커맨드 실행 자체가 전제조건)". 그러나 AC-RSW-001(`acceptance.md:46-57`)의 When은 "`_qualifying_orders_queryset()`을 평가한다"이며 `resync_order_sweep`을 호출하지 않는다. `spec.md:231`의 [HARD] 추적표 무결성 규칙("REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다")의 자기 위반이다. (실질 커버리지는 AC-007/011/012에 존재하므로 매핑 정정으로 해소 가능.)

**D12. REQ-RSW-028은 요구사항이 아니다.** (MP-2 근거와 동일, `spec.md:193-194`/`:229`.)

### MEDIUM

**D13. REQ-RSW-017("어떤 DB 락도 공유하지 않는다")은 문자 그대로 거짓이며, D1(실패 시 전진)과의 상호작용이 분석되지 않았다.**
`backend/order/management/commands/sync_orders.py`는 스토어 전체 `sync_store()`를 **하나의** `transaction.atomic()`으로 감싼다 — 그 동안 자신이 쓰는 모든 order/line_item 행에 InnoDB 행 잠금을 커밋 시점까지 보유한다(1회 약 16초, `.moai/project/scheduled-jobs.md:16`). 스위프는 **같은 행들**을 쓴다. `sync_orders.py` 자신의 독스트링이 "one of the two fails on a lock wait or a duplicate-key conflict"라고 적고 있다. 설계 결정 D1 때문에 lock-wait 패배는 이제 다음 사이클이 아니라 **다음 랩(약 2.8시간)** 지연을 뜻하고, 매 겹침마다 `CommandError` → 스케줄러 경보가 울린다. 두 작업 모두 5분 트리거다(`plan.md:412`). §8에 항목 없음.

**D14. 0.5초 페이싱은 여유가 0이며, 동시 소비자와 기존 선례를 무시한다.**
가정 A5(`spec.md:71`)가 예산을 ~2회/초로 잡았는데 REQ-RSW-014는 정확히 0.5초를 택했다 — 한도를 정확히 소진한다. 같은 상점에 대해 `sync_store()`(5분 주기)와 수동 재동기화 버튼이 같은 버킷을 동시에 소비하고, Exclusions #9가 429 대응을 제거했다. D3의 촉발 조건이다.
또한 저장소에는 이미 페이싱 선례가 있다: `backend/order/management/commands/repair_refunds.py:36-39`, `--sleep` 기본값 **0.3**, 도움말 "respects the REST rate limit". A5는 "사용자 제공, 재검증하지 않음"이라고 적었으나 사내 선례는 코드에 있었다.

**D15. plan.md의 사이클 소요 산정이 SPEC 자신이 지목한 지배항을 빠뜨렸다.**
`plan.md:266`/R6(`plan.md:517`): "80회 × 0.5초 ≈ 40초, 5분 대비 여유". 이는 페이싱만 센 값이다. `spec.md:31`의 자체 수치(주문당 약 2초의 DB 시간)로는 40건 ≈ 80초가 추가되고, 80회의 네트워크 왕복이 별도다. 현실적 사이클은 약 2~3분이며, `plan.md:395`가 의존하는 "Do not start a new instance" 여유는 주장보다 훨씬 얇다.

**D16. AC-RSW-024는 판별력을 좌우하는 지점에서 픽스처가 미정의다.**
`acceptance.md:408`의 Given은 "대상 주문 3건(모두 성공 모킹)"이다. AC-RSW-007(`acceptance.md:147`)처럼 `_sync_single_order`를 모킹하면, M17 변이는 `ShopifySkuSetMapping` 조회를 **3회가 아니라 0회** 만들고 `acceptance.md:414`가 적은 대비(`1 ≠ 3`)는 성립하지 않는다. "HTTP 계층만 모킹하고 `_sync_single_order`는 실물로 실행한다"가 AC에 명시되어야 한다.

**D17. 부분 입고: 기준 자체는 옳으나 SPEC이 그 사실을 진술하지 않고, 입고 데이터 보존도 검증하지 않는다.**
검증 결과: `_process_warehouse_receipt_rows`는 `logistics_status IN ("not_shipped","shipment_confirmed")`을 대상으로 하고(`purchase_order_views.py:2481`), `received_quantity >= effective_quantity`일 때만 `"received"`로 올린다(`:2549-2550`); 부분 입고는 `logistics_status`를 건드리지 않는다(`:2415-2418`, `:2596-2597`). 따라서 부분 입고된 라인아이템은 `not_shipped`로 남아 **대상에 포함된다** — 실수로 배제되지는 않았다.
그러나 (a) 이 사실을 진술한 REQ가 없고, (b) 스위프가 `received_quantity`/`received_at`/`shipped_quantity`/`rack_number`/`damaged_quantity`/`confirmed_*`를 보존하는지 검증하는 AC가 없다. REQ-RSW-020(`spec.md:163-164`)은 "쓰지 않는다"만 금지하고 보존을 단정하지 않으며, 그 추적은 "AC 없음 — `git diff` 확인"(`spec.md:221`)이다. 이 DoD는 스위프가 새로 밟게 되는 라인아이템 stale 삭제 경로(`shopify_orders.py:287-289`, `purchase_orders__isnull=True`인 행을 삭제)로 인한 손실을 검출할 수 없다 — 그리고 REQ-RSW-015가 새로 도달하게 만드는 종료/취소·편집된 주문이 바로 Shopify 페이로드가 달라질 수 있는 주문군이다.

### MINOR

**D18. `local.py:11` 인용이 주장을 뒷받침하지 않는다.** `spec.md:259`(C5)와 `plan.md:386`은 "이 프로젝트의 pytest 기본 DB는 SQLite(`backend/config/settings/local.py:11`)"라고 적는다. 해당 라인은 `config("DB_ENGINE", default="django.db.backends.sqlite3")` 즉 **폴백 기본값**일 뿐이고, `backend/.env`가 `django.db.backends.mysql`로 덮어쓴다. 인용된 줄은 실재하나 주장을 지지하지 않는다.

**D19. 가정 A4가 잘못된 DB를 대상으로 한다.** `spec.md:70`은 PostgreSQL의 NULLS LAST 기본값을 근거로 기아(starvation) 위험을 설명한다. MySQL은 ASC에서 NULL을 먼저 정렬하므로 서술된 형태의 위험은 존재하지 않는다(그리고 그 때문에 D5가 발생한다).

**D20. 요구사항에 구현 기법이 박혀 있다(RQ-3/RQ-4).** REQ-RSW-004는 `Exists()` 사용을 지시하고 `.distinct()`를 금지한다(`spec.md:105-106`); REQ-RSW-010은 `transaction.atomic()`을 지정(`:126`); REQ-RSW-021은 파라미터 이름을 고정(`:168-169`); REQ-RSW-024/025는 판별 키를 고정(`:180`,`:183`). 각 경우의 검증 가능한 요구는 결과(중복 행 없음 / 주문 단위 격리 / 데이터 무유실)다.

**D21. 문서 간 추적 불일치.** `spec.md:222`는 REQ-RSW-021 → AC-RSW-025만 매핑하지만 `acceptance.md:405`의 AC-RSW-024도 REQ-RSW-021을 추적한다고 선언한다.

---

## Chain-of-Verification Pass

1차 감사 후 재점검한 항목과 결과:

- **REQ를 전부 읽었는가, 앞부분만 훑었는가** → 001~028을 개별적으로 5개 EARS 패턴에 대조해 재독. 이 과정에서 조동사 누락 9건과 REQ-RSW-028 비규범성(D12), REQ-RSW-015 오분류를 새로 발견해 MP-2를 PASS→**FAIL**로 하향했다.
- **REQ 번호를 끝까지 확인했는가** → `grep` 기계 검증으로 28/28/중복 0 확인.
- **추적성을 REQ 전건에 대해 확인했는가, 표본만 봤는가** → 28건 전부를 acceptance.md의 실제 AC 본문과 대조. 이 과정에서 D11(REQ-007 오매핑)과 D21(문서 간 불일치)을 발견했다. 1차에서는 "AC 있음"만 보고 넘어갈 뻔했다.
- **Exclusions를 존재 여부만 봤는가** → 11개 항목을 개별 검토. 전부 구체적이며 REQ와 모순되지 않음. 다만 D3/D4가 만들어내는 실패 모드가 어느 Exclusion에도 "의도적 비대상"으로 선언되어 있지 않음을 확인(= 누락이지 배제가 아님).
- **요구사항 간 모순을 봤는가** → D7(REQ-RSW-022 "동작 무변경" vs REQ-RSW-024/025의 무조건 적용)은 이 2차 패스에서 발견했다. 1차에서는 Exclusions #8의 문구만 보고 정합하다고 판단할 뻔했다.
- **인용을 "그럴듯해서" 통과시키지 않았는가** → 41건 전부를 원본에서 열어 대조했고, 그 결과 D18(인용은 실재하나 주장을 지지하지 않음)을 잡았다. 더 중요하게, **인용된 줄이 아니라 인용되지 않은 인접 코드**(`shopify_orders.py:100-101`, `:165`, `:242`, `:287-289`, `models.py:328`)를 읽은 것이 D2·D3·D4의 근거가 되었다. 이 SPEC의 위험은 "가짜 인용"이 아니라 "읽지 않은 경로에 대한 가정"에 있다.
- **DB 전제를 검증했는가** → 이 항목은 1차 계획에 없었고, `plan.md:386`의 "SQLite/PostgreSQL 양쪽" 문장이 걸려 추가 검증한 결과 D1(치명)·D5·D6·D18·D19가 연달아 나왔다. 감사 프롬프트조차 "Remote shared PostgreSQL"이라고 기술했으나 저장소 실물은 MySQL이다 — **전달된 맥락을 코드로 재검증하지 않았다면 이 SPEC은 통과했을 것이다.**

신규 발견: D1, D5, D6, D7, D11, D12, D18, D19, D21. 전부 위 목록에 반영했고 점수를 하향 조정했다.

---

## Regression Check

해당 없음 — iteration 1(이전 리뷰 리포트 없음).

---

## Recommendation (manager-spec 대상, 우선순위 순)

1. **DB 전제를 먼저 정정하라.** 실제 백엔드는 MySQL(`backend/.env`, `mysqlclient 2.2.7`, Django 5.1.6)이다. `spec.md:70`(A4), `spec.md:259`(C5), `plan.md:386`(§1.5-C), `plan.md:520`(R9), `plan.md:455`, `plan.md:571`·`:591`을 전부 다시 쓰라. 정정 없이는 이후 항목의 근거가 성립하지 않는다.
2. **`plan.md:336-338`, `plan.md:376-378`에서 `unique_fields`를 제거하라.** MySQL에서는 `bulk_create(rows, update_conflicts=True, update_fields=[...])` 형태만 유효하다. 그리고 이 리팩터가 `sync_store()`·`sync_single_order_from_shopify()`·`backfill_missing_orders` 전부에 즉시 적용된다는 사실을 위험 항목으로 신설하라.
3. **header-only 환불(`line_item_id IS NULL`)을 별도 요구사항 + AC로 다뤄라.** upsert 경로에서 제외하고 명시적으로 처리하거나(권장), 최소한 "동일 페이로드 2회 연속 스위프 후 `Refund.objects.filter(order=…, line_item_id__isnull=True).count() == 1`"을 단정하는 AC를 추가하라. 기존 회귀 테스트 `test_shopify_orders.py:765`는 1회 동기화만 하므로 이 결함을 잡지 못한다.
4. **fulfillment 조회 실패 시 위치 덮어쓰기 금지를 REQ로 명문화하라.** `_build_fulfillment_location_data`가 `("", {})`를 반환한 경우(`shopify_orders.py:100-101`) 스위프는 `location`을 쓰지 않아야 하며(또는 그 주문을 실패로 계상해야 하며), 이를 검증하는 AC(예: fulfillment 호출이 예외를 던지도록 모킹 → `Order.location`이 "NJ"로 유지, 실패 카운트 1)를 추가하라. 현재 AC-RSW-014는 정상 경로만 본다.
5. **번들 매핑 전파의 부작용을 결정하라.** `spec.md:29`의 3번 명분을 유지하려면 고아 `bundle_sku` 행 처리를 REQ+AC로 정의해야 하고(migration `0026_backfill_bundle_lineitems.py:63-64`의 제자리 UPDATE 방식이 선례), 유지하지 않으려면 3번 명분을 명분 목록에서 내리고 Exclusions에 "번들 매핑 변경의 소급 정리는 하지 않는다 — 고아 행이 남는다"를 명시하라. `test_order_resync.py:255-292`가 현재 동작을 이미 고정하고 있다.
6. **AC-RSW-006을 MySQL에서 판별력을 갖도록 다시 설계하라.** `nulls_first` 누락 변이는 이 DB에서 SQL이 동일하다. 대안: 정렬을 순수 SQL 수준이 아니라 "한 번도 스윕되지 않은 주문이 값이 있는 주문보다 먼저 처리된다"는 **커맨드 실행 결과**(처리 순서/`_sync_single_order` 호출 순서)로 단정하고, DESC·오름차순 양방향 변이를 모두 커버하라.
7. **보존 계열 AC(017–022)의 Given에 "이 주문은 REQ-RSW-003을 만족한다(60일 이내 + `not_shipped` 라인아이템 ≥ 1)"를 명시하고, Then에 "그 주문이 실제로 처리되었다"(`last_resynced_at` 전진 등)를 추가하라.** 특히 AC-RSW-018(`acceptance.md:314`)의 현재 픽스처는 대상 조건을 만족하지 않는다.
8. **AC-RSW-026을 rate 검증으로 강화하라.** "훅 2회 이상"이 아니라 "6회 호출 사이 5개 간격 전부에 대해 페이싱 계산이 수행되고, 인자가 상수 0.5초 기준으로 산출된다"를 단정하라.
9. **AC-RSW-024의 Given에 "`_sync_single_order`는 모킹하지 않는다(HTTP 계층만 모킹)"를 명시하라.**
10. **REQ-RSW-002의 인덱스 근거를 MySQL 기준으로 다시 쓰고, 필요하면 복합 인덱스를 검토하라.** 그리고 `EXPLAIN`(MySQL 8) 결과를 DoD의 통과 조건으로 못 박아, "인덱스가 존재한다"가 아니라 "정렬이 filesort가 아니다"를 검증하라.
11. **REQ-RSW-022의 "동작이 무변경이다"를 "신규 파라미터를 전달하지 않는다"로 축소하고**, 환불/배송라인 동작 변경이 세 기존 호출부 전부에 적용됨을 별도 REQ 또는 §8에 명시하라. `plan.md:499`의 `sync_store()` **무변경** 표기도 "소스 무변경, 동작 변경 있음"으로 정정하라.
12. **REQ-RSW-028을 §8로 이동하고, `spec.md:208`의 REQ-RSW-007 매핑을 AC-RSW-007(또는 011/012)로 정정하라.** 조동사 누락 9건(003/005/006/007/008/009/012/017/023/027)과 REQ-RSW-015의 서술 방향도 함께 정리하라.
13. **REQ-RSW-017을 사실에 맞게 재서술하라** — "명시적 락(`select_for_update`)을 쓰지 않는다"는 참이지만 "어떤 DB 락도 공유하지 않는다"는 거짓이다. `sync_orders.py`가 스토어 전체를 한 트랜잭션으로 감싸는 사실과, D1로 인해 lock-wait 패배가 랩 단위 지연이 된다는 점을 §8에 추가하라.
14. **페이싱 상수는 `repair_refunds.py:36-39`의 선례(0.3초)와 함께 재산정하고**, `sync_store()`/수동 버튼과 버킷을 공유한다는 사실을 A5 또는 §8에 반영하라.
