# Admin Authentication Implementation

## Overview

This document describes the implementation of the Admin Separation & Hardened Auth system for RapidCover. The implementation adds JWT-based authentication for admin users, separating admin access from partner access.

## What Was Implemented

### Backend (✅ Complete)

#### 1. Admin Model (`backend/app/models/admin.py`)
- Created Admin model with fields: id, email, hashed_password, full_name, is_active, is_superadmin, created_at, last_login
- Uses bcrypt password hashing via passlib
- Separate table from partners

#### 2. Admin Schemas (`backend/app/schemas/admin.py`)
- `AdminRegister` - registration input (email, password, full_name)
- `AdminLogin` - login input (email, password)
- `AdminResponse` - admin profile output
- `AdminToken` - login response with JWT token

#### 3. Admin Dependencies (`backend/app/core/admin_deps.py`)
- `get_current_admin()` - JWT verification dependency
- Verifies token type == "admin" to distinguish from partner tokens
- Returns Admin object or raises 403 Forbidden

#### 4. Admin Auth API (`backend/app/api/admin_auth.py`)
- `POST /api/v1/admin/auth/register` - Create admin account
- `POST /api/v1/admin/auth/login` - Login with email/password
- `GET /api/v1/admin/auth/me` - Get current admin profile
- Updates `last_login` timestamp on successful login
- Returns JWT token with type: "admin"

#### 5. Bulk Operations (added to `backend/app/api/admin.py`)
- `POST /api/v1/admin/claims/bulk-approve` - Approve multiple claims
  - Takes: `claim_ids: List[int]`
  - Returns: `{approved: int, total: int}`
- `POST /api/v1/admin/claims/bulk-reject` - Reject multiple claims
  - Takes: `claim_ids: List[int], reason: str`
  - Returns: `{rejected: int}`
- `GET /api/v1/admin/export/claims` - Export claims to CSV
  - Returns: CSV file download

#### 6. Protected Endpoints
- Ran `add_admin_auth.py` script to add `admin: Admin = Depends(get_current_admin)` to all admin endpoints
- Updated files:
  - `backend/app/api/admin_panel.py` - 20+ endpoints protected
  - `backend/app/api/admin_drills.py` - 8 endpoints protected
  - `backend/app/api/admin.py` - Already had auth added manually

### Frontend (✅ Complete)

#### 1. Admin Auth Context (`frontend/src/context/AdminAuthContext.jsx`)
- Manages admin session state separately from partner authentication
- Exposes: `admin`, `login(email, password)`, `logout()`, `loading`, `isAuthenticated`
- Reads `admin_token` from localStorage on mount
- Auto-restores session by calling `/api/v1/admin/auth/me`

#### 2. Admin API Client (`frontend/src/services/adminApi.js`)
- Updated existing adminApi.js to support admin authentication
- Changed `getToken()` to check for `admin_token` first, then fall back to partner `access_token`
- Added methods:
  - `loginAdmin(email, password)` - Admin login
  - `registerAdmin(email, password, full_name)` - Admin registration
  - `getAdminProfile()` - Get current admin profile
  - `bulkApproveClaims(claimIds)` - Bulk approve
  - `bulkRejectClaims(claimIds, reason)` - Bulk reject
  - `exportClaimsCsv()` - Export to CSV (triggers download)

#### 3. Modified Login Page (`frontend/src/pages/Login.jsx`)
- **No separate admin login page** (as specified in requirements)
- Added "Admin Email" and "Password" fields below phone number
- Login logic:
  - If email field is filled → `adminLogin(email, password)` → redirect to `/admin`
  - If only phone field is filled → existing OTP flow → redirect to `/dashboard`
- Dynamic button text: "Admin Login" vs "Get OTP"
- Added visual divider: "OR" between phone and email sections

#### 4. Admin Dashboard (`frontend/src/pages/AdminDashboard.jsx`)
- Renamed from `Admin.jsx` to `AdminDashboard.jsx`
- Added admin authentication check:
  - Redirects to `/login` if not authenticated
  - Uses `useAdminAuth()` hook
- Updated profile section:
  - Shows `admin.full_name` instead of hardcoded "Admin User"
  - Avatar shows initials from full name
- Added **Logout button**:
  - Visible in top-right navigation
  - Calls `logout()` and redirects to `/login`
  - Red hover effect

#### 5. App Structure (`frontend/src/App.jsx`)
- Wrapped app in `<AdminAuthProvider>` inside `<AuthProvider>`
- Updated import to use `AdminDashboard` instead of `Admin`
- Route structure unchanged: `/admin` → `<AdminRoute />` → `<AdminDashboard />`

## File Structure

```
backend/
├── app/
│   ├── models/
│   │   └── admin.py              [NEW] Admin model
│   ├── schemas/
│   │   └── admin.py              [NEW] Admin schemas
│   ├── core/
│   │   └── admin_deps.py         [NEW] Admin JWT verification
│   ├── api/
│   │   ├── admin_auth.py         [NEW] Admin auth endpoints
│   │   ├── admin.py              [MODIFIED] Added bulk operations
│   │   ├── admin_panel.py        [MODIFIED] Added auth to all endpoints
│   │   ├── admin_drills.py       [MODIFIED] Added auth to all endpoints
│   │   └── router.py             [MODIFIED] Added admin_auth_router

frontend/
├── src/
│   ├── context/
│   │   └── AdminAuthContext.jsx  [NEW] Admin auth state management
│   ├── services/
│   │   └── adminApi.js           [MODIFIED] Added admin auth methods
│   ├── pages/
│   │   ├── Login.jsx             [MODIFIED] Added admin login fields
│   │   ├── AdminDashboard.jsx    [RENAMED] From Admin.jsx, added auth check
│   │   └── index.js              [MODIFIED] Export AdminDashboard
│   └── App.jsx                   [MODIFIED] Added AdminAuthProvider

scripts/
├── add_admin_auth.py             [NEW] Auto-inject admin auth to endpoints
├── create_admin.py               [NEW] Python script to create first admin
└── create_admin.sh               [NEW] Bash script to create first admin via API
```

