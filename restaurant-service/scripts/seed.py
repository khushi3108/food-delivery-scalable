"""Insert demo restaurants and menu items.

This used to run inside the application at import time. Under gunicorn
``--preload`` that happened in the master process before forking, and with more
than one replica pointing at the same database the inserts raced each other.
Seeding is now a deliberate operator action:

    cd restaurant-service
    python scripts/seed.py

It is safe to run twice: it does nothing when restaurants already exist, unless
you pass --force, which wipes the demo rows first.
"""

import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from app import create_app          # noqa: E402
from db import db                   # noqa: E402
from models import MenuItem, Restaurant   # noqa: E402

DEMO_RESTAURANTS = [
    {
        'name': 'Pizza Palace',
        'cuisine': 'Italian',
        'address': '12 MG Road, Bangalore',
        'rating': 4.5,
        'menu': [
            {'name': 'Margherita Pizza', 'price': Decimal('299.00')},
            {'name': 'Pepperoni Pizza', 'price': Decimal('349.00')}
        ]
    },
    {
        'name': 'Biryani House',
        'cuisine': 'Indian',
        'address': '45 Brigade Road, Bangalore',
        'rating': 4.2,
        'menu': [
            {'name': 'Chicken Biryani', 'price': Decimal('249.00')},
            {'name': 'Veg Biryani', 'price': Decimal('199.00')}
        ]
    }
]


def wipe_demo_rows():
    """Delete the demo restaurants. The relationship cascade takes the menu."""
    for entry in DEMO_RESTAURANTS:
        existing = Restaurant.query.filter(Restaurant.name == entry['name']).all()
        for restaurant in existing:
            db.session.delete(restaurant)
    db.session.commit()


def insert_demo_rows():
    for entry in DEMO_RESTAURANTS:
        restaurant = Restaurant(
            name=entry['name'],
            cuisine=entry['cuisine'],
            address=entry['address'],
            rating=entry['rating']
        )
        for menu_entry in entry['menu']:
            item = MenuItem(name=menu_entry['name'], price=menu_entry['price'])
            restaurant.menu_items.append(item)
        db.session.add(restaurant)
    db.session.commit()


def main(argv):
    force = '--force' in argv

    app = create_app()
    with app.app_context():
        if force:
            wipe_demo_rows()

        count = Restaurant.query.count()
        if count > 0:
            print('Skipping seed: %d restaurant row(s) already present.' % count)
            print('Run with --force to replace the demo rows.')
            return 0

        insert_demo_rows()
        print('Seeded %d restaurants.' % len(DEMO_RESTAURANTS))
        return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
