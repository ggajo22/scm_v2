---
id: SPEC-AUTO-DIST-001
version: "1.0.0"
status: Planned
created: 2026-06-21
updated: 2026-06-21
author: ggajo
priority: High
issue_number: ~
---

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-06-21 | ggajo | 초안 작성 — 발주처 자동 선택 로직 고도화 |

---

## 개요

`auto_select_distributor()` 함수의 현재 구현은 단순 재고 유무와 가격 비교만 수행하는 스텁이다.
이 SPEC은 다음 5단계 의사결정 트리를 포함하는 완전한 비즈니스 로직으로 교체한다:

1. DistributorVendorRule 우선 적용 (아가페 / 처음교육)
2. 창고 재고 우선 선택
3. 양사 재고 충분 시 가격·반품 조건 비교
4. 단독 재고 기준 선택
5. 양사 재고 없음 시 상태·가격 우위 기반 선택

또한 가격차이 알림, 후보기준(candidate_basis) 레이블을 추가한다.

### 대상 파일

- `backend/order/excel_utils.py` — `auto_select_distributor()` 함수 교체
- `backend/order/models.py` — `VendorComparison` 신규 필드 4개 추가
- `backend/order/purchase_order_views.py` — comparison API 응답 필드 확장
- `backend/order/migrations/` — migration 파일 신규 생성

---

## 범위 (Scope)

**대상 시스템**: SCM v2 백엔드 (`backend/order/` 앱)

**비즈니스 목적**: 발주처 자동 선택의 정확도를 높여 수동 확인 작업을 최소화하고,
가격차이 알림 및 후보기준 레이블을 통해 담당자의 의사결정을 지원한다.

---

## 요구사항 (EARS 형식)

### REQ-AD-001: DistributorVendorRule 우선 적용

**When** `kyobo_publisher` 값이 `DistributorVendorRule` 테이블에 존재하고,
해당 룰의 `distributor`가 `agape`이면,
**the system shall** `selected_distributor = "agape"`, `candidate_basis = "아가페규칙"` 으로 설정하고 이후 모든 단계를 건너뛴다.

**When** `kyobo_publisher` 값이 정확히 `"처음교육"`과 일치하면,
**the system shall** `selected_distributor = "choeumgoyuk"`, `candidate_basis = "처음교육규칙"` 으로 설정하고 이후 모든 단계를 건너뛴다.

- 구현 참고: `DistributorVendorRule.objects.filter(publisher_name=kyobo_publisher)` 조회 결과가 없으면 다음 단계로 진행.
- 아가페 매칭은 substring 포함(`"아가페" in kyobo_publisher`)으로 처리.

---

### REQ-AD-002: 창고 재고 우선 선택

**The system shall** 해당 SKU에 대해 발주 미연결(PurchaseOrder 미연결) `LineItem` 수량의 합계를 `total_qty`로 산출한다.

**When** `WarehouseStock`에서 `isbn = sku`로 조회한 한국 창고 재고(`location="korea"`)가
`korea_stock >= total_qty`이면,
**the system shall** `selected_distributor = "재고"`, `candidate_basis = "재고우선"`으로 설정하고 벤더 비교 단계를 건너뛴다.

**When** 한국 재고로 부족하지만 (`korea_stock < total_qty`) CA 또는 NJ 창고 재고가
`ca_stock >= total_qty OR nj_stock >= total_qty`이면,
**the system shall** `selected_distributor = "재고-서부확인"`, `candidate_basis = "서부창고확인"`으로 설정하고 벤더 비교 단계를 건너뛴다.

**If** 어느 창고도 `total_qty`를 충족하지 못하면,
**then the system shall** 벤더 비교 단계(REQ-AD-003 ~ REQ-AD-006)로 진행한다.

---

### REQ-AD-003: 양사 재고 충분 시 가격·반품 기준 선택 (Step 2-A)

**When** `bookseen_stock >= total_qty AND kyobo_stock >= total_qty`이면 (양사 재고 충분),
**the system shall** 아래 우선순위 순서로 발주처를 선택한다:

