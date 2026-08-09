# SPEC-ORDER-013 태스크 분해 (TDD)

개발 방법론: **TDD (RED-GREEN-REFACTOR)** — `quality.yaml` `development_mode: tdd`,
`test_first_required: true`, `min_coverage_per_commit: 80%`, 목표 커버리지 85%+.

각 TASK는 단일 RED-GREEN-REFACTOR 사이클로 완결 가능한 최소 단위다. `plan.md`의 M1-M6
마일스톤을 파일 단위 원자적 태스크로 분해했으며, 신규 파일은 `plan.md`가 명시한 파일 목록을
벗어나지 않는다(단, 기존 파일에 대한 필수적인 소규모 추가 — `frontend/src/types/order.ts`
필드 추가, `Sidebar.test.tsx`/`OrderDetailPage.test.tsx` 어서션 추가 — 는 코드베이스 관례
확인 결과에 따라 포함했다. 상세 근거는 리포트 본문 참조).

## 태스크 목록

| Task ID | Description | Requirement | Dependencies | Planned Files | Status |
|---------|-------------|-------------|---------------|----------------|--------|
| TASK-001 | `LineItem.rack_number` 필드 추가(`location` 패턴 그대로) + 단일 `AddField` 마이그레이션(`0034`, 백필 없음) + Order 레벨 필드/프로퍼티 부재 검증 테스트 | REQ-RACK-001, REQ-RACK-002 | 없음 | `backend/order/models.py` [MODIFY]; `backend/order/migrations/0034_lineitem_add_rack_number.py` [NEW]; `backend/order/tests/test_spec_013.py` [NEW] | pending |
| TASK-002 | 단건 PATCH 엔드포인트 `LineItemRackNumberUpdateView`(존재/미존재 404, 10자 초과 400, 정상 200 + 응답 바디) + urls.py 등록 + 중복값 허용(REQ-RACK-013) 검증 | REQ-RACK-003, REQ-RACK-003a, REQ-RACK-003b, REQ-RACK-013(부분) | TASK-001 | `backend/order/purchase_order_views.py` [MODIFY]; `backend/order/urls.py` [MODIFY]; `backend/order/tests/test_spec_013.py` [MODIFY] | pending |
| TASK-003 | 일괄 PATCH 엔드포인트 `LineItemBulkRackNumberUpdateView`(빈 id 리스트 400, 존재/미존재 id 혼합 처리 + `missing_ids`, `_recompute_order_aggregates()` 미호출 확인) + urls.py 등록(`<int:pk>` 경로보다 선행) + 중복값 허용(REQ-RACK-013) 검증 | REQ-RACK-004, REQ-RACK-004a, REQ-RACK-013(부분) | TASK-001 (urls.py 편집은 TASK-002와 동일 블록이므로 순차 진행 권장) | `backend/order/purchase_order_views.py` [MODIFY]; `backend/order/urls.py` [MODIFY]; `backend/order/tests/test_spec_013.py` [MODIFY] | pending |
| TASK-004 | `parse_rack_number_excel()` 순수 파서 함수(주문번호/SKU/렉번호 3컬럼 대소문자·순서 무관 헤더 탐색, 컬럼 누락 시 `ValueError`) | REQ-RACK-005, REQ-RACK-005a | 없음(DB 비의존 순수 함수, TASK-001과 병렬 가능) | `backend/order/excel_utils.py` [MODIFY]; `backend/order/tests/test_spec_013.py` [MODIFY] | pending |
| TASK-005 | 업로드 엔드포인트 `UploadRackNumberView`(422 처리, (주문번호,SKU) dedup 마지막-행-우선, 주문 매칭 시 전체 LineItem 갱신, 교차 주문 격리, `matched_count`/`skipped_count` distinct-키 집계) + urls.py 등록 | REQ-RACK-006, REQ-RACK-006a, REQ-RACK-006b, REQ-RACK-007 | TASK-001, TASK-004 | `backend/order/purchase_order_views.py` [MODIFY]; `backend/order/urls.py` [MODIFY]; `backend/order/tests/test_spec_013.py` [MODIFY] | pending |
| TASK-006 | `LineItemDetailSerializer.Meta.fields`에 `"rack_number"` 추가(읽기 노출) | REQ-RACK-001(노출), REQ-RACK-009 지원 | TASK-001 | `backend/order/serializers.py` [MODIFY]; `backend/order/tests/test_spec_013.py` [MODIFY] | pending |
| TASK-007 | `rackNumberApi.ts` — 타입(`RackNumberResponse`/`BulkRackNumberResponse`/`UploadRackNumberResponse`) + 함수(`updateLineItemRackNumber`/`bulkUpdateLineItemRackNumber`/`uploadRackNumber`) | REQ-RACK-003/004/005 프론트 소비 지원 | TASK-002, TASK-003, TASK-005, TASK-006(계약) — 병행 개발 가능(spec.md 계약 기준) | `frontend/src/services/rackNumberApi.ts` [NEW] | pending |
| TASK-008 | `useRackNumberQueries.ts` — `useUpdateLineItemRackNumber`/`useBulkUpdateLineItemRackNumber`(missing_ids 경고 토스트)/`useUploadRackNumber`(matched/skipped 토스트), Order 상세 쿼리 무효화 | REQ-RACK-010a, REQ-RACK-011, REQ-RACK-006/007(업로드 트리거) 지원 | TASK-007 | `frontend/src/hooks/useRackNumberQueries.ts` [NEW] | pending |
| TASK-009 | `RackNumberPage.tsx` 초기 골격 — 주문번호 검색 입력/버튼, 검색 성공 시 LineItem 테이블(SKU/도서명/rack_number 컬럼), 실패 시 not-found 상태 + `LineItemDetail.rack_number` 타입 추가 | REQ-RACK-009, REQ-RACK-009a | TASK-006 (응답에 rack_number 포함 필요) | `frontend/src/pages/RackNumberPage.tsx` [NEW]; `frontend/src/types/order.ts` [MODIFY]; `frontend/src/pages/RackNumberPage.test.tsx` [NEW] | pending |
| TASK-010 | 라우팅(`/rack-number` lazy route) + 사이드바 메뉴 항목(`MapPin` 아이콘) 등록 | REQ-RACK-008 | TASK-009(페이지 컴포넌트 존재 필요) | `frontend/src/router/index.tsx` [MODIFY]; `frontend/src/components/Sidebar.tsx` [MODIFY]; `frontend/src/components/Sidebar.test.tsx` [MODIFY] | pending |
| TASK-011 | 체크박스 다중 선택 — 행별 체크박스 + 헤더 전체선택 토글 + 재검색 시 선택 초기화(로컬 `useState<number[]>`, 결정 F) | REQ-RACK-010 | TASK-009 | `frontend/src/pages/RackNumberPage.tsx` [MODIFY]; `frontend/src/pages/RackNumberPage.test.tsx` [MODIFY] | pending |
| TASK-012 | 일괄 적용 컨트롤 — 렉번호 입력 + "일괄 적용" 버튼(체크 1건 이상일 때만 활성화), 성공 시 단일 bulk-PATCH 요청 + 선택 해제 + 테이블 갱신 | REQ-RACK-010a | TASK-011, TASK-008 | `frontend/src/pages/RackNumberPage.tsx` [MODIFY]; `frontend/src/pages/RackNumberPage.test.tsx` [MODIFY] | pending |
| TASK-013 | 개별 인라인 편집 — `rack_number` 셀 텍스트 입력(`maxLength=10`), blur/Enter 확정 시 단건 PATCH, 페이지 새로고침 없이 셀 갱신, 다른 행/선택 상태에 영향 없음 | REQ-RACK-011 | TASK-009, TASK-008 | `frontend/src/pages/RackNumberPage.tsx` [MODIFY]; `frontend/src/pages/RackNumberPage.test.tsx` [MODIFY] | pending |
| TASK-014 | Excel 업로드 UI — 파일 선택 + 업로드 트리거 버튼, 성공 시 matched/skipped 카운트 토스트 표시(백엔드 로직은 TASK-005에서 이미 구현됨, 여기서는 트리거 UI만) | REQ-RACK-006/007 프론트 트리거 지원 | TASK-009, TASK-008 | `frontend/src/pages/RackNumberPage.tsx` [MODIFY]; `frontend/src/pages/RackNumberPage.test.tsx` [MODIFY] | pending |
| TASK-015 | `OrderDetailPage` 회귀 방지 가드 — API 응답에 `rack_number`가 포함되어도 화면 어디에도 렌더링/편집 UI가 나타나지 않음을 확인하는 부정 어서션 추가(코드 변경 없음, 테스트만 추가) | REQ-RACK-012 | TASK-006(현실적인 mock payload 구성을 위해 권장, 강제 아님) | `frontend/src/pages/OrderDetailPage.test.tsx` [MODIFY] | pending |

