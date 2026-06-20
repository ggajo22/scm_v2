---
name: project-fe-auth-001
description: SPEC-FE-AUTH-001 React/TypeScript 인증 UI 구현 현황 및 기술 결정사항
metadata:
  type: project
---

SPEC-FE-AUTH-001 프론트엔드 인증 UI를 TDD로 구현 완료 (2026-06-18).

**구현 결과**: 54개 테스트 통과, 커버리지 80%+ 달성, 빌드 성공

## 기술 스택 결정사항

- Vite v5 (v8은 Windows에서 rolldown 바이너리 미지원으로 동작 불가)
- vitest v2 (v3/v4는 rolldown 의존으로 Windows Git Bash 환경에서 불가)
- happy-dom (jsdom v27은 @csstools/css-calc ESM 모듈 require 충돌)
- Tailwind CSS v4 (@tailwindcss/vite 플러그인 방식, tailwind.config.ts 불필요)
- shadcn/ui 컴포넌트 수동 생성 (npx shadcn init이 Git Bash에서 실패)
- `@hookform/resolvers` 별도 설치 필요

## 중요 패턴

- Zustand selector mock: `useAuthStore(selector => selector(state))` 형식으로 mock 구성 필요
- vitest.config.ts를 vite.config.ts와 분리 (vite 빌드에서 test 필드 오류)
- tsconfig.app.json에 `ignoreDeprecations: "6.0"` 추가 (baseUrl deprecation)
- Zod v4 enum: `z.enum(['a', 'b'] as const, { message: '...' })` 형식

**Why:** Windows 환경에서 최신 버전들이 네이티브 바이너리 의존성 문제로 실패함.
**How to apply:** 향후 Windows Git Bash 환경 프로젝트에서 동일한 버전 제약 적용.