1. `bookseen_price < kyobo_price` → `selected = "BOOXEN"`, `candidate_basis = "양사재고/북센저가"`
2. `kyobo_price < bookseen_price` → `selected = "교보"`, `candidate_basis = "양사재고/교보저가"`
3. 동가이며 `bookseen_returnable = True AND kyobo_returnable != True` → `selected = "BOOXEN"`, `candidate_basis = "양사재고/동가/북센반품"`
4. 동가이며 `kyobo_returnable = True AND bookseen_returnable != True` → `selected = "교보"`, `candidate_basis = "양사재고/동가/교보반품"`
5. 동가이며 반품 조건이 동일 → `selected = "BOOXEN"`, `candidate_basis = "양사재고/동가/반품동일"`
6. `bookseen_price is None` (교보 가격만 있음) → `candidate_basis = "양사재고/교보가격만확인"` (selected 미결정)
7. `kyobo_price is None` (북센 가격만 있음) → `candidate_basis = "양사재고/북센가격만확인"` (selected 미결정)
8. 양사 모두 가격 없음 → `selected = "BOOXEN"`, `candidate_basis = "양사재고/가격없음"`

---

### REQ-AD-004: 단독 재고 기준 선택 (Step 2-B / 2-C)

**When** `bookseen_stock >= total_qty AND kyobo_stock < total_qty`이면,
**the system shall** `selected = "BOOXEN"`, `candidate_basis = "북센재고우선"`.

**When** `kyobo_stock >= total_qty AND bookseen_stock < total_qty`이면,
**the system shall** `selected = "교보"`, `candidate_basis = "교보재고우선"`.

---

### REQ-AD-005: 양사 재고 없음 시 상태·가격 우위 기준 선택 (Step 2-D)

`bookseen_price_cheaper`는 실시간 계산값 (`bookseen_price <= kyobo_price`, 어느 쪽이라도 None이면 False).

**When** `bookseen_stock < total_qty AND kyobo_stock < total_qty`이면 (양사 재고 부족),
**the system shall** 아래 순서로 발주처를 결정한다:

1. `bookseen_status = "정상" AND bookseen_price_cheaper = True` → `selected = "BOOXEN"`, `candidate_basis = "양사재고없음"`
2. `bookseen_status = "정상" AND bookseen_price_cheaper = False`:
   - `kyobo_status = "정상"` → `selected = "교보"`, `candidate_basis = "양사재고없음"`
   - `kyobo_status != "정상"` → `selected = "확인필요"`, `candidate_basis = "양사재고없음"`
3. `bookseen_status != "정상" AND kyobo_status in ("정상", "주문판매")` → `selected = "교보"`, `candidate_basis = "양사재고없음"`
4. 위 조건 모두 미해당 → `selected = "확인필요"`, `candidate_basis = "양사재고없음"`

---

### REQ-AD-006: 반품 상태 오버라이드 (Step 2-E)

**When** Step 2-D 결과가 결정된 후,
`kyobo_returnable = True AND bookseen_returnable != True`이면,
**the system shall** 아래 오버라이드를 적용한다:

- `kyobo_status = "정상"` → `selected = "교보"` (candidate_basis는 2-D 결과 유지)
- `kyobo_status != "정상"` → `selected = "확인필요"`

---

### REQ-AD-007: 가격차이 알림 계산

**The system shall** `price_diff = bookseen_price - kyobo_price`를 계산한다 (어느 쪽이라도 None이면 None).

**When** `abs(price_diff) >= 3000` 이고 다음 중 하나에 해당하면,
**the system shall** `price_diff_alert = True`를 설정한다:

- `selected = "확인필요"`
- `selected = "BOOXEN" AND bookseen_price > kyobo_price`
- `selected = "교보" AND kyobo_price > bookseen_price`

**If** 위 조건에 해당하지 않으면,
**then the system shall** `price_diff_alert = False`를 설정한다.

---

### REQ-AD-008: 후보기준(candidate_basis) 레이블 생성

**The system shall** `auto_select_distributor()` 실행 결과에 `candidate_basis` 문자열을
항상 포함하여 반환한다 (REQ-AD-001 ~ REQ-AD-006의 각 케이스별 레이블 참조).

**The system shall** `candidate_basis`를 `VendorComparison.candidate_basis` 필드에 저장한다.

---

### REQ-AD-009: VendorComparison 모델 신규 필드 추가 및 migration

