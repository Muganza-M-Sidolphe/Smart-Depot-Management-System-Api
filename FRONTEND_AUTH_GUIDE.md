# Frontend Authentication Guide

How to connect the frontend to the Smart Depot API now that it requires login
and role-based access. Follow this in your **frontend** project (React / Vue /
plain JS) — none of this changes the backend.

---

## 1. The short version

1. The user logs in → the API returns an **`accessToken`**.
2. Store that token.
3. Send it as a header on **every** other API request:
   ```
   Authorization: Bearer <accessToken>
   ```
4. If a request returns **401**, the token is missing/expired → send the user back to login.
5. If a request returns **403**, the user is logged in but their **role** isn't allowed to do that action.

If you skip step 3, every protected request fails with:
```json
{ "detail": "Could not validate credentials" }
```

---

## 2. Endpoints you need

Base URL (local): `http://127.0.0.1:8000/api/v1`

### Public (no token required)
| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/signup` | `{ name, email, password, role, phone? }` | `{ accessToken, tokenType, user }` |
| POST | `/auth/login` | `{ email, password }` | `{ accessToken, tokenType, user }` |
| GET | `/health` | — | `{ status: "ok" }` |

### Requires token
| Method | Path | Notes |
|---|---|---|
| GET | `/auth/me` | Returns the current logged-in user |
| POST | `/auth/logout` | Revokes the current token (see §10) |
| GET/POST/PATCH/DELETE | everything else (`/products`, `/customers`, `/sales`, …) | Token required; writes also require a role (see §5) |

### Example login response
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "user": {
    "id": 1,
    "name": "Admin User",
    "email": "admin@smartdepot.rw",
    "role": "owner",
    "phone": "+250788000000",
    "status": "active",
    "createdAt": "2026-06-30T10:00:00"
  }
}
```

> Note: all request/response fields are **camelCase** (`accessToken`, `fullCases`, `customerId`, …).

---

## 3. Set it up with Axios (recommended)

Create one shared API instance and import it everywhere. Put this in e.g.
`src/lib/api.js`:

```js
import axios from "axios";

export const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
});

// Attach the token to EVERY request automatically.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401 (expired/invalid token), clear it and go to login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("accessToken");
      localStorage.removeItem("user");
      // e.g. window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);
```

Login + logout helpers:
```js
import { api } from "./lib/api";

export async function login(email, password) {
  const { data } = await api.post("/auth/login", { email, password });
  localStorage.setItem("accessToken", data.accessToken);
  localStorage.setItem("user", JSON.stringify(data.user));
  return data.user;
}

export async function logout() {
  // Revoke the token on the server first (needs the token, so call before clearing).
  try {
    await api.post("/auth/logout");
  } catch {
    // ignore network/401 errors — we still log out locally below
  }
  localStorage.removeItem("accessToken");
  localStorage.removeItem("user");
}

export function currentUser() {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}
```

Then **always call the API through `api`** so the token is attached:
```js
const products = (await api.get("/products/")).data;
await api.post("/sales/", salePayload);
```

> Do NOT mix in bare `axios.get(...)` or bare `fetch(...)` for protected routes —
> those skip the interceptor and will return 401.

---

## 4. Set it up with Fetch (if you don't use Axios)

```js
const BASE_URL = "http://127.0.0.1:8000/api/v1";

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem("accessToken");
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem("accessToken");
    // redirect to login
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

// Usage
const products = await apiFetch("/products/");
await apiFetch("/sales/", { method: "POST", body: JSON.stringify(salePayload) });
```

---

## 5. Roles & permissions

There are six accepted roles. The role is chosen at signup and shown on `/auth/me`.
Sending any other value returns 422.

| Role | Value to send | Access level |
|---|---|---|
| Owner | `owner` | Full |
| Admin | `admin` | Full (same as owner) |
| Manager | `manager` | Management |
| Cashier | `cashier` | Sales |
| Storekeeper | `storekeeper` | Stock |
| Staff | `staff` | Operations only (read + empties) |

**Reading data (GET):** any logged-in user.

**Writing data (POST/PATCH/DELETE):** depends on role —

| Action | Owner | Admin | Manager | Cashier | Storekeeper | Staff |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Users (create/edit/delete) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Products / Suppliers / Supplier-returns / Damaged-cases | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| Customers / Sales | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Empty-case transactions & returns | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Expenses / Notifications / Audits / Depots | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

> Creating users via `POST /users/` now accepts an optional `password` — include
> it so the created user can log in. Without it the account exists but cannot
> authenticate. Password minimum length is **6** characters (signup and user creation).

If a user tries an action their role can't do, the API returns **403**:
```json
{ "detail": "You do not have permission to perform this action" }
```

**UX tip:** read `currentUser().role` and hide/disable buttons the role can't use,
so users don't hit 403s. Always still handle 403 in code as a safety net.

---

## 6. Handling errors

| Status | Meaning | What the frontend should do |
|---|---|---|
| 401 | No/expired/invalid token | Clear token, redirect to login |
| 403 | Logged in, role not allowed | Show "You don't have permission" message |
| 409 | Conflict (e.g. email already registered on signup) | Show the `detail` message |
| 422 | Validation error (bad email, missing field, invalid role) | Show field errors from `detail` |

