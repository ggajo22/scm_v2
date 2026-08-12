---
id: SPEC-ORDER-017
document: spec-compact
version: 1.0.3
status: draft
updated: 2026-08-12
---

# SPEC-ORDER-017 압축 요약 — 렉번호 엑셀 업로드 배치 처리

전체 문서: `spec.md`(EARS 요구사항 전문), `plan.md`(구현 계획), `acceptance.md`
(Given/When/Then), `research.md`(코드베이스 조사 근거, file:line 인용 전량).

문제: `UploadRackNumberView`가 dedup-키 개수에 비례해 3쿼리/키를 실행 — 원격 MySQL 130ms
왕복 비용 때문에 업로드가 느리다. SPEC-ORDER-015의 `_process_outbound_rows`가 이미 해결한
배치 패턴(Order 조회 1 + LineItem 조회 1 + `bulk_update` 1)을 이식하되, 그 함수의 "2+ 매칭
거부" 규칙(결정 A)만은 이식하지 않는다 — 렉번호 엔드포인트는 SPEC-ORDER-013 결정 E에 따라
2+ 매칭 시 전부 갱신해야 한다.

**아키텍처(v1.0.2, 사용자 결정, 설계 결정 H)**: dedup·배치 조회·판정·`transaction.atomic()`·
`bulk_update`를 전부 소유하는 모듈 레벨 순수 함수 `_process_rack_number_rows(rows) -> dict`를
신설한다(`_process_outbound_rows`/`_process_force_outbound_rows`와 동일 아키텍처).
`UploadRackNumberView.post()`는 파일 검증 → 파싱 → 이 함수 호출 → 응답 포장만 하는 얇은
래퍼가 된다. 이 추출이 쿼리 카운트 AC를 함수 직접 호출로 측정 가능하게 만들어(HTTP·인증
쿼리 없음) plan-auditor D2/D7/D12의 근본 원인을 해소한다.

**v1.0.3**(iteration 3, PASS 0.88 후속, 문서 정리 6건): AC-011(a)를 "SET 절 참조"에서
"SET 절 대입"으로 좁혀 Django `bulk_update`의 `CASE WHEN "id"=...`를 오탐하지 않게 정정
(D17). AC-011/012를 함수 스코프로 spec.md와 acceptance.md 간 정렬(D18). REQ-001에 "빈
배치엔 쿼리 0건" 절 추가(D16). AC-012 근거 서술의 부정확한 "autocommit" 표현을 세이브포인트
설명으로 정정(D19). `@MX:WARN` 이관 위치 표현을 "함수 본문 안"으로 통일(D20(b)), AC-007
스코프 선언을 정렬(D20(a)). tie-break 참조 테스트 인용을 정정 — 참조 테스트는 `pk` 뒤집기를
실증하지 않는다(D21).

## REQ 목록 (요약)

**모듈 1 — 쿼리 배치 불변식**

- REQ-RACKBATCH-001 — 쿼리 수가 dedup-키 개수와 무관하게 고정(Order 1 + LineItem 1 +
  write 최대 1)
- REQ-RACKBATCH-002 — 2-키 배치와 10-키 배치의 쿼리 수가 **동일**(O(1)의 증명)

**모듈 2 — 매칭·중복 제거 시맨틱 보존**

- REQ-RACKBATCH-003 — 동일 키 중복 행은 **마지막 행** 값 적용
- REQ-RACKBATCH-004 — `Order.name` 정확 일치, 동명 충돌 시 **최저 `pk`**
- REQ-RACKBATCH-005 — 빈 주문 식별자 행은 병합 없이 개별 skipped 카운트

**모듈 3 — 반영 규칙 보존 (결정 E 승계, 결정 A 비승계)**

- REQ-RACKBATCH-006 — 키 하나에 매칭되는 LineItem이 **몇 건이든 전부** 갱신,
  `matched_count`는 키 단위 1회 (2+ 매칭 거부 **없음**)
