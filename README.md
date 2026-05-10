# 🍔 Food Delivery App — Microservices

Group assignment for SEZG583 Scalable Services, BITS Pilani WILP.

## Services

| Service             | Port | Responsibility                          |
|---------------------|------|-----------------------------------------|
| restaurant-service  | 5001 | Manage restaurants and menu items       |
| order-service       | 5000 | Place and track orders (calls restaurant-service) |

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
│   ├── src/app.py
│   └── tests/test_restaurant.py
└── order-service/
    ├── Dockerfile
    ├── requirements.txt
    ├── src/app.py
    └── tests/test_order.py
```

---

## Option 1: Run Locally with Docker Compose

```bash
# From the root fooddelivery/ directory
docker compose up --build

# Restaurant Service → http://localhost:5001
# Order Service      → http://localhost:5000
```

---

## Option 2: Deploy to Minikube (Kubernetes)

### Prerequisites
- [minikube](https://minikube.sigs.k8s.io/docs/start/) installed
- [kubectl](https://kubernetes.io/docs/tasks/tools/) installed
- Docker installed

### Step-by-step

```bash
# 1. Start minikube
minikube start

# 2. Point Docker to minikube's daemon (so images are available inside cluster)
eval $(minikube docker-env)          # Linux/Mac
# minikube docker-env | Invoke-Expression    # Windows PowerShell

# 3. Build images inside minikube
docker build -t restaurant-service:latest ./restaurant-service
docker build -t order-service:latest ./order-service

# 4. Apply Kubernetes manifests
kubectl apply -f k8s/restaurant-deployment.yaml
kubectl apply -f k8s/order-deployment.yaml

# 5. Verify pods are running
kubectl get pods
kubectl get services

# 6. Access Order Service (NodePort 30000)
minikube ip     # get your minikube IP, e.g. 192.168.49.2
# Then call: http://192.168.49.2:30000/health
# OR use:
minikube service order-service --url
```

### Kubernetes Dashboard

```bash
# Enable dashboard addon
minikube addons enable dashboard
minikube addons enable metrics-server

# Apply admin service account
kubectl apply -f k8s/dashboard-admin.yaml

# Generate login token
kubectl -n kubernetes-dashboard create token admin-user

# Open dashboard in browser
minikube dashboard
```

---

## API Reference

### Restaurant Service (port 5001)

| Method | Endpoint                          | Description               |
|--------|-----------------------------------|---------------------------|
| GET    | /health                           | Health check              |
| GET    | /restaurants                      | List all restaurants      |
| GET    | /restaurants?cuisine=Indian       | Filter by cuisine         |
| POST   | /restaurants                      | Create restaurant         |
| GET    | /restaurants/{id}                 | Get restaurant by ID      |
| PUT    | /restaurants/{id}                 | Update restaurant         |
| DELETE | /restaurants/{id}                 | Delete restaurant         |
| GET    | /restaurants/{id}/menu            | Get menu for restaurant   |
| POST   | /restaurants/{id}/menu            | Add menu item             |
| GET    | /menu/{item_id}                   | Get menu item (internal)  |
| GET    | /menu/{item_id}/availability      | Check item availability   |

### Order Service (port 5000)

| Method | Endpoint                  | Description              |
|--------|---------------------------|--------------------------|
| GET    | /health                   | Health check             |
| POST   | /orders                   | Place a new order        |
| GET    | /orders                   | List all orders          |
| GET    | /orders?customer_name=X   | Filter orders by customer|
| GET    | /orders/{id}              | Get order by ID          |
| PATCH  | /orders/{id}/status       | Update order status      |
| DELETE | /orders/{id}              | Cancel an order          |

### Order Status Flow
```
PLACED → PREPARING → OUT_FOR_DELIVERY → DELIVERED
   ↓          ↓
CANCELLED  CANCELLED
```

---

## Sample Postman Requests

### Create a Restaurant
```json
POST http://localhost:5001/restaurants
{
  "name": "Biryani House",
  "cuisine": "Indian",
  "address": "45 Brigade Road, Bangalore",
  "rating": 4.2
}
```

### Add Menu Item
```json
POST http://localhost:5001/restaurants/1/menu
{
  "name": "Chicken Biryani",
  "price": 249.0
}
```

### Place an Order
```json
POST http://localhost:5000/orders
{
  "customer_name": "Arjun Kumar",
  "restaurant_id": 1,
  "delivery_address": "22 Koramangala, Bangalore",
  "items": [
    { "menu_item_id": 1, "quantity": 2 }
  ]
}
```

### Update Order Status
```json
PATCH http://localhost:5000/orders/1/status
{
  "status": "PREPARING"
}
```

---

## Running Tests

```bash
# Install test dependencies
pip install pytest flask flask-sqlalchemy requests

# Restaurant Service tests
cd restaurant-service
pytest tests/ -v

# Order Service tests
cd order-service
pytest tests/ -v
```

---

## GitHub Repositories
- Restaurant Service: `https://github.com/<your-org>/restaurant-service`
- Order Service:      `https://github.com/<your-org>/order-service`
