# Offer and redirect architecture

The catalog is provider-neutral. Providers emit normalized `OfferRead` values; the core service applies country, category, device, pagination, and ranking rules.

`POST /api/v1/offers/{id}/click` creates a server-owned click record. No client reward, payout, or destination is accepted. `POST /api/v1/offers/{id}/redirect` is intentionally unavailable for mock/unconfigured providers and returns a controlled 503 rather than fabricating an external URL.

The offer-network registry is seeded with Lootably, AdGem, CPAlead, Offerwall.GG, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU. All ten start disabled with `NOT_CONFIGURED` status. Credential columns do not exist: `api_key_env` and `secret_key_env` contain environment-variable names only, never secret values. Publisher/placement IDs and provider API base URLs are nullable until verified configuration is available. `postback_url` is WorkBit's relative callback route, not a provider-specific parameter format.

The adapter registry is an interface boundary, not a claim that these providers have working integrations. Each provider implementation must separately normalize offers, build tracking URLs, and verify/normalize callbacks using that provider's current official documentation. Provider-specific callback routes return 503 until such an implementation is configured. Do not infer callback parameter names or signatures from another network. Mock offer data and mock postbacks are development-only; production offer listing fails closed.

Advertising and rewarded/display ads use the separate `ad_networks` registry and adapter boundary. They are not offer inventory and do not create wallet rewards through the offer conversion pipeline.
