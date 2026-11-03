# WorkBit Fraud Prevention Audit

**Status:** Initial audit and incremental baseline implementation  
**Reviewed:** 2026-11-03

This report distinguishes controls already present in WorkBit from the fraud-review features added in this increment. The application is **not yet a complete production-grade fraud prevention system**; the outstanding provider-dependent controls below must not be treated as active.

## Existing protections

| Area | Existing control | Remaining concern |
|---|---|---|
| Registration and email verification | Registration creates an unverified account; email verification codes expire, are hashed, and are limited to five attempts. | CAPTCHA and durable registration throttling are absent. |
| Authentication | Separate user/admin cookies, password hashing, signed expiring session JWTs, and hashed reset/action tokens. | Sessions are stateless; logout or password changes do not revoke already-issued tokens server-side. |
| Account eligibility | Package purchases and withdrawals check active status and email verification. Suspended and banned accounts cannot authenticate. | Phone numbers have no OTP verification flow. |
| Provider conversions | TheoremReach, BitLabs, CPX Research, and Offerwall.GG validate provider-specific callbacks; network transaction IDs have a database uniqueness constraint and providers support duplicate handling/reversals. | Invalid callback attempts are not represented in the fraud-review queue; callback validity is not a substitute for broader behavioral detection. |
| Wallet and rewards | Reward policies are server-side; wallet transactions are immutable; reward decisions are unique per conversion; reversal paths append ledger movements. | These paths were not redesigned in this change. |
| Admin access | Admin endpoints use role/permission dependencies; sensitive financial actions have admin logs. | No dedicated fraud console existed before this increment. |
| Rate limiting | A cooldown helper exists. | It is process-local memory, so it is bypassable across replicas/restarts and is not a production distributed limiter. |

## Added in this increment

- Persistent fraud events with risk level, status, reason, structured evidence, keyed IP fingerprint, review details, and 90-day opportunistic retention.
- Configurable thresholds for repeated registrations from one IP and repeated sign-in failures. The email in a failed-login event is masked.
- Shared-IP registration is only a risk signal; it never automatically restricts or bans an account.
- Admin fraud overview, event list/review, account restrict/suspend/ban/restore actions, and audit-log entries. Account actions are permission-gated and require a reason; restoring an unverified account as active is rejected.
- Immediate rejection of authenticated requests for accounts under review, suspended, or banned.
- Email-code-verified user appeal request and submission flow. An appeal is queued for manual review and does not restore access automatically.
- Privacy-policy and README updates. No security dependency was added and no wallet conversion rate, reward calculation, or accounting rule was changed.

## Gaps and deployment prerequisites

These controls are **not implemented or operational** in the current repository:

1. CAPTCHA on registration, login, and suspicious activity.
2. SMS/phone OTP verification.
3. VPN, proxy, datacenter, or IP-reputation intelligence.
4. Device-reuse detection, bot detection, and broader unusual-activity/referral-abuse detection.
5. Durable distributed rate limiting for login, registration, and OTP requests.
6. Fraud-queue instrumentation for invalid provider signatures, duplicate callback attempts, and suspicious survey/referral patterns.
7. A numeric risk score and configurable rules beyond the registration/login thresholds currently documented.

No provider credentials were supplied or configured for CAPTCHA, SMS, or IP reputation. Select providers, configure credentials and privacy/retention terms, and test them before enabling those controls. `REDIS_URL` exists in configuration, but the current cooldown implementation does not use Redis.

## Implementation risks and handling

- Shared networks (families, offices, schools, mobile carriers) can produce multiple accounts or failures from one IP. Such activity is recorded for human review and is never sufficient by itself to ban an account.
- IP fingerprints are keyed with the application session secret. Rotating that secret breaks correlation with older fingerprints.
- Event expiry is opportunistic: expired fraud events are deleted during subsequent security-event writes, not by a scheduled retention worker. Admin audit logs have separate retention behavior.
- Session tokens remain stateless. Account-status checks stop blocked users from using existing sessions, but server-side token revocation for other events is not implemented.
- Provider callback verification and wallet invariants were existing controls and passed the regression suite; this increment does not claim additional provider-specific anti-fraud detection.

## Database and validation

- Migration: `0026_fraud_events`, creating the indexed `fraud_events` table.
- The configured production database reported Alembic revision `0026_fraud_events` as head on the read-only revision check.
- Operational incident: the attempted migration validation resolved to the configured production `DIRECT_URL` and applied `0026_fraud_events` before the target was recognized. After disclosure, only a read-only revision check was authorized; it confirmed `0026_fraud_events` as head. No downgrade or further production write was attempted.
- Full backend test suite: **145 passed**. The final focused fraud/authentication run, after the last backend edits, passed **22 tests**.
- Frontend production build and TypeScript `--noEmit` check passed.
