# SPEC-ORDER-003 구현 계획

## 구현 범위 요약

백엔드 1개 엔드포인트 + 프론트엔드 1개 페이지로 구성되는 읽기 전용 주문 상세 기능이다.
기존 모델 변경 없이 Serializer, View, URL 등록, TypeScript 타입, 훅, 라우트, 컴포넌트를 추가한다.

---

## 마일스톤

### Priority High — 백엔드

**M1. Serializer 구현**
- `OrderDetailSerializer` 및 중첩 Serializer 작성
- 대상 파일: `backend/order/serializers.py`
- 포함 항목: `ShippingAddressSerializer`, `LineItemSerializer`, `ShippingLineSerializer`, `RefundSerializer`

**M2. View 및 URL 등록**
- `OrderDetailView(RetrieveAPIView)` 작성
- `orders/<int:pk>/` URL 패턴 등록
- 대상 파일: `backend/order/views.py`, `backend/order/urls.py`

**M3. 백엔드 테스트**
- 200 응답 및 필드 검증
- 404 응답 검증
- 미인증 접근 403 검증

### Priority High — 프론트엔드

**M4. TypeScript 타입 정의**
- `OrderDetail`, `LineItemDetail`, `ShippingAddress`, `ShippingLine`, `Refund` 인터페이스 추가
- 기존 `Order` 타입 확장

**M5. useOrderDetail 훅**
- `useOrderDetail(id: number)` 구현
- TanStack Query v5 패턴 준수

**M6. 라우트 등록 및 주문 목록 클릭 이벤트**
- `/orders/$id` 라우트 추가
- `OrdersPage` 행 클릭 시 네비게이션 추가

**M7. OrderDetailPage 컴포넌트**
- 헤더, 6개 섹션 레이아웃 구현
- 스켈레톤 로딩, 에러, 404 상태 처리

---

## 기술적 접근

### 백엔드 Serializer 설계

```
OrderDetailSerializer
├── CustomerSerializer (기존 패턴 참조 또는 신규)
├── ShippingAddressSerializer (신규)
├── LineItemSerializer (신규)
├── ShippingLineSerializer (신규)
└── RefundSerializer (신규)
```

`many=True` 중첩 Serializer를 사용하며, `source` 파라미터로 ORM 역참조(`shipping_lines`, `refunds`, `line_items`)를 연결한다.

### 프론트엔드 데이터 흐름

```
OrdersPage (row click)
  → navigate('/orders/{id}')
  → OrderDetailPage
    → useOrderDetail(id)
      → GET /api/orders/{id}/
        → OrderDetail 데이터
    → 6개 섹션 렌더링
```

### 스켈레톤 UI 전략

데이터 로딩 중에는 각 섹션 카드의 콘텐츠를 `animate-pulse` Tailwind 클래스를 사용한 회색 블록으로 대체한다.

---

## 위험 요소 및 완화 방안

| 위험 | 완화 방안 |
|------|-----------|
| `refunds`가 Order 모델에서 역참조 이름이 다를 수 있음 | Django ORM 관계 확인 후 `related_name` 또는 `source` 파라미터 조정 |
| `shipping_lines`가 별도 모델로 연결될 경우 | `ShippingLine` 모델의 FK 관계 확인 후 `source` 설정 |
| 기존 `OrdersPage` 행 클릭 이벤트가 다른 인터랙션과 충돌 | 행의 `onClick`만 추가하고 기존 체크박스/버튼 이벤트는 `stopPropagation` 처리 |
| 고객이 없는 주문(guest checkout) 처리 | `customer` 필드를 nullable로 정의하고 프론트엔드에서 null 체크 |

---

## 정의 완료 (Definition of Done)

- [ ] `GET /api/orders/{id}/` 200 응답 반환
- [ ] `GET /api/orders/{id}/` (존재하지 않는 ID) 404 반환
- [ ] 주문 목록 행 클릭 시 `/orders/{id}` 네비게이션 동작
- [ ] `OrderDetailPage` 6개 섹션 정상 렌더링
- [ ] `has_refund: false`인 주문에서 환불 섹션 미표시
- [ ] 로딩 스켈레톤 표시
- [ ] 에러 상태 메시지 + 재시도 버튼 표시
- [ ] 404 상태 메시지 + 목록 돌아가기 링크 표시
- [ ] 백엔드 테스트 통과
