"""Money handling.

Prices used to be stored as ``db.Float``. Binary floating point cannot hold a
value like 249.10 exactly, so totals drifted and never reconciled against a
payment provider. Everything money related now goes through ``Decimal`` with
exactly two decimal places, and the column type below keeps it that way in the
database as well.
"""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import types

TWO_PLACES = Decimal('0.01')


def to_money(value):
    """Convert anything price-like into a Decimal rounded to 2 places."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, float):
        # str() first, otherwise Decimal(0.1) keeps the binary float error.
        amount = Decimal(str(value))
    else:
        amount = Decimal(value)
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def money_to_json(value):
    """Money goes over the wire as a string so no client re-introduces floats."""
    if value is None:
        return None
    return str(to_money(value))


class Money(types.TypeDecorator):
    """NUMERIC(10, 2) on PostgreSQL, TEXT on SQLite.

    SQLite has no native decimal type, so SQLAlchemy would round-trip a NUMERIC
    column through a C double and warn about it. Storing the digits as text on
    SQLite keeps the unit tests exact while production still gets a real
    NUMERIC column.
    """

    impl = types.Numeric
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'sqlite':
            return dialect.type_descriptor(types.String(20))
        return dialect.type_descriptor(types.Numeric(10, 2))

    def process_bind_param(self, value, dialect):
        amount = to_money(value)
        if amount is None:
            return None
        if dialect.name == 'sqlite':
            return str(amount)
        return amount

    def process_result_value(self, value, dialect):
        return to_money(value)
