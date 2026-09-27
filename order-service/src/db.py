"""The SQLAlchemy handle.

It lives in its own module so models, routes and the seed script can all import
it without importing the application factory (which would be a circular
import). Nothing here touches the database at import time: no ``create_all``.
Schema changes are applied by Alembic, see ``migrations/``.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
