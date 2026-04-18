# Event-Driven Design (EDD) - Plan Refaktoryzacji

## Executive Summary

Obecna implementacja działa poprawnie, ale jest oparta na **Request-Reply Pattern (synchroniczne RPC)** zamiast na prawdziwym podejściu **Event-Driven Design**. Plan opisuje kroki przemiany z architektury hybrydowej na pełnie event-driven z event sourcing.

---

## 1. Główne Problemy w Obecnej Implementacji

### 1.1 Anti-Pattern: Request-Reply (Synchroniczne RPC)
**Problem**:
- API Gateway blokuje się czekając na odpowiedź od Order Service
- Order Service blokuje się czekając na odpowiedź od Inventory Service
- Tworzy to ścisłe powiązanie między serwisami (tight coupling)
- Utraty korzyści asynchroniczności i skalowalności

**Obecny flow**:
```
Client → [czeka] → API Gateway → [czeka] → Order Service → [czeka] → Inventory Service
```

### 1.2 Brak Event Sourcing
**Problem**:
- Brak audytu zmian (audit trail)
- Niemożliwość odtworzenia historii stanu agregatu
- Niemożliwość debugowania problemów
- Utraty zdolności do temporal queries

**Obecny stan**: Dane tylko w tabelach, bez historii zdarzeń

### 1.3 Słaby Model Domenowy
**Problem**:
- Foldery `domain/` i `application/` są puste
- Business logic miesza się z message handling
- Brak separacji concerns (Domain Layer, Application Layer, Infrastructure Layer)
- Brak agregacji, value objects, domain events

### 1.4 Brak Saga Pattern dla Transakcji Rozproszonych
**Problem**:
- Order creation to transakcja rozproszona (Order Service + Inventory Service)
- Brak mechanizmu do obsługi failover i kompensacji
- Jeśli Order Service pada po otrzymaniu sukcesu od Inventory, inventory jest zmniejszone ale order nie został zapisany

### 1.5 Synchroniczny API Gateway
**Problem**:
- `publish_and_wait_for_response()` blokuje HTTP request
- HTTP timeout może być zbyt krótki dla skoncentrowanych operacji
- Utraty korzyści z async/await

### 1.6 Brak Dedykowanego Event Store
**Problem**:
- Zdarzenia nie są trwale przechowywane
- Niemożliwość replay zdarzeń
- Niemożliwość integracji nowych konsumentów

---

## 2. Docelowa Architektura Event-Driven

### 2.1 Nowy Flow Asynchroniczny

```
Client
  ↓ (HTTP 202 Accepted)
API Gateway
  ├─ Publikuje: OrderCreationRequested
  └─ Zwraca: { requestId, status: "processing" }
  ↓
EventStore (persystencja)
  ├─ OrderCreationRequested
  └─ [Webhook/Polling] GET /order-creation-status/{requestId}
  ↓
Order Service (Event Consumer & Producer)
  ├─ Subskrybuje: OrderCreationRequested
  ├─ Publikuje: OrderCreationValidationRequested
  ↓
Inventory Service (Event Consumer & Producer)
  ├─ Subskrybuje: OrderCreationValidationRequested
  ├─ Check inventory
  ├─ Publikuje: InventoryReserved lub InventoryNotAvailable
  ↓
Order Service (kontynuacja)
  ├─ Subskrybuje: InventoryReserved lub InventoryNotAvailable
  ├─ Publikuje: OrderCreated lub OrderCreationFailed
  ├─ Persistuje order w DB
  ↓
Notification Service
  ├─ Subskrybuje: OrderCreated, OrderCreationFailed
  ├─ Wyświetla powiadomienia
```

### 2.2 Komponenty Architektury

```
┌─────────────────────────────────────────┐
│      Event Store (PostgreSQL)           │
│  ┌───────────────────────────────────┐  │
│  │ events table                      │  │
│  │ (eventId, aggregate_id,           │  │
│  │  event_type, payload, timestamp)  │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
              ↑
              │ (Publish/Subscribe)
┌─────────────────────────────────────────┐
│      RabbitMQ Event Bus                  │
│  (domain events jako wiadomości)        │
└─────────────────────────────────────────┘
              ↑↓
    ┌─────────┼──────────┐
    │         │          │
Order Service │    Inventory Service
              │
       Notification Service
```