## 요구사항 커버리지 매트릭스

REQ-RACK-001~013 및 하위 접미사(003a/003b/004a/005a/006a/006b/009a/010a) 전체 21개 항목이
1개 이상의 TASK에 매핑됨을 검증했다.

| REQ ID | 매핑 TASK | REQ ID | 매핑 TASK | REQ ID | 매핑 TASK |
|--------|-----------|--------|-----------|--------|-----------|
| REQ-RACK-001 | TASK-001, TASK-006, TASK-009 | REQ-RACK-006 | TASK-005 | REQ-RACK-009a | TASK-009 |
| REQ-RACK-002 | TASK-001 | REQ-RACK-006a | TASK-005 | REQ-RACK-010 | TASK-011 |
| REQ-RACK-003 | TASK-002 | REQ-RACK-006b | TASK-005 | REQ-RACK-010a | TASK-012 |
| REQ-RACK-003a | TASK-002 | REQ-RACK-007 | TASK-005 | REQ-RACK-011 | TASK-013 |
| REQ-RACK-003b | TASK-002 | REQ-RACK-008 | TASK-010 | REQ-RACK-012 | TASK-015 |
| REQ-RACK-004 | TASK-003 | REQ-RACK-009 | TASK-009 | REQ-RACK-013 | TASK-002, TASK-003 |
| REQ-RACK-004a | TASK-003 | | | | |
| REQ-RACK-005 | TASK-004 | | | | |
| REQ-RACK-005a | TASK-004 | | | | |

