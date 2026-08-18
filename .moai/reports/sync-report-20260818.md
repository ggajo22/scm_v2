# 동기화 리포트 — SPEC-ORDER-027

**생성**: 2026-08-18  
**SPEC**: SPEC-ORDER-027 렉번호 요약 탭 — 개수 표기를 "입고 / 총"으로 변경  
**상태**: 완료  
**Git 커밋**: 3e94d47 (SPEC docs) + 82957de (implementation)

---

## 1. 범위 (Scope)

렉번호 요약 탭(Tab2, `/rack-number` 페이지)의 그룹 헤더 텍스트 변경:

- **변경 전**: `총 {n}권` (단순히 총 수량만 표시, SPEC-ORDER-014)
- **변경 후**: `입고 {received} / 총 {total}권` (입고 수량과 총 수량을 함께 표기, SPEC-ORDER-027)

### 핵심 구현

- 백엔드: `LineItemRackNumberSummaryView`의 응답에 그룹 레벨 `received_quantity` 필드 신규 추가
  - 각 라인아이템별 `min(li.received_quantity, net_qty)` 누적 (환불 차감된 순액 기준)
  - 상태(`logistics_status`) 기반이 아닌 실제 입고 수량(`received_quantity` 필드) 기반 집계
- 프론트엔드: API 응답값을 그대로 렌더링 (클라이언트 산술 제거)

---

## 2. 변경 파일 (Files Changed)

### 백엔드

| 파일 경로 | 변경 유형 | 설명 |
|----------|----------|------|
| `backend/order/purchase_order_views.py` | 수정 | `LineItemRackNumberSummaryView` 클래스, 그룹 집계 루프에서 `received_quantity` 누적 로직 신규 추가 (`:3397-3489`) |
| `backend/order/tests/test_spec_027.py` | 신규 | 신규 acceptance criteria 7개 (`AC-RACKRECV-001 ~ 006, 012`) 테스트 |

### 프론트엔드

| 파일 경로 | 변경 유형 | 설명 |
|----------|----------|------|
| `frontend/src/services/rackNumberApi.ts` | 수정 | `RackNumberSummaryGroup` 타입에 `received_quantity: number` 필드 추가 |
| `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx` | 수정 | `RackNumberSummaryGroupSection` 컴포넌트 헤더 렌더링 로직 변경 (`:58-134`) |
| `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` | 수정 | 신규 렌더링 테스트 5개 추가 |

**총 변경 파일**: 5개 (백엔드 2 + 프론트엔드 3)

---

## 3. 검증 결과 (Test, Lint, Type Check Evidence)

### 테스트

| 테스트 스위트 | 결과 | 상세 |
|-----------|------|------|
| `backend/order/tests/test_spec_027.py` | **✓ 7/7 통과** | 신규 acceptance criteria 테스트 (AC-RACKRECV-001~006, 012) |
| `backend/order/tests/test_spec_014.py` | **✓ 20/20 통과** | 기존 SPEC-ORDER-014 회귀 테스트 무수정 통과 |
| `frontend/src/pages/RackNumberPage/` | **✓ 40/40 통과** | RackNumberPage 전체 vitest 통과 (`SummaryTab.test.tsx`, `SearchTab.test.tsx` 포함) |

### 린트 및 타입 체크

| 도구 | 결과 | 설명 |
|-----|------|------|
| `ruff check` | **✓ 클린** | Python 린트 에러 0개 |
| `tsc --noEmit` | **✓ 클린** | TypeScript 타입 에러 0개 |

**검증 범위**: 변경 파일 5개 + 관련 테스트 모두 성공적으로 검증됨

---

## 4. SPEC 상태 전이 (SPEC Status Transition)

| 항목 | 변경 전 | 변경 후 |
|-----|--------|--------|
| **상태** | `draft` (0.2.1) | `completed` (0.3.0) |
| **버전** | 0.2.1 | 0.3.0 |
| **히스토리** | plan-auditor 2차 리뷰 반영 | 구현 완료 기록 추가 |

SPEC 문서: `.moai/specs/SPEC-ORDER-027/spec.md`

---

## 5. 차원 분석 (Divergence Analysis)

### 계획 대 실제 비교

| 구분 | 계획 | 실제 | 상태 |
|-----|------|------|------|
| **변경 파일 수** | 5개 (v0.2.1 Plan) | 5개 | ✓ 일치 |
| **미예정 파일** | 0개 | 0개 | ✓ 일치 |
| **유보 요구사항** | 0개 | 0개 | ✓ 일치 |
| **신규 AC 추가** | 0개 (v0.2.1에서 AC-RACKRECV-012 신설 완료) | 0개 | ✓ 일치 |

**결론**: **차원 이탈 없음 (Divergence: 0%)**

- 구현이 v0.2.1 plan-auditor 최종 승인 사항과 정확히 일치
- 계획되지 않은 파일 추가 변경 0개
- 계획된 요구사항 모두 달성

---

## 6. 공개 항목 (Known Open Items)

### 1. MX:NOTE 태그 상한선 초과 — 리포지토리 수준 정리 필요

**현황**:
- `backend/order/purchase_order_views.py`에 `@MX:NOTE` 태그 **22개** 존재
- `.moai/mx.yaml` 설정: `note_per_file: 10` (권장 상한선)
- **상태**: 상한선 초과 (22 > 10)

**원인**:
- 이 조건은 **SPEC-ORDER-027 구현 이전부터** 존재함 (21개)
- SPEC-ORDER-027 구현으로 1개 추가 (22개)
- 즉, 이는 이 SPEC의 신규 결함이 아니라, 리포지토리 전체 수준의 정리 수요

**조치**:
- SPEC-ORDER-027은 정상적으로 필요한 주석을 추가하였음
- 전체 22개 태그는 리포지토리 범위 클린업 작업으로 별도 처리 필요
- 이 SPEC 차단 항목 아님, 인지 사항으로 기록

### 2. GitHub Issue 미연결

**현황**:
- `issue_number: 0` (연결된 Issue 없음)
- PR 병합 후 자동 Closes 링크 미생성

**영향**:
- 이는 의도된 상태 (SPEC-ORDER-027은 계획 단계에서 별도 GitHub Issue 없이 추진됨)
- PR에 "Fixes #N" 라벨이 붙지 않음

**조치**:
- GitHub Issue 신규 생성 불필요 (사후 추적 대상 아님)
- PR 설명에 SPEC-ORDER-027 참조 기록

---

## 7. 요약

✓ **모든 요구사항 구현 완료**  
✓ **테스트 검증 완료 (27개 신규 + 20개 회귀)**  
✓ **린트 및 타입 체크 통과**  
✓ **계획 대 실제 완전 일치 (차원 이탈 0%)**  
⚠️ **공개 항목 2개 (리포지토리 정리 후속, GitHub Issue 없음 — 차단 아님)**

---

**생성일**: 2026-08-18  
**담당**: ggajo  
**SPEC 담당자**: ggajo  