---

## 3. Etapy Refaktoryzacji

### Etap 1: Przygotowanie Infrastruktury Event Store

#### 1.1 Event Store Table
```sql
CREATE TABLE events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    aggregate_type VARCHAR(100) NOT NULL,  -- "Order", "Inventory"
    aggregate_id UUID NOT NULL,             -- order_id, product_id
    event_type VARCHAR(100) NOT NULL,       -- "OrderCreationRequested", "InventoryReserved"
    version INT NOT NULL,                   -- Version for optimistic locking
    payload JSONB NOT NULL,                 -- Event data
    metadata JSONB,                         -- timestamp, userId, correlation_id
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT events_aggregate_uq UNIQUE(aggregate_type, aggregate_id, version)
);

CREATE INDEX idx_events_aggregate ON events(aggregate_type, aggregate_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(created_at);
```

#### 1.2 Snapshot Table (dla optymalizacji)
```sql
CREATE TABLE snapshots (
    id BIGSERIAL PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    aggregate_state JSONB NOT NULL,
    version INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT snapshots_aggregate_uq UNIQUE(aggregate_type, aggregate_id)
);
```

#### 1.3 Saga State Table
```sql
CREATE TABLE sagas (
    id BIGSERIAL PRIMARY KEY,
    saga_id UUID NOT NULL UNIQUE,
    saga_type VARCHAR(100) NOT NULL,  -- "OrderCreationSaga"
    state JSONB NOT NULL,              -- Current state (started, pending_inventory, completed, compensating)
    compensation_actions JSONB,        -- Actions to perform if rollback
    correlation_id UUID,               -- Link do original request
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

### Etap 2: Implementacja Domain Layer (Order Service)

#### 2.1 Domain Events
```
📁 order_services/app/domain/
├── events.py
│   ├── OrderCreationRequested
│   ├── OrderCreationValidationRequested
│   ├── InventoryReserved
│   ├── InventoryNotAvailable
│   ├── OrderCreated
│   ├── OrderCreationFailed
│   └── OrderCompensated
├── aggregates.py
│   ├── Order (Aggregate Root)
│   │   ├── apply_event(event)
│   │   ├── reserve_inventory()
│   │   ├── confirm_order()
│   │   └── compensate()
│   └── OrderId (Value Object)
└── repositories.py
    └── OrderRepository
        ├── save(order) - saves events, nie state
        └── get_by_id(order_id) - reconstruct from events
```

#### 2.2 Order Aggregate Root (Domain Model)

```python
# order_services/app/domain/aggregates.py

from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

class OrderStatus(str, Enum):
    CREATED = "created"
    PENDING_VALIDATION = "pending_validation"
    VALIDATION_ACCEPTED = "validation_accepted"
    COMPLETED = "completed"
    COMPENSATED = "compensated"
    FAILED = "failed"

class Order:
    """Aggregate Root - zawiera business logic"""

    def __init__(self, order_id: UUID, user_id: int, product_id: int, quantity: int):
        self.order_id = order_id
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.status = OrderStatus.CREATED
        self.version = 0
        self.uncommitted_events: List = []

    def create(self):
        """Inicia order creation process"""
        event = OrderCreationRequested(
            order_id=self.order_id,
            user_id=self.user_id,
            product_id=self.product_id,
            quantity=self.quantity,
            created_at=datetime.now()
        )
        self._record_event(event)
        return event

    def request_inventory_validation(self):
        """Request inventory validation"""
        event = OrderCreationValidationRequested(
            order_id=self.order_id,
            product_id=self.product_id,
            quantity=self.quantity,
            created_at=datetime.now()
        )
        self._record_event(event)
        self.status = OrderStatus.PENDING_VALIDATION
        return event

    def confirm_inventory(self):
        """Apply successful inventory check"""
        event = OrderConfirmed(
            order_id=self.order_id,
            created_at=datetime.now()
        )
        self._record_event(event)
        self.status = OrderStatus.COMPLETED
        return event

    def reject_order(self, reason: str):
        """Reject order due to failed inventory"""
        event = OrderRejected(
            order_id=self.order_id,
            reason=reason,
            created_at=datetime.now()
        )
        self._record_event(event)
        self.status = OrderStatus.FAILED
        return event

    def _record_event(self, event):
        """Record event for Event Store"""
        self.uncommitted_events.append(event)
        self.version += 1

    def apply_event(self, event):
        """Reconstruct state from event"""
        if isinstance(event, OrderCreationRequested):
            self.status = OrderStatus.CREATED
        elif isinstance(event, OrderCreationValidationRequested):
            self.status = OrderStatus.PENDING_VALIDATION
        elif isinstance(event, OrderConfirmed):
            self.status = OrderStatus.COMPLETED
        elif isinstance(event, OrderRejected):
            self.status = OrderStatus.FAILED
        self.version += 1
