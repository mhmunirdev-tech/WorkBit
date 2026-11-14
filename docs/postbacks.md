# Postbacks and conversions

Only `mock` is enabled in development. `POST /api/v1/postbacks/mock` accepts a typed test event, resolves a server-stored click, and writes one normalized conversion record. When the explicit development reward flag is enabled, unconfirmed conversions do not credit a wallet; an approved conversion applies the reward policy and credits `available_balance` immediately. Manual-review decisions remain uncredited until an authorized admin approves them. The development-only simulated ad completion uses this same approved-conversion flow.

The unique `(network_id, external_transaction_id)` constraint makes conversion creation idempotent even when application processes race. Reversal-like events update the original conversion rather than creating a second record, and reward decisions use a unique conversion reference to prevent duplicate credits.

## CPX Research

The CPX Research wall uses the authenticated WorkBit user's UUID as `ext_user_id`. Keep the CPX App Security Hash in the backend environment as `CPX_RESEARCH_SECURE_HASH`; never put it in a frontend variable or the callback URL. When CPX Security Check is enabled, the wall request's `secure_hash` is MD5 of `user_id + "-" + app_security_hash`.

Configure these backend environment variables:

- `CPX_RESEARCH_ENABLED=true` only after CPX publisher approval and callback setup.
- `CPX_RESEARCH_POSTBACK_ENABLED=false` keeps wallet callbacks disabled while allowing the wall to be displayed. Set it to `true` only after the callback endpoint is protected by a source-IP allowlist or another provider-approved verification method.
- `CPX_RESEARCH_APP_ID=37861` (the App ID shown in the supplied publisher screenshot).
- `CPX_RESEARCH_SECURE_HASH`: the current App Security Hash from CPX General Settings.

Set CPX's **Main Postback URL** to the following exact URL, without adding the Security Hash itself:

```text
https://api.workbitbd.com/api/v1/postbacks/cpx-research?status={status}&trans_id={trans_id}&user_id={user_id}&sub_id={subid_1}&sub_id_2={subid_2}&amount_local={amount_local}&amount_usd={amount_usd}&offer_id={offer_ID}&hash={secure_hash}&ip_click={ip_click}&type={type}
```

The callback validates CPX's documented MD5 signature `md5(trans_id + "-" + app_security_hash)` using constant-time comparison, rejects duplicate query parameters, requires a valid WorkBit UUID and USD wallet, and processes each `trans_id` once. Status `1` records a positive `amount_usd` through the WorkBit reward policy, including positive bonus callbacks. Status `2` reverses the matching original transaction; an unknown transaction is rejected so CPX can retry. Zero-amount callbacks are acknowledged without a wallet credit. `amount_local` is recorded for audit only; `amount_usd` is the provider payout used for WorkBit accounting.

Security limitation: CPX's documented callback hash covers `trans_id`, not the other callback fields. Restrict requests to this endpoint to CPX's dashboard-listed postback source IPs at the API firewall/WAF (`188.40.3.73`, `2a01:4f8:d0a:30ff::2`, and `157.90.97.92`) before enabling wallet credits. If the deployment proxy prevents reliable source-IP filtering, do not enable the callback for real rewards until CPX supplies a signature that covers the payout and user fields or the ingress can be protected.

The screenshot's Security Hash was visible in the conversation. Rotate it in CPX General Settings, save the new hash, and update `CPX_RESEARCH_SECURE_HASH` in the backend environment before enabling this callback. Do not share the new hash. Keep the CPX Test Mode inactive for live users; test callbacks only with a CPX test user/IP and confirm no real user is credited.

## BitLabs

The BitLabs integration uses the provider-hosted web offerwall in an iframe and the general Reward & Reconciliation callback. The authenticated `GET /api/v1/offers/providers/bitlabs/wall-url` endpoint returns the documented `https://web.bitlabs.ai/?uid=<workbit-user-id>&token=<app-api-token>` URL; package purchase is not required. The BitLabs App/API Token is necessarily visible in that iframe URL; do not use it as a secret. The URL is returned with `Cache-Control: no-store`.

Configure these backend environment variables:

- `BITLABS_ENABLED=true`
- `BITLABS_API_KEY`: BitLabs Integration page's **App/API Token**.
- `BITLABS_POSTBACK_SECRET`: BitLabs Integration page's **Secret Key**. BitLabs documents this key for callback hash verification.
- `BITLABS_CALLBACK_URL`: the exact public HTTPS endpoint URL, for example `https://api.workbitbd.com/api/v1/postbacks/bitlabs` (no query string or trailing slash).

Do not put the App/API Token, Secret Key, or Server-to-Server Key in frontend environment variables. This web iframe/callback flow uses the App/API Token and the Secret Key; it does not use the Server-to-Server Key.

