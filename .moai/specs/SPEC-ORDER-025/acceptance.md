# Acceptance Criteria — SPEC-ORDER-025

판별력 원칙(프로젝트 확정 규칙): 각 AC는 자신을 깨뜨리는 mutation을 명시하고, 그 mutation을 실제로 주입했을 때 실패해야 한다. "통과하는 테스트"가 아니라 "틀린 구현에서 반드시 실패하는 테스트"를 기준으로 작성한다.

> v1.1.0: plan-audit 1차 리뷰(FAIL, 0.62) 반영. D4/D5/D6/D1/D7/D11/D12를 해소했다.
> v1.2.0: plan-audit 2차 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-025-review-2.md`, FAIL, 0.71) 반영 + 사용자 승인 범위 추가(R4 확장, spec.md D4/REQ-LCONF-304~308). **ND1**(AC-014의 판별 mutation이 DRF 프로젝트 기본 설정 때문에 실제로는 통과 상태를 못 깨뜨리는 오류 — `permission_classes = [AllowAny]`로 정정 + AC-014b 신설), **ND2**(AC-302b가 Given에서 노트 존재를 전제해 항상 통과하고 AC-302c가 무관한 스위트 재실행에 그쳐 판별력이 0이었던 문제 — REQ-LCONF-303의 사실 오류 정정과 함께 재작성), **ND5**(AC-012가 SQLite 기본 엔진에서 `select_for_update()`가 무시돼 판별력을 잃는 문제 — 결정론적 SQL 단정(012a)과 마커 명시 스레드 테스트(012b)로 분할), **ND3**(`test_spec_024.py` 참조 수 11→10 정정)를 해소했다. 신규 REQ-LCONF-107/108/204/304~308에 대응하는 AC를 추가/재배치했다.
> v1.3.0: plan-audit 3차(최종) 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-025-review-3.md`, FAIL, 0.78) 반영 + 사용자 승인 범위 추가(spec.md D5/REQ-LCONF-309, Daily Review 업로드의 타출판사 노트 무조건 생성). **ND-A**(critical — AC-LCONF-308이 지정한 픽스처의 메모 기본값이 빈 문자열이라 무수정 코드에서도 실패하는 결함이었음 — REQ-LCONF-309 신설로 실제로 참이 되는 주장으로 재작성, blank-memo(308a)/filled-memo(308b) 두 케이스 + 범위 한정 대조군(309c) 추가), **ND-B**(major — AC-305의 mutation 서술에서 근거 없는 두 소비처 언급 제거), **ND-D**(minor — 품질 게이트에 `purchaseOrderApi.test.ts:23-35` 기존 단정 반전 필요성 명시)를 해소했다.
> v1.4.0: plan-audit 4차(최종) 리뷰(`.moai/reports/plan-audit/SPEC-ORDER-025-review-4.md`, **PASS, 0.90**) 반영 — SPEC 승인, 마지막 정리 패스. **ND-G**(AC-LCONF-308a가 참조하던 "REQ-LCONF-309가 규정하는 기본 안내 문구"를 `spec.md`가 확정한 리터럴로 직접 단정하도록 정정), **ND-H**(근거 없이 홀로 있던 `AC-LCONF-309c`를 `AC-LCONF-308c`로 개명해 308a/308b/308c 연속 그룹으로 정리)를 해소했다. **ND-I**(REQ-LCONF-202 타입 절의 AC 부재)는 AC를 신설하는 대신 `tsc -b` 게이트가 이미 판별력을 갖는 이유(타입 비-optional 필드와 픽스처 3곳 제거가 서로를 강제)를 AC-LCONF-202 아래에 명시적으로 기록했다.

---

## R1 — LineItem 단건 발주처리 백엔드 엔드포인트

### AC-LCONF-001 — 정상 발주처리(일반 행)

- **Given** `purchase_status="unordered"`이고 어떤 `PurchaseOrder`에도 연결되지 않은 LineItem(`quantity=5`, 환불 없음, `sku="ISBN-A"`)이 존재한다.
- **When** `POST /api/purchase-orders/line-items/<pk>/confirm/` `{"distributor": "북센직접입력", "unit_price": "12000"}`을 요청한다.
- **Then** HTTP 201이며, 신규 `PurchaseOrder`가 정확히 1개 생성되고(`status="confirmed"`, `distributor="북센직접입력"`, `quantity=5`, `unit_price=Decimal("12000")`), 그 `PurchaseOrder.line_items`에 대상 LineItem이 포함되며, LineItem의 `confirmed_distributor=="북센직접입력"`이고 `confirmed_price==Decimal("12000")`이며 `purchase_status`는 `"unordered"`로 변함이 없다.
- **판별 mutation**: `confirmed_distributor`/`confirmed_price`만 갱신하고 `PurchaseOrder`를 생성하지 않는 구현 → `PurchaseOrder.objects.filter(line_items=li).count() == 0`이 되어 단정 실패.

### AC-LCONF-002 — damaged_exchange 행의 순수량 계산 + 상태 자동 복귀

- **Given** `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`, 환불 없음인 LineItem이 이미 다른 `PurchaseOrder`(파손 이전 발주, 무관)에 연결되어 있다.
- **When** `POST .../confirm/` `{"distributor": "kyobo", "unit_price": null}`을 요청한다.
- **Then** HTTP 201이며, 신규 `PurchaseOrder.quantity == 3`(damaged_quantity 기반, `quantity=10`이 아님)이고 `unit_price is None`이며, LineItem의 `purchase_status`는 `"unordered"`로 재설정된다.
- **판별 mutation**: `base_qty`를 항상 `li.quantity`로 계산(damaged_quantity 무시)하는 구현 → `PurchaseOrder.quantity == 10`이 되어 단정 실패. `purchase_status`를 재설정하지 않는 구현 → 두 번째 단정 실패.

### AC-LCONF-003 — 이미 연결된 unordered 행 → 409, 부작용 없음

- **Given** `purchase_status="unordered"`인 LineItem이 이미 `PurchaseOrder`(status="confirmed")에 연결되어 있다.
- **When** 같은 LineItem에 대해 다시 `POST .../confirm/`을 요청한다.
- **Then** HTTP 409이며, `PurchaseOrder.objects.count()`는 요청 전후 동일(신규 생성 없음), LineItem의 `confirmed_distributor`도 요청 전 값 그대로다.
- **판별 mutation**: 409 가드가 없거나 `select_for_update()` 이전 상태로 판정하는 구현 → 두 번째 `PurchaseOrder`가 생성되어 count 단정 실패.

### AC-LCONF-004 — 부적격 상태 5종 전수 검증(parametrize)

