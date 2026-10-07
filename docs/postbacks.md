# Postbacks and conversions

Only `mock` is enabled in development. `POST /api/v1/postbacks/mock` accepts a typed test event, resolves a server-stored click, writes one normalized conversion record, and never writes to a wallet.

The unique `(network_id, external_transaction_id)` constraint makes conversion creation idempotent even when application processes race. Reversal-like events update the original conversion rather than creating a second record.

Lootably, AdGem, and CPAlead are disabled. Their adapter, redirect, request, and signature implementations must be added only after reviewing current official publisher documentation and providing approved credentials.
