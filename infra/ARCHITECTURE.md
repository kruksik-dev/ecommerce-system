# E-Commerce System Architecture

## Overview

This is a **microservices-based e-commerce platform** built with **FastAPI**, **RabbitMQ**, and **PostgreSQL**. The system uses asynchronous message-driven communication between services for loose coupling and scalability.

---

## System Components

### 1. **Infrastructure Layer**

#### PostgreSQL Database
- Shared database for all services (single `ecommerce` database)
- Connection: `postgresql+asyncpg://postgres:postgres@database:5432/ecommerce`
- Services connect using async SQLModel ORM

#### RabbitMQ Message Broker
- **Port 5672**: AMQP protocol (internal service communication)
- **Port 15672**: Management console
- Pattern: Request-Reply pattern with correlation IDs and callback queues

#### pgAdmin
- Database admin interface at `http://localhost:5050`
- Credentials: admin@admin.com / admin

---

## Services Architecture

### 2. **API Gateway** (Entry Point)
**Technology**: FastAPI
**Port**: 5000 (maps to 8000 internal)

#### Responsibilities:
- HTTP API for client requests
- Request aggregation and routing
- Synchronous interface to async services (using `publish_and_wait_for_response`)

#### Endpoints:

```
POST /main/orders              → Creates order (publishes to "order_created" queue)
POST /inventory/new            → Adds inventory item (publishes to "inventory_new_item" queue)
POST /users/register           → Registers user (publishes to "user_register" queue)
GET  /users/                   → Lists all users (direct DB query)
GET  /users/{user_id}          → Gets user by ID (direct DB query)
```

#### Key Mechanism: Request-Reply Pattern
```
1. Client → API Gateway (HTTP POST)
2. API Gateway → RabbitMQ (Publish message with correlation_id + reply_to queue)
3. Service processes message → Publishes response to callback_queue with same correlation_id
4. API Gateway receives response → Returns to client
```

---

### 3. **Order Service**
**Responsibility**: Order processing and persistence

#### Message Handlers:
- **Queue**: `order_created` (listens)
- **Process**:
  1. Receives order creation request
  2. Validates inventory by sending request to `order_validate` queue
  3. Waits for inventory response (RPC pattern)
  4. If valid: saves order to DB, sends success response
  5. If invalid: sends error response

#### Database: Orders table
```
Order:
  - id (int, PK)
  - user_id (FK)
  - product_id (FK)
  - quantity (int)
  - status
  - created_at
```

#### Message Flow:
```
API Gateway                Order Service           Inventory Service
     │                         │                          │
     ├─ order_created ────────→│                          │
     │                         ├─ order_validate ────────→│
     │                         │                  [check stock]
     │                         │←─ response ──────────────┤
     │                         │ [update DB]
     │←─ response ────────────┤│
     │                         │
```

---

### 4. **Inventory Service**
**Responsibility**: Product inventory management

#### Message Handlers:
- **Queue**: `inventory_new_item` (listens)
- **Queue**: `order_validate` (listens, RPC style)

#### Operations:

**1. Add New Item**
- Receives: `{quantity, description}`
- Creates new inventory record
- Returns: inventory item with ID

**2. Validate & Decrease for Order**
- Receives order: `{product_id, quantity}`
- Checks stock availability with write lock
- If sufficient: decrements quantity, returns success
- If insufficient: returns failure with message
- Returns: `{success: bool, message: str}`

#### Database: Inventory table
```
Inventory:
  - id (int, PK)
  - quantity (int)
  - description (str)
  - created_at
```

#### Architecture Pattern:
- Uses `select(...).with_for_update()` for pessimistic locking
- Prevents race conditions during concurrent order processing

---

### 5. **User Service**
**Responsibility**: User registration and authentication

#### Message Handlers:
- **Queue**: `user_register` (listens)

#### Operations:

**User Registration**
- Receives: `{username, email, password}`
- Validates: Email uniqueness
- Stores: User with bcrypt-hashed password
- Returns: `{success: bool, user_id?: int, error?: str}`

#### Database: Users table
```
User:
  - id (int, PK)
  - username (str)
  - email (str, unique)
  - password_hash (str)
  - created_at
```

---

### 6. **Notification Service**
**Status**: Placeholder (not yet configured)
**Future Purpose**: Email/SMS notifications for orders, user registration confirmations

---

## Data Flow Diagrams

### Complete Request Lifecycle: Create Order

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /main/orders
     │ {user_id, product_id, quantity}
     ▼
┌──────────────────────────────────────────┐
│        API Gateway (FastAPI)             │
│  - Validates input schema                │
│  - Generates correlation_id              │
│  - Creates callback queue                │
└────────┬─────────────────────────────────┘
         │
         │ RabbitMQ publish
         │ Queue: "order_created"
         │ correlation_id: UUID
         │ reply_to: callback_queue_XXX
         ▼
