"""JSON error handlers.

This is a JSON API, but a bare ``get_or_404()`` used to bubble up as a Werkzeug
HTML error page, which broke any client that tried to parse the body. Every
error now leaves the service as JSON with the same shape.
"""

from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from db import db


def error_body(status, error, message, details=None):
    body = {}
    body['status'] = status
    body['error'] = error
    body['message'] = message
    if details is not None:
        body['details'] = details
    return body


def json_error(status, error, message, details=None):
    return jsonify(error_body(status, error, message, details)), status


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        # Covers 400, 404, 405, 409, 415 and friends in one place.
        return json_error(exc.code, exc.name, exc.description)

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(exc):
        db.session.rollback()
        app.logger.warning('Integrity error: %s', exc)
        return json_error(
            409,
            'Conflict',
            'The request conflicts with data already stored.'
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):
        db.session.rollback()
        app.logger.exception('Unhandled error')
        return json_error(
            500,
            'Internal Server Error',
            'The server hit an unexpected condition.'
        )
