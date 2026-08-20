# SPEC Review Report: SPEC-ORDER-028

Iteration: 2/3
Verdict: **FAIL**
Overall Score: **0.68** (iteration 1: 0.55)

> M1 Context Isolation: 프롬프트가 전달한 저자의 주장("D1–D21, MP-2 전부 해소")은 **근거로 채택하지 않았다**. 판정은 `.moai/specs/SPEC-ORDER-028/{spec,plan,acceptance}.md` 세 파일의 실제 변경 텍스트와, 이 세션에서 직접 연 저장소 코드·설치된 Django 5.1.6 소스만을 근거로 한다. 프롬프트가 제공한 DB 기능 플래그 4건과 `test_order_resync.py:289`는 재도출하지 않고 기준값으로 사용했다.

---

## Must-Pass Results

- **[PASS] MP-1 REQ 번호 일관성** — `REQ-RSW-001`~`REQ-RSW-034`, 선언 33건(활성) + 결번 1건. 중복 0건, 3자리 zero-padding 일관. **결번 REQ-RSW-028은 침묵의 결번이 아니다**: `spec.md:96`(§5 도입부), `spec.md:258`(추적표 행), `spec.md:297`(§8 C6 이관처) 세 곳에 명시. 인용된 선례도 실재함을 확인 — `.moai/specs/SPEC-ORDER-027/spec.md:69-70` 및 `:125`가 `REQ-RACKRECV-006`을 동일한 방식(폐기 + 결번 + 번호 재부여 금지)으로 처리하고 있다. 문서 순서상 REQ-RSW-027이 034 뒤(`spec.md:222`)에 오는 것은 모듈 배치 결과이며 번호 무결성과 무관하다.
- **[FAIL] MP-2 EARS 형식 준수** — **REQ-RSW-032(`spec.md:209-210`)가 규범적 요구사항이 아니다.**
  - 전문: "배치 컨텍스트 호이스팅(REQ-RSW-021/023)은 주문당 쿼리 수를 약 15개에서 약 13개로 **줄인다** … 이 SPEC은 그 이상의 정량적 쿼리 감소를 **약속하지 않으며**, … 라운드로빈 아키텍처(N=40건씩만 처리) 자체임을 **명시한다**."
  - `shall`/`shall not`이 한 번도 등장하지 않는다. 나머지 32개 활성 REQ는 전부 볼드체 `**shall**`을 포함한다(기계 확인: `grep -c shall spec.md` = 33, 그중 1건은 HISTORY 산문).
  - 내용이 시스템 행동이 아니라 **범위 면책 선언**이다("약속하지 않는다", "임을 명시한다"). 이는 iteration 1이 D12로 지적해 §8 C6으로 퇴출시킨 REQ-RSW-028("검토할 수 있다")과 **정확히 같은 결함 부류**다. 같은 문서가 같은 개정에서 한쪽 번호를 비우고 다른 번호로 같은 결함을 재도입했다.
  - 부수: **REQ-RSW-033(`spec.md:214`)만 `[HARD]` 마커가 없다** — 나머지 32건은 전부 `[HARD]`. 라벨 체계 불일치.
  - 나머지는 개선 확인: 조동사 누락 9건(003/005/006/007/008/009/012/017/023/027) 전부 `shall` 보완됨(`spec.md:108,114,117,122,125,128,131,158,180,222`), REQ-RSW-012는 `(Complex)`로 재라벨링(`:137`), REQ-RSW-015는 시스템 행동 서술로 재작성(`:150-151`).
- **[PASS] MP-3 YAML frontmatter 유효성** — `spec.md:1-11`: `id: SPEC-ORDER-028`(string), `version: 0.2.0`(string), `status: draft`(string), `created_at: 2026-08-19`(ISO date), `priority: High`(string), `labels: [order, shopify, sync, resync, performance, backend]`(array). 전부 존재, 타입 정합.
- **[N/A] MP-4 Section 22 언어 중립성** — 단일 언어(Python/Django) 프로젝트 SPEC. 자동 통과.

**MP-2 단일 실패로 must-pass firewall 발동 → 다른 점수와 무관하게 FAIL.**

---

## Category Scores (rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.70 | 0.50–0.75 | DB 전제(MySQL)는 `spec.md:43`/`:72-73`/`:296`, `plan.md:16`/`:60-78`/`:402-404`에서 전면 정정되어 iteration 1의 최대 혼선이 해소됨. 그러나 §1 문제 정의 3번(`spec.md:30`)이 **자기모순**이다(N1) — 유지한 명분("최초 1회 번들 확장")과 Exclusions #12(`spec.md:283`)가 배제한 대상이 같은 코드 경로다. `spec.md:218` REQ-RSW-034의 근거 사슬도 사실과 다르다(N8) |
| Completeness | 0.70 | 0.50–0.75 | 신규 REQ 6건 + AC 4건 + §8 C7~C10 + 위험 R12~R15로 iteration 1의 커버리지 공백 대부분이 채워짐(`spec.md:194-218`, `:298-301`, `plan.md:649-652`). 그러나 D3의 **비-예외 경로**(빈 값 정상 반환)가 여전히 REQ·AC·위험 어디에도 없고(N2), header-only 환불의 **선존 중복/경합** 상태가 새 설계에서 자가치유되지 않게 된 사실이 없다(N3) |
| Testability | 0.65 | 0.50–0.75 | AC-RSW-026 재설계는 실효적이다(`acceptance.md:484-490` ↔ `plan.md:252-259` 로직 대조 결과 sleep 5회·인자 0.3 단정이 정확). AC-RSW-024의 픽스처 명확화도 유효. 그러나 D8의 "처리됨" 대리 지표가 **실패한 주문에서도 참**이라 보존 계열 AC 전부가 여전히 전면 실패 시나리오에서 공허 통과한다(N4). AC-RSW-006은 "역순" 변이는 잡지만 "정렬 제거" 변이는 픽스처 생성 순서에 따라 통과한다(N5) |
| Traceability | 0.70 | 0.50–0.75 | `spec.md:229-264` 34행 전건을 `acceptance.md` 본문과 대조. D11/D21은 spec.md 쪽에서 정정됨(`:237`, `:251`). 그러나 acceptance.md 쪽이 동기화되지 않아 **새 문서 간 불일치 3건**이 생겼고(N7), AC 번호에 5개의 무설명 결번이 있으며(N9), REQ-RSW-032↔AC-RSW-024 매핑은 `spec.md:266`의 [HARD] 추적표 무결성 규칙 자체를 위반한다(N6) |

---

## Part 1 — Iteration 1 지적사항 개별 종결 판정

