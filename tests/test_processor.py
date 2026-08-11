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
