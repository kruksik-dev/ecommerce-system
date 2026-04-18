"""Event Store implementation - core of Event Sourcing"""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .models import EventModel


class EventStore:
    """
    Immutable event log for Event Sourcing.

    Stores domain events for all aggregates - allows:
    - Full audit trail
    - Event replay
    - Temporal queries
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def append_event(
        self,
        event_id: UUID,
        aggregate_type: str,
        aggregate_id: UUID,
        event_type: str,
        version: int,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Append event to Event Store (immutable).

        Args:
            event_id: Unikatowy identyfikator eventu
            aggregate_type: Typ agregatu (Order, Inventory, etc)
            aggregate_id: ID agregatu (order-123, product-456)
            event_type: Typ zdarzenia (OrderCreated, OrderRejected)
            version: Numer wersji agregatu (dla optimistic locking)
            payload: Dane eventu
            metadata: Metadata (userId, timestamp, etc)

        Returns:
            Event record as dict

        Raises:
            ValueError: Jeśli version już istnieje dla tego agregatu
        """
        try:
            # Use raw SQL for SQLite compatibility (handles AUTOINCREMENT properly)
            query = text("""
                INSERT INTO events (event_id, aggregate_type, aggregate_id, event_type, version, payload, metadata, created_at)
                VALUES (:event_id, :aggregate_type, :aggregate_id, :event_type, :version, :payload, :metadata, :created_at)
            """)

            self.db.execute(
                query,
                {
                    "event_id": str(event_id),
                    "aggregate_type": aggregate_type,
                    "aggregate_id": str(aggregate_id),
                    "event_type": event_type,
                    "version": version,
                    "payload": json.dumps(payload),
                    "metadata": json.dumps(metadata) if metadata else None,
                    "created_at": datetime.now().isoformat(),  # ISO format for SQLite compatibility (Python 3.12+)
                },
            )
            self.db.flush()

            # Retrieve the inserted event by event_id to get the auto-generated ID
            select_query = select(EventModel).where(
                EventModel.event_id == str(event_id)
            )
            event_record = self.db.execute(select_query).scalar_one()

            return {
                "id": event_record.id,
                "event_id": event_record.event_id,
                "aggregate_type": event_record.aggregate_type,
                "aggregate_id": event_record.aggregate_id,
                "event_type": event_record.event_type,
                "version": event_record.version,
                "payload": event_record.payload
                if isinstance(event_record.payload, dict)
                else json.loads(str(event_record.payload)),
                "metadata": event_record.event_metadata
                if isinstance(event_record.event_metadata, dict)
                else (
                    json.loads(str(event_record.event_metadata))
                    if event_record.event_metadata
                    else None
                ),
                "created_at": event_record.created_at,
            }

        except Exception as e:
            if (
                "duplicate key value" in str(e).lower()
                or "unique constraint failed" in str(e).lower()
            ):
                raise ValueError(f"Event with ID {event_id} already exists") from e
            raise

    def get_events(
        self,
        aggregate_type: str,
        aggregate_id: UUID,
        from_version: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Get all events for an aggregate.

        Args:
            aggregate_type: Typ agregatu
            aggregate_id: ID agregatu
            from_version: Pobierz eventy od tej wersji (dla snapshots)

        Returns:
            list of events in order
        """
        query = (
            select(EventModel)
            .where(
                (EventModel.aggregate_type == aggregate_type)
                & (EventModel.aggregate_id == str(aggregate_id))
                & (EventModel.version > from_version)
            )
            .order_by(EventModel.version.asc())
        )

        events_models = self.db.execute(query).scalars().all()

        events = []
        for event_model in events_models:
            events.append(
                {
                    "id": event_model.id,
                    "event_id": event_model.event_id,
                    "aggregate_type": event_model.aggregate_type,
                    "aggregate_id": event_model.aggregate_id,
                    "event_type": event_model.event_type,
                    "version": event_model.version,
                    "payload": event_model.payload
                    if isinstance(event_model.payload, dict)
                    else json.loads(str(event_model.payload)),
                    "metadata": event_model.event_metadata
                    if isinstance(event_model.event_metadata, dict)
                    else (
                        json.loads(str(event_model.event_metadata))
                        if event_model.event_metadata
                        else None
                    ),
                    "created_at": event_model.created_at,
                }
            )

        return events

    def get_events_by_type(self, event_type: str) -> list[dict[str, Any]]:
        """Get all events of a specific type"""
        query = (
            select(EventModel)
            .where(EventModel.event_type == event_type)
            .order_by(EventModel.created_at.asc())
        )

        events_models = self.db.execute(query).scalars().all()

        events = []
        for event_model in events_models:
            events.append(
                {
                    "id": event_model.id,
                    "event_id": event_model.event_id,
                    "aggregate_type": event_model.aggregate_type,
                    "aggregate_id": event_model.aggregate_id,
                    "event_type": event_model.event_type,
                    "version": event_model.version,
                    "payload": event_model.payload
                    if isinstance(event_model.payload, dict)
                    else json.loads(str(event_model.payload)),
                    "metadata": event_model.event_metadata
                    if isinstance(event_model.event_metadata, dict)
                    else (
                        json.loads(str(event_model.event_metadata))
                        if event_model.event_metadata
                        else None
                    ),
                    "created_at": event_model.created_at,
                }
            )

        return events