REQ-LCONF-006이 열거하는 부적격 상태 5종을 모두 파라미터화한다. `on_hold` 1건만 검증하면 단일값 블랙리스트 구현(`if purchase_status == "on_hold": raise ConflictError`)이 통과해버리므로, 5종 전부를 개별 케이스로 실행해야 그 편향을 잡는다.

| 케이스 | Given: LineItem 상태 | When | Then |
|--------|----------------------|------|------|
| AC-LCONF-004a | `purchase_status="on_hold"`, 미연결 | `POST .../confirm/` | HTTP 409, `PurchaseOrder` 미생성 |
| AC-LCONF-004b | `purchase_status="order_cancelled"`, 미연결 | 〃 | 〃 |
| AC-LCONF-004c | `purchase_status="cs_required"`, 미연결 | 〃 | 〃 |
| AC-LCONF-004d | `purchase_status="other_publisher"`, 미연결 | 〃 | 〃 |
| AC-LCONF-004e | `purchase_status="in_stock"`, 미연결 | 〃 | 〃 |

- **판별 mutation**: 자격 검사를 단일값 블랙리스트(`on_hold`만 검사)로 구현 → AC-LCONF-004a만 통과하고 004b~004e 전부 200/201이 되어 실패. 특히 004d(`other_publisher`)가 중요하다 — R4(REQ-LCONF-302)가 이 상태의 행을 보류/제외 뷰에서 감추므로, 이 가드가 잘못된 발주처리를 막는 마지막 방어선이다. v1.2.0 이후로는 `other_publisher`가 `PURCHASE_STATUS_OPTIONS`에서도 제거되므로(REQ-LCONF-304), 이 케이스는 API 직접 호출이나 레거시 데이터에 대한 방어로서 의미가 남는다.

### AC-LCONF-005 — 전액 환불된 행(순수량 0) → 409

- **Given** `purchase_status="unordered"`, `quantity=2`, 해당 (order, shopify_line_item_id)에 대해 `Refund.quantity` 합이 2인 LineItem이 존재한다(전액 환불, 미연결).
- **When** `POST .../confirm/`을 요청한다.
- **Then** HTTP 409이며 `PurchaseOrder`가 생성되지 않는다.
- **판별 mutation**: 순수량을 요청 시점에 재계산하지 않고 항상 원본 `quantity`를 쓰는 구현 → 200/201로 성공해 단정 실패.

### AC-LCONF-006 — distributor 공백 → 400

- **Given** 자격을 갖춘 LineItem이 존재한다.
- **When** `{"distributor": "   ", "unit_price": null}`로 요청한다.
- **Then** HTTP 400이며 `PurchaseOrder`가 생성되지 않는다.

### AC-LCONF-007 — distributor 21자 → 400

- **Given** 자격을 갖춘 LineItem이 존재한다.
- **When** `distributor`가 21자인 문자열로 요청한다.
- **Then** HTTP 400이며 `PurchaseOrder`가 생성되지 않는다.
- **판별 mutation**: 길이 검증이 없는 구현(ConfirmOrderView 선례를 그대로 복사) → `DataError`(strict 모드) 또는 잘린 값으로 조용히 저장(non-strict 모드) — 어느 쪽이든 "HTTP 400 + PO 미생성" 단정과 불일치.

### AC-LCONF-008 — unit_price 파싱 불가 → 400

- **Given** 자격을 갖춘 LineItem이 존재한다.
- **When** `{"distributor": "booxen", "unit_price": "abc"}`로 요청한다.
- **Then** HTTP 400이며 `PurchaseOrder`가 생성되지 않는다.

### AC-LCONF-009 — unit_price 생략 → null 저장

- **Given** 자격을 갖춘 LineItem이 존재한다.
- **When** `{"distributor": "booxen"}`(unit_price 키 없음)로 요청한다.
- **Then** HTTP 201이며 신규 `PurchaseOrder.unit_price is None`이다.

### AC-LCONF-010 — 존재하지 않는 pk → 404

- **Given** 존재하지 않는 LineItem pk(예: `999999`)를 사용한다.
- **When** `POST /api/purchase-orders/line-items/999999/confirm/`을 요청한다.
- **Then** HTTP 404이며 응답 바디는 `{"error": "Not found"}`이다(`{"detail": ...}` 아님 — `research.md` §1-7 컨벤션).

### AC-LCONF-011 — sku 없는 LineItem → 400

- **Given** `purchase_status="unordered"`, 미연결, `sku=None`인 LineItem이 존재한다(정상 UI에서는 도달 불가한 방어적 케이스).
- **When** `POST .../confirm/`을 요청한다.
- **Then** HTTP 400이며 `PurchaseOrder`가 생성되지 않는다.
- **판별 mutation**: sku 검증이 없는 구현 → `PurchaseOrder.sku`가 non-null 필드라 `IntegrityError`로 500이 되어 "400" 단정 실패(또는 테스트 자체가 예외로 크래시).

### AC-LCONF-012a — `FOR UPDATE` 락 결정론적 검증(정정, ND5 해소)

동시성 스레드 테스트는 SQLite(프로젝트 기본 테스트 DB 엔진, `backend/config/settings/local.py:11`)에서 `select_for_update()`가 무시되므로 락 누락을 판별하지 못할 수 있다 — `test_spec_016.py:1013-1027` `TestForceProcessLockingDeterministic.test_target_select_uses_for_update`의 결정론적 companion 패턴을 그대로 재사용한다.

- **Given** 자격을 갖춘 LineItem 1건이 존재한다.
- **When** `CaptureQueriesContext` 안에서 `POST .../confirm/`을 요청한다.
- **Then** 캡처된 SQL 중 대상 LineItem을 조회하는 쿼리(`orders_line_item` 테이블 대상)에 `FOR UPDATE`가 대소문자 무관하게 포함되어 있다.
- **판별 mutation**: `select_for_update()`를 제거한 구현 → 캡처된 SQL 어디에도 `FOR UPDATE`가 나타나지 않아 단정 실패. 실행 엔진(SQLite/MySQL)과 무관하게 항상 판별력을 갖는다 — 잠금이 실제로 유효한지 여부가 아니라 잠금을 **요청했는지**를 SQL 텍스트로 직접 확인하기 때문이다.

### AC-LCONF-012b — 동시 요청 2건 중 1건만 성공(스레드, `concurrency` 마커 명시, 정정, ND5 해소)

