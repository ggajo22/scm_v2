---
id: SPEC-ORDER-028
version: 0.5.0
status: superseded
superseded_by: SPEC-ORDER-029
created_at: 2026-08-19
updated: 2026-08-19
author: ggajo
priority: High
issue_number: 0
labels: [order, shopify, sync, resync, performance, backend]
---

# 선별적 주문 재싱크 스위프 (Selective Order Resync Sweep)

> **[폐기됨 — 2026-08-19, SPEC-ORDER-029로 대체]**
>
> 이 SPEC은 구현되지 않았다. 사용자의 실제 목표가 "주문의 수정·취소를 찾는 것"임이 확인되면서,
> 이 문서가 전제한 표적(기존 주문을 순회하며 배송지·제목을 갱신하는 것)이 그 목표와 맞지
> 않는다는 것이 드러났다. 취소는 **없어진 것을 찾는 문제**인데 라운드로빈은 **있는 것을 다시
> 읽는 방식**이라 방향이 반대다.
>
> 결정적 실측(2026-08-19, 프로덕션 Shopify API 직접 조회):
> - Shopify에서 열려 있는 주문 801건 vs 로컬 3,910건 — **3,109건(80%)이 이미 닫히거나 취소됐으나 로컬은 모름**
> - Shopify 취소 주문 중 로컬에 있는 것 58건, 그중 `cancelled_at` 반영은 **6건뿐**
> - 취소된 주문인데 아직 `not_shipped`로 남은 라인 **79개**, 그중 **51개는 이미 발주가 나감**
> - `status=cancelled` 목록 대조는 API **1~5회**면 끝난다 — 라운드로빈(사이클당 40건 × API 2회 + DB 80초)보다 압도적으로 싸고, 30일 창 제약도 2.14시간 랩 지연도 없다
>
> **이 문서를 폐기해도 감사 이력은 유효하다.** 4회 감사(FAIL 0.55 → FAIL 0.68 → PASS 0.80 →
> PASS 0.78)에서 확인된 코드 사실 — MySQL의 `bulk_create` 제약, header-only 환불의 NULL 키
> 문제, `_build_fulfillment_location_data()`의 무예외 빈값 반환, 번들 고아 행 생성 경로,
> `closed_at`/`cancelled_at` 소비처 부재 — 는 SPEC-ORDER-029에 그대로 승계된다.
> 상세는 `.moai/reports/plan-audit/SPEC-ORDER-028-review-{1,2,3,4}.md` 참조.

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-08-19 | ggajo | 최초 작성. 기존 증분 동기화(`sync_store()`)가 구조적으로 닫지 못하는 3개 결함(위치 미갱신·종료/취소 미반영·자체 데이터 변경 미반영)을 라운드로빈 스위프로 해소한다. |
| 0.2.0 | 2026-08-19 | ggajo | plan-auditor 1차 리뷰(FAIL, 0.55) 반영. DB 전제를 PostgreSQL→MySQL로 정정하고 D1~D21/MP-2를 반영했다(상세는 이 표의 이전 판 참조, 아래 v0.3.0 항목이 그 후속이다). REQ 28개(그중 1개 결번) → 유효 33개, AC 26개 → 30개. |
| 0.3.0 | 2026-08-19 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-028-review-2.md`, iteration 2, **FAIL, 0.68**) 반영. **이번에도 41건 인용 전수가 정확했다 — 결함은 다시 "인용하지 않은 인접 코드"에 있었다**(감사 자평, migration `0026`과 `test_order_location.py:62`). **CRITICAL 2건**: **N1** — v0.2.0이 문제 정의 3번에서 유지한 명분("최초 1회 번들 확장")이 정확히 고아 `sku=bundle_sku` 행을 만드는 그 케이스였다(번들 분기의 조회 키가 `sku`라 기존 원본 행에 매치되지 않고, stale 삭제는 `shopify_line_item_id`만 보므로 원본 행이 삭제되지도 않는다 — migration `0026_backfill_bundle_lineitems.py:9-26/55-64`가 정확히 이 함정을 피하려고 제자리 UPDATE로 우회했던 그 케이스). 유지한 명분과 Exclusions #12의 배제 대상이 같은 코드 경로를 가리켜 서로 모순이었다. **문제 정의 3번에서 번들 관련 이득을 완전히 제거**하고(도서 제목 전파만 남김), REQ-RSW-031·Exclusions #12·§8 C9를 "최초 전개·사후 변경 구분 없이 번들 매핑 존재 전반"으로 확장해 모순을 해소했다(감사가 제시한 두 선택지 중 (a) 채택 — 명분 삭제 + 배제 확장. (b), 즉 migration 0026 방식의 제자리 UPDATE를 스위프에 구현하는 안은 3개 기존 호출부에 영향을 미치는 별도 SPEC급 변경이라 채택하지 않았다). **N2** — `raise_on_error`는 **예외** 경로만 막았고, `_build_fulfillment_location_data()`가 **예외 없이 정상적으로** 빈 위치를 반환하는 경로(할당 위치 이름에 언더스코어가 없거나 `fulfillment_orders`가 빈 배열인 경우, `shopify_orders.py:88-89`, `test_order_location.py:62`가 이 정상 동작으로 고정)는 전혀 막지 못해 D3의 사고(위치 조용한 소거)가 그대로 재현됐다 — REQ-RSW-030을 두 개의 하위 절로 확장해 (a) 예외 경로(기존)와 (b) 정상-빈값 경로(신규)를 모두 다루도록 했다: (b)는 스위프가 새로 조회한 값이 비어 있을 때 기존 저장값을 유지하는 값-병합 로직(위치 단위, `_sync_single_order()`/`_build_fulfillment_location_data()` 시그니처는 무변경)이며, AC-RSW-030을 신설했다. **MAJOR 4건**: **N3** — header-only 환불(`line_item_id IS NULL`)에는 유니크 제약이 걸리지 않아(가정 A8) 이력 데이터나 `sync_store()`와의 동시 실행 경합(§8 C8)으로 이미 중복 행이 존재할 수 있는데, 기존 `.all().delete()`가 담당하던 자가치유가 차등 갱신 설계에서 사라져 `update_or_create`의 내부 `.get()`이 `MultipleObjectsReturned`를 던지고 그 주문이 영구 실패한다 — REQ-RSW-029에 "upsert 전 중복 행을 1건으로 정리"하는 자가치유 복원 절을 추가하고 AC-RSW-029b를 신설했다. **N4/N4b** — "처리됨"의 증거로 채택한 `last_resynced_at` 전진(`finally`에서 성공/실패 무관하게 항상 참)이 "성공"의 증거가 아니어서, 보존 계열 AC 전체가 스위프가 전면 실패하는 시나리오에서 공허하게 통과할 수 있었다(AC-RSW-018의 판별력 문단은 이 결함의 구체적 사례로 자기모순이었다 — `logistics_status`를 `defaults`에 넣는 변이는 `IntegrityError`로 롤백되어 "무변경" 단정을 오히려 통과시킨다) — `acceptance.md` §0.1의 [HARD] 규약을 "실패 0건(CommandError 미발생)" 또는 "실제 변경 반영" 중 하나의 명시적 성공 증거로 강화하고, 그 규약을 실제로 지키지 않던 8개 AC(013/014/021/022/023/024/026/029)와 보존 계열 4개(017~020)에 증거를 추가했다 — 이제 IntegrityError 롤백 변이는 "실패 1건"으로 잡혀 AC-018도 판별력을 회복한다. **N6/MP-2** — REQ-RSW-032(v0.2.0에서 D10 대응으로 신설)가 `shall`이 없는 범위 면책 선언이라 iteration 1에서 REQ-RSW-028을 §8로 퇴출시킨 것과 정확히 같은 결함이 같은 개정에서 재도입됐다("stagnation" 경고, 3차에서 재발 시 blocking 격상 예고) — **REQ-RSW-032를 완전히 삭제**하고 번호를 결번 처리했다(REQ-RSW-028과 동일한 3-place 명시 규약). 그 안의 "15→13" 수치도 `_build_title_map()`의 조기 반환(`shopify_orders.py:62-63`, ISBN 목록이 비면 쿼리 없이 반환)을 놓쳐 과대 추정이었음을 확인 — 정정된 수치("번들 SKU가 없는 주문에서는 15→14, 있는 주문에서는 15→13")를 비규범 정보로 §8 C11에 남겼다. **[v0.5.0 정정, 감사 D7]** 이 HISTORY 항목은 원래 "있는 주문에서는 절감 없음"이라고 잘못 적었었다 — 실제로는 정반대다: 번들 SKU가 **없는** 주문은 `_build_title_map()`이 빈 ISBN 목록에서 조기 반환하므로(`shopify_orders.py:62-63`) 절감이 `ShopifySkuSetMapping` 쿼리 1개뿐이고, 번들 SKU가 **있는** 주문만 도서 제목 쿼리까지 추가로 절감된다 — 즉 번들 주문이 더 많이 절감한다. §8 C11 본문은 처음부터 옳았다(`15→14`/`15→13`); 이 HISTORY 요약문만 뒤집혀 있었다. **MEDIUM 4건**: **N5** — AC-RSW-006의 픽스처 생성 순서(G→F→E)가 기대 처리 순서와 우연히 같아 `order_by` 삭제 변이가 통과할 수 있었다 — Given의 생성 순서를 E→F→G(기대 처리 순서와 의도적으로 불일치)로 뒤집었다. **N7** — 개정 과정에서 `spec.md`와 `acceptance.md` 간 추적 선언이 다시 어긋났다(AC-RSW-001이 여전히 REQ-RSW-007을 선언, AC-RSW-029가 REQ-RSW-025/026 선언 누락) — 양쪽을 대조해 정정했다. **N9** — AC 번호에 무설명 결번이 있고 "AC-RSW-001~034"라는 문구가 34개 연속인 것처럼 오도했다 — 실제 33개 목록과 결번 사유를 `acceptance.md` §0에 명시했다. **N10** — `--count` 생략 시 기본값 40이 적용된다는 사실을 검증하는 AC가 없었다 — AC-RSW-007b를 신설했다. **MINOR 3건(대부분 수용)**: **N8** — REQ-RSW-034의 보존 근거가 REQ-RSW-018/019를 잘못 인용했다(실제 근거는 그 필드들이 `common_defaults`에 아예 없다는 사실) — 인용을 정정했다. **N11** — REQ-RSW-033에만 `[HARD]` 마커가 없었다 — 추가해 통일했다. **N12(수용, 미조치)** — REQ-RSW-024/025/029에 매칭 키 등 구현 기법이 일부 남아 있다(D20 잔여) — 감사 자신이 "정확성에는 영향 없음"으로 낮은 심각도를 매겼고, 이번 개정에서 또 다른 문서 전반 재작성을 유발할 위험이 이득보다 크다고 판단해 **의도적으로 미조치** — 이 SPEC의 알려진, 수용된 잔여 항목으로 §8 C12에 명시한다. **N13**: 결함 아님(정보 기록용), 조치 없음. REQ 결번 2개(028, 032) → 활성 REQ 32개(v0.2.0 33개에서 REQ-RSW-032 삭제로 1건 감소), AC 30개 → 33개(신규 3개: 007b/029b/030). |
| 0.4.0 | 2026-08-19 | ggajo | **사용자 확정 결정 반영(재론 아님, 구현): 대상 연령 상한 60일 → 30일.** 재측정 데이터(§2): not_shipped 주문 1,349건(60일 기준 재측정, v0.1.0 당시 1,328건에서 재측정으로 21건 증가) 중 30일 이내 1,029건(26.5%)이 신규 대상, 30~60일 320건이 신규 제외. **논거를 정직하게 교체했다** — 60일 상한을 정당화하던 "그 시점 not_shipped 전량이 이미 60일 이내였다"는 무손실(lossless) 논거는 30일에서 더 이상 성립하지 않는다(320건이 실제로 제외됨). 대체 논거는 **휴면성**이다: 제외되는 320건 중 최근 30일 이내 Shopify `updated_at` 변경이 있던 주문은 13건(4%)뿐, 최근 7일 이내는 1건뿐이다 — 스위프의 존재 이유가 "Shopify 쪽 변경 포착"이므로 거의 안 바뀌는 밴드를 빼는 것이 대상 판정의 취지에 맞는다(§4 D7, §2). **잔여 위험을 §8 C13에 평문으로 명시했다**(HISTORY에 묻지 않음) — 제외 밴드 320건의 not_shipped 라인아이템 중 97%(1,255/1,292건)에 이미 `PurchaseOrder`가 연결되어 있다(방치가 아니라 입고 대기 중). 이 중 하나의 배송 위치가 재배정되면 스위프는 잡지 못하고, 기존 5분 주기 `sync_store()`도 기존 주문의 위치를 절대 갱신하지 않는다(`shopify_orders.py:420-428`) — 4% 휴면율은 이 위험을 경계 지을 뿐 제거하지 않는다. **완화책으로 REQ-RSW-035(`--days` CLI 인자, 기본값 30, `backfill_missing_orders.py`의 `--created-since` 관례 미러링)를 신설**해, 위험이 실제로 발현되면 코드 변경 없이 더 넓은 창으로 일회성 catch-up 스위프를 돌릴 수 있게 했다 — Exclusions #10을 이에 맞춰 축소했다(`not_shipped` 판정 기준은 여전히 상수로 고정되지만, 연령 상한은 운영상 CLI로 조정 가능한 이스케이프 해치가 되었다. 기본값 없는 실행은 여전히 항상 30을 쓴다). AC-RSW-003/004의 경계 픽스처를 61일/59일 → 31일/29일로 갱신하고(경계값이 실제로 30일을 검증하도록), AC-RSW-035(명시적 override)·AC-RSW-035b(커맨드 경로 기본값 30 적용)를 신설했다(M26/M27). 파생 수치를 전부 재도출했다(스케일링 아님) — 다음 랩 소요 2.8시간 → 2.14시간(1,029÷40≈25.73사이클×5분), 대상 비중 34% → 26.5%(1,029/3,883), 번들 노출 빈도 약 8회·일 → 약 11회·일(24÷2.14시간). REQ/AC 개수: 활성 REQ 32개 → 33개(REQ-RSW-035 신규), AC 33개 → 35개(AC-RSW-035/035b 신규). **carry-forward(변경하지 않음, 2차 감사가 RED-test-time·non-blocking으로 남긴 항목)**: AC-RSW-018의 `logistics_status="not_shipped"` 픽스처가 모델 기본값과 동일해 리셋 변이가 트리비얼하게 통과하는 문제, AC-RSW-030이 전체-빈값 `("", {})` 형태만 모킹하고 부분 병합 케이스는 다루지 않는 문제, `plan.md:186-192`가 `from … import` 스타일을 쓰는데 모의 패치 대상이 REQ/AC 어디에도 명시되지 않은 문제 — 이 3건은 v0.3.0 감사가 이미 "판정 유예"로 남긴 항목이며 이번 개정은 손대지 않는다. **[v0.5.0 정정, 감사 D7]** 이 carry-forward 선언은 원래 3건으로 축소 표기되어 있었으나, review-3의 "구현 착수 전 처리" 권고 중 2건이 실제로는 여기 포함되지 않은 채 미조치로 남아 있었다 — §8에 종료/취소 필드 소비자 부재 항목이 추가되지 않았고(review-3 권고 1), 바로 위 이 HISTORY 항목의 수치 오류(review-3 권고 2, 이번에 정정)도 잔존해 있었다. 두 항목 모두 v0.5.0에서 처리했다(§8 C14 신설, 수치 정정) — 처리 전까지 이 선언은 실제 미조치 항목(5건)보다 적게 표기해 다음 감사·구현자를 오도할 수 있었다. |
| 0.5.0 | 2026-08-19 | ggajo | plan-auditor v0.4.0 델타 감사(`.moai/reports/plan-audit/SPEC-ORDER-028-review-4.md`, iteration 4, **PASS, 0.78**, blocking 결함 없음) 반영. 신규 실측: 30일 대상 집합(1,033건/4,389 라인아이템) 중 번들 멤버 라인 65건(1.5%), 잔존 `sku=bundle_sku` 고아 행 0건, NULL 제목 라인 0건. **감사 D2(MAJOR) — 명분 과장 정정.** `_build_title_map()`의 유일한 소비처가 번들 분기(`shopify_orders.py:255`)임을 확인 — 일반 라인아이템에는 제목 전파가 전혀 적용되지 않는다. §1 문제 정의 3번을 "스위프가 온전히 해소한다"에서 "실재하나 번들 한정·현재 규모 근사 0인 부차적 이득"으로 재서술하고, **문제 정의 1번(입고 위치 갱신)을 이 SPEC의 load-bearing 명분으로 명시**했다. 이 정정은 §2의 휴면성 논거에도 소급 적용된다 — 4% 휴면율은 `updated_at` 기반이고 카탈로그 발원 변경(제목)은 `updated_at`에 나타나지 않으므로(§1 3번 자체가 단정), 그 지표는 애초에 Shopify 발원 변경(명분 1·2)만 유계화한다는 사실을 §2와 §8 C13에 명시했다. **감사 D3(MAJOR) — 미검증 전제 노출.** C13의 4% 유계화는 "fulfillment 위치 재배정이 부모 `Order.updated_at`을 갱신한다"는 미검증 전제에 의존한다 — 이 전제가 거짓이면 4%는 위치 위험에 대해 아무것도 유계화하지 못한다. 가정 **A10**(미검증으로 명시)을 신설하고 C13에 단서를 추가했다. **REQ-RSW-035 프레이밍 정정(비차단 권고 반영)** — `--days`를 "완화책"으로 부르던 3곳(§4 D7, REQ-RSW-035 본문, §8 C13, 그리고 일관성을 위해 §2·Exclusions #10도 함께)을 "이스케이프 해치"로 수정했다 — 이 위험에는 검출기가 시스템 안에 없으므로(스위프는 창 밖이라 구조상 미도달, `sync_store()`는 기존 주문 위치 갱신 안 함, 단건 재동기화는 수동 트리거 전용) `--days`는 검출 지연을 줄이지 못하고 발현 후 복구 시간(MTTR)만 줄인다. C13에 감사의 비차단 권고(REQ-RSW-027 스케줄러 패턴을 따르는 저빈도 `--days 60` 정기 작업, 코드 변경 0)를 선택지로 기록했다. §8 **C9**에 우호적 데이터(30일 창 안 잔존 고아 행 0건, 스냅숏 한정)를 추가했다. **감사 D1(MAJOR, N7 재발) — 추적 선언 동기화.** `acceptance.md`의 AC-RSW-035b가 `Traces: REQ-RSW-003`만 선언해 `spec.md` §6(REQ-RSW-035 → AC-035/AC-035b)과 불일치했다 — `Traces: REQ-RSW-003, REQ-RSW-035`로 정정했다(spec.md §6은 원래부터 정확했다). **재발 방지를 위해 35개 AC의 `Traces:` 선언 전체를 §6 추적표와 기계적으로 재대조했다 — 이 건 외 추가 불일치 0건.** **감사 D4(MINOR) — 단측 AC 보강.** AC-RSW-035b가 35일 주문 1건의 순수 음성 단정뿐이라 기본값이 30→20으로 어긋나는 변이와 전면 실패 시나리오를 놓쳤다 — Given에 29일 양성 대조군(주문 O)을 추가하고 Then에 O의 처리 성공 증거(`last_resynced_at` 갱신 + `CommandError` 없이 종료)를 추가해 한 번에 해소했다(M27 판별력 보강). DoD `§0.1 성공 증거 규약 재확인` 목록에 035/035b를 편입했다. **감사 D6(MINOR) — DoD 산술 정정.** DoD 신규 검증 열거가 34개를 나열하고 35개라 표기했다(`AC-RSW-014b` 누락, review-3 D5(iii) 2회 연속 미해결) — 열거에 추가했다. **감사 D7(MAJOR) — carry-forward 선언 정확성.** v0.4.0 HISTORY가 carry-forward를 3건으로 축소 표기했으나 review-3의 "착수 전 처리" 권고 중 2건이 실제로는 미조치로 남아 선언에서 빠져 있었다 — §8에 **C14**(종료/취소 필드 소비자 부재, review-3 D1 원문 반영)를 신설하고, HISTORY v0.3.0의 "15→13" 수치 오기를 C11과 일치하도록 정정했다(위 v0.3.0/v0.4.0 항목에 소급 표기). REQ/AC 개수는 델타로 불변(활성 REQ 33개, AC 35개 — 신규 REQ/AC 없음, 전부 문서 정합 수정). **감사가 수용한 개방 위험(조치 불요)**: D5(AC-035/035b Given이 `_make_qualifying_order()` 오버라이드 스타일 대신 처음부터 서술 — RED 작성 시점 반영 유예), D8(4% 지표가 회전 모집단의 시점 측정이라는 정상성 가정이 미명시 — 권고, 결함 아님). 두 항목 모두 이번 개정에서 의도적으로 손대지 않았다(사용자 지시: "tidy-up pass, do not reopen anything" 범위 밖). |

---

## 1. 문제 정의

Shopify 주문은 자주 바뀐다(입고 위치 이동, 취소, 품목 수정). 기존 증분 동기화가 이미 존재하지만, 아래 3가지 결함은 구조적으로 닫을 수 없다.

1. **[이 SPEC의 load-bearing 명분, v0.5.0 명시] 기존 주문의 입고 위치가 절대 갱신되지 않는다.** `sync_store()`(`backend/order/shopify_orders.py:355`)는 이미 로컬에 존재하는 주문을 만나면 저장된 `location`을 재사용하고 `orders/{id}/fulfillment_orders.json` 호출 자체를 건너뛴다(`shopify_orders.py:420-428`). NJ↔CA 재배정은 단건 재동기화(`OrderResyncView`)를 통해서만 반영되며, 5분 주기 스케줄에서는 절대 감지되지 않는다. 이 SPEC이 존재하는 구조적 이유는 이 결함이다 — 아래 2번·3번도 실재하는 이득이지만 규모와 필요성에서 이 항목에 미치지 못한다(3번은 특히 그렇다, 아래 참조).
2. **종료/취소가 절대 반영되지 않는다.** `fetch_all_open_orders()`(`shopify_orders.py:32-45`)는 `status=open`으로만 조회하므로, Shopify에서 종료·취소된 주문은 그 피드에서 그냥 사라지고 로컬 `closed_at`/`cancelled_at`은 영원히 NULL로 남는다. 실측: 3,883건 중 `closed_at` 12건, `cancelled_at` 6건뿐이다. **[v0.5.0 참조, §8 C14]** 다만 이 두 필드를 현재 소비하는 백엔드 로직은 없다 — 상세는 §8 C14.
3. **[v0.5.0 재서술, 감사 D2] 도서 제목 전파는 실재하나 번들 한정·현재 규모 근사 0인 부차적 이득이다 — 명분이 아니다.** 도서 제목은 `_build_title_map()`(`:198-207`, `Inven`/`Info` 조인)을 읽으며, 이 세션에서 확인한 유일한 소비처는 `_sync_single_order()`의 번들 분기(`shopify_orders.py:255`, `member_defaults = {**common_defaults, "title": title_map.get(member_isbn)}`)뿐이다 — **일반(비번들) 라인아이템에는 전혀 적용되지 않는다.** 카탈로그에 도서를 추가해도 Shopify의 `updated_at`은 바뀌지 않으므로 기존 번들 멤버 행은 재제목화되지 않는다 — 스위프는 이 경로를 되살린다. 다만 v0.5.0에서 30일 대상 집합(1,033건/4,389 라인아이템)을 직접 측정한 결과 번들 멤버 라인은 65건(1.5%)뿐이고 그중 NULL 제목은 **0건**이다(§2) — 오늘 시점 이 효과가 실제로 되살리는 데이터는 없다. 이 SPEC의 구조적 명분은 **1번**이다(위 참조) — 도서 제목 전파는 실재하는 부차적 이득일 뿐 이 SPEC을 정당화하는 근거가 아니다. **번들 매핑 전파(최초 전개·사후 변경 구분 없이)는 이 SPEC의 명분에서 완전히 제외한다.** [v0.2.0은 "최초 1회 번들 확장"만 명분으로 남기고 "사후 변경(멤버 추가/제거)"만 배제했으나, 감사 N1이 확인한 대로 **최초 전개 자체가 고아 행을 만드는 바로 그 경로**였다 — 번들 분기는 `sku=member_isbn`을 조회 키로 삼아 새 행을 만들고(`shopify_orders.py:265-269`), stale 삭제는 `shopify_line_item_id`만 기준으로 하므로(`:287-289`) 기존 `sku=bundle_sku` 원본 행은 삭제되지 않고 고아로 남는다. migration `0026_backfill_bundle_lineitems.py`(주석 `:9-26`)가 바로 이 함정을 피하려고 첫 멤버에 대해 원본 행을 제자리 UPDATE했다(`:63-64`, `li.sku = first_isbn; li.save(update_fields=["sku"])`). v0.2.0의 "유지한 명분"과 "배제한 대상"은 사실 같은 코드 경로였다 — v0.3.0은 이 모순을 명분 삭제로 해소한다.] 스위프가 번들 매핑이 존재하는 라인아이템을 처리하면(최초 전개든 사후 변경이든) `_sync_single_order()`의 이 기존 알려진 한계가 그대로 발동하며, 이 SPEC은 그 로직을 고치지 않는다(REQ-RSW-031, Exclusions #12, §8 C9) — 스위프가 하는 일은 이 한계의 노출 빈도를 수동/희귀에서 자동/약 11회·일(v0.4.0 재산정, §4 D7)로 늘리는 것뿐이다.

**왜 느린가(주문 건수가 아니라 건당 비용의 문제)**: `_sync_single_order()`(`:104`)는 주문마다 약 15개 쿼리(모든 주문에 대해 동일한 결과를 내는 `ShopifySkuSetMapping` 전수 스캔 재조회 포함, `_build_title_map()`, `protected_sku_by_key` 조회, `shipping_lines.all().delete()` + `bulk_create`, `refunds.all().delete()` + 라인별 `update_or_create`, 라인아이템당 `update_or_create`)를 실행한다. 원격 DB 지연이 쿼리당 ~130ms이므로 건당 약 2초 — 3,883건 전체를 재동기화하면 2시간을 넘는다. 이 SPEC이 그 2시간 문제를 실제로 해소하는 것은 라운드로빈 아키텍처(N=40건씩만 처리, 전체 재동기화를 절대 하지 않음) 그 자체다 — 배치 컨텍스트 호이스팅(REQ-RSW-023)에 의한 주문당 쿼리 절감은 부차적이며 그 정확한 크기는 주문마다 다르다(§8 C11, **[v0.3.0 정정, 감사 N6]** 이전 버전의 "15→13"이라는 REQ-RSW-032는 삭제되었다 — 성능 문제의 1차 해법은 라운드로빈 아키텍처이지 이 호이스팅이 아니다).

---

## 2. Environment (환경)

| 항목 | 내용 |
|------|------|
| 대상 코드(백엔드, 기존/무변경 유지) | `sync_store()`(`backend/order/shopify_orders.py:355-461`, 5분 주기 스케줄), `OrderResyncView`(`backend/order/views.py:408`) → `sync_single_order_from_shopify()`(`shopify_orders.py:334-352`), `backfill_missing_orders` 커맨드(`backend/order/management/commands/backfill_missing_orders.py`) |
| 대상 코드(백엔드, 이 SPEC이 수정) | `_sync_single_order()`(`shopify_orders.py:104-331`) — 배치 불변 컨텍스트 파라미터 추가 + 환불/배송라인 차등 갱신, `_build_fulfillment_location_data()`(`:72-101`) — 하위호환 실패-전파 옵션 추가(시그니처만; 정상-빈값 병합 로직은 스위프 자신이 담당), `Order` 모델(`backend/order/models.py:30-111`) — `last_resynced_at` 필드 추가 |
| 대상 코드(백엔드, 이 SPEC이 신설) | 신규 관리 커맨드 `resync_order_sweep`(`backend/order/management/commands/resync_order_sweep.py`), 신규 마이그레이션 `0045` |
| 데이터베이스 | **MySQL**(RDS, `backend/.env`: `DB_ENGINE=django.db.backends.mysql`, `DB_PORT=3306`), `mysqlclient 2.2.7`, Django `5.1.6`. 로컬 pytest와 운영 모두 동일 MySQL RDS를 바라본다. 이 세션에서 Django 소스를 직접 읽어 확인한 4개 기능 플래그: `supports_update_conflicts=True`, `supports_update_conflicts_with_target=False`, `order_by_nulls_first=True`, `supports_order_by_nulls_modifier=False` |
| 기존 스케줄 등록 절차(참고) | `scripts/sync_orders.bat` + `scripts/run_hidden.vbs`, `.moai/project/scheduled-jobs.md` — 동일 패턴을 신규 커맨드에도 적용한다 |
| 영향 API | 없음(신규 관리 커맨드는 CLI 전용, HTTP 엔드포인트를 신설하지 않는다). `OrderSyncStatusView`(`backend/order/views.py:99-156`)는 참고만 하며 이 SPEC의 필수 변경 대상이 아니다(§8 C6) |
| 데이터 소재 | `Order.shopify_created_at`(`models.py:77`), `Order.closed_at`(`:79`), `Order.cancelled_at`(`:80`), `Order.location`(`:76`), `LineItem.logistics_status`(`:204-208`), `LineItem.location`(`:182`), `LineItem.received_quantity`(`:228`), `LineItem.received_at`/`shipped_quantity`/`shipped_at`/`rack_number`/`damaged_quantity`/`confirmed_price`/`confirmed_distributor`/`confirmed_at`(전부 REQ-RSW-034 보존 대상), `Refund.line_item_id`(`:328`, nullable — REQ-RSW-029 대상), `StoreSyncWatermark`(`:565-603`, 이 SPEC은 쓰지 않음) |
| 신규 필드 | `Order.last_resynced_at`(nullable `DateTimeField`) — 마이그레이션 `0045`(최신 마이그레이션은 `0044_lineitem_original_sku.py`) |

### 측정된 프로덕션 데이터 (사용자 제공, 이 세션에서 재조회하지 않음)

```
전체 주문                                     3,883건   (gimssine 3,801 / etoile 82)
전체 라인아이템                              15,384건   (주문당 평균 3.96개)
logistics_status: shipped 9,980 / not_shipped 4,887 / received 517
not_shipped 라인아이템이 1개 이상인 주문        1,349건   (60일 기준 재측정치, §4 D7 — v0.1.0 당시 1,328건에서 재측정으로 21건 증가)
  └ 생성일 30일 이내 (v0.4.0 신규 대상)        1,029건   (26.5%)
  └ 생성일 30~60일 (v0.4.0 신규 제외)            320건
  └ 생성일 60일 초과                               0건
