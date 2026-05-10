import pytest
import sys
import os
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from app import app, db

MOCK_ITEM = {'id': 1, 'name': 'Chicken Biryani', 'price': 249.0, 'available': True, 'restaurant_id': 1}
MOCK_ITEM_UNAVAILABLE = {**MOCK_ITEM, 'available': False}

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def valid_order():
    return {
        'customer_name': 'Arjun Kumar',
        'restaurant_id': 1,
        'delivery_address': '22 Koramangala, Bangalore',
        'items': [{'menu_item_id': 1, 'quantity': 2}]
    }

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_create_order(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['customer_name'] == 'Arjun Kumar'
    assert data['status'] == 'PLACED'
    assert data['total_amount'] == 498.0   # 249 * 2

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_create_order_total_calculation(mock_fetch, client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': 3}]
    resp = client.post('/orders', json=order)
    assert resp.get_json()['total_amount'] == 747.0

def test_create_order_missing_fields(client):
    resp = client.post('/orders', json={'customer_name': 'Test'})
    assert resp.status_code == 400

@patch('app.fetch_item', return_value=(None, 'Restaurant Service is unreachable'))
def test_create_order_restaurant_down(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 502

@patch('app.fetch_item', return_value=(MOCK_ITEM_UNAVAILABLE, None))
def test_create_order_item_unavailable(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 400

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_get_order(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.get('/orders/1')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == 1

def test_get_nonexistent_order(client):
    resp = client.get('/orders/999')
    assert resp.status_code == 404

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_list_orders(mock_fetch, client):
    client.post('/orders', json=valid_order())
    client.post('/orders', json={**valid_order(), 'customer_name': 'Priya'})
    resp = client.get('/orders')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_valid(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'PREPARING'})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'PREPARING'

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_invalid_transition(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'DELIVERED'})
    assert resp.status_code == 409

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_cancel_order(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.delete('/orders/1')
    assert resp.status_code == 200
    assert resp.get_json()['order']['status'] == 'CANCELLED'

@patch('app.fetch_item', return_value=(MOCK_ITEM, None))
def test_cancel_delivered_order_fails(mock_fetch, client):
    client.post('/orders', json=valid_order())
    client.patch('/orders/1/status', json={'status': 'PREPARING'})
    client.patch('/orders/1/status', json={'status': 'OUT_FOR_DELIVERY'})
    client.patch('/orders/1/status', json={'status': 'DELIVERED'})
    resp = client.delete('/orders/1')
    assert resp.status_code == 409
