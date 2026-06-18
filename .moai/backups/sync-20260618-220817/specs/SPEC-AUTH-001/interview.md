# Interview: SPEC-AUTH-001 관리자 인증 및 권한 관리

## Clarity Score
Initial: 2/10
Final: 7/10
Rounds completed: 2 + 1 clarification

## Round 0: 권한 모델 (명확도 향상 질문)
Question: 권한 관리 모델을 명확히 해주세요. 이 부분이 SPEC 설계에 가장 큰 영향을 줍니다.
Answer: 역할 분리 2단계 — 슈퍼관리자 vs 관리자

## Round 1: 역할 범위
Question: 슈퍼관리자 vs 관리자의 차이는 무엇인가요?
Answer: 관리자 추가/삭제는 슈퍼관리자만 — 슈퍼관리자: 모든 기능 + 관리자 계정 관리(CRUD). 관리자: 도서 리스팅/주문 관리 가능, 유저 계정 생성 불가.

## Round 2: 로그인 방식
Question: 로그인 방식과 보안 제약을 확인해 주세요.
Answer: 아이디(username) + 비밀번호로 로그인. 이메일 기반 비밀번호 리셋 없음. 슈퍼관리자가 직접 다른 관리자의 비밀번호를 리셋. JWT Access Token(15분) + Refresh Token(24시간).

## Confirmed Requirements Summary
- Login method: username + password (NOT email)
- Auth: JWT — Access Token 15min, Refresh Token 24h
- Password reset: SuperAdmin manually resets for other admins (no email flow)
- Roles:
  - SuperAdmin: ALL features + admin account CRUD (create/update/delete/list admins)
  - Admin: book listings + order management ONLY (no access to user management)
- Scope: admin-only system (no public user accounts)
- Out of scope: social login, MFA, email verification, audit log (v1)
