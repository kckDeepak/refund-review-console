from flask import Flask, render_template, jsonify, request
from processor import load_state, PINNED_NOW
import json
import os

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DECISIONS_PATH = os.path.join(DATA_DIR, 'decisions.json')
os.makedirs(DATA_DIR, exist_ok=True)

state = load_state()


def order_status(order):
    if order['pending_minor'] > 0:
        return 'pending'
    if order['refunded_minor'] > 0 and order['failed_minor'] > 0:
        return 'mixed'
    if order['refunded_minor'] > 0:
        return 'refunded'
    if order['failed_minor'] > 0:
        return 'failed'
    return 'none'

def load_decisions():
    if not os.path.exists(DECISIONS_PATH):
        return {}
    with open(DECISIONS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_decisions(d):
    with open(DECISIONS_PATH, 'w', encoding='utf-8') as f:
        json.dump(d, f, indent=2)

@app.route('/')
def index():
    query = (request.args.get('q') or '').strip().lower()
    status_filter = (request.args.get('status') or 'all').strip().lower()
    currency_filter = (request.args.get('currency') or 'all').strip().upper()

    orders = []
    for order in state['orders'].values():
        status = order_status(order)
        if query and query not in order['order_id'].lower() and query not in order['customer_id'].lower():
            continue
        if status_filter != 'all' and status != status_filter:
            continue
        if currency_filter != 'ALL' and order['currency'] != currency_filter:
            continue

        order_copy = dict(order)
        order_copy['status'] = status
        orders.append(order_copy)

    orders.sort(key=lambda item: (item['pending_minor'] == 0, item['order_id']))

    currencies = sorted({order['currency'] for order in state['orders'].values()})
    pending_totals = {}
    for cur, minor in state['totals']['pending'].items():
        pending_totals[cur] = minor / 100.0
    decisions = load_decisions()
    return render_template(
        'index.html',
        orders=orders,
        pending_totals=pending_totals,
        now=PINNED_NOW.isoformat(),
        decisions=decisions,
        query=query,
        status_filter=status_filter,
        currency_filter=currency_filter,
        currencies=currencies,
    )

@app.route('/orders/<order_id>')
def order_detail(order_id):
    order = state['orders'].get(order_id)
    if not order:
        return 'Not found', 404
    events = state['events_by_order'].get(order_id, [])
    decisions = load_decisions()
    return render_template('detail.html', order=order, events=events, decisions=decisions, now=PINNED_NOW.isoformat())

@app.route('/orders/<order_id>/action', methods=['POST'])
def order_action(order_id):
    payload = request.json or {}
    refund_id = payload.get('refund_id')
    action = payload.get('action')
    reason = payload.get('reason')
    if action not in ('approve', 'reject'):
        return jsonify({'error': 'invalid action'}), 400
    decisions = load_decisions()
    key = f"{order_id}:{refund_id}"
    if key in decisions:
        return jsonify({'error': 'already recorded'}), 409
    decisions[key] = {
        'order_id': order_id,
        'refund_id': refund_id,
        'action': action,
        'reason': reason,
        'recorded_at': PINNED_NOW.isoformat()
    }
    save_decisions(decisions)
    return jsonify({'ok': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
