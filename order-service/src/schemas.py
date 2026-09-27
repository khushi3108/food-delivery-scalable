"""Request body validation with Pydantic v2.

The old code called ``int(entry['quantity'])`` straight on the request body, so
``"abc"`` was a 500 and ``-3`` was accepted and quietly discounted the order.
Quantities are now integers of at least 1 before any arithmetic happens.
"""

from flask import request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from errors import json_error


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    menu_item_id: int = Field(ge=1)
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    customer_name: str = Field(min_length=1, max_length=120)
    restaurant_id: int = Field(ge=1)
    delivery_address: str = Field(min_length=1, max_length=200)
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str = Field(min_length=1, max_length=50)


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
