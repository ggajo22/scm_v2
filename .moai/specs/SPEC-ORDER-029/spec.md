---
id: SPEC-ORDER-029
version: 0.5.0
status: planned
created_at: 2026-08-19
updated: 2026-08-19
author: ggajo
priority: High
issue_number: 0
labels: [order, shopify, sync, cancellation, closure, backend]
---

# 주문 취소·종료 감지 및 반영 (Order Cancellation & Closure Detection)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1.0 | 2026-08-19 | ggajo | 최초 작성. `status=cancelled`/`status=closed` + `updated_at_min` 커서 기반 증분 조회로 설계했다. |
| 0.2.0 | 2026-08-19 | ggajo | plan-auditor 1차 리뷰(FAIL, 0.66)의 D1(datetime→URL 직렬화 버그)·D2(미측정 Shopify 규모·livelock 위험)를 커서 완전 제거 + `ids=`/`status=any` + 로컬 후보 집합(`cancelled_at IS NULL AND closed_at IS NULL`) 재설계로 구조적으로 해소. |
| 0.3.0 | 2026-08-19 | ggajo | plan-auditor 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md`, iteration 2, **FAIL, 0.71**)의 blocking 5건 반영. **D1(major, blocking) — 후보 집합의 생애주기 사각지대.** `cancelled_at IS NULL AND closed_at IS NULL`은 "첫 상태 전이"에서 관측을 멈춘다 — 종료(보관)가 먼저 일어난 주문은 후보 집합을 영구히 이탈하고, 그 뒤에 취소되면 어떤 자동 경로도 감지하지 못한다(`status=open` 피드에도 없어 `sync_store()`도 무력). 프로덕션 실측(gimssine, 취소 1,170건 전수): `cancelled_at`+`closed_at` 둘 다 기록됨 1,121건 — 그중 취소가 먼저(안전) 762건, 60초 이내 동시(안전) 358건, **종료가 먼저(사각지대) 1건**. 노출률 0.09%지만 영구 미감지다. v0.1.0의 `status=cancelled` 전수 스윕에는 이 사각지대가 없었다 — 재설계가 조용히 도입한 회귀였다. **감사가 제시한 저비용 확장으로 해소한다**: "취소는 종결 상태, 종료는 아니다"라는 비대칭을 반영해, 후보 집합을 `cancelled_at IS NULL AND (closed_at IS NULL OR closed_at >= 현재 - N일)`로 확장하고 감지 커맨드는 N=30, 백필 커맨드는 무제한(N 없음, `cancelled_at IS NULL`만)을 쓴다 — 감지는 최근 종료된 주문을 계속 관찰해 사각지대를 좁히면서 반복 비용을 유계화하고, 백필은 실행할 때마다 이력 전체를 무제한으로 재확인해 30일 창을 넘긴 잔여 노출을 흡수한다(§4 D7, §1.1). Shopify에서 삭제된 주문(두 필드가 영원히 NULL이라 매 사이클 재조회됨)에 대해서는 요청 id 수와 실제 반환 레코드 수의 차이(`missing_ids`)를 신설 요구사항(REQ-CANC-006)으로 보고한다. **D2(major, blocking) — AC-CANC-005가 선언한 판별력이 거짓.** `existing[r["id"]]` 변이가 던지는 `KeyError`가 청크 레벨 `except Exception`(당시 `plan.md:151`)에 삼켜져 세 단정이 전부 통과했다 — v0.2.0에서 신설한 역방향 [HARD] 규약이 AC-011/017/019(구 번호) 세 건에만 적용되고 신규 AC-005에는 적용되지 않았다. `chunk_failures`가 빈 리스트라는 단정과 같은 청크의 다른 주문이 실제로 갱신됐다는 양성 증거를 추가했고, 역방향 규약의 적용 범위를 "AC 번호 열거"에서 "이 문서의 모든 부정형 단정"으로 일반화했다(acceptance.md §0). **D3(major, blocking) — "기계적 대조, 불일치 0건" 선언이 거짓이었다.** `spec.md:214`(구 버전)가 20행짜리 표를 "25개 매핑 행"이라 칭했고(v0.1.0 잔재), AC-CANC-011의 소속 테스트 파일이 `acceptance.md` 헤더·`plan.md` M1·섹션 헤더·DoD 네 곳에서 서로 모순됐다(watermark 검증은 `call_command`를 쓰는 커맨드 레벨 테스트인데 헤더·M1은 "핵심 함수" 파일로 잘못 분류). §6 추적표 자체는 실제로 깨끗했다(감사가 독립 재검증) — 선언의 절반이 참이었기 때문에 나머지 절반의 거짓이 더 위험했다. 이번 개정은 실제로 grep을 실행하고 그 출력을 각주로 남긴다(§6 하단). **D4(major, blocking) — 가정 A1의 출처 오귀속.** v0.2.0은 `ids=` 메커니즘 확인을 "plan-auditor review-1"에 귀속했으나, review-1 전문에 `ids=` 문자열이 단 한 번도 등장하지 않는다 — review-1의 D2 지시는 정반대(`status=closed` 규모를 프로덕션에서 측정하라)였다. 사실 자체(250개 요청 → 250개 반환, 두 타임스탬프 채워짐, `Link` 헤더 없음)는 참이지만, 출처가 틀렸고 동시에 "재검증 면제"를 선언해 추적 불가능한 근거가 됐다. 이번 개정은 이 검증을 **2026-08-19 세션에서 프로덕션 직접 조회로 확인**(review-1이 아니라)으로 정정한다. **D5(major, blocking) — `fields=`/`limit=`을 단정하는 AC가 여전히 0개.** review-1 D6의 미해결 잔여분(`status=`/`ids=`는 v0.2.0에서 해소됐으나 `fields=`/`limit=`는 남아 있었다). AC-CANC-006에 한 줄 추가로 닫았다. **Major**: D6(청크 영구 실패 시 원인 id가 기록되지 않음 — `chunk_failures`를 `{"ids": [...], "error": ...}` 구조로 변경하고 §8에 제약 신설), D7(호출 비용 추정이 스토어별 청킹을 무시하고 합산 모집단에서 도출됨 — review-1 D2와 동일 부류 — 17회/스토어별 청킹 반영 산식으로 재도출, D1의 창 확장과 함께 재계산), D8(커맨드 테스트 패치 대상 규약이 쓰기 결과를 단정하는 7개 AC를 작성 불가능하게 만듦 — HTTP 계층 패치로 교체, 저장소 실제 관례인 `test_backfill_missing_orders_command.py:17`과 정렬), D9(`_sync_single_order()` 경유 시 파괴 범위 과소 서술 — `:291`/`:306`의 `ShippingLine`/`Refund` 전량 무조건 삭제를 가정 A4·REQ-CANC-008에 추가하고 AC에 `Refund` 행 수 보존 단정 신설, 이 저장소의 환불 넷팅 회귀 이력 고려). **Minor**: D10(`original_sku` 픽스처 누락 추가), D11(REQ-CANC-010 EARS 라벨 State-Driven으로 정정), D12(REQ-CANC-002/005 능동태 정정), D13(REQ-CANC-005에 전용 AC 신설), D14(AC-CANC-019(구 번호)의 M19 서술이 이 아키텍처에서 구조적으로 불가능한 변이를 주장 — 서술 좁힘), D15(250개 `ids=` URL 길이 측정치 기록 + AC에 길이 단정 추가), D16(`parse_datetime` 함수 내부 재import를 모듈 레벨로 이동). REQ 20개 → **24개**(모듈 2·4·5·6 확장), AC 19개 → **23개**(신규: 후보 집합 창 검증, 갭 보고, 감지/백필의 `closed_grace_days` 전달 검증). **프로세스 확인**: 이번 개정 완료 시점에 (1) 모든 파생 수치가 나누는 모집단을 명시하고 그 모집단이 옳은지 확인, (2) 모든 AC의 변이가 어느 예외 경계를 통과하는지 확인하고 그 경계를 통과해도 관측 가능한지 재확인, (3) 모든 문서 간 배정(파일 소속·마일스톤·DoD)을 grep으로 추출해 대조, (4) 모든 출처 귀속 주장을 실제로 열어 확인 — 네 가지를 전부 수행했고 각 결과를 §6 각주·§4 표·본 HISTORY에 기록했다. |
| 0.4.0 | 2026-08-19 | ggajo | plan-auditor 3차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-029-review-3.md`, iteration 3, **FAIL, 0.80**, 4회차 감사 불필요 판정)의 blocking 4건 반영 — 감사가 "이 SPEC의 설계는 옳고 남은 것은 판별력 격자의 구멍 2개와 출처 문장 2개뿐"이라고 명시한 종결 회차다. iteration 2 결함 16건 중 14건 CLOSED, 1건 CLOSED(부류 재발), **1건 NOT CLOSED(D11)**로 재확인됐다. **D-N1(major, blocking) — REQ-CANC-002("최대 250개")를 검출할 수 있는 AC가 0개.** AC-CANC-007/008/016이 전부 청크 크기를 명시적으로 넘겨 호출해, `IDS_CHUNK_SIZE=250` 기본값 자체를 단정하는 AC가 없었다(§6이 REQ-CANC-002 → AC-CANC-007로 커버 선언한 것과 모순, `spec.md`가 스스로 [HARD]로 금지한 형태). AC-CANC-007에 `IDS_CHUNK_SIZE == 250`과 `reconcile_order_status_for_ids`의 `chunk_size` 기본 인자 단정을 추가했다. **D-N2(major, blocking) — REQ-CANC-017의 "또는 청크" 절반을 검출할 수 있는 AC가 0개.** AC-CANC-017의 유일한 시나리오는 스토어 레벨 실패(AC-015와 동일 설정)였고, 청크 실패를 `call_command` 경유로 주입하는 AC가 없었다 — `failed.append(f"{store_type} (partial)")` 한 줄이 빠져도 23개 AC 전부가 통과하는 상태였다. 이는 §8 C6이 스스로 예상 시나리오로 규정한 상황("한 청크에 영구적 실패 원인이 있으면 같은 청크의 나머지가 매 사이클 함께 실패")과 정확히 일치한다 — AC-CANC-017에 청크 레벨 실패 시나리오(시나리오 2)를 추가해, 다른 청크의 정상 반영(양성 증거)과 `CommandError(match="partial")`을 함께 단정하도록 확장했다. **D-N3(major, blocking, 근거 오귀속 3회 연속 재발) — 후보 집합 생애주기 실측(1,121/762/358/49)의 출처가 사실과 다르다.** v0.3.0은 이 수치를 "plan-auditor review-2가 이 세션에서 프로덕션 직접 조회"로 귀속했으나, `.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md` 전문에 이 수치들이 단 한 번도 등장하지 않으며, review-2는 스스로 "프로덕션 수치를 재검증하지 않고 기준값으로 채택했다"고 명시한다(review-2 M1) — plan-auditor는 프로덕션을 조회하지 않는다. 같은 문서가 5줄 간격으로 올바른 형식(A1)과 틀린 형식(생애주기 실측 헤더)을 동시에 쓰고 있었다 — D4(iteration 2) 수정을 적용한 문장 바로 위 14줄에서 같은 실수가 반복된 것이었다. 실제 출처는 A1과 동일하게 **사용자가 2026-08-19 세션에서 프로덕션을 직접 조회**한 것이다 — 귀속을 정정했다. 부수적으로 "감사가 제시한 저비용 확장을 그대로 채택한다"는 서술도 과장이었다 — review-2 D1이 제시한 세 선택지에 유예 창(`closed_grace_days`) 방식은 없었다(가장 근접한 것은 선택지 3, 백필 `--include-closed`였다). 유예 창 설계는 **저자(관리자-spec)의 독자적 합성**이며, 이번 개정에서 그렇게 정확히 서술했다. **D-N4(D11, minor, blocking — 자기 인증 오류) — REQ-CANC-011 EARS 라벨이 HISTORY에서만 정정 단정되고 본문은 그대로였다.** v0.3.0 HISTORY가 "D11(REQ-CANC-010 EARS 라벨 State-Driven으로 정정)"이라 단정했으나, 실제로는 번호만 010→011로 밀렸을 뿐 라벨은 `(Ubiquitous)`로 남아 있었다 — "HISTORY에서 수정을 단정했으나 본문은 미수정"이라는, 이 SPEC이 반복 지적받은 자기 인증 결함의 정확한 사례였다. 라벨을 `(State-Driven)` + `**While**` 절로 정정했다. **적용(권고, blocking 아님)**: D-N5(30일 창 잔여 노출의 유일한 흡수 경로였던 백필 정기 재실행이 REQ도 DoD도 아닌 순수 권고에만 있었다 — 이 저장소에 정확히 이 패턴의 실패 선례가 있다(환율 동기화 정기 실행 미등록 → 마진 과대 계상, auto-memory 참조). DoD 스케줄러 절에 백필 저빈도 등록 여부 기록 체크박스 1건 추가), D-N6(무제한 백필의 후보 집합이 로컬 테이블과 함께 단조 증가한다는 성질과, 10배 규모에서 감지 사이클이 Shopify 버스트 한도를 넘겨 429가 실제로 발생하기 시작한다는 사실이 문서 어디에도 없었다 — §8에 제약으로 신설), D-N7(`acceptance.md` §0.2가 "셋으로 나뉜다"면서 4개를 열거하고 `plan.md` §1.6은 "3가지"라 쓰며 구성원도 서로 달랐다 — D8을 고치기 위해 신설한 바로 그 절에서 배정 드리프트가 재발한 것이었다. 4분류로 통일하고 양쪽 문서의 구성원을 동일하게 맞췄다), D-N8(AC-CANC-005의 형제 주문 id 표기 `900005 + 1 (=90005b)`가 산술도 표기도 실행 불가능했다 — 실제 정수 90006으로 정정), D-N11(a)(`plan.md`가 이미 모듈 레벨에 있는 `django.utils.timezone`을 함수 내부에서 재import해 자기 주석과 모순됐다 — D16이 잡은 안티패턴이 다른 심볼에서 재발한 것이므로 제거). REQ 24개 → 24개(라벨만 정정, 개수 불변), AC 23개 → 23개(AC-CANC-007/017 내용 확장, 개수 불변). **프로세스 확인 — "부류를 막는 절차"를 이번에 실제로 적용했다**: 근거 오귀속이 iter1 D8 → iter2 D4 → iter3 D-N3으로 3회 연속 재발했다는 감사의 최종 지적에 따라, `spec.md` 전체에서 "plan-auditor"/"review-"/"감사가"를 포함하는 모든 문장을 이번 개정 직후 다시 추출해(§1.1, §3 A1) 각 문장이 실제로 무엇을 근거로 하는지(누가, 언제, 무엇을 확인했는지)를 인라인으로 명시했다 — §6의 grep 각주가 추적성 부류의 재발을 실제로 멈춘 것과 동일한 처방이다. |
| 0.5.0 | 2026-08-19 | ggajo | **[v0.4.0 HISTORY 행 순서 정정]** 이 표가 직전 개정까지 0.4.0 행을 0.3.0 행보다 앞에 적고 있었다(연대순 위반) — 내용 변경 없이 순서만 바로잡았다. **[본 개정 — 코디네이터 지시, 신규 감사 없이 적용]** 사용자가 제기한 동시성 문제(SPEC-028 §8 C8에 있었으나 이 SPEC으로 재설계되며 소실되고 재수록되지 않았던 항목)를 다룬다: 신규 감지 커맨드(`sync_order_cancellations`)와 기존 5분 주기 `sync_orders` 작업 사이의 상호작용. 이 세션에서 측정: `logs/sync_orders.log` 4회 연속 실행이 `:X4:05`~`:X4:24`(약 18~24초) 패턴을 보여 `sync_store()`(`sync_orders.py:60`)가 그 전체 시간 동안 `Order` 행에 InnoDB 행 잠금을 보유함을 확인했고, `SHOW VARIABLES`로 `innodb_lock_wait_timeout=50`, `transaction_isolation=READ-COMMITTED`, `innodb_deadlock_detect=ON`을 확인했다. 세 가지 상호작용을 분석해 문서화했다(§1.2 신설): (1) **분실 갱신** — `_sync_single_order()`가 `status=open` 피드의 stale 페이로드로 `cancelled_at=NULL`을 무조건 쓸 수 있어 감지 잡의 방금 쓴 값을 덮어쓸 수 있으나, 그 주문은 다시 후보 집합에 재진입해 다음 사이클에 재감지된다 — 최대 1사이클 지연, 가드 불필요(구조적으로 자기 치유). (2) **잠금 대기** — 50초 타임아웃 대비 ~20초 보유 시간이라 평소엔 그냥 대기 후 성공하지만, `sync_orders`가 비정상적으로 길어지면(대량 변경, Shopify 지연) 타임아웃을 넘겨 청크 실패 → `CommandError`(REQ-CANC-017) → 5분마다 스케줄러 경보가 될 수 있다 — **이것이 실제로 대응할 가치가 있는 상호작용**이며, 분실 갱신이 아니다. (3) **교착 상태** — `innodb_deadlock_detect=ON`이라 MySQL이 즉시 한쪽을 롤백하고, 그 롤백된 쪽은 다음 사이클에 재시도된다. **필수 변경**: 트리거를 스태거링한다 — 감지 잡을 `sync_orders`(매 5분, `:X4:05` 정렬)와 최소 2~3분 어긋나게 등록해(§4 D10, §1.5) 정상 상태에서 두 잡이 절대 겹치지 않게 한다(잔여 위험: 스태거링은 겹침을 "일으키기 어렵게" 할 뿐 "불가능하게"는 못 한다 — `sync_orders`가 약 2.5분을 넘겨 실행되면 여전히 충돌할 수 있다, §8 C8). **판단(코디네이터 요청)**: 잠금 대기 시간 초과를 REQ-CANC-017의 경성 실패로 계상할지, 구분 가능한 연성 실패로 취급할지 — **연성으로 판단한다**(§4 D10에서 논거 전개, 요지: 자기 치유되는 잘 이해된 실패 모드에 매 5분 경보를 울리면 경보 피로가 생겨 진짜 실패를 가린다 — 다만 정보 자체를 지우지는 않는다, `chunk_failures`에 구분 가능하게 계속 기록하고 그 실패만으로는 `failed` 목록에 추가하지 않는다. 잠금 대기가 아닌 실패는 REQ-CANC-017 그대로 경성 실패다). 신규: 가정 A7·A8, 설계 결정 D10, §1.2, 모듈 9(REQ-CANC-025/026/027), Exclusions #8, §8 C8, AC-CANC-024·025. REQ 24개 → **27개**, AC 23개 → **25개**. 이번 리비전이 만드는 새 출처 귀속 문장(측정치)은 처음부터 "이 세션에서 사용자가 직접 측정"으로 정확히 표기했다(부류 재발 방지, iter1 D8/iter2 D4/iter3 D-N3의 교훈 적용) — 별도 검증 절차로 위장하지 않는다, 이 문장 자체가 그 검증이다. |

