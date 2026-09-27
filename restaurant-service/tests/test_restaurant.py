from decimal import Decimal


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'Restaurant Service is running'


# ── Restaurants ───────────────────────────────────────────────────────────────

def test_create_restaurant(client):
    resp = client.post('/restaurants', json={
        'name': 'Test Cafe', 'cuisine': 'Indian', 'address': '1 Test St'
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Test Cafe'
    assert data['cuisine'] == 'Indian'


def test_create_restaurant_missing_field(client):
    resp = client.post('/restaurants', json={'name': 'Incomplete'})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body['error'] == 'Validation Failed'
    reported = []
    for detail in body['details']:
        reported.append(detail['field'])
    assert 'cuisine' in reported
    assert 'address' in reported


def test_get_all_restaurants(client):
    client.post('/restaurants', json={'name': 'R1', 'cuisine': 'Italian', 'address': 'Addr1'})
    client.post('/restaurants', json={'name': 'R2', 'cuisine': 'Chinese', 'address': 'Addr2'})
    resp = client.get('/restaurants')
    assert resp.status_code == 200
    body = resp.get_json()
    assert len(body['items']) == 2
    assert body['next_cursor'] is None


def test_get_restaurant_by_id(client):
    client.post('/restaurants', json={'name': 'Solo', 'cuisine': 'Mexican', 'address': 'Addr'})
    resp = client.get('/restaurants/1')
    assert resp.status_code == 200
    assert resp.get_json()['id'] == 1


def test_get_nonexistent_restaurant(client):
    resp = client.get('/restaurants/999')
    assert resp.status_code == 404


def test_update_restaurant(client):
    client.post('/restaurants', json={'name': 'Old', 'cuisine': 'French', 'address': 'Old Addr'})
    resp = client.put('/restaurants/1', json={'name': 'New Name', 'is_open': False})
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'New Name'
    assert resp.get_json()['is_open'] is False
    # Fields absent from the body must be left alone.
    assert resp.get_json()['cuisine'] == 'French'


# ── Menu items ────────────────────────────────────────────────────────────────

def test_add_menu_item(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Pad Thai', 'price': 199.0})
    assert resp.status_code == 201
    assert resp.get_json()['name'] == 'Pad Thai'
    assert resp.get_json()['price'] == '199.00'


def test_get_menu(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    client.post('/restaurants/1/menu', json={'name': 'Item 1', 'price': 100.0})
    client.post('/restaurants/1/menu', json={'name': 'Item 2', 'price': 150.0})
    resp = client.get('/restaurants/1/menu')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_check_item_availability(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    client.post('/restaurants/1/menu', json={'name': 'Item', 'price': 120.0, 'available': True})
    resp = client.get('/menu/1/availability')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['available'] is True
    assert data['price'] == '120.00'


def test_delete_restaurant(client):
    client.post('/restaurants', json={'name': 'ToDelete', 'cuisine': 'Greek', 'address': 'Addr'})
    resp = client.delete('/restaurants/1')
    assert resp.status_code == 200
    assert client.get('/restaurants/1').status_code == 404


# ── Money is exact ────────────────────────────────────────────────────────────

def test_price_is_stored_as_exact_decimal(client, app):
    from db import db
    from models import MenuItem

    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Awkward', 'price': '249.10'})
    assert resp.status_code == 201
    assert resp.get_json()['price'] == '249.10'

    item = db.session.get(MenuItem, 1)
    assert isinstance(item.price, Decimal)
    assert item.price == Decimal('249.10')


def test_price_accepts_a_numeric_string(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Item', 'price': '99.5'})
    assert resp.status_code == 201
    assert resp.get_json()['price'] == '99.50'


# ── Validation ────────────────────────────────────────────────────────────────

def test_negative_price_is_rejected(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Free lunch', 'price': -5})
    assert resp.status_code == 400
    assert resp.get_json()['details'][0]['field'] == 'price'


def test_non_numeric_price_is_rejected_not_a_500(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Item', 'price': 'abc'})
    assert resp.status_code == 400


def test_rating_out_of_range_is_rejected(client):
    resp = client.post('/restaurants', json={
        'name': 'R', 'cuisine': 'Thai', 'address': 'A', 'rating': 9.9
    })
    assert resp.status_code == 400


def test_missing_body_is_a_400(client):
    resp = client.post('/restaurants', data='not json', content_type='application/json')
    assert resp.status_code == 400
    assert resp.is_json


# ── JSON error handling ───────────────────────────────────────────────────────

def test_404_is_json_not_html(client):
    resp = client.get('/restaurants/999')
    assert resp.status_code == 404
    assert resp.content_type.startswith('application/json')
    body = resp.get_json()
    assert body['status'] == 404
    assert 'message' in body


def test_unknown_route_is_json(client):
    resp = client.get('/no/such/route')
    assert resp.status_code == 404
    assert resp.content_type.startswith('application/json')


def test_wrong_method_is_json(client):
    resp = client.delete('/health')
    assert resp.status_code == 405
    assert resp.content_type.startswith('application/json')


def test_unhandled_exception_is_json_500(app, monkeypatch):
    import routes

    def explode():
        raise RuntimeError('boom')

    monkeypatch.setattr(routes, 'live_restaurants', explode)
    # Flask re-raises exceptions while TESTING, which hides the 500 handler.
    app.config['TESTING'] = False
    app.config['PROPAGATE_EXCEPTIONS'] = False
    client = app.test_client()

    resp = client.get('/restaurants')
    assert resp.status_code == 500
    assert resp.content_type.startswith('application/json')
    assert resp.get_json()['status'] == 500


# ── Pagination ────────────────────────────────────────────────────────────────

def make_restaurants(client, count):
    for index in range(count):
        client.post('/restaurants', json={
            'name': 'R%d' % index,
            'cuisine': 'Italian',
            'address': 'Addr %d' % index
        })


def test_restaurants_default_page_size(client):
    make_restaurants(client, 25)
    resp = client.get('/restaurants')
    body = resp.get_json()
    assert len(body['items']) == 20
    assert body['limit'] == 20
    assert body['next_cursor'] is not None


def test_restaurants_cursor_walks_every_row_once(client):
    make_restaurants(client, 25)

    seen = []
    cursor = None
    pages = 0
    while pages < 10:
        url = '/restaurants?limit=10'
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


def test_restaurants_limit_over_maximum_is_rejected(client):
    resp = client.get('/restaurants?limit=500')
    assert resp.status_code == 400


def test_restaurants_limit_must_be_an_integer(client):
    resp = client.get('/restaurants?limit=lots')
    assert resp.status_code == 400


def test_restaurants_bad_cursor_is_rejected(client):
    resp = client.get('/restaurants?cursor=not-a-cursor')
    assert resp.status_code == 400


def test_restaurants_cursor_keeps_the_cuisine_filter(client):
    make_restaurants(client, 12)
    client.post('/restaurants', json={'name': 'Other', 'cuisine': 'Thai', 'address': 'A'})

    body = client.get('/restaurants?cuisine=Italian&limit=10').get_json()
    assert len(body['items']) == 10
    body = client.get('/restaurants?cuisine=Italian&limit=10&cursor=' + body['next_cursor']).get_json()
    assert len(body['items']) == 2
    for item in body['items']:
        assert item['cuisine'] == 'Italian'


# ── Soft delete and cascade ───────────────────────────────────────────────────

def test_soft_deleted_restaurant_is_hidden_but_kept(client, app):
    from db import db
    from models import Restaurant

    client.post('/restaurants', json={'name': 'Gone', 'cuisine': 'Greek', 'address': 'A'})
    client.delete('/restaurants/1')

    # Hidden from the API...
    assert client.get('/restaurants/1').status_code == 404
    assert client.get('/restaurants').get_json()['items'] == []

    # ...but the row survives for the audit trail.
    restaurant = db.session.get(Restaurant, 1)
    assert restaurant is not None
    assert restaurant.deleted_at is not None


def test_menu_of_a_deleted_restaurant_is_not_served(client):
    client.post('/restaurants', json={'name': 'Gone', 'cuisine': 'Greek', 'address': 'A'})
    client.post('/restaurants/1/menu', json={'name': 'Item', 'price': 10})
    client.delete('/restaurants/1')

    assert client.get('/restaurants/1/menu').status_code == 404
    assert client.get('/menu/1').status_code == 404
    assert client.get('/menu/1/availability').status_code == 404


def test_hard_delete_cascades_to_menu_items(client, app):
    from db import db
    from models import MenuItem, Restaurant

    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Greek', 'address': 'A'})
    client.post('/restaurants/1/menu', json={'name': 'Item', 'price': 10})
    assert MenuItem.query.count() == 1

    # A real delete, as the seed script does it, must not orphan menu rows.
    restaurant = db.session.get(Restaurant, 1)
    db.session.delete(restaurant)
    db.session.commit()

    assert MenuItem.query.count() == 0
