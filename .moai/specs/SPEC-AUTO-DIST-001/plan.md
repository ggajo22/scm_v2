# SPEC-AUTO-DIST-001 구현 계획

## 마일스톤 (우선순위 기반)

### M1 (Priority High): 사전 확인 — 북센 파일 샘플 분석
- 실제 북센 `.xls` 파일에서 "가격비교" 컬럼의 인덱스 확인
- `_BOOKSEEN_COL_PRICE_COMPARISON` 상수 값 결정
- REQ-AD-009의 TBD 해소 없이는 M3 이후 진행 불가

### M2 (Priority High): VendorComparison 모델 확장 + Migration
- REQ-AD-010 구현
- `VendorComparison`에 4개 필드 추가 (`bookseen_price_comparison`, `candidate_basis`, `price_diff`, `price_diff_alert`)
- `selected_distributor` choices 확장
- `python manage.py makemigrations order` 실행 및 migration 파일 생성

### M3 (Priority High): auto_select_distributor() 전면 교체
- 현재 stub 함수 삭제
- 5단계 의사결정 트리 구현 (REQ-AD-001 ~ REQ-AD-006)
- 가격차이 계산 (REQ-AD-007)
- candidate_basis 레이블 반환 (REQ-AD-008)
- 반환 타입을 `dict`로 변경

### M4 (Priority High): 북센 파서 가격비교 컬럼 추가
- REQ-AD-009 구현 (M1 완료 후 진행)
- `_parse_bookseen_xls()`에 `bookseen_price_comparison` 파싱 추가
- "TRUE"/"FALSE" 문자열 및 불리언 값 모두 처리

### M5 (Priority High): UploadVendorFileView 연동 수정
- 업로드 후 `auto_select_distributor()` 호출 인터페이스 변경
- 신규 반환값 (`candidate_basis`, `price_diff`, `price_diff_alert`) `VendorComparison` 저장
- `WarehouseStock` 재고 조회 로직 추가 (REQ-AD-002)

### M6 (Priority High): VendorComparisonView 응답 확장
- REQ-AD-011 구현
- 신규 필드 8개를 comparison API 응답에 포함
- `bookseen_returnable` → `"가능"`/`"불가"` 변환
- `kyobo_returnable` → `"Y"`/`"N"` 변환

### M7 (Priority Medium): 단위 테스트 작성
- `auto_select_distributor()` 의사결정 트리 각 분기 커버
- REQ-AD-001 ~ REQ-AD-007 각 케이스 최소 1개 테스트
- 경계값(총 수량 = 재고 수량) 테스트

---

## 기술적 접근 방식

### 함수 시그니처 변경

현재:
```python
def auto_select_distributor(
    bookseen_available, bookseen_price, kyobo_available, kyobo_price
) -> str | None
```

변경 후 (두 가지 옵션 중 구현 시 결정):

**옵션 A — 파라미터 명시 방식** (testability 우수)
```python
def auto_select_distributor(
    *,
    kyobo_publisher: str | None,
    bookseen_stock: int | None,
    bookseen_price: Decimal | None,
    bookseen_returnable: bool | None,
    bookseen_status: str | None,
    bookseen_price_comparison: bool | None,
    kyobo_stock: int | None,
    kyobo_price: Decimal | None,
    kyobo_returnable: bool | None,
    kyobo_status: str | None,
    total_qty: int,
    korea_stock: int,
    ca_stock: int,
    nj_stock: int,
    vendor_rules: dict[str, str],  # publisher_name -> distributor (pre-fetched)
) -> dict:
```

**옵션 B — VendorComparison 객체 방식** (뷰 연동 간결)
```python
def auto_select_distributor(
    vc: VendorComparison,
    total_qty: int,
    warehouse: dict,       # {"korea": int, "ca": int, "nj": int}
    vendor_rules: dict,    # pre-fetched
) -> dict:
```

### 반환값 구조

```python
{
    "selected_distributor": str | None,   # "BOOXEN", "교보", "재고", "재고-서부확인", "확인필요", "agape", "choeumgoyuk"
    "candidate_basis": str | None,
    "price_diff": Decimal | None,
    "price_diff_alert": bool,
}
```

### DB 쿼리 최적화

UploadVendorFileView의 업로드 루프에서:
- `DistributorVendorRule` 전체를 루프 전 한 번에 pre-fetch (현재 이미 M6에서 패턴 존재)
- `WarehouseStock`은 해당 SKU별로 조회 (isbn=sku 필터)
- `LineItem` 미연결 수량은 `aggregate(Sum('quantity'))` 사용

### 리스크

| 리스크 | 대응 |
|--------|------|
| `_BOOKSEEN_COL_PRICE_COMPARISON` TBD | M1을 구현 착수 전 완료 (블로커) |
| `selected_distributor` choices 확장 시 기존 데이터 영향 | null/blank 허용이므로 기존 레코드 영향 없음; 새로운 choices는 추가만 |
| UploadVendorFileView 내 루프에서 추가 DB 쿼리 발생 | WarehouseStock/LineItem 조회는 SKU별 O(n) — 허용 범위 내 |
| 의사결정 트리 복잡도로 인한 if-branch >= 8 | `@MX:WARN` 추가 필요 |
