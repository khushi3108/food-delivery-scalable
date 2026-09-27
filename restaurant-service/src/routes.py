"""HTTP routes for the Restaurant Service."""

from flask import Blueprint, abort, jsonify, request

from db import db
from models import MenuItem, Restaurant, utc_now
from money import money_to_json
from pagination import encode_cursor, page_envelope, read_cursor, read_limit
from schemas import MenuItemCreate, RestaurantCreate, RestaurantUpdate, parse_body

api = Blueprint('api', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def live_restaurants():
    """Base query that hides soft-deleted restaurants."""
    return Restaurant.query.filter(Restaurant.deleted_at.is_(None))


def get_live_restaurant_or_404(restaurant_id):
    restaurant = live_restaurants().filter(Restaurant.id == restaurant_id).first()
    if restaurant is None:
        abort(404, description='Restaurant %d was not found.' % restaurant_id)
    return restaurant


def get_live_menu_item_or_404(item_id):
    """A menu item of a soft-deleted restaurant is treated as gone too."""
    item = (
        MenuItem.query
        .join(Restaurant, MenuItem.restaurant_id == Restaurant.id)
        .filter(MenuItem.id == item_id)
        .filter(Restaurant.deleted_at.is_(None))
        .first()
    )
    if item is None:
        abort(404, description='Menu item %d was not found.' % item_id)
    return item


# ── Health ────────────────────────────────────────────────────────────────────

@api.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'Restaurant Service is running'}), 200


# ── Restaurants ───────────────────────────────────────────────────────────────

@api.route('/restaurants', methods=['GET'])
def get_restaurants():
    limit = read_limit()
    cursor = read_cursor(1)

    query = live_restaurants()

    cuisine = request.args.get('cuisine')
    if cuisine:
        query = query.filter(Restaurant.cuisine == cuisine)

    if cursor is not None:
        try:
            last_id = int(cursor[0])
        except ValueError:
            abort(400, description='cursor is not a valid pagination cursor.')
        query = query.filter(Restaurant.id > last_id)

    # One extra row tells us whether another page exists.
    rows = query.order_by(Restaurant.id.asc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    items = []
    for restaurant in rows:
        items.append(restaurant.to_dict())

    next_cursor = None
    if has_more:
        next_cursor = encode_cursor([rows[-1].id])

    return jsonify(page_envelope(items, next_cursor, limit)), 200


@api.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    restaurant = get_live_restaurant_or_404(restaurant_id)
    return jsonify(restaurant.to_dict()), 200


@api.route('/restaurants', methods=['POST'])
def create_restaurant():
    body, error = parse_body(RestaurantCreate)
    if error is not None:
        return error

    restaurant = Restaurant(
        name=body.name,
        cuisine=body.cuisine,
        address=body.address,
        is_open=body.is_open,
        rating=body.rating
    )
    db.session.add(restaurant)
    db.session.commit()
    return jsonify(restaurant.to_dict()), 201


@api.route('/restaurants/<int:restaurant_id>', methods=['PUT'])
def update_restaurant(restaurant_id):
    restaurant = get_live_restaurant_or_404(restaurant_id)

    body, error = parse_body(RestaurantUpdate)
    if error is not None:
        return error

    # Only fields actually present in the request body are touched.
    supplied = body.model_dump(exclude_unset=True)
    for field in supplied:
        setattr(restaurant, field, supplied[field])

    db.session.commit()
    return jsonify(restaurant.to_dict()), 200


@api.route('/restaurants/<int:restaurant_id>', methods=['DELETE'])
def delete_restaurant(restaurant_id):
    restaurant = get_live_restaurant_or_404(restaurant_id)
    # Soft delete: historical orders still reference this restaurant, so the row
    # and its menu items stay for the audit trail and simply stop being served.
    restaurant.deleted_at = utc_now()
    db.session.commit()
    return jsonify({'message': 'Restaurant %d deleted' % restaurant_id}), 200


# ── Menu items ────────────────────────────────────────────────────────────────

@api.route('/restaurants/<int:restaurant_id>/menu', methods=['GET'])
def get_menu(restaurant_id):
    get_live_restaurant_or_404(restaurant_id)
    rows = (
        MenuItem.query
        .filter(MenuItem.restaurant_id == restaurant_id)
        .order_by(MenuItem.id.asc())
        .all()
    )
    items = []
    for item in rows:
        items.append(item.to_dict())
    return jsonify(items), 200


@api.route('/restaurants/<int:restaurant_id>/menu', methods=['POST'])
def add_menu_item(restaurant_id):
    get_live_restaurant_or_404(restaurant_id)

    body, error = parse_body(MenuItemCreate)
    if error is not None:
        return error

    item = MenuItem(
        restaurant_id=restaurant_id,
        name=body.name,
        price=body.price,
        available=body.available
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@api.route('/menu/<int:item_id>', methods=['GET'])
def get_menu_item(item_id):
    """Called by the Order Service to validate an item before placing an order."""
    item = get_live_menu_item_or_404(item_id)
    return jsonify(item.to_dict()), 200


@api.route('/menu/<int:item_id>/availability', methods=['GET'])
def check_availability(item_id):
    item = get_live_menu_item_or_404(item_id)
    return jsonify({
        'item_id': item_id,
        'available': item.available,
        'price': money_to_json(item.price)
    }), 200