The error message is always in the response body under `detail`.

---

## 7. Token expiry

- Tokens expire after **24 hours** by default (backend setting
  `ACCESS_TOKEN_EXPIRE_MINUTES`).
- After expiry, requests return 401 → the user must log in again.
- There is currently **no refresh-token** flow; re-login is the way to get a new token.

---

## 8. Verify it works (checklist)

1. Log in → confirm `accessToken` is saved (check `localStorage` in DevTools).
2. Open DevTools → **Network** → click a `products` request → **Headers** tab.
   - You should see `Authorization: Bearer eyJ...` in the request headers.
3. The response should be **200**, not 401.
4. Log in as a **cashier** and try to create a product → should get **403**
   (cashiers can't manage stock). Log in as **owner/manager/storekeeper** → **201**.
5. Manually delete the token from `localStorage` and refresh → protected calls
   should 401 and bounce you to login.
6. Click logout, then try any protected request with the **same** token → it must
   now return **401** (the server revoked it — see §10).

---

## 9. Common mistakes

- **Token not attached** — the #1 cause of 401. Check the Network → Headers tab.
- **Calling the API without the shared instance** — some screen uses bare
  `fetch`/`axios` and skips the interceptor.
- **Wrong base URL** — must include `/api/v1`.
- **Sending `role` not in the allowed list** at signup → 422.
- **CORS error in console** (different from 401) — the frontend's origin must be
  in the backend's `BACKEND_CORS_ORIGINS`. Ask the backend owner to add your
  dev URL (e.g. `http://localhost:5173`).

---

## 10. Logout

Logout is **server-side**: calling `POST /auth/logout` revokes the token so it can
no longer be used, even if someone copied it. This is stronger than just deleting
the token from the browser.

### Endpoint
| Method | Path | Headers | Returns |
|---|---|---|---|
| POST | `/auth/logout` | `Authorization: Bearer <token>` | `{ "detail": "Successfully logged out" }` |

### Rules
- The logout call **needs the token** → call it **before** you clear `localStorage`.
- After logout, that token returns **401** on every protected endpoint
  (including `/auth/me`). The user must log in again to get a new token.
- Logout with no token → 401.

### How to call it (Axios)
The `logout()` helper from §3 already does this:
```js
import { logout } from "./lib/api";

async function handleLogout() {
  await logout();          // revokes on server + clears localStorage
  // window.location.href = "/login";
}
```

### How to call it (Fetch)
```js
async function logout() {
  try {
    await apiFetch("/auth/logout", { method: "POST" }); // revoke server-side
  } catch {
    // ignore errors — still log out locally
  }
  localStorage.removeItem("accessToken");
  localStorage.removeItem("user");
}
```

> Important: always clear local storage even if the network call fails, so the
> user is logged out on this device regardless. And don't keep using the old
> token after logout — request a fresh one by logging in again.

---

## 11. Newly supported request fields (inventory, sales, expenses)

The backend was extended so the fields the current forms send are **persisted**
(previously they were silently dropped). All fields are camelCase.

### Products — `POST/PATCH /products/`
In addition to the base product fields, these are now stored and returned:
`containerType`, `containerSizeLabel`, `bottlesPerContainer`,
`purchasePricePerContainer`, `sellingPricePerContainer`,
`bottleInfo` (object `{damaged, missing, returned, notes}`),
`partialCases` (array), `lastStockCheck`. Reads also return `updatedAt`.

### Sales — `POST /sales/`
Now accepted and applied server-side (do **not** send computed totals — the
server calculates them):
- `tax` — a **percentage** (e.g. `10` = 10%); the server computes the tax amount and adds it to `total`.
- `isPartialPayment` (boolean) + optional `remainingBalance`. On a partial sale the unpaid amount is added to the customer's `unpaidBalance`.
- Per line item: `emptyCasesReturned` (returned at the sale) and `remainingEmptyCases`.
- The sale response now includes `tax`, `isPartialPayment`, `remainingBalance`, `emptyCasesTotal`, `remainingEmptyCasesTotal`, and per-item `emptyCasesReturned` / `remainingEmptyCases`.

Payment values: `cash`, `mobile`, `card`, `bank`.

### Expenses — `POST/PATCH /expenses/`
Now stored: `description`, `paymentMethod`, `dueDate`, `receiptNumber`,
`quantity`, `unitPrice`, `createdBy`, `updatedBy`. The `notes` field is accepted
and maps onto `note`.

**Receipt upload:** send the file as a base64 data URL in `receipt` plus
`receiptFileName` (and optionally `receiptFileType`, `receiptFileSize`). The
backend stores it and returns **`receiptUrl`** (a fully-qualified URL you can use
directly in an `<img>`/link) and `receiptFileName`. Invalid base64 returns 400.

> Still not implemented (calling these will 404): the analytics/filter helper
> endpoints in the services (`/sales/daily-summary`, `/expenses/summary/category`,
> `/products/low-stock`, `/products/{id}/stock`, `PATCH`/`DELETE /sales/{id}`, etc.).
> Keep computing those client-side for now, or ask the backend team to add them.
