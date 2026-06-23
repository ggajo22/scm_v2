# SPEC-PURCHASE-ORDER-001 인수 조건

## 인수 기준 개요

이 문서는 `SPEC-PURCHASE-ORDER-001`의 구현이 완료되었음을 검증하기 위한 Given-When-Then 시나리오와 품질 게이트를 정의한다.

---

## Given-When-Then 시나리오

### SC-PO-001: 미발주 LineItem 조회

**Given** 데이터베이스에 다음 상태가 존재한다:
- `LineItem` 레코드 10건이 존재하며, 그 중 6건은 `PurchaseOrder`와 연결되지 않음
- `DistributorVendorRule`에 publisher_name="처음교육", distributor="choeumgoyuk" 규칙이 등록됨

**When** 인증된 관리자가 `GET /api/purchase-orders/unordered/`를 요청한다

**Then**:
- HTTP 200 응답을 반환한다
- 응답의 `results`는 연결되지 않은 LineItem을 SKU 단위로 집계한 목록을 포함한다
- vendor가 "처음교육"인 SKU의 `auto_distributor`는 `"choeumgoyuk"`이다
- vendor가 규칙에 없는 SKU의 `auto_distributor`는 `null`이다
- 이미 PurchaseOrder에 연결된 LineItem은 목록에 포함되지 않는다

---

### SC-PO-002: 발주 파일 생성 — 정상 케이스

**Given** 미발주 LineItem에 SKU `"9788901234567"`, `"9788901234568"` 2건이 존재한다

**When** 관리자가 다음 요청을 보낸다:
```json
POST /api/purchase-orders/generate-order-file/
{
  "distributor": "bookseen",
  "skus": ["9788901234567", "9788901234568"]
}
```