**The system shall** `VendorComparison` 모델에 아래 필드를 추가한다:

| 필드명 | 타입 | 속성 |
|--------|------|------|
| `candidate_basis` | `CharField(max_length=100)` | `null=True, blank=True` |
| `price_diff` | `DecimalField(max_digits=12, decimal_places=2)` | `null=True, blank=True` |
| `price_diff_alert` | `BooleanField` | `null=True, blank=True` |

**The system shall** `VendorComparison.selected_distributor` choices를 다음으로 확장한다:
`"BOOXEN"`, `"교보"`, `"재고"`, `"재고-서부확인"`, `"확인필요"`, `"agape"`, `"choeumgoyuk"`

**The system shall** Django migration 파일을 생성하여 `orders_vendorcomparison` 테이블에
신규 컬럼 3개를 추가한다.

---

### REQ-AD-010: API 응답에 신규 필드 포함

**When** `GET /api/purchase-orders/comparison/`이 호출되면,
**the system shall** 기존 필드에 더하여 다음 필드를 응답에 포함한다:

- `bookseen_returnable` — `"가능"` / `"불가"` 문자열 (None이면 null)
- `kyobo_returnable` — `"Y"` / `"N"` 문자열 (None이면 null)
- `kyobo_status` — 기존 저장값 그대로 반환
- `kyobo_publisher` — 기존 저장값 그대로 반환
- `bookseen_arrival` — 기존 저장값 그대로 반환
- `price_diff_alert` — Boolean
- `candidate_basis` — 문자열
- `selected_distributor` — 확장된 choices 중 하나

---

## 기술적 접근 방식

### auto_select_distributor() 함수 교체

현재 함수 시그니처:
```python
def auto_select_distributor(
    bookseen_available, bookseen_price, kyobo_available, kyobo_price
) -> str | None
```

신규 함수는 입력 파라미터를 `VendorComparison` 인스턴스(또는 동등한 데이터 객체)와
`total_qty: int`를 받는 방식으로 확장한다. 반환 타입은 `dict`로 변경한다:

```python
# 반환 예시
{
    "selected_distributor": "교보",
    "candidate_basis": "양사재고없음",
    "price_diff": Decimal("-1500"),
    "price_diff_alert": False,
}
```

DistributorVendorRule 조회는 함수 외부에서 pre-fetch하여 함수에 전달하거나,
함수 내부에서 단일 DB 쿼리로 처리할 수 있다 (구현 시 결정).

### Migration

`python manage.py makemigrations order` 실행 후 생성된 migration 파일을 커밋한다.
신규 컬럼 3개: `candidate_basis`, `price_diff`, `price_diff_alert`.

### UploadVendorFileView 수정

업로드 후 `auto_select_distributor()` 호출 시 신규 반환값(`candidate_basis`, `price_diff`, `price_diff_alert`)을
`VendorComparison`에 함께 저장한다.

---

## 의존성 (Dependencies)

| 의존 대상 | 유형 | 비고 |
|-----------|------|------|
| `SPEC-PURCHASE-ORDER-001` | 선행 SPEC | VendorComparison, WarehouseStock, DistributorVendorRule 모델 제공 |
| 북센/교보 업체 파일 업로드 | 외부 데이터 | 실제 업로드 후 bookseen_stock, kyobo_stock 등 필드 채워짐 |
| Django migration | 내부 | REQ-AD-010 신규 필드 반영 |

---

## 제외 사항 (Exclusions — What NOT to Build)

- **만화(comic) 예외 처리**: 이번 SPEC에서 제외. 별도 SPEC 또는 후속 이터레이션에서 결정.
- **프론트엔드 UI 변경**: 이번 SPEC에서 제외. 신규 API 필드가 확정된 후 별도 SPEC 또는 구현 중 결정.
- **기존 PurchaseOrder 레코드 소급 재계산**: 신규 로직은 업로드 시점부터 적용. 기존 데이터 batch 재처리 제외.
- **가격차이 임계값(3000원) 설정 UI**: 하드코딩 유지. 관리자 설정 기능 제외.
- **DistributorVendorRule CRUD**: 이미 구현된 M6 엔드포인트 변경 제외.
