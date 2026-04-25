# Playto Payout Engine - Founding Engineer Challenge

## Tech Stack
- **Backend:** Django, Django REST Framework, Django-Q (Database-backed job queue), PostgreSQL (sqlite locally for simplicity).
- **Frontend:** React, Vite, Tailwind CSS v4.

## Setup Instructions (Windows)

We use natively isolated processes. No Docker is necessary, ensuring maximum compatibility. Django-Q uses the database as a durable event queue.

### 1. Backend Setup
```powershell
# Open a terminal in the payout_engine dir
cd backend # (Actually run it from root since manage.py is in the root directory for this codebase)
python -m venv venv
.\venv\Scripts\activate
pip install django djangorestframework django-cors-headers django-q2 dj-database-url psycopg2-binary
```

**Run Migrations & Seed the DB:**
```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py seed  # Creates merchants and sets up the retry scheduler
```

**Run the API:**
```powershell
python manage.py runserver 127.0.0.1:8000
```

**Run the Background Worker (In a new terminal window):**
```powershell
# If using PowerShell or Command Prompt:
.\venv\Scripts\activate

# If using Git Bash (MINGW64):
source venv/Scripts/activate

python manage.py qcluster
```

### 2. Frontend Setup
```powershell
cd frontend
npm install
npm run dev
```

Visit the running frontend link (usually `http://localhost:5173`) to view the interactive dashboard.

## Tests
To verify concurrency and idempotency robustness, run:
```powershell
python manage.py test core
```

## Deployment
Deploy via Render or Railway using the included `dj-database-url` integration. Define `DATABASE_URL` in your env.
