from decimal import Decimal
from unittest.mock import patch

MOCK_ITEM = {'id': 1, 'name': 'Chicken Biryani', 'price': '249.00', 'available': True, 'restaurant_id': 1}
MOCK_ITEM_UNAVAILABLE = {**MOCK_ITEM, 'available': False}
MOCK_ITEM_AWKWARD_PRICE = {**MOCK_ITEM, 'price': '249.10'}


def valid_order():
    return {
        'customer_name': 'Arjun Kumar',
        'restaurant_id': 1,
        'delivery_address': '22 Koramangala, Bangalore',
        'items': [{'menu_item_id': 1, 'quantity': 2}]
    }


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200


# ── Creating orders ───────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_create_order(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['customer_name'] == 'Arjun Kumar'
    assert data['status'] == 'PLACED'
    assert data['total_amount'] == '498.00'   # 249.00 * 2


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_create_order_total_calculation(mock_fetch, client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': 3}]
    resp = client.post('/orders', json=order)
    assert resp.get_json()['total_amount'] == '747.00'


def test_create_order_missing_fields(client):
    resp = client.post('/orders', json={'customer_name': 'Test'})
    assert resp.status_code == 400
    reported = []
    for detail in resp.get_json()['details']:
        reported.append(detail['field'])
    assert 'restaurant_id' in reported
    assert 'delivery_address' in reported
    assert 'items' in reported


@patch('routes.fetch_item', return_value=(None, 'Restaurant Service is unreachable'))
def test_create_order_restaurant_down(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 502


@patch('routes.fetch_item', return_value=(MOCK_ITEM_UNAVAILABLE, None))
def test_create_order_item_unavailable(mock_fetch, client):
    resp = client.post('/orders', json=valid_order())
    assert resp.status_code == 400


# ── Reading orders ────────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_get_order(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.get('/orders/1')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == 1


def test_get_nonexistent_order(client):
    resp = client.get('/orders/999')
    assert resp.status_code == 404


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_list_orders(mock_fetch, client):
    client.post('/orders', json=valid_order())
    client.post('/orders', json={**valid_order(), 'customer_name': 'Priya'})
    resp = client.get('/orders')
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body['items']) == 2
    assert body['next_cursor'] is None


# ── Status transitions ────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_valid(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'PREPARING'})
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'PREPARING'


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_invalid_transition(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'DELIVERED'})
    assert resp.status_code == 409


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_unknown_status(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'TELEPORTED'})
    assert resp.status_code == 400


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_update_status_missing_status(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={})
    assert resp.status_code == 400


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_cancel_order(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.delete('/orders/1')
    assert resp.status_code == 200
    assert resp.get_json()['order']['status'] == 'CANCELLED'


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_cancel_delivered_order_fails(mock_fetch, client):
    client.post('/orders', json=valid_order())
    client.patch('/orders/1/status', json={'status': 'PREPARING'})
    client.patch('/orders/1/status', json={'status': 'OUT_FOR_DELIVERY'})
    client.patch('/orders/1/status', json={'status': 'DELIVERED'})
    resp = client.delete('/orders/1')
    assert resp.status_code == 409


# ── Money is exact ────────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM_AWKWARD_PRICE, None))
def test_total_is_exact_for_a_price_a_float_cannot_hold(mock_fetch, client, app):
    from db import db
    from models import Order

    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': 3}]
    resp = client.post('/orders', json=order)

    # 249.10 * 3 is exactly 747.30. In binary floating point it is 747.3000...04.
    assert resp.get_json()['total_amount'] == '747.30'
    assert resp.get_json()['items'][0]['subtotal'] == '747.30'

    stored = db.session.get(Order, 1)
    assert isinstance(stored.total_amount, Decimal)
    assert stored.total_amount == Decimal('747.30')


@patch('routes.fetch_item', return_value=(MOCK_ITEM_AWKWARD_PRICE, None))
def test_many_lines_still_reconcile(mock_fetch, client):
    order = valid_order()
    order['items'] = []
    for index in range(10):
        order['items'].append({'menu_item_id': 1, 'quantity': 1})

    resp = client.post('/orders', json=order)
    # Ten lines of 249.10 is exactly 2491.00, with no drift accumulated.
    assert resp.get_json()['total_amount'] == '2491.00'


# ── Validation ────────────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_non_numeric_quantity_is_a_400_not_a_500(mock_fetch, client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': 'abc'}]
    resp = client.post('/orders', json=order)
    assert resp.status_code == 400
    assert resp.get_json()['details'][0]['field'] == 'items.0.quantity'


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_negative_quantity_is_rejected(mock_fetch, client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': -3}]
    resp = client.post('/orders', json=order)
    assert resp.status_code == 400


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_zero_quantity_is_rejected(mock_fetch, client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1, 'quantity': 0}]
    resp = client.post('/orders', json=order)
    assert resp.status_code == 400


def test_empty_item_list_is_rejected(client):
    order = valid_order()
    order['items'] = []
    resp = client.post('/orders', json=order)
    assert resp.status_code == 400


def test_item_without_quantity_is_rejected(client):
    order = valid_order()
    order['items'] = [{'menu_item_id': 1}]
    resp = client.post('/orders', json=order)
    assert resp.status_code == 400


def test_missing_body_is_a_400(client):
    resp = client.post('/orders', data='not json', content_type='application/json')
    assert resp.status_code == 400
    assert resp.is_json


# ── JSON error handling ───────────────────────────────────────────────────────

def test_404_is_json_not_html(client):
    resp = client.get('/orders/999')
    assert resp.status_code == 404
    assert resp.content_type.startswith('application/json')
    body = resp.get_json()
    assert body['status'] == 404
    assert 'message' in body


def test_unknown_route_is_json(client):
    resp = client.get('/no/such/route')
    assert resp.status_code == 404
    assert resp.content_type.startswith('application/json')


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_conflict_body_is_json(mock_fetch, client):
    client.post('/orders', json=valid_order())
    resp = client.patch('/orders/1/status', json={'status': 'DELIVERED'})
    assert resp.status_code == 409
    assert resp.content_type.startswith('application/json')
    assert resp.get_json()['status'] == 409


def test_unhandled_exception_is_json_500(app, monkeypatch):
    import routes

    def explode(order_id):
        raise RuntimeError('boom')

    monkeypatch.setattr(routes, 'get_order_or_404', explode)
    app.config['TESTING'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = False
    client = app.test_client()

    resp = client.get('/orders/1')
    assert resp.status_code == 500
    assert resp.content_type.startswith('application/json')
    assert resp.get_json()['status'] == 500


# ── Pagination ────────────────────────────────────────────────────────────────

def make_orders(client, count):
    for index in range(count):
        payload = valid_order()
        payload['customer_name'] = 'Customer %02d' % index
        client.post('/orders', json=payload)


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_orders_default_page_size(mock_fetch, client):
    make_orders(client, 25)
    body = client.get('/orders').get_json()
    assert len(body['items']) == 20
    assert body['limit'] == 20
    assert body['next_cursor'] is not None


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_orders_cursor_walks_every_row_once(mock_fetch, client):
    make_orders(client, 25)

    seen = []
    cursor = None
    pages = 0
    while pages < 10:
        url = '/orders?limit=10'
        if cursor is not None:
            url = url + '&cursor=' + cursor
        body = client.get(url).get_json()
        for item in body['items']:
            seen.append(item['id'])
        cursor = body['next_cursor']
        pages = pages + 1
        if cursor is None:
            break

    assert len(seen) == 25
    assert len(set(seen)) == 25


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_orders_are_newest_first(mock_fetch, client):
    make_orders(client, 5)
    body = client.get('/orders').get_json()
    ids = []
    for item in body['items']:
        ids.append(item['id'])
    assert ids == sorted(ids, reverse=True)


@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_orders_cursor_keeps_the_status_filter(mock_fetch, client):
    make_orders(client, 12)
    client.patch('/orders/1/status', json={'status': 'PREPARING'})

    body = client.get('/orders?status=placed&limit=10').get_json()
    assert len(body['items']) == 10
    body = client.get('/orders?status=placed&limit=10&cursor=' + body['next_cursor']).get_json()
    assert len(body['items']) == 1
    for item in body['items']:
        assert item['status'] == 'PLACED'


def test_orders_limit_over_maximum_is_rejected(client):
    resp = client.get('/orders?limit=500')
    assert resp.status_code == 400


def test_orders_bad_cursor_is_rejected(client):
    resp = client.get('/orders?cursor=not-a-cursor')
    assert resp.status_code == 400


# ── N+1 ───────────────────────────────────────────────────────────────────────

@patch('routes.fetch_item', return_value=(MOCK_ITEM, None))
def test_listing_orders_does_not_issue_one_query_per_order(mock_fetch, client, app):
    from sqlalchemy import event

    make_orders(client, 15)

    statements = []

    def record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    engine = app.extensions['sqlalchemy'].engine
    event.listen(engine, 'before_cursor_execute', record)
    try:
        body = client.get('/orders?limit=15').get_json()
    finally:
        event.remove(engine, 'before_cursor_execute', record)

    assert len(body['items']) == 15
    selects = []
    for statement in statements:
        if statement.strip().upper().startswith('SELECT'):
            selects.append(statement)
    # One query for the orders plus one selectin load for all their items.
    assert len(selects) == 2
