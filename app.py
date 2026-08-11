from flask import Flask, render_template, jsonify, request
from processor import load_state, PINNED_NOW
import json
import os

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DECISIONS_PATH = os.path.join(DATA_DIR, 'decisions.json')
os.makedirs(DATA_DIR, exist_ok=True)

state = load_state()

STATUS_PRIORITY = {
    'pending': 0,
    'mixed': 1,
    'failed': 2,
    'refunded': 3,
    'none': 4,
}

SORT_COLUMNS = {
    'order_id',
    'customer_id',
    'status',
    'total',
    'refunded',
    'pending',
    'refundable',
}


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


def order_sort_value(order, sort_column):
    if sort_column == 'order_id':
        return order['order_id']
    if sort_column == 'customer_id':
        return order['customer_id']
    if sort_column == 'status':
        return STATUS_PRIORITY.get(order['status'], 99)
    if sort_column == 'total':
        return order['total_amount_minor']
    if sort_column == 'refunded':
        return order['refunded_minor']
    if sort_column == 'pending':
        return order['pending_minor']
    if sort_column == 'refundable':
        return order['refundable_minor']
    return order['pending_minor']

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
    sort_column = (request.args.get('sort') or 'pending').strip().lower()
    sort_direction = (request.args.get('dir') or 'desc').strip().lower()

    if sort_column not in SORT_COLUMNS:
        sort_column = 'pending'
    if sort_direction not in ('asc', 'desc'):
        sort_direction = 'desc'

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

    reverse = sort_direction == 'desc'
    orders.sort(key=lambda item: (order_sort_value(item, sort_column), item['order_id']), reverse=reverse)

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
        sort_column=sort_column,
        sort_direction=sort_direction,
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
