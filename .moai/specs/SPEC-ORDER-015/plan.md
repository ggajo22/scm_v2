---
id: SPEC-ORDER-015
document: plan
version: 1.0.0
status: draft
updated: 2026-08-10
---

# 구현 계획 — SPEC-ORDER-015 출고 처리

`spec.md`의 요구사항(REQ-OUTBOUND-001~019)을 구현하기 위한 파일별 변경 계획, 기술적 접근,
마일스톤, 리스크를 정리한다. 근거 자료는 `research.md`(파일:라인 인용 포함)를 참조한다.

## 마일스톤 (우선순위 기반, 시간 추정 없음)

- **M1 (High) — 데이터 모델**: `LineItem`에 `shipped_quantity`/`shipped_at` 필드 추가 +
  마이그레이션 작성. 이후 모든 마일스톤의 선행 조건.
- **M2 (High) — 백엔드 처리 로직**: 공용 매칭/판정/반영 함수 + Excel 파서 + 2개 뷰(`OutboundProcessView`,
  `UploadOutboundView`) + URL 등록.
- **M3 (High) — 백엔드 테스트**: 매칭/중복 합산/수량초과/상태 전이/복수 매칭 스킵/null quantity
  케이스에 대한 pytest 작성 — REQ-OUTBOUND-001~019 전량 커버.
- **M4 (Medium) — 프론트엔드**: 서비스 함수 + 훅 + 신규 페이지(수동 입력/Excel 업로드/결과
  시각화) + 사이드바/라우터 등록.
- **M5 (Medium) — 프론트엔드 테스트 + 회귀 확인**: 신규 페이지 테스트 작성 + SPEC-ORDER-013/014
  기존 테스트 스위트 재실행으로 무영향 확인.
- **M6 (Low) — 문서 동기화**: `product.md` 기능 목록 갱신, SPEC 상태를 `completed`로 전이.

## 파일별 변경 계획

### 백엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| MODIFY | `backend/order/models.py` (`LineItem` 클래스, `logistics_status` 필드 직후 197행 부근) | `shipped_quantity = models.IntegerField(default=0)`, `shipped_at = models.DateTimeField(null=True, blank=True)` 추가. SPEC-ORDER-015 참조 주석 포함. |
| NEW | `backend/order/migrations/0035_lineitem_add_shipped_fields.py` | 위 2개 필드 추가 마이그레이션. 현재 최신 마이그레이션은 `0034_lineitem_add_rack_number.py`(확인 완료). |
| MODIFY | `backend/order/excel_utils.py` (994행 `parse_rack_number_excel` 인근에 신규 함수 추가) | `parse_outbound_excel(file_bytes: bytes) -> list[dict]` — 동일 헤더 자동탐색 패턴(소문자화 substring 매칭). 별칭: `name→["name","주문번호"]`, `sku→["sku","lineitem sku"]`, `total→["total","수량"]`. 실패 시 `ValueError`(뷰에서 HTTP 422로 변환, REQ-OUTBOUND-012a). |
| MODIFY | `backend/order/purchase_order_views.py` | 공용 처리 함수(가칭 `_process_outbound_rows(rows: list[dict]) -> dict`) 신설 — REQ-OUTBOUND-003~010a 전체 로직 포함(아래 "기술적 접근" 참조). 신규 뷰 2개: `OutboundProcessView`(POST, 수동입력 JSON), `UploadOutboundView`(POST, Excel 업로드) — 둘 다 `_process_outbound_rows` 공유, `UploadRackNumberView`(2151-2254행) 구조 재사용. |
| MODIFY | `backend/order/urls.py` (82-97행 SPEC-ORDER-013 블록 인근) | `path("purchase-orders/line-items/outbound-process/", OutboundProcessView.as_view(), name="po-line-item-outbound-process")`, `path("purchase-orders/upload-outbound/", UploadOutboundView.as_view(), name="po-upload-outbound")` 등록. 두 경로 모두 `<int:pk>` 세그먼트가 없어 기존 패턴과 충돌 없음. |
| MODIFY (선택) | `backend/order/serializers.py` (`LineItemDetailSerializer.Meta.fields`, 108-118행) | `shipped_quantity`, `shipped_at` 필드 노출 추가(낮은 리스크, 향후 주문 상세 화면에서 참조 가능하도록). |

### 프론트엔드

