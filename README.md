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
6. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in the frontend environment (for example, `frontend/.env.local`), then from `frontend/` run `npm install` and `npm run dev`. **Explore offers** includes the configured Adsterra Social Bar and native banner, a responsive 320x50 mobile/468x60 tablet/728x90 desktop banner, a 300x250 banner, and 160x300/160x600 desktop placements. Adsterra scripts and zone keys are public by design. You can also show AmanahAds placements by setting `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY` to the instance key from AmanahAds. These display ads only; ad views do not credit WorkBit wallet rewards. BitLabs' hosted offerwall and verified reward callbacks can be enabled separately. TheoremReach web surveys and verified server callbacks are also supported; see [provider callback setup](./docs/postbacks.md).

To enable Offerwall.GG's WorkBit-native offer cards locally, configure `OFFERWALL_GG_ENABLED=true`, `OFFERWALL_GG_PUBLIC_KEY`, `OFFERWALL_GG_SECRET_KEY`, and `OFFERWALL_GG_CURRENCY_NAME=USD` in the root `.env` used by the backend. The backend uses the secret key to request paginated, country-targeted offers and tracked click URLs from Offerwall.GG; it never exposes the secret to the browser. Register `https://<your-public-api-host>/api/v1/postbacks/offerwall-gg` in the placement, with no callback macros so Offerwall.GG appends all documented fields. Configure the placement currency as `USD` at exactly one unit per USD, enable **require signature**, and allow `workbitbd.com` (and your local test host only while testing). Only users with an approved active WorkBit earning package can see these offers. The card reward is an estimate based on WorkBit's reward policy; only a verified callback credits the wallet. See [Offerwall.GG postbacks](./docs/postbacks.md) for callback, reward, reversal, and test details.

