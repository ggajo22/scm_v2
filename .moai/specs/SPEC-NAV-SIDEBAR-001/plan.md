---
id: SPEC-NAV-SIDEBAR-001
document: plan
version: 1.0.0
updated: 2026-06-20
---

# 구현 계획: SPEC-NAV-SIDEBAR-001

## 구현 접근법

`Sidebar.tsx`의 데이터 구조를 플랫 배열에서 **그룹 기반 구조**로 전환한다. 기존 역할(role) 필터링 로직은 보존하되, 렌더링 로직은 그룹 헤더 + 하위 항목 패턴으로 교체한다.

---

## 마일스톤

### Priority High

1. **`Sidebar.tsx` 데이터 구조 변경**
   - `NavItem` 인터페이스를 `NavGroup`(그룹 헤더 + 하위 항목 배열) 구조로 교체하거나 병행 정의
   - `navItems` 배열을 그룹화된 구조로 재정의

2. **`Sidebar.tsx` 렌더링 로직 변경**
   - 그룹 헤더: 클릭 불가, `role="group"`, `aria-label` 포함
   - 하위 항목: 들여쓰기 적용, `Link` 컴포넌트 사용
   - `useLocation`으로 현재 경로 감지 → 완전 일치로 활성 스타일 적용

3. **역할 필터링 유지**
   - "관리자 계정 관리"는 `super_admin`만 노출되는 로직 그대로 유지

### Priority Medium

4. **`Sidebar.test.tsx` 업데이트**
   - 기존 테스트를 새 구조에 맞게 수정
   - 신규 테스트 추가: 그룹 헤더 표시, 하위 항목 링크, 활성 상태 정확성, 역할별 노출

---

## 기술 접근법

### 데이터 구조 설계

```
NavGroup (그룹)
  └── label: string          (그룹 헤더 레이블)
  └── icon: ComponentType    (그룹 아이콘)
  └── items: NavSubItem[]    (하위 항목 배열)
  └── roles?: string[]       (그룹 자체 역할 제한, 선택적)

NavSubItem (하위 항목)
  └── label: string
  └── href: string
  └── roles?: string[]
```

"관리자 계정 관리"는 하위 항목이 없는 단독 플랫 항목이므로 별도 타입 또는 `items` 배열 없이 처리하는 방안 중 구현 시 선택.

### 활성 상태 판별

`useLocation().pathname`과 `href`를 완전 일치(`pathname === href`)로 비교. React Router의 `NavLink` 컴포넌트 사용 시 `end` prop으로 처리 가능.

---

## 리스크

| 리스크 | 영향도 | 완화 방안 |
|--------|--------|-----------|
| 기존 테스트 일괄 실패 | Medium | 테스트를 새 구조에 맞게 먼저 업데이트 후 구현 |
| `useLocation` 미사용 시 활성 상태 오판 | Low | `NavLink`의 `end` prop 또는 `===` 완전 일치 사용 |
| 그룹 헤더에 클릭 이벤트 잔류 | Low | `button` 대신 `div`/`span` 사용, `tabIndex=-1` 또는 aria-hidden 검토 |