In the BitLabs dashboard, configure the **Reward & Reconciliation Callback** to call the URL in `BITLABS_CALLBACK_URL`. Include the callback parameters `uid` (`USER:UID`), `tx` (`TX`), `usd` (`VALUE:USD`), `ref` (`REF`), and `activity_type` (`ACTIVITY:TYPE`). Offer metadata may also be included as `offer_id` (`OFFER:ID`), `task_id` (`OFFER:TASK:ID`), and `offer_state` (`OFFER:TASK:STATE`). BitLabs appends `hash` automatically. The callback endpoint verifies the HMAC-SHA1 over the exact callback URL and raw query string using the BitLabs **Secret Key**, rejects duplicate parameters and invalid signatures, and acknowledges dashboard `debug=true` tests without crediting a wallet.

Only completed callbacks with a positive `VALUE:USD` are processed. Screen-outs, start bonuses, pending/reconciled offer states, and zero-value callbacks do not create credits. `REF` links reconciliation callbacks to the original transaction; an eligible existing reward is reversed through WorkBit's reward ledger. Repeated transaction callbacks are idempotent. If a non-zero reconciliation amount differs from the original provider payout, WorkBit fails closed with a retry response rather than guessing how to apply a partial adjustment; review such cases before manually resending the callback. WorkBit treats BitLabs `VALUE:USD` as publisher payout and applies the configured WorkBit reward policy; check the BitLabs app-currency configuration so the amount shown in their wall is clear and consistent with the WorkBit credit. Test the endpoint with BitLabs' **Callback Tester** after saving the callback settings. The BitLabs offerwall is hidden when `BITLABS_ENABLED=false`.

## TheoremReach

TheoremReach appears in Explore offers as a provider-hosted web survey iframe. The authenticated `GET /api/v1/offers/providers/theoremreach/wall-url` endpoint does not require a WorkBit package purchase. It builds the direct entry URL server-side with the WorkBit user UUID, a unique entry transaction ID, the configured partner/placement ID, and the app currency settings. The URL is signed with the TheoremReach app secret using HMAC-SHA1 over the complete unsigned URL, then URL-safe Base64 encoding of the raw digest. The API key is required in the iframe URL by TheoremReach; the secret key is never sent to the browser. The URL response is marked `Cache-Control: no-store`.

Configure these backend environment variables:

- Keep `THEOREMREACH_ENABLED=false` while configuring. A correctly signed `debug=true` callback can be tested while disabled and never credits the wallet. Set it to `true` only after publisher approval to show the live wall and accept real rewards.
- `THEOREMREACH_API_KEY`: TheoremReach publisher app API key.
- `THEOREMREACH_SECRET_KEY`: The app secret used to sign entry and verify callbacks.
- `THEOREMREACH_PARTNER_ID`: optional partner ID for an Offerwall integration, if TheoremReach assigned one. Leave unset if the dashboard does not provide it.
- `THEOREMREACH_PLACEMENT_ID`: the ID generated for the currency placement in the app's **Placements** table. This is passed as `placement_id`; it is not the test user ID.
- `THEOREMREACH_CALLBACK_URL`: the exact public HTTPS endpoint, for example `https://api.workbitbd.com/api/v1/postbacks/theoremreach` (no query string or trailing slash).
- `THEOREMREACH_CURRENCY_NAME_SINGULAR=Credit` and `THEOREMREACH_CURRENCY_NAME_PLURAL=Credits`.
- `THEOREMREACH_EXCHANGE_RATE=10` (TheoremReach requires at least 10).
- `THEOREMREACH_DECIMALS_TO_DISPLAY=2`.

In the TheoremReach publisher app, use the HTTPS website URL, choose a rewards/GPT category if available, set the currency names and exchange rate to match the backend variables, and select server-side callbacks with reversals enabled. Create a currency placement and use its generated Placement ID as `THEOREMREACH_PLACEMENT_ID`. The Placement ID is passed as `placement_id`; it is different from the optional `partner_id`. Leave `THEOREMREACH_PARTNER_ID` unset unless TheoremReach supplies a separate partner ID for an Offerwall integration. Never substitute the test user ID or reuse the placement ID as the partner ID. Register the callback URL above and map its callback fields to `user_id`, `tx_id`, `currency`, `reward`, `external_transaction_id`, `partner_id`, `reversal`, and `debug` where available. The handler accepts TheoremReach's documented `reward_amount_in_dollars` alias for `currency` and `transaction_id` alias for `tx_id`. The `currency`/`reward_amount_in_dollars` field is treated as USD publisher payout; the separate `reward` app-currency field is recorded only as metadata. WorkBit applies its reward policy to the USD payout and does not trust the client-side iframe to credit balances.

