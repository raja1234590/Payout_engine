# Playto Payout Engine - Founding Engineer Challenge

## Project Description
A minimal payout engine for merchants. Merchants accumulate balance in paise from credits, request payouts, and the backend processes those payouts asynchronously. The system is designed to handle balance integrity, concurrency, and idempotency.

## Tech Stack
- **Backend:** Django, Django REST Framework, Django-Q (database-backed job queue), PostgreSQL (SQLite locally for simplicity)
- **Frontend:** React, Vite, Tailwind CSS v4

## Setup Instructions (Windows)
We use natively isolated processes. No Docker is required. Django-Q uses the database as a durable event queue.

### 1. Backend Setup
```powershell
# Open a terminal in the payout_engine root directory
python -m venv venv
.\venv\Scripts\activate
pip install django djangorestframework django-cors-headers django-q dj-database-url psycopg2-binary
```

**Run migrations and seed the database:**
```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py seed
```

**Run the backend API:**
```powershell
python manage.py runserver 127.0.0.1:8000
```

**Run the background worker in a new terminal:**
```powershell
.\venv\Scripts\activate
python manage.py qcluster
```

If you use Git Bash, activate with:
```bash
source venv/Scripts/activate
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

Open the provided Vite URL, usually `http://localhost:5173`.

## Local API Endpoints
- `GET /api/v1/merchants/me` — fetch the merchant dashboard
- `POST /api/v1/payouts` — request a payout
  - Required header: `Idempotency-Key: <uuid>`
  - Body example:
    ```json
    {
      "amount_paise": 100000,
      "bank_account_id": "123"
    }
    ```

## Testing
### Automated tests
Run the core tests for concurrency and idempotency:
```powershell
python manage.py test core
```

### Manual Postman testing
Use Postman to verify:
- idempotency by sending the same `Idempotency-Key` twice
- concurrency by firing multiple requests at the same time against `/api/v1/payouts`

## Notes
- The backend is local by default at `http://127.0.0.1:8000`
- The frontend reads the backend URL from `VITE_API_URL`
- For production, set `DATABASE_URL` in the deployment environment and run both the web process and `python manage.py qcluster`

## Deployment
Deploy via Render or Railway using the included `dj-database-url` integration. Be sure to set:
- `DATABASE_URL`
- a worker process for `python manage.py qcluster`
- `VITE_API_URL` for the frontend build

## Screenshots
- Merchant dashboard showing available balance, held balance, recent transactions, and payout history.
- Postman request example for `POST /api/v1/payouts` with `Idempotency-Key` header.
- Local app workflow from frontend to backend to background processing.