closed_at이 채워진 주문                          12건
cancelled_at이 채워진 주문                        6건
```

#### 제외 대상(30~60일, 320건) 밴드 상세 — 30일 상한 재확정 근거 `[v0.4.0 신설]`

```
밴드 내 not_shipped 라인아이템                1,292건
  └ PurchaseOrder 연결됨                     1,255건   (97%)
  └ PurchaseOrder 미연결                        37건
  └ 부분 입고(received_quantity > 0)              0건
밴드 내 주문의 Shopify updated_at 변경 이력(현재 시각 기준 역산)
  └ 최근 7일 이내 변경                            1건
  └ 최근 14일 이내 변경                           2건
  └ 최근 30일 이내 변경                          13건   (4%)
  └ 최근 60일 이내 변경                         320건   (전량 — 60일 창의 정의상 당연)
```

#### 대상 집합(30일)의 도서 제목 전파 규모 — 문제 정의 3번 재평가 근거 `[v0.5.0 신설, 감사 D2]`

```
대상 집합(30일)                            1,033건 / 4,389 라인아이템
  └ 번들 멤버 라인(member-ISBN, 번들 확장분)      65건   (1.5%)
  └ 잔존 sku=bundle_sku 고아 라인                  0건   (§8 C9 참조)
  └ NULL 제목 라인(전체)                           0건
  └ NULL 제목 번들 멤버 라인                        0건
