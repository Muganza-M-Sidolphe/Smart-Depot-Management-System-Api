# Smart Depot Management System API

Python backend for the Smart Depot Management System, built with FastAPI and SQLAlchemy.
It is designed to serve the existing Next.js frontend in `../Smart-Depot-Management-System`.
This supports sellers who want to dynamically manage depot inventory, sales, customers, expenses, and returns.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs will be available at:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Test

```bash
pytest
```

If you are not inside the virtual environment:

```bash
.venv/bin/pytest
```

## API

All routes are prefixed with `/api/v1`.

Frontend developers should also read [FRONTEND_INTEGRATION_GUIDE.md](./FRONTEND_INTEGRATION_GUIDE.md).

Core system routes:

- `GET /health`
- `GET/POST/PATCH/DELETE /depots`

Frontend business routes:

- `GET/POST/PATCH/DELETE /products`
- `GET/POST/PATCH/DELETE /suppliers`
- `GET/POST/PATCH/DELETE /customers`
- `GET/POST/PATCH/DELETE /users`
- `GET/POST /sales`
- `GET/POST/PATCH/DELETE /expenses`
- `GET/POST /activities`
- `GET /notifications`
- `POST /notifications/generate`
- `POST /notifications/mark-read`
- `GET/POST /empty-case-transactions`
- `POST /empty-case-transactions/{id}/process-return`
- `GET/POST /supplier-returns`
- `GET/POST /damaged-cases`
- `GET/POST /transaction-audits`
- `GET /reports/dashboard`

The backend uses snake_case internally and returns camelCase JSON fields for frontend compatibility.

## Business Behavior

- Creating a sale reduces product `fullCases`.
- Creating a sale creates sale items and empty-case transactions.
- Creating a sale updates customer `pendingEmpties`, `totalPurchases`, `totalSpent`, `totalTransactions`, and `refundableDeposits`.
- Processing an empty-case return updates the transaction, customer pending empties, customer refundable deposits, audit trail, and activity feed.
- Dashboard reports summarize products, customers, sales, expenses, stock status, expiry status, empty cases, deposits, and recent activity.

## Project Structure

```text
app/
  api/
    v1/
      endpoints/
  core/
  db/
  models/
  schemas/
  services/
tests/
```
