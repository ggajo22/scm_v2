# SPEC-ORDER-014 Compact

버전 1.0.0 기준(초안). SPEC-ORDER-013(완료)을 확장하는 읽기 전용 렉번호 요약 뷰. 상세 구현
참조는 `plan.md`, 인수 시나리오는 `acceptance.md` 참조.

## 요구사항

- REQ-RACKSUM-001: "미출고" 정의 — `LineItem.logistics_status != "shipped"`
  (`not_shipped`/`shipment_confirmed`/`received`/`outbound_scheduled` 포함)
- REQ-RACKSUM-002/002a: 미출고 필터는 항상 고정 적용, 끄거나 완화하는 파라미터 없음/
  전달되어도 무시(Unwanted)
- REQ-RACKSUM-003: 전체 Order를 가로지르는 교차 조회(특정 주문으로 제한하지 않음)
- REQ-RACKSUM-004/004a: `rack_number`별 그룹핑, 빈 문자열은 별도 "미지정" 그룹으로 포함
  (드롭하지 않음)
- REQ-RACKSUM-005: 그룹별 `total_quantity` = 멤버 LineItem `quantity` 합(null은 0 처리)
- REQ-RACKSUM-006: 그룹별 LineItem 목록에 최소 `order_number`/`sku`/`title`/`quantity`/
  `logistics_status` 포함
- REQ-RACKSUM-007: `shipped` LineItem은 어떤 그룹에도 포함 안 됨(전 품목 출고 완료 Order는
  완전히 제외, Unwanted)
- REQ-RACKSUM-008: 페이지네이션 미적용(`UnorderedItemsView` 선례)
- REQ-RACKSUM-009/009a/009b: `/rack-number` 페이지에 "주문 검색"/"렉번호 요약" 탭 2개,
  Tab1 동작 완전 무변경(SPEC-ORDER-013 REQ-RACK-009~011 유지), 기본 활성 탭은 "주문 검색"
- REQ-RACKSUM-010: Tab2 활성화 시 자동 조회(별도 검색 액션 불필요)
- REQ-RACKSUM-011/011a: 그룹 헤더에 렉번호(또는 미지정 라벨) + 총 수량 표시
- REQ-RACKSUM-012: LineItem 행에 주문번호/SKU/도서명/수량/물류상태 표시
- REQ-RACKSUM-013: 그룹 0개일 때 빈 상태 메시지(빈 테이블 아님)
- REQ-RACKSUM-014/015: Tab2에는 체크박스/일괄편집/인라인편집 없음, 어떤 상호작용도 PATCH/
  업로드 요청을 발생시키지 않음(Unwanted)

## 설계 결정 요약

- 미지정 버킷 드롭하지 않고 항상 포함(결정 A, 명시적 가정 문서화)
- 페이지네이션 미적용, `UnorderedItemsView` 선례 재사용(결정 B)
- SPEC-ORDER-013 Exclusions의 "역방향 조회 범위 밖" 조항을 이 읽기 전용 유스케이스에 한해
  대체(결정 C) — Tab1 흐름/배제 규칙은 무변경
- 그룹핑은 Python 애플리케이션 레벨(`select_related` + dict 그룹핑), DB annotate 미사용
  (결정 D)
- 미출고 필터는 하드코딩, 끄는 파라미터 없음(결정 E)
- Tab2는 탭 활성화 시 자동 조회, 별도 검색 액션 없음(결정 F)

## 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/order/purchase_order_views.py` | 수정 | `LineItemRackNumberSummaryView` 클래스 추가(GET, 페이지네이션 없음) |
| `backend/order/urls.py` | 수정 | `line-items/rack-number-summary/` 경로 등록 |
| `backend/order/tests/test_spec_014.py` | 신규 | 필터/그룹핑/미지정 버킷/합계/제외 케이스 테스트 |
| `frontend/src/pages/RackNumberPage/index.tsx` | 신규 | 탭 셸(주문 검색/렉번호 요약), 기본 활성 탭 = 주문 검색 |
| `frontend/src/pages/RackNumberPage.tsx` → `RackNumberPage/tabs/SearchTab.tsx` | 이동 | Tab1 콘텐츠, 로직 무변경 |
| `frontend/src/pages/RackNumberPage/tabs/SummaryTab.tsx` | 신규 | 읽기 전용 요약 렌더링 |
| `frontend/src/services/rackNumberApi.ts` | 수정 | `getRackNumberSummary()` 함수 + 타입 추가 |
| `frontend/src/hooks/useRackNumberQueries.ts` | 수정 | `useRackNumberSummary()` 조회 훅 추가 |
| `frontend/src/pages/RackNumberPage.test.tsx` → `RackNumberPage/tabs/SearchTab.test.tsx` | 이동 | 기존 15개 테스트 단언 무변경 |
| `frontend/src/pages/RackNumberPage/index.test.tsx` | 신규 | 탭 전환/기본 탭 테스트 |
| `frontend/src/pages/RackNumberPage/tabs/SummaryTab.test.tsx` | 신규 | 그룹 렌더링/미지정/빈 상태/읽기 전용 테스트 |

## 인수 기준 요약

- 미출고 4개 상태 포함, `shipped` 제외(AC-RACKSUM-001) + 필터 우회 파라미터 무시
  (AC-RACKSUM-002/002a)
- 전체 주문 교차 조회(AC-RACKSUM-003), 동일 렉에 여러 주문 LineItem 혼재 시 모두 포함
  (AC-RACKSUM-004/004b)
- 빈 `rack_number` → 미지정 그룹 포함, 누락 없음(AC-RACKSUM-004a)
- 총 수량 = 합계(null quantity → 0, AC-RACKSUM-005), LineItem 필드 5종 노출(AC-RACKSUM-006)
- 전 품목 출고 완료 Order 완전 제외(AC-RACKSUM-007) + 부분 출고 Order는 미출고분만
  (AC-RACKSUM-007a)
- 페이지네이션 필드 없음(AC-RACKSUM-008)
- 탭 2개, 기본 활성 탭 "주문 검색"(AC-RACKSUM-009/009b) + Tab1 동작 완전 무변경
  (AC-RACKSUM-009a)
- Tab2 클릭 시 자동 조회(AC-RACKSUM-010), 그룹 헤더(AC-RACKSUM-011) + 미지정 라벨
  (AC-RACKSUM-011a) + LineItem 행 상세(AC-RACKSUM-012) + 빈 상태(AC-RACKSUM-013)
- Tab2에 편집 엘리먼트 전무, PATCH/업로드 요청 발생 안 함(AC-RACKSUM-014/015)

## 제외

- Tab2 편집 기능(체크박스/일괄편집/인라인편집)
- 미출고 필터 토글/파라미터
- 페이지네이션(v1 명시적 보류)
- 렉번호 기준 추가 검색/정렬 UI
- 요약 데이터 Excel/CSV 내보내기
- Tab1(SPEC-ORDER-013) 흐름 변경
