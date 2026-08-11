import csv
import json
from collections import defaultdict
from datetime import datetime
from dateutil import parser, tz
import os

# Pin now as requested
PINNED_NOW = parser.isoparse("2026-08-11T10:00:00+05:30")

ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT, 'refund-console-data')

def to_minor(amount, currency):
    # amount may be string decimal or numeric in minor units
    if isinstance(amount, int):
        return amount
    if isinstance(amount, float):
        return int(round(amount * 100))
    s = str(amount)
    if s.isdigit():
        return int(s)
    # decimal
    return int(round(float(s) * 100))

def load_orders(path=None):
    path = path or os.path.join(DATA_DIR, 'orders.csv')
    orders = {}
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            order_id = r['order_id']
            currency = r['currency']
            total_minor = to_minor(r['total_amount'], currency)
            orders[order_id] = {
                'order_id': order_id,
                'customer_id': r.get('customer_id'),
                'currency': currency,
                'total_amount_minor': total_minor,
                'placed_at': r.get('placed_at'),
                'channel': r.get('channel'),
                'region': r.get('region')
            }
    return orders

def parse_event_line(line):
    obj = json.loads(line)
    # normalize amount_minor
    if 'amount_minor' in obj and obj['amount_minor'] is not None:
        obj['amount_minor'] = int(obj['amount_minor'])
    elif 'amount' in obj and obj['amount'] is not None:
        obj['amount_minor'] = to_minor(obj['amount'], obj.get('currency', ''))
    else:
        obj['amount_minor'] = None
    # parse occurred_at tolerant
    try:
        dt = parser.parse(obj.get('occurred_at'))
        # normalize: if naive, assume legacy gateway local time (Hyderabad) per spec
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz.gettz('Asia/Kolkata'))
        # convert to UTC for consistent comparisons
        obj['occurred_at_parsed'] = dt.astimezone(tz.tzutc())
    except Exception:
        obj['occurred_at_parsed'] = None
    return obj

def load_events(path=None):
    path = path or os.path.join(DATA_DIR, 'events.jsonl')
    events = []
    seen_ids = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = parse_event_line(line)
            eid = obj.get('event_id')
            if eid and eid in seen_ids:
                continue
            if eid:
                seen_ids.add(eid)
            events.append(obj)
    # sort by occurred_at_parsed then received_at as fallback
    # use an aware minimal datetime for fallback to avoid mixing naive/aware
    min_aware = datetime.min.replace(tzinfo=tz.tzutc())
    events.sort(key=lambda e: (e.get('occurred_at_parsed') or min_aware, e.get('received_at') or ''))
    return events

def derive_state(orders, events):
    # group events by refund_id and order
    refunds = defaultdict(list)
    events_by_order = defaultdict(list)
    for e in events:
        rid = e.get('refund_id')
        oid = e.get('order_id')
        if rid:
            refunds[rid].append(e)
        if oid:
            events_by_order[oid].append(e)

    refund_states = {}
    # determine state per refund_id: succeeded, failed, pending (requested only)
    for rid, evs in refunds.items():
        status = 'unknown'
        amt = None
        for e in evs:
            t = e.get('type')
            if amt is None and e.get('amount_minor') is not None:
                amt = e.get('amount_minor')
            if t == 'refund.succeeded':
                status = 'succeeded'
                break
            if t == 'refund.failed' and status != 'succeeded':
                status = 'failed'
            if t == 'refund.requested' and status == 'unknown':
                status = 'requested'
        refund_states[rid] = {'refund_id': rid, 'status': status, 'amount_minor': amt, 'events': evs}

    # aggregate per order
    orders_state = {}
    totals = {'succeeded': defaultdict(int), 'pending': defaultdict(int), 'failed': defaultdict(int)}
    for oid, order in orders.items():
        succeeded = 0
        pending = 0
        failed = 0
        currency = order['currency']
        # find refunds for this order
        rs = [r for r in refund_states.values() if any(ev.get('order_id') == oid for ev in r['events'])]
        rlist = []
        for r in rs:
            a = r.get('amount_minor') or 0
            if r['status'] == 'succeeded':
                succeeded += a
            elif r['status'] == 'failed':
                failed += a
            else:
                pending += a
            rlist.append(r)
        refundable = max(0, order['total_amount_minor'] - succeeded)
        # cap pending by refundable (can't pay out more than order total)
        pending_capped = min(pending, refundable)
        orders_state[oid] = dict(order)
        orders_state[oid].update({
            'refunds': rlist,
            'refunded_minor': succeeded,
            'pending_minor': pending_capped,
            'failed_minor': failed,
            'refundable_minor': refundable,
        })
        totals['succeeded'][currency] += succeeded
        totals['pending'][currency] += pending_capped
        totals['failed'][currency] += failed

    return {
        'orders': orders_state,
        'refunds': refund_states,
        'events_by_order': events_by_order,
        'totals': totals,
    }

def load_state():
    orders = load_orders()
    events = load_events()
    return derive_state(orders, events)

if __name__ == '__main__':
    st = load_state()
    import pprint
    pprint.pprint({k: list(v.keys())[:5] for k, v in st['orders'].items()})
