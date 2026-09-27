# Food Delivery App — Microservices Architecture

> SEZG583 Scalable Services | Group Assignment | BITS Pilani WILP

A microservices-based Food Delivery application built with Python (Flask) and deployed using Docker and Kubernetes (Minikube).

---





---

## Project Overview

This project implements a subset of a Food Delivery platform (similar to Swiggy/Zomato) using a microservices architecture. Two services are fully implemented:

| Service | Port | Responsibility |
|---------|------|----------------|
| **Restaurant Service** | 5001 | Manage restaurants and menu items |
| **Order Service** | 5000 | Place and track food orders |

The Order Service calls the Restaurant Service via REST to validate menu items before accepting an order — demonstrating real inter-service communication.

Each service owns its own PostgreSQL database and never reads the other's
tables. Every replica of a service shares that service's database, so the
deployments can be scaled out horizontally.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Framework | Flask 3.0 |
| ORM | Flask-SQLAlchemy 3.1 |
| Database | PostgreSQL 16 — one database per service |
| Migrations | Alembic via Flask-Migrate |
| Validation | Pydantic v2 |
| DB driver | psycopg 3 |
| Communication | Synchronous REST / HTTP |
| Containerisation | Docker + Docker Compose |
| Orchestration | Kubernetes (Minikube) |
| Testing | pytest |

---

## Project Structure

Each service is a small package instead of one large `app.py`. Both services
follow the same layout, so what you learn in one applies to the other.

```
distributed-order-platform/
├── docker-compose.yml
├── k8s/
│   ├── restaurant-deployment.yaml   # Secret, PVC, Postgres, migrate Job, app, Service
│   ├── order-deployment.yaml        # same shape for the Order Service
│   └── dashboard-admin.yaml
├── restaurant-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── migrations/                  # Alembic, initial revision 0001_initial
│   │   └── versions/0001_initial_schema.py
│   ├── scripts/
│   │   └── seed.py                  # demo data, run by an operator on purpose
│   ├── src/
│   │   ├── app.py                   # create_app() factory, JSON provider
│   │   ├── config.py                # DATABASE_URL and the engine pool settings
│   │   ├── db.py                    # the SQLAlchemy handle, nothing else
│   │   ├── errors.py                # JSON error handlers
│   │   ├── models.py                # Restaurant, MenuItem
│   │   ├── money.py                 # Decimal helpers and the Money column type
│   │   ├── pagination.py            # cursor helpers
│   │   ├── routes.py                # the HTTP layer
│   │   └── schemas.py               # Pydantic request bodies
│   └── tests/
│       ├── conftest.py              # SQLite in-memory app fixture
│       └── test_restaurant.py
└── order-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── migrations/
    │   └── versions/0001_initial_schema.py
    ├── src/
    │   ├── app.py
    │   ├── clients.py               # the call out to the Restaurant Service
    │   ├── config.py
    │   ├── db.py
    │   ├── errors.py
    │   ├── models.py                # Order, OrderItem
    │   ├── money.py
    │   ├── pagination.py
    │   ├── routes.py
    │   └── schemas.py
    └── tests/
        ├── conftest.py
        └── test_order.py
```

The Order Service has no `scripts/seed.py`: there is no demo order to insert
that would not need the Restaurant Service running. Orders are created through
the API.

---

## API Reference

### Restaurant Service — `http://localhost:5001`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/restaurants` | List restaurants, cursor paginated |
| POST | `/restaurants` | Create a restaurant |
| GET | `/restaurants/{id}` | Get restaurant by ID |
| PUT | `/restaurants/{id}` | Update restaurant |
| DELETE | `/restaurants/{id}` | Soft delete a restaurant |
| GET | `/restaurants/{id}/menu` | Get menu items |
| POST | `/restaurants/{id}/menu` | Add a menu item |
| GET | `/menu/{item_id}` | Get one menu item (used by the Order Service) |
| GET | `/menu/{item_id}/availability` | Check item availability |

### Order Service — `http://localhost:5002`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/orders` | Place a new order |
| GET | `/orders` | List orders, cursor paginated |
| GET | `/orders/{id}` | Get order by ID |
| PATCH | `/orders/{id}/status` | Update order status |
| DELETE | `/orders/{id}` | Cancel an order |

### Money is a string, not a number

Every money field — `price`, `unit_price`, `subtotal`, `total_amount` — is a
`NUMERIC(10, 2)` column mapped to a Python `Decimal`, and it is serialised as a
**JSON string** with exactly two decimals:

```json
{ "total_amount": "747.30", "items": [ { "unit_price": "249.10", "subtotal": "747.30" } ] }
```

Previously these were `db.Float`. Binary floating point cannot hold a value like
`249.10`, so `249.10 * 3` came out as `747.3000000000001` and the error grew with
every line of the order; totals could not be reconciled against a payment
provider. A string keeps the exact value and stops any client from parsing it
back into a float by accident. Clients should read these fields into their own
decimal type.

Prices may be **sent** as a number or a string (`199`, `199.5`, `"249.10"`); they
always come back as a two-decimal string.