---

## 1. 문제 정의

Shopify에서 취소되거나 종료(자동 보관)된 주문을 기존 동기화는 구조적으로 볼 수 없다.

`sync_store()`(`backend/order/shopify_orders.py:355-461`, 5분 주기)는 `fetch_all_open_orders()`(`:32-45`)를 통해 `orders.json?status=open&updated_at_min=<워터마크>`만 조회한다. Shopify에서 주문이 취소되거나 종료되면 그 주문은 `status=open` 피드에서 사라진다. 그 결과 로컬 `Order.closed_at`/`Order.cancelled_at`(`models.py:79-80`)은 최초 동기화 시점 값(대개 둘 다 NULL)에 영원히 고정된다.

유일한 예외는 `sync_single_order_from_shopify()`(`:334-352`)가 쓰는 `orders/{id}.json` 단건 엔드포인트다 — `OrderResyncView`(`views.py:408`)를 통해 **사람이 그 주문을 콕 집어 눌러야만** 동작한다.

### 실측 (사용자가 이 세션에서 프로덕션 직접 조회, 재도출하지 않고 그대로 채택)

```
Shopify open orders          gimssine 776    etoile 25     total 801
local Order rows             gimssine 3,828  etoile 82     total 3,910
local이지만 Shopify open에 없음                              3,109  (80%)

Shopify status=cancelled 전체       gimssine 1,170   etoile 21
  └ 로컬에 존재                     gimssine    58   etoile  0
      └ 로컬 cancelled_at 이미 반영               6
      └ 로컬에 미반영                            52   ← 현재 실재하는 결함
  └ 미반영 52건 중 logistics_status="not_shipped"로 남은 라인아이템   79개
      └ 그중 PurchaseOrder 연결됨                                    51개
```