```

`title_map`의 유일한 소비처는 번들 분기(`shopify_orders.py:255`)이므로 도서 제목 전파는 번들 멤버 라인에만 적용된다 — 대상 집합에서 그 비중은 1.5%이고, 그중 실제로 제목이 비어 있어 전파가 필요한 라인은 0건이다. 이 수치는 §1 문제 정의 3번의 재서술 근거다.

**30일 상한 재확정 근거(데이터 지원) `[v0.4.0 신설, v0.5.0 보강]`**: v0.1.0~v0.3.0의 60일 상한은 "그 시점 not_shipped 주문 전량이 이미 60일 이내였다"는 무손실(lossless) 논거로 정당화되었다 — **이 논거는 30일에서는 더 이상 성립하지 않는다**(위 320건이 실제로 제외된다). 이번 개정이 채택하는 논거는 **휴면성(dormancy)**이다: 제외되는 320건 중 최근 30일 이내에 Shopify `updated_at`이 조금이라도 바뀐 주문은 13건(4%)뿐이고, 최근 7일 이내는 1건뿐이다. 이 스위프의 존재 이유가 "Shopify 쪽에서 실제로 바뀐 것을 잡아내는 것"이므로, 거의 바뀌지 않는 밴드를 대상에서 제외하는 것은 대상 판정의 취지에 부합한다. **[v0.5.0 명시, 감사 D2]** 이 4% 지표는 **Shopify 발원 변경**(문제 정의 1번 위치 재배정, 2번 종료/취소)만 유계화한다 — **로컬 카탈로그 발원 변경(문제 정의 3번, 도서 제목)에는 원리적으로 적용되지 않는다**, 카탈로그에 도서를 추가해도 Shopify `updated_at`은 움직이지 않기 때문이다(§1 3번 재확인). 다만 문제 정의 3번이 확인하듯 이 효과의 오늘 시점 규모는 근사 0이므로(위 표), 이 적용 불가능성 자체가 실무적 손실을 의미하지는 않는다. 이 논거는 (적용 가능한 범위 안에서도) 위험을 **경계 지을 뿐 제거하지 않는다** — 제외 밴드의 97%에 이미 `PurchaseOrder`가 연결되어 있어(위 표) 방치된 주문이 아니라 입고 대기 중인 살아있는 주문이다. 이 잔여 위험과 그 이스케이프 해치는 §8 C13에 명시한다.

---

## 3. Assumptions (명시적 가정)

| # | 가정 | 근거 / 틀렸을 때의 영향 |
|---|------|--------------------------|
| A1 | §2의 측정치는 사용자가 라이브 DB에서 직접 조회해 제공한 값이며, 이 세션에서 재조회로 검증하지 않았다 | 대상 기준(REQ-RSW-003)과 N 기본값(REQ-RSW-006) 산정의 입력값이다. 실제 분포가 달라도 대상 기준 자체(로직)는 무관하게 성립하지만, 한 랩(lap)이 완주되는 데 걸리는 시간 추정치(§8 C1)는 이 값에 의존한다 |
| A2 | `Order.shopify_created_at`은 모든 주문에 채워져 있다 — Shopify 주문 페이로드의 `created_at`을 그대로 저장한다(`shopify_orders.py:159`, `"shopify_created_at": order_data.get("created_at")`) | 이 세션에서 `_sync_single_order()` 본문을 직접 읽어 확인. NULL이면 REQ-RSW-003(b)의 연령 상한 필터(기본값 30일, v0.4.0)가 그 주문을 항상 제외하므로(NULL은 어떤 `>=` 비교에서도 참이 되지 않음, SQL 3치 논리), 결과적으로 안전한 방향(과소포함)으로 실패한다 |
| A3 | `orders/{id}.json` 단건 엔드포인트는 주문의 open/closed/cancelled 상태와 무관하게 항상 그 주문을 반환한다 — `fetch_all_open_orders()`의 `status=open` 목록 피드(`:32-45`)와 달리 상태 필터가 없다 | `sync_single_order_from_shopify()`(`:334-352`)가 이미 이 엔드포인트를 그렇게 사용하고 있다(이 세션에서 확인) — 문제 정의 2번(종료/취소 미반영)을 이 스위프가 닫을 수 있는 근거다. Shopify가 이 계약을 바꾸면(예: 종료된 주문에 404를 반환하기 시작하면) REQ-RSW-015의 전제가 깨진다 — 이 SPEC은 그 변경을 감지하는 별도 로직을 두지 않는다(§8 C2) |
| A4 | MySQL은 `ASC` 정렬에서 NULL을 이미 가장 앞에 둔다(`order_by_nulls_first=True`, `django/db/backends/mysql/features.py:59`, 이 세션에서 확인) | MySQL에서는 `last_resynced_at`이 NULL인 주문(한 번도 스윕되지 않음)이 별도 지정 없이도 오름차순 정렬에서 먼저 나온다. `nulls_first=True`를 명시적으로 주더라도(방어적/이식성 목적) 이 DB에서는 컴파일되는 SQL이 동일하다(가정 A4a) |
| A4a | Django의 `OrderBy.as_sql`(`django/db/models/expressions.py:1795-1819`)은 `supports_order_by_nulls_modifier`가 False인 백엔드에서 `order_by_nulls_first`(백엔드 네이티브 NULL 정렬 방향)와 맞물려 `nulls_first`/`nulls_last` 보조 정렬 컬럼 추가 여부를 결정한다. MySQL은 `order_by_nulls_first=True`이므로 `.asc(nulls_first=True)`를 호출해도 이 조건이 거짓이 되어 어떤 보조 컬럼도 추가되지 않는다 — 즉 `.asc(nulls_first=True)`와 `.asc()`는 이 DB에서 **바이트 단위로 동일한 SQL**을 생성한다(이 세션에서 Django 소스를 직접 추적해 확인) | `nulls_first=True` 파라미터의 유무는 이 DB에서 독립적으로 관측 가능한 변이가 아니다 — AC-RSW-006(§acceptance.md)은 이 사실을 반영해 "결과 처리 순서"로만 검증을 설계한다(SQL 파라미터 존재 여부가 아니라) |
| A5 | Shopify Admin REST API의 표준 속도 제한은 초당 약 2회로 알려져 있으나(외부 근거, 재검증하지 않음), 이 저장소에는 이미 동작 중인 페이싱 선례가 있다: `backend/order/management/commands/repair_refunds.py:36-39`, `--sleep` 기본값 **0.3초**, 도움말 문구 "respects the REST rate limit"(이 세션에서 확인) | REQ-RSW-014의 페이싱 간격은 이론적 예산(~2회/초 = 0.5초 간격, 여유 0)이 아니라 **이 저장소의 실제 운영 선례(0.3초)**를 채택한다 — 다만 `sync_store()`(5분 주기)와 수동 재동기화 버튼이 같은 상점의 같은 속도 제한 버킷을 동시에 소비하므로(§8 C2), 페이싱은 "속도 제한 보장"이 아니라 "최선 노력 부하 경감"으로 취급하며, 429 발생 시의 진짜 안전망은 REQ-RSW-030(실패/빈값 시 위치 보존)이다 |
| A6 | `Order`-`LineItem` 관계에서 "최소 1건의 not_shipped LineItem"을 판정할 때 서브쿼리 기반 존재 판정을 쓰면 JOIN에 의한 행 중복(fanout)을 피할 수 있다 | 이미 이 저장소에 확립된 패턴이다 — `_apply_logistics_display_filter`(`backend/order/views.py:188-253`)가 동일한 목적으로 `Exists(trackable_qs.exclude(...))` 방식을 쓴다(`:203-223`). 이 SPEC의 대상 판정 쿼리는 새 패턴을 발명하지 않고 이 선례를 재사용한다(구체적 구현은 `plan.md`) |
| A7 | `_build_fulfillment_location_data()`는 (i) 예외가 발생하거나 (ii) 예외 없이 정상적으로 빈 값을 낼 때(Shopify 응답의 `assigned_location.name`에 언더스코어가 없거나 `fulfillment_orders`가 빈 배열, `shopify_orders.py:86-89`) 모두 `("", {})` 또는 부분적으로 빈 항목을 반환할 수 있다 — 이 두 경로는 `backend/order/tests/test_order_location.py`가 각각 `:79-88`(예외)과 `:62-76`(정상-빈값)로 독립적으로 고정한다. 3개 기존 호출부(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`)는 두 경로 모두를 이미 이 계약대로 소비한다 | 이 계약 자체(함수 시그니처·반환 형태)를 바꾸면 3개 기존 호출부의 동작이 바뀐다(회귀 위험) — REQ-RSW-030은 이 함수의 **기존 시그니처를 보존**한 채, (i)은 선택적 파라미터로 스위프만 예외를 전파받고, (ii)는 스위프가 반환값을 소비하는 지점에서 스스로 병합 처리하여 두 경로 모두에서 스위프만 위치를 보존하도록 한다 |
| A8 | `Refund.line_item_id`는 nullable이며(`models.py:328`) unique_together의 일부다(`:342`) — SQL 표준상 NULL은 어떤 값과도(자기 자신을 포함해) 같다고 판정되지 않으므로, 유니크 제약 기반의 충돌 판별(upsert)은 `line_item_id IS NULL`인 행끼리 절대 "충돌"로 인식하지 않는다. 따라서 이 컬럼에는 사실상 유니크 제약이 걸리지 않는 것과 같아, 이력 데이터나 동시 실행 경합으로 동일 (주문, `shopify_refund_id`, NULL) 조합의 행이 2건 이상 존재하는 상태가 물리적으로 가능하다 | 이 규칙은 MySQL·PostgreSQL·SQLite 등 표준 SQL을 따르는 모든 백엔드에 공통이다(DB 종류와 무관) — header-only 환불 행은 REQ-RSW-025의 일반 upsert 경로에서 반드시 제외하고 REQ-RSW-029의 별도 경로(사전 중복 정리 포함)로 처리해야 한다 |
| A9 | `_sync_single_order()`의 번들 분기는 `sku=member_isbn`을 조회 키로 삼아 멤버 행을 생성하고(`:265-269`), stale-삭제는 `shopify_line_item_id`만 기준으로 한다(`:287-289`) — 번들 매핑이 존재하는 라인아이템을 처음 전개하든 나중에 재전개하든, 기존 `sku=bundle_sku` 원본 행은 이 두 조건 중 어느 것으로도 갱신·삭제되지 않아 고아로 남는다. 이 한계는 migration `0026_backfill_bundle_lineitems.py`(주석 `:9-26`, 제자리 UPDATE 우회 `:63-64`)와 `test_order_resync.py:255-292`(accepted edge case로 고정된 회귀 테스트)로 이미 문서화되어 있다 | 이 SPEC은 이 로직을 수정하지 않는다(REQ-RSW-031, Exclusions #12) — 번들 매핑이 존재하는 어떤 주문이든 스위프가 처리하면 이 한계가 발동하며(최초 전개·사후 변경 구분 없음), 스위프는 그 노출 빈도만 수동/희귀에서 자동/약 11회·일(v0.4.0 재산정)로 늘린다(§8 C9) |
| A10 | **[v0.5.0 신규, 감사 D3, 미검증]** fulfillment order(배송 위치)의 재배정이 부모 `Order`의 `updated_at`을 갱신한다 — Shopify에서 fulfillment order는 주문과 별개 리소스이며, 이 명제는 이 세션에서도 저장소 어디에서도 검증되지 않았다 | §8 C13이 4% 휴면율(Shopify `updated_at` 변경률)로 위치 재배정 위험의 발생 확률을 경계 짓는 근거가 바로 이 가정이다. **이 가정이 거짓이면**(위치만 바뀐 주문의 `updated_at`이 움직이지 않는다면) 4%는 C13이 다루는 위치 위험에 대해 아무것도 유계화하지 못한다 — C13의 위험 서술 자체(검출기 부재)는 이 가정과 무관하게 유효하지만, "발생 확률이 낮다"는 완화 주장만 이 가정에 의존한다 |

---

## 4. 확정된 설계 결정

이 절은 사용자가 이미 확정한 3개 결정(대상 기준·실행 모델·성능 최적화 범위, 프롬프트 "User-confirmed decisions" 참조)을 재론하지 않는다. 아래는 그 결정들을 구현 가능한 수준으로 구체화한다.

- **D1 (last_resynced_at은 성공/실패 무관하게 항상 전진한다)**: 개별 주문 처리가 예외로 실패해도 `last_resynced_at`을 현재 시각으로 갱신한다(REQ-RSW-011). 대안(실패 시 갱신 보류)은 "poison order" 하나가 라운드로빈 슬롯을 영구히 점유해 나머지 주문의 회전을 막는 결함 부류를 만든다 — 그 대가는 실패한 주문의 재시도가 다음 랩(최대 약 2.14시간, v0.4.0 재산정, §8 C1)까지 지연되는 것뿐이다. 이 지연은 `sync_store()`와의 락 대기 패배(§8 C8)에도 그대로 적용된다. **[HARD 주의, 감사 N4]** 이 필드는 "성공"의 증거가 **아니다** — "선택되어 처리 시도되었다"의 증거일 뿐이다. `acceptance.md`의 모든 보존 계열 AC는 이 필드만으로 성공을 증명하지 않고, 별도의 명시적 성공 증거(실패 0건 또는 실제 반영된 변경값)를 함께 요구한다.
- **D2 (배치 불변 컨텍스트 호이스팅은 신규 스위프 커맨드에만 적용한다)**: `_sync_single_order()`의 시그니처는 배치 단위로 사전 계산 가능한 컨텍스트(번들 매핑, 도서 제목)를 선택적으로 받도록 확장하되(REQ-RSW-021), 이를 실제로 사전 계산해 전달하는 호출부는 신규 `resync_order_sweep` 커맨드뿐이다. 이 옵트인은 호이스팅(REQ-RSW-021/023)에**만** 해당한다 — 환불/배송라인 쓰기 방식 변경(REQ-RSW-024/025)은 `_sync_single_order()` **내부**의 무조건 변경이라 기존 3개 호출부(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`) 전부에 즉시 적용된다(§8 C7).
- **D3 (환불/배송라인은 무조건적 delete-and-recreate 대신 차등 갱신, 자가치유 보존)**: `.all().delete()`를 선행하지 않고, 이번 페이로드에도 여전히 존재하는 행은 제자리에서 갱신하며, Shopify가 더 이상 보고하지 않는 행만 골라서 삭제한다. MySQL은 `supports_update_conflicts_with_target=False`이므로 유니크 키를 지정하는 형태의 upsert(`unique_fields=[...]`)는 `NotSupportedError`로 즉시 실패한다 — 유니크 키 지정 없이 위반된 유니크 제약을 DB가 알아서 판별하는 형태만 쓸 수 있다. header-only 환불 행(`line_item_id IS NULL`, 가정 A8)은 이 upsert 방식 자체로 매치되지 않으므로 별도 경로(REQ-RSW-029)로 분리하며, **[v0.3.0 추가, 감사 N3]** 그 별도 경로는 upsert 전에 이미 존재하는 중복 행을 1건으로 정리하는 자가치유 단계를 포함해야 한다 — 기존 `.all().delete()`가 매 동기화마다 공짜로 제공하던 이 속성을 차등 설계에서도 유지하기 위함이다. 구체적 구현 기법은 `plan.md`에서 다룬다.
- **D4 (실패 집계 후 사이클 종료 시점에 종료 코드 결정)**: `sync_orders.py`의 계약(각 스토어를 끝까지 순회하되 실패 목록을 모아 마지막에 `CommandError`로 종료)을 그대로 커맨드 레벨에 적용한다 — 개별 주문 실패가 사이클을 중단시키지 않는다는 요구사항(REQ-RSW-010)과, 실패가 Task Scheduler의 "마지막 실행 결과"에 드러나야 한다는 요구사항(REQ-RSW-012)을 동시에 만족하는 유일한 조합이다. 위치 조회 실패(REQ-RSW-030(a))도 이 실패 집계에 포함된다 — 위치 조회가 예외 없이 빈 값만 낸 경우(REQ-RSW-030(b))는 실패가 아니라 정상 성공으로 계상한다.
- **D5 (페이싱은 고정 간격, 적응형 백오프 없음)**: Shopify API 호출(주문 조회 + fulfillment 조회) 사이에 최소 **0.3초**(저장소 기존 선례 `repair_refunds.py:36-39` 채택, 가정 A5) 간격만 둔다. 429 응답에 대한 재시도/백오프는 이 SPEC의 범위가 아니다(Exclusions #9, §8 C2) — 페이싱은 속도 제한을 보장하지 않으며, 429가 실제로 발생했을 때 데이터가 훼손되지 않도록 보장하는 것은 REQ-RSW-030의 몫이다.
- **D6 (번들 매핑 전파는 명분에서 제외한다) `[v0.3.0 신규, 감사 N1]`**: 문제 정의 3번에서 번들 관련 이득 주장을 완전히 제거했다. 대안은 migration `0026`의 제자리 UPDATE 방식을 스위프에도 구현하는 것이었으나, 그 변경은 `_sync_single_order()`의 stale-삭제 로직을 `sku` 기준까지 확장해야 하고 이는 기존 3개 호출부 전부에 영향을 미치는 별도 SPEC급 위험 변경이다 — 이 SPEC의 범위를 넘는다고 판단해 채택하지 않았다. 남은 잔여 위험은 §8 C9에 명시한다.
- **D7 (대상 연령 상한 30일 재확정 + `--days` 이스케이프 해치) `[v0.4.0 신규]`**: 사용자가 대상 연령 상한을 60일에서 30일로 재확정했다 — 이는 재론이 아니라 이미 확정된 결정이며 이 SPEC은 그것을 구현할 뿐이다. 재측정된 프로덕션 데이터(§2)가 보여주듯 이 변경은 더 이상 무손실이 아니다(320건이 새로 제외된다) — 새 근거는 그 제외 밴드의 휴면성이다(§2 상세 참조). 이 결정은 REQ-RSW-003(b)의 기본값을 30으로 갱신하고, 제외 밴드에 남는 위치 재배정 미감지 위험(§8 C13)에 대한 운영상 이스케이프 해치로 REQ-RSW-035(`--days` CLI 인자, 기본값 30, `backfill_missing_orders.py`의 `--created-since` 관례 미러링)를 신설한다 — 이 위험에는 검출기가 없으므로(§8 C13) `--days`는 검출 지연을 줄이지 않고 발현 후 복구 시간(MTTR)만 줄이는 수단이다(`[v0.5.0 명시]`). Exclusions #10은 이에 맞춰 축소된다 — `not_shipped` 판정 기준 자체는 여전히 상수로 고정되지만, 연령 상한은 이제 운영상의 이스케이프 해치로서 CLI 인자로 조정 가능하다(정책 자체가 "언제든 자유롭게 바뀌는 값"이 되었다는 뜻은 아니다 — 인자를 생략한 실행은 여전히 항상 기본값 30을 쓴다).

---

## 5. Requirements (EARS)

REQ 접두사는 `REQ-RSW-`를 쓴다. **REQ-RSW-028과 REQ-RSW-032는 결번이다** — 028은 §8 C6으로 이동(비규범 권고, iteration 1 D12), 032는 삭제됨(비규범 범위 면책 선언이었음, iteration 2 N6/MP-2). 두 번호 모두 인용 안정성을 위해 재부여하지 않는다(SPEC-ORDER-027 REQ-RACKRECV-006 선례와 동일).

### 모듈 1 — 모델/마이그레이션 `[NEW]`

**REQ-RSW-001** (Ubiquitous) [HARD]
`Order` 모델(`backend/order/models.py:30`)은 신규 필드 `last_resynced_at`(nullable `DateTimeField`)을 **shall** 가지며, 마이그레이션 `0045`(의존성: `0044_lineitem_original_sku`)로 반영된다.

**REQ-RSW-002** (Ubiquitous) [HARD]
`last_resynced_at`에는 DB 인덱스가 **shall** 존재한다 — 라운드로빈 정렬(REQ-RSW-005)이 정렬 단계에서 `orders_order` 테이블 전체를 정렬용 임시 파일(filesort)로 처리하는 상황에 의존하지 않도록 한다. 대상 판정 쿼리가 `shopify_created_at` 필터(기존 인덱스, `models.py:99`)와 `last_resynced_at` 정렬을 동시에 요구하므로, 이 인덱스는 `(last_resynced_at, shopify_created_at)` 복합 인덱스여야 **shall** 하며, MySQL `EXPLAIN`으로 정렬이 filesort가 아님을 확인하는 것이 완료 조건에 포함된다(DoD, plan.md 참조).

### 모듈 2 — 대상 판정 (스위프 큐잉) `[NEW]`

**REQ-RSW-003** (Ubiquitous) [HARD]
THE 시스템은 주문이 다음 두 조건을 **모두** 만족할 때만 스위프 대상으로 **shall** 판정한다: (a) 그 주문에 속한 `LineItem` 중 최소 1건의 `logistics_status == "not_shipped"`, (b) `shopify_created_at >= (현재 시각 - D일)`, D의 기본값은 **30**이다(§4 D7, 사용자 재확정 결정, v0.4.0 — 60일에서 축소). D는 REQ-RSW-035의 `--days` 인자로 재정의될 수 있으며, 인자를 생략한 실행은 항상 30을 쓴다.

**REQ-RSW-004** (Ubiquitous) [HARD]
대상 판정 결과 집합은 조건을 만족하는 각 주문을 정확히 1행으로만 **shall** 포함해야 하며, 그 주문에 매칭되는 `LineItem` 건수에 비례해 같은 주문이 중복 반환되어서는 **shall not** 안 된다(fanout 금지). 구체적 구현 기법(존재 서브쿼리 등)은 `plan.md`에서 다룬다.

**REQ-RSW-005** (Ubiquitous) [HARD]
THE 시스템은 대상 주문을, 한 번도 스윕되지 않은 주문(`last_resynced_at IS NULL`)과 오래 전에 스윕된 주문이 최근에 스윕된 주문보다 먼저 처리되도록 **shall** 정렬한다(가정 A4, MySQL 네이티브 동작). 구체적 SQL 파라미터 사용 여부는 `plan.md`에서 다루며, 이 요구사항의 검증은 처리 순서라는 결과로 이루어진다(가정 A4a).

**REQ-RSW-006** (Ubiquitous) [HARD]
THE 시스템은 정렬된 대상 주문 중 상위 N건만 **shall** 처리한다. N의 기본값은 40이다(인자를 생략한 실행에도 적용된다).

### 모듈 3 — 신규 관리 커맨드 `resync_order_sweep` `[NEW]`

**REQ-RSW-007** (Ubiquitous) [HARD]
THE 시스템은 `python manage.py resync_order_sweep`로 실행 가능한 신규 관리 커맨드를 **shall** 제공한다.

**REQ-RSW-008** (Optional) [HARD]
WHERE `--count <N>` 인자가 주어지면, THE 시스템은 기본값 40 대신 그 값을 **shall** 사용한다.

**REQ-RSW-009** (Optional) [HARD]
WHERE `--store <gimssine|etoile|all>` 인자가 주어지면, THE 시스템은 해당 스토어(들)의 대상 주문만 **shall** 처리한다. 기본값은 `all`이다.

**REQ-RSW-035** (Optional) [HARD] `[v0.4.0 신규]`
WHERE `--days <D>` 인자가 주어지면, THE 시스템은 REQ-RSW-003(b)의 기본값 30 대신 그 값을 **shall** 사용한다. 이는 §8 C13에 명시된 잔여 위험(30일 창 밖으로 밀려난, `PurchaseOrder`가 연결된 주문의 배송 위치 재배정을 스위프가 감지하지 못하는 위험)에 대한 운영상 이스케이프 해치다 `[v0.5.0 명시]` — 이 위험에는 검출기가 없으므로 `--days`는 검출 지연을 줄이지 않으며, 위험이 외부 신호(예: 위치 오류 신고)로 드러난 뒤 코드 변경 없이 더 넓은 창으로 일회성 catch-up 스위프를 실행해 복구 시간을 줄이는 수단이다. 인자를 생략하면 항상 30이 적용된다(REQ-RSW-003).

**REQ-RSW-010** (Unwanted) [HARD]
**If** 대상 주문 하나의 처리 중 예외가 발생하면, **then** 시스템은 그 예외로 나머지 대상 주문의 처리를 **shall not** 중단하고 계속 진행한다 — 한 주문의 처리 실패가 다른 주문의 처리나 커밋을 막지 않는다(구체적 격리 기법은 `plan.md`, `backfill_missing_orders.handle()`의 per-order 트랜잭션 패턴, `backend/order/management/commands/backfill_missing_orders.py:131-149` 재사용).

**REQ-RSW-011** (Event-Driven) [HARD]
**When** 대상 주문 하나의 처리가 완료되면(성공/실패 무관, "변경 없음" 결과도 포함), THE 시스템은 그 주문의 `last_resynced_at`을 현재 시각으로 **shall** 갱신한다(설계 결정 D1). **이 갱신은 그 주문이 성공했다는 증거가 아니다(§4 D1 [HARD 주의]).**

**REQ-RSW-012** (Complex) [HARD]
**While** 하나 이상의 대상 주문이 예외로 실패한 상태에서, **when** 모든 대상 주문에 대한 처리 시도가 끝나면, THE 시스템은 0이 아닌 종료 코드(`CommandError`)를 **shall** 반환한다(설계 결정 D4, `sync_orders.py`의 "끝까지 순회 후 실패 집계" 계약 재사용).

### 모듈 4 — Fulfillment Location 갱신 (문제 정의 1) `[MODIFY]`

**REQ-RSW-013** (Ubiquitous) [HARD]
스위프가 처리하는 각 대상 주문에 대해, THE 시스템은 `_build_fulfillment_location_data()`를 호출해 `Order.location`과 각 `LineItem.location`을 최신값으로 **shall** 갱신한다 — `sync_store()`가 기존 주문에 적용하는 "저장된 위치 재사용, API 호출 생략" 단축 경로(`shopify_orders.py:420-428`)를 스위프에는 **shall not** 적용한다. 이 요구사항은 REQ-RSW-030의 두 예외(호출 실패, 정상-빈값)에 종속된다.

**REQ-RSW-014** (Ubiquitous) [HARD]
THE 시스템은 스위프가 발생시키는 Shopify API 호출(주문 조회 + fulfillment 조회) 사이에 최소 0.3초의 간격을 **shall** 둔다(가정 A5, 저장소 기존 선례 `repair_refunds.py:36-39` 채택, 설계 결정 D5). 이 간격은 속도 제한 준수를 보장하지 않는 최선 노력 조치다.

### 모듈 5 — Close/Cancel 감지 (문제 정의 2) `[MODIFY]`

**REQ-RSW-015** (Ubiquitous) [HARD]
스위프는 대상 주문마다 `orders/{shopify_order_id}.json` 단건 엔드포인트를 **shall** 사용하여 조회하며, `status=open` 목록 피드(`fetch_all_open_orders()`)는 **shall not** 사용한다. (Shopify가 이 엔드포인트에서 종료/취소된 주문도 반환한다는 사실은 가정 A3이며, 이 요구사항 자체는 시스템이 어느 엔드포인트를 쓰는지만 규정한다.)

### 모듈 6 — Watermark/락 격리 `[NEW/EXISTING]`

**REQ-RSW-016** (Ubiquitous) [HARD]
THE 시스템은 스위프 실행 중 `StoreSyncWatermark`의 `last_synced_updated_at` 또는 `last_run_at` 어느 필드도 **shall not** 갱신한다 — 이 두 필드는 `sync_store()` 전용이다(`backfill_missing_orders`가 이미 확립한 "워터마크를 절대 전진시키지 않는다"는 계약과 동일 패턴).

**REQ-RSW-017** (Ubiquitous) [HARD]
THE 시스템은 스위프의 쓰기 경로에서 명시적 애플리케이션 레벨 락(`select_for_update()` 등)을 **shall not** 사용한다. (`sync_orders.py:60`이 스토어 전체를 하나의 `transaction.atomic()`으로 감싸 그동안 그 트랜잭션이 쓰는 모든 행에 대해 DB 엔진(InnoDB) 차원의 암묵적 행 잠금을 보유하며, 스위프가 같은 행을 건드리면 잠금 대기가 발생할 수 있다 — 이 상호작용은 §8 C8에 별도로 기술한다.)

### 모듈 7 — 매뉴얼 상태/보정 불변식 보존 `[EXISTING]`

**REQ-RSW-018** (Ubiquitous) [HARD]
스위프가 호출하는 동기화 경로는 `_sync_single_order()`의 매뉴얼 필드 제외 규약(`Order.status`/`Order.ready_to_ship`/`LineItem.purchase_status`/`LineItem.logistics_status`가 Shopify `defaults`에서 제외됨, `shopify_orders.py:140-147`/`:229-230`)을 그대로 **shall** 상속한다 — 스위프 전용의 별도 쓰기 경로를 신설하지 않는다.

**REQ-RSW-019** (Ubiquitous) [HARD]
스위프가 호출하는 동기화 경로는 `LineItem.original_sku` 보호 로직(`shopify_orders.py:209-224`의 `protected_sku_by_key` 조회, 번들 분기 `:256-270`과 비번들 분기 `:271-285` 모두)을 그대로 **shall** 상속한다.

**REQ-RSW-020** (Ubiquitous) [HARD]
스위프는 `LineItem.received_quantity`를 직접 **shall not** 쓴다 — 입고 판정은 이 SPEC이 건드리지 않는 `_process_warehouse_receipt_rows`(`backend/order/purchase_order_views.py:2392-2579`) 전용이다.

### 모듈 8 — `_sync_single_order()` 리팩터: 배치 불변 컨텍스트 `[MODIFY]`

**REQ-RSW-021** (Ubiquitous) [HARD]
`_sync_single_order()`(`shopify_orders.py:104`)는 배치 단위로 사전 계산 가능한 컨텍스트(번들 매핑, 도서 제목)를 선택적으로 주입받을 수 있도록 시그니처가 **shall** 확장된다. 이 컨텍스트가 주어지지 않으면 함수 내부에서 기존과 동일하게(`:191-196`/`:198-207`) 계산해야 **shall** 한다. 구체적 파라미터 형태는 `plan.md`에서 다룬다.

**REQ-RSW-022** (Ubiquitous) [HARD]
`sync_single_order_from_shopify()`(`:334-352`)와 `backfill_missing_orders`(`management/commands/backfill_missing_orders.py`)는 이 시그니처 확장 이후에도 신규 배치 컨텍스트 파라미터를 **shall not** 전달한다. **(이 요구사항은 배치 컨텍스트 호이스팅에만 해당한다 — 환불/배송라인 쓰기 방식 변경(REQ-RSW-024/025/029)은 `_sync_single_order()` 내부의 무조건 변경이라 이 세 호출부에도 그대로 적용되며, "동작 전체가 무변경"이 아니다. §8 C7 참조.)**

**REQ-RSW-023** (Ubiquitous) [HARD]
THE 시스템은 스위프 사이클마다 배치 컨텍스트(번들 매핑, 도서 제목)를 정확히 1회씩 계산해, 그 사이클이 처리하는 모든 대상 주문의 `_sync_single_order()` 호출에 **shall** 재사용한다 — 주문별 재계산을 금지한다.

### 모듈 9 — `_sync_single_order()` 리팩터: 환불/배송라인 차등 갱신 `[MODIFY]`

**REQ-RSW-024** (Ubiquitous) [HARD]
`_sync_single_order()`의 `ShippingLine` 쓰기(`:291-304`)는 무조건적인 `.all().delete()` + 재삽입 대신, 이번 페이로드에도 여전히 존재하는 배송라인 행을 그 행 고유의 실제 식별자(주문 + `shopify_shipping_line_id`, `models.py:320`의 기존 unique 제약)로 매칭해 제자리에서 갱신하는 차등 갱신으로 **shall** 대체한다 — Shopify가 더 이상 보고하지 않는 행만 별도로 삭제한다. `shopify_shipping_line_id`는 nullable이 아니므로(가정 A8과 달리) NULL 매칭 문제가 없다.

**REQ-RSW-025** (Ubiquitous) [HARD]
`_sync_single_order()`의 `Refund` 쓰기(`:306-329`)는 무조건적인 `.all().delete()` 선행 없이, `line_item_id`가 NULL이 **아닌** 환불 행에 한해 그 행 고유의 실제 식별자(주문 + `shopify_refund_id` + `line_item_id`, `models.py:342`의 기존 unique 제약)로 매칭해 제자리에서 갱신하는 차등 갱신으로 **shall** 대체하고, Shopify가 더 이상 보고하지 않는 환불 행만 별도로 삭제한다. `line_item_id`가 NULL인 header-only 환불 행은 이 경로에서 **shall not** 처리하며 REQ-RSW-029를 따른다(가정 A8).

**REQ-RSW-026** (Ubiquitous) [HARD]
이 리팩터(REQ-RSW-024/025/029) 적용 후에도, 이전에 저장되었고 이번 페이로드에도 여전히 존재하는 환불/배송라인 행의 데이터(수량/가격/subtotal/total_tax 등)를 **shall not** 유실한다 — 차등 갱신 적용 후의 최종 상태는 기존 delete-and-recreate 방식과 동일해야 한다.

**REQ-RSW-029** (Unwanted) [HARD]
**If** 환불 페이로드에 `line_item_id`가 NULL인 header-only 환불 행(순수 배송/금액 환불, `shopify_orders.py:314`의 `or [{}]`가 만드는 형태)이 포함되어 있으면, **then** 시스템은 그 행을 REQ-RSW-025의 upsert 경로로 **shall not** 처리하고, 대신 NULL을 인식하는 조회로 매칭해 갱신한다 — 동일 (주문, `shopify_refund_id`) 조합에 대해 반복되는 스위프 사이클마다 중복 행이 INSERT되어서는 **shall not** 안 된다. **[v0.3.0 추가, 감사 N3]** 이 NULL 키에는 유니크 제약이 걸리지 않으므로(가정 A8) 이력 데이터나 `sync_store()`와의 동시 실행 경합(§8 C8)으로 인해 동일 (주문, `shopify_refund_id`, NULL) 조합의 행이 이미 2건 이상 존재하는 상태가 될 수 있다 — 기존 `.all().delete()` 방식은 이 상태를 다음 동기화마다 자동으로 정리했으나(자가치유), 단순 조회 기반 매칭은 그 조회가 2건 이상과 매치될 때 예외를 던져 그 주문을 영구적으로 실패시킬 수 있다. 시스템은 upsert를 시도하기 **전에** 그 키에 매칭되는 기존 행이 2건 이상이면 1건만 남기고 나머지를 삭제하여 이 자가치유 능력을 **shall** 복원해야 한다.

### 모듈 10 — Fulfillment Location 실패/빈값 처리 `[NEW]`

**REQ-RSW-030** (Unwanted) [HARD]
`_build_fulfillment_location_data()`는 두 가지 서로 다른 상황에서 빈 값(`""`/`{}`)을 반환할 수 있다 — (i) 호출 자체가 예외로 실패한 경우(기존 계약, `shopify_orders.py:100-101`), (ii) 호출은 성공했지만 Shopify가 반환한 `assigned_location.name`에 언더스코어 구분자가 없거나(`:88-89`) `fulfillment_orders`가 빈 배열이라 정상적으로 빈 값을 낸 경우(`test_order_location.py:62`가 이 정상 동작을 고정). 스위프는 이 두 경우 모두에서 위치 데이터를 조용히 지우지 않도록 다음을 **shall** 수행한다:
**(a) 예외 경로**: 스위프는 그 실패를 명시적으로 전달받아(하위호환 선택적 파라미터, 구체 설계는 `plan.md`) 그 주문의 `Order.location`/`LineItem.location`에 빈 값을 **shall not** 기록하고(기존에 저장된 값을 그대로 유지), 그 주문의 처리를 실패로 계상한다(REQ-RSW-011/012의 실패 집계에 포함).
**(b) 정상-빈값 경로**: 호출이 예외 없이 성공했으나 반환된 `order_location`(또는 특정 라인아이템의 위치)이 빈 문자열이면, 스위프는 그 특정 값에 대해서만(주문 전체가 아니라 위치 단위로) `Order.location` 또는 해당 `LineItem.location`을 빈 값으로 **shall not** 덮어쓰며 기존 저장값을 그대로 유지한다 — 이 경우는 실패가 아니므로 그 주문의 처리는 정상 성공으로 계상된다(다른 필드는 정상적으로 갱신됨).
기존 3개 호출부(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`)는 이 정책의 영향을 받지 않는다 — (a)는 신규 옵션을 사용하지 않는 한 발동하지 않고(기존 계약 `test_order_location.py:79-88` 그대로 유지), (b)는 스위프 자신의 값-병합 로직(구체 설계는 `plan.md`)이며 `_build_fulfillment_location_data()`나 `_sync_single_order()`의 시그니처/동작을 바꾸지 않는다.

### 모듈 11 — 번들 전파 범위 (문제 정의 3 축소) `[EXISTING]`

**REQ-RSW-031** (Ubiquitous) [HARD]
스위프는 `_sync_single_order()`의 번들 stale-삭제 로직(`:287-289`, `shopify_line_item_id` 기준)을 **shall not** 수정한다 — 번들 매핑이 존재하는 라인아이템을 재동기화할 때(최초 전개든 사후 변경이든 무관하게) 고아 `sku=bundle_sku` 행이 남는 기존 알려진 한계(migration `0026:9-26/63-64`, `test_order_resync.py:255-292`)를 이 SPEC은 **shall not** 정리한다(정리 로직을 추가하지 않는다). **[v0.3.0 확장, 감사 N1]** v0.2.0은 이 배제를 "사후 변경"에만 한정했으나, 최초 전개 자체가 이미 같은 방식으로 고아 행을 만든다(`update_or_create(..., sku=member_isbn, ...)`가 조회 키로 `sku`를 쓰므로 기존 `sku=bundle_sku` 행에 매치되지 않음, `:265-269`) — 이 REQ는 최초 전개를 포함한 번들 매핑 존재 전반에 적용된다.

### 모듈 12 — 부분 입고 대상 포함 및 보존 (문제 정의 보완) `[NEW]`

**REQ-RSW-033** (Ubiquitous) [HARD]
부분 입고된(즉 `received_quantity`가 0보다 크지만 `quantity`에 도달하지 못한) `LineItem`을 가진 주문은, 그 라인아이템이 `logistics_status="not_shipped"`로 남아 있는 한(`purchase_order_views.py:2415-2418`/`:2549-2550`, 부분 입고는 상태를 전환하지 않음) REQ-RSW-003의 대상 판정에서 정상적으로 **shall** 포함된다 — 실수로 배제되지 않는다는 사실을 이 SPEC은 명시적으로 확인한다.

**REQ-RSW-034** (Ubiquitous) [HARD]
스위프가 갱신하는 각 `LineItem`에 대해, `received_quantity`/`received_at`/`shipped_quantity`/`shipped_at`/`rack_number`/`damaged_quantity`/`confirmed_price`/`confirmed_distributor`/`confirmed_at`/`original_sku`의 값은 **shall** 보존된다. **[v0.3.0 정정, 감사 N8]** 이 보존의 실제 근거는 REQ-RSW-018/019가 아니다(그 두 REQ는 각각 4개 상태 필드 제외 규약과 `original_sku` 보호 로직만 다룬다) — 진짜 근거는 이 필드들이 전부 `_sync_single_order()`의 Shopify 동기화 `defaults` 딕셔너리(`shopify_orders.py:231-243`의 `common_defaults`)에 **애초에 포함되어 있지 않다**는 사실이다. **(알려진 잔여 위험, §8 C10)**: 이 보존은 행이 **갱신**되는 경우에 한한다 — `purchase_orders__isnull=True`인 라인아이템이 Shopify 페이로드에서 완전히 사라지면(`:287-289`) 그 행 자체가 삭제되며, 그 경우 위 필드들도 행과 함께 사라진다. 이 SPEC은 이 기존 stale-삭제 경로에 추가 보호를 두지 않는다.

### 모듈 13 — 스케줄러 등록 `[NEW]`

**REQ-RSW-027** (Ubiquitous) [HARD]
THE 시스템은 신규 커맨드를 `scripts/resync_order_sweep.bat` + 기존 `scripts/run_hidden.vbs`로 Windows 작업 스케줄러에 등록 가능한 형태로 **shall** 제공한다(`scripts/sync_orders.bat` 구조 미러링: 작업 디렉터리 `backend/` 고정, `PYTHONIOENCODING=utf-8`, 로그 파일, 종료 코드 전파).

---

## 6. Traceability (REQ → AC)

| REQ | AC |
|-----|-----|
| REQ-RSW-001 | AC 없음 — DoD 검증(`backend/order/migrations/0045_*.py` 존재 + `Order._meta.get_field("last_resynced_at")` 확인) |
| REQ-RSW-002 | AC 없음 — DoD 검증(MySQL `EXPLAIN`으로 정렬이 filesort가 아님을 확인, `plan.md` 참조) |
| REQ-RSW-003 | AC-RSW-001, AC-RSW-002, AC-RSW-003, AC-RSW-004, AC-RSW-035b |
| REQ-RSW-004 | AC-RSW-005 |
| REQ-RSW-005 | AC-RSW-006 |
| REQ-RSW-006 | AC-RSW-007, AC-RSW-007b |
| REQ-RSW-007 | AC-RSW-007, AC-RSW-011, AC-RSW-012 |
| REQ-RSW-008 | AC-RSW-007 |
| REQ-RSW-009 | AC 없음 — DoD 검증(`--store` 인자 파싱, `sync_orders.py`의 동일 패턴 재사용이라 별도 AC 불필요) |
| REQ-RSW-010 | AC-RSW-010 |
| REQ-RSW-011 | AC-RSW-008, AC-RSW-009 |
| REQ-RSW-012 | AC-RSW-011, AC-RSW-012 |
| REQ-RSW-013 | AC-RSW-014 |
| REQ-RSW-014 | AC-RSW-026 |
| REQ-RSW-015 | AC-RSW-015, AC-RSW-016 |
| REQ-RSW-016 | AC-RSW-013 |
| REQ-RSW-017 | AC 없음 — DoD 검증(코드 리뷰, 스위프 코드에 `select_for_update` 부재 확인) |
| REQ-RSW-018 | AC-RSW-017, AC-RSW-018 |
| REQ-RSW-019 | AC-RSW-019, AC-RSW-020 |
| REQ-RSW-020 | AC 없음 — DoD 검증(`git diff`로 스위프 코드가 `received_quantity`를 쓰지 않는지 확인) |
| REQ-RSW-021 | AC-RSW-024, AC-RSW-025 |
| REQ-RSW-022 | AC-RSW-025 |
| REQ-RSW-023 | AC-RSW-024 |
| REQ-RSW-024 | AC-RSW-023 |
| REQ-RSW-025 | AC-RSW-021, AC-RSW-022, AC-RSW-029 |
| REQ-RSW-026 | AC-RSW-021, AC-RSW-023, AC-RSW-029 |
| REQ-RSW-027 | AC 없음 — DoD 검증(`scripts/resync_order_sweep.bat` 파일 존재 확인) |
| REQ-RSW-028 | **결번(§8 C6으로 이동)** |
| REQ-RSW-029 | AC-RSW-029, AC-RSW-029b |
| REQ-RSW-030 | AC-RSW-014b(예외 경로), AC-RSW-030(정상-빈값 경로) |
| REQ-RSW-031 | AC 없음 — DoD 검증(`git diff`로 `:287-289` 무변경 확인 + `test_order_resync.py::test_resync_after_mapping_change_reexpands_with_current_mapping_orphans_removed_member` 무수정 통과 확인) |
| REQ-RSW-032 | **결번(§8 C11로 이동, 비규범 성능 참고치)** |
| REQ-RSW-033 | AC-RSW-033 |
| REQ-RSW-034 | AC-RSW-034 |
| REQ-RSW-035 | AC-RSW-035, AC-RSW-035b |

> **[HARD] 추적표 무결성 규칙**: REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다. AC 없이 DoD 검사만으로 보증되는 REQ는 "(AC 없음 — DoD 검증)"으로 명시한다.

---

## 7. Exclusions (What NOT to Build)

1. **전체 배치 재동기화(모든 대상 주문을 한 사이클에) — 하지 않는다.** 라운드로빈(사이클당 N=40건)만 구현한다. 사용자 확정 결정(실행 모델).
2. **Webhook 기반 실시간 동기화 — 하지 않는다.** 사용자 확정 결정(실행 모델). 이 SPEC은 폴링 기반 라운드로빈만 다룬다.
3. **`StoreSyncWatermark` 갱신 — 하지 않는다(REQ-RSW-016).** 스위프는 `sync_store()`의 대체재가 아니다.
4. **`_process_warehouse_receipt_rows`(`purchase_order_views.py:2392-2579`) 수정 — 하지 않는다.** 입고 쓰기 경로는 이 SPEC의 범위 밖이다.
5. **매뉴얼 필드(Order.status/ready_to_ship, LineItem.purchase_status/logistics_status)를 Shopify 값으로 덮어쓰는 로직 신설 — 하지 않는다(REQ-RSW-018).**
6. **N(사이클당 처리 건수)의 동적/적응형 조정(예: 실패율 기반 자동 축소, 서버 부하 기반 자동 조절) — 하지 않는다.** 고정 기본값(40) + CLI 인자(`--count`)만 제공한다.
7. **스위프 전용 UI 대시보드/진행률 화면 신설 — 하지 않는다.** `OrderSyncStatusView` 확장 여부는 `plan.md`의 권고 사항으로만 남긴다(§8 C6).
8. **`sync_store()`/`backfill_missing_orders`의 배치 컨텍스트 호이스팅 옵트인 — 하지 않는다.** 두 호출부는 신규 배치 컨텍스트 파라미터를 전달하지 않는다(REQ-RSW-022, 설계 결정 D2). **단, 환불/배송라인 쓰기 방식 변경(REQ-RSW-024/025/029)은 이 배제 대상이 아니다 — `_sync_single_order()` 내부 변경이라 세 호출부 모두에 무조건 적용된다(§8 C7).**
9. **Shopify 429 응답에 대한 재시도/백오프 로직 신설 — 하지 않는다.** 고정 페이싱(호출 간 최소 0.3초, 설계 결정 D5)만으로 부하를 경감하는 것을 목표로 하며, 429 자체에 대한 적응형 재시도 전략은 후속 과제로 남긴다(§8 C2). 429 발생 시 데이터가 훼손되지 않도록 하는 것은 REQ-RSW-030이 담당한다.
10. **`not_shipped` 판정 기준을 설정 가능한 값으로 만들기 — 하지 않는다.** `[v0.4.0 축소]` 사용자 확정 결정(대상 기준)이며, `not_shipped` 조건 자체는 이 SPEC에서 상수로 고정한다. **연령 상한(일수)은 더 이상 이 배제 대상이 아니다** — REQ-RSW-035가 `--days` CLI 인자(기본값 30)로 운영상 조정 가능한 이스케이프 해치를 신설한다(§4 D7, §8 C13 — 검출 수단이 아니라 복구 수단이다). 이는 "정책이 임의로 바뀔 수 있다"는 뜻이 아니다 — 인자를 생략한 실행은 항상 기본값 30을 쓰며, 기본값 자체를 바꾸려면(예: 정책 변경으로 45일 확정) 여전히 이 SPEC의 REQ-RSW-003(b)를 직접 수정해야 한다.
11. **레거시 데이터(예: 이미 31일이 지나 기본 대상에서 빠지는 오래된 not_shipped 주문)에 대한 소급 처리 — 하지 않는다.** 이 SPEC은 신규/현재 대상 주문의 반복 스위프만 다루며, 30일(기본값) 상한을 넘긴 주문의 별도 백필은 범위 밖이다. 코드 변경 없이 넓은 창으로 다시 훑고 싶다면 REQ-RSW-035의 `--days`로 일회성 실행이 가능하다 — 다만 이는 소급 "처리"가 아니라 대상 판정 창을 넓힌 통상적 스위프 실행일 뿐이다.
12. **[v0.3.0 확장, 감사 N1] 번들 매핑이 존재하는 라인아이템의 고아 `sku=bundle_sku` 행 정리 — 최초 전개·사후 변경 구분 없이 하지 않는다.** `_sync_single_order()`의 기존 동작(변경 전부터 존재, migration `0026`/`test_order_resync.py:255-292`로 문서화된 accepted behavior, REQ-RSW-031)을 그대로 상속하며, 스위프는 이 결함의 노출 빈도만 늘린다는 사실을 알려진 제약(§8 C9)에 명시한다. [v0.2.0은 이 배제를 "사후 변경"으로만 한정해, 남겨둔 명분("최초 1회 번들 확장")과 모순되었다(감사 N1) — v0.3.0은 문제 정의에서 번들 관련 명분을 완전히 제거하고 이 배제를 최초 전개까지 포괄하도록 넓혀 그 모순을 해소했다.] 이를 고치려면 `_sync_single_order()`의 stale-삭제 로직을 `sku` 기준까지 확장해야 하는데, 이는 기존 3개 호출부 전부에 영향을 미치는 별도 SPEC급 변경이다.
13. **`_build_fulfillment_location_data()`의 기존 예외-삼킴 계약 자체를 변경 — 하지 않는다.** 기존 3개 호출부(`sync_store()`, `sync_single_order_from_shopify()`, `backfill_missing_orders`)가 의존하는 `("", {})` 반환 계약(`test_order_location.py:79-88`)은 그대로 유지하며, 스위프만 선택적 파라미터로 실패를 전파받는다(REQ-RSW-030(a)). 정상-빈값 경로(REQ-RSW-030(b))의 병합도 이 함수 내부가 아니라 스위프 자신의 호출 지점에서 이루어진다.

---

## 8. 알려진 제약 / 후속 과제

| # | 내용 |
|---|------|
| C1 | §4 D1에 따라 실패한 주문도 `last_resynced_at`이 전진하므로, 그 주문의 재시도는 다음 사이클이 아니라 다음 랩(대상 1,029건 ÷ N=40 ≈ 25.73사이클 × 5분 ≈ 약 2.14시간, v0.4.0 재산정)까지 지연될 수 있다. 반복적으로 실패하는 특정 주문이 관측되면 알림/모니터링을 추가하는 것이 후속 과제다 |
| C2 | Shopify 429(rate limit) 응답에 대한 적응형 백오프가 없다(설계 결정 D5, Exclusions #9) — 고정 페이싱(0.3초/호출, 저장소 기존 선례 채택)만으로 부하를 경감한다. `sync_store()`(5분 주기)와 수동 재동기화 버튼이 같은 상점의 같은 속도 제한 버킷을 동시에 소비하므로 이 페이싱은 보장이 아니다 — 429 발생 시 데이터 훼손을 막는 진짜 안전망은 REQ-RSW-030이다. 운영 중 429가 자주 관측되면 후속 SPEC에서 재시도/백오프 전략을 추가 검토한다 |
| C3 | `OrderSyncStatusView`(`views.py:99`) 확장 여부가 미정이다 — `plan.md`가 권고안만 제시하며, 실제 구현 여부는 이 SPEC의 승인 과정에서 사용자가 별도로 결정한다 |
| C4 | `[v0.4.0 갱신]` 대상 판정 기준 중 `not_shipped` 조건은 여전히 상수로 고정된다(Exclusions #10) — 정책 변경(예: 조건 자체를 바꾸는 것) 시 별도 SPEC이 필요하다. **연령 상한(기본값 30일)은 더 이상 완전한 상수가 아니다** — REQ-RSW-035의 `--days` CLI 인자로 실행 단위로 조정 가능하지만, 인자를 생략하면 항상 기본값 30이 적용되며 그 **기본값 자체**를 바꾸려면(정책 재확정) 여전히 이 SPEC의 REQ-RSW-003(b)를 직접 수정해야 한다 — `--days`는 운영상 이스케이프 해치이지 정책 변경 메커니즘이 아니다 |
| C5 | 이 프로젝트의 DB는 **MySQL**(RDS)이다 — 로컬 pytest와 운영 모두 `backend/.env`의 `DB_ENGINE=django.db.backends.mysql`을 따르는 동일 RDS 인스턴스를 바라본다. REQ-RSW-024/025/029의 차등 갱신은 `unique_fields`를 지정하지 않는 형태(`ON DUPLICATE KEY UPDATE`가 위반된 유니크 키를 알아서 판별)와 NULL 안전 별도 경로(REQ-RSW-029, 자가치유 포함)의 조합으로 MySQL에서 동작해야 한다. 구체적 구현과 검증 절차는 `plan.md`에서 다룬다 |
| C6 | (구 REQ-RSW-028, 비규범 권고) 운영자가 스위프 진행 상황(예: 마지막 사이클 처리 건수, 대상 잔여 건수)을 UI에서 확인하길 원하면 `OrderSyncStatusView`(`views.py:99`) 확장을 검토할 수 있다 — 이 SPEC은 이를 구현하지 않으며, `plan.md`가 향후 확장 방향만 권고한다 |
| C7 | REQ-RSW-022("배치 컨텍스트 호이스팅에 옵트인하지 않는다")는 `sync_store()`/`sync_single_order_from_shopify()`/`backfill_missing_orders`의 **전체** 동작이 무변경이라는 뜻이 아니다 — 환불/배송라인 쓰기 방식 변경(REQ-RSW-024/025/029)은 `_sync_single_order()` 내부에 있어 이 세 호출부 전부에 즉시, 무조건 적용된다. Run 단계에서 이 세 회귀 스위트(`test_shopify_orders.py`, `test_order_resync.py`, `test_backfill_missing_orders_command.py`)를 반드시 무수정 통과시켜야 한다 |
| C8 | `sync_orders.py:60`이 스토어 전체 `sync_store()`를 하나의 `transaction.atomic()`으로 감싸 그동안 쓰는 모든 order/line_item 행에 DB 엔진(InnoDB) 차원의 암묵적 행 잠금을 커밋 시점까지 보유한다(1회 약 16초). 스위프는 같은 행을 쓸 수 있다 — 겹치면 한쪽이 락 대기 타임아웃이나 중복 키 충돌로 실패한다. 설계 결정 D1 때문에 락 대기 패배는 다음 사이클이 아니라 다음 랩(~2.14시간, v0.4.0 재산정) 지연을 뜻하고, 매 겹침마다 `CommandError`가 발생해 스케줄러 경보가 울릴 수 있다. 두 작업 모두 5분 트리거다 — 겹침 빈도가 운영상 문제가 되면 후속 과제로 락 조정을 검토한다. **이 동시성 경합은 header-only 환불 중복 발생의 확실한 경로 중 하나이기도 하다(REQ-RSW-029가 그 결과를 다룬다)** |
| C9 | **[v0.3.0 확장, 감사 N1]** 번들 매핑이 존재하는 라인아이템의 고아 `sku=bundle_sku` 행(§1 문제 정의 3번, REQ-RSW-031, Exclusions #12)은 이 SPEC 적용 전에도 존재하던 `_sync_single_order()`의 알려진 한계이며, **최초 전개와 사후 변경을 구분하지 않고 둘 다 적용된다**. 스위프는 그 노출 빈도를 수동/희귀(사용자가 개별 주문을 수동 재동기화할 때만)에서 자동/약 11회·일(대상 주문마다 랩당 1회, 랩은 약 2.14시간, v0.4.0 재산정)로 늘린다. 결과 상태는 `bundle_sku` 원본 행 + 멤버 N행이 모두 전량(미분할) 수량을 들고 공존하는 것이며, 수량 집계 규약에 오염 위험이 있다. **이는 이 SPEC이 알고도 남겨두는 명시적 개방 위험이다** — 이 SPEC은 정리 로직을 추가하지 않는다(설계 결정 D6). 운영 중 실제로 문제가 되면 `_sync_single_order()`의 stale-삭제 로직을 `sku` 기준까지 확장하는 별도 SPEC이 필요하다. **[v0.5.0 신규, 우호적 데이터]** 30일 대상 집합(1,033건/4,389 라인아이템)을 직접 측정한 결과 잔존 `sku=bundle_sku` 고아 행은 **0건**이다(§2) — 오늘 시점 이 위험의 실사례는 없다. 이 수치는 위험의 현재 심각도를 좁힐 뿐(측정 시점의 스냅숏이며 앞으로도 0이라는 보장은 아니다), 정리 로직을 추가하지 않기로 한 결정(D6)을 바꾸지 않는다 |
| C10 | REQ-RSW-034가 보존을 보장하는 것은 LineItem 행이 **갱신**되는 경우에 한한다 — `purchase_orders__isnull=True`인 라인아이템이 Shopify 페이로드에서 완전히 사라지면(`:287-289`) 행 자체가 삭제되어 `received_quantity` 등도 함께 사라진다. REQ-RSW-015가 스위프를 종료/취소·편집된 주문(페이로드가 달라졌을 가능성이 높은 주문군)에 더 자주 도달하게 만들므로, 이 경로의 노출 빈도도 함께 늘어난다. 이 SPEC은 이 기존 stale-삭제 경로에 추가 보호를 두지 않는다 — 운영 중 실제 데이터 손실이 관측되면 후속 과제로 검토한다 |
| C11 | **[v0.3.0 신설, 감사 N6, 구 REQ-RSW-032]** 배치 컨텍스트 호이스팅(REQ-RSW-021/023)의 쿼리 절감 크기는 주문마다 다르다 — `_build_title_map()`은 ISBN 목록이 비어 있으면 쿼리 없이 즉시 반환한다(`shopify_orders.py:62-63`). 번들 SKU가 전혀 없는 주문(다수)에서는 호이스팅되는 쿼리가 `ShopifySkuSetMapping` 1개뿐이라 절감은 "약 15 → 약 14"이고, 번들 SKU가 있는 주문에서만 도서 제목 쿼리까지 절감되어 "약 15 → 약 13"에 가까워진다. 이 수치는 **비규범 참고치**이며(REQ-RSW-032가 이를 규범 요구사항으로 만들려다 iteration 2에서 삭제됨, MP-2), 이 SPEC이 검증하는 것은 REQ-RSW-023(사이클당 정확히 1회 계산)뿐이다 |
| C12 | **[v0.3.0 신설, 감사 N12, 수용된 미조치 항목]** REQ-RSW-024/025/029는 여전히 매칭 키(`(order, shopify_shipping_line_id)` 등)와 `models.py` 라인 번호를 요구사항 본문에 직접 인용한다 — SPEC은 WHAT을 규정하고 HOW는 `plan.md`로 미뤄야 한다는 원칙(D20)의 잔여 위반이다. 감사가 이를 "정확성에는 영향 없음"의 낮은 심각도로 판정했고, 이 시점에서 또 다른 전면 재작성을 시도하면 새로운 문서 간 불일치(N7/N9 부류)를 만들 위험이 이득보다 크다고 판단해 **의도적으로 조치하지 않는다**. 향후 이 SPEC을 다시 개정할 기회가 있으면(예: 구현 중 발견된 다른 이유로) 함께 정리한다 |
| C13 | **[v0.4.0 신설, v0.5.0 보강]** 30일 상한 축소로 제외되는 30~60일 밴드(320건)의 not_shipped 라인아이템 중 97%(1,255/1,292건)에는 이미 `PurchaseOrder`가 연결되어 있다(§2) — 이 주문들은 방치된 것이 아니라 입고 대기 중인 살아있는 주문이다. 이 중 하나의 Shopify 배송 위치가 재배정되면, 그 주문이 (기본값) 30일 창 밖에 있는 한 스위프는 이를 잡지 못한다 — 그리고 `sync_store()`(5분 주기)는 기존 주문의 위치를 절대 갱신하지 않으므로(`shopify_orders.py:420-428`, 문제 정의 1번) 그 재배정은 어느 자동 경로로도 감지되지 않는다. §2가 보이는 4% 휴면율(제외 밴드 중 최근 30일 내 Shopify 변경이 있던 비율)은 이 위험이 발생할 확률을 낮게 경계 지을 뿐 **제거하지 않는다**. **[v0.5.0 신규, 감사 D3]** 이 유계화 자체가 미검증 전제에 의존한다 — "fulfillment order의 위치 재배정이 부모 `Order.updated_at`을 갱신한다"가 참이어야 4%가 이 위험을 유계화하는데, 이 전제는 가정 A10으로 명시했듯 검증되지 않았다. **이 전제가 거짓이면**(위치만 바뀐 주문이 `updated_at`을 움직이지 않는다면) 4%는 이 위험에 대해 아무것도 유계화하지 못한다. **[v0.5.0 신규, 감사 D2]** 제외 밴드의 주문은 도서 제목 재전파도 받지 못한다(문제 정의 3번) — 다만 이 위험은 애초에 4% 휴면율이 유계화하는 대상이 아니다(그 지표는 Shopify 발원 변경만 측정하며, 카탈로그 발원 변경인 제목 갱신은 `updated_at`에 나타나지 않는다, §2). 문제 정의 3번이 확인하듯 이 효과의 오늘 시점 규모는 근사 0이므로(대상 집합 중 NULL 제목 라인 0건, §2), 실무적 손실은 현재 없다. **REQ-RSW-035(`--days`)는 검출 수단이 아니라 복구 수단이다** `[v0.5.0 명시]` — 이 위험의 검출기가 시스템 안에 없으므로(스위프는 창 밖이라 구조상 미도달, `sync_store()`는 기존 주문 위치를 갱신하지 않음, 단건 재동기화는 사람이 그 주문을 콕 집어야만 동작) `--days`를 넓혀도 검출 지연은 줄지 않고 오배송이 외부 신호(예: 위치 오류 신고)로 드러난 뒤의 복구 시간(MTTR)만 준다: 기본값 30보다 넓은 창(예: `--days 90`)을 지정해 코드 변경 없이 일회성 catch-up 스위프를 실행할 수 있다. **선택지(비규범, 조치 불요, 감사 review-4 권고)**: 상시적으로 검출 지연을 유계화하고 싶으면 REQ-RSW-027의 스케줄러 등록 패턴(`.bat` + 작업 스케줄러)을 그대로 따라 `--days 60`을 낮은 빈도(예: 주 1회)로 도는 별도 스케줄러 항목을 추가하면 되며, 이는 코드 변경 0·신규 REQ 0으로 검출 지연을 무한대에서 최대 7일로 바꾼다 — 이 SPEC은 이를 요구사항으로 만들지 않는다. 상시적 완화(예: 기본값 자체를 확대)가 필요해지면 REQ-RSW-003(b)의 정책 재확정이 필요하다(C4) |
| C14 | **[v0.5.0 신규, review-3 D1 최종 반영]** `closed_at`/`cancelled_at`(문제 정의 2번)은 현재 어떤 조회·집계·필터도 읽지 않는다(`_reorder_candidate_filter`·`_apply_logistics_display_filter`·`_recompute_order_aggregates` 전부 미참조, review-3가 `backend/` 전수 검색으로 확인 — 두 필드의 출현 지점은 쓰기/선언 4곳뿐이고 읽는 코드는 0건이다: `shopify_orders.py:161-162`(쓰기), `models.py:79-80`(필드 선언), `migrations/0001_initial.py:57-58`, `serializers.py:436`(직렬화 선언만); 프런트엔드도 `frontend/src/types/order.ts:224-225`의 타입 선언과 테스트 픽스처가 전부이며 렌더링하는 컴포넌트가 없다). 이 SPEC은 두 필드의 **데이터 정확성**만 확보하며, 그 값을 소비하는 로직은 후속 과제로 남긴다. 대상 판정(REQ-RSW-003)도 취소/종료 주문을 배제하지 않으므로, 취소된 주문에 `not_shipped` 라인아이템이 하나라도 남아 있으면 그 주문은 (기본값) 30일 창이 닫힐 때까지 라운드로빈 슬롯을 계속 점유하며 매 랩 동일 값을 재기록한다 — 최초 감지 이후의 반복 처리는 순비용이다(현 실측 규모로는 무시 가능하나, 문서화되지 않은 설계 귀결이었다). AC 추가는 불필요하다(AC-015/016이 데이터 반영 자체는 이미 검증한다) |

---