- **Given** 자격을 갖춘 LineItem 1건이 존재한다.
- **When** 동일 LineItem에 대해 거의 동시에 2개의 confirm 요청을 스레드로 보낸다(`test_spec_016.py:1030-1064` `TestForceProcessLockingConcurrent`의 `threading.Barrier(2)` 구조 재사용).
- **Then** 정확히 1건은 201, 나머지 1건은 409이며, `PurchaseOrder.objects.filter(line_items=li).count() == 1`이다.
- **테스트 마커(필수)**: `@pytest.mark.concurrency` + `@pytest.mark.django_db(transaction=True)`를 명시한다 — `backend/pytest.ini`의 markers 절이 이 마커를 "실제 스레드로 공유 리모트 DB에 접근하므로 다른 pytest 프로세스와 동시 실행 금지, `-m concurrency`로 선택 실행, `-m "not concurrency"`로 제외 실행"이라고 정의한다(프로젝트 메모리 `feedback_pytest_remote_db_concurrency`와 일치). 이 마커 없이 일반 스위트 실행에 섞이면 공유 리모트 DB에서 가짜 실패를 유발할 수 있다.
- **판별 mutation**: `select_for_update()`를 제거한 구현 → 두 요청이 모두 "미연결" 상태를 읽어 둘 다 201이 되고 `PurchaseOrder`가 2개 생성되어 count 단정 실패. (AC-012a가 "락을 요청하는지"를, 이 AC는 "락이 실제로 동시성을 막는지"를 검증한다 — 상호 보완적이며 어느 한쪽만으로는 불충분하다.)

### AC-LCONF-013 — Order 집계 재계산 호출 확인(스파이, 간접 검증 아님)

- **Given** 자격을 갖춘 LineItem이 존재하며, 그 `order_id`를 미리 기록해 둔다.
- **When** `order.purchase_order_views._recompute_order_aggregates`를 `unittest.mock.patch`로 스파이한 상태에서 `POST .../confirm/`을 요청한다.
- **Then** 스파이가 정확히 1회 호출되며, 인자는 `{line_item.order_id}`를 포함하는 집합/이터러블이다.
- **판별 mutation**: 재계산 호출을 빠뜨린 구현 → `assert_called_once()`가 실패.
- **주의(D6 해소)**: `Order.status`/`ready_to_ship` 값의 변화를 관찰하는 간접 검증은 이 AC의 대체 수단이 **아니다** — `_recompute_order_aggregates`는 `logistics_status` 기반 집계이고(`purchase_order_views.py:124-130`), 발주처리 쓰기는 `logistics_status`를 변경하지 않으므로 호출을 빠뜨려도 간접 관찰로는 값이 동일해 잡히지 않는다. `plan.md` M1도 이 스파이 방식으로 통일한다.

### AC-LCONF-014 — 미인증 요청 → 401 (정정, ND1 해소)

- **Given** JWT 토큰이 없는 익명 클라이언트(`anon_client` 픽스처, `test_purchase_orders.py:2300-2304` `test_patch_unauthenticated_returns_401` 선례 — `test_spec_018.py:86/:408`보다 같은 쓰기 URL 패밀리라 그레인이 더 맞다)와 자격을 갖춘 LineItem이 존재한다.
- **When** `anon_client`로 `POST /api/purchase-orders/line-items/<pk>/confirm/`을 요청한다.
- **Then** HTTP 401이며 `PurchaseOrder`가 생성되지 않는다.
- **판별 mutation(정정)**: `permission_classes`/`authentication_classes` 선언을 단순 제거하는 것은 이 AC를 깨뜨리지 **않는다** — `backend/config/settings/base.py:106-108`이 프로젝트 전역 기본값으로 `DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]`를 설정하므로(이 세션에서 직접 확인), 뷰가 명시적으로 선언하지 않아도 DRF가 그 기본값으로 폴백해 익명 요청은 여전히 401이다. **이 AC를 실제로 깨뜨리는 mutation은 `permission_classes = [AllowAny]`를 명시적으로 추가하는 것뿐이다.** (iteration 1 감사 원문이 "제거하면 401이 깨진다"고 서술했고 v1.1.0은 그것을 코드 대조 없이 그대로 옮겨 적은 결함이 있었다 — 이번에 `base.py`를 직접 읽어 정정했다.)

### AC-LCONF-014b — 뷰 수준 인증 클래스 선언 정적 확인(신규, ND1 해소)

AC-LCONF-014만으로는 "뷰가 인증 클래스 선언 자체를 빠뜨리는" 실수를 잡을 수 없다(프로젝트 기본값이 401로 폴백하므로 응답만으로는 구분 불가) — REQ-LCONF-001이 규정하는 "이 뷰가 인증을 요구한다"는 사실을 코드 리뷰가 아니라 테스트로 고정하기 위해 정적 검증을 추가한다.

- **Given** 없음(정적 검증, import만 필요).
- **When** `LineItemConfirmView.permission_classes`와 `LineItemConfirmView.authentication_classes`를 클래스 속성으로 직접 조회한다.
- **Then** `permission_classes`에 `IsAuthenticated`가 포함되어 있고, `authentication_classes`에 `JWTAuthentication`이 포함되어 있다.
- **판별 mutation**: 뷰가 `permission_classes`/`authentication_classes` 선언 자체를 빠뜨리는 구현 → AC-LCONF-014(401 응답)는 프로젝트 기본값 폴백으로 여전히 통과하지만, 이 AC는 클래스 속성 멤버십 검사가 실패한다(선언이 없으면 `APIView` 기본값 또는 `AttributeError`).

### AC-LCONF-015 — distributor 정확히 20자 → 성공(경계값, D7 해소)

- **Given** 자격을 갖춘 LineItem이 존재한다.
- **When** 정확히 20자인 `distributor` 문자열로 요청한다.
- **Then** HTTP 201이며 `PurchaseOrder`가 생성된다.
- **판별 mutation**: 길이 검사를 `len(dist) >= 20`으로 구현(20자를 초과가 아니라 이상으로 거부) → 이 AC가 400이 되어 실패. AC-LCONF-007(21자 거부)과 짝을 이뤄야 `> 20` vs `>= 20`의 경계 오류를 잡는다.

---

## R2 — 발주처리 모달 (프론트엔드)

### AC-LCONF-101 — 버튼 클릭 시 모달 오픈 + 정보 표시

- **Given** 미발주 품목 테이블에 도서명 "테스트도서", SKU "ISBN-A", 필요 수량 5인 행이 렌더링되어 있다.
- **When** 그 행의 발주처리 버튼을 클릭한다.
- **Then** 모달이 열리고 "테스트도서", "ISBN-A", "5"가 모달 안에 표시된다.

### AC-LCONF-102/103 — 드롭다운·자유텍스트 최종 조작값 우선(양방향 판별)

