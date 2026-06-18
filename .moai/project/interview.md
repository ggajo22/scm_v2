# Project Interview

## Round 1: Vision
Question: 이 프로젝트는 무엇을 하는 시스템인가요?
Answer: 웹 애플리케이션 — Shopify를 통해 도서를 판매하는 비즈니스의 관리자 전용 웹 애플리케이션. 도서 리스팅 상태와 주문을 관리하며, 50만 건의 데이터를 다루고 속도가 중요한 시스템.

## Round 2: Technology
Question: 주요 기술 스택은 무엇인가요?
Answer: Django (백엔드, 기존 경험 보유) + React/TypeScript (프론트엔드, 대용량 테이블 UX) + MySQL RDS (기존 AWS RDS 유지, 비용 절감) + Celery + Redis (Shopify API 비동기 동기화)

## Round 3: Scope
Question: 핵심 기능과 우선순위는 무엇인가요?
Answer: 핵심 기능 3가지 — (1) Shopify API 주문 동기화: 배치 + 웹훅 기반 실시간 동기화, (2) 도서 리스팅 상태 관리: 재고/가격/노출 여부 관리, (3) 주문 목록 조회/상태 관리: 50만 건 대용량 데이터 처리. 통계 대시보드, 재고 발주 관리는 1차 범위 외.

## Additional Context
- Shopify를 통한 도서 판매 비즈니스
- 총 50만 건 데이터 (도서 리스팅 + 주문)
- 기존 Django 개발 경험 보유
- AWS RDS MySQL 사용 중 (기존 인스턴스 유지)
- 관리자 전용 시스템 (일반 사용자 없음)
- 속도/성능이 핵심 요구사항