```

---

### Etap 3: Application Layer (Use Cases)

#### 3.1 Use Case: CreateOrder
```
📁 order_services/app/application/
├── use_cases/
│   ├── create_order_use_case.py
│   └── confirm_order_use_case.py
└── dto/
    ├── create_order_request.py
    └── create_order_response.py
```

```python
# order_services/app/application/use_cases/create_order_use_case.py

class CreateOrderUseCase:
    def __init__(self, order_repository, event_publisher):
        self.order_repository = order_repository
        self.event_publisher = event_publisher

    def execute(self, user_id: int, product_id: int, quantity: int) -> str:
        """
        Zwraca request_id (UUID), nie pełną odpowiedź
        Asynchroniczna obsługa w event handlers
        """
        order_id = generate_uuid()
        order = Order(order_id, user_id, product_id, quantity)

        # Create domain event
        event = order.create()

        # Save to Event Store
        self.order_repository.save(order)

        # Publish to Event Bus
        self.event_publisher.publish(event)

        return str(order_id)
```

---

### Etap 4: Event Handlers (Choreography)

#### 4.1 Order Service Event Handlers

```python
# order_services/app/consumer/event_handlers.py

class OrderEventHandlers:

    @event_handler("OrderCreationRequested")
    async def on_order_creation_requested(self, event: OrderCreationRequested):
        """Otrzymał request do utworzenia order"""
        order = self.order_repository.get_by_id(event.order_id)

        # Trigger validation
        validation_event = order.request_inventory_validation()

        # Publish event
        await self.event_publisher.publish(validation_event)

    @event_handler("InventoryReserved")
    async def on_inventory_reserved(self, event: InventoryReserved):
        """Inventory zarezerwowany pomyślnie"""
        order = self.order_repository.get_by_id(event.order_id)

        # Mark order as completed
        confirm_event = order.confirm_inventory()
        self.order_repository.save(order)

        # Publish OrderCreated event
        await self.event_publisher.publish(OrderCreated(
            order_id=order.order_id,
            user_id=order.user_id,
            product_id=order.product_id,
            quantity=order.quantity,
            created_at=datetime.now()
        ))

    @event_handler("InventoryNotAvailable")
    async def on_inventory_not_available(self, event: InventoryNotAvailable):
        """Inventory nie dostępny"""
        order = self.order_repository.get_by_id(event.order_id)

        # Reject order
        reject_event = order.reject_order("Insufficient inventory")
        self.order_repository.save(order)

        # Publish OrderCreationFailed
        await self.event_publisher.publish(OrderCreationFailed(
            order_id=order.order_id,
            reason="Insufficient inventory",
            created_at=datetime.now()
        ))
```

#### 4.2 Inventory Service Event Handlers

```python
# inventory_services/app/consumer/event_handlers.py

class InventoryEventHandlers:

    @event_handler("OrderCreationValidationRequested")
    async def on_order_validation_requested(self, event: OrderCreationValidationRequested):
        """Order Service prosi o rezerwację inventory"""
        async with async_session() as session:
            result = await session.execute(
                select(Inventory)
                .where(Inventory.id == event.product_id)
                .with_for_update()
            )
            inventory = result.scalar_one_or_none()

            if not inventory or inventory.quantity < event.quantity:
                # Publish failure event
                await self.event_publisher.publish(InventoryNotAvailable(
                    order_id=event.order_id,
                    product_id=event.product_id,
                    reason="Insufficient stock",
                    created_at=datetime.now()
                ))
            else:
                # Reserve inventory
                inventory.quantity -= event.quantity
                session.add(inventory)
                await session.commit()

                # Publish success event
                await self.event_publisher.publish(InventoryReserved(
                    order_id=event.order_id,
                    product_id=event.product_id,
                    quantity_reserved=event.quantity,
                    created_at=datetime.now()
                ))
