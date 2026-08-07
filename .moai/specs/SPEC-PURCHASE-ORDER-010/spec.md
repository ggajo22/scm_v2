---
id: SPEC-PURCHASE-ORDER-010
version: 1.2.0
status: draft
created: 2026-08-07
created_at: 2026-08-07
updated: 2026-08-07
author: ggajo
priority: High
issue_number: 9
labels: [purchase-order, reorder-queue, backend]
---

# 파손/교환 재발주 큐 재진입

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 1.0.0 | 2026-08-07 | ggajo | 최초 작성 — Decision Point 1~3 리비전(5개 쿼리 사이트 정정, 양쪽 write 경로 대칭 자동 리셋) 반영한 최종 승인본 |
| 1.1.0 | 2026-08-07 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 1, FAIL) 반영 — 프론트매터 `labels`/`created_at` 추가, `status` 유효값 수정, EARS 형식 `## ACCEPTANCE CRITERIA` 섹션 신설(REQ 1:1 추적, 기존 Given/When/Then은 "테스트 시나리오" 섹션으로 재배치), REQ-DMG-001/005/006/007에서 구현 세부사항(파일:라인·마이그레이션 파일명·필드 리스트)을 제거해 "설계 결정" 섹션으로 이관, REQ-DMG-005를 읽기측 공통 패턴(005)과 ConfirmOrderView 전용 예외(005B)로 분리, 기존 AC-6(고아 상태)를 신규 REQ-DMG-008에 연결, 누락됐던 REQ-DMG-001/002/007 인수 기준 보강, REQ-CON-022 출처를 SPEC-ORDER-007로 명시 |
| 1.2.0 | 2026-08-07 | ggajo | Phase 2.3 plan-auditor 리뷰(iteration 2, FAIL — MP-2만 잔존) 반영 — AC-DMG-005/005B/006/006B의 "Given...when...shall" 하이브리드 구문을 순수 Event-Driven EARS로 재작성(Given절을 트리거절에 접힘), AC-DMG-006의 복합 절을 분리해 배치 범위 보장을 신규 AC-DMG-006C(Unwanted)로 독립, AC-DMG-007의 "After...shall" 비표준 구문을 Event-Driven("When the migration is applied...")으로 교체, AC-DMG-004 결번 사유 및 알파벳 접미사(005B/006B/006C) 표기 규칙을 ACCEPTANCE CRITERIA 섹션 상단에 명문화. `priority: High` 표기는 SPEC-PURCHASE-ORDER-009/SPEC-ORDER-001/007 등 기존 승인 SPEC 전체가 동일하게 대문자 표기를 쓰고 있음을 직접 확인 후 프로젝트 일관성을 위해 변경하지 않음(하단 비고 참조) |

---

> **참고**: 이 SPEC의 코드베이스 감사(재발주 후보 쿼리 4→5곳 확인, `ConfirmOrderView`/`DailyReviewExcelView`/`UploadDailyReviewView` 등의 정확한 라인 번호와 구현 세부사항)는 `SPEC-ORDER-011`(LineItem 물류 상태 추적)과 동일한 조사 세션에서 함께 수행되었다. 공유 코드베이스 감사 컨텍스트와 구체적인 코드 위치 인용은 `.moai/specs/SPEC-ORDER-011/research.md`를 참조. 두 SPEC은 데이터/쿼리 접점이 없는 완전 독립 기능이다(`logistics_status` 필드와 `purchase_status`의 `damaged_exchange` 값은 서로 관여하지 않음).

---

## 문제 정의

배송된 도서가 파손되었거나 교환이 필요할 때, 이를 다시 발주 대상으로 올릴 방법이 없다. `LineItem`이 이미 최초 `PurchaseOrder`에 연결되어 있어, 단순히 `purchase_status`에 새 값을 추가하는 것만으로는 재발주 후보 쿼리들이 모두 기존 발주 연결을 이유로 배제하는 조건을 걸고 있어 재노출되지 않는다(직접 코드 확인 완료 — 상세 근거는 아래 결정 G 및 `SPEC-ORDER-011/research.md` 참조).

## 솔루션 개요

