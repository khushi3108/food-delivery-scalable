"""Restaurant Service application factory.

``app.py`` used to hold the models, the routes and a ``db.create_all()`` call
that ran at import time. That import-time call is gone: the schema is owned by
Alembic (``flask db upgrade``) and demo data by ``scripts/seed.py``.

Gunicorn still targets ``app:app`` and the Flask CLI finds the same object, so
``flask --app src/app.py db upgrade`` works from the service directory.
"""

import decimal
import os

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_migrate import Migrate

from config import build_config
from db import db
from errors import register_error_handlers
# Importing the blueprint also imports models, which is what registers the
# mappers that Alembic autogenerate reads.
from routes import api

# migrations/ sits next to src/, in the service root, so the same path works
# locally and inside the container.
SERVICE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(SERVICE_ROOT, 'migrations')

migrate = Migrate()


class ApiJSONProvider(DefaultJSONProvider):
    """Flask cannot serialise Decimal on its own and would raise a 500.

    Money is already turned into a string by ``money_to_json``; this is the
    safety net so a stray Decimal never takes a response down.
    """

    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        return super().default(obj)


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.json = ApiJSONProvider(app)
    app.config.update(build_config(config_overrides))

    db.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR)

    register_error_handlers(app)
    app.register_blueprint(api)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
