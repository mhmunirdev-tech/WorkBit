# Offer and redirect architecture

The catalog is provider-neutral. Providers emit normalized `OfferRead` values; the core service applies country, category, device, pagination, and ranking rules.

`POST /api/v1/offers/{id}/click` creates a server-owned click record. No client reward, payout, or destination is accepted. `POST /api/v1/offers/{id}/redirect` is intentionally unavailable for mock/unconfigured providers and returns a controlled 503 rather than fabricating an external URL.

The offer-network registry is seeded with Lootably, AdGem, CPAlead, Offerwall.GG, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU. All ten start disabled with `NOT_CONFIGURED` status. Credential columns do not exist: `api_key_env` and `secret_key_env` contain environment-variable names only, never secret values. Publisher/placement IDs and provider API base URLs are nullable until verified configuration is available. `postback_url` is WorkBit's relative callback route, not a provider-specific parameter format.

The adapter registry is an interface boundary, not a claim that these providers have working integrations. Lootably, AdGem, CPAlead, Monlix, BitLabs, AdGate Media, Torox, AdswedMedia, and RevU remain disabled; their provider-specific callback routes return 503 until individually implemented from official documentation. Offerwall.GG's official offers API populates a separate, WorkBit-native card catalog in Explore offers; users follow the provider-issued, user-specific `clickUrl`, and the verified server-to-server callback remains the only source of wallet credits. The hosted Offerwall.GG wall URL endpoint remains available for compatibility, but Explore offers does not embed the provider's full wall. Mock offer data and mock postbacks are development-only; production offer listing fails closed.

The authenticated `GET /api/v1/offers/providers/offerwall-gg/catalog` endpoint requires an approved active earning package. It fetches up to 200 offers per page from the official API on the backend, passes the stable WorkBit user UUID and the account's stored country, and sends the secret only in the `X-Api-Key` header. The API response is validated before its tracked click URLs are returned; client caching is disabled. The Explore page displays responsive offer cards with provider, requirements, categories, and a WorkBit reward estimate, and supports searching and filtering the loaded offers.

Offerwall.GG's placement currency must be `USD` at exactly one unit per USD, matching the WorkBit wallet and configured callback currency. The displayed user estimate applies the active WorkBit reward policy and rounding; it is not the provider's gross payout and is not guaranteed until the conversion is verified. For each category or search view, further inventory is available with the page's **Load more offers** button.

Advertising and rewarded/display ads use the separate `ad_networks` registry and adapter boundary. They are not offer inventory and do not create wallet rewards through the offer conversion pipeline.

## CPX Research survey wall

The CPX Research frame is rendered on `/offers` after the BitLabs wall. It uses the publisher App ID `37861` shown in the supplied CPX dashboard guide and the authenticated WorkBit user's UUID as `ext_user_id`. The backend creates CPX's documented `secure_hash` using MD5 of `ext_user_id`, an underscore, and the server-side CPX Security Hash (`md5(user_id + "_" + security_hash)`). The CPX secret must never be exposed in a `NEXT_PUBLIC_*` variable.

Set `CPX_RESEARCH_ENABLED=true`, `CPX_RESEARCH_APP_ID=37861`, and `CPX_RESEARCH_SECURE_HASH` in the backend environment after configuring the CPX publisher dashboard. The route requires an approved earning package and returns a no-store response.

Configure the Main Postback URL as described in [postbacks.md](./postbacks.md). The callback verifies the dashboard's `md5(trans_id + "-" + app_security_hash)` hash, credits positive USD amounts through the WorkBit reward policy, is idempotent by transaction ID, and reverses the original reward when CPX sends status `2`. Only status `1` and `2` callbacks are accepted. The dashboard currency factor must match the WorkBit wallet currency; WorkBit wallets use USD.

Ad display providers are isolated under `frontend/components/ads/providers/<provider>/`, while the provider-neutral page selector lives in `frontend/components/ads/ads-placements.tsx`. Add a provider-specific component there and register it with the selector; do not place provider script or URL details in the offers catalog. Backend adapters for providers that require server integration belong under `backend/app/integrations/ad_providers/`; the shared contract and registry are separate from provider-specific code.

The Explore offers page can display AmanahAds placements when the frontend build has `NEXT_PUBLIC_AMANAHADS_INSTANCE_KEY` configured. `AmanahAd` supports the documented iframe and script-based `div` render modes and the provider's five documented sizes. The page uses iframe mode by default and offers a user-initiated popup; it does not open repeated or unsolicited popups. The optional `useAmanahPopup` hook listens only to `amanah:popup-close` messages from `https://amanahads.com`.

An instance key used by browser code is visible to users and must not be treated as an API or postback secret. Use the dev key only for local testing and use the provider's approved production key for the production domain. These placements display ads only: they do not verify an offer completion or credit a WorkBit wallet. Do not advertise or issue user rewards for these placements until an authenticated provider callback and an approved reward flow are implemented and tested.