1. `LineItem.PURCHASE_STATUS_CHOICES`에 `damaged_exchange`(파손/교환) 신규 값 추가.
2. 기존 단건/일괄 상태 변경 기능이 이미 선택 가능한 값 목록 기반으로 검증하므로, 값만 추가하면 별도 코드 변경 없이 수기로 설정 가능.
3. Daily Review 업로드의 `선택` 컬럼에 "파손/교환" 라벨이 오면 기존 상태 자동 매핑 패턴을 확장해 자동 적용.
4. **읽기측**: 재발주 후보를 판별하는 쿼리들의 필터를 예외 처리해 `damaged_exchange` LineItem이 기존 발주 연결 여부와 무관하게 노출되도록 한다.
5. **쓰기측**: 재발주를 실제로 확정하는 두 흐름(Daily Review 업로드 확정, 수기 발주확정 화면) 모두, 신규 발주가 생성/연결되는 순간 해당 배치의 `damaged_exchange` LineItem을 자동으로 `unordered`로 리셋해 큐에서 자동 제거한다 — 대칭 적용.

구체적인 코드 위치, 함수/클래스명, 필드 리스트는 아래 "설계 결정" 섹션 및 `SPEC-ORDER-011/research.md`에 있다 — REQUIREMENTS 섹션은 관찰 가능한 동작(WHAT)만 규정한다.

## 범위 — 포함

- `LineItem.PURCHASE_STATUS_CHOICES`에 파손/교환 값 추가; `LineItemNote.NOTE_TYPE_CHOICES`에 대응 값 추가.
- Daily Review 업로드의 상태 자동 매핑에 파손/교환 항목 추가.
- 재발주 후보를 판별하는 5개 쿼리 지점의 필터 예외 처리.
- 재발주 확정 시 자동 상태 리셋(Daily Review 업로드 확정 경로, 수기 발주확정 경로 양쪽).
- 프론트엔드: 상태 선택 옵션에 항목 추가(기존 드롭다운 자동 반영).
- 마이그레이션: 두 choices 필드에 신규 값 추가(데이터 백필 불필요).

## 설계 결정

### 결정 G — 읽기측: 재발주 큐 재진입은 링크-배제 조건 예외 처리로 구현 (최종, 5개 사이트)

직접 코드 재확인 결과, 재발주 후보를 판별하는 쿼리는 **5곳**이며 패턴이 두 가지로 나뉜다(정확한 파일:라인은 `SPEC-ORDER-011/research.md` "Additional verification" 절 참조):

| # | 위치 | 현재 필터 패턴 |
|---|------|-----------|
| 1 | 미발주 목록 조회 뷰 | `purchase_status="unordered"` + 기존 발주 연결 시 배제 |
| 2 | 업체 자료 비교 뷰 | 동일 패턴 |
| 3 | Daily Review 다운로드 뷰 | 동일 패턴 |
| 4 | Daily Review 업로드 확정 뷰 | 동일 패턴(SKU 목록 일괄 매칭) |
| 5 | 수기 발주확정 뷰(`ConfirmOrderView`) | **`purchase_status` 필터 자체가 없음** — 기존 발주 연결 여부만으로 판별하는 별도 패턴 |

1~4는 "`unordered`이면서 기존 발주에 전혀 연결되지 않은 LineItem" 또는 "`damaged_exchange`인 LineItem(연결 여부 무관)"을 모두 포함하도록 교체한다(REQ-DMG-005). 5(`ConfirmOrderView`)는 별도 패턴이라 "기존 발주에 전혀 연결되지 않은 LineItem" 또는 "`damaged_exchange`인 LineItem(연결 여부 무관)"으로 별도 교체한다(REQ-DMG-005B) — 이 수정이 없으면 `damaged_exchange` LineItem이 다른 4곳 목록에는 재노출되어도 실제로 "발주 확정" 화면에서 확정 시도 시 충돌 오류로 실패한다. 정확한 쿼리 표현식(Q-object 조합)은 `SPEC-ORDER-011/research.md`와 Run 단계 구현에서 확정한다.

### 결정 H — 쓰기측: 재발주 확정 시 자동 리셋, 양쪽 confirm 경로 대칭 적용 (최종)

Daily Review 업로드의 발주 생성 확정 분기와 수기 발주확정 화면 양쪽 모두에서, 신규 발주가 생성되어 LineItem이 연결되는 순간 그 배치 안에서 `purchase_status == "damaged_exchange"`인 LineItem을 `unordered`로 자동 리셋한다(REQ-DMG-006). 두 흐름 모두 이미 자신의 확정 배치에 대해 일괄 갱신을 수행하고 있으므로, 그 갱신 대상 필드에 `purchase_status`를 추가하는 것만으로 구현된다 — 새 신호/훅 인프라는 도입하지 않는다. 구체적인 함수명, 코드 라인, 일괄 갱신 API 호출 방식은 `SPEC-ORDER-011/research.md` 및 Run 단계 구현에서 확정한다.

