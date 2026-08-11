# Refund Review Console

This take-home is about turning a messy payment export into a trustworthy internal console. The app shows refund state, the customer-facing history behind that state, and a durable approve/reject action for pending refunds. The emphasis is on correctness, clear assumptions, and readable reasoning rather than UI polish.

The implementation handles the main data issues called out in the brief: mixed event formats, replayed events, and legacy gateway timestamps. Amounts are normalized into minor units, duplicate event IDs are ignored, and naive timestamps from the legacy gateway are treated as Hyderabad local time before being converted to UTC.

## Run locally

Python 3.9+.

1. Create a venv and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

Open http://localhost:5000.

## What it does

- Processes `refund-console-data/orders.csv` and `events.jsonl` to derive per-order refund state (succeeded, failed, pending) and refundable amount.
- Shows a queue view and order detail view with refund timeline and derived totals.
- Allows recording an `approve`/`reject` action for pending refunds; decisions are saved to `data/decisions.json`.

## API checks

- I used Postman to hit `GET /` for the queue summary, `GET /orders/<order_id>` for order detail, and `POST /orders/<order_id>/action` to record approve/reject decisions.
- For the POST request, I sent JSON like `{"refund_id":"...","action":"approve","reason":"..."}` and checked the `200`, `400`, and `409` responses.

## Verification

- I ran the test suite with the project virtual environment: `.venv\Scripts\python -m pytest -q`
- Current result: `5 passed`
