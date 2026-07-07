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
    "mustChangePassword": false,
    "createdAt": "2026-06-30T10:00:00"
  }
}
```

**`mustChangePassword`** — `true` when the user still has a system-generated
temporary password (i.e. an admin created them and they haven't chosen their own
yet). It's on the `user` object in the login **and** `/auth/me` responses. After
login, check it and, if `true`, route the user straight to a "change password"
screen instead of the dashboard:

```js
const { user } = data;                 // from login
if (user.mustChangePassword) {
  // redirect to /change-password (don't send them to the dashboard yet)
} else {
  // normal role-based redirect
}
```

Change it via **`POST /auth/change-password`** (requires the token):
```js
await api.post("/auth/change-password", {
  currentPassword,   // their temp/current password
  newPassword,       // min 6 chars
});
// on 200 the flag is cleared; proceed to the dashboard. 400 = current password wrong.
```
(Signup users and anyone who has reset their password have `mustChangePassword: false`.)

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

> **Creating users via `POST /users/`:** you do **not** need to send a password.
> If you omit it, the backend generates a temporary password and **emails the new
> user their credentials + a login link** automatically. You may still send a
> `password` to set one explicitly (then no email is sent). Password minimum
> length is **6** characters (signup and user creation).
>
> So the "add user" form only needs `name`, `email`, `role`, and optionally
> `phone`. After creating, tell the admin the user will receive an email to log
> in. (In dev, if SMTP isn't configured, the email — including the temp password —
> is written to the backend logs instead of being sent.)

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

### Forgot / reset password (public, no token)
Two steps, both under `/auth`:

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/forgot-password` | `{ email }` | 200 always (generic message) |
| POST | `/auth/reset-password` | `{ token, newPassword }` | 200, or 400 if token invalid/expired |

Flow:
1. **Forgot-password page** → `POST /auth/forgot-password` with the email. The
   response is always a generic 200 (`"If an account exists…"`) — it never reveals
   whether the email is registered, so show that message regardless.
2. The backend emails a link: `FRONTEND_URL/reset-password?token=<token>`
   (token valid for `PASSWORD_RESET_EXPIRE_MINUTES`, default 60 min).
3. **Build a `/reset-password` page** that reads `token` from the query string and
   collects a new password (min 6), then `POST /auth/reset-password` with
   `{ token, newPassword }`.
4. On 200, redirect to `/login`. On 400, show "This reset link is invalid or has
   expired" and let them request a new one. Tokens are single-use.

```js
// forgot-password page
await api.post("/auth/forgot-password", { email });
// always show: "If an account exists for that email, a reset link has been sent."

// reset-password page (token from URL ?token=...)
const token = new URLSearchParams(location.search).get("token");
await api.post("/auth/reset-password", { token, newPassword });
// on success -> go to /login
```

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

#### Full vs partial payment + paying off the balance
Every sale now has a **`paymentStatus`**: `"paid"`, `"partial"`, or `"unpaid"`, and a
**`payments`** array (the ledger of amounts received, including the amount paid at
the point of sale).

- **Full payment:** send `amountPaid >= total` (and omit/false `isPartialPayment`) → `paymentStatus: "paid"`, `remainingBalance: 0`.
- **Partial payment:** send `isPartialPayment: true` with `amountPaid` less than the total → `paymentStatus: "partial"`, `remainingBalance` = what's still owed, and the customer's `unpaidBalance` goes up by that amount.

**Record later payments until the balance is cleared:**

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/sales/{id}/payments` | sales roles | Record a payment toward the balance |
| GET | `/sales/{id}/payments` | any logged-in | The payment ledger for a sale |
| GET | `/sales/outstanding` | any logged-in | All sales with a balance still owed (receivables) |

`POST /sales/{id}/payments` body:
```json
{ "amount": 40000, "method": "cash", "receivedBy": "Aline", "note": "optional" }
```
It returns the **updated sale** (new `amountPaid`, `remainingBalance`, `paymentStatus`,
and the appended `payments`). When the last payment clears the balance,
`paymentStatus` becomes `"paid"`, `remainingBalance` is `0`, and the customer's
`unpaidBalance` is reduced accordingly. Errors: **400** if the sale is already
paid or the amount exceeds the remaining balance.

Build a "Record payment" button on partial/unpaid sales, and an "Outstanding /
receivables" screen from `GET /sales/outstanding`.

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

---

## 12. Automatic PDF reports by email

The backend can email a **PDF business report** (daily / weekly / monthly) to
configured recipients, automatically on a schedule. All endpoints are under
`/reports` and require a token; settings/sending require **owner or admin**.

| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/reports/settings` | any logged-in | Current schedule + recipients |
| PUT | `/reports/settings` | owner/admin | Update schedule + recipients |
| GET | `/reports/{period}/pdf` | manager+ | Download the PDF (`period` = `daily`/`weekly`/`monthly`) |
| POST | `/reports/send?period=daily` | owner/admin | Generate + email the report **now** (optionally `&recipients=a@x.com`) |

### Settings shape (`GET`/`PUT /reports/settings`)
```json
{
  "recipients": ["boss@depot.rw", "owner@depot.rw"],
  "whatsappNumber": null,
  "dailyEnabled": true,
  "weeklyEnabled": false,
  "monthlyEnabled": true,
  "sendHour": 8,          // 0-23, in the server's configured timezone (default Africa/Kigali, UTC+2)
  "weeklyWeekday": 0,     // 0=Mon … 6=Sun
  "monthlyDay": 1         // 1-28
}
```
`PUT` accepts any subset of those fields. When a period is enabled and has
recipients, the server emails the PDF automatically at `sendHour` (daily), on
`weeklyWeekday` (weekly), and on `monthlyDay` (monthly).

### Build a "Reports settings" screen
- Load current values with `GET /reports/settings`.
- Let the admin edit recipients (email list), toggles, and times → `PUT`.
- Add a **"Send test report now"** button → `POST /reports/send?period=daily`.
- Add **"Download PDF"** links → `GET /reports/{period}/pdf` (opens/downloads the PDF).

> `whatsappNumber` is accepted and stored now but not yet used — WhatsApp delivery
> is a planned follow-up. To actually send emails, the backend needs SMTP
> configured (`.env`); otherwise reports are logged instead of sent.
