# Database foundation

Initial tables: `users`, `profiles`, `roles`, `permissions`, `user_roles`, `role_permissions`, `wallets`, `wallet_transactions`, `auth_tokens`, and `admin_logs`.

Each user has exactly one wallet. Monetary values use `NUMERIC(18,8)` and Python `Decimal`; no floating point columns are used. `wallet_transactions` exists as an immutable ledger foundation but Phase 1 does not create financial transactions.

`offer_networks` stores non-secret provider configuration metadata and references to secret environment-variable names. It is seeded with ten disabled offerwall provider slots; `api_key_env` and `secret_key_env` are names, not credential values. `ad_networks` stores ad monetization configuration separately. Both registries default to `enabled=false` and `status=NOT_CONFIGURED`.
