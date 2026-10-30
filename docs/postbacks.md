# Postbacks and conversions

Only `mock` is enabled in development. `POST /api/v1/postbacks/mock` accepts a typed test event, resolves a server-stored click, and writes one normalized conversion record. When the explicit development reward flag is enabled, unconfirmed conversions do not credit a wallet; an approved conversion applies the reward policy and credits `available_balance` immediately. Manual-review decisions remain uncredited until an authorized admin approves them. The development-only simulated ad completion uses this same approved-conversion flow.

The unique `(network_id, external_transaction_id)` constraint makes conversion creation idempotent even when application processes race. Reversal-like events update the original conversion rather than creating a second record, and reward decisions use a unique conversion reference to prevent duplicate credits.

## BitLabs

The BitLabs integration uses the provider-hosted web offerwall in an iframe and the general Reward & Reconciliation callback. The authenticated `GET /api/v1/offers/providers/bitlabs/wall-url` endpoint requires an approved active WorkBit earning package and returns the documented `https://web.bitlabs.ai/?uid=<workbit-user-id>&token=<app-api-token>` URL. The BitLabs App/API Token is necessarily visible in that iframe URL; do not use it as a secret. The URL is returned with `Cache-Control: no-store`.

Configure these backend environment variables:

- `BITLABS_ENABLED=true`
- `BITLABS_API_KEY`: BitLabs Integration page's **App/API Token**.
- `BITLABS_POSTBACK_SECRET`: BitLabs Integration page's **Secret Key**. BitLabs documents this key for callback hash verification.
- `BITLABS_CALLBACK_URL`: the exact public HTTPS endpoint URL, for example `https://api.workbitbd.com/api/v1/postbacks/bitlabs` (no query string or trailing slash).

Do not put the App/API Token, Secret Key, or Server-to-Server Key in frontend environment variables. This web iframe/callback flow uses the App/API Token and the Secret Key; it does not use the Server-to-Server Key.

In the BitLabs dashboard, configure the **Reward & Reconciliation Callback** to call the URL in `BITLABS_CALLBACK_URL`. Include the callback parameters `uid` (`USER:UID`), `tx` (`TX`), `usd` (`VALUE:USD`), `ref` (`REF`), and `activity_type` (`ACTIVITY:TYPE`). Offer metadata may also be included as `offer_id` (`OFFER:ID`), `task_id` (`OFFER:TASK:ID`), and `offer_state` (`OFFER:TASK:STATE`). BitLabs appends `hash` automatically. The callback endpoint verifies the HMAC-SHA1 over the exact callback URL and raw query string using the BitLabs **Secret Key**, rejects duplicate parameters and invalid signatures, and acknowledges dashboard `debug=true` tests without crediting a wallet.

Only completed callbacks with a positive `VALUE:USD` are processed. Screen-outs, start bonuses, pending/reconciled offer states, and zero-value callbacks do not create credits. `REF` links reconciliation callbacks to the original transaction; an eligible existing reward is reversed through WorkBit's reward ledger. Repeated transaction callbacks are idempotent. If a non-zero reconciliation amount differs from the original provider payout, WorkBit fails closed with a retry response rather than guessing how to apply a partial adjustment; review such cases before manually resending the callback. WorkBit treats BitLabs `VALUE:USD` as publisher payout and applies the configured WorkBit reward policy; check the BitLabs app-currency configuration so the amount shown in their wall is clear and consistent with the WorkBit credit. Test the endpoint with BitLabs' **Callback Tester** after saving the callback settings. The BitLabs offerwall is hidden when `BITLABS_ENABLED=false`.

## TheoremReach

TheoremReach appears in Explore offers as a provider-hosted web survey iframe. The authenticated `GET /api/v1/offers/providers/theoremreach/wall-url` endpoint requires an approved active WorkBit earning package. It builds the direct entry URL server-side with the WorkBit user UUID, a unique entry transaction ID, the configured partner/placement ID, and the app currency settings. The URL is signed with the TheoremReach app secret using HMAC-SHA1 over the complete unsigned URL, then URL-safe Base64 encoding of the raw digest. The API key is required in the iframe URL by TheoremReach; the secret key is never sent to the browser. The URL response is marked `Cache-Control: no-store`.

Configure these backend environment variables:

- Keep `THEOREMREACH_ENABLED=false` while configuring. A correctly signed `debug=true` callback can be tested while disabled and never credits the wallet. Set it to `true` only after publisher approval to show the live wall and accept real rewards.
- `THEOREMREACH_API_KEY`: TheoremReach publisher app API key.
- `THEOREMREACH_SECRET_KEY`: The app secret used to sign entry and verify callbacks.
- `THEOREMREACH_PARTNER_ID`: the app/placement partner ID shown in the publisher dashboard.
- `THEOREMREACH_CALLBACK_URL`: the exact public HTTPS endpoint, for example `https://api.workbitbd.com/api/v1/postbacks/theoremreach` (no query string or trailing slash).
- `THEOREMREACH_CURRENCY_NAME_SINGULAR=Credit` and `THEOREMREACH_CURRENCY_NAME_PLURAL=Credits`.
- `THEOREMREACH_EXCHANGE_RATE=10` (TheoremReach requires at least 10).
- `THEOREMREACH_DECIMALS_TO_DISPLAY=2`.