| # | 판정 | 근거 |
|---|------|------|
| **D1** (unique_fields → NotSupportedError) | **CLOSED** | 세 문서 전체를 `unique_fields`로 기계 검색한 결과, **코드 스케치에서 인자로 전달하는 곳이 0건**이다. 남은 15건은 전부 금지·설명·검증 지시(`plan.md:427`, `:476`, `:497`, `:581`, `acceptance.md:620`). 대체안의 유효성도 Django 소스로 직접 재검증: `QuerySet._check_bulk_create_options`는 `unique_fields`가 비어 있고 `supports_update_conflicts_with_target=False`일 때 어떤 분기에도 걸리지 않는다(`if unique_fields and not …` → False, `if not unique_fields and db_features.supports_update_conflicts_with_target` → False). `update_fields` 필수 조건도 양쪽 호출부가 충족. **모델별 적합성 개별 검증**: ① `ShippingLine` — `shopify_shipping_line_id = models.BigIntegerField()`(`models.py:312`, **non-nullable 확인**), unique_together `("order","shopify_shipping_line_id")`(`:320`) → NULL 매칭 문제 없음. `plan.md:500`의 주장 및 인용 라인 정확. ② `Refund` — unique_together `("order","shopify_refund_id","line_item_id")`(`models.py:342`), `line_item_id`는 nullable(`:328`). 플랜이 NULL 행을 bulk 목록에서 **사전 배제**하므로(`plan.md:453-459`) bulk에 들어가는 모든 행의 복합 키는 non-null → `ON DUPLICATE KEY UPDATE`가 정확히 그 유니크 키로만 충돌 판정. pk는 `objs_without_pk` 경로에서 INSERT 컬럼에서 제외되므로 PK 충돌 오발동 없음. `created_at = auto_now_add`(`models.py:332`)는 `update_fields`에 없어 보존됨 |
| **D2** (header-only 환불 무한증식) | **PARTIAL** | 프롬프트가 지정한 두 종결 시나리오는 **실제로 종결된다**: ① 한 주문에 header-only 환불이 **여러 건**인 경우 — `shopify_orders.py:314`의 `or [{}]`는 refund 하나당 최대 1개의 `{}`만 만들고, `plan.md:486-492`의 `update_or_create(order, shopify_refund_id=<각각>, line_item_id=None)`은 refund_id로 분리되므로 각 refund가 정확히 1행으로 수렴한다. ② **전이 케이스** — 저장된 `(R, NULL)`이 다음 페이로드에서 `(R, 5)`가 되면 `incoming_refund_keys={(R,5)}`이므로 `plan.md:464-470`의 튜플 비교가 `(R, NULL)`을 stale로 판정해 삭제하고 새 행을 upsert한다. 역방향(`(R,5)` → `(R, NULL)`)도 대칭적으로 성립. 그러나 **자가치유 상실이라는 새 결함**이 생겼다 → **N3** |
| **D3** (fulfillment 실패 시 위치 소거) | **PARTIAL** | 프롬프트가 우려한 "부분 쓰기"는 **발생하지 않는다** — `plan.md:276-289`에서 `_build_fulfillment_location_data(..., raise_on_error=True)`가 `_sync_single_order()` **호출 이전**에 실행되므로, 예외 발생 시 `shopify_orders.py:165`(Order.location)와 `:242`(LineItem.location) 어느 쪽에도 도달하지 않는다. 두 값이 분리 처리되지 않고 하나의 선행 호출에서 함께 나오므로 부분 쓰기 경로가 구조적으로 없다. 기존 3개 호출부 무영향도 확인 — `plan.md:335-354`의 기본값 `raise_on_error=False`가 `test_order_location.py:79-88`의 계약을 그대로 보존한다. **그러나 예외가 아닌 경로로 같은 사고가 그대로 재현된다** → **N2** |
| **D4** (번들 고아 행) | **NOT CLOSED** | 배제가 정직하지도 완전하지도 않다 → **N1**. 저자가 선택한 "명분 축소"가 **고아를 만드는 바로 그 케이스를 명분으로 유지**했다 |
| **D5** (AC-006 판별력 0) | **PARTIAL** | 재설계는 정직하고 방향이 옳다(`acceptance.md:136`이 "`nulls_first` 파라미터 자체를 겨냥한 판별은 이 DB에서 성립하지 않는다"고 명시). DESC 변이 판별도 성립. 그러나 "정렬 제거" 변이 미커버 → **N5** |
| **D6** (인덱스 근거) | **CLOSED** | `plan.md:60-78`이 MySQL 기준으로 전면 재작성됨. 복합 인덱스 `(last_resynced_at, shopify_created_at)`(`plan.md:33`, `:50-56`), "이것은 옵티마이저의 선택이지 보장이 아니다"(`:66`)라는 정직한 한정, `EXPLAIN` DoD(`:66-76`, `acceptance.md:624`), filesort 발생 시 대안 2안(`plan.md:76`)까지 갖춤. `models.py:99`의 기존 `shopify_created_at` 인덱스 인용 정확 |
| **D7** ("동작 무변경" 거짓) | **CLOSED** | REQ-RSW-022가 "신규 배치 컨텍스트 파라미터를 전달하지 않는다"로 축소(`spec.md:177-178`), §8 C7 신설(`:298`), Exclusions #8에 단서 추가(`:279`), `plan.md:625-627`의 `[EXISTING]` 3행이 전부 "**소스 코드 무변경.** 단, … 런타임 동작에도 적용된다"로 정정됨 |
| **D8** (보존 AC 공허 통과) | **PARTIAL** | `_make_qualifying_order()` 헬퍼 규약 신설(`acceptance.md:46`)과 017/018/019/020 픽스처 정정은 실효적이다. 그러나 선택한 "처리됨" 증거가 실패를 성공과 구분하지 못한다 → **N4**. AC-RSW-018은 자체 판별력 문단이 자기모순 → **N4b** |
| **D9** (AC-026 rate 미검증) | **CLOSED** | `acceptance.md:484-490`을 `plan.md:252-259`의 `_pace()` 구현과 직접 대조: `last_call_at is None`인 첫 호출만 sleep 없음 → 3주문×2호출=6개 페이싱 지점 중 5회 sleep. `time.monotonic` 고정 시 `elapsed=0` → `sleep(0.3-0=0.3)`. **산술과 구현이 정확히 일치**. 0.05초 변이·주문당 1회 변이 모두 판별됨 |
| **D10** (성능 목표 반증 불가) | **PARTIAL** | REQ-RSW-032가 신설되었으나 규범성이 없고(MP-2) 수치도 검증되지 않는다 → **N6** |
| **D11** (REQ-007 오매핑) | **CLOSED(spec.md) / 잔존(acceptance.md)** | `spec.md:237`은 `AC-RSW-007, AC-RSW-011, AC-RSW-012`로 정정됨. 그러나 `acceptance.md:58`이 여전히 "Traces: REQ-RSW-003, **REQ-RSW-007**"을 선언 → **N7** |
| **D12** (REQ-028 비규범) | **NOT CLOSED (동일 결함 재발)** | 번호는 비웠으나 **같은 결함이 REQ-RSW-032로 재도입**됨(MP-2 참조). 이는 "문제의 이름을 바꾼" 사례이며 stagnation 신호로 기록한다 |
| **D13** (락 서술 거짓) | **CLOSED** | REQ-RSW-017이 "명시적 애플리케이션 레벨 락(`select_for_update()` 등)"으로 축소(`spec.md:158-159`), §8 C8 신설(`:299`), R15 신설(`plan.md:652`). 인용 검증: `sync_orders.py:60`은 실제로 `with transaction.atomic():`이다(직접 확인, 라인 정확) |
| **D14** (0.5초 여유 0) | **CLOSED** | 상수 0.3초로 재산정(`spec.md:146`, `plan.md:187`). **인용 정확도 확인**: `repair_refunds.py:36-39`는 실제로 `"--sleep"`(36) / `type=float`(37) / `default=0.3`(38) / `help="… (default: 0.3, respects the REST rate limit)"`(39)이다 — 인용이 주장을 정확히 뒷받침한다. 페이싱을 "최선 노력 부하 경감"으로 재정의(`spec.md:74`, `:146`, `:293`)한 것도 정직하다 |
| **D15** (사이클 산정 누락) | **CLOSED** | `plan.md:643`/`:526`: 80회×0.3초=24초 ✓, 40×2초=80초 ✓, 합계 ~104초 + 네트워크 → "약 2~3분" — **SPEC 자신의 수치로부터 산술이 따라 나온다**. (참고: 실제로는 주문 간 DB 시간이 이미 0.3초를 초과해 페이싱 sleep이 거의 발동하지 않으므로 24초는 과대 추정이다. 보수적 방향이라 결함 아님) |
| **D16** (AC-024 픽스처 미정의) | **CLOSED** | `acceptance.md:450`이 "HTTP 계층만 모킹하고 `_sync_single_order`는 모킹하지 않는다"를 명시하고, 그 이유("0회 대 0회로 위장 통과")까지 적었다. `models.py:556` = `db_table = "order_shopify_sku_set_mapping"` 인용 정확(직접 확인) |
| **D17** (부분 입고) | **CLOSED(사실 확정) / 근거 오류** | REQ-RSW-033(`spec.md:215`) + AC-RSW-033(`acceptance.md:496-507`), REQ-RSW-034 + AC-RSW-034 신설. 필드명 전건 실재 확인: `rack_number`(`models.py:189`), `confirmed_price`(`:195`), `confirmed_distributor`(`:196`), `confirmed_at`(`:197`), `received_quantity`(`:228`), `damaged_quantity`(`:238`), `original_sku`(`:247`). §8 C10(`spec.md:301`)의 stale-삭제 잔여 위험 명시도 정직하다. 다만 REQ-RSW-034의 **근거 사슬이 틀렸다** → **N8** |
| **D18** (local.py:11 인용) | **CLOSED** | SQLite 관련 서술이 전부 삭제되고 `spec.md:43`/`:296`이 MySQL 단일 전제로 통일됨 |
| **D19** (가정 A4 PostgreSQL) | **CLOSED** | `spec.md:72`(A4) + `:73`(A4a 신규)로 MySQL 네이티브 동작 기준 재작성. A4a의 "바이트 단위 동일 SQL" 서술은 프롬프트가 제공한 기준값(`order_by_nulls_first=True`, `supports_order_by_nulls_modifier=False`)과 정합 |
| **D20** (요구사항의 구현 기법) | **PARTIAL** | 004(`spec.md:112`)·010(`:132`)·021(`:175`)은 결과 중심으로 재작성되고 기법이 `plan.md`로 이동함. 그러나 REQ-RSW-024/025는 여전히 매칭 키와 `models.py` 라인을 명시하고(`:186`, `:189`), REQ-RSW-029는 `update_or_create(..., line_item_id=None, ...)`을 예시로 박아 넣었다(`:195`). 요구사항 층에 남은 기법 잔재. 심각도 낮음(정확성에는 영향 없음) |
| **D21** (REQ-021 문서 간 불일치) | **CLOSED / 새 불일치 발생** | `spec.md:251`이 `AC-RSW-024, AC-RSW-025`로 정정되어 `acceptance.md:447`/`:462`와 일치. 그러나 다른 쌍에서 같은 부류의 불일치가 새로 생김 → **N7** |