### Cursor pagination

`GET /orders` and `GET /restaurants` return a page, not the whole table.

| Parameter | Meaning |
|-----------|---------|
| `limit` | page size, default **20**, maximum **100**; anything else is a 400 |
| `cursor` | opaque value from the previous response's `next_cursor` |

The response is an envelope:

```json
{
  "items": [ ... ],
  "next_cursor": "MjAyNi0wOS0yN1QxMTo1MjozNy45MDc3MzF8MTU=",
  "limit": 20
}
```

`next_cursor` is `null` on the last page. Treat the cursor as opaque: it encodes
the sort key, `(created_at, id)` for orders and `id` for restaurants, so rows are
never repeated or skipped when data changes between pages, which is exactly what
`OFFSET` gets wrong. Orders are returned newest first; restaurants by ascending
id. Filters (`customer_name`, `status`, `cuisine`) must be resent with every
page.

### Errors are always JSON

A `404` used to return a Werkzeug HTML page, which broke any client that parsed
the body. Every error now has the same JSON shape:

```json
{ "status": 404, "error": "Not Found", "message": "Order 999 was not found." }
```

A failed body validation adds a `details` list naming each bad field:

```json
{
  "status": 400,
  "error": "Validation Failed",
  "message": "The request body is not valid.",
  "details": [ { "field": "items.0.quantity", "message": "Input should be greater than or equal to 1" } ]
}
```

Request bodies are validated with Pydantic before anything touches the database.
`quantity` must be an integer of at least 1 and `price` must be at least 0, so
`"abc"` is a 400 instead of a 500 and `-3` can no longer discount an order.

### Soft delete

`DELETE /restaurants/{id}` stamps a `deleted_at` column instead of removing the
row. The restaurant, and its menu items, disappear from every endpoint (`404`),
but the rows survive, because historical orders reference them and hard deleting
would destroy the audit trail. `Restaurant.menu_items` carries
`cascade='all, delete-orphan'`, so a genuine delete (for example from the seed
script) still cannot leave menu items pointing at a restaurant that is gone.

### Order Status Flow

```
PLACED → PREPARING → OUT_FOR_DELIVERY → DELIVERED
  ↓           ↓
CANCELLED  CANCELLED
```

---

## Running the Project

The database schema is applied by Alembic, never by the application. There is no
`db.create_all()` anywhere on the import path, so a service that starts against
an empty database does not silently invent its own tables.

### Option 1 — Docker Compose (Recommended)

```bash
docker compose up --build

# Restaurant Service → http://localhost:5001
# Order Service      → http://localhost:5002
```

