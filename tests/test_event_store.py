from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.event_store import EventStore


class TestEventStore:
    def test_event_store_table_exists(self, db_session: Session) -> None:
        """Verify events table was created properly"""
        result = db_session.execute(
            text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='events'
        """)
        )

        assert result.fetchone() is not None, "events table should exist"

    def test_append_single_event(self, db_session: Session) -> None:
        """Test inserting a single event into Event Store"""
        event_store = EventStore(db_session)

        event_id = uuid4()
        aggregate_id = uuid4()

        result = event_store.append_event(
            event_id=event_id,
            aggregate_type="Order",
            aggregate_id=aggregate_id,
            event_type="OrderCreated",
            version=1,
            payload={
                "user_id": 5,
                "product_id": 42,
                "quantity": 10,
            },
            metadata={
                "timestamp": "2026-04-18T10:30:00Z",
                "user_id": 5,
            },
        )
        assert result is not None
        assert result["event_id"] == str(event_id)
        assert result["aggregate_type"] == "Order"
        assert result["event_type"] == "OrderCreated"
        assert result["version"] == 1
        assert result["payload"]["product_id"] == 42

    def test_get_events_for_aggregate(self, db_session: Session) -> None:
        """Test querying events for specific aggregate"""
        event_store = EventStore(db_session)

        aggregate_id = uuid4()

        for i in range(1, 4):
            event_store.append_event(
                event_id=uuid4(),
                aggregate_type="Order",
                aggregate_id=aggregate_id,
                event_type=f"OrderEvent{i}",
                version=i,
                payload={"step": i},
            )

        events = event_store.get_events(
            aggregate_type="Order",
            aggregate_id=aggregate_id,
        )

        assert len(events) == 3
        assert events[0]["version"] == 1
        assert events[1]["version"] == 2
        assert events[2]["version"] == 3

    def test_event_immutability_duplicate_rejected(self, db_session: Session) -> None:
        """Verify events cannot be modified - duplicate ID rejected"""
        event_store = EventStore(db_session)

        event_id = uuid4()
        aggregate_id = uuid4()

        event_store.append_event(
            event_id=event_id,
            aggregate_type="Order",
            aggregate_id=aggregate_id,
            event_type="OrderCreated",
            version=1,
            payload={"user_id": 5},
        )

        with pytest.raises(ValueError, match="already exists"):
            event_store.append_event(
                event_id=event_id,  # Same ID!
                aggregate_type="Order",
                aggregate_id=aggregate_id,
                event_type="OrderModified",
                version=2,
                payload={"user_id": 6},
            )

    def test_optimistic_locking_duplicate_version_rejected(
        self, db_session: Session
    ) -> None:
        """Verify optimistic locking via version uniqueness"""
        event_store = EventStore(db_session)

        aggregate_id = uuid4()

        event_store.append_event(
            event_id=uuid4(),
            aggregate_type="Order",
            aggregate_id=aggregate_id,
            event_type="OrderCreated",
            version=1,
            payload={},
        )

        with pytest.raises(ValueError):
            event_store.append_event(
                event_id=uuid4(),  # Different ID
                aggregate_type="Order",
                aggregate_id=aggregate_id,
                event_type="OrderModified",
                version=1,  # Same version! - violates unique constraint
                payload={},
            )

    def test_event_payload_stored_as_json(self, db_session: Session) -> None:
        """Verify complex payloads stored and retrieved correctly"""
        event_store = EventStore(db_session)

        aggregate_id = uuid4()
        complex_payload = {
            "user_id": 5,
            "product_id": 42,
            "quantity": 10,
            "items": [
                {"sku": "A001", "name": "Item 1"},
                {"sku": "A002", "name": "Item 2"},
            ],
            "nested": {
                "deep": {
                    "value": "test",
                }
            },
        }

        event_store.append_event(
            event_id=uuid4(),
            aggregate_type="Order",
            aggregate_id=aggregate_id,
            event_type="OrderCreated",
            version=1,
            payload=complex_payload,
        )

        events = event_store.get_events("Order", aggregate_id)
        assert events[0]["payload"] == complex_payload
        assert events[0]["payload"]["nested"]["deep"]["value"] == "test"

    def test_get_events_by_type(self, db_session: Session) -> None:
        """Test querying events by event type"""
        event_store = EventStore(db_session)

        for _ in range(3):
            event_store.append_event(
                event_id=uuid4(),
                aggregate_type="Order",
                aggregate_id=uuid4(),
                event_type="OrderCreated",
                version=1,
                payload={},
            )

        for _ in range(2):
            event_store.append_event(
                event_id=uuid4(),
                aggregate_type="Order",
                aggregate_id=uuid4(),
                event_type="OrderCancelled",
                version=1,
                payload={},
            )

        created_events = event_store.get_events_by_type("OrderCreated")
        cancelled_events = event_store.get_events_by_type("OrderCancelled")

        assert len(created_events) == 3
        assert len(cancelled_events) == 2


class TestEventStoreSchema:
    """Test Event Store schema and constraints"""

    def test_events_table_has_required_columns(self, db_session: Session) -> None:
        """Verify events table has all required columns"""
        result = db_session.execute(
            text("""
            PRAGMA table_info(events)
        """)
        )

        columns = {row[1]: row[2] for row in result}

        required_columns = [
            "id",
            "event_id",
            "aggregate_type",
            "aggregate_id",
            "event_type",
            "version",
            "payload",
            "metadata",
            "created_at",
        ]

        for col in required_columns:
            assert col in columns, f"Column {col} should exist in events table"

    def test_snapshots_table_exists(self, db_session: Session) -> None:
        """Verify snapshots table created for performance optimization"""
        result = db_session.execute(
            text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='snapshots'
        """)
        )

        assert result.fetchone() is not None, "snapshots table should exist"

    def test_sagas_table_exists(self, db_session: Session) -> None:
        """Verify sagas table for distributed transactions"""
        result = db_session.execute(
            text("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='sagas'
        """)
        )

        assert result.fetchone() is not None, "sagas table should exist"