- **AC-LCONF-102 Given** 모달이 열려 있다. **When** 드롭다운에서 "교보"를 선택하고 그 외 아무것도 조작하지 않은 채 제출한다. **Then** `POST` 요청 바디의 `distributor`는 `"kyobo"`다.
- **AC-LCONF-103 Given** 모달이 열려 있다. **When** 드롭다운에서 "교보"를 선택한 뒤 자유 텍스트 필드를 "특수출판사"로 직접 수정하고 제출한다. **Then** `POST` 요청 바디의 `distributor`는 `"특수출판사"`다(드롭다운 값 `"kyobo"`가 아님).
- **판별 mutation**: "항상 드롭다운 값 우선" 구현 → AC-LCONF-103이 `"kyobo"`를 전송해 실패. "항상 자유텍스트 값 우선(빈 문자열 포함)" 구현 → AC-LCONF-102에서 드롭다운 선택이 자유 텍스트 필드에 반영되지 않는 구현이면 빈 문자열이 전송되어 실패. 두 AC를 함께 둬야 어느 한쪽 편향 구현도 잡아낸다.

### AC-LCONF-104 — 제출 성공 시 3개 쿼리 무효화 + 모달 닫힘

- **Given** 실제 `QueryClientProvider`로 감싼 상태에서 `invalidateQueries`를 spy한다(SPEC-ORDER-018 `usePurchaseOrderQueries.test.tsx` 선례).
- **When** 모달에서 제출해 서버가 201을 반환한다.
- **Then** `invalidateQueries`가 `QUERY_KEYS.unordered`, `QUERY_KEYS.excludedItems`, `['purchase-orders','list']` 3개 키 각각에 대해 최소 1회씩 호출되고, 모달이 닫히며, 성공 토스트가 표시된다.
- **판별 mutation**: 1~2개 키만 무효화하는 구현 → 누락된 키에 대한 `toHaveBeenCalledWith` 단정이 실패.

### AC-LCONF-105 — 제출 실패 시 무효화 없음 + 모달 유지

- **Given** 위와 동일한 spy 설정. 서버가 409와 `{"error": "이미 발주서에 연결되어 있습니다."}`를 반환하도록 목킹한다.
- **When** 모달에서 제출한다.
- **Then** `invalidateQueries`가 호출되지 않고, 모달이 열린 채로 남아 있으며, "이미 발주서에 연결되어 있습니다." 문구가 화면에 표시된다.
- **판별 mutation**: 성공/실패 무관하게 항상 무효화하는 구현 → `invalidateQueries`가 호출되어 "not.toHaveBeenCalled" 단정 실패.

### AC-LCONF-106 — distributor 공백 시 제출 버튼 비활성화

- **Given** 모달이 열려 있고 드롭다운은 기본값(빈 선택), 자유 텍스트도 빈 문자열이다.
- **When** 아무 값도 입력하지 않는다.
- **Then** 제출 버튼이 `disabled` 상태다.

### AC-LCONF-107 — 발주처리 버튼 클릭이 행 선택을 트리거하지 않음(REQ-LCONF-107, D7/ND4 해소)

- **Given** 미발주 품목 테이블의 한 행이 렌더링되어 있고, 그 행의 SKU는 현재 선택되지 않은 상태다.
- **When** 그 행의 발주처리 버튼을 클릭한다.
- **Then** 모달은 열리지만, 그 행의 체크박스(SKU 선택 상태)는 선택되지 않은 채로 남는다.
- **판별 mutation**: 버튼에 `stopPropagation`을 적용하지 않은 구현 → 클릭 이벤트가 행(`<tr onClick>`)까지 버블링되어 SKU가 함께 선택되므로, 체크박스 상태 단정이 실패.

### AC-LCONF-108 — damaged_exchange 행의 모달 초기 표시 수량(REQ-LCONF-108, D7/ND4 해소)

- **Given** `purchase_status="damaged_exchange"`, `quantity=10`, `damaged_quantity=3`인 LineItem이 미발주 목록 행에 순수량 `3`으로 표시되어 있다.
- **When** 그 행의 발주처리 버튼을 클릭해 모달을 연다.
- **Then** 모달에 표시되는 수량은 `3`이다(`10`이 아님) — REQ-LCONF-003이 서버에 실제로 기록하는 값과 담당자가 모달에서 보는 값이 일치해야 한다.
- **판별 mutation**: 모달이 LineItem의 원본 `quantity`를 그대로 표시하는 구현 → `10`이 표시되어 단정 실패.

---

## R3 — 자동 추천 발주처 제거

### AC-LCONF-201 — 응답에 auto_distributor 키 부재

- **Given** 미발주 후보 LineItem이 최소 1건 존재하고, 그 `vendor`가 `DistributorVendorRule`에 등록된 출판사명과 일치한다(규칙이 있어도 응답에 안 나오는지 확인하기 위한 대조 조건).
- **When** `GET /api/purchase-orders/unordered/`를 요청한다.
- **Then** 응답의 모든 `results[i]`에 대해 `"auto_distributor" not in results[i]`이다(값이 `null`인 것으로는 불충분 — 키 자체가 없어야 한다).
- **판별 mutation**: 키를 `None`으로만 바꾸고 남겨두는 구현("`"auto_distributor": None`") → `not in` 단정 실패.

### AC-LCONF-202 — rule_map 쿼리 자체가 사라짐

> **REQ-LCONF-202의 타입 절에 전용 AC가 없는 이유(v1.4.0 명시 — ND-I)**: REQ-LCONF-202는 두 절을 규정한다 — ① 프론트엔드 `UnorderedItem` 타입에서 `auto_distributor` 필드 제거, ② 미발주 품목 테이블에서 "자동 추천 발주처" 열 미렌더링. ②는 AC-LCONF-203이 직접 검증한다. ①은 별도 AC를 신설하지 않고 `tsc -b` 타입 체크 게이트(품질 게이트 표)에 의존한다 — 이것이 우연한 커버리지 공백이 아니라 의도적 판단인 이유: `purchaseOrderApi.ts:12`의 `auto_distributor: string | null`은 optional(`?`) 필드가 아니므로, 타입에서 이 필드를 제거하면 그 필드를 참조하는 모든 코드가 컴파일 타임에 깨진다. `plan.md`가 지시하는 `UnorderedItemsTab.test.tsx:170,328,356`의 `auto_distributor: null` 픽스처 3곳을 제거하지 않고 타입만 고치면 `tsc -b`가 그 3곳에서 실패하고, 반대로 타입은 그대로 두고 픽스처만 지우면 다른 필드 접근에서 타입 에러가 나지 않아 "제거됐는지" 자체를 판별할 수 없다 — 즉 타입 제거와 픽스처 제거는 서로를 강제하는 구조이며, `tsc -b`가 이미 그 강제를 판별력 있게 집행한다. 별도 런타임 AC를 추가하는 것은 이미 존재하는 컴파일 타임 보증을 중복 검증하는 것이라 이 SPEC은 추가하지 않는다.

