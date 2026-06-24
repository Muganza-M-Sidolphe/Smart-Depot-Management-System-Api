# Frontend Integration Guide

This backend serves the Smart Depot Management System frontend.

## Local API URLs

Run the backend from `Smart-Depot-Management-System-Api`:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

Default local URLs:

- API base URL: `http://127.0.0.1:8000/api/v1`
- Swagger docs: `http://127.0.0.1:8000/docs`
- ReDoc docs: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/api/v1/health`

Yes, frontend developers can access and test every API route in Swagger at `/docs`.

## Environment Variable

In the Next.js frontend, add:

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Use this value for all frontend requests.

## Recommended API Client

Create a small API helper in the frontend, for example `lib/api.ts`:

```ts
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
}
```

## Important Endpoints

Products:

- `GET /products/`
- `POST /products/`
- `GET /products/{id}`
- `PATCH /products/{id}`
- `DELETE /products/{id}`

Customers:

- `GET /customers/`
- `POST /customers/`
- `GET /customers/{id}`
- `PATCH /customers/{id}`
- `DELETE /customers/{id}`

Sales:

- `GET /sales/`
- `POST /sales/`
- `GET /sales/{id}`

Empty cases:

- `GET /empty-case-transactions/`
- `POST /empty-case-transactions/`
- `POST /empty-case-transactions/{id}/process-return`

Dashboard:

- `GET /reports/dashboard`

Notifications:

- `GET /notifications/`
- `POST /notifications/generate`
- `POST /notifications/mark-read`

Other resources:

- `/suppliers/`
- `/expenses/`
- `/users/`
- `/activities/`
- `/supplier-returns/`
- `/damaged-cases/`
- `/transaction-audits/`

## Request Examples

Create product:

```json
{
  "name": "Primus",
  "brand": "Bralirwa",
  "category": "Lager",
  "fullCases": 100,
  "emptyCases": 40,
  "purchasePrice": 9000,
  "sellingPrice": 11000,
  "supplier": "Bralirwa Ltd",
  "batchNumber": "BR-001",
  "manufactureDate": "2026-01-01T00:00:00",
  "expiryDate": "2026-12-01T00:00:00",
  "lowStockThreshold": 10,
  "depositAmount": 3000
}
```

Create customer:

```json
{
  "name": "Kigali Bar",
  "phone": "+250788000000",
  "email": "orders@kigali-bar.rw",
  "address": "Kigali",
  "type": "wholesale",
  "city": "Kigali",
  "notes": ""
}
```

Create sale:

```json
{
  "customerId": 1,
  "customerName": "Kigali Bar",
  "items": [
    {
      "productId": 1,
      "quantity": 5
    }
  ],
  "discount": 5000,
  "payment": "mobile",
  "amountPaid": 60000,
  "cashier": "Eric Mugisha"
}
```

Process empty-case return:

```json
{
  "returnQuantity": 3,
  "processedBy": "Claude Niyonzima"
}
```

## Frontend Behavior Notes

- The API accepts and returns camelCase fields to match the existing frontend TypeScript types.
- Creating a sale reduces product `fullCases`.
- Creating a sale updates customer `pendingEmpties`, `totalPurchases`, `totalSpent`, `totalTransactions`, and `refundableDeposits`.
- Creating a sale automatically creates empty-case transactions.
- Processing an empty-case return updates the transaction, customer deposits, activity feed, and audit log.

## Browser Testing Checklist

1. Open `http://127.0.0.1:8000/docs`.
2. Open `GET /api/v1/health`, click `Try it out`, then `Execute`.
3. Create a product with `POST /api/v1/products/`.
4. Create a customer with `POST /api/v1/customers/`.
5. Create a sale with `POST /api/v1/sales/`.
6. Confirm stock changed with `GET /api/v1/products/{id}`.
7. Confirm customer balances changed with `GET /api/v1/customers/{id}`.
8. Confirm empty-case transaction exists with `GET /api/v1/empty-case-transactions/`.
9. Test dashboard with `GET /api/v1/reports/dashboard`.