The callback verifies the URL-safe Base64 HMAC-SHA1 over the exact HTTPS callback URL and raw query string before the final `hash` parameter, using the configured app secret. Duplicate query parameters and mismatched partner IDs are rejected. A correctly signed `debug=true` callback is acknowledged without a wallet credit, even while the integration is disabled; real reward callbacks are rejected until `THEOREMREACH_ENABLED=true`. Signed rewards are idempotent by TheoremReach `tx_id`; a reversal must carry the original transaction ID, negative USD amount, and `reversal=true`, and is applied once through WorkBit's reward ledger. Test the callback in the publisher dashboard before enabling the live wall. Follow TheoremReach's [offerwall guide](https://theoremreach.com/docs/offerwall), [web integration guide](https://theoremreach.com/docs/web), and [router callback documentation](https://theoremreach.com/docs/routers).

## Offerwall.GG

Explore offers displays a WorkBit-native Offerwall.GG card catalog (not the provider-hosted full-page wall) when `OFFERWALL_GG_ENABLED=true` and the backend public/secret keys are configured. The authenticated `GET /api/v1/offers/providers/offerwall-gg/catalog` endpoint does not require a WorkBit package purchase and requests targeted, paginated inventory using the stable WorkBit user UUID and country `BD`, regardless of the account's country. Offerwall.GG therefore returns eligible inventory for Bangladesh across its available categories. The backend sends the secret only in the `X-Api-Key` header, validates the response and user-specific tracked click URLs, and sets `Cache-Control: no-store`. The browser follows only Offerwall.GG's returned click URL, never a direct advertiser URL. The older `GET /api/v1/offers/providers/offerwall-gg/wall-url` endpoint remains available and generates the documented HMAC-SHA256 signature over the sorted `appId` and user UUID; it is not used by the Explore offers UI.

The catalog supports `page` (1-based), `limit` (1-200), `search`, and `category`. The frontend starts with 50 offers and requests the next page when the user chooses **Load more offers**. Country is fixed to Bangladesh (`BD`) and device targeting comes from the request's browser user-agent. The returned estimate applies WorkBit's currently active reward policy, including its rounding; it is not the provider's gross payout and does not guarantee a credit.

Register `https://api.workbitbd.com/api/v1/postbacks/offerwall-gg` as the placement callback and configure the provider to append all callback fields (leave the callback URL without macros). The endpoint accepts the documented GET query-string and POST form-urlencoded modes. It verifies HMAC-SHA256 over the exact decoded `userId:transactionId:currencyAmount` fields with constant-time comparison, validates the configured currency, and never uses unsigned `payoutUsd` for a wallet reward. `test=1` callbacks are signature-checked and acknowledged without database or wallet changes. A durable callback receives `200 OK`; a failure receives a non-2xx response so the provider can retry.

Offerwall.GG does not include `status` in its signature. The signed amount's sign is authoritative for credit versus reversal, and the endpoint requires the unsigned `status` to agree with that sign. A reversal must match the original transaction, user, currency, and amount; the same transaction ID is reused, and repeated reversals cannot debit twice. A reversed reward can make the USD wallet balance negative when the amount has already been withdrawn. This debt offsets future approved earnings, and withdrawals remain disabled until the withdrawable balance recovers.

WorkBit wallet currency is USD, so configure the Offerwall.GG placement currency name as `USD` with one placement unit per USD. WorkBit then applies its configured reward policy (seeded default: 70% user reward / 30% platform share) only after provider-confirmed completion. Do not enable the wall if the placement uses a different currency or exchange rate. Offerwall.GG publisher payout is separate from user withdrawals: it publicly lists a $30 minimum and NET30 terms and does not list bKash/Nagad as publisher payout options; WorkBit's own user payouts remain the existing manual bKash/Nagad workflow.

## Offerwall.me

Offerwall.me offers are displayed as native WorkBit cards in Explore offers. The backend requests the offer catalog using the signed-in user's UUID, trusted client IP, country, and one-hour HMAC-SHA256 identity signature. The public API key, API bearer token, and private placement secret are backend-only values. Enable `OFFERWALL_ME_ENABLED=true` only after configuring the placement and its callback.

Configure these backend environment variables:

- `OFFERWALL_ME_PUBLIC_API_KEY`: the placement's public API key.
- `OFFERWALL_ME_API_TOKEN`: the private bearer token used by Offerwall.me's server-side offer API.
- `OFFERWALL_ME_SECRET_KEY`: the private placement secret.
- `OFFERWALL_ME_CURRENCY_NAME=Points`.
- `OFFERWALL_ME_EXCHANGE_RATE=1000`: configure the placement for 1000 Points per $1 payout, rounded to 2 decimal places. The catalog checks rewards at that precision and uses the provider's USD payout for WorkBit reward estimates. The WorkBit wallet remains USD; the callback converts provider Points to the signed USD payout before applying WorkBit's reward policy.
- `OFFERWALL_ME_ENABLED=false` while configuring; set to `true` after testing the signed catalog request.
- `OFFERWALL_ME_POSTBACK_ENABLED=false` until the Vercel firewall is configured and the callback is tested; then set to `true`.

In Offerwall.me, choose **Single Postback** and enter this exact URL:

```text
https://api.workbitbd.com/api/v1/postbacks/offerwall-me
```

The endpoint accepts the provider's POST form callback, rejects duplicate fields, verifies `md5(subId + transId + reward + secretKey)`, validates the configured reward currency, exchange rate and payout, requires a valid WorkBit UUID, and processes credits and status `2` reversals idempotently. WorkBit derives the USD amount from the signed `reward` and configured exchange rate, then applies its reward policy. Configure the placement currency as `Points` at 1000 units per USD and use the matching backend environment values. Do not label points as USD in the provider wall.

The provider signature does not cover status, payout, or all other callback fields. Before enabling rewards, create a Vercel Firewall rule to allow the callback path only from Offerwall.me's documented postback IPs (`95.216.65.163` and `2a01:4f9:2b:1dc::2`) and deny all other source IPs. WorkBit also checks the trusted `X-Forwarded-For` source IP against this list. Do not enable `OFFERWALL_ME_POSTBACK_ENABLED` if the deployed proxy does not provide a trustworthy client IP. The callback returns `ok` with HTTP 200 after durable processing; failures return non-2xx so Offerwall.me can retry.

Offerwall.me requires signed user IDs from 1 October 2026. WorkBit generates the required expiring HMAC-SHA256 identity signature server-side. Do not expose the private placement secret or API bearer token, or share generated signed requests/tracking URLs.

WorkBit uses Offerwall.me's documented `GET https://offerwall.me/offerapi.php` API. It derives the USD amount used for WorkBit reward estimates from the returned Points reward and configured exchange rate, matching the signed callback amount rather than the API's separate gross `payout` field. It validates each returned start URL and country, applies the active reward policy, and opens the returned tracking URL unchanged when the user chooses **Start offer**. The offer API has no documented pagination parameter, so the page's **Load more offers** control reveals the next batch from the fetched catalog. The provider may include a per-user tracking URL in the API response; the endpoint is authenticated, marked no-store, and never logs or persists those links.

## BitcoTasks

The BitcoTasks SDK v2 wall is shown only when `BITCOTASKS_ENABLED=true` and `BITCOTASKS_API_KEY` is configured. Its API key and 32-character WorkBit UUID-hex `subId` are intentionally browser-visible; the Secret Key must remain in the backend environment. WorkBit uses that Secret Key to produce a per-user HMAC-SHA256 `sig` for the SDK's optional signed Worker Balance tags. Set the website's postback URL in BitcoTasks to:

```text
https://api.workbitbd.com/api/v1/postbacks/bitcotasks
```

Configure `BITCOTASKS_SECRET_KEY`, `BITCOTASKS_CURRENCY_NAME`, and `BITCOTASKS_EXCHANGE_RATE` to match the BitcoTasks app exactly. Keep `BITCOTASKS_POSTBACK_ENABLED=false` until its callback is tested and a trusted ingress rule allows only BitcoTasks' documented postback IP `45.14.135.48`; WorkBit also checks that source IP from the deployment's trusted `X-Forwarded-For` header. The handler accepts HTTP POST form callbacks, rejects duplicate parameters, verifies `md5(subId + transId + reward + secretKey)` with constant-time comparison, and acknowledges correctly signed `debug=1` callbacks without crediting. Since the provider signature does not cover `status` or `payout`, the source-IP restriction is required as an additional guard.

For live callbacks, WorkBit converts the signed reward to USD using the configured exchange rate, does not trust the unsigned `payout` field for wallet accounting, and uses the existing reward-policy ledger. Status `1` credits idempotently; status `2` must reference the original transaction and reverses it idempotently. The SDK's Balance tab remains available for provider-side withdrawals; when BitcoTasks Worker Balance is enabled, WorkBit receives the reward callback when the user withdraws there (or when Auto Withdraw sends it). The provider's separate Banner, PopUp/PopAds, and Direct Link placements are not part of this SDK integration.

Other offer providers remain disabled. Their adapters, request formats, and callback signature implementations must be added only after reviewing each provider's official documentation and testing with its sandbox. Do not infer formats from Offerwall.GG or another network.
