# Postbacks and conversions

Only `mock` is enabled in development. `POST /api/v1/postbacks/mock` accepts a typed test event, resolves a server-stored click, and writes one normalized conversion record. When the explicit development reward flag is enabled, unconfirmed conversions do not credit a wallet; an approved conversion applies the reward policy and credits `available_balance` immediately. Manual-review decisions remain uncredited until an authorized admin approves them. The development-only simulated ad completion uses this same approved-conversion flow.

The unique `(network_id, external_transaction_id)` constraint makes conversion creation idempotent even when application processes race. Reversal-like events update the original conversion rather than creating a second record, and reward decisions use a unique conversion reference to prevent duplicate credits.

Lootably, AdGem, and CPAlead are disabled. Their adapter, redirect, request, and signature implementations must be added only after reviewing current official publisher documentation and providing approved credentials. Do not enable real offer earnings until at least one provider's server-to-server signature validation and reversal flow are configured and tested.