```

---

### Etap 5: Saga Pattern dla Kompensacji

#### 5.1 OrderCreationSaga

```
Problem: Co jeśli Order Service pada po otrzymaniu InventoryReserved
ale przed zapisaniem order do DB?

Solution: Saga State + Compensation Events
```

```python
# order_services/app/application/sagas/order_creation_saga.py

class OrderCreationSaga:
    """
    Orchestrator (alternatywa do choreography)
    Tracks saga state i triggeruje kompensacje
    """

    def __init__(self, event_store, event_publisher):
        self.event_store = event_store
        self.event_publisher = event_publisher

    async def start(self, command: CreateOrderCommand):
        """Initiate saga"""
        saga_id = generate_uuid()

        # Save saga state
        await self.event_store.save_saga_state(
            saga_id=saga_id,
            state="STARTED",
            data={
                "order_id": command.order_id,
                "product_id": command.product_id,
                "quantity": command.quantity
            }
        )

        # Publish first event
        await self.event_publisher.publish(
            OrderCreationValidationRequested(
                order_id=command.order_id,
                product_id=command.product_id,
                quantity=command.quantity,
                saga_id=saga_id
            )
        )

    async def on_inventory_reserved(self, event: InventoryReserved):
        """Inventory zarezerwowany"""
        # Update saga state
        await self.event_store.update_saga_state(
            saga_id=event.saga_id,
            state="INVENTORY_RESERVED",
            compensation=[
                {
                    "action": "release_inventory",
                    "params": {"product_id": event.product_id, "quantity": event.quantity_reserved}
                }
            ]
        )

    async def on_inventory_not_available(self, event: InventoryNotAvailable):
        """Inventory nie dostępny - end saga"""
        await self.event_store.update_saga_state(
            saga_id=event.saga_id,
            state="FAILED"
        )

        await self.event_publisher.publish(
            OrderCreationFailed(
                order_id=event.order_id,
                reason=event.reason,
                saga_id=event.saga_id
            )
        )

    async def compensate(self, saga_id: UUID):
        """Execute compensation logic"""
        saga = await self.event_store.get_saga(saga_id)

        for compensation_action in saga.compensation_actions:
            if compensation_action["action"] == "release_inventory":
                await self.event_publisher.publish(
                    InventoryReleased(
                        product_id=compensation_action["params"]["product_id"],
                        quantity=compensation_action["params"]["quantity"]
                    )
                )
```

---

### Etap 6: Asynchroniczny API Gateway

#### 6.1 Nowe Endpoints
```
POST /orders                          → HTTP 202 + requestId (zamiast 200/400)
GET /orders/{requestId}/status        → Polling statusu
GET /orders/{orderId}                 → Get created order (eventual consistency)
```

```python
# api_gateway/app/main.py

@main_router.post("/orders", status_code=202)
async def create_order(order: OrderRequest):
    """
    Asynchronous order creation - zwraca request ID
    Client polls POST /orders/{request_id}/status
    """
    request_id = str(uuid4())

    # Save request to Redis (cache)
    await request_cache.set(
        f"order_request:{request_id}",
        {
            "status": "processing",
            "created_at": datetime.now().isoformat()
        },
        ttl=3600  # 1 hour
    )

    # Publish event (don't wait for response)
    await event_publisher.publish(OrderCreationRequested(
        request_id=request_id,
        user_id=order.user_id,
        product_id=order.product_id,
        quantity=order.quantity
    ))

    return {
        "request_id": request_id,
        "status": "processing",
        "status_url": f"/orders/{request_id}/status",
        "message": "Order creation in progress"
    }


