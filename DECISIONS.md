# Decisions and assumptions

These are the judgement calls I made while turning the export into the console.

## Data rules

- Time: pinned to `2026-08-11T10:00:00+05:30` as requested; all recorded decision timestamps use this fixed "now".
- Amount normalization: prefer `amount_minor` when present; otherwise use `amount` and multiply by 100 (rounding). This handles legacy gateway events that use `amount` as a decimal.
- Duplicate events: deduplicated by `event_id` when present (simple de-dup to handle replays).
- Refund state per `refund_id`: if any `refund.succeeded` event exists -> `succeeded`; else if any `refund.failed` -> `failed`; else if `refund.requested` -> `requested` (pending).
- Per-order refundable amount = max(0, order_total - sum(succeeded)). Pending amounts are capped by refundable amount (can't pay out more than original order total).
- Currency handling: totals are computed per-currency and shown that way; no FX conversions.
- Actions: `approve`/`reject` are recorded durably to `data/decisions.json`. An action is idempotent-blocked (second attempt returns 409).
- Queue UX: I added a compact search bar and server-side sortable columns so agents can filter and re-order the queue without changing the underlying refund logic.
- Sorting behavior: sort is query-param driven and applied server-side to keep the implementation simple, reproducible, and easy to explain.

## What I left out

- No authentication or role-based approval flows (would be required for production).
- No background job / retry handling for newly arrived events — app reload needed to pick up new export files.
- No ledger reconciliation or traceability links beyond events; for production we'd include event_ids in aggregates and expose CSV/trace exports for Priya.
- Render deployment uses local filesystem storage for decisions, so decision history is not durable across redeploys. That is acceptable for the take-home, but a production version would need persistent storage.

## Queue interpretation

- The console shows the full refund activity for the sampled orders, while the derived state makes it obvious which refunds still have money moving.
- That matches the two competing asks in the email thread without pretending the spec gave a single unambiguous queue definition.
