"""Database models for the Order Service."""

from datetime import datetime, timezone
from decimal import Decimal

from db import db
from money import Money, money_to_json, to_money


def utc_now():
    """Naive UTC timestamp, so the column stays a plain TIMESTAMP everywhere."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Order(db.Model):
    __tablename__ = 'orders'   # 'order' is a reserved word in SQL, avoid quoting it forever

    # (created_at, id) is the sort key used by cursor pagination on GET /orders,
    # so it gets a composite index in the same direction the query reads it.
    __table_args__ = (
        db.Index('ix_orders_created_at_id', 'created_at', 'id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.String(50), nullable=False, default='PLACED', index=True)
    total_amount = db.Column(Money, nullable=False, default=Decimal('0.00'))
    delivery_address = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now, index=True)

    items = db.relationship(
        'OrderItem',
        back_populates='order',
        cascade='all, delete-orphan',
        lazy='select'
    )

    def to_dict(self):
        item_dicts = []
        for item in self.items:
            item_dicts.append(item.to_dict())
        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'restaurant_id': self.restaurant_id,
            'items': item_dicts,
            'status': self.status,
            'total_amount': money_to_json(self.total_amount),
            'delivery_address': self.delivery_address,
            'created_at': self.created_at.isoformat()
        }


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    menu_item_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(Money, nullable=False)

    order = db.relationship('Order', back_populates='items')

    def subtotal(self):
        return to_money(to_money(self.unit_price) * self.quantity)

    def to_dict(self):
        return {
            'menu_item_id': self.menu_item_id,
            'name': self.name,
            'quantity': self.quantity,
            'unit_price': money_to_json(self.unit_price),
            'subtotal': money_to_json(self.subtotal())
        }
