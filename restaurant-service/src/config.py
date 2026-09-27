"""Application configuration.

The database is PostgreSQL. ``DATABASE_URL`` is still injected by the
environment (Docker Compose, Kubernetes) so the same image runs everywhere.
Unit tests pass an override and run against SQLite in memory, which is why the
engine options are chosen per URL instead of being hard-coded.
"""

import os

DEFAULT_DATABASE_URL = 'postgresql+psycopg://restaurant:restaurant@localhost:5432/restaurants'


def normalise_database_url(url):
    """Make sure a PostgreSQL URL uses the psycopg 3 driver."""
    if url.startswith('postgres://'):
        return 'postgresql+psycopg://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg://' + url[len('postgresql://'):]
    return url


def engine_options_for(database_url):
    """Pool settings only make sense for a real network database."""
    if database_url.startswith('postgresql'):
        options = {}
        options['pool_pre_ping'] = True     # drop connections the server closed
        options['pool_size'] = 5            # 2 gunicorn workers per pod, keep it modest
        options['max_overflow'] = 5
        options['pool_timeout'] = 10
        options['pool_recycle'] = 1800      # recycle every 30 minutes
        return options
    return {'pool_pre_ping': True}


def build_config(overrides=None):
    config = {}
    config['SQLALCHEMY_DATABASE_URI'] = normalise_database_url(
        os.getenv('DATABASE_URL', DEFAULT_DATABASE_URL)
    )
    config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if overrides is not None:
        for key in overrides:
            config[key] = overrides[key]

    if 'SQLALCHEMY_DATABASE_URI' in config:
        config['SQLALCHEMY_DATABASE_URI'] = normalise_database_url(
            config['SQLALCHEMY_DATABASE_URI']
        )

    if 'SQLALCHEMY_ENGINE_OPTIONS' not in config:
        config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options_for(
            config['SQLALCHEMY_DATABASE_URI']
        )
    return config
