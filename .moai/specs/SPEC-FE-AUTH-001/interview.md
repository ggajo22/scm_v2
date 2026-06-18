# Interview: SPEC-FE-AUTH-001 프론트엔드 인증 UI

## Round 1: Scope

Question: 이번 프론트엔드 SPEC의 구현 범위를 선택해 주세요
Answer: 로그인 + 관리자 계정 관리 UI 전체

Question: 프레임워크 선택 — tech.md 기준 Vite 5.0+가 명시되어 있습니다
Answer: React + Vite 유지 (Recommended)

## Round 2: Constraints

Question: JWT 토큰 저장 위치를 선택해 주세요 (보안 vs 편의성 트레이드오프)
Answer: localStorage + memory 하이브리드 (Access Token: 메모리, Refresh Token: localStorage)

Question: Admin 역할 사용자 로그인 시 UI를 어떻게 처리할까요?
Answer: 메뉴 숨김 + 접근 차단 (Admin은 관리자 계정 관리 메뉴 숨김, URL 직접 접근 시 403 페이지)

## Clarity Score

Initial: 6/10
Final: 9/10
Rounds completed: 2
Early exit reason: Clarity >= 8 achieved after Round 2
