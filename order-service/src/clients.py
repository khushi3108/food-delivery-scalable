"""Outbound calls to other services.

Kept in its own module so a later step can put retries, a circuit breaker or an
async message instead of this synchronous call in one place, without touching
the routes.
"""

import os

import requests

RESTAURANT_SERVICE_URL = os.getenv('RESTAURANT_SERVICE_URL', 'http://restaurant-service:5001')
REQUEST_TIMEOUT_SECONDS = 3


def fetch_item(item_id):
    """Ask the Restaurant Service about one menu item.

    Returns ``(item, None)`` on success and ``(None, message)`` on failure.
    """
    url = '%s/menu/%s' % (RESTAURANT_SERVICE_URL, item_id)
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        return None, 'Restaurant Service is unreachable'
    except requests.exceptions.RequestException:
        return None, 'Restaurant Service call failed'

    if response.status_code == 200:
        return response.json(), None
    return None, 'Item %s not found in Restaurant Service' % item_id
