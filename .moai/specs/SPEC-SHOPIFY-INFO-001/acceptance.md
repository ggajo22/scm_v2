---
id: SPEC-SHOPIFY-INFO-001
document: acceptance
version: 1.0.0
---

# SPEC-SHOPIFY-INFO-001: Acceptance Criteria

---

## Scenario 1: 두 스토어 모두 등록된 도서 — 정상 응답

**Given** 특정 `inven_id`에 대해 `Shopify_product`(Booksen)와 `EtoileShopifyProduct`(Etoile) 레코드가 모두 존재하고,  
  Shopify Admin API가 정상 응답을 반환하는 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/`를 JWT 인증 헤더와 함께 호출하면

**Then**
- HTTP 200 반환
- `booksen.registered == true`
- `booksen.status` 가 `"active"`, `"draft"`, `"archived"` 중 하나
- `booksen.weight` 가 숫자 (null이 아님)
- `booksen.weight_unit` 이 `"g"`, `"kg"`, `"lb"`, `"oz"` 중 하나
- `booksen.error == null`
- `etoile.registered == true`
- `etoile.status`, `etoile.weight`, `etoile.weight_unit` 동일 조건 만족
- `etoile.error == null`

---

## Scenario 2: Booksen 미등록 도서

**Given** 특정 `inven_id`에 대해 `Shopify_product` 레코드가 없는 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환
- `booksen.registered == false`
- `booksen.status == null`
- `booksen.weight == null`
- `booksen.weight_unit == null`
- `booksen.error == null`
- Booksen Shopify API 미호출 (로그에 API 요청 없음)

---

## Scenario 3: Etoile 미등록 도서

**Given** `EtoileBookInven` 또는 `EtoileShopifyProduct` 레코드가 없는 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환
- `etoile.registered == false`
- 모든 etoile 필드 `null`
- Etoile Shopify API 미호출

---

## Scenario 4: Shopify API 네트워크 오류 (단일 스토어)

**Given** Booksen Shopify API 호출이 네트워크 오류 또는 5xx 응답을 반환하는 경우  
  (Etoile API는 정상)

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 200 반환 (전체 요청 실패가 아님)
- `booksen.error` 가 non-null 문자열 (오류 설명 포함)
- `booksen.status == null`, `booksen.weight == null`
- `etoile` 필드는 정상 데이터 반환

---

## Scenario 5: JWT 인증 없는 요청

**Given** Authorization 헤더가 없거나 유효하지 않은 토큰인 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시

**Then**
- HTTP 401 반환
- Shopify API 미호출

---

## Scenario 6: 존재하지 않는 inven_id

**Given** DB에 해당 `inven_id`가 없는 경우

**When** `GET /api/book/{inven_id}/shopify-live-info/` 호출 시 (JWT 유효)

**Then**
- HTTP 404 반환

---

## Scenario 7: 프론트엔드 — 정상 로딩 및 표시

**Given** 두 스토어 모두 등록되고 API가 정상 응답을 반환하는 도서의 상세 페이지

**When** 사용자가 도서 상세 페이지(`/book/{id}`)에 접근하면

**Then**
- "Shopify 연동 정보" 섹션이 페이지에 렌더링됨
- API 응답 대기 중 스켈레톤 로딩 UI 표시
- 응답 후:
  - Booksen 스토어 이름 배지 표시
  - Booksen 상태 배지 표시 (active → 녹색, draft → 황색, archived → 회색)
  - Booksen 무게 + 단위 표시 (e.g., `500 g`)
  - Etoile 동일하게 표시

---

## Scenario 8: 프론트엔드 — 스토어 미등록

**Given** Booksen에 미등록된 도서의 상세 페이지

**When** 사용자가 해당 도서 상세 페이지에 접근하면

**Then**
- Booksen 항목에 "미등록" 표시
- 상태 배지 회색 렌더링
- 무게 필드 표시 없음 또는 "-" 표시
- 페이지 다른 섹션은 정상 동작

---

## Scenario 9: 프론트엔드 — API 오류

**Given** Shopify API 호출 시 네트워크 오류가 발생한 경우

**When** 사용자가 도서 상세 페이지에 접근하면

**Then**
- 해당 스토어 항목에 오류 메시지 표시
- 페이지 전체가 크래시되지 않음
- 나머지 섹션(기본 정보, 노트 등)은 정상 표시

---

## Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| `variant_id == "0"` (기본값) | weight API 호출 시 오류 반환, `weight == null`, `error` 필드 설명 |
| `product_id == "0"` (기본값) | status API 호출 시 오류 반환, `status == null`, `error` 필드 설명 |
| Shopify API 429 Too Many Requests | `error` 필드에 rate limit 메시지, `status/weight == null` |
| Shopify API 응답이 `status` 필드 누락 | `status == null` 반환, 예외 발생하지 않음 |
| `weight == 0` | 유효한 값으로 처리 (`0 g` 표시) |
| 두 API 중 하나만 타임아웃 | 타임아웃된 API 결과는 error 반환, 다른 API 결과는 정상 반환 |

---

## Definition of Done

- [ ] `GET /api/book/{inven_id}/shopify-live-info/` 엔드포인트 구현 완료
- [ ] REQ-SHPINFO-001 ~ REQ-SHPINFO-014 모든 요구사항 코드에서 동작 확인
- [ ] JWT 인증 적용 확인 (401 반환 테스트)
- [ ] 스토어 미등록 케이스: `registered: false` + null 필드 반환 확인
- [ ] Shopify API 오류 시 전체 요청 실패 없이 `error` 필드 반환 확인
- [ ] Booksen, Etoile API 병렬 호출 구현 확인
- [ ] 프론트엔드 "Shopify 연동 정보" 섹션 렌더링 확인
- [ ] 상태 배지 색상 (active=녹색, draft=황색, archived=회색) 시각 확인
- [ ] 로딩 중 스켈레톤 UI 확인
- [ ] 오류 시 섹션 내 오류 메시지 표시 확인 (페이지 크래시 없음)
- [ ] 환경 변수(`SHOPIFY_*`) 미설정 시 명확한 오류 처리 확인
- [ ] Shopify API 토큰이 응답 payload에 노출되지 않음 확인

---

## Quality Gate Criteria

- 백엔드: `ruff check` 통과, Django 기존 패턴(JWTAuthentication, APIView) 준수
- 프론트엔드: TypeScript 타입 오류 없음 (`tsc --noEmit`)
- API 응답 구조가 REQ-SHPINFO-008 스키마와 일치
- 오류 시나리오에서 HTTP 5xx 미반환 (내부 오류는 200 + `error` 필드로 처리)
