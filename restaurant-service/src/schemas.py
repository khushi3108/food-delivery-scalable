"""Request body validation with Pydantic v2.

Before this, request data went straight into the model, so a price could be a
string and a missing field only failed later inside SQLAlchemy. Now every
POST/PUT body is validated first and a bad body comes back as a 400 that lists
the offending fields.
"""

from decimal import Decimal

from flask import request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from errors import json_error


class RestaurantCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    cuisine: str = Field(min_length=1, max_length=80)
    address: str = Field(min_length=1, max_length=200)
    is_open: bool = True
    rating: float = Field(default=0.0, ge=0.0, le=5.0)


class RestaurantUpdate(BaseModel):
    """PUT is a partial update here, so every field is optional."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    cuisine: str | None = Field(default=None, min_length=1, max_length=80)
    address: str | None = Field(default=None, min_length=1, max_length=200)
    is_open: bool | None = None
    rating: float | None = Field(default=None, ge=0.0, le=5.0)


class MenuItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    available: bool = True


def field_path(location):
    """Turn a Pydantic error location tuple into 'items.0.quantity'."""
    parts = []
    for piece in location:
        parts.append(str(piece))
    return '.'.join(parts)


def validation_details(exc):
    details = []
    for problem in exc.errors():
        entry = {}
        entry['field'] = field_path(problem['loc'])
        entry['message'] = problem['msg']
        details.append(entry)
    return details


def parse_body(schema):
    """Validate the JSON body against ``schema``.

    Returns ``(model, None)`` when the body is good and ``(None, response)``
    when it is not, so the caller can simply return the response.
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return None, json_error(
            400,
            'Bad Request',
            'A JSON request body is required.'
        )
    try:
        model = schema.model_validate(payload)
    except ValidationError as exc:
        return None, json_error(
            400,
            'Validation Failed',
            'The request body is not valid.',
            validation_details(exc)
        )
    return model, None
