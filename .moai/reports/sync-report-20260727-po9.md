# Sync Report: SPEC-PURCHASE-ORDER-009

**생성 일시**: 2026-07-27  
**SPEC ID**: SPEC-PURCHASE-ORDER-009  
**커밋**: 0820ac5 (`perf(order): Daily Review 업로드 N+1 쿼리 제거 및 성능 최적화 (1447s→3.3s)`)  
**개발 모드**: TDD  
**평가자 검증**: 2 사이클 (cycle 1 FAIL → 고정 → cycle 2 PASS)

---

## 개요

SPEC-PURCHASE-ORDER-009는 `UploadDailyReviewView.post()`의 N+1 쿼리 패턴을 제거하여 대용량 Daily Review 파일 업로드 시간을 약 400배 개선하는 순수 성능 리팩터링이다. 이 SPEC은 SPEC-008에서 도입한 전체 행 벤더 데이터 동기화 기능의 결과는 그대로 유지하면서, 배치 쿼리를 통해 실행 방식만 최적화한다.

---

## 실장 상태 변경

| 항목 | 이전 | 현재 | 비고 |
|------|------|------|------|
| **SPEC 상태** | `planned` | `completed` | frontmatter 업데이트 |
| **SPEC 버전** | 1.1.0 (변경 없음) | 1.1.0 | 추적 유지 |
| **updated** | 2026-07-27 | 2026-07-27 | 동일 (구현 당일) |

---

## 파일 변경사항

### 수정된 파일

| 파일 경로 | 변경 유형 | 상세 |
|----------|----------|------|
| `.moai/specs/SPEC-PURCHASE-ORDER-009/spec.md` | 수정 | frontmatter `status: planned` → `status: completed`; 구현 노트 섹션 추가 |

### 변경되지 않은 파일 (구현은 완료, 문서는 스킵)

| 파일 경로 | 사유 |
|----------|------|
| `.moai/project/product.md` | Daily Review 업로드 성능 특성이 문서화되지 않음 (SPEC-008 sync와 동일한 결론) |
| `backend/order/purchase_order_views.py` | 구현 완료 (커밋 0820ac5에 포함) — 이번 sync는 문서화만 담당 |
| `backend/order/tests/test_daily_review_upload.py` | 구현 완료 (커밋 0820ac5에 포함) — 이번 sync는 문서화만 담당 |

---

## 질리팅 게이트 및 평가자 검증 이력

### 자동화 테스트

**상태**: ✓ 완전히 통과

- **기존 73개 테스트**: SPEC-005/006/007/008 관련 케이스 무변경 통과 (REQ-PO9-012)
- **신규 회귀 테스트**: 300~500행 합성 픽스처 기반 쿼리 수 상한 검증 추가 (REQ-PO9-010)
  - 측정 결과: 14쿼리 (상한 30개 미만 충족)
  - 행 수 선형성: 불변 확인 (300행 vs 500행 쿼리 수 동일)
- **총 테스트 건수**: 76건 (기존 73 + 신규 회귀 3)

### 평가자 활용(evaluator-active) 검증

**상태**: ✓ 2 사이클 후 PASS

#### 사이클 1: FAIL (픽스 사이클 1 구현, 0820ac5)

**측정**: 실제 프로덕션 파일 (447행, 400개 유니크 SKU) 재측정

- **성능**: 120초 / 795쿼리
- **평가 결과**: ❌ FAIL
- **이유**: REQ-PO9-009("초 단위" 목표) 미달. 전체 행의 98%(439행)가 흐르는 비창고 분기의 개별 `PurchaseOrder.objects.create()` + `po.line_items.add()` 호출이 여전히 지배적 병목.

**피드백**:
- `PurchaseOrder` 배칭이 필요 (REQ-PO9-007, 초기 구현에서는 "낮은 우선순위"로 보류됨)
- 벤더 테이블/LineItem/LineItemNote 배칭만으로는 불충분

#### 사이클 2: PASS (픽스 사이클 2 구현, 0820ac5 동일 커밋)

**변경**: REQ-PO9-007 `PurchaseOrder` 배칭 완성

- `PurchaseOrder.objects.bulk_create()`로 배치 생성
- `PurchaseOrder.line_items.through.objects.bulk_create()`로 M2M 연결 배치 처리
- MySQL 백엔드의 `can_return_rows_from_bulk_insert = False` 제약에 대응하여 `created_at__gte=t_before` 재조회 폴백 채택

**측정**: 동일 프로덕션 파일 최종 재측정

- **성능**: 3.50초 / 14쿼리
- **개선도**: 1447초 대비 **약 413배**, 픽스 사이클 1의 120초 대비 **약 34배 추가 개선**
- **평가 결과**: ✓ PASS

**사용자 수용성**: 사용자가 실제 UI를 통해 동일 파일로 재테스트한 결과, 측정된 3.50초의 성능이 현실에서도 유지됨을 확인 (실제 운영 환경에서의 최종 검증)

---

## 발산도 분석 (Divergence Analysis)

**상태**: ✓ 발산 없음

### 구현 범위 vs SPEC 범위