### 후보 집합 생애주기 실측 (v0.3.0 신설, gimssine 취소 1,170건 전수 — **사용자가 2026-08-19 세션에서 프로덕션 직접 조회로 확인**, A1과 동일 출처)

> **[v0.4.0 정정, 3차 감사 D-N3]** 이 수치(1,121/762/358/49)는 이전 개정에서 "plan-auditor review-2가 이 세션에서 프로덕션 직접 조회"로 잘못 귀속됐었다 — `.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md` 전문에 이 수치들이 등장하지 않으며, 그 보고서는 스스로 "프로덕션 수치를 재검증하지 않고 기준값으로 채택했다"고 명시한다(review-2 M1). plan-auditor는 프로덕션을 조회하지 않는다 — 이 수치의 실제 출처는 A1과 동일하게 사용자다. 근거 오귀속이 iteration 1(D8, 내부 상호참조 오류) → iteration 2(D4, A1의 `ids=` 오귀속) → iteration 3(이 항목, D-N3)으로 3회 연속 재발한 부류이며, 이번 정정으로 이 SPEC에 남은 모든 프로덕션 수치의 출처가 A1·A2와 동일한 형식(사용자, 2026-08-19 세션)으로 통일됐다.

```
cancelled_at + closed_at 둘 다 기록됨            1,121
  ├ closed_at이 cancelled_at보다 나중(취소 먼저)     762   안전 — 취소 시점엔 아직 열려있어 후보 집합에 있었다
  ├ 60초 이내 동시 기록                             358   안전 — 사실상 동시 전이
  └ closed_at이 cancelled_at보다 먼저(종료 먼저)       1   ← §1.1의 사각지대. 노출률 1/1,170 = 0.09%
cancelled_at만 기록됨(closed_at 없음)                49
```

이 1건이 실재하는 위험을 증명한다 — `cancelled_at IS NULL AND closed_at IS NULL`만으로 후보 집합을 정의하면, 종료가 먼저 일어난 주문은 그 즉시 후보 집합을 이탈하고 그 뒤의 취소를 영구히 놓친다. §1.1이 이 문제를 해소하는 설계를 서술한다.

### 1.1 핵심 메커니즘 — `ids=` 파라미터 + 비대칭 후보 집합

**`ids=` 파라미터(사용자가 2026-08-19 세션에서 프로덕션 직접 조회로 확인, 가정 A1)**: Shopify 목록 엔드포인트는 `orders.json?ids=<최대 250개, 쉼표구분>&status=any&limit=250&fields=id,cancelled_at,closed_at`를 받아, 요청한 주문들의 **현재** 상태를 상태와 무관하게 반환한다 — 요청 250건 중 250건 반환, `cancelled_at`/`closed_at` 둘 다 채워짐, `Link` 헤더 없음(250개 이하 요청은 페이지네이션이 불필요). 이 사실은 review-1이 확인한 것이 아니다 — review-1의 D2 지시는 `status=closed` 규모 측정이었다(§4 D9 참조, v0.2.0의 오귀속을 이번 개정에서 정정한다).

**비대칭 후보 집합(v0.3.0 신설)**: plan-auditor review-2의 D1이 §1의 사각지대(종료 후 취소 영구 미감지)를 blocking으로 지적했다 — 그 지적 자체는 review-2 원문에 실재한다(`.moai/reports/plan-audit/SPEC-ORDER-029-review-2.md` D1). **다만 review-2가 D1의 수정으로 제시한 세 선택지 중 어느 것도 유예 창(`closed_grace_days`) 방식을 포함하지 않았다**(선택지 1: `closed_at` 조건 전면 제거, 선택지 2: 현행 유지+Exclusions 명시, 선택지 3: 백필에 `--include-closed` 인자 — 이 셋 중 가장 근접한 것은 3번이다). 아래의 유예 창 설계 자체는 **저자(manager-spec)가 review-2 D1이 제기한 문제에 대해 독자적으로 합성한 해법**이다(v0.4.0 정정, 3차 감사 D-N3 — 이전 개정은 이를 "감사가 제시한 저비용 확장을 그대로 채택한다"고 서술해 review-2의 기여를 과장했었다). 논거: 취소는 Shopify에서 되돌릴 공개 API가 없는 **종결 상태**이지만(가정 A6, 미검증), 종료(보관)는 그 뒤에도 취소가 일어날 수 있는 **비종결 상태**다(§1의 1건 실측). 이 비대칭을 그대로 후보 집합 정의에 반영한다:

```
후보 집합 = cancelled_at IS NULL
            AND (closed_at IS NULL OR closed_at >= 현재 시각 - N일)
```

`N`(유예 일수)은 호출자가 지정하는 파라미터다:
- **감지 커맨드(상시, 5분 주기)**: `N=30`. 최근 30일 이내 종료된 주문은 계속 관찰해 사각지대를 좁히면서, 오래전에 종료된 주문은 후보 집합에서 제외해 반복 비용을 유계화한다.
- **백필 커맨드(1회성/수동 재실행)**: `N` 없음(`closed_at` 조건 자체를 걸지 않음) — `cancelled_at IS NULL`인 로컬 주문 전체를 매번 무제한으로 재확인한다. 1회성 실행이므로 반복 비용 유계화가 필요 없고, 30일 창을 넘긴 잔여 노출은 이 무제한 재확인이 흡수한다.

**잔여 노출(정직하게 명시)**: 종료 후 30일을 초과해서 취소가 도착하면, 감지 커맨드는 그 사이 그 주문을 놓친다 — 다음 백필 실행이 잡을 때까지 미반영 상태가 지속된다. 실측된 1건의 정확한 종료→취소 간격은 이 세션에서 측정되지 않았으므로 30일이 그 1건을 반드시 포착했을지는 보장할 수 없다 — 30일은 이 저장소의 기존 30일 창 선례(SPEC-028의 휴면성 논거)와 일반적인 전자상거래 반품·취소 정책 기간을 참고해 합리적으로 선택한 값이며, 정밀한 최적값이 아니다. 운영 권고: 백필을 정기적으로(예: 월 1회) 재실행해 이 잔여 노출을 "다음 백필 주기까지"로 상한을 둔다(§8 C5, REQ는 아님 — 운영 관행).

**Shopify에서 삭제된 주문**: `ids=` 응답이 그 id를 그냥 누락한다(예외 없음). 그 주문은 두 필드가 영원히 NULL이라 매 사이클 후보 집합에 잔류하며 재조회된다 — 이 SPEC은 이를 막지 않되, 요청 id 수와 실제 반환 레코드 수의 차이(`missing_ids`)를 보고해(REQ-CANC-006) 운영자가 식별할 수 있게 한다(§8 C6).

**비용(스토어별 청킹을 반영해 재도출, v0.3.0 — 감사 D7 대응)**: 청킹은 **스토어 단위**로 일어난다(커맨드가 스토어를 순회하며 각 스토어의 후보 집합을 독립적으로 조회·청킹한다, §plan.md). 오늘 실측치를 스토어별로 나누면:

```
백필(무제한, cancelled_at IS NULL만):
  gimssine: 3,828 − 6(이미 반영) = 3,822건 → ⌈3822/250⌉ = 16청크
  etoile:   82건                            → ⌈82/250⌉   = 1청크
  합계: 17회 (결정론적 — 오늘 로컬 건수 기준, 매 백필 실행 시 재도출됨)

감지(N=30일 창):
  [배포 후 실측, 2026-08-19] 백필 완료 직후 커맨드 stdout의 candidates=N 기준:
    gimssine: 2,188건 → ⌈2188/250⌉ = 9청크
    etoile:      47건 → ⌈47/250⌉   = 1청크
    합계: 10회/사이클 (5분 주기 = 초당 0.033회, Shopify 한도 약 2회/초의 1.7%)

  이 값은 아래 사전 추정치를 대체한다. 추정 당시 서술을 남겨둔다:
  "최근 30일 이내 종료된, 아직 열려있는 주문 수는 이 세션에서 측정되지 않았다.
   상한: 백필과 동일한 무제한 모집단(3,904건)을 절대 넘지 않는다.
   참고치: 현재 open 주문만(801건) 기준으로는 5회."

  실측이 참고치의 2배가 된 이유는 30일 유예 창이다 — 후보 집합은 열린 주문(약 814건)뿐
  아니라 최근 30일 내 종료된 주문(약 1,420건)까지 포함한다. 사전 추정은 전자만 세었다.
  추정치를 확정치처럼 쓰지 않고 관측을 지시해둔 덕분에 이 차이가 결함이 아니라
  정상적인 확정 절차로 처리됐다.

백필(창 없음) 실측: gimssine 3,790건 → 16청크 + etoile 82건 → 1청크 = 17회.
  사전 추정 17회와 정확히 일치했다.
```

### 페이지네이션 계약 (방어적으로만 유지)

`_parse_next_page_info()`(`shopify_orders.py:25-29`)를 재사용하되, 250개 이하 청크는 정상적으로 `Link` 헤더 없이 단일 호출로 끝난다(가정 A1). 예상 밖으로 `Link` 헤더가 오면 여전히 끝까지 따라간다(REQ-CANC-003).

### 1.2 동시성: 기존 sync_orders와의 상호작용 (v0.5.0 신설)

기존 `sync_store()`(5분 주기, `sync_orders.py:60`)와 이 SPEC의 신규 감지 커맨드(`sync_order_cancellations`, 역시 5분 주기 권장, §4 D6)는 동일한 `Order` 테이블을 대상으로 별도 스케줄러 작업으로 동시에 실행될 수 있다. 이 상호작용은 SPEC-028(이 SPEC의 재설계 이전 버전) §8 C8에 문서화돼 있었으나, 아키텍처가 `ids=` 기반으로 교체되며 소실되고 이 SPEC에 재수록되지 않았다 — 이번 개정에서 되살린다.