@main_router.get("/orders/{request_id}/status")
async def get_order_status(request_id: str):
    """
    Poll order creation status
    """
    request = await request_cache.get(f"order_request:{request_id}")

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    return {
        "request_id": request_id,
        "status": request["status"],  # "processing", "completed", "failed"
        "order_id": request.get("order_id"),
        "error": request.get("error")
    }
```

---

### Etap 7: Event Store Repository

#### 7.1 OrderRepository
```python
# order_services/app/infrastructure/repositories/order_repository.py

class OrderRepository:
    """
    Implementuje Event Sourcing pattern
    Persystuje events, nie state
    """

    def __init__(self, event_store):
        self.event_store = event_store

    async def save(self, order: Order):
        """
        Persystuje niepotwierdzne eventy z agregatu do Event Store
        """
        for event in order.uncommitted_events:
            await self.event_store.append(
                aggregate_id=order.order_id,
                aggregate_type="Order",
                event_type=event.__class__.__name__,
                version=order.version,
                payload=event.to_dict(),
                metadata={
                    "timestamp": datetime.now().isoformat(),
                    "correlation_id": event.correlation_id
                }
            )

        # Clear uncommitted events
        order.uncommitted_events = []

    async def get_by_id(self, order_id: UUID) -> Optional[Order]:
        """
        Rekonstruuje Order agregat z Event Store
        Odczytuje wszystkie eventy dla order_id i aplikuje je
        """
        # Sprawdź snapshot first (dla optymalizacji)
        snapshot = await self.event_store.get_snapshot(order_id)

        if snapshot:
            order = Order.from_snapshot(snapshot)
            version_from = snapshot["version"]
        else:
            version_from = 0
            order = None

        # Get events from snapshot version or beginning
        events = await self.event_store.get_events(
            aggregate_id=order_id,
            from_version=version_from
        )

        if not events and not snapshot:
            return None

        # If no snapshot, create new order from first event
        if not snapshot:
            first_event = events[0]
            order = Order(
                order_id=order_id,
                user_id=first_event["payload"]["user_id"],
                product_id=first_event["payload"]["product_id"],
                quantity=first_event["payload"]["quantity"]
            )

        # Apply all events
        for event_record in events:
            event = DomainEventFactory.create(event_record)
            order.apply_event(event)

        return order
```

---

### Etap 8: Event Publishing Infrastructure

#### 8.1 EventPublisher
```python
# shared/infrastructure/event_publisher.py

class RabbitMQEventPublisher:
    """
    Publikuje domain events na RabbitMQ
    """

    async def publish(self, event: DomainEvent):
        """
        1. Publikuje na wiele routing keys (event type + aggregate type)
        2. Używa dead letter queues dla failover
        3. Implementuje retry policy
        """
        routing_key = f"domain.{event.__class__.__name__}"

        message = {
            "event_id": str(uuid4()),
            "event_type": event.__class__.__name__,
            "aggregate_id": event.aggregate_id,
            "aggregate_type": event.aggregate_type,
            "payload": event.to_dict(),
            "timestamp": datetime.now().isoformat()
        }

        channel.basic_publish(
            exchange="domain_events",
            routing_key=routing_key,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                correlation_id=str(uuid4())
            )
        )
```

---

## 4. Plan Implementacji (Timeline)

| Etap | Komponenta | Czas | Zależności |
|------|-----------|------|-----------|
| 1 | Event Store Tables | 1 dzień | - |
| 2 | Domain Layer (Order) | 2 dni | Etap 1 |
| 3 | Application Layer (Use Cases) | 1.5 dnia | Etap 2 |
| 4 | Event Handlers (Order Service) | 1 dzień | Etap 3 |
| 5 | Event Handlers (Inventory Service) | 1 dzień | Etap 3 |
| 6 | Saga Pattern | 1.5 dnia | Etap 4-5 |
| 7 | OrderRepository (Event Sourcing) | 1.5 dnia | Etap 1-2 |
| 8 | Asynchroniczny API Gateway | 1 dzień | Etap 6 |
| 9 | Event Publishing Infrastructure | 1 dzień | Etap 7 |
| 10 | Integracyjne testy | 1 dzień | Wszystkie |
| 11 | Migration starych danych (opcjonalnie) | 0.5 dnia | Wszystkie |

**Całkowity czas**: ~13 dni (1 sprint)

---

## 5. Kroki Migracyjne (Zero Downtime)

### 5.1 Faza 1: Dual Write (2 dni)
```
┌─ Nowy System (Event Store + Event Bus)
│  ├─ Tworzy eventy
│  └─ Persystuje w Event Store
├─ Stary System
│  └─ Persystuje w Orders table
└─ Synchronizacja
   └─ Event adapter converts State → Events
