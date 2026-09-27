"""HTTP routes for the Order Service."""

from datetime import datetime
from decimal import Decimal

from flask import Blueprint, abort, jsonify, request
from sqlalchemy.orm import selectinload

from clients import fetch_item
from db import db
from models import Order, OrderItem
from money import to_money
from pagination import encode_cursor, page_envelope, read_cursor, read_limit
from schemas import OrderCreate, OrderStatusUpdate, parse_body

api = Blueprint('api', __name__)

VALID_TRANSITIONS = {
    'PLACED': ['PREPARING', 'CANCELLED'],
    'PREPARING': ['OUT_FOR_DELIVERY', 'CANCELLED'],
    'OUT_FOR_DELIVERY': ['DELIVERED'],
    'DELIVERED': [],
    'CANCELLED': []
}


def parse_cursor_timestamp(value):
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        abort(400, description='cursor is not a valid pagination cursor.')


def get_order_or_404(order_id):
    order = (
        Order.query
        .options(selectinload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if order is None:
        abort(404, description='Order %d was not found.' % order_id)
    return order


# ── Health ────────────────────────────────────────────────────────────────────

@api.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'Order Service is running'}), 200


# ── Orders ────────────────────────────────────────────────────────────────────

@api.route('/orders', methods=['POST'])
def create_order():
    body, error = parse_body(OrderCreate)
    if error is not None:
        return error

    order_items = []
    total = Decimal('0.00')

    for entry in body.items:
        item_data, message = fetch_item(entry.menu_item_id)
        if message is not None:
            return jsonify({
                'status': 502,
                'error': 'Bad Gateway',
                'message': message
            }), 502

        if not item_data.get('available', False):
            return jsonify({
                'status': 400,
                'error': 'Bad Request',
                'message': 'Item %s is not available' % entry.menu_item_id
            }), 400

        # Decimal from here on. quantity is already a validated int >= 1.
        unit_price = to_money(item_data['price'])
        line_total = to_money(unit_price * entry.quantity)
        total = total + line_total

        order_items.append(OrderItem(
            menu_item_id=entry.menu_item_id,
            name=item_data['name'],
            quantity=entry.quantity,
            unit_price=unit_price
        ))

    order = Order(
        customer_name=body.customer_name,
        restaurant_id=body.restaurant_id,
        delivery_address=body.delivery_address,
        total_amount=to_money(total),
        items=order_items
    )
    db.session.add(order)
    db.session.commit()
    return jsonify(order.to_dict()), 201


@api.route('/orders', methods=['GET'])
def list_orders():
    limit = read_limit()
    cursor = read_cursor(2)

    # selectinload pulls every order's items in one extra query instead of one
    # query per order, which is what made listing 100 orders 101 queries.
    query = Order.query.options(selectinload(Order.items))

    customer = request.args.get('customer_name')
    if customer:
        query = query.filter(Order.customer_name == customer)

    status = request.args.get('status')
    if status:
        query = query.filter(Order.status == status.upper())

    if cursor is not None:
        last_created_at = parse_cursor_timestamp(cursor[0])
        try:
            last_id = int(cursor[1])
        except ValueError:
            abort(400, description='cursor is not a valid pagination cursor.')
        # Newest first, so the next page is everything strictly "older" than the
        # last row we returned.
        query = query.filter(
            db.or_(
                Order.created_at < last_created_at,
                db.and_(
                    Order.created_at == last_created_at,
                    Order.id < last_id
                )
            )
        )

    rows = (
        query
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit + 1)
        .all()
    )

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    items = []
    for order in rows:
        items.append(order.to_dict())

    next_cursor = None
    if has_more:
        last = rows[-1]
        next_cursor = encode_cursor([last.created_at.isoformat(), last.id])

    return jsonify(page_envelope(items, next_cursor, limit)), 200


@api.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    order = get_order_or_404(order_id)
    return jsonify(order.to_dict()), 200


@api.route('/orders/<int:order_id>/status', methods=['PATCH'])
def update_status(order_id):
    order = get_order_or_404(order_id)

    body, error = parse_body(OrderStatusUpdate)
    if error is not None:
        return error

    new_status = body.status.upper()
    if new_status not in VALID_TRANSITIONS:
        allowed = list(VALID_TRANSITIONS.keys())
        return jsonify({
            'status': 400,
            'error': 'Bad Request',
            'message': 'Invalid status. Must be one of: %s' % allowed
        }), 400

    if new_status not in VALID_TRANSITIONS[order.status]:
        return jsonify({
            'status': 409,
            'error': 'Conflict',
            'message': 'Cannot transition from %s to %s' % (order.status, new_status)
        }), 409

    order.status = new_status
    db.session.commit()
    return jsonify(order.to_dict()), 200


@api.route('/orders/<int:order_id>', methods=['DELETE'])
def cancel_order(order_id):
    order = get_order_or_404(order_id)
    if order.status not in ('PLACED', 'PREPARING'):
        return jsonify({
            'status': 409,
            'error': 'Conflict',
            'message': 'Cannot cancel order in status: %s' % order.status
        }), 409

    order.status = 'CANCELLED'
    db.session.commit()
    return jsonify({
        'message': 'Order %d cancelled' % order_id,
        'order': order.to_dict()
    }), 200
