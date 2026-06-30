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

export function logout() {
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

There are four roles. The role is chosen at signup and shown on `/auth/me`.

| Role | Value to send |
|---|---|
| Owner | `owner` |
| Manager | `manager` |
| Cashier | `cashier` |
| Storekeeper | `storekeeper` |

**Reading data (GET):** any logged-in user.

**Writing data (POST/PATCH/DELETE):** depends on role —

| Action | Owner | Manager | Cashier | Storekeeper |
|---|:--:|:--:|:--:|:--:|
| Users (create/edit/delete) | ✅ | ❌ | ❌ | ❌ |
| Products / Suppliers / Supplier-returns / Damaged-cases | ✅ | ✅ | ❌ | ✅ |
| Customers / Sales | ✅ | ✅ | ✅ | ❌ |
| Empty-case transactions & returns | ✅ | ✅ | ✅ | ✅ |
| Expenses / Notifications / Audits / Depots | ✅ | ✅ | ❌ | ❌ |

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