- **배치 범위**: 두 흐름 모두 자신의 SKU 스코프 조회 결과에서만 파생되므로, 현재 확정 요청에 포함되지 않은 다른 SKU의 `damaged_exchange` LineItem은 이 write에 전혀 노출되지 않는다.
- **우선순위(수기 발주확정 화면 한정)**: 수기 발주확정 화면은 요청으로 `purchase_status`를 명시적으로 지정할 수 있는 기존 옵션(REQ-CON-022, `SPEC-ORDER-007`에서 정의)이 있다. 자동 리셋을 먼저 적용한 뒤, 요청이 명시적으로 `purchase_status`를 지정한 경우 그 값이 자동 리셋을 덮어쓴다 — 기존 화면 시맨틱을 보존하면서 새 기본 동작을 그 아래 깔아둔다.
- **적용 범위 한정**: Daily Review 업로드의 창고 입고 분기(다른 사유로 `purchase_status`를 무조건 덮어씀)와 CS 분기는 대상이 아니다 — "신규 발주 생성/연결" 흐름에만 적용된다.

---

## 요구사항 (EARS)

### 데이터 모델

**REQ-DMG-001** (Ubiquitous): The system shall provide `damaged_exchange`(파손/교환) as a valid `purchase_status` value, distinct from `unordered`, so the reorder reason persists on the LineItem row itself rather than requiring a reset to `unordered`.

**REQ-DMG-002** (Event-Driven): When an admin sets a LineItem's `purchase_status` to `damaged_exchange` via the existing single/bulk status-change capability, the system shall accept it as a valid choice with no change to that capability's validation behavior beyond recognizing the new value.

**REQ-DMG-003** (Event-Driven): When a Daily Review upload's `선택` column for a SKU contains "파손/교환", the system shall set matched unordered LineItems' `purchase_status` to `damaged_exchange` and create an accompanying note recording the reason, following the same automatic status-mapping behavior already used for the other CS-type labels in that column.

**REQ-DMG-004** (Ubiquitous): The system shall provide a note-type classification for "파손/교환" so that notes created under REQ-DMG-003 are categorized consistently with other note types.

### 읽기측 (결정 G)

**REQ-DMG-005** (Event-Driven): When any of the four SKU-based reorder-candidate queries that currently require `purchase_status="unordered"` AND no existing purchase-order linkage evaluate LineItem eligibility, the system shall also include LineItems where `purchase_status="damaged_exchange"`, regardless of existing purchase-order linkage, in addition to the existing `unordered`-and-unlinked criterion.

**REQ-DMG-005B** (Event-Driven): When the manual order-confirmation flow's own eligibility check (which currently requires only "no existing purchase-order linkage," independent of `purchase_status`) evaluates a SKU, the system shall also treat LineItems where `purchase_status="damaged_exchange"` as eligible regardless of existing purchase-order linkage, so that confirming a reorder for a `damaged_exchange` SKU does not fail due to the pre-existing linkage.

### 쓰기측 (결정 H)

**REQ-DMG-006** (Event-Driven): When either of the two order-confirmation flows (Daily Review upload confirmation, or the manual order-confirmation flow) creates a new purchase order and links matched LineItems, the system shall, for LineItems in that confirmation batch whose current `purchase_status` is `damaged_exchange`, reset `purchase_status` to `unordered` as part of the same write operation that updates the batch's other fields. This reset shall apply only to LineItems present in the current confirmation batch — LineItems outside that batch shall be unaffected. In the manual order-confirmation flow, where the request explicitly supplies a `purchase_status` value for an item, that explicit value shall take precedence over the automatic reset. This requirement does not apply to the Daily Review upload's warehouse-receipt or CS-note branches, which set `purchase_status` for unrelated reasons.

### 마이그레이션

**REQ-DMG-007** (Ubiquitous): The system shall make the new `purchase_status` and note-type values available via a schema migration that requires no data backfill for existing records.

### 하위 호환

**REQ-DMG-008** (Unwanted): If a `damaged_exchange` SKU is included in a client-supplied SKU list for order-file generation, then the system shall NOT require any additional code change to include it in the generated file, since eligibility for that flow is determined solely by the client-supplied list, not by a server-side `purchase_status` filter.

---

## Exclusions (What NOT to Build)

- `PurchaseOrder.status`/M2M 연결 방식 변경
- `LineItem.logistics_status`(SPEC-ORDER-011)와의 상호작용 — 완전 독립
- 수기 메모 생성 화면에서 메모 유형 선택만으로 `purchase_status`를 자동 연동하는 기능 — 기존 4개 CS성 메모 유형 어느 것도 수기 메모 생성 시 자동으로 `purchase_status`를 바꾸지 않으므로, 파손/교환만 예외를 두면 메모 유형 체계 전체에 비일관적 특례가 생긴다. 수기 경로는 기존 상태 변경 기능으로 충분히 커버.

