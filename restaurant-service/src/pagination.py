"""Cursor pagination helpers.

Listing endpoints used to call ``.all()`` over the whole table, which gets
slower with every row and eventually times out. They now return one page plus a
``next_cursor`` the client sends back to get the following page. The cursor is
keyed on the sort columns, so inserts and deletes cannot make rows repeat or go
missing the way OFFSET does.
"""

import base64
import binascii

from flask import abort, request

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def read_limit(default=DEFAULT_PAGE_SIZE, maximum=MAX_PAGE_SIZE):
    raw = request.args.get('limit')
    if raw is None:
        return default
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        abort(400, description='limit must be an integer.')
    if limit < 1:
        abort(400, description='limit must be at least 1.')
    if limit > maximum:
        abort(400, description='limit must not be greater than %d.' % maximum)
    return limit


def encode_cursor(parts):
    values = []
    for part in parts:
        values.append(str(part))
    raw = '|'.join(values)
    return base64.urlsafe_b64encode(raw.encode('utf-8')).decode('ascii')


def read_cursor(expected_parts):
    """Return the decoded cursor parts, or None when no cursor was sent."""
    raw = request.args.get('cursor')
    if raw is None or raw == '':
        return None
    try:
        decoded = base64.urlsafe_b64decode(raw.encode('ascii')).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError, UnicodeEncodeError, ValueError):
        abort(400, description='cursor is not a valid pagination cursor.')
    parts = decoded.split('|')
    if len(parts) != expected_parts:
        abort(400, description='cursor is not a valid pagination cursor.')
    return parts


def page_envelope(items, next_cursor, limit):
    return {
        'items': items,
        'next_cursor': next_cursor,
        'limit': limit
    }
