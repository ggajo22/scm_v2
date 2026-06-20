# Acceptance Criteria — SPEC-ETOILE-DASHBOARD-001

## 시나리오 1: 인증 없이 요청
- **Given**: JWT 토큰 없이 `GET /api/book/etoile/dashboard/` 요청
- **Then**: HTTP 401 반환

## 시나리오 2: 정상 응답 구조
- **Given**: 유효한 JWT 토큰으로 `GET /api/book/etoile/dashboard/` 요청
- **Then**: HTTP 200, `status_counts` 배열 + `total` 정수 반환

## 시나리오 3: status_counts 집계 정확성
- **Given**: DB에 status=0 레코드 50개, status=80 레코드 30개, status=null 레코드 3개
- **Then**: `status_counts`에 3개 항목, `total=83` 반환

## 시나리오 4: 레이블 매핑
- **Given**: status=0인 레코드 존재
- **Then**: 해당 항목 `label: "리스팅 준비"` 반환

## 시나리오 5: 미정의 상태 레이블
- **Given**: status=99 (정의 외) 레코드 존재
- **Then**: 해당 항목 `label: "정의되지 않은 상태"` 반환

## 시나리오 6: null status 레이블
- **Given**: status=null 레코드 존재
- **Then**: 해당 항목 `label: "상태 없음"`, 테이블 맨 하단 표시

## 시나리오 7: 사이드바 항목
- **Given**: 인증된 사용자가 사이드바를 봄
- **Then**: "도서관리" 그룹 내 "Etoile 현황" 링크가 `/books/etoile`로 존재

## 시나리오 8: 활성 상태
- **Given**: 현재 경로가 `/books/etoile`
- **Then**: "Etoile 현황" 링크만 `aria-current="page"`, 다른 항목은 없음

## 시나리오 9: 로딩 상태
- **Given**: API 호출 진행 중
- **Then**: 로딩 스켈레톤 표시, 테이블 미노출

## 시나리오 10: 에러 상태
- **Given**: API 호출 실패
- **Then**: 에러 메시지 표시

## 시나리오 11: 전체 건수 요약
- **Given**: `total: 83` 응답
- **Then**: "전체 83개" 카드 표시

## 시나리오 12: 정렬 순서
- **Given**: status=-1, 0, 12, 80, null 레코드 혼재
- **Then**: -1 → 0 → 12 → 80 → null 순서로 표시