| 구분 | 파일 | 변경 내용 |
|---|---|---|
| NEW | `frontend/src/pages/OutboundPage/index.tsx` | 독립 페이지 — 수동 입력 폼 + Excel 업로드 + 결과 시각화(matched/매칭실패/수량초과 3섹션) + "다시 처리하기" 리셋 버튼. `RackNumberPage`와 완전히 분리, import 없음. |
| NEW | `frontend/src/services/outboundApi.ts` | `processOutboundManual(rows)`, `uploadOutbound(formData)` — `rackNumberApi.ts` 패턴(타입 정의 + `api.post` 호출) 재사용. |
| NEW | `frontend/src/hooks/useOutboundQueries.ts` | `useProcessOutboundManual()`, `useUploadOutbound()` — `useRackNumberQueries.ts`의 `useMutation` + `toast` 패턴 재사용. |
| MODIFY | `frontend/src/router/index.tsx` (116-121행 `/rack-number` 등록 인근) | `/outbound` lazy route 추가(`RackNumberPage` 등록과 동일 패턴). |
| MODIFY | `frontend/src/components/Sidebar.tsx` (3행 import, 37-80행 `flatNavItems`) | `Truck` 아이콘 import 추가, `{ label: '출고 처리', href: '/outbound', icon: Truck }` 항목을 '렉번호 관리'(63-67행) 인근에 배치. |

## 기술적 접근 — 공용 처리 함수 로직 (REQ-OUTBOUND-003~010a, 설계 결정 A/B/C 반영)

`_process_outbound_rows`는 수동 입력과 Excel 업로드 두 엔드포인트가 공유하는 단일 진입점이다.
처리 순서는 다음과 같다:

1. **정규화 + 중복 합산 (설계 결정 C, REQ-OUTBOUND-007)**: 입력받은 원시 행 목록을
   `(order_name, sku)` 키로 그룹화하고, 같은 키를 가진 모든 행의 `total` 값을 합산해 키당 결과
   행 1개로 축약한다. `UploadRackNumberView`의 dedup 패턴(last-row-wins)과 달리, 이 SPEC은
   합산(sum) 방식을 사용한다.
2. **Order 매칭 (REQ-OUTBOUND-003)**: 각 그룹의 `order_name`으로 `Order.name` 정확 일치 조회.
   매칭 실패 시 해당 그룹을 매칭 실패 목록에 추가하고 다음 그룹으로.
3. **LineItem 매칭 (REQ-OUTBOUND-004/005/005a, 설계 결정 A)**: 매칭된 Order와 그룹의 `sku`로
   LineItem을 조회. 0건이면 매칭 실패, 2건 이상이면 매칭 실패(분배 불가), 정확히 1건일 때만
   다음 단계로 진행.
4. **수량초과 판정 (REQ-OUTBOUND-009, 설계 결정 B)**: 매칭된 LineItem의 `quantity`가 null이면
   0으로 취급. `shipped_quantity + 합산된 total > quantity`(0으로 취급된 경우 포함)이면
   수량초과 목록에 추가하고 반영하지 않음.
5. **반영 및 상태 전이 (REQ-OUTBOUND-008/010/010a)**: 통과한 경우 `shipped_quantity`에 합산된
   `total`을 더하고 `shipped_at`을 현재 시각으로 갱신. 갱신 후 `shipped_quantity >= quantity`이면
   `logistics_status = "shipped"`로 설정, 아니면 `logistics_status`는 변경하지 않음.
6. **트랜잭션**: 전체 처리는 `transaction.atomic()`으로 감싸 원자성을 보장한다(`UploadRackNumberView`
   패턴 재사용, REQ-OUTBOUND-011/013).
7. **응답 구성 (REQ-OUTBOUND-014)**: `matched`/`unmatched`/`quantity_exceeded` 3개 리스트(각
   항목은 최소 order_name, sku, total, 그리고 unmatched의 경우 실패 사유를 식별 가능하게 포함)와
   각각의 count를 응답으로 반환.

두 뷰(`OutboundProcessView`, `UploadOutboundView`)는 이 함수에 입력을 공급하는 얇은 어댑터
역할만 수행한다 — `OutboundProcessView`는 요청 JSON body의 rows 리스트를 그대로 전달하고,
`UploadOutboundView`는 `parse_outbound_excel`의 반환값을 전달한다.