---

## ACCEPTANCE CRITERIA

EARS 형식의 인수 기준. 각 항목은 대응하는 REQ-DMG-XXX 하나 이상에 1:1 이상으로 추적된다. Given/When/Then 형태의 실행 가능한 테스트 시나리오는 아래 "테스트 시나리오" 섹션에 별도로 있으며, 각 시나리오는 AC-DMG-XXX ID를 인용해 상호 추적된다.

**번호 규칙 참고**:
- `AC-DMG-004`는 의도적으로 결번이다 — `AC-DMG-003`이 `REQ-DMG-003`과 `REQ-DMG-004` 둘 다를 함께 추적하므로 별도 ID를 두지 않았다.
- `005B`/`006B`/`006C`처럼 대문자 알파벳이 붙은 ID는 원래 하나였던 요구사항·기준을 단일 트리거·단일 응답 원칙에 따라 분리한 결과다(예: `REQ-DMG-005`의 4곳 공통 패턴과 `REQ-DMG-005B`의 `ConfirmOrderView` 전용 예외 분리). 기본 번호 계열(001~008)에는 결번·중복이 없으며, 알파벳 접미사는 그 기본 항목에서 파생된 하위 항목임을 나타낸다.

**AC-DMG-001** (Ubiquitous) — Traces: REQ-DMG-001. The system shall accept `damaged_exchange` as a stored `purchase_status` value on a LineItem, and that value shall persist unchanged until explicitly modified by an admin action or by REQ-DMG-006's automatic reset.

**AC-DMG-002** (Event-Driven) — Traces: REQ-DMG-002. When a status-change request specifies `damaged_exchange` for one or more LineItems, the system shall apply it exactly as it would any other valid `purchase_status` value, with no additional error or side effect.

**AC-DMG-003** (Event-Driven) — Traces: REQ-DMG-003, REQ-DMG-004. When a Daily Review upload row's `선택` column value is "파손/교환" for a given SKU, the system shall set every matched unordered LineItem for that SKU to `purchase_status="damaged_exchange"` and shall create exactly one accompanying note per matched LineItem, categorized under the 파손/교환 note type.

**AC-DMG-005** (Event-Driven) — Traces: REQ-DMG-005. When any of the four SKU-based reorder-candidate queries is evaluated for a SKU that has a LineItem with `purchase_status="damaged_exchange"` already linked to a prior purchase order, the system shall include that LineItem in the result set.

**AC-DMG-005B** (Event-Driven) — Traces: REQ-DMG-005B. When a reorder is confirmed via the manual order-confirmation flow for a SKU that has a LineItem with `purchase_status="damaged_exchange"` already linked to a prior purchase order, the system shall accept the confirmation and shall NOT reject it due to the pre-existing linkage.

**AC-DMG-006** (Event-Driven) — Traces: REQ-DMG-006. When a confirmation batch (via either confirmation flow — Daily Review upload confirmation or the manual order-confirmation flow) that does not explicitly override `purchase_status` includes a `damaged_exchange` LineItem and that batch's new purchase order is created and linked, the system shall set that LineItem's `purchase_status` to `unordered` as part of the same write.

**AC-DMG-006B** (Event-Driven) — Traces: REQ-DMG-006. When a manual order-confirmation batch containing a `damaged_exchange` LineItem is confirmed and the request explicitly specifies a `purchase_status` value other than the automatic reset value for that LineItem, the system shall persist the explicitly-requested value rather than `unordered`.

**AC-DMG-006C** (Unwanted) — Traces: REQ-DMG-006. If a `damaged_exchange` LineItem is not part of the current confirmation batch, then the system shall NOT change that LineItem's `purchase_status` as a result of that batch's write.

**AC-DMG-007** (Event-Driven) — Traces: REQ-DMG-007. When the migration is applied, the system shall make `damaged_exchange` and its corresponding note-type value selectable, and shall NOT alter any existing LineItem or LineItemNote record's stored values.

**AC-DMG-008** (Unwanted) — Traces: REQ-DMG-008. If a `damaged_exchange` SKU is present in a client-supplied SKU list submitted for order-file generation, then the system shall include it in the generated file using the existing, unmodified order-file generation behavior.

---

## 테스트 시나리오 (BDD, 참고용)

아래는 위 AC-DMG-XXX를 검증하기 위한 실행 가능한 Given/When/Then 시나리오다. 각 시나리오는 대응하는 AC-DMG-XXX를 인용한다.

### 시나리오 1 — Traces: AC-DMG-005

