import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from processor import load_orders, load_events, derive_state

def test_known_refund_full_success():
    orders = load_orders()
    events = load_events()
    st = derive_state(orders, events)
    # ord_1001 was fully refunded for 1299.00 INR
    o = st['orders']['ord_1001']
    assert o['refunded_minor'] == 129900
    assert o['refundable_minor'] == 0

def test_split_refunds_sum():
    orders = load_orders()
    events = load_events()
    st = derive_state(orders, events)
    # ord_1009 has three split refunds totaling 100000 minor
    o = st['orders']['ord_1009']
    assert o['refunded_minor'] == 100000
    assert o['refundable_minor'] == 0


def test_duplicate_event_is_deduped():
    events = load_events()
    assert sum(1 for event in events if event['event_id'] == 'evt_0001') == 1


def test_legacy_amount_and_naive_time_are_normalized():
    orders = load_orders()
    events = load_events()
    st = derive_state(orders, events)

    legacy = next(event for event in events if event['event_id'] == 'evt_0201')
    assert legacy['amount_minor'] == 82355
    assert legacy['occurred_at_parsed'].tzinfo is not None

    order = st['orders']['ord_2107']
    refund = next(refund for refund in order['refunds'] if refund['refund_id'] == 'rfnd_7107')
    assert refund['amount_minor'] == 82355
    assert refund['status'] == 'requested'
    assert order['pending_minor'] == 82355


def test_failed_refund_does_not_count_as_paid_out():
    orders = load_orders()
    events = load_events()
    st = derive_state(orders, events)

    order = st['orders']['ord_2107']
    failed_refund = next(refund for refund in order['refunds'] if refund['refund_id'] == 'rfnd_6107')
    assert failed_refund['status'] == 'failed'
    assert order['refunded_minor'] == 0
    assert order['failed_minor'] == 164711
