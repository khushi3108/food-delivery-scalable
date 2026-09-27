"""Test setup.

Production runs on PostgreSQL, but the tests build the application through the
factory with an in-memory SQLite override so the suite needs no database server
at all. The override is passed into create_app() rather than assigned to
app.config afterwards, because Flask-SQLAlchemy 3.x builds the engine during
init_app() and would otherwise ignore a later change.

DATABASE_URL is set to SQLite before app.py is imported, and that ordering
matters. app.py ends with a module level `app = create_app()` so that gunicorn
can target `app:app`, which means importing the module builds an engine
immediately, before any fixture gets a chance to pass an override. Without the
environment variable set first, that import tries to reach PostgreSQL and the
whole suite fails at collection time.
"""

import os
import sys

import pytest

TEST_DATABASE_URL = 'sqlite+pysqlite:///:memory:'
os.environ['DATABASE_URL'] = TEST_DATABASE_URL

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from app import create_app   # noqa: E402
from db import db            # noqa: E402

TEST_CONFIG = {
    'TESTING': True,
    'SQLALCHEMY_DATABASE_URI': TEST_DATABASE_URL
}


@pytest.fixture
def app():
    application = create_app(TEST_CONFIG)
    with application.app_context():
        # The schema itself is owned by Alembic; create_all is only a shortcut
        # for building the throwaway in-memory database used by the tests.
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