- **Given** 위와 동일한 데이터.
- **When** `CaptureQueriesContext` 안에서 `GET /api/purchase-orders/unordered/`를 요청한다.
- **Then** 캡처된 SQL 목록 중 `DistributorVendorRule`의 테이블(`orders_distributorvendorrule`)을 대상으로 하는 쿼리가 0건이다.
- **판별 mutation**: 응답 직렬화 단계에서만 `auto_distributor` 키를 제거하고 `rule_map` 조회는 그대로 남긴 구현("응답은 맞지만 내부적으로 여전히 쿼리 발행") → 쿼리 목록에 해당 테이블이 나타나 단정 실패. 이 AC의 "쿼리 1개 감소"라는 정성적 주장을 정량적으로 고정하는 것이 아래 AC-LCONF-205다.

### AC-LCONF-203 — 프론트 테이블에 열 자체가 없음

- **Given** 미발주 품목 탭이 렌더링되어 있다.
- **When** 테이블 헤더를 조회한다.
- **Then** "자동 추천 발주처" 텍스트를 가진 `<th>`가 존재하지 않는다(`queryByText` 결과 `null`).
- **판별 mutation**: 헤더 텍스트만 다른 문자열로 바꾸고 열 자체는 유지하는 구현 → 이 AC와 별개로 아래 AC-LCONF-206(열 수 8 검증)에서 잡힌다.

### AC-LCONF-204 — 발주처 규칙 설정 탭·기존 auto_distributor 소비처 회귀 없음(D11 해소, ND3 정정)

- **Given** 다음 기존 테스트 스위트가 이 SPEC 구현 전에 전량 통과 상태다.
  - `frontend/src/pages/PurchaseOrders/tabs/VendorRulesTab.tsx`를 검증하는 프론트 테스트
  - `backend/order/tests/test_auto_dist.py`(`auto_select_distributor`/`resolve_publisher_distributor` 전용 스위트, 두 함수에 대한 참조 40건)
  - `backend/order/tests/test_spec_024.py`(타출판사 확정 발주처/단가 로직, `DistributorVendorRule` 관련 참조 **10건** — `:13,:30,:89,:108,:129,:162,:186,:210,:228,:246`, 이 세션에서 재실측)
  - `DistributorVendorRuleListCreateView`/`DistributorVendorRuleDeleteView`를 검증하는 백엔드 테스트
- **When** 이 SPEC 구현 후 위 스위트 전체를 재실행한다.
- **Then** 무수정 전량 통과한다(회귀 없음) — `UnorderedItemsView`에서 `rule_map`을 제거해도 `DistributorVendorRule` 모델·CRUD 뷰·Daily Review 소비 로직은 전혀 건드리지 않았음을 이 회귀로 증명한다.
- **판별 mutation**: `UnorderedItemsView.get()`을 수정하며 실수로 `DistributorVendorRule` import나 `excel_utils.py`의 `auto_select_distributor`/`resolve_publisher_distributor` 호출부까지 건드리는 구현 → 위 스위트 중 하나 이상이 실패한다.

### AC-LCONF-205 — GET /unordered/ 쿼리 수는 정확히 2(D1 해소)

- **Given** `backend/order/tests/test_spec_018.py:64`가 이 SPEC 이전 베이스라인으로 `UNORDERED_ENDPOINT_QUERY_COUNT = 3`(JWT 사용자 조회 1 + 뷰가 SPEC-ORDER-018 이전부터 발행하던 쿼리 2)을 고정하고 있다. REQ-LCONF-201이 그 2개 중 `rule_map` 쿼리 1개를 제거하므로, 이 SPEC 적용 후 신규 값은 **2**(JWT 사용자 조회 1 + 나머지 쿼리 1)다.
- **When** `CaptureQueriesContext` 안에서 인증된 클라이언트로 `GET /api/purchase-orders/unordered/`를 요청한다(JWT 웜업 후 측정, `test_spec_018.py:502-508` 패턴 재사용).
- **Then** 캡처된 쿼리 수는 정확히 2다.
- **판별 mutation**: `rule_map` 조회를 제거하지 않고 응답 직렬화에서만 키를 숨긴 구현 → 쿼리 수가 3으로 남아 단정 실패. 이 AC는 `test_spec_018.py:64,542-543`의 기존 핀을 `plan.md` M2가 3에서 2로 갱신하는 작업과 짝을 이룬다 — 두 파일(신규 AC-LCONF-205, 갱신된 `test_spec_018.py` 상수) 중 하나만 고치면 서로 모순되므로 반드시 함께 갱신한다.

### AC-LCONF-206 — 미발주 품목 테이블 열 수 8 불변(REQ-LCONF-204, D7/ND4 해소)

- **Given** 미발주 품목 탭이 렌더링되어 있다("자동 추천 발주처" 열 제거 + "발주처리" 열 추가 이후).
- **When** `<thead>`의 `<th>` 개수를 센다.
- **Then** 정확히 8개다 — 그리고 빈 상태 행(`data.results.length === 0`)의 `colSpan` 속성값도 `8`과 일치한다.
- **판별 mutation**: "자동 추천 발주처" 열만 제거하고 "발주처리" 열을 추가하지 않거나, 반대로 열은 추가했지만 실제로 열 수가 7 또는 9가 된 경우 → `<th>` 개수 단정이 실패한다.

---

## R4 — 보류/제외 품목에서 타출판사 숨김 + 수동 지정 통로 차단

### AC-LCONF-301 — other_publisher만 제거, 나머지 3개 상태는 유지(대조군 포함)

- **Given** `on_hold`, `order_cancelled`, `cs_required`, `other_publisher` 각 상태의 LineItem이 정확히 1건씩(총 4건) 존재한다.
- **When** `GET /api/purchase-orders/excluded-items/`를 요청한다.
- **Then** 응답 `results`는 정확히 3건이며, `on_hold`/`order_cancelled`/`cs_required` 3건은 모두 포함되고 `other_publisher` 1건만 없다.
- **판별 mutation**: `EXCLUDED_PURCHASE_STATUSES`를 빈 튜플로 바꾸는 "과잉 구현" → `results`가 0건이 되어 "3건 포함" 단정에서 실패(대조군 3개 상태 검증이 이 mutation을 잡아낸다 — other_publisher만 확인했다면 우연히 통과했을 것).

