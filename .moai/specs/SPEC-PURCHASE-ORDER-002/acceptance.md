# 인수 조건 — SPEC-PURCHASE-ORDER-002

## AC-01: 복수 SKU 선택 시 수량 합산 표시
- **Given** 미발주 현황 탭에 아이템이 로드됨
- **When** quantity가 각각 50, 30인 SKU 2개를 체크
- **Then** "2건 선택됨 / 수량 80개 선택됨" 표시

## AC-02: 단일 SKU 선택
- **When** quantity 100인 SKU 1개 선택
- **Then** "1건 선택됨 / 수량 100개 선택됨" 표시

## AC-03: 전체 선택
- **When** 전체 선택 체크박스 클릭
- **Then** 전체 행 수와 quantity 합산 값 표시

## AC-04: 선택 초기화
- **When** 모든 체크 해제
- **Then** "항목을 선택하세요" 표시 (수량 정보 없음)