┌──────────────────────────────────────────┐
│      Order Service (Consumer)            │
│  1. Parse message                        │
│  2. Validate inventory availability      │
└────┬─────────────────────────────────────┘
     │
     │ RabbitMQ publish (RPC-style)
     │ Queue: "order_validate"
     ▼
┌──────────────────────────────────────────┐
│   Inventory Service (Consumer)           │
│  1. Check stock (with write lock)        │
│  2. Decrement quantity                   │
│  3. Return success/failure               │
└────┬─────────────────────────────────────┘
     │
     │ RabbitMQ publish response
     │ Queue: callback_queue_order_validate
     ▼
┌──────────────────────────────────────────┐
│      Order Service (Consumer)            │
│  1. Receive validation result            │
│  2. If valid: Insert into DB             │
│  3. Prepare response                     │
└────┬─────────────────────────────────────┘
     │
     │ RabbitMQ publish response
     │ Queue: callback_queue_XXX
     │ correlation_id matches original
     ▼
┌──────────────────────────────────────────┐
│        API Gateway (Listener)            │
│  1. Match correlation_id                 │
│  2. Stop consuming (response received)   │
│  3. Return to client                     │
└────┬─────────────────────────────────────┘
     │ HTTP 200 OK
     │ {order_id, success, created_at}
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

### Service Dependencies

```
┌─────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                   │
│          (Single shared database: ecommerce)            │
├──────────────┬──────────────┬──────────────┬────────────┤
│   Orders     │  Inventory   │    Users     │ Contracts  │
│   Table      │   Table      │   Table      │  (empty)   │
└──────────────┴──────────────┴──────────────┴────────────┘
       ▲              ▲              ▲
       │              │              │
       └──────────────┼──────────────┘
                      │
           (All services connect)

┌─────────────────────────────────────────────────────────┐
│                 RabbitMQ Message Broker                 │
├──────────────┬──────────────┬──────────────┬────────────┤
│order_created │inventory_new │user_register │order_      │
│              │_item         │              │validate    │
│ (producer:   │(producer:    │(producer:    │(producer:  │
│  API GW)     │  API GW)     │  API GW)     │  Order Svc)│
│ (consumer:   │(consumer:    │(consumer:    │(consumer:  │
│  Order Svc)  │  Inv Svc)    │  User Svc)   │  Inv Svc)  │
└──────────────┴──────────────┴──────────────┴────────────┘
       ▲              ▲              ▲              ▲
       │              │              │              │
       └──────────────┼──────────────┼──────────────┘
                      │              │
    ┌─────────────────┘              │
    │                                │
┌───────────────────┐    ┌───────────────────────┐
│   API Gateway     │    │  Background Services  │
│  (Synchronous)    │    │  (Asynchronous)       │
│                   │    │                       │
│ • REST Endpoints  │    │ ├─ Order Service     │
│ • Database checks │    │ ├─ Inventory Service│
│ • Pub/Sub wait    │    │ ├─ User Service     │
│   (RPC pattern)   │    │ └─ Notification Svc │
└───────────────────┘    └───────────────────────┘
```

---

## Message Queue Patterns

### 1. **Request-Reply Pattern (Fire and Wait)**

Used by API Gateway for synchronous operations.

```python
# API Gateway (producer)
def publish_and_wait_for_response(queue: str, message: dict) -> dict:
    1. Create temporary callback queue (auto-deleted, exclusive)
    2. Generate correlation_id (UUID)
    3. Publish message with:
       - routing_key = target service queue
       - reply_to = callback_queue
       - correlation_id = UUID
    4. Listen on callback queue (blocking)
    5. When response arrives (matching correlation_id):
       - Extract response body
       - Return to caller
```

### 2. **Fire-and-Forget Pattern**

Simple message publishing without waiting for response (for future use).

```python
def publish(queue: str, message: dict):
    1. Publish message
    2. Close connection
    3. No callback listening
```

### 3. **Consumer Pattern (Listener)**

All background services run consumers that:

```python
1. Connect to RabbitMQ
2. Bind to specific queue(s)
3. Register callback handler
4. Listen indefinitely
5. When message arrives:
   - Process in async function
   - If reply_to exists: send response back
   - Acknowledge message (auto_ack)
```

---

## Data Models & Database Schema

### Orders Table
```sql
CREATE TABLE order (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    status VARCHAR,
    created_at TIMESTAMP
);
```

### Inventory Table
```sql
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY,
    quantity INTEGER,
    description VARCHAR,
    created_at TIMESTAMP
);
```

### Users Table
```sql
CREATE TABLE "user" (
    id INTEGER PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    password_hash VARCHAR,
    created_at TIMESTAMP
);
```

---

## Communication Flows

### Scenario 1: Create Order (With Validation)

```
Timeline:
T0:  Client sends POST /main/orders
T1:  API Gateway receives request
T2:  API Gateway publishes to "order_created" queue
T3:  Order Service receives message
T4:  Order Service publishes validation to "order_validate"
T5:  Inventory Service receives validation request
T6:  Inventory Service checks stock + decrements
T7:  Inventory Service responds to callback queue
T8:  Order Service receives inventory response
T9:  Order Service inserts order into DB
T10: Order Service responds to API Gateway callback
T11: API Gateway receives response, stops consuming
T12: API Gateway returns HTTP 200 with order_id
```

