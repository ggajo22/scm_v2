# SPEC-AUTO-DIST-001 인수 기준

## Given-When-Then 시나리오

### 시나리오 1: 아가페 출판사 — DistributorVendorRule 우선 적용

**Given** `DistributorVendorRule`에 `publisher_name="아가페출판사"`, `distributor="agape"` 룰이 존재하고
`kyobo_publisher = "아가페출판사"` 인 VendorComparison 레코드가 있다.

**When** `auto_select_distributor()`가 호출된다.

**Then** 반환값의 `selected_distributor = "agape"`, `candidate_basis = "아가페규칙"` 이어야 한다.
창고 재고 조회 및 벤더 가격 비교 로직이 실행되지 않아야 한다.

---

### 시나리오 2: 처음교육 출판사 — DistributorVendorRule 우선 적용

**Given** `kyobo_publisher = "처음교육"` 인 레코드가 있다.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "choeumgoyuk"`, `candidate_basis = "처음교육규칙"`.

---

### 시나리오 3: 한국 창고 재고 충분

**Given** 특정 SKU에 대해 미발주 LineItem 수량 합계(`total_qty`) = 5 이고,
`WarehouseStock(isbn=sku, location="korea").quantity = 10` 이다.
`kyobo_publisher`는 DistributorVendorRule에 해당 없음.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "재고"`, `candidate_basis = "재고우선"`.

---

### 시나리오 4: 한국 창고 부족, CA 창고 충분

**Given** `total_qty = 8`, `korea_stock = 3`, `ca_stock = 10`, `nj_stock = 0`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "재고-서부확인"`, `candidate_basis = "서부창고확인"`.

---

### 시나리오 5: 양사 재고 충분 + 북센 저가

**Given** 창고 재고 없음, `bookseen_stock = 10`, `kyobo_stock = 10` (total_qty = 5),
`bookseen_price = 15000`, `kyobo_price = 16000`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "BOOXEN"`, `candidate_basis = "양사재고/북센저가"`.

---

### 시나리오 6: 양사 재고 충분 + 교보 저가

**Given** 창고 재고 없음, `bookseen_stock = 10`, `kyobo_stock = 10` (total_qty = 5),
`bookseen_price = 17000`, `kyobo_price = 15000`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "교보"`, `candidate_basis = "양사재고/교보저가"`.

---

### 시나리오 7: 양사 재고 충분 + 동가 + 북센만 반품 가능

**Given** 동가(`bookseen_price = kyobo_price = 15000`), `bookseen_returnable = True`, `kyobo_returnable = False`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "BOOXEN"`, `candidate_basis = "양사재고/동가/북센반품"`.

---

### 시나리오 8: 북센 단독 재고

**Given** `bookseen_stock = 10`, `kyobo_stock = 2` (total_qty = 5).

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "BOOXEN"`, `candidate_basis = "북센재고우선"`.

---

### 시나리오 9: 양사 재고 없음 + 북센 정상 + 가격비교 True

**Given** `bookseen_stock = 1`, `kyobo_stock = 1` (total_qty = 5),
`bookseen_status = "정상"`, `bookseen_price_comparison = True`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "BOOXEN"`, `candidate_basis = "양사재고없음"`.

---

### 시나리오 10: 양사 재고 없음 + 북센 정상 + 가격비교 False + 교보 정상

**Given** `bookseen_status = "정상"`, `bookseen_price_comparison = False`, `kyobo_status = "정상"`.

**When** `auto_select_distributor()`가 호출된다.

**Then** `selected_distributor = "교보"`, `candidate_basis = "양사재고없음"`.

---

### 시나리오 11: 가격차이 알림 — 북센 선택 + 북센이 비쌈

**Given** `selected = "BOOXEN"`, `bookseen_price = 18000`, `kyobo_price = 14000`.
`abs(18000 - 14000) = 4000 >= 3000` AND `bookseen_price > kyobo_price`.

**When** 가격차이 알림 계산 (REQ-AD-007).

**Then** `price_diff = Decimal("4000")`, `price_diff_alert = True`.

---

### 시나리오 12: 가격차이 알림 없음 — 북센 선택 + 북센이 저렴

**Given** `selected = "BOOXEN"`, `bookseen_price = 13000`, `kyobo_price = 14000`.
`abs(price_diff) = 1000 < 3000`.

**When** 가격차이 알림 계산.

**Then** `price_diff_alert = False`.

---

### 시나리오 13: VendorComparison migration

**Given** Django migration이 실행된다 (`python manage.py migrate`).

**When** `orders_vendorcomparison` 테이블 스키마를 확인한다.

**Then** 컬럼 `bookseen_price_comparison`, `candidate_basis`, `price_diff`, `price_diff_alert`가 존재해야 한다.

---

### 시나리오 14: comparison API 응답 필드 확인

**Given** `VendorComparison` 레코드가 존재하고 `candidate_basis = "양사재고/북센저가"`, `price_diff_alert = False`.

**When** `GET /api/purchase-orders/comparison/`가 호출된다.

**Then** 응답 `results[]` 각 항목에 `candidate_basis`, `price_diff_alert`, `selected_distributor`,
`bookseen_arrival`, `bookseen_returnable`, `kyobo_status`, `kyobo_publisher`, `kyobo_returnable` 필드가 포함되어야 한다.

---

## 엣지 케이스

| 케이스 | 기대 결과 |
|--------|-----------|
| `total_qty = 0` (미발주 LineItem 없음) | 창고 재고 체크 시 0 대비 재고가 항상 충족 → "재고" 선택 (또는 구현 시 예외 처리) |
| `bookseen_stock = None`, `kyobo_stock = None` | None은 0으로 취급하여 양사 재고 없음 경로 진행 |
| `kyobo_publisher = None` | DistributorVendorRule 조회 건너뜀, Step 1 이후 진행 |
| WarehouseStock 레코드 없음 | 해당 location stock = 0으로 처리 |
| `bookseen_price_comparison = None` (TBD 컬럼 미파싱) | False로 취급 (2-D 로직에서 False 분기 진행) |
| `price_diff = None` (가격 하나 이상 None) | `price_diff_alert = False` |

---

## Definition of Done

- [ ] REQ-AD-001 ~ REQ-AD-011 시나리오 테스트 전체 통과
- [ ] `python manage.py migrate` 성공
- [ ] `GET /api/purchase-orders/comparison/` 응답에 신규 필드 포함 확인
- [ ] 기존 `auto_select_distributor()` 호출부 (`UploadVendorFileView`) 신규 인터페이스로 갱신
- [ ] `_BOOKSEEN_COL_PRICE_COMPARISON` TBD 해소 (파일 샘플 확인 완료)
- [ ] `ruff check backend/` 경고 없음
- [ ] `@MX:WARN` 태그 추가 (`auto_select_distributor` 함수 — 브랜치 복잡도 >= 8)
- [ ] 단위 테스트 커버리지 주요 분기 포함 (최소 시나리오 1 ~ 12 커버)
