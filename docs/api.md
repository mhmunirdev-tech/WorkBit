# API

Base path: `/api/v1`.

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `POST /auth/verify-email`, `POST /auth/resend-verification`
- `POST /auth/forgot-password`, `POST /auth/reset-password`
- Registration and resend-verification deliver a single-use link to the `FRONTEND_ORIGIN/verify-email` page through Resend. Set `EMAIL_PROVIDER=resend`, `EMAIL_API_KEY`, and a verified `EMAIL_FROM_ADDRESS`; registration returns `503` rather than reporting success when email delivery is unavailable.
- `GET /dashboard`, `GET /admin/dashboard`
- Authenticated `GET /dashboard` returns the current user's account summary, ledger-backed balances and earnings, referral counts/rewards, a 90-day approved-earnings series, and recent wallet transactions. It retains the top-level wallet balance fields for compatibility and is scoped to the signed-in user.
- `GET /offers` returns the country-eligible offer catalog. Offer clicks must be recorded through `POST /offers/{id}/click`; the client cannot provide a reward or external destination.
- `GET /withdrawals`, `POST /withdrawals` let a signed-in, active, email-verified user view and request manual withdrawals. Destinations are encrypted at rest and omitted from user responses. Requests reserve wallet funds and require `WITHDRAWAL_ENCRYPTION_KEY`.
- Admin users with `withdrawals.view` can use `GET /admin/withdrawals` and `GET /admin/withdrawals/{id}`. The detail route returns the encrypted destination in plaintext only after logging the access. Mutations require the separate `withdrawals.review` permission and use `approve`, `reject`, and `complete` actions; state changes are written to admin audit logs, while wallet movements remain immutable and releases are appended as compensating ledger transactions.

Interactive OpenAPI documentation is served at `/docs`. API errors use `{ "success": false, "error": { "code": "…", "message": "…" } }`.
