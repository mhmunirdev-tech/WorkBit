# WorkBit

WorkBit is a web reward marketplace foundation: users discover legitimate offers and rewards are only credited after a provider-confirmed conversion passes server-side validation.

## Current milestone: user dashboard and manual payouts

- Next.js App Router user/admin entry pages, dashboard shell, and responsive authentication UI
- FastAPI `/api/v1` authentication, cookie sessions, RBAC, user/admin dashboard APIs, and OpenAPI docs
- Separate user and admin authentication: public `/register` always creates USER accounts, `/login` and `/admin/login` issue independent session cookies, and admin routes require the admin cookie. User identity/logout use `/auth/me` and `/auth/logout`; admin identity/logout use `/auth/admin/me` and `/auth/admin/logout`. Admin and SUPER_ADMIN accounts are provisioned by seed or authorized operations.
- PostgreSQL SQLAlchemy schema and Alembic migrations
- Provider-neutral offer/conversion handling, configurable reward policies, and a Decimal-safe wallet ledger foundation
- Six database-managed earning packages with admin-editable titles, descriptions, prices, durations, visibility, and display order; users choose a package before paying its exact BDT amount by manual bKash/Nagad transfer, and each request snapshots the package terms and exchange rate for review
- Manual admin review of package payment references; standalone wallet deposits and wallet-funded package purchases are retired, while earnings remain withdrawable
- User-scoped dashboard, referral overview, wallet history, and encrypted manual withdrawal requests with up to two saved bKash and two saved Nagad accounts, registered-email OTP verification, and audited admin review
- Referral links award the inviter 5% of each referred user's package price only after the package payment is approved and the package activates
- Automatic member ranks and leaderboard: approved USD offer rewards plus approved USD package purchases count toward database-managed tiers (seeded defaults: Starter $0, Bronze $50, Silver $200, Gold $500)
- Registration stores the accepted terms version and timestamp; development demo offers are seeded records loaded through the same database-backed catalog API
- Provider-approved ad completions apply the configured reward policy and credit available balance immediately; unconfirmed conversions do not create wallet rewards
- Docker Compose services for web, API, PostgreSQL, Redis, and worker placeholder

## Run locally