### AC-LCONF-302 — other_publisher는 대체 경로에서 조건부로 조회 가능(REQ-LCONF-303 정정에 맞춰 재작성, ND2 해소)

REQ-LCONF-303(v1.2.0 정정판)이 규정하는 것을 정확히 검증한다 — Daily Review 경로는 더 이상 "조회 가능한 경로"로 주장하지 않고, 대신 "그 경로에 나타나지 않는다"는 참 명제로 검증한다. 품목 노트 탭은 "노트가 있으면 보이고 없으면 안 보인다"는 조건부 사실을 대조군으로 직접 검증한다.

- **AC-LCONF-302a (주문상세, 무조건)** — **Given** `purchase_status="other_publisher"`인 LineItem이 속한 주문. **When** `GET /api/orders/<order_id>/`(`OrderDetailView`, `backend/order/views.py:39`)를 요청한다. **Then** 응답의 line_items 목록에 그 LineItem이 포함된다.
- **AC-LCONF-302b (품목 노트 타출판사 탭, 노트 있음/없음 대조군, 정정)**:
  - **Given-1(노트 있음)** `note_type="타출판사"`인 미해결 `LineItemNote`가 연결된 `other_publisher` LineItem `A`. **When** `GET /api/orders/line-item-notes/`(`LineItemNoteUnresolvedListView`, `backend/order/views.py:489-502`)를 요청한다. **Then** `A`에 연결된 노트가 응답에 포함된다.
  - **Given-2(노트 없음, 대조군 — 레거시 시나리오 재현)** 노트가 전혀 연결되지 않은 `other_publisher` LineItem `B`(REQ-LCONF-304~307 적용 이전에 `LineItemStatusUpdateView`로 수동 지정된 상태를 재현). **When** 동일 엔드포인트를 조회한다. **Then** `B`에 대응하는 노트는 응답에 없다(원천적으로 존재하지 않으므로) — 이 케이스는 "알려진 제약"(spec.md)이 실제로 재현됨을 문서화하는 목적이며, 이 자체가 결함 판정 기준은 아니다.
  - **판별 mutation**: `LineItemNoteUnresolvedListView`(`views.py:497-502`)가 `purchase_status`를 참조하는 배제 필터를 잘못 갖게 되는 구현 → Given-1(노트 있음) 케이스에서도 노트가 빠져 그 절이 실패한다.
- **AC-LCONF-302c (Daily Review 경로 — other_publisher를 읽지 않는다는 사실 검증, 사실에 맞게 교체, ND2 해소)** — **Given** `purchase_status="other_publisher"`인 LineItem 1건과, 대조군으로 `purchase_status="unordered"`(미연결)인 LineItem 1건이 함께 존재한다. **When** `GET /api/purchase-orders/daily-review-excel/`(`DailyReviewExcelView`)를 요청해 생성된 엑셀을 파싱한다. **Then** `other_publisher` LineItem은 결과에 **포함되지 않고**, 대조군 `unordered` LineItem은 포함된다.
- **판별 mutation(302c)**: `_reorder_candidate_filter`(`purchase_order_views.py:108-111`)를 넓혀 `other_publisher`도 admit하게 만드는 구현 → 그 LineItem이 엑셀에 나타나 "포함되지 않는다" 단정이 실패한다. 대조군(`unordered` 행이 포함됨)이 있어야 "필터가 아예 다 빼버린" 과잉 구현과 구별된다.

### AC-LCONF-303 — 상수 레벨 검증

- **Given** 없음(정적 검증).
- **When** `order.purchase_order_views.EXCLUDED_PURCHASE_STATUSES`를 임포트한다.
- **Then** 값은 정확히 `("on_hold", "order_cancelled", "cs_required")`이고 길이는 3이며 `"other_publisher"`를 포함하지 않는다.

### AC-LCONF-304 — PURCHASE_STATUS_OPTIONS에서 other_publisher 제거, 4개 렌더 사이트 전파(REQ-LCONF-304, 신규)

`frontend/src/services/purchaseOrderApi.test.ts:15-21`의 `damaged_exchange` 제외 검증 패턴을 그대로 재사용한다.

- **Given** `purchaseOrderApi.ts` 모듈을 import한다.
- **When** `PURCHASE_STATUS_OPTIONS`을 조회한다.
- **Then** `other_publisher` 값을 가진 옵션이 없다(`PURCHASE_STATUS_OPTIONS.map((o) => o.value)).not.toContain('other_publisher')`). 추가로 `UnorderedItemsTab.tsx`의 4개 렌더 사이트(미발주 품목 행별 select, 미발주 품목 일괄 상태 변경 select, 보류/제외 품목 행별 select, 보류/제외 품목 일괄 상태 변경 select) 각각에서 "타출판사" `<option>`이 렌더되지 않는다.
- **판별 mutation**: 소스 배열에서 제거하지 않고 4개 렌더 사이트 중 일부에서만 필터링하는 구현("`.filter(o => o.value !== 'other_publisher')`"을 특정 select에만 적용) → 나머지 렌더 사이트에 "타출판사" 옵션이 남아 단정 실패. 소스 배열 1곳만 고치면 4곳 전부에 자동 전파되므로, 이 mutation은 그 전파를 개별적으로 재구현하려다 일부를 빠뜨리는 실수를 잡는다.

### AC-LCONF-305 — PURCHASE_STATUS_LABELS는 other_publisher 유지(REQ-LCONF-305, 신규, 근거 v1.3.0 정정 — ND-B)

`purchaseOrderApi.test.ts`의 `damaged_exchange` 라벨 유지 검증(`:43-45`)과 동일 패턴.

- **Given** `purchaseOrderApi.ts` 모듈을 import한다.
- **When** `PURCHASE_STATUS_LABELS.other_publisher`를 조회한다.
- **Then** `'타출판사'`다.
- **판별 mutation**: `PURCHASE_STATUS_OPTIONS`에서 제거하며 실수로 `PURCHASE_STATUS_LABELS`에서도 함께 제거하는 구현 → `PURCHASE_STATUS_LABELS.other_publisher`가 `undefined`가 되어 단정 실패. **주의(ND-B 해소)**: v1.2.0판은 이 mutation의 실무 영향을 "보류/제외 뷰의 제외 사유 배지나 주문상세 화면에서 원시 문자열로 표시된다"고 서술했으나, 전자는 REQ-LCONF-302가 그 표에서 `other_publisher` 행 자체를 제거해 정상 흐름에서 도달 불가능하고, 후자는 `OrderDetailPage.tsx`가 `purchase_status`를 렌더링하지 않아(`grep` 결과 0건) 애초에 성립하지 않는 근거였다 — `spec.md` REQ-LCONF-305가 이제 정정된 근거(damaged_exchange 패턴 일관성 + 방어적 조치)를 쓴다. 이 AC 자체의 판별력(라벨 존재 직접 단정)에는 영향 없다.

