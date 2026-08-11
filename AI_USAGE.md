# AI usage

## Where AI helped most

- Drafting the processor code that normalizes event shapes and timestamps; iterating on edge cases (legacy `amount` vs `amount_minor`).

## Where AI was wrong

- Suggested trusting `received_at` instead of `occurred_at`; I used `occurred_at` when available and fell back to `received_at`.
- Proposed summing pending refunds without capping; I noticed this would allow pending > order total and changed to cap pending to refundable amount.
- Suggested treating duplicate events as independent; I deduplicated by `event_id` instead to avoid replay double-counting.

## Decision I made against AI

- AI suggested converting all currencies to a single base; I avoided FX assumptions because no rates were provided.

## How I verified the output

- Wrote `tests/test_processor.py` asserting known refunds (ord_1001 and ord_1009) match expected minor-unit totals from the sample data.
- Exercised the live endpoints in Postman: `GET /`, `GET /orders/<order_id>`, and `POST /orders/<order_id>/action` with valid and invalid payloads to confirm the success, validation, and duplicate-record paths.