1. From the project root, create and activate `.venv` if needed (`python -m venv .venv`, then `.\.venv\Scripts\Activate.ps1` in PowerShell).
2. From `backend/`, install dependencies with `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` in the project root. Set `DATABASE_URL` to the PostgreSQL connection string; optionally set `DIRECT_URL` for migrations. To send verification, password-reset, and payout confirmation emails, set either `RESEND_API_KEY` or `BREVO_API_KEY` and set `EMAIL_FROM_ADDRESS` to an address verified with that provider. The app automatically uses whichever provider key is configured. If both keys are set, choose one with `EMAIL_PROVIDER=resend` or `EMAIL_PROVIDER=brevo`. See Resend's [API key guide](https://resend.com/docs/dashboard/api-keys/introduction) and [domain verification guide](https://resend.com/docs/dashboard/domains/introduction), or Brevo's [API key guide](https://developers.brevo.com/docs/api-key-authentication) and [sender setup instructions](https://help.brevo.com/hc/en-us/articles/208836149-Create-a-new-sender-From-name-and-From-email). Only providers with an implemented integration are supported. New registrations receive a six-digit email verification code, valid for `EMAIL_VERIFICATION_OTP_TTL_MINUTES` (default 10 minutes); verification codes expire after five failed attempts and only the newest code remains valid. Payout account changes and withdrawal requests also require a six-digit code sent to the registered email; these codes expire under the same setting, are limited to five attempts, and are bound to the payout details or withdrawal amount. To enable profile photo uploads and the admin dashboard banner CMS, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET` from your Cloudinary account. To enable manual withdrawal requests, set `WITHDRAWAL_ENCRYPTION_KEY` to a generated 32-byte URL-safe base64 key. `WITHDRAWAL_MINIMUM_AMOUNT` (USD, default $5) is used only to initialize the database setting during migration or first seed; thereafter, manage the live minimum in **Admin → Withdrawals**. Generate a key with `python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. Run `python -m alembic upgrade head` from `backend/` to create and update the saved payout-account table and payout settings. Users can save up to two bKash and two Nagad numbers on Wallet; each is encrypted at rest, and withdrawal requests remain subject to the database-managed minimum and exchange rate, available earning balance, and manual admin review. Then sign in with an administrator that has `withdrawals.review` permission and manage the USD/BDT exchange rate and minimum withdrawal on **Admin → Withdrawals**. Withdrawals stay disabled until both the encryption key and exchange rate are configured. Keep API keys and the encryption key secret; losing or rotating the encryption key makes previously stored payout destinations unreadable. Do not commit `.env`.
4. From `backend/`, run `python -m alembic upgrade head`, `python -m app.services.seed`, then `python -m uvicorn app.main:app --reload`. Seed each new database before accepting registrations, and make sure the seed command and API use the same configured `DATABASE_URL`.
5. Sign in to the admin console and open **Dashboard banners** to upload, publish, reorder, edit, or delete announcements. Only published banners appear in the signed-in user dashboard carousel.
6. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the frontend environment (for example, `frontend/.env`), then from `frontend/` run `npm install` and `npm run dev`.

To test the demo ad earning flow locally, set `ENVIRONMENT=development` and `ENABLE_MOCK_REWARDS=true` in the root `.env`, then restart the API. Sign in with a user account that has an admin-approved earning package, open a development demo offer, and choose **Complete demo ad and add test earning**. The displayed amount is the gross ad reward: the 80/20 reward policy immediately credits 80% to the user's available balance and records 20% as platform share. The cumulative approved platform share appears on the admin dashboard. This simulation endpoint is disabled outside development and must never be enabled in production.

The admin dashboard includes traffic and security analytics: visitors active in the last five minutes, daily unique visitors and page views, failed user/admin logins, and a 90-day daily trend. The frontend stores a random browser identifier locally and sends a heartbeat every three minutes while visible; the API stores only a keyed hash of the identifier, a keyed IP hash, and masked email for failed logins—never the supplied password or full IP/email. Analytics refreshes every 30 seconds, repeated views of the same route within 30 seconds are grouped, and events older than 90 days are purged during analytics activity.

## Deploying frontend and API on Vercel

Deploy `backend/` and `frontend/` as separate Vercel projects. Set the backend project's Root Directory to `backend` and the frontend project's Root Directory to `frontend`. Before routing traffic to a backend release that changes the database schema, run `python -m alembic upgrade head` from `backend/` against that deployment's configured production database (`DIRECT_URL` when set, otherwise `DATABASE_URL`), then verify with `python -m alembic current`. Do not run migrations against a different database or commit production connection strings. Set `NEXT_PUBLIC_API_URL` in the frontend project's Vercel environment to the backend origin, such as `https://api.workbitbd.com`; the frontend adds the OpenAPI `/api/v1` prefix to endpoint paths and preserves cookie credentials. Set `FRONTEND_ORIGIN` in the backend project to the frontend's exact production origin so credentialed browser requests are allowed. To send email through Brevo, set `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY`, and a Brevo-verified `EMAIL_FROM_ADDRESS` in the backend project's Production environment. Redeploy the backend after changing environment variables.

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

Withdrawal requests use manual admin review and stay disabled until the encryption key and the administrator-managed USD/BDT rate are configured. Users can request bKash or Nagad payouts from withdrawable earning balance once it reaches the configured minimum (default $5); each request reserves the amount from available balance and snapshots the exchange rate and resulting BDT payout. After the reviewer has sent the payout, approving the request marks it paid immediately; rejection releases the reserved amount. Reviewer permissions are separate from read-only withdrawal access. Package prices and wallet balances are USD. To buy a package, users select it from **Packages**, pay its fixed BDT amount to the configured bKash/Nagad account, and submit the transaction reference. The initial configured rate is 1 USD = BDT 120; administrators can update it under **Admin → Withdrawals**. The package price, duration, BDT amount, and USD/BDT rate are snapshotted for admin review; renewals made before expiry extend from the current package expiry. Standalone BDT deposits and wallet-funded package purchases are retired; the admin deposit review remains available for previously submitted legacy requests. Configure `PACKAGE_BKASH_NUMBER` and `PACKAGE_NAGAD_NUMBER` for receiving accounts. Package catalog settings are managed under **Admin → Package settings**. Only externally approved package payments count toward the admin's **Registered user amount**; approved package records count toward referral-member eligibility and ranks. Referral links currently award 5% of the referred user's snapshotted package price to the inviter's wallet when an admin approves the package payment. The current offer catalog is development-only; no production network credentials or approved Lootably, AdGem, or CPAlead adapters are configured. Network approval and credentials, fraud rules, data retention, and user-facing legal policies require product, legal, security, and provider approval before public launch. Daily bonuses, achievements, and notifications are not implemented and are not represented as available rewards.