**Then**:
- HTTP 200 응답을 반환한다
- Content-Type이 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`이다
- 응답 바이너리를 Excel로 열었을 때 헤더 행(ISBN, 도서명, 수량)이 존재한다
- 요청한 2개 SKU에 대응하는 데이터 행이 존재한다

---

### SC-PO-003: 발주 파일 생성 — 알 수 없는 SKU 포함

**Given** 미발주 LineItem에 SKU `"9788901234567"` 1건만 존재한다

**When** 관리자가 존재하지 않는 SKU `"9780000000000"`을 포함하여 요청한다:
```json
POST /api/purchase-orders/generate-order-file/
{
  "distributor": "kyobo",
  "skus": ["9788901234567", "9780000000000"]
}
```

**Then**:
- HTTP 200 응답을 반환한다
- 응답에 `"unknown_skus": ["9780000000000"]`이 포함된다
- 알 수 없는 SKU는 Excel 파일에 포함되지 않는다

---

### SC-PO-004: 업체 자료 업로드 — 북센 파일

**Given** 유효한 Excel 파일이 준비되어 있으며, SKU `"9788901234567"`에 대해 재고=true, 단가=12000 데이터가 포함된다

**When** 관리자가 다음 요청을 보낸다:
```
POST /api/purchase-orders/upload-vendor-file/
Content-Type: multipart/form-data
distributor=bookseen
file=<유효한 xlsx 파일>
```

**Then**:
- HTTP 200 응답을 반환한다
- `VendorComparison` 레코드가 `sku="9788901234567"`, `bookseen_available=True`, `bookseen_price=12000.00`으로 저장된다
- 응답의 `parsed_count`가 파일에서 파싱된 행 수와 일치한다
- 응답에 `comparisons` 배열이 포함되지 않는다 (데이터 저장만 수행)
- `VendorComparison.selected_distributor`는 이 시점에 갱신되지 않는다

---

### SC-PO-004a: run-comparison — 미발주 LineItem과 VendorComparison 매칭

**Given**:
- 미발주 LineItem: SKU `"9788901234567"`, 주문 #1001(수량 3), 주문 #1002(수량 2)
- `VendorComparison`: bookseen_price=12000, bookseen_stock=20, kyobo_price=11500, kyobo_stock=15

**When** 관리자가 `POST /api/purchase-orders/run-comparison/`을 호출한다

**Then**:
- HTTP 200 응답을 반환한다
- 응답 `results`에 `sku="9788901234567"`, `total_qty=5` 항목이 포함된다
- `line_items`에 `[{id: ..., order_name: "#1001", quantity: 3}, {id: ..., order_name: "#1002", quantity: 2}]`가 포함된다
- `selected_distributor`는 `"kyobo"` (교보 가격이 더 저렴)
- `VendorComparison` 레코드의 `selected_distributor`가 `"kyobo"`로 갱신된다

---

### SC-PO-005: 자동 발주처 선택 로직 — 재고 기준

**Given** `VendorComparison` 테이블에 다음 데이터가 존재한다:
- SKU `"A"`: bookseen_available=True, bookseen_price=10000, kyobo_available=False, kyobo_price=null
- SKU `"B"`: bookseen_available=False, bookseen_price=null, kyobo_available=True, kyobo_price=9500
- SKU `"C"`: bookseen_available=True, bookseen_price=11000, kyobo_available=True, kyobo_price=10500

각 SKU에 해당하는 미발주 LineItem이 존재한다

**When** 관리자가 `POST /api/purchase-orders/run-comparison/`을 요청한다

**Then**:
- SKU `"A"`의 `selected_distributor`는 `"bookseen"`이다 (유일하게 재고 있는 업체)
- SKU `"B"`의 `selected_distributor`는 `"kyobo"`이다 (유일하게 재고 있는 업체)
- SKU `"C"`의 `selected_distributor`는 `"kyobo"`이다 (양쪽 재고 있고 교보가 500원 더 저렴)

---

### SC-PO-006: 발주 확정 — 정상 케이스

**Given**:
- SKU `"9788901234567"`에 해당하는 미발주 `LineItem` 3건이 존재한다
- `VendorComparison`에 해당 SKU의 비교 데이터가 존재한다

**When** 관리자가 다음 요청을 보낸다:
```json
POST /api/purchase-orders/confirm/
{
  "items": [
    {
      "sku": "9788901234567",
      "distributor": "kyobo",
      "quantity": 3,
      "unit_price": "10500.00"
    }
  ]
}
```

**Then**:
- HTTP 201 응답을 반환한다
- `PurchaseOrder` 레코드 1건이 생성된다
- 생성된 `PurchaseOrder.status`는 `"pending"`이다
- `PurchaseOrder.line_items`에 해당 SKU의 미발주 LineItem 3건이 연결된다
- `GET /api/purchase-orders/unordered/` 재조회 시 해당 SKU가 목록에 나타나지 않는다

---

### SC-PO-007: 발주 확정 — 이중 발주 방지

**Given** SKU `"9788901234567"`의 LineItem이 이미 `PurchaseOrder`에 연결되어 있다

**When** 동일한 SKU에 대해 `POST /api/purchase-orders/confirm/`을 다시 요청한다

**Then**:
- HTTP 409 Conflict를 반환한다
- 새로운 `PurchaseOrder` 레코드가 생성되지 않는다

---

### SC-PO-008: 발주처 규칙 등록 및 중복 방지

**Given** `DistributorVendorRule`에 publisher_name="처음교육"이 이미 등록되어 있다

**When** 관리자가 동일한 publisher_name으로 POST 요청을 보낸다:
```json
POST /api/purchase-orders/vendor-rules/
{
  "publisher_name": "처음교육",
  "distributor": "agape"
}
```

**Then**:
- HTTP 409 Conflict를 반환한다
- 기존 규칙이 변경되지 않는다

---

### SC-PO-009: 발주처 규칙 삭제

**Given** `DistributorVendorRule`에 id=1, publisher_name="아가페출판사" 규칙이 존재한다

**When** 관리자가 `DELETE /api/purchase-orders/vendor-rules/1/`을 요청한다

**Then**:
- HTTP 204 No Content를 반환한다
- 해당 규칙이 DB에서 삭제된다
- 이후 `GET /api/purchase-orders/unordered/`에서 해당 출판사의 LineItem `auto_distributor`가 `null`로 반환된다

---

### SC-PO-010: 프론트엔드 — 미발주 현황 탭

**Given** 인증된 관리자가 `/purchase-orders` 페이지에 접속한다

**When** "미발주 현황" 탭이 활성화된다

**Then**:
- `GET /api/purchase-orders/unordered/` 호출이 발생한다
- 로딩 중 스켈레톤 또는 스피너가 표시된다
- 데이터 로드 완료 후 SKU별 집계 테이블이 표시된다
- 각 행에 체크박스가 표시된다
- 항목 선택 시 "북센 발주 파일 생성", "교보 발주 파일 생성" 버튼이 활성화된다

---

### SC-PO-011: 프론트엔드 — 발주 파일 다운로드

**Given** 미발주 현황 탭에서 SKU 2건이 체크박스로 선택되어 있다

**When** "북센 발주 파일 생성" 버튼을 클릭한다

**Then**:
- 버튼이 로딩 상태로 전환된다
- `POST /api/purchase-orders/generate-order-file/` 호출이 발생한다
- 성공 시 브라우저에서 Excel 파일 다운로드가 시작된다
- 버튼이 정상 상태로 복원된다

---

### SC-PO-012: 프론트엔드 — 업체 자료 업로드

**Given** 업체 자료 업로드 탭이 열려 있다

**When** 관리자가 "교보" 유통사를 선택하고 Excel 파일을 업로드한다

**Then**:
- `POST /api/purchase-orders/upload-vendor-file/`에 `distributor=kyobo`로 호출된다 (UI의 "교보"가 API 값 "kyobo"로 변환됨)
- 업로드 완료 후 파싱 건수(`parsed_count`)가 화면에 표시된다
- 비교 결과 테이블은 표시되지 않는다

---

### SC-PO-012a: 프론트엔드 — 비교 실행 및 미발주 매칭 결과 표시

**Given** 업체 자료 업로드 탭에서 북센/교보 파일이 모두 업로드된 상태이다

**When** 관리자가 "비교 실행" 버튼을 클릭한다

**Then**:
- `POST /api/purchase-orders/run-comparison/`이 호출된다
- 결과 테이블에 SKU별로 미발주 주문 목록(order_name × 수량), 북센/교보 재고·단가, 자동 선택 발주처, 선택 근거가 표시된다
- "발주 확정 탭으로 이동" 버튼이 표시된다

---

### SC-PO-013: 프론트엔드 — 발주 확정 후 상태 업데이트

**Given** 발주 확정 탭에 확정 대상 항목이 표시되어 있다

**When** "발주 확정" 버튼을 클릭한다

**Then**:
- `POST /api/purchase-orders/confirm/`이 호출된다
- 성공 시 토스트 메시지("발주가 확정되었습니다.")가 표시된다
- 미발주 현황 탭의 데이터가 자동으로 갱신된다 (TanStack Query 무효화)
- 발주 이력 탭에 새로운 레코드가 반영된다

---

### SC-PO-014: 비인증 접근 차단

**Given** 인증 토큰이 없는 사용자가 존재한다

**When** 해당 사용자가 `GET /api/purchase-orders/unordered/`를 요청한다

**Then**:
- HTTP 401 Unauthorized를 반환한다
- 응답 바디에 인증 오류 메시지가 포함된다

---

### SC-PO-015: 잘못된 파일 형식 업로드 거부

**Given** `.pdf` 또는 `.csv` 파일이 준비되어 있다

**When** 관리자가 해당 파일을 `POST /api/purchase-orders/upload-vendor-file/`에 업로드한다

**Then**:
- HTTP 400 Bad Request를 반환한다
- 응답에 "Excel 파일(.xlsx, .xls)만 업로드 가능합니다." 메시지가 포함된다

---

## 엣지 케이스

### EC-PO-001: SKU가 없는 발주 파일 생성 요청
- 입력: `{"distributor": "bookseen", "skus": []}`
- 기대: HTTP 400 Bad Request

### EC-PO-002: 미발주 LineItem 없을 때 unordered 조회
- 입력: 모든 LineItem이 PurchaseOrder에 연결된 상태
- 기대: HTTP 200, `results: []`, `count: 0`

### EC-PO-003: 북센 업로드만 된 상태에서 comparison 조회
- 입력: bookseen 데이터만 있고 kyobo 데이터는 없음
- 기대: HTTP 200, `kyobo_available: null`, `kyobo_price: null`로 반환; `selected_distributor: "bookseen"` (재고 있는 유일한 업체)

### EC-PO-004: vendor-rules에 없는 rule id 삭제
- 입력: `DELETE /api/purchase-orders/vendor-rules/99999/`
- 기대: HTTP 404 Not Found

### EC-PO-005: 발주 파일 생성 시 distributor 값 오류
- 입력: `{"distributor": "unknown_vendor", "skus": ["A"]}`
- 기대: HTTP 400 Bad Request, 유효하지 않은 distributor 오류 메시지

### EC-PO-006: Excel 필수 컬럼 누락 업로드
- 입력: ISBN 컬럼이 없는 Excel 파일 업로드
- 기대: HTTP 422 Unprocessable Entity, 누락된 컬럼명 오류 메시지

---

## 품질 게이트 기준 (Definition of Done)

### 백엔드

- [ ] 신규 3개 모델(`PurchaseOrder`, `VendorComparison`, `DistributorVendorRule`) Django 마이그레이션 정상 적용
- [ ] `PurchaseOrder ↔ LineItem` M2M 중간 테이블 생성 확인
- [ ] 모든 API 엔드포인트 JWT 인증 적용 확인
- [ ] `GET /api/purchase-orders/unordered/` — SKU별 집계 정상 동작
- [ ] `POST /api/purchase-orders/generate-order-file/` — Excel 다운로드 정상 동작
- [ ] `POST /api/purchase-orders/upload-vendor-file/` — Excel 파싱 및 VendorComparison 저장 정상 동작 (auto_select 호출 없음)
- [ ] `POST /api/purchase-orders/run-comparison/` — 미발주 LineItem 집계 → auto_select → 결과 반환 정상 동작
- [ ] 자동 발주처 선택 로직 (재고 우선, 단가 비교) 정확성 검증 — run-comparison 호출 시 동작
- [ ] `POST /api/purchase-orders/confirm/` — PurchaseOrder 생성 및 LineItem 연결 정상 동작
- [ ] 이중 발주 방지 (HTTP 409) 동작 확인
- [ ] `GET/POST /api/purchase-orders/vendor-rules/` — CRUD 정상 동작
- [ ] `DELETE /api/purchase-orders/vendor-rules/{id}/` — 삭제 정상 동작
- [ ] `GET /api/purchase-orders/` — 목록 조회 및 필터 정상 동작
- [ ] pytest 단위 테스트 작성 (핵심 비즈니스 로직 커버리지 80% 이상)
- [ ] ruff 린트 통과

### 프론트엔드

- [ ] `/purchase-orders` 경로 라우팅 정상 동작
- [ ] 사이드바에 "발주 관리" 메뉴 항목 표시
- [ ] 6개 탭 렌더링 및 전환 정상 동작
- [ ] 미발주 현황 테이블 데이터 표시 (로딩 상태 포함)
- [ ] 체크박스 선택 및 발주 파일 생성 버튼 활성화 동작
- [ ] Excel 파일 다운로드 정상 동작
- [ ] 업체 자료 파일 업로드 후 parsed_count 표시
- [ ] "비교 실행" 버튼 클릭 시 run-comparison 호출 및 미발주 LineItem 매칭 결과 테이블 표시
- [ ] 유통사 선택 UI 값(북센/교보)이 API 전송 시 bookseen/kyobo로 변환됨 확인
- [ ] 발주 확정 후 TanStack Query 캐시 무효화 및 UI 갱신
- [ ] 발주 이력 테이블 표시 및 필터 동작
- [ ] 발주처 규칙 추가/삭제 동작
- [ ] API 오류 시 토스트 또는 인라인 에러 메시지 표시
- [ ] JWT 미인증 시 로그인 페이지 리디렉션
- [ ] TypeScript 컴파일 오류 없음
- [ ] ESLint 통과

### 통합

- [ ] 발주 확정 흐름 엔드-투-엔드 동작: 미발주 조회 → 파일 생성 → 업로드 비교 → 확정 → 이력 확인
- [ ] 발주처 규칙 등록 후 미발주 현황에서 auto_distributor 자동 반영 확인
