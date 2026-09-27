"""Database models for the Restaurant Service."""

from datetime import datetime, timezone

from db import db
from money import Money, money_to_json


def utc_now():
    """Naive UTC timestamp, so the column stays a plain TIMESTAMP everywhere."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Restaurant(db.Model):
    __tablename__ = 'restaurant'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    cuisine = db.Column(db.String(80), nullable=False, index=True)
    address = db.Column(db.String(200), nullable=False)
    is_open = db.Column(db.Boolean, nullable=False, default=True)
    rating = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)

    # Soft delete. A restaurant referenced by historical orders must not vanish,
    # so DELETE only stamps this column and every read filters on it being NULL.
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)

    # Without this relationship a deleted restaurant left its menu items behind
    # pointing at a dead foreign key. The cascade cleans them up whenever a row
    # really is removed (for example by the seed script).
    menu_items = db.relationship(
        'MenuItem',
        back_populates='restaurant',
        cascade='all, delete-orphan',
        lazy='select'
    )

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'cuisine': self.cuisine,
            'address': self.address,
            'is_open': self.is_open,
            'rating': self.rating
        }


class MenuItem(db.Model):
    __tablename__ = 'menu_item'

    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer,
        db.ForeignKey('restaurant.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(Money, nullable=False)
    available = db.Column(db.Boolean, nullable=False, default=True)

    restaurant = db.relationship('Restaurant', back_populates='menu_items')

    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'price': money_to_json(self.price),
            'available': self.available
        }
