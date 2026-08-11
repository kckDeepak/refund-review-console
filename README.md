# Refund Review Console

This take-home asks for a small internal refund console that can explain the current refund state from a messy payment export, show an agent queue and order detail view, and record an approve/reject decision with a reason. The main work is in reading the data correctly and writing down the assumptions clearly.

The implementation focuses on the hard parts of the brief: handling mixed event formats, replayed events, and legacy gateway timestamps. Amounts are normalized into minor units, duplicate event IDs are ignored, and naive timestamps from the legacy gateway are treated as Hyderabad local time before being converted to UTC.

Run locally (Python 3.9+):

1. Create a venv and install:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

2. Start the app:

```bash
python app.py
```

Open http://localhost:5000

What it does:

- Processes `refund-console-data/orders.csv` and `events.jsonl` to derive per-order refund state (succeeded, failed, pending) and refundable amount.
- Shows a queue view and order detail view with refund timeline and derived totals.
- Allows recording an `approve`/`reject` action for pending refunds; decisions are saved to `data/decisions.json`.

How I exercised the endpoints:

- I used Postman to hit `GET /` for the queue summary, `GET /orders/<order_id>` for order detail, and `POST /orders/<order_id>/action` to record approve/reject decisions.
- For the POST request, I sent JSON like `{"refund_id":"...","action":"approve","reason":"..."}` and checked the `200`, `400`, and `409` responses.

Verification:

- I ran the test suite with the project virtual environment: `.venv\Scripts\python -m pytest -q`
- Current result: `5 passed`
