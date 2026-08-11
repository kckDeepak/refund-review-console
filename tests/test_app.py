import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import app


def test_index_renders():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    assert b'Refund Review Console' in response.data


def test_index_filters_and_empty_state_render():
    client = app.test_client()
    response = client.get('/?q=does-not-match-anything')
    assert response.status_code == 200
    assert b'No matching orders.' in response.data


def test_index_sorts_by_order_id_desc():
    client = app.test_client()
    response = client.get('/?sort=order_id&dir=desc')
    assert response.status_code == 200
    body = response.data.decode('utf-8')
    assert body.index('ord_2119') < body.index('ord_1001')