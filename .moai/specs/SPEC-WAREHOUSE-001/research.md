# SPEC-WAREHOUSE-001 Research Notes

## 피벗 API 응답 vs 플랫(Flat) 행 방식 결정

---

### 배경

`WarehouseStock` 모델은 `(isbn, location)` 복합 유니크 키 기반의 정규화 테이블이다. API 응답 설계 시 두 가지 방식을 검토하였다.

---

### 방식 A — 플랫 행 (Flat Rows)

각 `(isbn, location)` 조합을 독립 행으로 반환.

```json
[
  { "id": 1, "isbn": "9788901234567", "location": "korea", "quantity": 10 },
  { "id": 2, "isbn": "9788901234567", "location": "ca",    "quantity": 5  },
  { "id": 7, "isbn": "9788901234568", "location": "nj",    "quantity": 3  }
]
```

**장점**
- 백엔드 구현이 단순하다 (DRF ModelSerializer + ListAPIView).
- 모델 구조와 1:1 대응하여 직관적이다.

**단점**
- 프론트엔드가 ISBN별로 그룹핑·피벗 로직을 직접 구현해야 한다.
- 동일 ISBN의 3개 위치를 테이블 1행으로 렌더링하기 위해 클라이언트 사이드 집계 코드가 필요하다.
- 삭제 시 특정 위치 행의 PK를 찾으려면 추가 필터 로직이 필요하다.

---

### 방식 B — 피벗 응답 (Pivoted Response) ← 채택

ISBN을 기준으로 서버에서 집계하여, 행당 3개 위치의 수량과 PK를 함께 반환.

```json
[
  {
    "isbn": "9788901234567",
    "korea_qty": 10, "korea_id": 1,
    "ca_qty": 5,     "ca_id": 2,
    "nj_qty": null,  "nj_id": null
  }
]
```

**장점**
- 프론트엔드는 응답을 그대로 테이블에 매핑하면 된다. 클라이언트 집계 코드 불필요.
- 삭제 시 각 셀의 `*_id`를 직접 DELETE 엔드포인트에 전달하여 단순하다.
- ISBN 검색 필터도 서버에서 처리되어 클라이언트 부담이 없다.
- UI 테이블 구조(ISBN | 한국 | CA | NJ)와 API 응답 구조가 동형(isomorphic)이다.

**단점**
- 백엔드에서 Python 딕셔너리를 활용한 피벗 집계 로직을 별도 구현해야 한다.
- 위치 종류가 변경되면 API 응답 스키마도 변경된다 (단, 이 SPEC에서는 위치를 고정값으로 취급하므로 문제 없음).

---

### 결정 근거

위치(korea, ca, nj)가 고정 3종이고, UI 테이블이 정확히 "ISBN 1행 + 위치 3열" 구조를 요구하는 상황에서 **피벗 응답 방식(B)**이 적합하다.

프론트엔드의 데이터 변환 복잡도를 제거하고, 삭제 인터랙션(`*_id`로 직접 DELETE)을 단순화하는 효과가 백엔드 집계 구현 비용을 상회한다.

위치가 동적으로 추가되는 요구사항이 발생한다면 플랫 행 방식으로 전환하고 프론트엔드 집계 로직을 도입하는 것이 타당하다. 그러나 현재 SPEC은 위치를 코드에 고정(hardcoded)하므로 방식 B를 채택한다.

---

### 구현 참고

백엔드 피벗 로직 핵심 패턴 (의사코드):

```python
# isbn별로 그룹핑
pivot = {}
for stock in WarehouseStock.objects.filter(isbn__icontains=isbn_filter):
    row = pivot.setdefault(stock.isbn, {
        "isbn": stock.isbn,
        "korea_qty": None, "korea_id": None,
        "ca_qty": None,    "ca_id": None,
        "nj_qty": None,    "nj_id": None,
    })
    row[f"{stock.location}_qty"] = stock.quantity
    row[f"{stock.location}_id"] = stock.pk
return list(pivot.values())
```

이 패턴은 단일 쿼리로 처리 가능하므로 N+1 문제가 발생하지 않는다.
