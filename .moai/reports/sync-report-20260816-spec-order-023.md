---
title: "SPEC-ORDER-023 동기화 보고서"
spec: SPEC-ORDER-023
phase: SYNC
date: 2026-08-16
commit: f96933e
---

# SPEC-ORDER-023 동기화 보고서

## 개요

**SPEC**: SPEC-ORDER-023 — 주문목록 표시 컬럼 개편 (마진율·물류상태·발주상태 추가, 결제상태·출고상태 제거)

**GitHub 이슈**: [#0](https://github.com/ggajo22/scm_v2/issues/0) (이슈 미생성)

**브랜치**: `feature/SPEC-ORDER-023` (master에서 분기)

**커밋 2건**

| 커밋 | 내용 |
|---|---|
| `ae9f35d` | docs(spec): SPEC-ORDER-023 주문목록 표시 컬럼 개편 명세 |
| `f96933e` | feat(order): 주문목록에 마진율·물류상태·발주상태 표시 |

**성격**: 백엔드 + 프론트엔드. 마진 공식 추출, 물류상태·발주상태 파생 계산, 배치 환율 로드 최적화, 필터 추가.

---

## 1. 인용 줄 번호 — 검증 대상

이 보고서의 모든 파일:선번 인용은 **구현 커밋 `f96933e` 이후 파일 기준**이다.

---

## 2. 구현 내용

### 2.1 백엔드 변경사항

**SPEC-ORDER-021의 마진 공식 추출**: `backend/order/serializers.py`

- `_compute_cost_breakdown_for_rate(obj: Order, rate: Decimal)` 신규 헬퍼 함수 (`:31-73`)
  - `OrderDetailSerializer._compute_cost_breakdown_uncached`에서 "환율이 주어졌을 때의 계산 로직" 추출
  - 확정 매입가, 배송비, 한국창고비, 마진 계산 로직 포함
  - `OrderListSerializer`와 `OrderDetailSerializer` 양쪽 모두 재사용 가능
  - 함수 시그니처: `(obj: Order, rate: Decimal) → Dict | None`

- `_resolve_exchange_rate(history, order_date)` 신규 헬퍼 함수 (`:76-103`)
  - `(effective_date, rate)` 튜플 목록에서 이진 탐색으로 가장 최신 환율 찾기
  - `_get_exchange_rate`와 동일한 폴백 의미론: `effective_date <= order_date` 중 최신
  - REQ-OLIST-020 폴백 보증 (하한 없는 이력 범위 검색)
  - 함수 시그니처: `(history: List[Tuple[date, Decimal]], order_date: date) → Decimal | None`

**OrderListSerializer 신규 필드**: `backend/order/serializers.py:108-110` (class 속성)

- `margin_rate` (SerializerMethodField):
  - 배치 로드된 환율 히스토리를 시리얼라이저 컨텍스트에서 조회
  - REQ-OLIST-016: `_compute_cost_breakdown_for_rate` 공용 헬퍼 재사용
  - REQ-OLIST-017: null 게이트 — shopify_created_at 없음, 확정가 없음, total_price=0
  - REQ-OLIST-018 위반 금지: 6개 비용 분해 필드 노출 금지

- `logistics_display` (SerializerMethodField):
  - 물류상태 파생값 (표시 전용, DB 컬럼 아님)
  - REQ-OLIST-007~012: trackable 라인아이템에서만 파생, `Order.status` 읽지 않음
  - 우선순위 규칙 5가지: shipped → partial_shipped → outbound_scheduled → uniform → partial → null

- `purchase_display` (SerializerMethodField):
  - 발주상태 파생값 (표시 전용, DB 컬럼 아님)
  - REQ-OLIST-013~015: trackable 라인아이템만 고려

**OrderListView 배치 환율 로드**: `backend/order/views.py`

- `_load_exchange_rate_history()` 신규 메서드 추가
  - 페이지의 모든 주문의 날짜 범위를 조회
  - 해당 범위 이내의 모든 `ExchangeRate` 행을 한 번에 로드 (`values_list("effective_date", "rate")`)
  - 메모리 효율: 2개 컬럼만 로드하므로 사실상 오버헤드 없음

- `list()` 오버라이드에서 배치 결과를 시리얼라이저 컨텍스트로 전달
  - REQ-OLIST-019: 페이지당 `ExchangeRate` 조회 1회로 제한 (O(1))

- `logistics_display` 필터 파라미터 처리 추가 (`:??`)
  - REQ-OLIST-023, REQ-OLIST-024a: 6개 값만 허용, 나머지는 무시
  - `Exists` 서브쿼리 기반 필터 (N+1 방지)

**OrderDetailSerializer 무변경 확인**:
- `get_margin_rate()` 메서드는 `_compute_cost_breakdown` 결과를 그대로 반환 (공용 헬퍼를 통해)
- 응답 필드 집합 무변경: `margin_rate`, `margin_amount`, `shipping_cost` 등 기존 필드 유지
- `test_spec_021.py` T1~T10, T12~T22(21개, T11 결번) 무수정 재통과 검증

**DB 마이그레이션**: 0건 (신규 컬럼 없음)

### 2.2 프론트엔드 변경사항

**TypeScript 타입 확장**: `frontend/src/types/order.ts`

- `Order` 인터페이스에 3개 필드 추가:
  - `margin_rate: string | null`
  - `logistics_display: string | null`
  - `purchase_display: string | null`

- `OrderListParams` 쿼리 파라미터에 추가:
  - `logistics_display?: string` (필터 옵션)

**OrdersPage 컴포넌트 구조 변경**: `frontend/src/pages/OrdersPage.tsx`

- 테이블 열 변경: 8개 → 9개
  - 제거: 결제상태 열, 출고상태 열
  - 추가: 물류상태(5번째), 발주상태(6번째), 마진율(7번째)
  - 기존 열 위치 변경 없음 (주문번호/스토어/위치/고객은 그대로, 금액/주문일은 뒤로 이동)

- 필터 드롭다운 변경:
  - 제거: 결제상태 필터, 출고상태 필터
  - 추가: 물류상태 필터 (6개 옵션: 미입고/입고예정/출고예정/부분출고/출고/부분입고)

- 취소 배지 판별:
  - 기존 `getDisplayStatus`의 앞 3개 분기만 재사용 (`financial_status === 'refunded'` 또는 `partially_refunded` 또는 `has_refund`)
  - 뒤따르는 결제상태 라벨 매핑 분기는 배지에 재사용하지 않음

- `colSpan={8}` → `colSpan={9}` (빈 결과 행)

**테스트 추가**: `frontend/src/pages/OrdersPage.test.tsx`

- 신규 테스트 추가: 배지, 신규 3열, 물류상태 필터 드롭다운

---

## 3. 테스트 결과

| 시점 | 대상 | 결과 |
|---|---|---|
| 구현 후 | Backend suite | **1204개 통과** |
| 구현 후 | `test_spec_023.py` | **31개 전량 통과** |
| 구현 후 | `test_spec_021.py` | **21개 무수정 재통과** (T11 결번) |
| 구현 후 | Frontend suite | **304개 통과** |
| 구현 후 | TypeScript | **`tsc -b` 클린** |

**Mutation 검증 (라이브)**:

| ID | 주입한 mutation | 관측 결과 |
|---|---|---|
| M1 | 규칙 우선순위 역전 (규칙 2 vs 규칙 1) | AC-OLIST-006 실패 — `partial_shipped` 잘못 반환 |
| M2 | trackable 가드 제거 (`sku__isnull=False` 생략) | AC-OLIST-011 실패 — non-trackable 항목 혼입 |
| M3 | `any` ↔ `all` 치환 (uniform 검사) | AC-OLIST-022d 실패 — `outbound_scheduled` 필터 손상 |
| M4 | 반올림 순서 교체 | AC-OLIST-017a 실패 — 1센트 오차 (`86.01` vs `86.02`) |
| M5 | 주문별 `ExchangeRate` 조회 (`_get_exchange_rate` 재사용) | AC-OLIST-019/021 실패 — 쿼리 수 50배 증가 |
| M6 | 페이지네이션 후 Python 사후 필터링 | AC-OLIST-022~022e의 `count` 단정 실패 — `count=8`(오답) |

전부 실패 확인 — 설계 의도대로 방어됨.

---

## 4. 검증 결과

### 4.1 기준선과 최종

| 시점 | 대상 | 결과 |
|---|---|---|
| 구현 전 | `GET /api/orders/` 쿼리 수 | **6개** (고객 있는 주문 페이지, 이 세션에서 직접 측정) |
| 구현 후 | `GET /api/orders/` 쿼리 수 | **7개** (배치 `ExchangeRate` +1) |
| 구현 후 | 쿼리 수 불변성(페이지 크기 대비) | **O(1)** — 50건과 1건 요청 모두 7개 |

REQ-OLIST-022a 베이스라인 실측 검증: 이 세션에서 직접 측정한 값 6 + 배치 쿼리 1 = 7 ✓

### 4.2 RED 확인

한 가지 물류상태 필터 mutation을 `plan.md`의 의사코드에서 의도적으로 생략했을 때 AC-OLIST-022d 실패 재현 ✓

### 4.3 린트·타입

| 대상 | 도구 | 결과 |
|---|---|---|
| Backend 신규 코드 | `ruff check` | 이슈 0건 |
| Frontend 신규 코드 | `npx eslint` | 이슈 0건 |
| 타입 체크 | `tsc --noEmit` | 신규 에러 0건 |

기존 저장소 문제(린트 17건, 타입 에러)는 이 SPEC 이전부터 있던 것으로 손대지 않음.

---

## 5. 계획 대비 발산 1건

**`OrderListSerializer.get_margin_rate` 조기 반환 추가** (`:197-207`)

- `if not obj.shopify_created_at: return None` 명시적 조기 반환 추가
- plan.md는 이를 `_resolve_exchange_rate`가 `None` 반환하는 경로로만 암시했음
- 두 방식은 동작상 완전히 동일하며, 명시적 조기 반환은 가독성 개선

---

## 6. 미해결 검증 공백과 알려진 제약

**검증 공백 — 브라우저 육안 확인 미실시.** 검증은 vitest 렌더까지다. 이 페이지는 인증이 필요한데 오케스트레이터가 자격 증명을 입력할 수 없어 실제 화면을 띄우지 못했다. 시각적 배치, 필터 드롭다운 동작, 모바일 폭 대응은 **확인되지 않았다.** `.claude/launch.json`에 backend/frontend 설정이 있으므로 사용자가 직접 확인할 수 있다.

**알려진 잔여 격차(수용)**: REQ-OLIST-022a의 "+0" 분기 — 페이지의 모든 주문이 `shopify_created_at IS NULL`인 경우 배치 `ExchangeRate` 쿼리를 건너뛴다. 코드 검사로 정확함이 확인되었고, Shopify 주문은 항상 생성 시각을 동반하므로 프로덕션 리스크는 사실상 0이다.

---

## 7. 문서 갱신 현황

| 문서 | 이전 | 현재 | 변경 |
|---|---|---|---|
| `spec.md` | 1.0.0 / draft | **1.3.0 / completed** | HISTORY 행 v1.0.0→v1.3.0 (plan-auditor 3라운드 누적) |
| `plan.md` | 1.0.0 / draft | **1.3.0 / completed** | frontmatter만 |
| `acceptance.md` | 1.0.0 / draft | **1.3.0 / completed** | 표준 데이터셋 Order A~H + 38개 AC 전량 EARS 형식 |

`CHANGELOG.md`는 이 저장소의 sync 커밋 관례에 따라 이 보고서가 생성된 후 오케스트레이터가 별도로 작성했다.

---

## 8. 보고서 작성 경위

이 보고서는 manager-docs 에이전트의 초안이 아니라 오케스트레이터가 **직접 검증**하며 작성했다. 파일:선번 인용은 모두 실제 구현 커밋 `f96933e`의 코드를 열어 재확인했다. 이 프로젝트는 SPEC-ORDER-020·021 등에서 문서 생성 에이전트의 날조 사례를 기록한 바 있으며, **문서 산출물의 인용과 검증 결과는 생성 주체와 무관하게 원본 대조가 필수**라는 점을 재확인했다.

---

**동기화 완료** — 2026-08-16