### AC-LCONF-306 — LineItemStatusUpdateView가 other_publisher를 400 거부(REQ-LCONF-306, 신규)

`damaged_exchange` 거부 테스트(`test_purchase_orders.py:2321-2335` `test_patch_damaged_exchange_rejected`)와 동일 패턴.

- **Given** 자격 있는 LineItem(`purchase_status="unordered"`)이 존재한다.
- **When** `PATCH /api/purchase-orders/line-items/<pk>/status/` `{"purchase_status": "other_publisher"}`를 요청한다.
- **Then** HTTP 400이며, LineItem을 다시 조회하면 `purchase_status`는 여전히 `"unordered"`다(변경되지 않음).
- **판별 mutation**: `other_publisher` 거부 분기가 없는 구현 → 200이 되고 `purchase_status`가 `"other_publisher"`로 실제 변경되어 두 단정 모두 실패.

### AC-LCONF-307 — LineItemBulkStatusUpdateView가 other_publisher를 400 거부(REQ-LCONF-307, 신규)

- **Given** 자격 있는 LineItem 2건(`purchase_status="unordered"`)이 존재한다.
- **When** `PATCH /api/purchase-orders/line-items/bulk-status/` `{"ids": [id1, id2], "purchase_status": "other_publisher"}`를 요청한다.
- **Then** HTTP 400이며, 두 LineItem 모두 `purchase_status`가 여전히 `"unordered"`다(부분 반영 없음 — `damaged_exchange` 거부가 `existing.update()` 호출 이전에 조기 반환하는 것과 동일한 구조).
- **판별 mutation**: 거부 분기가 없는 구현 → 200과 `updated_count=2`가 되고 두 LineItem 모두 `"other_publisher"`로 변경되어 실패.

### AC-LCONF-308 — Daily Review 타출판사 업로드는 메모 유무와 무관하게 항상 노트를 생성(REQ-LCONF-308/309, v1.3.0 재작성 — ND-A 해소)

> v1.2.0판은 `_make_daily_review_excel` 헬퍼가 메모 셀을 기본값 `""`(→ `_str_or_none`을 거쳐 `None`)로 채우는데도 "노트가 함께 생성된다"고 단정해, **무수정 코드에서도 실패하는 결함**이 있었다(plan-audit 3차 ND-A). REQ-LCONF-309 신설로 이제 이 단정이 실제로 참이 되므로, 그 참인 이유(메모 공란/비공란 각각의 처리)를 blank/filled 두 케이스로 나눠 직접 검증한다. 두 케이스 모두 REQ-LCONF-306/307의 400 게이트가 이 업로드 경로를 막지 않는다는 회귀도 함께 증명한다(그 경로는 PATCH 엔드포인트를 거치지 않으므로).

- **AC-LCONF-308a (메모 공란)** — **Given** '선택'="타출판사"이고 메모(또는 Status) 셀이 비어 있는 행을 포함한 Daily Review 업로드 파일(`_make_daily_review_excel`을 `"note"` 키 없이 호출 — 헬퍼 기본값이 정확히 이 상황을 재현한다). **When** `POST /api/purchase-orders/upload-daily-review/`로 업로드한다. **Then** HTTP 200/201이며, 해당 LineItem의 `purchase_status == "other_publisher"`이고, `LineItemNote(note_type="타출판사", assignee="CS")`가 정확히 1건 생성되며 그 `content == "타출판사 확정 처리 (Daily Review 업로드, 메모 없음)"`다(REQ-LCONF-309가 확정한 리터럴, `spec.md` 참조 — v1.3.0판은 이 문구가 규범 문서에 없는데도 "REQ-LCONF-309가 규정하는"이라고 잘못 참조했다, ND-G 정정).
- **AC-LCONF-308b (메모 있음)** — **Given** '선택'="타출판사"이고 메모(또는 Status) 셀에 임의의 비공백 문자열(예: `"아가페"`)이 있는 행(`_make_daily_review_excel`을 `"note": "아가페"`로 호출, 또는 `test_spec_024.py:96`의 `"status": "아가페"` 신규 템플릿 픽스처 패턴 재사용). **When** 동일 업로드. **Then** HTTP 200/201이며, `purchase_status == "other_publisher"`이고, `LineItemNote`의 `content == "아가페"`다(셀 값 그대로 — 기존 동작 무변경).
- **판별 mutation**: `note is not None` 가드를 그대로 둔(REQ-LCONF-309 미구현) 상태 → AC-308a에서 `LineItemNote.objects.filter(line_item=li, note_type="타출판사").count() == 0`이 되어 "정확히 1건" 단정 실패. `UploadDailyReviewView`가 (가상의) 리팩터링으로 `LineItemStatusUpdateView`/`LineItemBulkStatusUpdateView`를 경유하게 되는 구현 → REQ-LCONF-306/307의 400 게이트에 걸려 두 케이스 모두 HTTP 200/201 단정이 실패.

### AC-LCONF-308c — 다른 3개 CS 유형은 메모 공란 시 여전히 노트 미생성(대조군, REQ-LCONF-309 범위 한정 검증, v1.4.0 개명 — ND-H)

> v1.3.0판에서는 이 AC가 `AC-LCONF-309c`로 명명되어 308a/308b와의 연속성이 끊겨 있었다(309a/309b 없이 309c만 존재) — REQ-LCONF-309의 검증이 308a/308b/308c 3건에 걸쳐 있다는 사실을 번호만으로 알 수 있도록 `308c`로 개명했다.

REQ-LCONF-309는 `note_type == "타출판사"`로만 범위를 한정한다 — 이 AC는 그 한정이 실제로 지켜지는지, 즉 "메모가 비어 있으면 노트를 만들지 않는다"는 기존 동작이 주문취소/주문보류/CS필요 3개 유형에는 그대로 남아 있는지를 검증한다.