- REQ-RACKBATCH-007 — 빈 문자열 rack_number는 명시적 "지움" 값으로 그대로 반영(falsy 필터
  금지)

**모듈 4 — 응답 계약·오류 처리·부수효과 보존**

- REQ-RACKBATCH-008 — 응답 스키마 `{matched_count, skipped_count}` 불변(추가 필드 없음)
- REQ-RACKBATCH-009 — 비-`.xlsx` → DB 접근 전 400
- REQ-RACKBATCH-010 — 파싱 실패(손상/빈 파일/헤더 누락) → 422, 무수정
- REQ-RACKBATCH-011 — 미인증 → 401
- REQ-RACKBATCH-012 — 주문 집계 재계산 루틴 절대 미호출
- REQ-RACKBATCH-015 (v1.0.1 신설) — 처리되지 않은 예외 → HTTP 500 + 부분 미반영. 번호
  보존을 위해 모듈 5 뒤에 배치되지만 모듈 4 소속(spec.md 설계 결정 G)

**모듈 5 — 원자성과 쓰기 범위**

- REQ-RACKBATCH-013 — 배치 전체 단일 원자적 트랜잭션, 중간 실패 시 부분 반영 없음
- REQ-RACKBATCH-014 — 쓰기는 `rack_number` 필드 하나뿐, 다른 LineItem/Order 필드 불변

## Acceptance Criteria (요약)

12개 인수 기준이 15개 요구사항 전량을 커버한다(REQ-013→AC-012, REQ-015→AC-009로 v1.0.2에서
분리 — v1.0.1까지는 두 REQ가 원자성을 증명하지 못하는 AC-009 하나를 공유했다, D12).

| AC | 요지 |
|---|---|
| AC-RACKBATCH-001 `[함수]` | 2-키 vs 10-키 쿼리 수 동일(1차 증거) + 절대 상한 `<= 6`/`<= 4`/`<= 2`(2차 증거, 렉번호 함수 자체 가드 구조에서 도출, D2/D2a/D2b/D2c) |
| AC-RACKBATCH-002 `[뷰]` | 결정 E — 한 키에 LineItem 2건 매칭 시 둘 다 갱신, matched_count=1 |
| AC-RACKBATCH-003 `[함수]` | 동명 Order 최저 `pk` 선점 |
| AC-RACKBATCH-004 `[뷰]` | 빈 문자열 rack_number → 명시적 clear 반영 |
| AC-RACKBATCH-005 `[뷰]` | 손상/빈/헤더누락 xlsx → 422, 무수정 |
| AC-RACKBATCH-006 `[뷰]` | 동일 키 중복 행 → 마지막 행 우선 |
| AC-RACKBATCH-007 `[뷰 또는 함수]` | 빈 주문 식별자 행 2건(**동일 SKU**) → 병합 없이 개별 skipped(D4-R — 서로 다른 SKU는 판별력이 없었다) |
| AC-RACKBATCH-008 `[뷰]` | 주문 집계 재계산 루틴 미호출 |
| AC-RACKBATCH-009 `[함수+뷰]` | 처리되지 않은 예외 → HTTP 500, 주입은 함수·관측은 뷰 (원자성은 증명하지 않음, D12) |
| AC-RACKBATCH-010 `[뷰]` | 응답 **키 집합**이 정확히 `{matched_count, skipped_count}`(신규 assertion, D13) + 400(비-xlsx) + 401(미인증) 회귀 없음 |
| AC-RACKBATCH-011 `[함수]` | 성공 호출의 SQL UPDATE가 `rack_number`만 **대입**(SET 절 좌변, D17로 "참조"에서 정밀화) + 필드 스냅샷 불변 |
| AC-RACKBATCH-012 (v1.0.2 신설) `[함수]` | `bulk_update` 실행 **후**, 트랜잭션 종료 전 고장 주입 → 예외가 호출자에게 전파 + 사후 조회로 롤백 확인(REQ-013 원자성 전용, D12) |