AC-RACK-006c(교차 주문 격리)와 AC-RACK-010b/010c(전체선택 토글/재검색 초기화)는 REQ-RACK-006과
REQ-RACK-010의 세부 시나리오이며 각각 TASK-005, TASK-011의 테스트 범위에 포함된다(spec.md
HISTORY 1.1.0 기록상 AC만 세분화되고 REQ는 세분화되지 않음).

## 실행 순서(의존성 그래프)

```
TASK-001 (모델)
 ├─> TASK-002 (단건 PATCH) ─┐
 ├─> TASK-003 (일괄 PATCH) ─┤ (urls.py 동일 블록, 순차 편집 권장)
 ├─> TASK-004 (엑셀 파서, 001과 병렬 가능)
 │     └─> TASK-005 (업로드 뷰)
 └─> TASK-006 (시리얼라이저 노출)

TASK-002, TASK-003, TASK-005, TASK-006 (백엔드 계약 확정)
 └─> TASK-007 (rackNumberApi.ts)
       └─> TASK-008 (useRackNumberQueries.ts)

TASK-006 ─> TASK-009 (RackNumberPage 골격 + 타입)
              ├─> TASK-010 (라우팅/사이드바)
              ├─> TASK-011 (체크박스) ─> TASK-012 (일괄 적용, TASK-008 필요)
              ├─> TASK-013 (인라인 편집, TASK-008 필요)
              └─> TASK-014 (엑셀 업로드 UI, TASK-008 필요)

TASK-006 ─(권장)─> TASK-015 (OrderDetailPage 가드, 독립 실행 가능)
```
