# Quick Start & Common Tasks

## Running the System

```bash
# Start all services with Docker Compose
docker-compose up --build

# Access points:
# - API Gateway: http://localhost:5000
# - pgAdmin: http://localhost:5050 (admin@admin.com / admin)
# - RabbitMQ Management: http://localhost:15672 (guest / guest)
```

## Testing the API

### 1. Create an Order
```bash
curl -X POST http://localhost:5000/main/orders \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "product_id": 1,
    "quantity": 5
  }'
```

### 2. Add Inventory Item
```bash
curl -X POST http://localhost:5000/inventory/new \
  -H "Content-Type: application/json" \
  -d '{
    "quantity": 100,
    "description": "Product XYZ"
  }'
```

### 3. Register User
```bash
curl -X POST http://localhost:5000/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

### 4. Get All Users
```bash
curl http://localhost:5000/users/
```

---

## Understanding Message Flow

### When you POST /main/orders:

1. **Client** sends HTTP request with order details
2. **API Gateway** validates input, generates unique correlation_id, creates callback queue
3. **API Gateway** publishes message to `order_created` queue
4. **API Gateway** blocks and waits for response on callback queue
5. **Order Service** consumes from `order_created` queue
6. **Order Service** needs to validate inventory, so publishes to `order_validate` queue
7. **Inventory Service** consumes from `order_validate` queue
8. **Inventory Service** checks stock with write lock, decrements quantity
9. **Inventory Service** publishes response back to Order Service's callback queue
10. **Order Service** receives response, if valid: saves order to DB
11. **Order Service** publishes success/failure response to API Gateway's callback queue
12. **API Gateway** receives response (matches correlation_id), stops waiting
13. **API Gateway** returns HTTP response to client

### Why this pattern?

- **Asynchronous processing**: Services don't block each other
- **Resilience**: If a service crashes, messages queue up and are processed when it restarts
- **Scalability**: Can run multiple instances of each service
- **Visibility**: Each step can be logged and monitored
- **Request-Reply**: Clients get synchronous responses despite async backend

---

## Monitoring & Debugging

### Check RabbitMQ Queues
1. Go to http://localhost:15672
2. Login: guest / guest
3. View queues, messages pending, consumers

### Check Database
1. Go to http://localhost:5050
2. Login: admin@admin.com / admin
3. Query `orders`, `inventory`, `user` tables

### Check Service Logs
```bash
# Watch all services
docker-compose logs -f

# Specific service
docker-compose logs -f order_services
docker-compose logs -f inventory_services
docker-compose logs -f user_services
docker-compose logs -f api_gateway
```

---

## Service Dependencies

```
API Gateway ← (all services depend on these):
  ├─ PostgreSQL (database)
  └─ RabbitMQ (messaging)

Order Service ← (depends on):
  ├─ PostgreSQL
  └─ RabbitMQ

Inventory Service ← (depends on):
  ├─ PostgreSQL
  └─ RabbitMQ

User Service ← (depends on):
  ├─ PostgreSQL
  └─ RabbitMQ
```

All services start ONLY after health checks pass on database and RabbitMQ.

---

## Scaling Considerations

✅ **Can scale horizontally**:
- Run multiple instances of Order Service, Inventory Service, User Service
- Each will listen to same queue, RabbitMQ round-robins messages

⚠️ **Single points of failure (need HA setup)**:
- PostgreSQL (shared database)
- RabbitMQ (message broker)

🔒 **Write safety**:
- Inventory uses write locks (`with_for_update`)
- Safe for concurrent order processing

---

## File Structure

```
README.md                          # Project overview
ARCHITECTURE.md                    # DETAILED ARCHITECTURE (generated)
docker-compose.yml                 # All services configuration
pyproject.toml                      # Python dependencies

api_gateway/
  app/
    main.py                         # FastAPI app + routes
    producer.py                     # publish_and_wait_for_response pattern
    crud.py                         # Database queries
    models.py                        # Pydantic models for validation
    database.py                      # SQLModel setup

order_services/
  app/
    consumer.py                      # Message listener + processing
    models.py                         # Order table model
    database.py                       # DB connection

inventory_services/
  app/
    consumer.py                       # Inventory validation + updates
    models.py                         # Inventory table model
    database.py                       # DB connection

user_services/
  app/
    consumer.py                        # User registration logic
    models.py                          # User table model
    database.py                        # DB connection

notification_services/              # Placeholder (not configured)
```
