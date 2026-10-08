# WorkBit

WorkBit is a web reward marketplace foundation: users discover legitimate offers and rewards are only credited after a provider-confirmed conversion passes server-side validation.

## Current milestone: user dashboard and manual payouts

- Next.js App Router user/admin entry pages, dashboard shell, and responsive authentication UI
- FastAPI `/api/v1` authentication, cookie sessions, RBAC, user/admin dashboard APIs, and OpenAPI docs
- PostgreSQL SQLAlchemy schema and Alembic migrations
- Provider-neutral offer/conversion handling, configurable reward policies, and a Decimal-safe wallet ledger foundation
- User-scoped dashboard, referral overview, wallet history, and encrypted manual withdrawal requests with audited admin review
- Docker Compose services for web, API, PostgreSQL, Redis, and worker placeholder

## Run locally

1. From the project root, create and activate `.venv` if needed (`python -m venv .venv`, then `.\.venv\Scripts\Activate.ps1` in PowerShell).
2. From `backend/`, install dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` in the project root. Set `DATABASE_URL` to the PostgreSQL connection string; optionally set `DIRECT_URL` for migrations. To send verification and password-reset emails, set `EMAIL_PROVIDER=resend`, `EMAIL_API_KEY` to your Resend API key, and `EMAIL_FROM_ADDRESS` to a sender address on a domain verified in Resend. To enable profile photo uploads and the admin dashboard banner CMS, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` from your Cloudinary account. To enable manual withdrawal requests, set `WITHDRAWAL_ENCRYPTION_KEY` to a generated 32-byte URL-safe base64 key and adjust `WITHDRAWAL_MINIMUM_AMOUNT` to the approved policy. Generate a key with `python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. Keep API keys and the encryption key secret; losing or rotating the encryption key makes previously stored payout destinations unreadable. Do not commit `.env`.
4. From `backend/`, run `python -m alembic upgrade head`, `python -m app.services.seed`, then `python -m uvicorn app.main:app --reload`. Seed each new database before accepting registrations, and make sure the seed command and API use the same configured `DATABASE_URL`.
5. Sign in to the admin console and open **Dashboard banners** to upload, publish, reorder, edit, or delete announcements. Only published banners appear in the signed-in user dashboard carousel.
5. From `frontend/`, run `npm install` and `npm run dev`.

## Deploying frontend and API on Vercel

Deploy `backend/` and `frontend/` as separate Vercel projects. Set the backend project's Root Directory to `backend` and the frontend project's Root Directory to `frontend`. The frontend proxies `/api/v1/*` requests to `https://work-bit.vercel.app` by default; set `BACKEND_URL` in the frontend project's Vercel environment variables if the API uses a different origin. Leave `NEXT_PUBLIC_API_URL` unset or set it to `/api/v1` so browser requests and the session cookie stay on the frontend's origin. Set `FRONTEND_ORIGIN` in the backend project to the frontend's exact production origin, then redeploy both projects after changing environment variables.

WorkBit is a FastAPI service, not a Django project: there is no `manage.py`; start the API with Uvicorn as above. The admin withdrawal review screen is available at `/admin` to authenticated users with the required backend permissions.

Docker Compose remains available for containerized development/deployment, but is not required for local development. The current API does not require Redis.

Development seed credentials are `workbit-admin@example.com` / `WorkBitDev123!` and `workbit-user@example.com` / `WorkBitDev123!`. They are development-only and must never be used in production.

## Backend commands

Run from `backend/`:

```powershell
python -m pip install -r requirements.txt
python verify_database.py
python -m alembic current
python -m alembic heads
# If the live revision is behind the listed head:
python -m alembic upgrade head
python -m app.services.seed
python -m uvicorn app.main:app --reload
python -m pytest -q
```

Create a migration with `alembic revision --autogenerate -m "description"`. Avoid downgrading production databases.

## Current platform boundaries

Withdrawal requests use manual admin review and stay disabled until the encryption key is configured. Reviewer permissions are separate from read-only withdrawal access. The current offer catalog is development-only; no production network credentials or approved Lootably, AdGem, or CPAlead adapters are configured. Network approval and credentials, referral reward percentages, fraud rules, data retention, and user-facing legal policies require product, legal, security, and provider approval before public launch. Daily bonuses, achievements, notifications, and automated referral commissions are not implemented and are not represented as available rewards.
