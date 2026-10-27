# API

Base path: `/api/v1`.

- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`
- `POST /auth/verify-email`, `POST /auth/resend-verification`
- `POST /auth/forgot-password`, `POST /auth/reset-password`
- Registration and resend-verification deliver a single-use code through Resend or Brevo. Set the matching `RESEND_API_KEY` or `BREVO_API_KEY` and an `EMAIL_FROM_ADDRESS` verified with that provider. With one provider key configured it is selected automatically; if both are set, select one with `EMAIL_PROVIDER=resend` or `EMAIL_PROVIDER=brevo`. Registration returns `503` rather than reporting success when email delivery is unavailable.
- `GET /dashboard`, `GET /admin/dashboard`
- Authenticated `GET /dashboard` returns the current user's account summary, ledger-backed balances and earnings, referral counts/rewards, a 90-day approved-earnings series, and recent wallet transactions. It retains the top-level wallet balance fields for compatibility and is scoped to the signed-in user.
- `GET /offers` returns the country-eligible development demo catalog only; it is unavailable in production until an approved provider is configured. Offer clicks must be recorded through `POST /offers/{id}/click`; the client cannot provide a reward or external destination.
- `GET /withdrawals`, `POST /withdrawals` let a signed-in, active, email-verified user view and request manual withdrawals. Destinations are encrypted at rest and omitted from user responses. Requests reserve wallet funds and require `WITHDRAWAL_ENCRYPTION_KEY`.
- Admin users with `withdrawals.view` can use `GET /admin/withdrawals` and `GET /admin/withdrawals/{id}`. The detail route returns the encrypted destination in plaintext only after logging the access. Mutations require the separate `withdrawals.review` permission. Approve moves a request to processing; reject releases reserved funds; complete requires the payment provider's transaction ID, stores it with the paid timestamp, and moves the request to `PAID`. Transaction IDs are unique per payout method. State changes are written to admin audit logs, while wallet movements remain immutable and releases are appended as compensating ledger transactions.

Interactive OpenAPI documentation is served at `/docs`. API errors use `{ "success": false, "error": { "code": "…", "message": "…" } }`.
