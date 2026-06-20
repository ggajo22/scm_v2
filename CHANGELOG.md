# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### SPEC-BOOK-EDIT-001: 도서 정보 수정 화면
- 도서 상세 정보 조회 엔드포인트 (`GET /api/book/{id}/`)
  - Inven, Info, BookNote, Shopify 상품, Etoile 정보 통합 조회
  - 미해결 노트 전체 + 최근 해결 노트 10건 포함
- 도서 기본 정보 수정 엔드포인트 (`PATCH /api/book/{id}/info/`)
  - 선택적 필드 업데이트 (partial update)
  - 기본, 부클, 교보, 중량, 장문 텍스트 필드 지원
- 노트 관리 엔드포인트
  - 노트 생성 (`POST /api/book/{id}/notes/`)
  - 노트 완료 처리 (`PATCH /api/book/notes/{note_id}/resolve/`)
- Shopify 상태 변경 엔드포인트
  - 본관 상태 변경 (`PATCH /api/book/{id}/shopify-status/`)
  - Etoile 상태 변경 (`PATCH /api/book/{id}/etoile-shopify-status/`)
- Etoile 태그 관리 엔드포인트 (`PATCH /api/book/{id}/etoile-tags/`)
- React 기반 도서 수정 화면 (`BookDetailPage`)
  - 탭 기반 섹션 구분 (기본 정보, 노트, Shopify, Etoile)
  - 실시간 필드 검증
  - 인라인 성공/오류 피드백 (토스트)
  - Etoile 섹션 조건부 표시
- 데이터베이스 마이그레이션
  - Info.name 전문 검색 인덱스 추가 (FULLTEXT NGRAM)

### Security

- 모든 도서 수정 API에 JWT 인증 적용 (`IsAuthenticated`)
- 노트 생성 시 작성자 자동 기록 (`created_by`)
- Shopify API 호출 실패 시 DB 상태 미변경 보장

### Fixed

- 한국어 도서명 검색 정확도 개선 (FULLTEXT NGRAM 인덱스)

## [0.1.0] - 2026-06-20

### Added

#### SPEC-BOOK-SEARCH-001: 도서 검색 기능
- ISBN 및 제목 검색 엔드포인트 (`GET /api/book/search/`)
- 페이지네이션 (50건/페이지)
- 한국어 전문 검색 지원 (FULLTEXT MATCH AGAINST)

#### SPEC-AUTH-001: 관리자 인증 및 RBAC
- JWT 기반 인증 (Access Token + Refresh Token)
- 2단계 RBAC (SuperAdmin, Admin)
- 토큰 블랙리스트 (로그아웃 및 계정 비활성화)
- 관리자 계정 관리 API

### Performance

- N+1 쿼리 최적화 (`select_related`)
- 도서 검색 인덱스 추가

### Infrastructure

- Django 5.2 LTS 기반 백엔드
- React 19 기반 프론트엔드
- MySQL RDS 데이터베이스
- JWT 기반 인증 시스템