**요약: CLOSED 12 / PARTIAL 6 / NOT CLOSED 2 (D4, D12).**

---

## Part 2 — Defects Found (신규·잔존, 심각도 순)

### CRITICAL

**N1 (D4 NOT CLOSED). 축소된 명분이 고아 행을 만드는 바로 그 케이스다 — 배제와 명분이 서로를 부정한다.**

`spec.md:30`이 유지한 문제 정의 3번의 헤드라인: "**도서 제목 전파와, 아직 한 번도 확장되지 않은 번들의 최초 전개는 기존 주문에 반영되지 않는다**"(= 스위프가 닫는 갭). 배제한 것은 "번들 매핑이 **사후 변경(멤버 추가/제거)**되는 경우"뿐이다(같은 줄, Exclusions #12 `spec.md:283`, REQ-RSW-031 `spec.md:205`).

그런데 "아직 한 번도 확장되지 않은 번들의 최초 전개"가 **정확히 고아를 만드는 케이스**다. 코드로 추적:
- 기존 주문의 LineItem 1행이 `sku=bundle_sku`, `shopify_line_item_id=5001`로 저장되어 있다(매핑이 나중에 추가되었으므로 확장된 적 없음).
- 스위프가 재동기화하면 `bundle_map.get(li.get("sku"))`가 Shopify 페이로드의 `sku=bundle_sku`로 멤버를 찾아 번들 분기에 진입한다(`shopify_orders.py:244-245`).
- 각 멤버에 대해 `LineItem.objects.update_or_create(order, shopify_line_item_id=5001, sku=member_isbn, …)` — **`sku`가 조회 키**이므로(`:265-269`) 기존 `sku=bundle_sku` 행에는 매치되지 않고 **새 행 N개가 생성**된다.
- stale 삭제는 `exclude(shopify_line_item_id__in=incoming_shopify_ids)`(`:287-289`)이고 `5001`은 incoming에 있으므로 원본 행은 **삭제되지 않는다**.
- 결과: `sku=bundle_sku` 1행 + 멤버 N행이 **모두 전량(미분할) 수량**(`:246-249` 주석)을 들고 공존.

이것이 정확히 migration `0026_backfill_bundle_lineitems.py`가 존재하는 이유다. 그 마이그레이션은 **최초 전개**를 수행하면서 첫 멤버에 대해 원본 행을 **제자리 UPDATE**했다(`:63` `li.sku = first_isbn`, `:64` `li.save(update_fields=["sku"])`, 직접 확인 — 라인 정확). 헤더 주석 `:9-16`이 그 방식을 명시적으로 설명한다. 즉 저장소는 "`update_or_create(sku=member_isbn)`로 최초 전개를 하면 원본 행이 고아가 된다"는 사실을 이미 알고 우회했고, SPEC-ORDER-028은 그 우회 없이 같은 전개를 **자동/랩당 1회**로 실행하겠다고 명분에 남겨두었다.

추가로, 배제 문구 자체가 명분과 **논리적으로 모순**된다: 없던 번들 매핑을 새로 만드는 것은 "멤버 추가"이므로 Exclusions #12의 배제 대상에 포함된다. 같은 문장(`spec.md:30`)이 같은 행위를 한쪽에서는 SPEC의 명분으로, 다른 쪽에서는 배제 대상으로 규정한다(CN-1, CN-2 위반).

§8 C9(`spec.md:300`)가 잔여 위험을 서술하긴 하나, 그 서술도 "번들 매핑이 **사후 변경된** 기존 주문"으로 한정되어 최초 전개 케이스를 덮지 못한다. REQ-RSW-031의 DoD(`spec.md:261`)가 무수정 통과를 요구하는 `test_order_resync.py::test_resync_after_mapping_change_reexpands_with_current_mapping_orphans_removed_member`는 **이미 확장된 주문의 매핑 변경**만 고정한다(`:289` `skus == {"ISBN-A","ISBN-B","ISBN-C"}` — 기준값으로 확인). 최초 전개 케이스를 고정하는 테스트도 AC도 없다.

**종결 조건**: 다음 중 하나. (a) `spec.md:30`의 명분에서 "아직 한 번도 확장되지 않은 번들의 최초 전개"를 **삭제**하고 Exclusions #12·§8 C9를 "번들 매핑 유무 변경 전반(최초 전개 포함)"으로 확장한다. (b) 명분을 유지하려면 migration `0026:63-64`의 제자리 UPDATE 선례를 따르는 REQ + AC(최초 전개 후 `LineItem.objects.filter(order=…, shopify_line_item_id=5001).count() == N`, `sku=bundle_sku` 행 부재)를 신설한다. 어느 쪽이든 §8 C9의 잔여 위험 서술을 최초 전개까지 포괄하도록 다시 써야 한다.

**N2 (D3 PARTIAL). `raise_on_error`는 예외만 막는다 — 위치 소거의 나머지 절반은 그대로 열려 있고, 이 SPEC이 그 노출을 스스로 키운다.**

`_build_fulfillment_location_data()`는 **예외가 아닌 정상 경로에서도** `("", …)`를 반환한다. 이는 가설이 아니라 저장소가 테스트로 고정한 동작이다:
- `backend/order/tests/test_order_location.py:62` `test_build_fulfillment_location_handles_names_without_underscore` → `assert loc == ""`, `assert line_map == {1001: ""}`(직접 확인). `assigned_location.name`에 `_` 구분자가 없으면 `parts[1] if len(parts) > 1 else ""`(`shopify_orders.py:88-89`)가 빈 코드를 낸다.
- `fulfillment_orders`가 빈 배열이면 `seen`이 비어 `"/".join([]) == ""`.

이 경우 예외가 없으므로 `raise_on_error=True`는 아무 것도 하지 않고, `plan.md:281-289`가 `location_code=""`, `line_item_location_map={}` 또는 `{id: ""}`를 그대로 `_sync_single_order()`에 넘긴다. 그러면 `shopify_orders.py:165`가 `Order.location`을 `""`로, `:242`가 각 `LineItem.location`을 `""`로 덮어쓴다. 이 쓰기 동작도 테스트로 고정되어 있다(`test_order_location.py:160` `test_sync_sets_empty_location_when_no_location_code`, `:187` `test_sync_sets_empty_line_item_location_when_no_map`).

이것은 D3와 **같은 사고(운영자 신호 없는 NJ/CA 라우팅 값 전면 소거)**이며, 이 SPEC이 새로 만드는 노출이다 — `sync_store()`는 기존 주문에 대해 저장값을 재사용하고 이 경로를 아예 타지 않기 때문이다(`shopify_orders.py:422-425`, 직접 확인: `if shopify_id in existing_order_locations: order_location = existing_order_locations[shopify_id] or ""`). REQ-RSW-013(`spec.md:142-143`)이 그 보호막을 제거하고, REQ-RSW-015(`:150-151`)가 스위프를 **종료·취소·편집된 주문**(fulfillment order가 비어 있거나 위치 배정이 사라졌을 가능성이 가장 높은 주문군)에 도달하게 만든다.

REQ-RSW-030(`spec.md:199-200`)은 "**호출이 실패하면**"으로만 조건을 걸어 이 경로를 덮지 못한다. AC-RSW-014b(`acceptance.md:272-283`)도 예외 모킹만 검증한다. 위험표에도 없다(R13은 예외 케이스 전용, `plan.md:650`).

**종결 조건**: REQ에 "조회는 성공했으나 위치 코드가 비어 있는 경우"의 정책을 명문화하라 — 권장은 "빈 결과는 기존 저장값을 덮어쓰지 않는다"(방어) 또는 최소한 "덮어쓴다"를 의도된 동작으로 **명시적으로 선언**하고 §8 잔여 위험에 넣는 것. 그리고 AC를 추가하라: `fulfillment_orders: []`(또는 `assigned_location.name`에 `_` 없음)를 반환하는 정상 응답을 모킹 → 스위프 후 `Order.location == "NJ"`(또는 선언된 정책대로 `""`) 단정.

### MAJOR

**N3 (D2 잔여). 차등 갱신이 header-only 환불의 자가치유를 없애고, 선존 중복 상태에서 그 주문을 영구히 실패시킨다.**

`Refund`의 유니크 제약은 NULL을 포함하므로 `(order, refund_id, NULL)` **중복 행을 DB가 막지 못한다**(`models.py:342` + 표준 SQL NULL 규칙, 이 SPEC의 가정 A8 `spec.md:77`이 스스로 인정하는 사실).

- **현행 코드**: `order_obj.refunds.all().delete()`(`shopify_orders.py:306`) → `update_or_create`. 어떤 경위로 중복이 생겼든 **다음 동기화 1회로 자동 정리**된다.
- **제안안**: `.all().delete()`가 사라지고, stale 판정은 `(refund_id, line_item_id) not in incoming_refund_keys`(`plan.md:464-468`)뿐이다. 중복된 두 행 모두 `(R, None)`이고 그 키가 incoming에 있으면 **둘 다 삭제되지 않는다**. 이어지는 `Refund.objects.update_or_create(order=…, shopify_refund_id=R, line_item_id=None, …)`(`plan.md:487-492`)는 내부적으로 `.get()`을 호출하므로 `MultipleObjectsReturned`를 던진다 → 그 주문은 매 랩 실패하고, 자가치유 경로가 없으므로 **영구 고착**된다.

중복이 실제로 발생할 수 있는가: (a) 이 저장소에는 환불 행 손상 복구용 `backend/order/management/commands/repair_refunds.py`가 이미 존재한다(migration 0038 이전 결함) — 이력 데이터가 깨끗하다고 가정할 근거가 없다. (b) 더 확실한 경로: `spec.md:299`(§8 C8)가 스스로 인정하듯 스위프와 `sync_store()`/수동 재동기화가 **같은 행을 동시에** 건드릴 수 있다. `update_or_create`는 원자적이지 않고 NULL 열에는 유니크 제약이 걸리지 않으므로, 두 프로세스의 `.get()`이 모두 실패하면 **양쪽이 각각 INSERT**해 중복이 생긴다. 현행 코드는 다음 동기화에서 이를 지우지만, 제안안은 지우지 못하고 그 시점부터 실패한다.

이는 REQ-RSW-026(`spec.md:191-192`, "최종 상태는 기존 delete-and-recreate 방식과 동일해야 한다")의 직접 위반이다 — 중복이 존재하는 상태에서 두 방식의 최종 상태가 다르다. AC-RSW-029(`acceptance.md:428-439`)는 깨끗한 초기 상태만 다루므로 잡지 못한다.

**종결 조건**: NULL 경로를 `update_or_create` 대신 "해당 키의 **모든** 행을 정리하고 정확히 1행을 보장"하는 형태로 명세하라(예: `filter(order=…, shopify_refund_id=R, line_item_id__isnull=True)`에서 첫 행만 남기고 나머지 삭제 후 갱신). 그리고 AC를 추가하라: Given에 `(order, R, NULL)` 행을 **2건 미리 삽입** → When 스위프 1회 → Then `count() == 1` **이고 그 주문이 실패로 집계되지 않는다**.

**N4 (D8 잔여). "처리됨"의 증거로 채택한 `last_resynced_at` 전진은 실패한 주문에서도 참이다 — 보존 계열 AC 전체가 여전히 전면 실패 시나리오에서 공허 통과한다.**

`acceptance.md:47`이 [HARD]로 규정한 종결 장치: "모든 AC의 Then은 최소한 그 주문의 `last_resynced_at`이 `None`이 아님을 단정한다 — 이것이 그 주문이 실제로 처리 시도되었다는 관측 가능한 증거다."

그러나 `plan.md:294-298`의 `finally` 블록은 **성공·실패·위치조회실패 세 경로 모두**에서 `last_resynced_at`을 전진시킨다(설계 결정 D1, 의도된 동작). 따라서 `last_resynced_at is not None`은 "선택되었다"의 증거일 뿐 "성공했다"의 증거가 아니다. 문서 자신도 `acceptance.md:47`에서 "처리 **시도**되었다"라고 정확히 쓰고 있으면서, `acceptance.md:5`·`:332`·`spec.md:20`에서는 이를 D8의 해소책으로 제시한다.

구체적 실패 모드: 어떤 변이가 스위프의 모든 주문을 예외로 실패시키면(예: N3의 `MultipleObjectsReturned`, 또는 `unique_fields` 재도입 시 `NotSupportedError`), `_sync_single_order()`가 한 번도 커밋되지 않으므로 AC-RSW-017/018/019/020/034의 "무변경" 단정이 **전부 통과**하고 `last_resynced_at` 단정도 통과한다. 판별력 0.

또한 `acceptance.md:47`의 [HARD] 규약을 **자기 문서가 8개 AC에서 지키지 않는다**: AC-RSW-013(`:251`), 014(`:266`), 021(`:392`), 022(`:407`), 023(`:422`), 024(`:454`), 026(`:488`), 029(`:437`)의 Then에 `last_resynced_at` 단정이 없다. 이 중 AC-RSW-021은 [핵심] 단독 판별자이면서 순수 보존형("환불 행이 여전히 존재하며 quantity==2")이라 같은 공허 통과 위험을 갖는다.

**N4b (동일 계열).** AC-RSW-018(`acceptance.md:347`)의 판별력 문단은 자기모순이다: "…규약이 깨지면 이 필드가 Shopify 응답에 없는 필드이므로 `update_or_create`가 **기존 값을 그대로 두는지**를 확인한다." 규약이 깨져 `logistics_status`가 `common_defaults`에 들어가면 값은 `li.get("logistics_status")` = `None`이 되고, `LineItem.logistics_status`는 `CharField(choices, default="not_shipped")` **non-nullable**(`models.py:~205`)이므로 `IntegrityError` → per-order 트랜잭션 롤백 → 필드는 원래 값 유지 → **"무변경" 단정 통과**, `last_resynced_at`도 `finally`로 전진 → **통과**. 즉 AC-RSW-018은 자신이 선언한 변이 M13을 잡지 못한다.

**종결 조건**: 보존 계열 AC(017/018/019/020/021/034)의 Then에 **성공 증거**를 추가하라 — 둘 중 하나로 충분하다. (a) `resync_order_sweep`이 `CommandError` 없이 종료했다(= 실패 0건), 또는 (b) 같은 실행에서 Shopify가 실제로 바꾼 값이 반영되었다(예: AC-018의 Given이 이미 "`title` 변경만 포함"이라고 적었으므로 Then에 `LineItem.title == <새 값>`을 추가하면 즉시 성공 증거가 된다). 그리고 `acceptance.md:47`의 [HARD] 문구를 실제 준수 상태에 맞게 고치거나, 미준수 8건에 단정을 추가하라.

**N5 (D5 잔여). AC-RSW-006의 픽스처는 "정렬 역전"은 잡지만 "정렬 제거"는 픽스처 생성 순서에 따라 통과한다.**

`acceptance.md:138-144`: G(`None`), F(-2시간), E(-10분) 생성 → `--count 2` → `{G, F}` 기대.
- DESC 변이: MySQL DESC는 NULL을 뒤로 보내므로 처리 대상 = {E, F} ≠ {G, F} → **잡힘** ✓
- `order_by(...)` 자체를 삭제한 변이: MySQL은 순서를 보장하지 않으나 실무상 PK/삽입 순서로 반환되는 경우가 흔하다. AC가 픽스처를 G → F → E 순으로 **원하는 처리 순서와 같게** 생성하면 상위 2건이 그대로 {G, F}가 되어 **통과**한다. `acceptance.md:20`이 M4를 AC-006 **단독** 판별자로 지정했으므로, 이 변이는 SPEC 전체에서 미커버가 된다.

**종결 조건**: Given의 픽스처 **생성 순서를 기대 처리 순서와 다르게** 고정하라(예: "E → F → G 순으로 생성한다 — 삽입 순서와 기대 처리 순서가 일치하지 않도록 의도적으로 뒤집는다"). 한 줄 추가로 "정렬 제거" 변이까지 커버된다.

**N6 (D10 잔여). REQ-RSW-032는 규범성도 검증 수단도 없다 — `spec.md:266`의 [HARD] 추적표 무결성 규칙을 그 문서가 스스로 위반한다.**

- 규범성: MP-2 참조(`shall` 없음, 범위 면책 선언).
- 검증: `spec.md:262`가 "REQ-RSW-032 | AC-RSW-024(대표 — **쿼리 수 감소분 검증**)"로 매핑했으나, AC-RSW-024(`acceptance.md:445-456`)의 Then은 "`ShopifySkuSetMapping`에 대한 SELECT가 정확히 1회"뿐이다. **"약 15개 → 약 13개"를 검증하는 단정이 없다.** `spec.md:266`의 [HARD] 규칙("REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다")에 따라 REQ-RSW-032는 미커버다.
- 수치 자체도 틀렸을 가능성이 높다: `_build_title_map()`은 `if not isbn_list: return {}`(`shopify_orders.py:62-63`)로 **쿼리 없이 반환**한다. 번들 SKU가 없는 주문(다수)은 오늘도 제목 조회 쿼리를 실행하지 않으므로, 호이스팅이 제거하는 쿼리는 2개가 아니라 **1개**다. 즉 그런 주문에서는 "약 15 → 약 14"다. 반대로 `_load_batch_invariant_context()`(`plan.md:190-208`)는 사이클마다 **전체 멤버 ISBN**에 대해 `_build_title_map`을 1회 실행하므로, 번들이 전혀 없는 배치에서는 없던 쿼리가 추가된다.

**종결 조건**: (a) REQ-RSW-032를 §7 Exclusions 또는 §8(범위 면책은 요구사항이 아니다)로 이동하고, 남길 성능 요구가 있다면 `shall`을 갖춘 검증 가능한 형태로 다시 쓴다(예: "THE 시스템은 한 스위프 사이클에서 `ShopifySkuSetMapping` 조회를 1회만 **shall** 실행한다" — 이건 AC-024가 실제로 검증한다). (b) "15 → 13" 수치를 유지하려면 `_build_title_map`의 조기 반환을 반영해 재산정하고, 그 수치를 검증하는 쿼리 카운트 AC를 만들거나 `spec.md:262`의 "(대표 — 쿼리 수 감소분 검증)" 표기를 삭제한다.

### MEDIUM

**N7. 개정 과정에서 문서 간 추적 불일치가 새로 3건 생겼다(D21과 동일 부류의 재발).**
- `spec.md:237`은 REQ-RSW-007 → `AC-007/011/012`로 정정했으나, `acceptance.md:58`은 여전히 "Traces: REQ-RSW-003, **REQ-RSW-007**(대표 …)"를 선언한다. spec.md는 더 이상 그 매핑을 인정하지 않는다.
- `spec.md:255`가 REQ-RSW-025 → `AC-021, AC-022, **AC-029**`로 매핑하나, `acceptance.md:430`의 AC-RSW-029는 "Traces: REQ-RSW-029"만 선언한다.
- `spec.md:256`이 REQ-RSW-026 → `AC-021, AC-023, **AC-029**`로 매핑하나, 같은 이유로 AC-RSW-029 쪽에 대응 선언이 없다.

**N8. REQ-RSW-034의 보존 근거가 사실과 다르다.**
`spec.md:218`: "…비-Shopify 소스 필드(`received_quantity`, … `original_sku`)의 값은 **REQ-RSW-018/019가 이미 보장하는 필드 제외 규약에 의해** shall 보존된다."
- REQ-RSW-018(`:163-164`)이 상속한다고 선언한 제외 규약은 `Order.status`/`Order.ready_to_ship`/`LineItem.purchase_status`/`LineItem.logistics_status` 4개뿐이다(`shopify_orders.py:140-147`, `:229-230`).
- REQ-RSW-019(`:166-167`)는 `original_sku` **보호 로직**(`protected_sku_by_key`)에 관한 것이지 필드 제외가 아니다.
- `received_quantity`/`received_at`/`shipped_quantity`/`shipped_at`/`rack_number`/`damaged_quantity`/`confirmed_*`가 보존되는 진짜 이유는 그저 **`common_defaults`(`shopify_orders.py:231-243`)에 들어 있지 않기 때문**이며, 어떤 명시적 규약도 그것을 보증하지 않는다. 요구사항 자체는 AC-RSW-034로 검증 가능하므로 실질 위험은 낮으나, 근거 문장이 존재하지 않는 보증을 인용한다.

**N9. AC 번호에 무설명 결번 5개(027/028/030/031/032)가 있고, 세 문서가 "AC-RSW-001~034"라고 적어 34개 연속인 것처럼 오도한다.**
- 실재 AC: 001–026(26) + 014b + 029 + 033 + 034 = **30개**. 기계 확인: `AC-RSW-027|028|030|031|032` 참조 **0건**(세 문서 전체 grep).
- 그런데 `acceptance.md:3`, `plan.md:622`, `plan.md:718`은 "AC-RSW-001~034"라고 쓴다. REQ-RSW-028의 결번은 세 곳에 명시했으면서(MP-1 참조) AC 결번은 어디에도 설명이 없다.
- 부수 불일치: 번호 체계가 혼재한다 — AC-029/033/034는 대응 REQ 번호를 미러링하는데, REQ-RSW-030의 AC만 `AC-RSW-014b`다.
- 부수: AC-RSW-033은 When이 `_qualifying_orders_queryset()` 평가(대상 판정)인데 `plan.md:590`이 이를 커맨드 마일스톤 M6에 배정했다 — 쿼리 마일스톤 M2가 맞다.

**N10. REQ-RSW-006이 규정한 기본값 40을 검증하는 AC가 없다.**
`spec.md:117-118`: "N의 기본값은 40이다." 추적표(`spec.md:236`)는 REQ-RSW-006 → AC-RSW-007로 매핑하나, AC-RSW-007(`acceptance.md:150-161`)은 `--count 2`를 **명시적으로 전달**한다. 기본값을 40에서 다른 값으로 바꾸는 변이는 어떤 AC에도 걸리지 않는다. `spec.md:266`의 [HARD] 규칙상 이 부분은 미커버다. (`plan.md:182` `DEFAULT_COUNT = 40`은 존재하나 DoD 검사도 없다.)

### MINOR

**N11. REQ-RSW-033만 `[HARD]` 마커가 없다**(`spec.md:214`) — 나머지 32개 활성 REQ는 전부 `[HARD]`. 의도적이라면(정보성 확정) 그 사실을 명시하고, 아니라면 통일할 것.

**N12. 요구사항 층에 구현 기법이 일부 남아 있다(D20 잔여).** REQ-RSW-024/025가 매칭 키와 `models.py:320`/`:342` 라인을 지정하고(`spec.md:186`, `:189`), REQ-RSW-029가 `update_or_create(..., line_item_id=None, ...)`을 예시로 명시한다(`:195`). 정확성에는 문제가 없으나 RQ-3/RQ-4 관점의 잔재.

**N13. `plan.md`의 사이클 산정은 보수적으로 과대 추정이다(결함 아님, 기록용).** `_pace()`는 마지막 API 호출 이후의 실제 경과 시간을 재므로(`plan.md:252-259`), 주문 사이의 약 2초 DB 시간이 이미 0.3초를 넘어 40개의 주문 간 페이싱 지점 중 대부분은 sleep 0초가 된다. 실제 페이싱 비용은 약 12초(주문 내 40회분)이며 24초가 아니다. "약 2~3분"이라는 결론은 안전한 방향이므로 유지해도 무방하다. AC-RSW-026은 `time.monotonic`을 고정 모킹한다고 Given에 적었으므로(`acceptance.md:484`) 이 사실과 충돌하지 않는다.

---

## Part 3 — 판별력 재점검 (감사 우선순위 4)

| 위험 영역 | 판별 AC 존재? | 판정 |
|---|---|---|
| 위치가 갱신되지 않는다 | AC-RSW-014(`acceptance.md:257-268`) | **충분** — NJ→CA 픽스처, 단축 경로 이식 변이를 직접 잡는다 |
| 위치가 조용히 지워진다(예외) | AC-RSW-014b(`:272-283`) | **충분** — `raise_on_error` 미전달 변이를 `"" ≠ "NJ"`로 잡는다 |
| 위치가 조용히 지워진다(정상 빈 응답) | **없음** | **미커버 — N2** |
| `last_resynced_at`이 전진하지 않는다 | AC-RSW-008(성공), AC-RSW-009(예외) | **충분** — `finally` 배치를 구조적으로 강제 |
| 워터마크가 전진한다 | AC-RSW-013(`:242-253`) | **충분** — T1/T2 불변 단정 |
| 수동 값이 되돌려진다 | AC-RSW-017/018/019/020 | **부족 — N4/N4b** — 픽스처는 고쳤으나 성공 증거가 없어 전면 실패 시 공허 통과 |
| 환불 행 유실 | AC-RSW-021(`:383-394`) | **부족** — 판별은 성립하나 성공 증거 없음(N4) |
| 환불 행 중복(header-only, 깨끗한 초기 상태) | AC-RSW-029(`:428-439`) | **충분** — 2회 연속 실행 후 `count()==1` |
| 환불 행 중복(선존 중복/경합 상태) | **없음** | **미커버 — N3** |
| 환불/배송라인 stale 미삭제 | AC-RSW-022, AC-RSW-023 | **충분** |
| 라운드로빈 순서 역전 | AC-RSW-006 | **부분** — 역전은 잡고 정렬 제거는 못 잡음(N5) |
| 부분 입고 주문 배제 | AC-RSW-033(`:496-507`) | **충분**(회귀 방지 목적) — `logistics_status` 조건에 `received_quantity=0`을 덧붙이는 변이를 잡는다 |
| 부분 입고 필드 소실 | AC-RSW-034(`:511-522`) | **부분** — 필드 목록은 실재 확인됨. 단, 성공 증거 부재(N4) + `§8 C10`의 stale-삭제 손실 경로는 의도적 미커버(정직하게 선언됨) |
| 페이싱 rate 저하 | AC-RSW-026(`:477-490`) | **충분** — `plan.md:252-259`와 대조해 sleep 5회·인자 0.3 산술 일치 확인 |
| 배치 컨텍스트 재계산 | AC-RSW-024(`:445-456`) | **충분** — `_sync_single_order` 미모킹 명시로 M17 판별 복구 |
| `--count` 기본값 40 | **없음** | **미커버 — N10** |

---

## Chain-of-Verification Pass

1차 판정 후 재점검한 항목과 그 결과:

- **저자의 "전부 해소" 주장을 어디서든 근거로 썼는가** → 21건 전부에 대해 변경된 실제 텍스트를 열어 대조했고, HISTORY 산문(`spec.md:20`)은 근거로 채택하지 않았다. 그 결과 D4·D12를 NOT CLOSED로, 6건을 PARTIAL로 강등했다.
- **D1을 "unique_fields가 사라졌다"로 끝내지 않았는가** → 세 문서를 기계 검색해 코드 스케치에서의 전달 0건을 확인한 뒤, **모델 두 개에 대해 대체안의 정확성을 따로 검증**했다(`models.py:312/320/328/332/342`). 이 과정에서 `Refund.created_at`이 `auto_now_add`이고 `update_fields`에 없어 보존된다는 점, pk가 INSERT 컬럼에서 제외되어 PK 충돌이 오발동하지 않는다는 점을 확인했다. Django 소스는 `_check_bulk_create_options`를 직접 출력해 대조했다.
- **D3을 "예외가 먼저 던져지니 안전"으로 끝내지 않았는가** → 프롬프트의 부분 쓰기 우려는 실제로 성립하지 않음을 코드 순서로 확인했으나(`plan.md:276-289`), 그 과정에서 **예외가 아닌 빈 값 경로**를 발견했다. 결정적 근거는 SPEC이 인용하지 않은 인접 테스트였다 — `test_order_location.py:62`(underscore 없음 → `loc == ""`)와 `:160`/`:187`(빈 값이 실제로 기록됨). N2는 이 두 테스트가 없었다면 추측에 그쳤을 것이다.
- **D2를 "두 시나리오가 종결되니 CLOSED"로 끝내지 않았는가** → 프롬프트가 지정한 두 시나리오는 종결됨을 확인한 뒤, "그렇다면 `.all().delete()`가 하던 다른 일은 무엇이었나"를 물었다. 그 답이 N3(자가치유 상실 + `MultipleObjectsReturned` 영구 고착)이다. NULL 열에 유니크 제약이 걸리지 않는다는 사실은 SPEC 자신(가정 A8)이 인정하고 있으면서 그 귀결의 절반만 다뤘다.
- **D4의 "배제"를 배제로 인정할 뻔하지 않았는가** → 1차에서는 Exclusions #12와 §8 C9의 존재만 보고 CLOSED로 넘어갈 뻔했다. 2차에서 `spec.md:30`이 **유지한** 명분 문장을 코드로 추적한 결과, 유지한 것이 배제한 것과 같은 경로임을 확인했다(N1). migration `0026:63-64`의 제자리 UPDATE가 결정적 증거다.
- **REQ를 전부 읽었는가** → 34개 번호 전건을 개별 대조했다. 이 과정에서 REQ-RSW-032의 `shall` 부재(MP-2 FAIL)와 REQ-RSW-033의 `[HARD]` 누락(N11)을 발견했다. 1차 패스에서는 "신규 6건이 추가되었다"만 보고 넘어갈 뻔했다.
- **추적성을 표본이 아니라 전건으로 봤는가** → `spec.md:229-264` 34행 전부를 `acceptance.md`의 실제 `Traces:` 선언과 대조했고, 그 결과 N7의 3건과 N6·N10을 발견했다. AC 결번(N9)은 `AC-RSW-027|028|030|031|032` 기계 검색으로 확인했다.
- **인용을 "그럴듯해서" 통과시키지 않았는가** → `repair_refunds.py:36-39`, `sync_orders.py:60`, `migration 0026:63-64`, `models.py:312/320/328/342/556`, `shopify_orders.py:62-63/88-89/100-101/165/231-243/242/287-289/422-425`, `test_order_location.py:62/79/160/187`, `test_shopify_orders.py:765`, `.moai/specs/SPEC-ORDER-027/spec.md:69-70/125`를 전부 원본에서 열었다. **모두 정확했다** — v0.2.0의 인용 품질 자체는 문제가 없다. 결함은 여전히 "인용하지 않은 인접 경로"에 있다.
- **정량 주장을 저자의 산술로만 확인하지 않았는가** → 0.3초 인용은 라인 단위로 일치했고 사이클 산정도 SPEC 자신의 수치에서 따라 나온다. 그러나 "15 → 13"은 `_build_title_map`의 조기 반환(`shopify_orders.py:62-63`)을 읽고서야 과대 주장임을 알 수 있었다(N6).

신규 발견: N1, N2, N3, N4, N4b, N5, N6, N7, N8, N9, N10, N11, N12, N13. 전부 위에 반영했다.

---

## Regression Check (iteration 1 → 2)

| 이전 결함 | 상태 |
|---|---|
| D1 | **RESOLVED** — 근거는 Part 1 D1행 |
| D2 | **PARTIALLY RESOLVED** — 명시된 두 시나리오 종결, 자가치유 상실 신규(N3) |
| D3 | **PARTIALLY RESOLVED** — 예외 경로 종결, 빈 값 경로 미해소(N2) |
| D4 | **UNRESOLVED** — 배제가 명분과 모순(N1) |
| D5 | **PARTIALLY RESOLVED** — 정직한 재설계, 정렬 제거 변이 미커버(N5) |
| D6 | **RESOLVED** |
| D7 | **RESOLVED** |
| D8 | **PARTIALLY RESOLVED** — 픽스처 해소, 성공 증거 부재(N4/N4b) |
| D9 | **RESOLVED** |
| D10 | **PARTIALLY RESOLVED** — REQ 신설되었으나 비규범·미검증(N6) |
| D11 | **RESOLVED(spec.md)** — acceptance.md 미동기화(N7) |
| D12 | **UNRESOLVED (동일 결함 재발)** — 번호만 비우고 REQ-RSW-032로 재도입 → MP-2 FAIL |
| D13 | **RESOLVED** |
| D14 | **RESOLVED** |
| D15 | **RESOLVED** |
| D16 | **RESOLVED** |
| D17 | **RESOLVED** — 근거 문장 오류만 잔존(N8) |
| D18 | **RESOLVED** |
| D19 | **RESOLVED** |
| D20 | **PARTIALLY RESOLVED**(N12) |
| D21 | **RESOLVED** — 동종 불일치 신규 발생(N7) |

**Stagnation 경고 1건**: D12(비규범 문장을 요구사항 절에 두는 결함)는 iteration 1에서 지적되어 REQ-RSW-028이 제거되었으나, **같은 개정에서 REQ-RSW-032로 같은 결함이 재도입**되었다. 이는 "요구사항 절에는 `shall`을 갖춘 시스템 행동만 들어간다"는 규칙이 이해되지 않았음을 시사한다. iteration 3에서 같은 부류가 또 나오면 blocking defect로 격상해야 한다.

---

## Recommendation (manager-spec 대상, 우선순위 순)

1. **MP-2를 먼저 닫아라.** `spec.md:209-210`의 REQ-RSW-032를 §7 Exclusions 또는 §8로 이동하라 — 범위 면책은 요구사항이 아니다(D12와 같은 이유). 성능 요구를 남기고 싶다면 `shall`을 갖추고 AC-RSW-024가 실제로 검증하는 형태로 다시 써라("THE 시스템은 한 스위프 사이클에서 `ShopifySkuSetMapping` 조회를 1회만 **shall** 실행한다"). 그리고 `spec.md:262`의 "(대표 — 쿼리 수 감소분 검증)" 표기를 삭제하라. `spec.md:214` REQ-RSW-033의 `[HARD]` 마커 유무도 통일하라.
2. **N1 — 번들 명분을 정리하라.** `spec.md:30`에서 "아직 한 번도 확장되지 않은 번들의 최초 전개"를 명분에서 **삭제**하고(권장), Exclusions #12(`:283`)와 §8 C9(`:300`)의 범위를 "번들 매핑 유무 변경 전반(최초 전개 포함)"으로 확장하라. 유지하려면 migration `0026:63-64`의 제자리 UPDATE 선례를 따르는 REQ + AC를 신설해야 한다. 현재 상태는 명분과 배제가 서로를 부정한다.
3. **N2 — 빈 값 경로를 명문화하라.** REQ-RSW-030(`spec.md:199-200`)의 조건은 "호출이 실패하면"뿐이다. "조회는 성공했으나 위치 코드가 비어 있는 경우"의 정책을 REQ로 추가하고(권장: 기존 저장값 유지), `fulfillment_orders: []` 정상 응답 픽스처로 검증하는 AC를 추가하라. 근거는 `test_order_location.py:62`/`:160`/`:187`이며, 이 노출은 REQ-RSW-013+015가 새로 만드는 것이다.
4. **N3 — header-only 환불의 자가치유를 복원하라.** `plan.md:486-492`의 `update_or_create`는 선존 중복이나 동시 실행 경합이 만든 중복 앞에서 `MultipleObjectsReturned`로 영구 고착된다. NULL 경로를 "해당 키의 모든 행을 정리하고 1행 보장"으로 명세하고, Given에 `(order, R, NULL)` 행을 2건 미리 삽입한 뒤 스위프 1회로 `count()==1` **이고 실패 0건**임을 단정하는 AC를 추가하라.
5. **N4 — 보존 계열 AC에 성공 증거를 넣어라.** `last_resynced_at` 전진은 `finally`(`plan.md:294-298`) 때문에 실패한 주문에서도 참이다. AC-RSW-017/018/019/020/021/034의 Then에 "`CommandError` 없이 종료(실패 0건)" 또는 "같은 실행에서 Shopify가 바꾼 값이 반영됨"(AC-018은 Given에 이미 `title` 변경을 적었으므로 `title` 단정을 추가하면 된다)을 넣어라. `acceptance.md:47`의 [HARD] 문구도 미준수 8건(013/014/021/022/023/024/026/029)과 정합하도록 고쳐라. AC-RSW-018의 판별력 문단(`:347`)은 자기모순이므로 다시 써라.
6. **N5 — AC-RSW-006 픽스처에 한 줄 추가하라.** "E → F → G 순으로 생성한다(삽입 순서와 기대 처리 순서를 의도적으로 불일치시킨다)". 이것만으로 "정렬 제거" 변이가 커버된다.
7. **N7 — `acceptance.md` 쪽 추적 선언을 동기화하라.** `:58`에서 REQ-RSW-007 제거, `:430`의 AC-RSW-029에 REQ-RSW-025/026 추가.
8. **N9 — AC 번호 결번을 명시하라.** `acceptance.md`에 REQ-RSW-028과 동일한 수준의 결번 주석(027/028/030/031/032)을 넣고, `acceptance.md:3`·`plan.md:622`·`plan.md:718`의 "AC-RSW-001~034"를 실제 30개 목록으로 고쳐라. `plan.md:590`의 AC-RSW-033은 M2로 옮겨라.
9. **N10 — `--count` 기본값 40에 대한 검증을 붙여라.** 인자를 생략한 실행에서 처리 건수가 40 상한을 따르는지 확인하는 AC를 추가하거나, 최소한 `spec.md:239` 방식의 "AC 없음 — DoD 검증(`DEFAULT_COUNT == 40`)"으로 정직하게 표기하라.
10. **N8 — REQ-RSW-034(`spec.md:218`)의 근거 문장을 고쳐라.** 보존의 실제 근거는 REQ-RSW-018/019가 아니라 "해당 필드들이 `common_defaults`(`shopify_orders.py:231-243`)에 존재하지 않는다"는 사실이다. 존재하지 않는 보증을 인용하지 마라.
