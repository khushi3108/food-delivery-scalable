import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from app import app, db


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'Restaurant Service is running'

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

def test_get_all_restaurants(client):
    client.post('/restaurants', json={'name': 'R1', 'cuisine': 'Italian', 'address': 'Addr1'})
    client.post('/restaurants', json={'name': 'R2', 'cuisine': 'Chinese', 'address': 'Addr2'})
    resp = client.get('/restaurants')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2

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

def test_add_menu_item(client):
    client.post('/restaurants', json={'name': 'R', 'cuisine': 'Thai', 'address': 'A'})
    resp = client.post('/restaurants/1/menu', json={'name': 'Pad Thai', 'price': 199.0})
    assert resp.status_code == 201
    assert resp.get_json()['name'] == 'Pad Thai'

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
    assert data['price'] == 120.0

def test_delete_restaurant(client):
    client.post('/restaurants', json={'name': 'ToDelete', 'cuisine': 'Greek', 'address': 'Addr'})
    resp = client.delete('/restaurants/1')
    assert resp.status_code == 200
    assert client.get('/restaurants/1').status_code == 404
