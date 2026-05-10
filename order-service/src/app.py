from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///orders.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

RESTAURANT_SERVICE_URL = os.getenv('RESTAURANT_SERVICE_URL', 'http://restaurant-service:5001')

# ── Models ────────────────────────────────────────────────────────────────────

class Order(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    restaurant_id = db.Column(db.Integer, nullable=False)
    items         = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    status        = db.Column(db.String(50), default='PLACED')   # PLACED | PREPARING | OUT_FOR_DELIVERY | DELIVERED | CANCELLED
    total_amount  = db.Column(db.Float, default=0.0)
    delivery_address = db.Column(db.String(200), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':               self.id,
            'customer_name':    self.customer_name,
            'restaurant_id':    self.restaurant_id,
            'items':            [i.to_dict() for i in self.items],
            'status':           self.status,
            'total_amount':     self.total_amount,
            'delivery_address': self.delivery_address,
            'created_at':       self.created_at.isoformat()
        }

class OrderItem(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    order_id    = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id= db.Column(db.Integer, nullable=False)
    name        = db.Column(db.String(120), nullable=False)
    quantity    = db.Column(db.Integer, nullable=False)
    unit_price  = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'menu_item_id': self.menu_item_id,
            'name':         self.name,
            'quantity':     self.quantity,
            'unit_price':   self.unit_price,
            'subtotal':     round(self.quantity * self.unit_price, 2)
        }

# ── Helpers ───────────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    'PLACED':           ['PREPARING', 'CANCELLED'],
    'PREPARING':        ['OUT_FOR_DELIVERY', 'CANCELLED'],
    'OUT_FOR_DELIVERY': ['DELIVERED'],
    'DELIVERED':        [],
    'CANCELLED':        []
}

def fetch_item(item_id):
    """Call Restaurant Service to get item details."""
    try:
        resp = requests.get(f'{RESTAURANT_SERVICE_URL}/menu/{item_id}', timeout=3)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f'Item {item_id} not found in Restaurant Service'
    except requests.exceptions.ConnectionError:
        return None, 'Restaurant Service is unreachable'

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'Order Service is running'}), 200

@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    required = ('customer_name', 'restaurant_id', 'items', 'delivery_address')
    if not data or not all(k in data for k in required):
        return jsonify({'error': f'Required fields: {required}'}), 400
    if not data['items']:
        return jsonify({'error': 'Order must contain at least one item'}), 400

    order_items = []
    total = 0.0

    for entry in data['items']:
        if 'menu_item_id' not in entry or 'quantity' not in entry:
            return jsonify({'error': 'Each item needs menu_item_id and quantity'}), 400

        item_data, err = fetch_item(entry['menu_item_id'])
        if err:
            return jsonify({'error': err}), 502

        if not item_data.get('available', False):
            return jsonify({'error': f"Item {entry['menu_item_id']} is not available"}), 400

        qty = int(entry['quantity'])
        price = float(item_data['price'])
        total += qty * price
        order_items.append(OrderItem(
            menu_item_id=entry['menu_item_id'],
            name=item_data['name'],
            quantity=qty,
            unit_price=price
        ))

    order = Order(
        customer_name=data['customer_name'],
        restaurant_id=data['restaurant_id'],
        delivery_address=data['delivery_address'],
        total_amount=round(total, 2),
        items=order_items
    )
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201

@app.route('/orders', methods=['GET'])
def list_orders():
    customer = request.args.get('customer_name')
    status   = request.args.get('status')
    query    = Order.query
    if customer:
        query = query.filter_by(customer_name=customer)
    if status:
        query = query.filter_by(status=status.upper())
    orders = query.order_by(Order.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200

@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify(order.to_dict()), 200

@app.route('/orders/<int:order_id>/status', methods=['PATCH'])
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    data  = request.get_json()
    new_status = data.get('status', '').upper()
    if new_status not in VALID_TRANSITIONS:
        return jsonify({'error': f'Invalid status. Must be one of: {list(VALID_TRANSITIONS.keys())}'}), 400
    if new_status not in VALID_TRANSITIONS[order.status]:
        return jsonify({'error': f'Cannot transition from {order.status} to {new_status}'}), 409
    order.status = new_status
    db.session.commit()
    return jsonify(order.to_dict()), 200

@app.route('/orders/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status not in ('PLACED', 'PREPARING'):
        return jsonify({'error': f'Cannot cancel order in status: {order.status}'}), 409
    order.status = 'CANCELLED'
    db.session.commit()
    return jsonify({'message': f'Order {order_id} cancelled', 'order': order.to_dict()}), 200

def init_db():
    with app.app_context():
        db.create_all()

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)