| 항목 | SPEC 정의 | 구현 실적 | 일치 여부 |
|------|----------|----------|----------|
| **벤더 테이블 배칭** | REQ-PO9-001/002 | ✓ 완성 (픽스 사이클 1) | ✓ 일치 |
| **LineItem 배칭** | REQ-PO9-004 | ✓ 완성 (픽스 사이클 1) | ✓ 일치 |
| **LineItemNote 배칭** | REQ-PO9-005 | ✓ 완성 (픽스 사이클 1) | ✓ 일치 |
| **WarehouseStock 검증** | REQ-PO9-006 | ✓ 완성 (SKU별 개별 유지) | ✓ 일치 |
| **PurchaseOrder 배칭** | REQ-PO9-007 (낮은 우선순위) | ✓ 완성 (픽스 사이클 2) | ✓ 일치 (평가자 피드백 반영) |
| **쿼리 수 상한 테스트** | REQ-PO9-010 (신규) | ✓ 완성 | ✓ 일치 |
| **기존 동작 무변경** | REQ-PO9-011/012 | ✓ 검증 완료 | ✓ 일치 |

### 평가자 피드백 반영

SPEC의 REQ-PO9-007은 초기에 "낮은 우선순위"로 설정되었지만, 평가자 활용(evaluator-active) 검증 사이클 1에서 실사용 파일 측정 결과를 바탕으로 **우선순위 격상 필요**로 지적되었다. 구현팀이 이 피드백을 즉시 반영하여 픽스 사이클 2에서 완성했으며, 이는 정상적인 TDD 개발 흐름의 일부이다 (평가자 피드백 → 개선 → 재평가).

**결론**: 발산이 아닌 **정상적인 반복 개선**. SPEC의 범위와 평가자 검증이 함께 작동하여 최적의 결과 도출.

---

## 기술적 발견사항

### MySQL bulk_create 제약

- Django의 `bulk_create()` 호출 후 생성된 객체의 `.pk`가 채워지지 않음 (MySQL 백엔드의 `can_return_rows_from_bulk_insert = False`)
- 폴백 전략: `bulk_create()` 직전 시각 기록 후 `created_at__gte=t_before`로 재조회하여 SKU별 매칭
- 상세: SPEC 본문 REQ-PO9-007 "PK 조회 방식 실증" 섹션 참고

### 필드 집합 그룹화

- `bulk_create(update_conflicts=True)` 호출 내 모든 객체가 동일한 `update_fields` 집합을 가져야 함 (Django ORM 제약)
- 레거시 형식/신 템플릿 형식의 벤더 컬럼 차이를 보존하기 위해 사전 그룹화 후 그룹별 배치 실행
- SPEC-008의 Bug-1-fix (레거시 데이터 무손실 보장) 완벽 승계

### `unique_fields` 회피

- Django의 `bulk_create(update_conflicts=True, unique_fields=[...])` 호출 시 MySQL 백엔드에서 `NotSupportedError` 발생
- MySQL의 `INSERT ... ON DUPLICATE KEY UPDATE`는 고유 제약을 자동으로 대상화하므로 별도 지정 불필요
- 폴백: `unique_fields` 생략

---

## 성능 개선 요약

| 측정 단계 | 처리 시간 | 쿼리 수 | 1447초 대비 | 비고 |
|----------|----------|--------|-----------|------|
| **초기 진단** | 1447초 | ~3000-6000 | — | SPEC-008 도입 후 실사용 파일 첫 측정 |
| **픽스 사이클 1** | 120초 | 795 | 약 12배 개선 | 벤더/LineItem/LineItemNote 배칭 |
| **픽스 사이클 2** | 3.50초 | 14 | 약 413배 개선 | + PurchaseOrder M2M 배칭 |
| **사용자 재검증** | ✓ 확인 | — | 같음 | 실제 UI 통해 운영 환경 재테스트 완료 |

---

## 관찰 가능한 동작 검증

REQ-PO9-011/012에 따라 다음 항목의 무변경을 확인했다 (기존 73개 테스트 무변경 통과 기반):

- ✓ **응답 값**: `confirmed_count`, `skipped_count`, `errors`, `confirmed_by_distributor`
- ✓ **생성/갱신 레코드**: `PurchaseOrder`, `LineItem`, `LineItemNote`, `WarehouseStock`, `BooxenData`, `KyoboData`, `Yes24Data`
- ✓ **분기 로직**: `선택` 값 처리, CS 분기, 창고 분기, YES24 발주 확정 분기의 판별

---

## 관련 아티팩트

| 아티팩트 | 위치 | 용도 |
|---------|------|------|
| SPEC 문서 | `.moai/specs/SPEC-PURCHASE-ORDER-009/spec.md` | 요구사항 및 구현 노트 |
| 테스트 스위트 | `backend/order/tests/test_daily_review_upload.py` | 76개 테스트 (기존 73 + 신규 3) |
| 구현 코드 | `backend/order/purchase_order_views.py` | `UploadDailyReviewView.post()` 리팩터링 |
| 커밋 | 0820ac5 | perf(order): Daily Review 업로드 N+1 쿼리 제거 및 성능 최적화 |

---

## 결론

SPEC-PURCHASE-ORDER-009의 구현은 **완료**되었으며, 모든 품질 게이트를 통과했다:

- ✓ 76개 자동화 테스트 전 통과
- ✓ 평가자 활용(evaluator-active) 2 사이클 검증 완료 (사이클 1 FAIL → 피드백 반영 → 사이클 2 PASS)
- ✓ 실사용 파일 성능: 1447초 → 3.50초 (약 413배 개선)
- ✓ 사용자 재검증: 운영 환경에서의 성능 개선 확인됨
- ✓ 기존 동작 무변경: 73개 기존 테스트 전 통과, 관찰 가능한 응답/레코드 값 동일
- ✓ SPEC 범위와의 발산 없음: 평가자 피드백 반영은 정상적인 개선 프로세스

SPEC 문서의 `status: planned` → `status: completed` 전환 및 구현 노트 추가를 통해 동기화를 완료했다.
