# Food Delivery App — Microservices Architecture

> SEZG583 Scalable Services | Group Assignment | BITS Pilani WILP

A microservices-based Food Delivery application built with Python (Flask) and deployed using Docker and Kubernetes (Minikube).

---

## Group Details

| # | Name | BITS ID |
|---|------|---------|
| 1 | < Khusi Gandhi > | < 2024MT03526> |
| 2 | < Vaishnavi R > | < 2024MT03527 > |


---

## Project Overview

This project implements a subset of a Food Delivery platform (similar to Swiggy/Zomato) using a microservices architecture. Two services are fully implemented:

| Service | Port | Responsibility |
|---------|------|----------------|
| **Restaurant Service** | 5001 | Manage restaurants and menu items |
| **Order Service** | 5000 | Place and track food orders |

The Order Service calls the Restaurant Service via REST to validate menu items before accepting an order — demonstrating real inter-service communication.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.12 |
| Framework | Flask 3.0 |
| ORM | Flask-SQLAlchemy |
| Database | SQLite (per service) |
| Communication | Synchronous REST / HTTP |
| Containerisation | Docker + Docker Compose |
| Orchestration | Kubernetes (Minikube) |
| Testing | pytest |

---

## Project Structure

```
fooddelivery/
├── docker-compose.yml
├── k8s/
│   ├── restaurant-deployment.yaml
│   ├── order-deployment.yaml
│   └── dashboard-admin.yaml
├── restaurant-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── src/
│   │   └── app.py
│   └── tests/
│       └── test_restaurant.py
└── order-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── src/
    │   └── app.py
    └── tests/
        └── test_order.py
```

---

## API Reference

### Restaurant Service — `http://localhost:5001`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/restaurants` | List all restaurants |
| POST | `/restaurants` | Create a restaurant |
| GET | `/restaurants/{id}` | Get restaurant by ID |
| PUT | `/restaurants/{id}` | Update restaurant |
| DELETE | `/restaurants/{id}` | Delete restaurant |
| GET | `/restaurants/{id}/menu` | Get menu items |
| POST | `/restaurants/{id}/menu` | Add a menu item |
| GET | `/menu/{item_id}/availability` | Check item availability |

### Order Service — `http://localhost:5002`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/orders` | Place a new order |
| GET | `/orders` | List all orders |
| GET | `/orders/{id}` | Get order by ID |
| PATCH | `/orders/{id}/status` | Update order status |
| DELETE | `/orders/{id}` | Cancel an order |

### Order Status Flow

```
PLACED → PREPARING → OUT_FOR_DELIVERY → DELIVERED
  ↓           ↓
CANCELLED  CANCELLED
```

---

## Running the Project

### Option 1 — Docker Compose (Recommended)

```bash
# From the fooddelivery/ root directory
docker compose up --build

# Restaurant Service → http://localhost:5001
# Order Service      → http://localhost:5002
```

### Option 2 — Run Locally (No Docker)

```bash
# Terminal 1 — Restaurant Service
cd restaurant-service
pip install -r requirements.txt
python src/app.py

# Terminal 2 — Order Service
cd order-service
pip install -r requirements.txt
RESTAURANT_SERVICE_URL=http://localhost:5001 python src/app.py
```

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

# Deploy
kubectl apply -f k8s/restaurant-deployment.yaml
kubectl apply -f k8s/order-deployment.yaml

# Check status
kubectl get pods
kubectl get services

# Get order service URL
minikube service order-service --url
```

---

## Running Tests

```bash
# Restaurant Service — 11 tests
cd restaurant-service
pip install pytest flask flask-sqlalchemy
pytest tests/ -v

# Order Service — 13 tests
cd order-service
pip install pytest flask flask-sqlalchemy requests
pytest tests/ -v
```

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
  -d '{"name": "Chicken Biryani", "price": 249.0}'
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
    restaurants.db           orders.db
      (SQLite)                (SQLite)
```

The Order Service calls `GET /menu/{item_id}` on the Restaurant Service to validate each item before accepting an order. The `RESTAURANT_SERVICE_URL` is injected via environment variable so the same code works locally, in Docker Compose, and in Kubernetes without changes.

---

## References

- Flask Documentation — https://flask.palletsprojects.com/
- Kubernetes Documentation — https://kubernetes.io/docs/
- Minikube — https://minikube.sigs.k8s.io/docs/
- Docker Documentation — https://docs.docker.com/
- Richardson, C. — Microservices Patterns (Manning, 2018)
