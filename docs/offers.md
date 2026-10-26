# Offer and redirect architecture

The catalog is provider-neutral. Providers emit normalized `OfferRead` values; the core service applies country, category, device, pagination, and ranking rules.

`POST /api/v1/offers/{id}/click` creates a server-owned click record. No client reward, payout, or destination is accepted. `POST /api/v1/offers/{id}/redirect` is intentionally unavailable for mock/unconfigured providers and returns a controlled 503 rather than fabricating an external URL.

The offer-network registry is seeded with Lootably, AdGem, CPAlead, Offerwall.GG, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU. All ten start disabled with `NOT_CONFIGURED` status. Credential columns do not exist: `api_key_env` and `secret_key_env` contain environment-variable names only, never secret values. Publisher/placement IDs and provider API base URLs are nullable until verified configuration is available. `postback_url` is WorkBit's relative callback route, not a provider-specific parameter format.

The adapter registry is an interface boundary, not a claim that these providers have working integrations. Lootably, AdGem, CPAlead, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU remain disabled; their provider-specific callback routes return 503 until individually implemented from official documentation. Offerwall.GG is integrated as its hosted wall in Explore offers with signed user identity and verified server-to-server callbacks, but it does not yet populate the provider-neutral offer catalog. Mock offer data and mock postbacks are development-only; production offer listing fails closed.

Advertising and rewarded/display ads use the separate `ad_networks` registry and adapter boundary. They are not offer inventory and do not create wallet rewards through the offer conversion pipeline.

Ad display providers are isolated under `frontend/components/ads/providers/<provider>/`, while the provider-neutral page selector lives in `frontend/components/ads/ads-placements.tsx`. Add a provider-specific component there and register it with the selector; do not place provider script or URL details in the offers catalog. Backend adapters for providers that require server integration belong under `backend/app/integrations/ad_providers/`; the shared contract and registry are separate from provider-specific code.

The Explore offers page can display AmanahAds placements when the frontend build has `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY` configured. `AmanahAd` supports the documented iframe and script-based `div` render modes and the provider's five documented sizes. The page uses iframe mode by default and offers a user-initiated popup; it does not open repeated or unsolicited popups. The optional `useAmanahPopup` hook listens only to `amanah:popup-close` messages from `https://amanahads.com`.

An instance key used by browser code is visible to users and must not be treated as an API or postback secret. Use the dev key only for local testing and use the provider's approved production key for the production domain. These placements display ads only: they do not verify an offer completion or credit a WorkBit wallet. Do not advertise or issue user rewards for these placements until an authenticated provider callback and an approved reward flow are implemented and tested.