**실측 (사용자가 이 세션에서 직접 확인, 가정 A7·A8)**:

```
logs/sync_orders.log 연속 4회 실행:
  17:39:05 → 17:39:28  (23s)
  17:44:05 → 17:44:23  (18s)
  17:49:05 → 17:49:24  (19s)
  17:54:05 → 17:54:29  (24s)
  → 매 5분(:X4:05, 즉 분%5==4, 초==05)에 시작, 소요 18~24초

MySQL SHOW VARIABLES (이 세션):
  innodb_lock_wait_timeout   = 50   (초)
  transaction_isolation      = READ-COMMITTED
  innodb_deadlock_detect     = ON
```

`sync_orders.py:60`은 스토어 하나의 `sync_store()` 전체를 단일 `transaction.atomic()`으로 감싸며, 그 블록 **안에서** Shopify API 왕복이 일어난다 — 따라서 InnoDB가 건드린 `Order` 행에 거는 행 잠금이 API 응답을 기다리는 동안을 포함해 전체 실행 시간(~18~24초) 동안 유지된다.

이 SPEC의 신규 코드는 이 노출을 물려받지 않는다 — HTTP 호출은 `transaction.atomic()` 블록 **밖**에 있고(plan.md 설계), 원자 블록은 청크 단위이며, 쓰기는 두 컬럼짜리 `bulk_update()`뿐이다(§4 D4) — 이 SPEC 자신의 잠금 보유 시간은 밀리초 단위다. 노출은 전적으로 `sync_orders`의 긴 트랜잭션에서 물려받은 것이며, 그 트랜잭션 구조를 바꾸는 것은 이 SPEC의 범위 밖이다(§7 Exclusions #8).

**세 가지 상호작용**:

1. **분실 갱신(lost update) — 실재하지만 자기 치유된다.** `_sync_single_order()`(`sync_orders.py` 내부)는 `status=open` 피드에서 가져온 페이로드로 Order-레벨 `defaults`(`cancelled_at`/`closed_at` 포함, 가정 A4)를 **무조건** 쓴다. `status=open` 피드의 주문은 정의상 아직 열려 있으므로 이 두 필드는 항상 NULL이다. 감지 잡이 방금 `cancelled_at`을 기록한 직후, 겹쳐 실행 중이던 `sync_orders`가 그 값을 stale NULL로 덮어쓸 수 있다. **가드를 추가하지 않는다** — 그 주문은 덮어써진 순간 `cancelled_at IS NULL`이 다시 참이 되어 후보 집합에 즉시 재진입하고(REQ-CANC-004), 다음 감지 사이클(최대 5분 뒤)에 재감지된다. 최악의 경우도 1사이클 지연일 뿐이다 — 정정이 이미 후보 집합 설계 자체에 구조적으로 내장돼 있으므로, 별도의 낙관적 잠금이나 조건부 쓰기를 추가하는 것은 불필요한 복잡성이다(오늘 도달 불가능한 위험에 재설계로 대응하지 않는다는, §4 D3/§8 C7이 이미 적용한 것과 동일한 원칙).
2. **잠금 대기(lock wait) — 실제로 대응할 가치가 있는 상호작용.** 평소(소요 18~24초)에는 `innodb_lock_wait_timeout=50`초의 절반도 안 되므로, 감지 잡의 `bulk_update()`는 그냥 대기했다가 정상적으로 성공한다. 문제는 `sync_orders`가 비정상적으로 길어질 때다(대량 상태 변경, Shopify 응답 지연) — 50초를 넘기면 감지 잡의 해당 청크가 `django.db.utils.OperationalError`(MySQL 에러 1205, "Lock wait timeout exceeded")로 실패한다. 이 실패는 REQ-CANC-016(청크 실패 계속 진행)까지는 무해하지만, 아무 구분 없이 REQ-CANC-017(하나라도 실패하면 `CommandError`)에 도달하면 5분마다 스케줄러 경보를 울릴 수 있다 — 반복되는 자기 치유형 실패(다음 사이클에 그 주문은 여전히 후보 집합에 남아 재시도된다, REQ-CANC-004)에 매번 경보가 울리면 **경보 피로**가 생겨 진짜 실패를 가린다. 이 SPEC은 이 실패를 별도로 식별 가능하게 만든다(REQ-CANC-025/026, §4 D10).
3. **교착 상태(deadlock) — 문서화만 한다.** `innodb_deadlock_detect=ON`이므로 두 트랜잭션이 서로의 잠금을 기다리는 순환이 형성되면 MySQL이 즉시 감지해 한쪽을 롤백한다(`django.db.utils.OperationalError`, 에러 1213). 롤백된 쪽이 감지 잡이면 그 청크는 `chunk_failures`에 잡히고(REQ-CANC-012), 그 청크의 주문들은 후보 집합에 그대로 남아 다음 사이클에 재시도된다 — 분실 갱신과 동일한 자기 치유 성질이다. 이 SPEC은 재시도 로직을 별도로 추가하지 않는다(이미 다음 사이클이 재시도 역할을 한다).

**완화 — 트리거 스태거링(REQ-CANC-027)**: 세 상호작용 모두 두 잡이 시간상 겹칠 때만 발생한다. 감지 커맨드의 스케줄러 트리거를 `sync_orders`(`:X4:05` 정렬)와 최소 2~3분 어긋나게 등록하면(권장: `:X2:30`, 즉 `sync_orders`보다 2분 35초 앞선 위상) 정상 상태에서 두 잡은 절대 겹치지 않는다 — `sync_orders`의 실행 시간이 실측 최대치(24초)의 몇 배가 되어도 여전히 5분 주기 안에서 서로의 실행 구간을 침범하지 않는다.

**잔여 위험(정직하게 명시, §8 C8)**: 스태거링은 겹침을 "일으키기 어렵게" 할 뿐 "불가능하게"는 못 한다. `sync_orders`가 어떤 이유로든 스태거 간격(약 2.5분)을 넘겨 실행되면, 다음 감지 사이클의 시작과 여전히 겹칠 수 있다. 이 SPEC은 상호 배제 잠금(뮤텍스/어드바이저리 락)을 두지 않는다(§7 Exclusions #8) — 스태거링만으로 실질적 위험을 낮추는 것을 이번 개정의 완화 범위로 한정한다.

---

## 2. Environment (환경)

| 항목 | 내용 |
|------|------|
| 대상 코드(백엔드, 이 SPEC이 신설) | `shopify_orders.py`에 신규 함수 4개 추가(§ plan.md), 신규 관리 커맨드 2개(`sync_order_cancellations`, `backfill_order_cancellations`) |
| 대상 코드(백엔드, 기존/무변경 유지) | `sync_store()`(`:355-461`), `fetch_all_open_orders()`(`:32-45`), `_sync_single_order()`(`:104-331`), `_build_fulfillment_location_data()`(`:72-101`), `sync_single_order_from_shopify()`(`:334-352`), `OrderResyncView`(`views.py:408`), `StoreSyncWatermark`(`models.py:565-603`), `backfill_missing_orders` 커맨드 |
| 데이터베이스 | **MySQL**(RDS), Django `5.1.6`. `TIME_ZONE="UTC"`, `USE_TZ=True`(`config/settings/base.py:92,94`) |
| 신규 마이그레이션 | **없음.** `Order.cancelled_at`/`closed_at`(기존 컬럼, `models.py:79-80`)만 읽고 쓴다 |
| 기존 스케줄 등록 절차(참고) | `scripts/sync_orders.bat` + `scripts/run_hidden.vbs`, `.moai/project/scheduled-jobs.md` |
| 영향 API | 없음. CLI 전용 |
| 데이터 소재(기록 대상) | `Order.closed_at`(`models.py:79`), `Order.cancelled_at`(`models.py:80`) — 둘 다 nullable `DateTimeField` |
| `closed_at`/`cancelled_at`의 현재 소비처 | **0곳**(§1 참조 위치와 동일) |

---

## 3. Assumptions (명시적 가정)

| # | 가정 | 근거 / 틀렸을 때의 영향 |
|---|------|--------------------------|
| A1 | `orders.json` 목록 엔드포인트는 `ids=<최대 250개>&status=any&fields=...`를 받아 요청한 주문들의 현재 필드값을 상태와 무관하게 정확히 반환하며, 250개 이하 요청에는 `Link` 헤더가 없다 | **사용자가 2026-08-19 세션에서 프로덕션 직접 조회로 확인**(v0.3.0 정정, 감사 D4 — v0.2.0이 이를 "plan-auditor review-1"에 잘못 귀속했다. review-1 전문에 `ids=`가 등장하지 않으며, D2 지시는 `status=closed` 규모 측정이었다). 요청 문자열: `orders.json?ids=<250개 쉼표구분>&status=any&limit=250&fields=id,cancelled_at,closed_at`. 결과: 요청 250건 중 250건 반환, `cancelled_at`/`closed_at` 양쪽 채워짐, `Link` 헤더 없음. 이 세션에서 재검증하지 않고 채택한다. 250개 요청 시 URL 길이는 약 3,610자(13자리 id 250개 + 쉼표 249개 + 기본 경로, 측정치)로, 일반적인 URL 길이 제한(대부분 8KB 이상) 이내다 |
| A2 | 목록 엔드포인트의 `fields=` 파라미터는 응답을 정확히 요청한 키로 제한한다 | v0.1.0 세션에서 프로덕션 검증. 재검증하지 않는다 |
| A3 | **[미검증]** `orders/{id}.json` 단건 엔드포인트(`sync_single_order_from_shopify()`가 사용, `:334-352`)는 주문의 상태와 무관하게 항상 그 주문을 반환한다 | `OrderResyncView`가 이미 이 엔드포인트를 그렇게 가정하고 사용 중이다(기존 코드). §1의 "유일한 예외" 서술이 이 가정에 의존하나, 이 SPEC이 새로 만드는 의존성은 아니다 |
| A4 | `_sync_single_order()`의 Order-레벨 `defaults` 딕셔너리(`shopify_orders.py:133-166`)는 `closed_at`/`cancelled_at`을 무조건 쓰며(`:161-162`), `fields=`로 제한된 페이로드로 이 함수를 호출하면 (a) 다른 모든 `Order` 필드가 `None`으로 덮어써지고, (b) `order_data.get("line_items", [])`가 빈 리스트가 되어 stale-삭제(`:287-289`)가 `PurchaseOrder` 미연결 라인아이템을 전량 삭제하며, **(c) `:291`의 `order_obj.shipping_lines.all().delete()`가 `ShippingLine` 전량을, `:306`의 `order_obj.refunds.all().delete()`가 `Refund` 전량을 무조건 삭제하고, 제한 페이로드에는 `shipping_lines`/`refunds` 키가 없어(`:301`,`:307`) 아무것도 재생성되지 않는다**(v0.3.0 확장, 감사 D9 — 이 세션에서 `shopify_orders.py:287-330`을 직접 읽어 확인) | 결론: 취소·종료됐던 주문이 재오픈되면 기존 `sync_store()`가 자동으로 `cancelled_at`/`closed_at`을 NULL로 되돌린다 — 이 SPEC은 재오픈 감지 로직이 불필요하다(Exclusions #4). 동시에 (c)가 REQ-CANC-008의 근거를 강화한다 — `_sync_single_order()` 경유는 그 주문의 환불 이력을 전부 소실시킨다. 이 저장소에서 환불 넷팅은 이미 신규 경로가 반복적으로 놓쳐 프로덕션 결함을 낸 관례다(과거 SPEC-ORDER-023/026에서 연속 발생) — 이 SPEC의 좁은 쓰기 경로(REQ-CANC-007/008)가 그 결함 부류를 원천 차단한다 |
| A5 | `StoreSyncWatermark`(`models.py:565-603`)는 `sync_store()` 전용 커서다. 그 독스트링이 명시하는 사고(2026-08-15, 주문 #37413)는 단건 쓰기 경로가 공유 워터마크를 건드릴 때 발생했다 | 이 SPEC의 신규 코드는 어떤 커서/워터마크도 유지하지 않으므로 이 사고 부류를 재현할 코드 경로가 없다. 실수로 그 모델을 import/참조하는 회귀를 막기 위해 REQ-CANC-024를 명시적으로 유지한다 |
| A6 | **[미검증]** Shopify는 취소된 주문을 다시 미취소(un-cancel) 상태로 되돌리는 공개 API를 제공하지 않는다 — 취소는 종결 상태다 | 이 세션 또는 어떤 이전 세션에서도 Shopify 공식 문서로 검증되지 않았다 — 일반적인 플랫폼 지식에 근거한다. 이 가정이 틀리면(Shopify가 취소 취소를 지원하면) 후보 집합에서 `cancelled_at`이 채워진 주문을 영구 제외하는 것이 너무 이르다. 다만 영향은 낮다 — 만약 그런 주문이 다시 `status=open` 피드에 나타나면(재오픈), 기존 `sync_store()`가 이미 무조건 `cancelled_at`을 NULL로 되돌리므로(가정 A4) 로컬 데이터 자체는 여전히 정확해진다. 이 SPEC의 두 커맨드만 그 특정 주문을 자신의 조회로 다시 관찰하지 못할 뿐이다 |
| A7 | **[v0.5.0 신설]** `sync_orders`(5분 주기)의 1회 실행 소요 시간은 관측된 범위 내에서 안정적이다(18~24초) | **사용자가 이 세션에서 `logs/sync_orders.log`를 직접 확인**: 연속 4회 실행이 17:39:05→17:39:28(23s), 17:44:05→17:44:23(18s), 17:49:05→17:49:24(19s), 17:54:05→17:54:29(24s)로 매 5분 `:X4:05`에 시작해 18~24초 소요됐다(§1.2). 이 관측이 대표적이지 않고(예: Shopify 응답 지연, 대량 상태 변경 발생 시) 실행 시간이 크게 늘어나면 §1.2의 스태거링 전제(최소 2~3분 간격이면 정상적으로 겹치지 않는다)가 흔들릴 수 있다 — §8 C8이 이 잔여 위험을 명시한다 |
| A8 | **[v0.5.0 신설]** 이 세션의 MySQL `SHOW VARIABLES`가 프로덕션 RDS 인스턴스의 현재 설정을 정확히 반영한다(`innodb_lock_wait_timeout=50`, `transaction_isolation=READ-COMMITTED`, `innodb_deadlock_detect=ON`) | **사용자가 이 세션에서 직접 조회**(§1.2). 이 값들이 향후 RDS 파라미터 그룹 변경으로 바뀌면 §1.2의 "50초 타임아웃 대비 ~20초 보유" 여유 폭 계산과 §4 D10의 연성 실패 판단 근거가 재검토돼야 한다 — 이 SPEC은 그 변경을 감지하지 않는다(범위 밖) |

---

## 4. 확정된 설계 결정

- **D1 (감지와 백필은 같은 후보 집합 메커니즘을 공유하되, 유예 일수 파라미터로 갈라진다)**: 두 커맨드 모두 `open_candidate_order_ids(store_type, closed_grace_days)` 형태의 공유 함수를 호출한다(§4 D2 참조 아래) — 감지는 `closed_grace_days=30`, 백필은 `closed_grace_days=None`(무제한)을 넘긴다. 각자 독립적으로 재구현하지 않아 코드 레벨 드리프트를 방지한다.
- **D2 (후보 집합 커서 없음)**: `cancelled_at`/`closed_at`이 채워지면(또는 유예 기간을 넘기면) 그 주문은 다음 호출에서 자동으로 후보 집합을 벗어난다 — 별도 진행 상태를 저장하지 않는다. 어떤 datetime 값도 URL에 보간되지 않는다(v0.1.0 D1의 구조적 해소는 v0.2.0에서 이미 달성됐고, v0.3.0의 창 확장도 이 성질을 보존한다 — `closed_at__gte=...` 필터는 Django ORM이 파라미터화된 쿼리로 처리하며 URL 문자열 조합과 무관하다).
- **D3 (조회 비용은 로컬 건수 + 최근 종료 건수에 비례한다 — "유계화"가 아니라 "단조 증가"다)**: 백필은 오늘 기준 17회(스토어별 청킹 반영, §1.1), 감지는 무제한 모집단(17회 상당)을 상한으로 하되 실제로는 그보다 훨씬 작을 것으로 예상된다(§1.1 — 정확한 수치는 배포 후 관측). **[v0.4.0 정정, 3차 감사 D-N6]** 백필의 후보 집합(`cancelled_at IS NULL`)은 로컬 `Order` 테이블 규모와 함께 **단조 증가**한다 — "유계화"라는 표현은 오늘 시점의 결정론적 계산 가능성을 뜻할 뿐, 상한이 고정돼 있다는 뜻이 아니다. 10배 규모(로컬 약 39,000건)에서는 백필이 약 157청크가 되며(§8 C7), 이 성질과 감지 커맨드의 429 노출 가능성을 §8 C7에 명시한다.
- **D4 (기록 범위는 두 컬럼으로 좁힌다)**: 가정 A4가 서술하듯, `_sync_single_order()` 경유는 다른 `Order` 필드를 `None`으로 덮어쓰고, `PurchaseOrder` 미연결 라인아이템·`ShippingLine` 전량·`Refund` 전량을 삭제한다 — `bulk_update(["cancelled_at","closed_at"])`가 유일하게 정확한 최소 경로다(REQ-CANC-007/008).
- **D5 (재오픈된 주문은 이 SPEC이 직접 감지하지 않는다)**: 가정 A4가 서술하듯, 재오픈된 주문은 `sync_store()`가 스스로 되돌리고, 그 순간 후보 집합에 자동 재진입한다(자기 치유).
- **D6 (별도 스케줄러 등록, 중복 실행 방지 포함)**: `scripts/sync_orders.bat`의 "새 인스턴스를 시작하지 않음" 경고를 신규 `.bat`에도 포함한다(REQ-CANC-021). 권장 주기 5분 — 이 SPEC의 어떤 REQ도 주기 자체를 규정하지 않으며, 스케줄러 등록 시점의 운영 결정이다.
- **D7 (비용 추정은 스토어별 청킹을 반영해 도출한다)**: v0.2.0의 "16회/4회" 추정은 스토어 경계를 무시하고 합산 모집단(3,910, 801)에 나눗셈을 적용한 오류였다(감사 D7 — review-1 D2와 동일 부류). 청킹은 각 스토어의 후보 집합에 독립적으로 적용되므로(`plan.md` §1.3/1.4의 스토어 순회 → 청킹 순서), 올바른 산식은 `⌈gimssine건수/250⌉ + ⌈etoile건수/250⌉`이다(§1.1에서 17회로 재도출).
- **D8 (테스트의 쓰기-결과 단정은 HTTP 계층을 패치해 실제 쓰기 경로를 살려둔다)**: 쓰기 결과를 단정하는 커맨드 AC는 `order.shopify_orders._get_with_headers`(HTTP 계층)만 패치한다 — `reconcile_order_status_for_ids`나 `open_candidate_order_ids` 자체를 패치하면 실제 쓰기가 일어나지 않아 그 AC들이 요구하는 양성 증거를 원천적으로 표현할 수 없다(감사 D8). 이 저장소의 기존 관례(`test_backfill_missing_orders_command.py:17`, HTTP 계층 패치)와 정렬한다. 실패 주입이 필요한 AC만 커맨드 모듈 네임스페이스의 함수에 `side_effect`를 건다.
- **D9 (가정 A1의 출처는 실제 검증 시점을 정확히 반영한다)**: v0.2.0은 `ids=` 확인을 "plan-auditor review-1의 D2 지시"에 귀속했으나, review-1 전문에 `ids=`가 등장하지 않는다(review-1 D2는 `status=closed` 규모 측정을 지시했을 뿐이다). 실제로는 **사용자가 2026-08-19 세션에서 프로덕션을 직접 조회**해 확인한 사실이다 — v0.3.0은 이 출처를 정정한다(감사 D4).
- **D10 (동시성: 스태거링으로 완화하고, 잠금 대기 시간 초과는 연성 실패로 계상한다 — v0.5.0 신설)**: §1.2의 실측을 근거로 두 가지를 결정한다.
  (1) **스태거링**: `sync_order_cancellations`의 스케줄러 트리거를 `sync_orders`(`:X4:05` 정렬)와 최소 2~3분 어긋나게 등록한다(REQ-CANC-027). 상호 배제 잠금은 두지 않는다 — 두 잡 모두 자기 치유형 재시도 구조(후보 집합 재진입)를 이미 갖고 있어, 드문 잔여 겹침이 데이터 정합성을 해치지 않고 단지 해당 사이클의 지연이나 경보 잡음만 유발하기 때문이다(§1.2 분실 갱신·교착 상태 분석).
  (2) **잠금 대기 시간 초과를 연성 실패로 계상한다**(REQ-CANC-025/026): 두 논거를 저울질했다.
  - **경성(硬性) 편에 선 논거**: 실패를 침묵시키면 진짜 문제(예: `sync_orders`가 만성적으로 느려지고 있다는 신호)도 함께 가릴 수 있다. 이 저장소에는 정확히 이 패턴의 실패 선례가 있다 — 환율 동기화 정기 실행이 등록되지 않은 채 방치돼 `ExchangeRate`가 조용히 멈추고 마진이 과대 계상된 사고(§8 C5).
  - **연성(軟性) 편에 선 논거**: 잠금 대기 시간 초과는 §1.2에서 분석했듯 다음 사이클에 자기 치유되는, 원인이 완전히 이해된 실패 모드다(REQ-CANC-004의 후보 집합 재진입이 재시도를 구조적으로 보장한다). 자기 치유되는 실패에 5분마다 경보를 울리면 오퍼레이터가 그 경보를 습관적으로 무시하게 되는 경보 피로가 발생하고, 그 상태에서 진짜(비-잠금) 실패가 나도 같은 잡음으로 취급될 위험이 크다 — ExchangeRate 사고(과소 경보가 신호를 죽인 사례)와 **반대 방향의 실패 모드**(과다 경보가 신호를 죽이는 사례)다.
  - **판단**: 연성으로 계상하되, 정보 자체는 지우지 않는다 — `chunk_failures`에 `lock_timeout=True`로 계속 기록·로그 출력하고(REQ-CANC-025), 오직 "그 스토어의 모든 실패가 잠금 대기 시간 초과였는가"만을 `CommandError` 발생 여부의 기준으로 삼는다(REQ-CANC-026). 하나라도 비-잠금 실패가 섞이면 즉시 REQ-CANC-017의 경성 실패 경로로 되돌아간다 — ExchangeRate 사고가 경계하는 "실패를 완전히 숨긴다"는 상황과는 다르다. 이 판단이 틀렸다고 판명되면(예: 잠금 대기 시간 초과가 실제로는 만성적 문제의 전조였던 사례가 관측되면) `chunk_failures`의 `lock_timeout` 필드가 이미 로그에 남아 있으므로 사후 분석과 재판단이 가능하다 — 정보 손실 없는 가역적 선택이다.

---

## 5. Requirements (EARS)

REQ 접두사는 `REQ-CANC-`를 쓴다.

### 모듈 1 — Shopify 조회 메커니즘 (`ids=` + `status=any`) `[NEW]`

**REQ-CANC-001** (Ubiquitous) [HARD]
THE 시스템은 Shopify `orders.json` 목록 엔드포인트를 `ids=<최대 250개, 쉼표구분 shopify_order_id>&status=any&fields=id,cancelled_at,closed_at&limit=250`로 조회하여, 요청한 주문들의 **현재** `cancelled_at`/`closed_at` 값을 그 주문의 상태와 무관하게 shall 가져온다(가정 A1). `fields=`와 `limit=250`은 매 요청에 shall 포함된다.

**REQ-CANC-002** (Ubiquitous) [HARD]
THE 시스템은 단일 조회 요청에 최대 250개의 `shopify_order_id`만 shall 포함한다 — 그 이상의 후보 집합은 여러 요청으로 shall 분할한다(청킹).

**REQ-CANC-003** (Event-Driven) [HARD]
**When** 단일 청크 요청(≤250개 id)에 대한 Shopify 응답에 `Link` 헤더(`rel="next"`)가 예상 밖으로 포함되면, THE 시스템은 그 헤더를 따라 다음 페이지까지 shall 조회한다.

### 모듈 2 — 후보 집합 산정 메커니즘 `[NEW/REDESIGNED, v0.3.0]`

**REQ-CANC-004** (Ubiquitous) [HARD]
THE 시스템은 조정 대상(후보 집합)을 다음과 같이 shall 정의한다: `cancelled_at IS NULL AND (closed_at IS NULL OR closed_at >= 현재 시각 - closed_grace_days)`. `closed_grace_days`는 호출자가 지정하는 파라미터이며, 지정하지 않으면(`None`) `closed_at` 조건 자체를 걸지 않는다(무제한 — `cancelled_at IS NULL`인 모든 주문 포함). `cancelled_at`이 채워지면 그 주문은 `closed_grace_days` 값과 무관하게 후보 집합에서 shall 영구 제외된다(가정 A6).

**REQ-CANC-005** (Ubiquitous) [HARD]
THE 시스템은 후보 집합을 스토어(`store_type`)별로 shall 별도 산정한다.

**REQ-CANC-006** (Event-Driven) [HARD]
**When** 한 번의 조정 호출이 완료되면, THE 시스템은 요청한 주문 id 수와 Shopify가 실제로 반환한 레코드 수의 차이(`missing_ids` — Shopify에서 삭제됐거나 반환되지 않은 id)를 shall 보고한다.

### 모듈 3 — 필드 기록 범위 `[NEW]`

**REQ-CANC-007** (Ubiquitous) [HARD]
매칭되는 로컬 `Order` 행이 있는 각 레코드에 대해, THE 시스템은 정확히 `cancelled_at`과 `closed_at` 두 필드만 shall 갱신하며, 그 외 어떤 `Order` 필드나 `LineItem`/`ShippingLine`/`Refund` 필드·행도 shall not 쓰거나 그것을 쓰는 코드 경로를 shall not 경유한다.

**REQ-CANC-008** (Ubiquitous) [HARD]
THE 시스템은 `_sync_single_order()`(`shopify_orders.py:104`)를 shall not 호출하고, `fields=`로 제한된 페이로드로부터 만든 `defaults` 딕셔너리를 `update_or_create()`에 shall not 넘긴다 — 그 경로는 다른 `Order` 필드를 `None`으로 덮어쓸 뿐 아니라(가정 A4-a), `PurchaseOrder` 미연결 라인아이템(A4-b), `ShippingLine` 전량, `Refund` 전량(A4-c)을 삭제하며 제한 페이로드에는 재생성 소스가 없다.

**REQ-CANC-009** (State-Driven) [HARD]
**While** 조회된 레코드에 매칭되는 로컬 `Order`가 없으면, THE 시스템은 예외를 발생시키지 않고 shall 건너뛴다.

**REQ-CANC-010** (Ubiquitous) [HARD]
THE 시스템은 각 레코드가 실제로 반환한 `cancelled_at`/`closed_at` 값을 그대로 shall 기록하며, 한 필드의 값으로 다른 필드의 값을 shall not 추론하지 않는다.

### 모듈 4 — 청킹 완전성과 실패 진단 `[NEW]`

**REQ-CANC-011** (State-Driven) [HARD] `[v0.4.0 라벨 정정, 3차 감사 D-N4 — HISTORY는 이 정정을 v0.3.0에서 이미 반영했다고 잘못 단정했으나 본문은 실제로 정정되지 않았었다]`
**While** 후보 집합이 250건을 초과하는 동안, THE 시스템은 **모든** 청크를 shall 처리한다 — 첫 청크만 처리하고 종료해서는 안 된다.

**REQ-CANC-012** (Unwanted) [HARD]
**If** 한 청크의 처리 중 예외가 발생하면, **then** THE 시스템은 그 청크에 포함된 주문 id 목록과 오류 내용을 함께 shall 기록한다 — 오류 문자열만 남기고 대상 id를 shall not 버린다(운영 진단 가능성 보장).

### 모듈 5 — 상시 감지 커맨드 (`sync_order_cancellations`) `[NEW]`

**REQ-CANC-013** (Ubiquitous) [HARD]
THE 시스템은 `python manage.py sync_order_cancellations`로 실행 가능한 신규 관리 커맨드를 shall 제공한다.

**REQ-CANC-014** (Ubiquitous) [HARD]
감지 커맨드는 후보 집합 조회 시 `closed_grace_days=30`을 shall 사용한다(§1.1, §4 D1).

**REQ-CANC-015** (Unwanted) [HARD]
**If** 하나의 스토어 처리 중 예외가 발생하면, **then** THE 시스템은 나머지 스토어의 처리를 shall not 중단하고 계속 진행한다.

**REQ-CANC-016** (Unwanted) [HARD]
**If** 하나의 청크 처리 중 예외가 발생하면, **then** THE 시스템은 같은 스토어의 나머지 청크 처리를 shall not 중단하고 계속 진행한다.

**REQ-CANC-017** (Complex) [HARD]
**While** 하나 이상의 스토어 또는 청크가 예외로 실패한 상태에서, **when** 모든 대상에 대한 처리 시도가 끝나면, THE 시스템은 0이 아닌 종료 코드(`CommandError`)를 shall 반환한다.

### 모듈 6 — 1회성 백필 (`backfill_order_cancellations`) `[NEW]`

**REQ-CANC-018** (Ubiquitous) [HARD]
THE 시스템은 `python manage.py backfill_order_cancellations`로 실행 가능한 별도의 관리 커맨드를 shall 제공하며, 모듈 1~5와 동일한 메커니즘을 각 스토어의 후보 집합에 대해 1회 수행한다.

**REQ-CANC-019** (Ubiquitous) [HARD]
백필 커맨드는 후보 집합 조회 시 `closed_grace_days`를 shall 지정하지 않는다(무제한 — §1.1, §4 D1). 이는 감지 커맨드의 30일 창을 넘긴 잔여 노출을 흡수하는 유일한 경로다.

**REQ-CANC-020** (Optional) [HARD]
WHERE `--dry-run` 인자가 주어지면, THE 시스템은 어떤 로컬 주문이 어떻게 바뀔지 stdout에 보고만 하고 아무것도 shall not 쓴다.

### 모듈 7 — 스케줄 등록 `[NEW]`

**REQ-CANC-021** (Ubiquitous) [HARD]
THE 시스템은 `sync_order_cancellations` 커맨드를 `scripts/sync_order_cancellations.bat` + 기존 `scripts/run_hidden.vbs`로 Windows 작업 스케줄러에 등록 가능한 형태로 shall 제공하며, `scripts/sync_orders.bat` 구조를 다음 5개 항목 전부에서 shall 미러링한다: (1) 작업 디렉터리 `backend/` 고정, (2) `PYTHONIOENCODING=utf-8`, (3) 전용 로그 파일, (4) 종료 코드 전파, (5) 작업 스케줄러 "새 인스턴스를 시작하지 않음" 설정. `scripts/sync_orders.bat`에는 shall not 통합한다.

### 모듈 8 — 기존 불변식 보존 `[EXISTING]`

**REQ-CANC-022** (Ubiquitous) [HARD]
감지 커맨드와 백필 커맨드 어느 쪽도 `LineItem` 행을 shall not 수정한다.

**REQ-CANC-023** (Ubiquitous) [HARD]
감지 커맨드와 백필 커맨드 어느 쪽도 `Order.status` 또는 `Order.ready_to_ship`(`models.py:49-62`)을 shall not 수정한다.

**REQ-CANC-024** (Ubiquitous) [HARD]
감지 커맨드와 백필 커맨드 어느 쪽도 `StoreSyncWatermark`의 어떤 필드도 shall not 읽거나 쓴다.

### 모듈 9 — 동시성: 기존 sync_orders와의 상호작용 `[NEW, v0.5.0]`

**REQ-CANC-025** (Event-Driven) [HARD]
**When** 청크 처리 중 발생한 예외가 MySQL 잠금 대기 시간 초과(에러 코드 1205, "Lock wait timeout exceeded" 메시지)에 해당하면, THE 시스템은 그 `chunk_failures` 엔트리에 `lock_timeout=True`를 shall 기록한다 — 그 외 예외는 `lock_timeout=False`로 shall 기록한다.

**REQ-CANC-026** (Unwanted) [HARD]
**If** 한 스토어의 `chunk_failures`에 포함된 모든 엔트리가 `lock_timeout=True`이면, **then** THE 시스템은 그 스토어를 감지 커맨드의 `failed` 목록에 shall not 추가한다(즉 `CommandError`를 shall not 발생시킨다) — 다만 그 `chunk_failures` 엔트리 자체는 REQ-CANC-012에 따라 shall 계속 기록·로그 출력된다. 하나라도 `lock_timeout=False`인 엔트리가 섞여 있으면 그 스토어는 REQ-CANC-017에 따라 shall `failed` 목록에 포함된다.

**REQ-CANC-027** (Ubiquitous) [HARD]
THE 시스템은 `sync_order_cancellations`의 Windows 작업 스케줄러 트리거 시각을 `sync_orders`의 트리거 시각(매 5분, `:X4:05` 정렬)과 최소 2분 이상 어긋나게 shall 등록한다(권장: `:X2:30`, §4 D10). 등록 시 실제 트리거 시각이 오프셋을 반영하는지는 REQ-CANC-021과 동일하게 DoD로만 검증한다 — 코드 자체는 스케줄을 강제하지 않는다.

---

## 6. Traceability (REQ → AC)

| REQ | AC |
|-----|-----|
| REQ-CANC-001 | AC-CANC-001, AC-CANC-002, AC-CANC-006 |
| REQ-CANC-002 | AC-CANC-007 |
| REQ-CANC-003 | AC-CANC-009 |
| REQ-CANC-004 | AC-CANC-001, AC-CANC-002, AC-CANC-010, AC-CANC-011 |
| REQ-CANC-005 | AC-CANC-010 |
| REQ-CANC-006 | AC-CANC-012 |
| REQ-CANC-007 | AC-CANC-018, AC-CANC-022 |
| REQ-CANC-008 | AC-CANC-018, AC-CANC-022 |
| REQ-CANC-009 | AC-CANC-005 |
| REQ-CANC-010 | AC-CANC-003, AC-CANC-004 |
| REQ-CANC-011 | AC-CANC-008 |
| REQ-CANC-012 | AC-CANC-016 |
| REQ-CANC-013 | AC-CANC-015, AC-CANC-017 |
| REQ-CANC-014 | AC-CANC-014 |
| REQ-CANC-015 | AC-CANC-015 |
| REQ-CANC-016 | AC-CANC-016 |
| REQ-CANC-017 | AC-CANC-017 |
| REQ-CANC-018 | AC-CANC-020, AC-CANC-023 |
| REQ-CANC-019 | AC-CANC-019 |
| REQ-CANC-020 | AC-CANC-021 |
| REQ-CANC-021 | AC 없음 — DoD 검증(`scripts/sync_order_cancellations.bat` 파일 존재 + 5개 미러링 항목 육안 확인 + 스케줄러 등록·1회 성공 실행 확인) |
| REQ-CANC-022 | AC-CANC-018, AC-CANC-022 |
| REQ-CANC-023 | AC-CANC-018, AC-CANC-022 |
| REQ-CANC-024 | AC-CANC-013 |
| REQ-CANC-025 | AC-CANC-024 |
| REQ-CANC-026 | AC-CANC-025 |
| REQ-CANC-027 | AC 없음 — DoD 검증(등록된 `sync_order_cancellations` 작업 트리거의 실제 시작 시각을 `sync_orders` 트리거 시각과 대조해 최소 2분 이상 어긋나 있는지 확인) |

> **[HARD] 추적표 무결성 규칙**: REQ가 그 위반을 실제로 검출할 수 없는 AC에 매핑되어 있으면 그 REQ는 미커버다. AC 없이 DoD 검사만으로 보증되는 REQ는 "(AC 없음 — DoD 검증)"으로 명시한다.

> **[프로세스 확인 — "실행한 grep 명령과 출력을 각주로 붙이거나 삭제하라"는 지시에 따라 실제로 실행한 명령과 결과를 기록한다]**
>
> **v0.3.0 시점 실행(2026-08-19)**: 아래 3~4항의 불일치 발견·정정과 파일 소속 5곳 대조는 v0.3.0 작성 시점에 수행됐다.
> 1. `Grep pattern="^\*\*REQ-CANC-\d+\*\*" path=spec.md` → 24개 매치(`REQ-CANC-001`~`024`, 각 1회) — 위 §6 표의 행 수와 정확히 일치. "25개"라는 표현은 문서 어디에도 쓰지 않는다(v0.2.0의 오기가 재발할 표현 자체를 제거했다).
> 2. `Grep pattern="^Traces:" path=acceptance.md` → 23개 매치 — AC-CANC-001~023과 1:1, 파일 순서와 AC 번호 순서가 일치.
> 3. 두 추출 결과를 수작업으로 양방향 대조한 결과 **불일치 1건 발견**: AC-CANC-020의 `Traces:`가 `REQ-CANC-018, REQ-CANC-019`였으나, §6 표는 `REQ-CANC-019 → AC-CANC-019`만 선언했고 AC-CANC-020은 REQ-CANC-019가 요구하는 "closed_grace_days 전달값"을 실제로 단정하지 않는다(AC-CANC-020의 판별력은 M20 — 기존 취소 반영 여부 — 하나뿐이다). **그 자리에서 `Traces: REQ-CANC-018`로 정정했다** — 재검증 후 불일치 0건. 이 1건은 이번 리비전 작성 과정에서 실제로 발견·수정됐으며, "처음부터 0건이었다"고 소급 서술하지 않는다.
> 4. AC 소속 파일(v0.2.0 D3의 실패 지점 — `acceptance.md` 헤더, 섹션 제목, `[CORE]`/`[COMMAND]` 태그, `plan.md` M1/M2/M3, DoD)을 5곳 각각 읽어 대조 — AC-CANC-001~012는 `test_spec_029.py`, AC-CANC-013~018은 `test_sync_order_cancellations_command.py`, AC-CANC-019~023은 `test_backfill_order_cancellations_command.py`로 5곳 전부 일치.
>
> **v0.4.0 재실행(2026-08-19, 같은 세션)**: plan-auditor 3차 리뷰가 위 각주를 독립적으로 재실행해 "라인 번호까지 한 자리도 틀리지 않는다"고 확인했다(review-3 §3). 이번 v0.4.0 개정은 REQ-CANC-011 라벨 정정과 AC-CANC-005/007/017의 본문 확장으로 문서 전체의 줄 번호가 이동했으므로, **이전 각주에 박제된 줄 번호(라인 149~232, 64~398)를 그대로 두면 그 자체가 새로운 stale-evidence 결함이 된다** — v0.4.0 편집 완료 직후 두 명령을 다시 실행했다: `REQ-CANC-\d+` 매치는 여전히 정확히 24개(현재 라인 152~235), `Traces:` 매치는 여전히 정확히 23개(현재 라인 66~410)이며, 위 §6 표와 재대조한 결과 **불일치 0건**이다(3항의 AC-CANC-020 정정은 v0.3.0에서 이미 반영된 상태로 유지된다). 이번 개정부터는 절대 줄 번호를 각주에 고정하지 않고 "몇 개 매치, 1:1 대응 여부"만 기술한다 — 줄 번호는 문서가 변경될 때마다 깨지는 종류의 증거이기 때문이다.
>
> **v0.5.0 재실행(2026-08-19, 같은 세션, 실제 명령·출력)**: 동시성 절(REQ-CANC-025~027, AC-CANC-024/025) 추가로 두 문서 모두 다시 늘어났으므로, 감사 없이 진행하는 이번 개정에서도 스스로 재검증했다 — 실행한 명령과 원시 출력:
> 1. `grep -cE '^\*\*REQ-CANC-[0-9]+\*\*' spec.md` → **27**. `grep -cE '^Traces:' acceptance.md` → **25**. `grep -coE '^## AC-CANC-[0-9]+' acceptance.md` → **25**. 세 개수 모두 위 §5(27개 REQ)·§6(27행)·`acceptance.md` §0.1(25개 변이)의 선언과 일치한다.
> 2. §6 표의 REQ→AC 매핑과 `acceptance.md`의 모든 `Traces:` 줄을 양방향으로 대조하는 스크립트를 실제로 실행했다(정규식으로 표 27행과 `Traces:` 25줄을 각각 파싱해 REQ→AC/AC→REQ 두 방향 모두 대응 여부 확인) — 결과: **REQ 27개, Traces 25개, 불일치 0건**. 특히 AC-CANC-024의 `Traces: REQ-CANC-025`와 AC-CANC-025의 `Traces: REQ-CANC-026`가 §6 표의 `REQ-CANC-025 → AC-CANC-024`, `REQ-CANC-026 → AC-CANC-025` 행과 정확히 대응함을 확인했다 — REQ 번호와 AC 번호가 1씩 어긋나 보이는 지점(REQ-025가 AC-024를 가리킴)이 실수가 아니라 REQ-CANC-024(기존, 워터마크)가 이미 그 번호를 쓰고 있어 신규 REQ가 025부터 시작했기 때문임을 이 재확인 과정에서 재확인했다.
> 3. 이전 회차(v0.3.0/v0.4.0)와 마찬가지로 절대 줄 번호는 각주에 남기지 않는다 — v0.5.0에서 §1.2/모듈 9/AC-CANC-024·025 삽입으로 문서 전체 줄 번호가 다시 이동했으므로, 줄 번호를 박았다면 이 문장 자체가 이번에도 stale evidence가 됐을 것이다.

---

## 7. Exclusions (What NOT to Build)

1. **신규 `Order` 행 생성 — 하지 않는다.** 로컬에 없는 취소·종료 주문은 조용히 건너뛴다(REQ-CANC-009).
2. **UI/API 서피스 — 신설하지 않는다.** `cancelled_at`/`closed_at`은 현재 백엔드 어디에서도 읽히지 않는다.
3. **취소된 주문의 라인아이템에 대한 어떤 결정도 — 내리지 않는다.** `logistics_status="not_shipped"`로 남은 79개 라인아이템과 그중 `PurchaseOrder`가 연결된 51개는 이 SPEC 전후로 정확히 동일하게 유지된다(REQ-CANC-022).
4. **재오픈(취소·종료 → 다시 open) 주문의 전용 감지 로직 — 만들지 않는다.** 가정 A4/A6·설계 결정 D5가 서술하듯, 재오픈된 주문은 `sync_store()`가 스스로 되돌리고, 그 순간 후보 집합에 자동 재진입한다.
5. **Shopify 429(rate limit) 응답에 대한 재시도/백오프 — 신설하지 않는다.** 이 SPEC의 호출량은 로컬 건수로 유계화된다(§1.1). **429처럼 일시적인 실패는** 그 청크만 실패로 계상되고(REQ-CANC-016) 다음 실행에서 그 주문이 여전히 후보 집합에 남아(REQ-CANC-004) 재시도되므로 자연히 수렴한다 — **영구적인 실패 원인(예: 특정 id에 대한 지속적인 400/422)이 있는 경우는 자연히 수렴하지 않는다**(§8 C6 참조. v0.3.0 정정, 감사 D6 — v0.2.0은 이 구분 없이 "자연히 수렴한다"고만 서술해 과잉 일반화했다).
6. **주문 편집 시 라인아이템 삭제 결함 — 고치지 않는다.** `_sync_single_order()`가 `PurchaseOrder` 미연결 라인아이템만 stale-삭제하는 기존 동작(`:287-289`)은 이 SPEC 이전부터의 별개 결함이며, 이 SPEC은 그 로직을 건드리지 않는다.
7. **감지 잡 진행 상황을 보여주는 UI 대시보드 — 신설하지 않는다.**
8. **[v0.5.0 신설]** **감지 커맨드와 `sync_orders` 사이의 상호 배제 잠금(뮤텍스/어드바이저리 락) — 두지 않는다.** 스태거링(REQ-CANC-027)이 정상 상태의 겹침을 방지하고, 두 잡 모두 자기 치유형 재시도 구조를 이미 갖추고 있어(§1.2) 드문 잔여 겹침이 데이터 정합성을 해치지 않는다. `sync_orders`의 트랜잭션 구조(§1.2가 노출의 원인으로 지목하는, `transaction.atomic()` 블록 안의 API 왕복) 자체를 변경하는 것도 이 SPEC의 범위 밖이다.

---

## 8. 알려진 제약 / 후속 과제

| # | 내용 |
|---|------|
| C1 | `_sync_single_order()`가 `PurchaseOrder` 미연결 라인아이템만 stale-삭제하는 기존 동작(`:287-289`)은 이 SPEC 이전부터의 별개 결함이며, 이 SPEC의 범위 밖이다 |
| C2 | 가정 A1이 깨지면 REQ-CANC-001의 조회가 실패하거나 레코드가 누락될 수 있다 — 전자는 REQ-CANC-017(실패 집계)로 드러나고, 후자는 REQ-CANC-003(방어적 Link 헤더 추적)이 흡수한다 |
| C3 | 가정 A3(단건 엔드포인트가 상태 무관 반환)이 틀리면 `OrderResyncView`를 통한 개별 취소 주문 재동기화가 실패할 수 있다 — 이 SPEC의 범위 밖이다 |
| C4 | 감지 커맨드와 백필 커맨드가 동일한 후보 집합 메커니즘을 `closed_grace_days` 파라미터만 다르게 공유하는 것(§4 D1)은 의도된 단순화다 |
| C5 | **[v0.3.0 신설, 감사 D1 대응]** 감지 커맨드의 30일 유예 창을 넘긴 "종료 후 취소"는 다음 백필 실행까지 미반영 상태로 남는다(§1.1의 잔여 노출 서술). 실측된 1건의 정확한 종료→취소 간격이 30일 이내였는지는 확인되지 않았다. 운영 권고(REQ 아님): 백필을 정기적으로(예: 월 1회, `scripts/sync_orders.bat` 등록 절차를 미러링한 별도 저빈도 작업으로) 재실행해 이 잔여 노출의 상한을 "다음 백필 주기까지"로 좁힌다. **[v0.4.0 추가, 3차 감사 D-N5]** 이 저장소에는 정확히 이 패턴(권고로만 남은 정기 작업이 실제로는 등록되지 않는 것)의 실패 선례가 있다 — 환율 동기화 정기 실행이 등록되지 않아 `ExchangeRate`가 멈추고 마진이 과대 계상됐던 사고. 이 위험을 낮추기 위해 `acceptance.md` DoD 스케줄러 절에 백필 저빈도 등록 여부를 명시적으로 기록하는 체크박스를 추가했다(등록 완료 또는 "등록하지 않기로 한 결정을 `.moai/project/scheduled-jobs.md`에 기록" 중 하나를 선택) |
| C6 | **[v0.3.0 신설, 감사 D1/D6 대응]** Shopify에서 영구적으로 삭제된 주문은 `ids=` 응답에서 그냥 누락되며, 두 필드가 영원히 NULL이라 후보 집합에 무기한 잔류하고 매 사이클 재조회된다 — REQ-CANC-006의 `missing_ids` 보고가 이를 드러내지만 자동으로 제거하지는 않는다. 마찬가지로, 한 청크에 영구적 실패 원인(예: 특정 id에 대한 지속적인 400/422)이 있으면 같은 청크의 나머지 최대 249건이 매 사이클 함께 실패로 계상된다 — REQ-CANC-012의 `chunk_failures` id 목록으로 운영자가 그 부분집합을 식별해 수동 조치(예: 해당 주문을 스킵 처리하거나 개별 확인)할 수 있다. 이 SPEC은 자동 격리·자동 스킵 로직을 두지 않는다 — 진단 정보 제공까지가 범위다 |
| C7 | **[v0.4.0 신설, 3차 감사 D-N6 — 개방 위험, 재설계 불필요]** 백필의 후보 집합(`cancelled_at IS NULL`, 창 없음)은 로컬 `Order` 테이블 규모와 함께 단조 증가한다 — 오늘 17청크, 10배 규모(로컬 약 39,000건)에서 약 157청크(청크당 Shopify 왕복 1회 + DB 조회 1회, 원격 MySQL ~130ms/쿼리 기준 실행 시간 약 1.5~2분으로 추정 — 월 1회 수동/저빈도 실행 기준으로는 무해). 같은 규모에서 감지 커맨드는 5분 사이클당 약 45청크가 되어 Shopify의 누수 버킷(버스트 40, 초당 2 회복)을 넘길 수 있다 — 이 시점부터 429가 실제로 발생하기 시작한다. Exclusions #5는 호출 **양**이 로컬 건수로 유계화된다는 근거로 429 백오프를 배제하는데, 호출 **속도**에 대한 별도 분석은 없다. 실패 모드 자체는 우아하다 — 청크 실패는 `chunk_failures`에 기록되고(REQ-CANC-012), 그 주문은 여전히 후보 집합에 남아(REQ-CANC-004) 다음 사이클에 재시도되므로 데이터 유실이나 무한 반복 없이 수렴한다(Exclusions #5). 오늘 규모에서는 도달 불가능하므로 재설계는 불필요하다 — 로컬 주문 규모가 유의미하게 커지면(예: 감지 사이클당 40청크 근접) Exclusions #5의 무백오프 결정을 재검토한다 |
| C8 | **[v0.5.0 신설]** 스태거링(REQ-CANC-027)은 감지 커맨드와 `sync_orders`의 정상 상태 겹침을 방지하지만, `sync_orders`가 스태거 간격(권장 2~3분)을 넘겨 실행되면 여전히 겹칠 수 있다(§1.2 잔여 위험). 이 SPEC은 상호 배제 잠금을 두지 않는다(§7 Exclusions #8) — 겹침이 발생해도 세 상호작용(분실 갱신·잠금 대기·교착 상태) 모두 다음 사이클에 자기 치유되므로 데이터 정합성 위험은 없으나, 겹침이 빈번해지면 잠금 대기로 인한 청크 실패 빈도가 늘어 §1.2의 연성 실패 분류(REQ-CANC-026)가 흡수해야 할 잡음이 커진다. `sync_orders`의 실행 시간이 구조적으로(예: 대량 배치 변경, Shopify 응답 지연 상시화) 늘어나는 추세가 관측되면 스태거 간격을 재조정하거나 상호 배제 잠금 도입을 재검토한다 |

---

Version: 0.5.0
REQ coverage: REQ-CANC-001 ~ REQ-CANC-027 (27개, 결번 없음)
