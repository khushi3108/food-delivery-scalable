from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///restaurants.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ── Models ────────────────────────────────────────────────────────────────────

class Restaurant(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(120), nullable=False)
    cuisine     = db.Column(db.String(80), nullable=False)
    address     = db.Column(db.String(200), nullable=False)
    is_open     = db.Column(db.Boolean, default=True)
    rating      = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id':       self.id,
            'name':     self.name,
            'cuisine':  self.cuisine,
            'address':  self.address,
            'is_open':  self.is_open,
            'rating':   self.rating
        }

class MenuItem(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    name          = db.Column(db.String(120), nullable=False)
    price         = db.Column(db.Float, nullable=False)
    available     = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id':            self.id,
            'restaurant_id': self.restaurant_id,
            'name':          self.name,
            'price':         self.price,
            'available':     self.available
        }

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'Restaurant Service is running'}), 200

# --- Restaurants ---

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    cuisine = request.args.get('cuisine')
    query = Restaurant.query
    if cuisine:
        query = query.filter_by(cuisine=cuisine)
    restaurants = query.all()
    return jsonify([r.to_dict() for r in restaurants]), 200

@app.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return jsonify(restaurant.to_dict()), 200

@app.route('/restaurants', methods=['POST'])
def create_restaurant():
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'cuisine', 'address')):
        return jsonify({'error': 'name, cuisine, and address are required'}), 400
    restaurant = Restaurant(
        name=data['name'],
        cuisine=data['cuisine'],
        address=data['address'],
        is_open=data.get('is_open', True),
        rating=data.get('rating', 0.0)
    )
    db.session.add(restaurant)
    db.session.commit()
    return jsonify(restaurant.to_dict()), 201

@app.route('/restaurants/<int:restaurant_id>', methods=['PUT'])
def update_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    data = request.get_json()
    for field in ('name', 'cuisine', 'address', 'is_open', 'rating'):
        if field in data:
            setattr(restaurant, field, data[field])
    db.session.commit()
    return jsonify(restaurant.to_dict()), 200

@app.route('/restaurants/<int:restaurant_id>', methods=['DELETE'])
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    db.session.delete(restaurant)
    db.session.commit()
    return jsonify({'message': f'Restaurant {restaurant_id} deleted'}), 200

# --- Menu Items ---

@app.route('/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_menu(restaurant_id):
    Restaurant.query.get_or_404(restaurant_id)
    items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify([i.to_dict() for i in items]), 200

@app.route('/restaurants/<int:restaurant_id>/menu', methods=['POST'])
def add_menu_item(restaurant_id):
    Restaurant.query.get_or_404(restaurant_id)
    data = request.get_json()
    if not data or not all(k in data for k in ('name', 'price')):
        return jsonify({'error': 'name and price are required'}), 400
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=data['name'],
        price=data['price'],
        available=data.get('available', True)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@app.route('/menu/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    """Called internally by Order Service to validate item before placing order."""
    item = MenuItem.query.get_or_404(item_id)
    return jsonify(item.to_dict()), 200

@app.route('/menu/<int:item_id>/availability', methods=['GET'])
def check_availability(item_id):
    item = MenuItem.query.get_or_404(item_id)
    return jsonify({'item_id': item_id, 'available': item.available, 'price': item.price}), 200

# ── Seed data ─────────────────────────────────────────────────────────────────

def seed():
    if Restaurant.query.count() == 0:
        r1 = Restaurant(name='Pizza Palace', cuisine='Italian', address='12 MG Road, Bangalore', rating=4.5)
        r2 = Restaurant(name='Biryani House', cuisine='Indian', address='45 Brigade Road, Bangalore', rating=4.2)
        db.session.add_all([r1, r2])
        db.session.flush()
        db.session.add_all([
            MenuItem(restaurant_id=r1.id, name='Margherita Pizza', price=299.0),
            MenuItem(restaurant_id=r1.id, name='Pepperoni Pizza', price=349.0),
            MenuItem(restaurant_id=r2.id, name='Chicken Biryani', price=249.0),
            MenuItem(restaurant_id=r2.id, name='Veg Biryani', price=199.0),
        ])
        db.session.commit()
        
def init_db():
    with app.app_context():
        db.create_all()
        seed()

# Works with both Gunicorn and direct run
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)