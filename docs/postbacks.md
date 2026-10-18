# Postbacks and conversions

Only `mock` is enabled in development. `POST /api/v1/postbacks/mock` accepts a typed test event, resolves a server-stored click, writes one normalized conversion record, and never writes to a wallet. When the explicit development reward flag is enabled, a valid conversion creates one pending reward decision. A later provider approval updates the conversion but does not bypass admin review; approved rewards move from `pending_balance` to `available_balance` only after authorized admin approval and the reward policy's `pending_period_days` have elapsed.

The unique `(network_id, external_transaction_id)` constraint makes conversion creation idempotent even when application processes race. Reversal-like events update the original conversion rather than creating a second record, and reward decisions use a unique conversion reference to prevent duplicate credits.

Lootably, AdGem, and CPAlead are disabled. Their adapter, redirect, request, and signature implementations must be added only after reviewing current official publisher documentation and providing approved credentials. Do not enable real offer earnings until at least one provider's server-to-server signature validation and reversal flow are configured and tested.
