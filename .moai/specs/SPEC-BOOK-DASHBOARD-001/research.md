# Dashboard API + Frontend Research

**Date**: 2026-06-19  
**Status**: Complete  

---

## 1. LEGACY ANALYSIS

### 1.1 Source
- **File**: C:/app/scm/main/book/views.py (lines 1017-1073)
- **Function**: index(request)
- **Metrics**: 8 total

### 1.2 Constants
**STATUS_LABELS**: 28 status codes (5-326)
- Image processing: 30-38
- Error states: 31-32, 41-44
- Completed listings: 80-82
- Other: 0-6, 12-15, 91-121, 205-326

**ERROR_STATUSES**: [31, 32, 41, 42, 43, 44]
**WAITING_STATUSES**: [0, 1, 5, 6, 14, 15, 16]

### 1.3 Metrics (8)

1. status_counts: Inven grouped by status_of_shopify
2. shopify_created_24h: Shopify_product in last 24h
3. error_total: Inven count with error status
4. error_rows: Filtered status_counts for errors
5. waiting_total: Inven count with waiting status
6. unresolved_note_count: BookNote GENERAL unresolved
7. sale_zero_count: Info price_sale=0 where Inven status in [80,81,82]
8. cost_zero_count: Info price=0 AND kyobo_supply_price=0 where status [80,81,82]

---

## 2. BACKEND MODELS

**Inven** (models.py 6-32)
- status_of_shopify (SmallIntegerField, db_index)
- created_at (DateTimeField, auto_now_add)

**Info** (models.py 35-80)
- inven (OneToOneField FK)
- price_sale, price, kyobo_supply_price (all indexed)

**Shopify_product** (models.py 83-92)
- inven (ForeignKey)
- created_at (DateTimeField, auto_now_add)

**BookNote** (models.py 118-139)
- note_type (CharField ["GENERAL", "SHIPPING"])
- is_resolved (BooleanField)
- db_table: 'book_note'

---

## 3. BACKEND API

### 3.1 Config (config/settings/base.py)

REST_FRAMEWORK:
- Authentication: JWTAuthentication
- Permission: IsAuthenticated

SIMPLE_JWT:
- ACCESS_TOKEN: 15 minutes
- REFRESH_TOKEN: 24 hours
- Role NOT in JWT (always read from DB)

### 3.2 Patterns

Endpoints: /api/auth/*, /api/admin/users/*
Views: APIView or ModelViewSet
Serializers: ModelSerializer or plain Serializer
Permissions: IsSuperAdmin or IsAuthenticated

---

## 4. FRONTEND

### 4.1 Stack
- React 19 + React Router 7 + Vite
- State: Zustand (authStore)
- HTTP: axios + TanStack Query 5
- UI: shadcn/ui + Tailwind 4
- Forms: React Hook Form + Zod
- Testing: Vitest + React Testing Library

### 4.2 HTTP Client (src/lib/axios.ts)

```
api = axios.create({
  baseURL: '' (Vite proxy: /api -> localhost:8000)
})

Request interceptor: Adds Bearer token
Response interceptor: Handles 401 with token refresh
```

### 4.3 React Query Pattern

**useAdminUsers**:
```
useQuery({
  queryKey: ['admin-users'],
  queryFn: () => api.get('/api/admin/users/')
})
```

**Mutations**:
```
useMutation({
  mutationFn: (payload) => api.post(...),
  onSuccess: () => invalidateQueries([...])
})
```

### 4.4 Auth Store (src/store/authStore.ts)

```
accessToken: memory only
refreshToken: localStorage ('scm_refresh_token')
restoreSession: Called at app init
login/logout: Updates state and token
```

### 4.5 Current DashboardPage

File: src/pages/DashboardPage.tsx (8 lines)
- Placeholder with title and welcome message
- Test expects title to render

---

## 5. API DESIGN

### 5.1 Endpoint

```
GET /api/book/dashboard/metrics/
Auth: Bearer token (IsAuthenticated)
Response: 200 OK
```

### 5.2 Response

```json
{
  "status_counts": [
    {"status": int, "label": string, "count": int}
  ],
  "shopify_created_24h": int,
  "error_total": int,
  "error_rows": [...],
  "waiting_total": int,
  "unresolved_note_count": int,
  "sale_zero_count": int,
  "cost_zero_count": int
}
```

---

## 6. IMPLEMENTATION

### 6.1 Backend (5 files)

1. **book/constants.py** (CREATE)
   - STATUS_LABELS, ERROR_STATUSES, WAITING_STATUSES

2. **book/serializers.py** (CREATE)
   - StatusCountSerializer
   - DashboardMetricsSerializer

3. **book/views.py** (CREATE)
   - DashboardMetricsView (APIView.get)

4. **book/urls.py** (CREATE)
   - path("book/dashboard/metrics/", DashboardMetricsView)

5. **config/urls.py** (MODIFY)
   - path("api/", include("book.urls"))

### 6.2 Frontend (4 files)

1. **features/book/hooks/useDashboardMetrics.ts** (CREATE)
   - useDashboardMetrics hook
   - DASHBOARD_METRICS_QUERY_KEY
   - DashboardMetrics interface

2. **types/book.ts** (CREATE)
   - StatusCount interface
   - DashboardMetrics interface

3. **pages/DashboardPage.tsx** (MODIFY)
   - Replace placeholder with metric cards/tables
   - Call useDashboardMetrics
   - Handle loading/error states

4. **pages/DashboardPage.test.tsx** (MODIFY)
   - Mock useDashboardMetrics
   - Test loading, error, data states

---

## 7. QUERIES

### Efficiency

status_counts: Aggregation with indexed field (GOOD)
shopify_created_24h: Filter + date index (GOOD)
error_total, waiting_total: Filter + indexed status (GOOD)
unresolved_note_count: NO index on note_type/is_resolved (MEDIUM RISK)
Info Exists: Indexed price fields (GOOD)

### Risk

BookNote query could be slow if note count grows. Monitor in real usage.

Mitigation: Add index if needed:
```python
indexes = [models.Index(fields=["note_type", "is_resolved"])]
```

---

## 8. CHANGES

**Backend**: 5 files (4 CREATE, 1 MODIFY)
**Frontend**: 4 files (2 CREATE, 2 MODIFY)
**Total**: 9 files

---

## 9. RISKS

- ✓ All models exist
- ✓ All fields present
- ✓ No migrations needed
- Constants not ported: CREATE constants.py
- BookNote no index: Monitor, add if needed
- Vite proxy required during dev

---

**Research Complete**