```

### 5.2 Faza 2: Gradual Propagation (3 dni)
```
50% traffic → Nowy system
50% traffic → Stary system

Monitorowanie synchronizacji, retry logic
```

### 5.3 Faza 3: Full Cutover (1 dzień)
```
100% traffic → Nowy system
Stary system → Archive
```

---

## 6. Benefits po Refaktoryzacji

| Aspekt | Przed | Po |
|--------|------|-----|
| **Coupling** | Tight (RPC) | Loose (Event-based) |
| **Scalability** | Limited (sync waits) | High (async) |
| **Auditability** | Brak historii | Pełna historia (Event Store) |
| **Debugging** | Trudne (deadlocks) | Łatwe (replay events) |
| **Eventual Consistency** | N/A | Wbudowana |
| **Fault Tolerance** | Brak kompensacji | Saga compensations |
| **CQRS** | Nie możliwy | Możliwy (read model) |
| **New Subscribers** | Wymagany redeploy | Tylko nowy subscriber |

---

## 7. Checklist Implementacji

### Pre-Implementation
- [ ] Code review z zespołem
- [ ] Setup Event Store schema (PostgreSQL migrations)
- [ ] Dokumentacja dla developerów

### implementation
- [ ] Etap 1-3: Domain & Application layers
- [ ] Etap 4-5: Event handlers
- [ ] Etap 6-7: Repository pattern
- [ ] Etap 8-9: Infrastructure
- [ ] Etap 10: Integration tests
- [ ] Performance testing

### Post-Implementation
- [ ] Monitoring Event Store queries
- [ ] Alert na du duży lag między eventem a konsumentem
- [ ] Archiwizacja starych zdarzeń (retention policy)
- [ ] Dokumentacja operational runbooks
- [ ] Training dla team-u

---

## 8. Potential Pitfalls & Solutions

### Pitfall 1: Event Versioning
**Problem**: Schema zmienia się, stare eventy są niekompatybilne

**Solution**:
```python
class EventUpgrader:
    def upgrade(self, event_record):
        if event_record["version"] == 1:
            # Migrate to v2 schema
            event_record["payload"]["new_field"] = default_value
        return event_record
```

### Pitfall 2: Event Store Performance
**Problem**: Wiele queryów do Event Store przy rekonstrukcji agregatu

**Solution**:
- Snapshots co N eventów
- Indexowanie na (aggregate_id, version)
- Eventual consistency readers

### Pitfall 3: Distributed Saga Failures
**Problem**: Order Service pada w środku compensacji

**Solution**:
- Saga state stored w Event Store
- Outbox pattern (ensure event published before saga completes)
- Periodic compensation sweeper

### Pitfall 4: Race Conditions
**Problem**: Dwa requesty jednocześnie dla tego samego order ID

**Solution**:
```python
await event_store.append(
    aggregate_id=order_id,
    version=expected_version + 1,  # Optimistic locking
    event=event
)
# If version mismatch, retry or fail
```

---

## 9. Useful Resources

- **Event Sourcing**: Greg Young - "Event Sourcing" (https://www.youtube.com/watch?v=8JKjvY4etfs)
- **CQRS**: Martin Fowler - CQRS (https://martinfowler.com/bliki/CQRS.html)
- **Saga Pattern**: Chris Richardson - Saga Pattern (https://microservices.io/patterns/data/saga.html)
- **Domain-Driven Design**: Eric Evans - DDD Book

---

## 10. Next Steps

1. **Sprint Planning**: Assign team members do każdego etapu
2. **Set up Development Database**: Event Store schema
3. **Create Spike**: POC dla Domain Layer + Event Sourcing
4. **Review & Approve**: Plan z team lead i architect