### Scenario 2: Register User

```
Timeline:
T0:  Client sends POST /users/register
T1:  API Gateway receives request
T2:  API Gateway publishes to "user_register" queue
T3:  User Service receives message
T4:  User Service validates email uniqueness
T5:  User Service hashes password with bcrypt
T6:  User Service inserts into DB
T7:  User Service responds to callback queue
T8:  API Gateway receives response
T9:  API Gateway returns HTTP 200 with user_id
```

### Scenario 3: Add Inventory Item

```
Timeline:
T0:  Client sends POST /inventory/new
T1:  API Gateway receives request
T2:  API Gateway publishes to "inventory_new_item" queue
T3:  Inventory Service receives message
T4:  Inventory Service inserts new item into DB
T5:  Inventory Service responds to callback queue
T6:  API Gateway receives response
T7:  API Gateway returns HTTP 200 with item details
```

---

## Deployment Architecture

### Docker Compose Services

```
┌──────────────────────────────────────────────────────────┐
│           Docker Compose (docker-compose.yml)           │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────┐  ┌────────────────┐                │
│  │   postgres:16  │  │  pgadmin:4     │                │
│  │  Port 5432     │  │  Port 5050     │                │
│  │  (internal)    │  │  (mapped)      │                │
│  └────────────────┘  └────────────────┘                │
│                                                          │
│  ┌────────────────────────────────────┐                │
│  │    rabbitmq:3-management          │                │
│  │    Port 5672 (AMQP)               │                │
│  │    Port 15672 (Management)        │                │
│  └────────────────────────────────────┘                │
│                                                          │
│  ┌──────────┬──────────┬──────────┬──────────┐         │
│  │ API GW   │ Order    │Inventory │  User    │         │
│  │ 5000→8K  │ Service  │ Service  │ Service  │         │
│  │(FastAPI) │(Consumer)│(Consumer)│(Consumer)│         │
│  └──────────┴──────────┴──────────┴──────────┘         │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Key Patterns & Best Practices

### 1. **Request-Reply with Correlation IDs**
- Matches responses to requests in async systems
- UUID ensures uniqueness across instances
- Cleans up callback queues after response

### 2. **Write Locks (Pessimistic Locking)**
- Uses `.with_for_update()` in Inventory Service
- Prevents race conditions on stock updates
- Ensures atomicity across concurrent orders

### 3. **Durable Queues**
- All queues created with `durable=True`
- Messages persist if service crashes
- Ensures no message loss

### 4. **Async/Await with Threading**
- Services run async DB operations in event loops
- RabbitMQ consumers run in separate threads
- Thread-safe work with `asyncio.run_coroutine_threadsafe()`

### 5. **Health Checks**
- Each service waits for dependencies (database, RabbitMQ)
- Services start only when infrastructure is ready
- Retry logic with `RABBITMQ_CONNECTION_ATTEMPTS`

---

## What Connects to What

### Service → RabbitMQ Connections

| Service | Publishes To | Listens On | Pattern |
|---------|--------------|-----------|---------|
| API Gateway | order_created, inventory_new_item, user_register, order_validate | (callback queues) | RPC (wait for response) |
| Order Service | order_validate | order_created, (callback queues) | RPC (request to inventory) |
| Inventory Service | - | inventory_new_item, order_validate | Fire-and-forget with reply |
| User Service | - | user_register | Fire-and-forget with reply |

### Service → Database Connections

All services connect to the same PostgreSQL database:
- Order Service → orders table
- Inventory Service → inventory table
- User Service → users table

**Connection String**: `postgresql+asyncpg://postgres:postgres@database:5432/ecommerce`

---

## Request Flow Checklist

**Order Creation End-to-End:**
1. ✅ Client POSTs to `/main/orders` (API Gateway)
2. ✅ API Gateway validates input schema
3. ✅ API Gateway publishes to "order_created" queue
4. ✅ Order Service consumes message
5. ✅ Order Service publishes to "order_validate" queue
6. ✅ Inventory Service consumes validation request
7. ✅ Inventory Service checks stock (with write lock)
8. ✅ Inventory Service publishes response back
9. ✅ Order Service consumes response
10. ✅ Order Service saves order to DB
11. ✅ Order Service publishes response to callback queue
12. ✅ API Gateway consumes response (matching correlation_id)
13. ✅ API Gateway returns HTTP response to client

---

## Notes

- **Single Database**: All services share one PostgreSQL instance & database
- **Async Everything**: All DB operations are async (sqlmodel + asyncpg)
- **RabbitMQ is Critical**: System cannot function without it
- **No API-to-API Communication**: All inter-service communication goes through RabbitMQ
- **Sync Gateway + Async Services**: API Gateway provides synchronous interface to clients while services process asynchronously
