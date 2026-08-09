# SPEC-ORDER-013 Compact

버전 1.1.0 기준(draft, Phase 2.3 plan-auditor 리뷰 iteration 3 반영 — AC-RACK-003/003a/003b
후행 "shall" 주어를 모두 "the system"으로 통일, REQ-RACK-002 동일 결함 정정, AC-RACK-006을
006(양성 매칭)/006c(음성 교차 주문 제한, 신설)로 분리, AC-RACK-010을 010(렌더링)/010b(전체선택
토글, 신설)/010c(재검색 시 선택 초기화, 신설)로 분리, REQ-RACK-008/AC-RACK-008에서 구현
세부사항 문구 제거. 상세 구현 참조는 plan.md, 인수 시나리오는 acceptance.md 참조).

## 요구사항

- REQ-RACK-001: `LineItem.rack_number` 신규 필드 — `location`과 동일한 패턴
  (`CharField(max_length=10, blank=True, default="")`)
- REQ-RACK-002: Order 레벨 집계/롤업 없음, `rack_number`는 수동 편집/일괄 적용/Excel
  업로드로만 설정되며 자동 계산 경로는 존재하지 않음(Unwanted)
- REQ-RACK-003/003a/003b: 단건 PATCH — 정상 갱신 / 존재하지 않는 id는 404 / 10자 초과 값은
  400(변경 없음 유지)
- REQ-RACK-004/004a: 일괄 PATCH(명시적 id 목록) — 매칭 갱신 + `missing_ids` 응답 / 빈
  id 목록은 400
- REQ-RACK-005/005a: Excel 업로드 — 주문번호/SKU/렉번호 3컬럼을 헤더 이름 기반 대소문자
  무시 부분일치로 탐색(컬럼 순서 무관) / 필수 컬럼 누락 시 422
- REQ-RACK-006/006a/006b: (주문번호, SKU) 조합으로 LineItem 매칭해 적용 / 미매칭 행은
  skip / 동일 (주문번호, SKU) 중복 행은 마지막 행 우선
- REQ-RACK-007: 업로드 응답 `matched_count`/`skipped_count`는 distinct (주문번호, SKU)
  행 기준 카운트
- REQ-RACK-008: 신규 독립 라우트 페이지 + 사이드바 메뉴 항목(관찰 가능한 라우팅/메뉴 동작만
  규정 — 구현 세부사항인 "lazy-loaded route"/"code-split" 문구는 v1.1.0에서 제거됨)
- REQ-RACK-009/009a: 주문번호 정확 매칭 검색 → LineItem 테이블 표시 / 미매칭 시 미발견
  상태
- REQ-RACK-010/010a: 체크박스 다중 선택(로컬 상태) + 전체선택 렌더링 / 일괄 적용 시 단일
  bulk-PATCH 요청 후 선택 초기화
- REQ-RACK-011: 개별 LineItem 인라인 편집 → 단건 PATCH, 새로고침 없이 반영
- REQ-RACK-012: OrderDetailPage에는 rack_number 미노출/미편집(Unwanted)
- REQ-RACK-013: capacity 검증/uniqueness 제약 없음(Unwanted)

## 설계 결정 요약

- 데이터 모델: `location` 필드 패턴 그대로 채택, Order 집계 없음(결정 A)
- 마이그레이션: `AddField` 단독, 백필 불필요(결정 B)
- 검색: 기존 `GET /api/orders/?search=`(정확 order_number 매칭) + 기존
  `GET /api/orders/{id}/`(`OrderDetailView`) 재사용, 신규 검색 엔드포인트 없음(결정 C)
- Excel 매칭: 이름 기반 대소문자 무시 부분일치 헤더 탐색 + 마지막 행 우선(결정 D)
- (주문번호, SKU) 조합이 LineItem 2개 이상과 매칭되면 전부 적용(결정 E, 명시적 가정)
- 프론트엔드 체크박스 선택 상태는 로컬 컴포넌트 상태(전역 스토어 미사용, 결정 F)

## 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/models.py` | 수정 | `LineItem`에 `rack_number` 필드 추가(REQ-RACK-001/002) |
| `backend/order/migrations/0034_lineitem_add_rack_number.py` | 신규 | `AddField` 단독, 백필 없음(번호는 Run 단계 재검증 필요) |
| `backend/order/purchase_order_views.py` | 수정 | `LineItemRackNumberUpdateView`/`LineItemBulkRackNumberUpdateView`/`UploadRackNumberView` 3개 클래스 추가 |
| `backend/order/urls.py` | 수정 | 3개 엔드포인트 등록(`bulk-rack-number`를 `<int:pk>/rack-number/`보다 먼저 등록) |
| `backend/order/excel_utils.py` | 수정 | `parse_rack_number_excel()` 신규 함수 추가 |
| `backend/order/serializers.py` | 수정 | `LineItemDetailSerializer.Meta.fields`에 `rack_number` 추가 |
| `frontend/src/pages/RackNumberPage.tsx` | 신규 | 검색 + 테이블(체크박스/인라인 편집) + 일괄 적용 + Excel 업로드 UI |
| `frontend/src/router/index.tsx` | 수정 | `/rack-number` 라우트 추가 |
| `frontend/src/components/Sidebar.tsx` | 수정 | `flatNavItems`에 "렉번호 관리" 메뉴 항목 추가 |
| `frontend/src/services/rackNumberApi.ts` | 신규 | 단건/일괄 PATCH, 업로드 API 함수 및 타입 정의 |
| `frontend/src/hooks/useRackNumberQueries.ts` | 신규 | TanStack Query mutation 훅 3종 |
| `backend/order/tests/test_spec_013.py` | 신규(권장) | 단건/일괄/업로드 정상·예외 경로 및 (주문번호, SKU) 매칭·미매칭 케이스 |

## 인수 기준 요약

- 단건/일괄 PATCH 정상 갱신(AC-RACK-003/004) + 404/400 예외 경로(AC-RACK-003a/003b/004a)
- Excel 업로드: 헤더 순서/대소문자 무관 탐색(AC-RACK-005/005a), (주문번호, SKU) 정확 매칭
  양성 적용(AC-RACK-006), 매칭되지 않은 다른 주문 소속 LineItem은 절대 변경되지 않음(AC-RACK-006c),
  주문번호/SKU 미매칭 skip(AC-RACK-006a), 중복 행 last-row-wins(AC-RACK-006b),
  matched+skipped 합산 검증(AC-RACK-007)
- 신규 라우트/메뉴로만 접근 가능, 발주 관리 페이지의 탭이 아님(AC-RACK-008)
- 주문번호 정확 매칭 검색(이름 부분일치 오탐 방지 포함, AC-RACK-009/009a)
- 체크박스 다중 선택 렌더링(AC-RACK-010) + 전체선택 토글(AC-RACK-010b) + 일괄 적용 후 선택
  해제(AC-RACK-010a) + 재검색 시 선택 상태 초기화(AC-RACK-010c)
- 개별 인라인 편집이 단건 PATCH만 트리거하고 페이지 새로고침 없음(AC-RACK-011)
- OrderDetailPage에는 rack_number가 전혀 노출되지 않음(AC-RACK-012)
- 값 중복/용량 제약 없음(AC-RACK-013)

## 제외

- OrderDetailPage rack_number 노출/편집
- Order 레벨 rack_number 집계/롤업/필터 UI·API
- 렉 용량 검증, rack_number 고유성 제약
- rack_number 변경 이력(audit trail)
- rack_number 기준 역방향 전역 검색/필터
- WarehouseStock 연동
