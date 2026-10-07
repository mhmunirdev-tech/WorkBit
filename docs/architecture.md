# Architecture

WorkBit is a monorepo with a Next.js browser client and a versioned FastAPI service. Browser authentication uses a signed HTTP-only cookie; no browser token storage is required. PostgreSQL owns durable state, Redis is reserved for rate limiting, caching, and worker coordination, and workers must not mutate balances without transactional ledger logic.

The offer engine and ad monetization are separate integration boundaries. `offer_networks` is the offerwall provider registry; `ad_networks` is a separate registry for display/rewarded ad products. The offer pipeline owns sync, country/device targeting, click attribution, normalized conversions, verified postbacks, fraud assessment, reward decisions, and ledger credits.

The registry contains Lootably, AdGem, CPAlead, Offerwall.GG, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU as `NOT_CONFIGURED` and disabled. Provider credentials are never database fields: only environment-variable names may be stored as references. API keys and postback secrets are supplied through environment/secret management. A registry row does not mean an integration is operational.

Provider adapters must be implemented against each provider's current official publisher documentation, then explicitly enabled after credentials, publisher/placement IDs, supported targeting, postback verification, and end-to-end tests are configured. Until then, offer sync, redirects, and provider-specific postbacks fail closed. The mock catalog/postback remain development-only and cannot be treated as production earning or create rewards unless the explicit development rewards flag is enabled. Ad placements are not mixed into the offer catalog or wallet reward pipeline.

Manual withdrawals are available only when the encryption key is configured: requests reserve funds through the wallet ledger, and authorized reviewers approve, reject, or complete them with audit records. Automated referral rewards, daily bonuses, achievements, and notifications are not implemented; the dashboard must not present those systems as active or imply that they can be claimed.