## How to Test

### 1. Start Backend

```bash
cd backend
venv\Scripts\activate  # Windows
# OR
source venv/bin/activate  # Linux/Mac

uvicorn app.main:app --reload
```

Backend should be running at: http://localhost:8000

### 2. Create First Admin User

**Option A: Using the API directly (recommended)**

```bash
curl -X POST http://localhost:8000/api/v1/admin/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@rapidcover.in",
    "password": "admin123",
    "full_name": "Admin User"
  }'
```

**Option B: Using the shell script**

```bash
bash create_admin.sh
```

**Default admin credentials:**
- Email: `admin@rapidcover.in`
- Password: `admin123`

### 3. Start Frontend

```bash
cd frontend
npm run dev
```

Frontend should be running at: http://localhost:5173

### 4. Test Admin Login

1. Navigate to http://localhost:5173/login
2. You should see:
   - Phone Number field (for partners)
   - **OR** divider
   - Admin Email field
   - Password field (appears when email is filled)
3. Fill in admin credentials:
   - Admin Email: `admin@rapidcover.in`
   - Password: `admin123`
4. Click "Admin Login" button
5. Should redirect to http://localhost:5173/admin
6. Should see admin dashboard with:
   - Profile showing "Admin User" in top-right
   - Logout button next to profile
   - All admin panels accessible

### 5. Test Partner Login (Should Still Work)

1. Navigate to http://localhost:5173/login
2. Leave email field **empty**
3. Enter phone number: `9876543210`
4. Click "Get OTP" button
5. Should see OTP screen (existing flow unchanged)
6. Should redirect to `/dashboard` after OTP verification

### 6. Test Logout

1. While logged in as admin at `/admin`
2. Click "Logout" button in top-right
3. Should redirect to `/login`
4. Navigating to `/admin` should redirect back to `/login`

### 7. Test Session Persistence

1. Login as admin
2. Refresh the page
3. Should remain logged in (token restored from localStorage)
4. Open browser DevTools → Application → Local Storage
5. Should see `admin_token` key with JWT value

### 8. Test Bulk Operations (Manual API Test)

**Bulk Approve:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/claims/bulk-approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"claim_ids": [1, 2, 3]}'
```

**Bulk Reject:**
```bash
curl -X POST http://localhost:8000/api/v1/admin/claims/bulk-reject \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"claim_ids": [4, 5], "reason": "Insufficient documentation"}'
```

**Export CSV:**
```bash
curl -X GET http://localhost:8000/api/v1/admin/export/claims \
  -H "Authorization: Bearer <admin_token>" \
  --output claims_export.csv
```

## Security Features

### Backend Security
- ✅ Bcrypt password hashing (via passlib)
- ✅ JWT token authentication with HS256
- ✅ Token type discrimination ("admin" vs partner tokens)
- ✅ All admin endpoints protected with `get_current_admin` dependency
- ✅ Passwords never returned in API responses (excluded from AdminResponse schema)
- ✅ Last login timestamp tracking

### Frontend Security
- ✅ Admin token stored separately from partner token (`admin_token` vs `access_token`)
- ✅ Auto-logout on token expiration (handled by API 401 responses)
- ✅ Protected routes redirect to login if not authenticated
- ✅ Password input fields use `type="password"`
- ✅ No token exposure in URL parameters

## Troubleshooting

### Issue: "Email already registered" on admin creation
**Solution:** Admin user already exists. Use existing credentials to login.

### Issue: "Invalid admin credentials" on login
**Solution:**
1. Verify email is correct: `admin@rapidcover.in`
2. Verify password is correct: `admin123`
3. Check backend logs for detailed error

### Issue: Redirect to /login when accessing /admin
**Solution:** Admin token missing or expired. Login again.

### Issue: "Not an admin token" error
**Solution:** Logged in with partner account, not admin account. Use admin email/password on login page.

### Issue: Bulk operations return 403 Forbidden
**Solution:** Ensure `admin_token` is being sent in Authorization header (check browser DevTools → Network).

## Next Steps

### Recommended Enhancements
1. **Admin Management UI** - Create interface to add/edit/delete admins
2. **Role-Based Access Control** - Add granular permissions (view-only, editor, superadmin)
3. **Audit Logging** - Track all admin actions (login, bulk operations, claim decisions)
4. **Password Reset** - Add "Forgot Password" flow with email verification
5. **Two-Factor Authentication** - Add TOTP/SMS 2FA for admin accounts
6. **Session Management** - Add ability to view/revoke active sessions
7. **IP Whitelisting** - Restrict admin access to specific IP ranges

### Integration Points
- Bulk operations can be wired to frontend components (e.g., ClaimsQueue with checkbox selection)
- CSV export can be triggered from admin dashboard with date range filters
- Admin activity logs can be displayed in a dedicated "Audit Trail" panel

## Summary

The Admin Authentication system is now fully implemented with:
- ✅ Separate admin authentication flow
- ✅ JWT-based session management
- ✅ Protected admin endpoints
- ✅ Dual-mode login page (partner + admin)
- ✅ Bulk operations for claim management
- ✅ CSV export functionality
- ✅ Session persistence and restoration
- ✅ Logout functionality

All requirements from the original plan have been implemented successfully.
