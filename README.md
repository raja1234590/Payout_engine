# Playto Payout Engine - Founding Engineer Challenge

## Live Deployment
- **Frontend:** https://payout-engine.vercel.app/
- **Backend API:** https://payout-engine-x94c.onrender.com

## Tech Stack
- **Backend:** Django, Django REST Framework, Django-Q (database-backed job queue), PostgreSQL (SQLite locally for simplicity)
- **Frontend:** React, Vite, Tailwind CSS v4

## Payout Creation Behavior
When requesting a payout via `POST /api/v1/payouts`, the system checks the merchant's available balance before creating the payout:
- **Sufficient Funds:** If the merchant's balance is greater than or equal to the payout amount, the payout is created with status "pending" and queued for processing by the background worker.
- **Insufficient Funds:** If the balance is less than the payout amount, the API returns an error "insufficient funds" and no payout is created.
- **Same Bank Account ID:** Multiple payout requests for the same bank account ID (merchant) will succeed only if the balance allows each one. For example, if the balance is 200,000 paise and you request two payouts of 100,000 paise each, both will be created. But if you request three, the third will fail with "insufficient funds".

This ensures that payouts are only initiated when funds are available, preventing overdrafts.

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

## API Endpoints
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

.
<img width="1034" height="772" alt="Screenshot 2026-04-25 162540" src="https://github.com/user-attachments/assets/b8c18187-b846-4cd6-b1b8-3bcb0f19305a" />
<img width="921" height="722" alt="Screenshot 2026-04-25 162446" src="https://github.com/user-attachments/assets/02952f9b-4b80-4057-a8c2-8139c7f793a9" />