## 파일 변경 대상

| 구분 | 파일 |
|---|---|
| NEW (같은 파일 안 모듈 레벨 함수) | `backend/order/purchase_order_views.py` — `_process_rack_number_rows(rows) -> dict` |
| MODIFY | `backend/order/purchase_order_views.py` — `UploadRackNumberView.post()` (얇은 래퍼로 축소) |
| NEW | `backend/order/tests/test_spec_017.py` (함수 직접 호출 테스트 + 뷰 호출 테스트) |
| EXISTING (무수정, 회귀 확인만) | `backend/order/tests/test_spec_013.py` (15개 특성화 테스트) |
| EXISTING (변경 없음) | `backend/order/excel_utils.py`, `backend/order/models.py`, `frontend/src/**` 전체 |

## Exclusions (요약)

- 응답 스키마 변경 없음 (`unmatched` 상세 사유 이식 없음)
- `select_for_update()` 행 단위 락 도입 없음 (기존 수용된 격차, 악화 없음)
- 프론트엔드 변경 없음 (진행률 UI, axios timeout 설정 포함)
- 신규 DB 인덱스·마이그레이션 없음
- `parse_rack_number_excel` 변경 없음
- `ConfirmOrderView` 등 다른 엔드포인트 배치화 작업 없음
- `_process_rack_number_rows` 외 추가 계층·클래스 없음 (기존 아키텍처 관례를 따르는
  리팩터링일 뿐, 새 추상화 계층 도입이 아니다)

## 참조 구현

- 배치 패턴 + 아키텍처 원본: `backend/order/purchase_order_views.py:2423-2714`
  (`_process_outbound_rows`, SPEC-ORDER-015)
- 아키텍처 2차 선례: `backend/order/purchase_order_views.py:3021-`
  (`_process_force_outbound_rows`, SPEC-ORDER-016, 호출부 `:3220` 단 하나)
- 재사용 후보 헬퍼: `backend/order/purchase_order_views.py:2812-2829`
  (`_resolve_orders_by_name`, SPEC-ORDER-016)
- 이식하지 **않을** 지점: `backend/order/purchase_order_views.py:2582-2594` (2+ 매칭 거부,
  결정 A)
- 쿼리 가드 3종(상한 도출 전제, D2): `:2533`(`if grouped:`), `:2550`(`if orders_by_name:`),
  `:2701`(`if to_update:`)
- 삭제하지 않고 이관할 기존 태그(D8): `backend/order/purchase_order_views.py:2218-2226`
  (`@MX:WARN`/`@MX:REASON`, 결정 E 다중 매칭 경고 — 신설 함수 **본문 안** 판정 지점으로
  이관, D20(b))
- 예외 처리 경로(REQ-RACKBATCH-015 근거): `backend/order/purchase_order_views.py:2216-2261`
  (기존 `try/except Exception -> 500`, 재작성 없이 유지)
- 뷰 레벨 측정이 부정확했던 근거(D2): `:2177`(`JWTAuthentication`), `:47`(임포트),
  `test_spec_013.py:76-79`(`auth_client` 실제 JWT 발급)
- 쿼리 카운트 테스트 기법 원본(함수 직접 호출): `backend/order/tests/test_spec_015.py:1104-1121`
- 절대 상한 근거(D2c 정정 — `:1143-1153`이 아니라 개별 인용): `:1143-1147`(`<= 6`),
  `:1149-1153`(`<= 4`), `:1155-1157`(`<= 2`)
- 동명 Order tie-break 테스트 기법(부분 재사용): `backend/order/tests/test_spec_015.py:1166-1186`
  — 판정 로직(`name__in` + `order_by("pk")`)은 재사용 가능하나, 이 테스트는 `pk`를 생성
  순서와 어긋나게 만들지 않으므로(D21) "`pk` 뒤집기" 픽스처는 별도로 구현해야 한다