In the TheoremReach publisher app, use the HTTPS website URL, choose a rewards/GPT category if available, set the currency names and exchange rate to match the backend variables, and select server-side callbacks with reversals enabled. Register the callback URL above and map its callback fields to `user_id`, `tx_id`, `currency`, `reward`, `external_transaction_id`, `partner_id`, `reversal`, and `debug` where available. The handler accepts TheoremReach's documented `reward_amount_in_dollars` alias for `currency` and `transaction_id` alias for `tx_id`. The `currency`/`reward_amount_in_dollars` field is treated as USD publisher payout; the separate `reward` app-currency field is recorded only as metadata. WorkBit applies its reward policy to the USD payout and does not trust the client-side iframe to credit balances.

The callback verifies the URL-safe Base64 HMAC-SHA1 over the exact HTTPS callback URL and raw query string before the final `hash` parameter, using the configured app secret. Duplicate query parameters and mismatched partner IDs are rejected. A correctly signed `debug=true` callback is acknowledged without a wallet credit, even while the integration is disabled; real reward callbacks are rejected until `THEOREMREACH_ENABLED=true`. Signed rewards are idempotent by TheoremReach `tx_id`; a reversal must carry the original transaction ID, negative USD amount, and `reversal=true`, and is applied once through WorkBit's reward ledger. Test the callback in the publisher dashboard before enabling the live wall. Follow TheoremReach's [offerwall guide](https://theoremreach.com/docs/offerwall), [web integration guide](https://theoremreach.com/docs/web), and [router callback documentation](https://theoremreach.com/docs/routers).

## Offerwall.GG

Explore offers displays a WorkBit-native Offerwall.GG card catalog (not the provider-hosted full-page wall) when `OFFERWALL_GG_ENABLED=true` and the backend public/secret keys are configured. The authenticated `GET /api/v1/offers/providers/offerwall-gg/catalog` endpoint requires an approved active earning package and requests targeted, paginated inventory using the stable WorkBit user UUID and country `BD`, regardless of the account's country. Offerwall.GG therefore returns eligible inventory for Bangladesh across its available categories. The backend sends the secret only in the `X-Api-Key` header, validates the response and user-specific tracked click URLs, and sets `Cache-Control: no-store`. The browser follows only Offerwall.GG's returned click URL, never a direct advertiser URL. The older `GET /api/v1/offers/providers/offerwall-gg/wall-url` endpoint remains available and generates the documented HMAC-SHA256 signature over the sorted `appId` and user UUID; it is not used by the Explore offers UI.

The catalog supports `page` (1-based), `limit` (1-200), `search`, and `category`. The frontend starts with 50 offers and requests the next page when the user chooses **Load more offers**. Country is fixed to Bangladesh (`BD`) and device targeting comes from the request's browser user-agent. The returned estimate applies WorkBit's currently active reward policy, including its rounding; it is not the provider's gross payout and does not guarantee a credit.

Register `https://api.workbitbd.com/api/v1/postbacks/offerwall-gg` as the placement callback and configure the provider to append all callback fields (leave the callback URL without macros). The endpoint accepts the documented GET query-string and POST form-urlencoded modes. It verifies HMAC-SHA256 over the exact decoded `userId:transactionId:currencyAmount` fields with constant-time comparison, validates the configured currency, and never uses unsigned `payoutUsd` for a wallet reward. `test=1` callbacks are signature-checked and acknowledged without database or wallet changes. A durable callback receives `200 OK`; a failure receives a non-2xx response so the provider can retry.

Offerwall.GG does not include `status` in its signature. The signed amount's sign is authoritative for credit versus reversal, and the endpoint requires the unsigned `status` to agree with that sign. A reversal must match the original transaction, user, currency, and amount; the same transaction ID is reused, and repeated reversals cannot debit twice. A reversed reward can make the USD wallet balance negative when the amount has already been withdrawn. This debt offsets future approved earnings, and withdrawals remain disabled until the withdrawable balance recovers.

WorkBit wallet currency is USD, so configure the Offerwall.GG placement currency name as `USD` with one placement unit per USD. WorkBit then applies its configured reward policy (seeded default: 80% user reward / 20% platform share). Do not enable the wall if the placement uses a different currency or exchange rate. Offerwall.GG publisher payout is separate from user withdrawals: it publicly lists a $30 minimum and NET30 terms and does not list bKash/Nagad as publisher payout options; WorkBit's own user payouts remain the existing manual bKash/Nagad workflow.

Other offer providers remain disabled. Their adapters, request formats, and callback signature implementations must be added only after reviewing each provider's official documentation and testing with its sandbox. Do not infer formats from Offerwall.GG or another network.