- **Given** '선택'="주문취소"이고 메모/Status 셀이 비어 있는 행을 포함한 Daily Review 업로드 파일.
- **When** `POST /api/purchase-orders/upload-daily-review/`로 업로드한다.
- **Then** HTTP 200/201이며 `purchase_status == "order_cancelled"`이지만, 대응하는 `LineItemNote`는 생성되지 않는다(0건 — v1.2.0 이전과 동일한 기존 동작).
- **판별 mutation**: REQ-LCONF-309 구현을 `note_type == "타출판사"` 조건 없이 모든 CS 유형에 적용하는 "과잉 구현" → `order_cancelled` 행에도 기본 안내 문구 노트가 생성되어 "0건" 단정 실패. 이 AC가 없으면 REQ-LCONF-309의 범위 한정 문구("다른 3개 CS 유형은 변경하지 않는다")가 코드 리뷰에만 의존하게 된다.

---

## Edge Cases

이전 초안의 번호 없는 Edge Case 4건은 전부 정식 AC로 승격되었다(D7 해소): 20자 경계값(AC-LCONF-015), stopPropagation(AC-LCONF-107), damaged_exchange 모달 초기 표시 수량(AC-LCONF-108), 열 수 8 불변(AC-LCONF-206). v1.2.0에서 신규로 추가된 Edge Case는 다음과 같다.

- **레거시 other_publisher 행의 조회 가능 범위**: AC-LCONF-302b의 Given-2가 이 케이스를 직접 재현한다 — 별도 Edge Case 항목이 아니라 정식 AC의 일부로 이미 다뤄진다.
- **PATCH 엔드포인트의 `other_publisher` 거부가 damaged_exchange 거부와 동시에 요청되는 경우는 없음**: 한 요청의 `purchase_status`는 단일 값이므로 두 거부 분기가 동시에 트리거되는 경우는 구조적으로 불가능하다 — 별도 AC 불필요.

---

## 품질 게이트

| 항목 | 기준 | 검증 방법 |
|------|------|-----------|
| 백엔드 신규 테스트(동시성 제외) | `test_spec_025.py`의 AC-LCONF-001~011/012a/013~015/014b 전량 통과(004는 a~e 5개 케이스) | `pytest backend/order/tests/test_spec_025.py -m "not concurrency" --no-cov` |
| 백엔드 신규 테스트(동시성) | AC-LCONF-012b 전용, 공유 리모트 DB 특성상 단독 실행 | `pytest backend/order/tests/test_spec_025.py -m concurrency --no-cov`(다른 pytest 프로세스와 동시 실행 금지) |
| 백엔드 회귀 — SPEC-ORDER-018 | `test_spec_018.py` 갱신(`:57`의 튜플 3개로 축소, `:320`/`:516`의 `% 4` 모듈러 인덱싱을 `% len(EXCLUDED_STATUSES)`로 수정, `:64`의 `UNORDERED_ENDPOINT_QUERY_COUNT`를 `3`→`2`로 갱신, `:542-543`/`:550` 단정 갱신) 후 전량 통과 | `pytest backend/order/tests/test_spec_018.py --no-cov` |
| 백엔드 회귀 — auto_distributor 소비처 | `test_purchase_orders.py`의 `test_auto_distributor_from_vendor_rule`(`:300-313`)/`test_auto_distributor_null_when_no_rule`(`:315-325`) 2건을 REQ-LCONF-201에 맞게 제거 또는 재작성, `test_patch_all_six_choices`(`:2306-2319`)를 5개 선택값(`other_publisher` 제외) + `test_patch_other_publisher_rejected` 신설로 재작성(`damaged_exchange` 거부 테스트 선례와 동일 패턴) | `pytest backend/order/tests/test_purchase_orders.py --no-cov` |
| 백엔드 회귀 — Daily Review 업로드 | `test_spec_024.py`/`test_daily_review_upload.py`는 이 세션에서 재확인한 결과 무수정으로 통과한다(`test_spec_024.py`의 모든 타출판사 픽스처가 Status 셀에 비공백 값을 명시하고, 노트 존재를 단정하는 테스트도 없다 — REQ-LCONF-309의 blank-memo 분기를 실제로 실행하는 기존 테스트는 없음). AC-LCONF-308a/308b/308c는 신규 테스트로 추가한다 | `pytest backend/order/tests/test_spec_024.py backend/order/tests/test_daily_review_upload.py --no-cov` |
| 백엔드 회귀 — 전체 | 전체 스위트 무손실(원격 DB 동시 실행 금지 — 프로젝트 확정 규칙) | `pytest backend/order -m "not concurrency" --no-cov` |
| 프론트엔드 신규/수정 테스트 | `UnorderedItemsTab.test.tsx`, `LineItemConfirmModal.test.tsx`, `purchaseOrderApi.test.ts`(`:23-35`의 기존 "6개 옵션 유지" 단정을 5개로 반전 + AC-304/305 신규 케이스) 전량 통과 | `npm test` (frontend) |
| 타입 체크 | `tsc -b` 클린 | CI/로컬 |
| Mutation 실측 | AC-LCONF-001/003/004(a~e)/007/011/012a/012b/014/014b/015/102-103/104-105/201/202/205/206/301/302(a~c)/304/305/306/307/308(a~c)의 판별 mutation을 실제로 코드에 주입해 각 AC가 실패함을 이 세션에서 직접 확인 | manager-tdd/ddd 구현 세션 |
| Exclusions 침범 없음 | `WarehouseStock`/`ConfirmOrderView`/`LineItem.PURCHASE_STATUS_CHOICES`(모델 필드) 무변경, `UploadDailyReviewView`는 REQ-LCONF-309가 규정하는 좁은 예외(타출판사 분기의 노트 생성 조건) 외 무변경(diff로 확인) | `git diff` 검토 |

## Definition of Done

1. `spec.md`의 REQ-LCONF-001~015(R1), 101~108(R2), 201~204(R3), 301~309(R4) 전항이 대응하는 AC를 통과한다.
2. 위 품질 게이트 표의 전 항목이 충족된다.
3. `EXCLUDED_PURCHASE_STATUSES`가 3개 값으로 축소되고, `UnorderedItemsView` 응답에 `auto_distributor`가 없으며, `PURCHASE_STATUS_OPTIONS`에 `other_publisher`가 없고(`PURCHASE_STATUS_LABELS`에는 유지), 신규 `LineItemConfirmView`가 배포 가능한 상태다.
4. `plan.md`의 mx_plan에 따라 신규 `@MX:NOTE` 1개만 추가되고, 기존 ANCHOR/WARN 태그는 무수정이다.
5. `spec.md` HISTORY에 구현 결과(테스트 통과 수, 계획 대비 발산 유무)가 기록된다.
6. `spec.md`의 "알려진 제약" 절이 유지된다(구현이 그 제약을 우연히 해소하더라도 HISTORY에 그 사실을 기록하고 절을 갱신 — 임의 삭제 금지).