Compose brings up five things per run: two PostgreSQL databases (one per
service, so neither service can read the other's tables), two one-shot migration
containers, and the two applications. The ordering is gated:

```
restaurant-db healthy → restaurant-migrate completes → restaurant-service healthy → order-service
order-db healthy      → order-migrate completes      ↗
```

Demo restaurants and menu items are not inserted automatically. Add them when you
want them:

```bash
docker compose exec restaurant-service python scripts/seed.py
```

### Option 2 — Run Locally (No Docker)

You need a PostgreSQL server for this path. Create one database per service:

```bash
createdb restaurants
createdb orders
```

```bash
# Terminal 1 — Restaurant Service
cd restaurant-service
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://localhost:5432/restaurants
flask --app src/app.py db upgrade      # apply migrations
python scripts/seed.py                 # optional demo data
python src/app.py

# Terminal 2 — Order Service
cd order-service
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://localhost:5432/orders
flask --app src/app.py db upgrade
RESTAURANT_SERVICE_URL=http://localhost:5001 python src/app.py
```

### Database migrations

Both services use Flask-Migrate, run from the service directory:

```bash
flask --app src/app.py db upgrade          # apply everything outstanding
flask --app src/app.py db migrate -m "..." # generate a revision from the models
flask --app src/app.py db downgrade -1     # step back one revision
flask --app src/app.py db current          # which revision is applied
```

`DATABASE_URL` must be set, or the default local PostgreSQL URL in
`src/config.py` is used. A plain `postgres://` or `postgresql://` URL is rewritten
to `postgresql+psycopg://` automatically, so a managed-database URL works as
pasted.

### Option 3 — Kubernetes (Minikube)

```bash
# Start minikube
minikube start

# Point Docker to minikube daemon
eval $(minikube docker-env)       # Mac/Linux
minikube docker-env | Invoke-Expression   # Windows PowerShell

# Build images inside minikube
docker build -t restaurant-service:latest ./restaurant-service
docker build -t order-service:latest ./order-service

# Deploy. Each file carries the service's database, its migration Job and the
# application, in that order.
kubectl apply -f k8s/restaurant-deployment.yaml
kubectl apply -f k8s/order-deployment.yaml

# The application pods hold in an init container until the migration Job has
# created the schema, so watch the Jobs first.
kubectl get jobs
kubectl wait --for=condition=complete job/restaurant-migrate --timeout=180s
kubectl wait --for=condition=complete job/order-migrate --timeout=180s

# Check status
kubectl get pods
kubectl get services

# Optional demo data
kubectl exec deploy/restaurant-service -- python scripts/seed.py

# Get order service URL
minikube service order-service --url
```

---

## Running Tests

The suite needs no database server. The fixtures build the application through
`create_app()` with an in-memory SQLite override, so tests run anywhere while
production stays on PostgreSQL.

```bash
# Restaurant Service — 30 tests
cd restaurant-service
pip install -r requirements.txt pytest
python -m pytest -v

# Order Service — 34 tests
cd order-service
pip install -r requirements.txt pytest
python -m pytest -v
```

One detail to be aware of on the SQLite path: the Alembic revision declares
money columns as `NUMERIC(10, 2)`, and SQLite's type affinity stores those as
reals rather than exact decimals. The application always quantises to two places
on the way in and out, so values stay correct, but exact decimal *storage* is a
PostgreSQL property. The tests build their schema from the models, where the
money type is text on SQLite, and are exact.

---

## Sample API Calls

### Create a Restaurant
```bash
curl -X POST http://localhost:5001/restaurants \
  -H "Content-Type: application/json" \
  -d '{"name": "Biryani House", "cuisine": "Indian", "address": "45 Brigade Road, Bangalore", "rating": 4.2}'
```

### Add a Menu Item
```bash
curl -X POST http://localhost:5001/restaurants/1/menu \
  -H "Content-Type: application/json" \
  -d '{"name": "Chicken Biryani", "price": "249.10"}'
```

### Place an Order
```bash
curl -X POST http://localhost:5002/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Arjun Kumar",
    "restaurant_id": 1,
    "delivery_address": "22 Koramangala, Bangalore",
    "items": [{"menu_item_id": 1, "quantity": 2}]
  }'
```

### Update Order Status
```bash
curl -X PATCH http://localhost:5002/orders/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "PREPARING"}'
```

### Walk a Paginated List
```bash
# first page
curl "http://localhost:5002/orders?limit=20"

# next page: pass the next_cursor from the previous response back in
curl "http://localhost:5002/orders?limit=20&cursor=<next_cursor>"

# filters are resent with every page
curl "http://localhost:5001/restaurants?cuisine=Indian&limit=50"
```

---

## Kubernetes Dashboard

```bash
minikube addons enable dashboard
minikube addons enable metrics-server
kubectl apply -f k8s/dashboard-admin.yaml
kubectl -n kubernetes-dashboard create token admin-user
minikube dashboard
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Client / Postman               │
└──────────┬──────────────────────┬────────────────┘
           │                      │
           ▼                      ▼
  ┌─────────────────┐    ┌─────────────────┐
  │ Restaurant Svc  │◄───│   Order Svc     │
  │   Port: 5001    │    │   Port: 5000    │
  │  (ClusterIP)    │    │  (NodePort)     │
  └────────┬────────┘    └────────┬────────┘
           │                      │
           ▼                      ▼
  ┌─────────────────┐    ┌─────────────────┐
  │  restaurant-db  │    │    order-db     │
  │  PostgreSQL 16  │    │  PostgreSQL 16  │
  │   restaurants   │    │     orders      │
  └─────────────────┘    └─────────────────┘
```

Every replica of a service shares that service's one database, which is what
makes `replicas: 2` mean anything. The previous version ran SQLite inside each
container, so two replicas held two private database files and served different
data. The two services keep separate databases: the Order Service still learns
about menu items by calling the Restaurant Service over HTTP, never by reading
its tables.

The Order Service calls `GET /menu/{item_id}` on the Restaurant Service to validate each item before accepting an order. The `RESTAURANT_SERVICE_URL` is injected via environment variable so the same code works locally, in Docker Compose, and in Kubernetes without changes.

---

## Not Here Yet

This is the data layer and validation. The following are deliberately left for
later steps, and the code leaves room for them rather than pretending they exist:

- **Asynchronous messaging.** The Order Service still calls the Restaurant
  Service synchronously (3 second timeout, `502` when unreachable). That call
  lives alone in `order-service/src/clients.py` so a retry policy, a circuit
  breaker or an event instead of a call can be dropped in there.
- **Idempotency keys** on `POST /orders`. Two identical retried requests still
  create two orders today.
- **Authentication and authorisation.** Every endpoint is open.
- **Caching.** No Redis; every read hits PostgreSQL.
- **Distributed transactions.** Nothing coordinates a change across both
  databases.
- **`status` as a database enum.** Order status is a validated string with a
  transition table in `routes.py`, not a PostgreSQL enum type.
- **Restaurant Service pagination on the menu.** `GET /restaurants/{id}/menu`
  still returns the whole menu, because a menu is naturally small; the list
  endpoints that grow without limit are the two that were paginated.

## References

- Flask Documentation — https://flask.palletsprojects.com/
- Kubernetes Documentation — https://kubernetes.io/docs/
- Minikube — https://minikube.sigs.k8s.io/docs/
- Docker Documentation — https://docs.docker.com/
- Richardson, C. — Microservices Patterns (Manning, 2018)