**Given** 기존 발주에 연결된 LineItem을 `damaged_exchange`로 변경한다
**When** 미발주 목록/업체 자료 비교/Daily Review 다운로드 뷰를 조회한다
**Then** 해당 LineItem이 결과에 재노출된다

### 시나리오 1b — Traces: AC-DMG-005B

**Given** 위와 동일한 damaged_exchange LineItem이 있다
**When** 해당 SKU를 수기 발주확정 화면으로 확정 시도한다
**Then** REQ-DMG-005B 적용 전에는 충돌 오류가 발생했을 것이 적용 후 정상적으로 신규 발주 생성/연결에 성공한다

### 시나리오 2 — Traces: AC-DMG-003

**Given** Daily Review 업로드 파일의 `선택` 컬럼 값이 "파손/교환"인 SKU 행이 있다
**When** 업로드가 처리된다
**Then** 매칭된 LineItem의 `purchase_status`가 `damaged_exchange`로 설정되고, 파손/교환 유형의 노트가 생성된다

### 시나리오 3 — Traces: AC-DMG-006

**Given** damaged_exchange LineItem이 포함된 SKU로 Daily Review 파일을 업로드한다
**When** `선택` 컬럼에 유통사(발주처) 값이 있어 신규 발주가 생성/연결된다
**Then** 같은 갱신 작업으로 해당 LineItem의 `purchase_status`가 자동으로 `unordered`로 리셋되고, 이후 후보 쿼리 재조회 시 더 이상 후보로 나타나지 않는다

### 시나리오 3b — Traces: AC-DMG-006C

**Given** 같은 업로드에 포함되지 않은 다른 SKU의 damaged_exchange LineItem이 있다
**When** 시나리오 3의 업로드가 처리된다
**Then** 그 LineItem은 이번 write에 전혀 영향받지 않고 `purchase_status`가 `damaged_exchange`로 유지된다

### 시나리오 4 — Traces: AC-DMG-006

**Given** damaged_exchange LineItem(SKU=Q)이 존재하고, 요청 바디에 `purchase_status`를 명시하지 않은 채 수기 발주확정 화면으로 재발주를 확정한다
**When** 신규 발주가 생성되고 해당 LineItem이 연결된다
**Then** 같은 갱신 작업으로 `purchase_status`가 자동으로 `unordered`로 리셋되고, 이후 후보 쿼리에서 더 이상 후보로 나타나지 않는다 — 시나리오 3(업로드 경로)와 동일한 결과

### 시나리오 4b — Traces: AC-DMG-006B

**Given** damaged_exchange LineItem(SKU=R)이 존재하고, 요청 바디에 `purchase_status="cs_required"`를 명시적으로 지정해 수기 발주확정 화면으로 확정한다
**When** confirm이 처리된다
**Then** 자동 리셋(`unordered`)이 아니라 요청이 명시한 `cs_required`가 최종 값으로 저장된다

### 시나리오 5 — Traces: AC-DMG-001, AC-DMG-002

**Given** 여전히 `unordered` + 발주 미연결 상태인 기존 LineItem이 있다
**When** REQ-DMG-005/006이 적용된 뒤에도 기존 발주 확정 흐름을 그대로 실행한다
**Then** 그 LineItem의 `purchase_status`와 발주 연결 결과는 이번 SPEC 적용 전과 동일한 값·개수를 유지한다(회귀 없음)

### 시나리오 6 — Traces: AC-DMG-008

**Given** damaged_exchange SKU가 프론트엔드에서 선택되어 있다
**When** 그 SKU 목록으로 발주 파일을 생성한다
**Then** 코드 변경 없이 파일에 포함된다

### 시나리오 7 — Traces: AC-DMG-007

**Given** 마이그레이션 적용 전 기존 LineItem/LineItemNote 레코드가 존재한다
**When** 마이그레이션이 적용된다
**Then** 기존 레코드의 값은 하나도 변경되지 않고, `damaged_exchange` 및 대응 노트 유형이 선택 가능해진다

## Definition of Done

- [ ] REQ-DMG-001~008(005B 포함) 및 AC-DMG-001~008(005B/006B/006C 포함, 004는 의도적 결번) 전체 구현 및 테스트 통과
- [ ] 시나리오 1~7 전체 통과, 특히 시나리오 4/4b(대칭 리셋 + 명시적 override 우선순위)
- [ ] 마이그레이션 적용, 데이터 백필 불필요 확인
- [ ] Exclusions 항목이 구현되지 않았음을 코드 리뷰로 확인
- [ ] SPEC-ORDER-011과의 완전 독립성(데이터/쿼리 접점 없음) 코드 리뷰로 재확인