## 리스크 및 제약사항

**MySQL 마이그레이션 안전성**: `shipped_quantity`(default=0, NOT NULL)와 `shipped_at`(null=True)
은 기존 행에 안전한 기본값/NULL을 가지는 additive 컬럼 추가로, 데이터 백필이나 다운타임이
필요하지 않다. MySQL 8.0(RDS)의 InnoDB Instant ADD COLUMN(8.0.12+)으로 메타데이터 수준 처리
가능성이 높다 — `0034_lineitem_add_rack_number.py`가 이미 동일 패턴의 선례. 프로젝트 제약
("MySQL 스키마 마이그레이션 최소화")에 부합하며 인덱스 추가는 없다.

**기존 렉번호 페이지와의 하위 호환성**: `OutboundPage`는 `RackNumberPage`와 완전히 분리된 신규
디렉터리/라우트이며 `SearchTab.tsx`/`SummaryTab.tsx`/`rackNumberApi.ts`를 import하거나 수정하지
않는다. 백엔드도 신규 뷰 2개 + 신규 파서 1개로 격리되며 `UploadRackNumberView`/
`parse_rack_number_excel`은 참고만 하고 수정하지 않는다. 완료 조건: SPEC-ORDER-013(51
pytest + 15 프론트) / SPEC-ORDER-014(13 pytest + 26 프론트) 기존 테스트 전량 통과.

**동시성**: `_process_outbound_rows`는 `UploadRackNumberView`와 동일하게 락 없이 처리한다 —
두 사용자가 동시에 같은 LineItem을 출고 처리하는 race condition은 이번 SPEC에서 명시적으로
다루지 않는다(기존 관례와 동일). 실사용에서 문제가 확인되면 후속 SPEC에서 `select_for_update()`
검토.

**엔드포인트 네이밍**: `POST /api/purchase-orders/line-items/outbound-process/`(수동 입력),
`POST /api/purchase-orders/upload-outbound/`(Excel) — 기존 `upload-rack-number`/
`upload-vendor-shipment` 네이밍 관례를 따름.

## MX 태그 계획

- `backend/order/purchase_order_views.py`의 `_process_outbound_rows` — 신규 함수. `@MX:NOTE`로
  중복 행 합산(설계 결정 C) 및 null quantity=0 취급(설계 결정 B) 같은 비자명한 비즈니스 규칙의
  근거를 명시(REQ-OUTBOUND-007/009 참조). 호출자는 `OutboundProcessView`/`UploadOutboundView`
  2곳으로 fan_in=2이며 `@MX:ANCHOR` 임계치(fan_in>=3)에는 미달하므로 부여하지 않는다.
- 동일 함수의 락 없는 갱신 로직(리스크 섹션의 "동시성" 항목) — `@MX:WARN` + `@MX:REASON`으로
  두 사용자가 동시에 같은 LineItem을 처리할 때의 race condition 미해결 상태를 명시하고,
  `UploadRackNumberView`도 동일하게 락 없이 처리하는 기존 관례를 참조로 남긴다.
- `LineItem.shipped_quantity`/`shipped_at` 필드(models.py) — `@MX:NOTE`로 SPEC-ORDER-015 도입
  배경(logistics_status 파이프라인의 outbound_scheduled→shipped 전이를 위한 누적 수량/시각
  필드)을 남긴다.
- `parse_outbound_excel` — 신규 파서 함수, 기존 `parse_rack_number_excel` 대비 특이사항 없어
  MX 태그 불필요(단순 구조적 재사용).
- 구현(run) 단계에서 위 태그를 실제 코드에 부여하고, 필요 시 이 목록을 갱신한다.

## 관련 참조 구현

- `backend/order/purchase_order_views.py:2151-2254` `UploadRackNumberView` — Excel 업로드 뷰
  구조, 트랜잭션 처리, matched/skipped count 분리 응답 패턴.
- `backend/order/excel_utils.py:994-1083` `parse_rack_number_excel` — 헤더 자동탐색 패턴.
- `backend/order/urls.py:82-104` — SPEC-ORDER-013/014 URL 등록 블록, 정적 경로 우선 등록 관례.
- `frontend/src/services/rackNumberApi.ts`, `frontend/src/hooks/useRackNumberQueries.ts` —
  프론트엔드 서비스/훅 패턴.