To configure TheoremReach, set the `THEOREMREACH_*` backend environment variables listed in the Backend Vercel project table below, register `https://<your-public-api-host>/api/v1/postbacks/theoremreach` as its server callback, and map the documented callback values as described in [provider callback setup](./docs/postbacks.md#theoremreach). Use an exchange rate of at least 10, test signed debug callbacks, then request publisher approval before enabling live surveys. Keep the TheoremReach secret key only in the backend environment.

To test the demo ad earning flow locally, set `ENVIRONMENT=development` and `ENABLE_MOCK_REWARDS=true` in the root `.env`, then restart the API. Sign in with a user account that has an admin-approved earning package, open a development demo offer, and choose **Complete demo ad and add test earning**. The displayed amount is the gross ad reward: the 80/20 reward policy immediately credits 80% to the user's available balance and records 20% as platform share. The cumulative approved platform share appears on the admin dashboard. This simulation endpoint is disabled outside development and must never be enabled in production.

The admin dashboard includes traffic and security analytics: visitors active in the last five minutes, daily unique visitors and page views, failed user/admin logins, and a 90-day daily trend. The frontend stores a random browser identifier locally and sends a heartbeat every three minutes while visible; the API stores only a keyed hash of the identifier, a keyed IP hash, and masked email for failed logins—never the supplied password or full IP/email. Analytics refreshes every 30 seconds, repeated views of the same route within 30 seconds are grouped, and events older than 90 days are purged during analytics activity.

## Deploying frontend and API on Vercel

Deploy `backend/` and `frontend/` as **separate Vercel projects**. Set the backend project's Root Directory to `backend` and the frontend project's Root Directory to `frontend`. In each project, add the variables below under **Settings → Environment Variables** and select the `Production` environment. Never put backend secrets in the frontend project or commit them to Git.

**Backend Vercel project** (`api.workbitbd.com`):

| Variable | Production value |
| --- | --- |
| `ENVIRONMENT` | `production` |
| `ENABLE_MOCK_REWARDS` | `false` |
| `DATABASE_URL` | Production PostgreSQL connection string |
| `DIRECT_URL` | Optional direct database connection string for migrations; otherwise migrations use `DATABASE_URL` |
| `SECRET_KEY` | A newly generated, long random secret |
| `SESSION_SECRET` | A different newly generated, long random secret |
| `FRONTEND_ORIGIN` | `https://workbitbd.com` |
| `EMAIL_PROVIDER` | `brevo` |
| `BREVO_API_KEY` | A new Brevo API key with email-sending access |
| `EMAIL_FROM_ADDRESS` | A sender address verified in Brevo, for example `WorkBitBD <noreply@workbitbd.com>` |
| `OFFERWALL_GG_ENABLED` | `true` only after the publisher placement and callback are configured and tested |
| `OFFERWALL_GG_PUBLIC_KEY` | Offerwall.GG placement public key |
| `OFFERWALL_GG_SECRET_KEY` | Offerwall.GG server-side secret key |
| `OFFERWALL_GG_CURRENCY_NAME` | `USD` |
| `THEOREMREACH_ENABLED` | `false` during callback testing; set `true` after publisher approval |
| `THEOREMREACH_API_KEY` | TheoremReach publisher app API key |
| `THEOREMREACH_SECRET_KEY` | TheoremReach app secret for URL signatures |
| `THEOREMREACH_PARTNER_ID` | TheoremReach app/placement partner ID |
| `THEOREMREACH_CALLBACK_URL` | `https://api.workbitbd.com/api/v1/postbacks/theoremreach` |
| `THEOREMREACH_CURRENCY_NAME_SINGULAR` / `THEOREMREACH_CURRENCY_NAME_PLURAL` | `Credit` / `Credits` |
| `THEOREMREACH_EXCHANGE_RATE` | `10` or greater |
| `THEOREMREACH_DECIMALS_TO_DISPLAY` | `2` |

If enabling withdrawals, also set `WITHDRAWAL_ENCRYPTION_KEY` to a securely generated 32-byte URL-safe Base64 key. If enabling profile-photo uploads or dashboard banners, set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, and `CLOUDINARY_API_SECRET`. `REDIS_URL` is not required by the current API. Offerwall.GG variables belong only in the backend deployment environment; never put its secret key in the frontend project.

**Frontend Vercel project** (`workbitbd.com`):

| Variable | Production value |
| --- | --- |
| `NEXT_PUBLIC_API_URL` | `https://api.workbitbd.com` |
| `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY` | AmanahAds iframe instance key (public in the browser) |
| `NEXT_PUBLIC_AADS_ENABLED` | `true` |
| `NEXT_PUBLIC_AADS_UNIT_ID` | `2460426` |
| `NEXT_PUBLIC_AADS_UNIT_SIZE` | `Adaptive` |

`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY`, and the A-ADS variables belong only in the frontend project. Next.js embeds them during the frontend build, so redeploy the frontend after changing them. The AmanahAds iframe key and A-ADS unit ID are necessarily visible in the browser; do not use these variables for private API or postback secrets. Redeploy the backend after changing backend environment variables. Do not add a trailing `/api/v1` to `NEXT_PUBLIC_API_URL`; the frontend adds the API path itself.

For the A-ADS unit above, use `https://workbitbd.com/` as the ad-unit verification URL. The unit is rendered on the public homepage so A-ADS can check it without a signed-in session. The production frontend must be redeployed after adding these variables.

Generate separate application secrets locally with `python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48)); print('SESSION_SECRET=' + secrets.token_urlsafe(48))"`. Generate the withdrawal key with `python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`. Copy each value directly into the matching Vercel backend variable; do not paste secrets in chat, documentation, or source control. Do not reuse development credentials or the default values from `.env.example` in Production.

Before routing traffic to a backend release that changes the database schema, run `python -m alembic upgrade head` from `backend/` against that deployment's configured production database (`DIRECT_URL` when set, otherwise `DATABASE_URL`), then verify with `python -m alembic current`. Seed each new production database with `python -m app.services.seed` using that same database configuration. Do not run migrations against a different database or commit production connection strings.

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

Withdrawal requests use manual admin review and stay disabled until the encryption key and the administrator-managed USD/BDT rate are configured. Users can request bKash or Nagad payouts from withdrawable earning balance once it reaches the configured minimum (default $5); each request reserves the amount from available balance and snapshots the exchange rate and resulting BDT payout. After the reviewer has sent the payout, approving the request marks it paid immediately; rejection releases the reserved amount. Reviewer permissions are separate from read-only withdrawal access. Package prices and wallet balances are USD. To buy a package, users select it from **Packages**, pay its fixed BDT amount to the configured bKash/Nagad account, and submit the transaction reference. The initial configured rate is 1 USD = BDT 120; administrators can update it under **Admin → Withdrawals**. The package price, duration, BDT amount, and USD/BDT rate are snapshotted for admin review; renewals made before expiry extend from the current package expiry. Standalone BDT deposits and wallet-funded package purchases are retired; the admin deposit review remains available for previously submitted legacy requests. Configure `PACKAGE_BKASH_NUMBER` and `PACKAGE_NAGAD_NUMBER` for receiving accounts. Package catalog settings are managed under **Admin → Package settings**. Only externally approved package payments count toward the admin's **Registered user amount**; approved package records count toward referral-member eligibility and ranks. Referral links currently award 5% of the referred user's snapshotted package price to the inviter's wallet when an admin approves the package payment. The provider-neutral offer catalog remains development-only. Offerwall.GG's hosted wall and verified callback can be enabled separately after the publisher placement is approved and configured. Other offer networks remain unimplemented. Provider approval, incentive/country eligibility, fraud rules, data retention, and user-facing legal policies still require product, legal, security, and provider review before public launch. Daily bonuses, achievements, and notifications are not implemented and are not represented as available rewards.
