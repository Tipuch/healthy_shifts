"""
Pytest configuration and fixtures for model testing.

This module provides:
- In-memory SQLite database setup for test isolation
- Async session fixtures for database operations
- Factory fixtures for creating test data
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator

import pytest
from sqlmodel import Session, SQLModel, create_engine

from models import (Member, MemberGroup, MemberRequest, MemberShiftScheduled,
                    Shift, ShiftConstraint, ShiftScheduled)


@pytest.fixture(scope="function")
def test_engine():
    """
    Create an in-memory SQLite engine for each test.

    Using scope="function" ensures each test gets a fresh database,
    providing complete isolation between tests.
    """
    from sqlalchemy import event

    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,  # Set to True to see SQL queries during debugging
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
async def session(test_engine) -> AsyncGenerator[Session, None]:
    """
    Provide a database session for each test.

    This fixture creates a new session for each test and ensures
    proper cleanup after the test completes.
    """
    with Session(test_engine) as session:
        yield session
        session.rollback()  # Rollback any uncommitted changes


# Factory Fixtures for Test Data


@pytest.fixture
def member_group_factory(session: Session):
    """
    Factory fixture for creating MemberGroup instances.

    Usage:
        member_group = member_group_factory(name="Engineering")
    """

    def _create_member_group(name: str = "Test Group", **kwargs) -> MemberGroup:
        member_group = MemberGroup(name=name, **kwargs)
        session.add(member_group)
        session.commit()
        session.refresh(member_group)
        return member_group

    return _create_member_group


@pytest.fixture
def member_factory(session: Session, member_group_factory):
    """
    Factory fixture for creating Member instances.

    Usage:
        member = member_factory(name="John Doe", email="john@example.com")
    """

    def _create_member(
        name: str = "Test Member",
        email: str | None = None,
        member_group_id: uuid.UUID | None = None,
        **kwargs,
    ) -> Member:
        # Auto-create a member group if not provided
        if member_group_id is None:
            group = member_group_factory(name=f"Group for {name}")
            member_group_id = group.id

        # Generate unique email if not provided
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"

        member = Member(
            name=name, email=email, member_group_id=member_group_id, **kwargs
        )
        session.add(member)
        session.commit()
        session.refresh(member)
        return member

    return _create_member


@pytest.fixture
def shift_factory(session: Session):
    """
    Factory fixture for creating Shift instances.

    Usage:
        shift = shift_factory(
            seconds_since_midnight=32400,  # 9:00 AM
            duration_seconds=28800,  # 8 hours
            days=["1", "2", "3"]  # Mon, Tue, Wed
        )
    """

    def _create_shift(
        seconds_since_midnight: int = 0,
        duration_seconds: int = 3600,
        days: list[str] | None = None,
        description: str = "",
        members_required: int = 1,
        **kwargs,
    ) -> Shift:
        if days is None:
            days = ["1"]  # Default to Monday

        shift = Shift(
            seconds_since_midnight=seconds_since_midnight,
            duration_seconds=duration_seconds,
            days=days,
            description=description,
            members_required=members_required,
            **kwargs,
        )
        session.add(shift)
        session.commit()
        session.refresh(shift)
        return shift

    return _create_shift


@pytest.fixture
def shift_scheduled_factory(session: Session, shift_factory):
    """
    Factory fixture for creating ShiftScheduled instances.

    Usage:
        scheduled = shift_scheduled_factory(
            start_at=datetime(2025, 1, 20, 9, 0),
            end_at=datetime(2025, 1, 20, 17, 0)
        )
    """

    def _create_shift_scheduled(
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        shift_id: uuid.UUID | None = None,
        description: str = "",
        **kwargs,
    ) -> ShiftScheduled:
        # Auto-create a shift if not provided
        if shift_id is None:
            shift = shift_factory()
            shift_id = shift.id

        # Default to today 9am-5pm if times not provided
        if start_at is None:
            start_at = datetime.now(timezone.utc).replace(
                hour=9, minute=0, second=0, microsecond=0
            )
        if end_at is None:
            end_at = start_at + timedelta(hours=8)

        shift_scheduled = ShiftScheduled(
            start_at=start_at,
            end_at=end_at,
            shift_id=shift_id,
            description=description,
            **kwargs,
        )
        session.add(shift_scheduled)
        session.commit()
        session.refresh(shift_scheduled)
        return shift_scheduled

    return _create_shift_scheduled


@pytest.fixture
def member_request_factory(session: Session, member_factory):
    """
    Factory fixture for creating MemberRequest instances.

    Usage:
        request = member_request_factory(
            start_at=datetime(2025, 1, 20, 9, 0),
            end_at=datetime(2025, 1, 21, 9, 0),
            description="Vacation"
        )
    """

    def _create_member_request(
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        member_id: uuid.UUID | None = None,
        description: str = "",
        **kwargs,
    ) -> MemberRequest:
        # Auto-create a member if not provided
        if member_id is None:
            member = member_factory()
            member_id = member.id

        # Default to tomorrow 9am-5pm if times not provided
        if start_at is None:
            start_at = datetime.now(timezone.utc).replace(
                hour=9, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        if end_at is None:
            end_at = start_at + timedelta(hours=8)

        member_request = MemberRequest(
            start_at=start_at,
            end_at=end_at,
            member_id=member_id,
            description=description,
            **kwargs,
        )
        session.add(member_request)
        session.commit()
        session.refresh(member_request)
        return member_request

    return _create_member_request


@pytest.fixture
def shift_constraint_factory(session: Session, shift_factory):
    """
    Factory fixture for creating ShiftConstraint instances.

    Usage:
        constraint = shift_constraint_factory(
            shift_id=shift1.id,
            linked_shift_id=shift2.id,
            within_last_shifts=2
        )
    """

    def _create_shift_constraint(
        shift_id: uuid.UUID | None = None,
        linked_shift_id: uuid.UUID | None = None,
        within_last_shifts: int = 1,
        **kwargs,
    ) -> ShiftConstraint:
        # Auto-create shifts if not provided
        if shift_id is None:
            shift1 = shift_factory(description="Primary Shift")
            shift_id = shift1.id

        if linked_shift_id is None:
            shift2 = shift_factory(description="Linked Shift")
            linked_shift_id = shift2.id

        constraint = ShiftConstraint(
            shift_id=shift_id,
            linked_shift_id=linked_shift_id,
            within_last_shifts=within_last_shifts,
            **kwargs,
        )
        session.add(constraint)
        session.commit()
        session.refresh(constraint)
        return constraint

    return _create_shift_constraint


@pytest.fixture
def member_shift_scheduled_factory(
    session: Session, member_factory, shift_scheduled_factory
):
    """
    Factory fixture for creating MemberShiftScheduled link instances.

    Usage:
        link = member_shift_scheduled_factory(
            member_id=member.id,
            shift_scheduled_id=scheduled_shift.id
        )
    """

    def _create_member_shift_scheduled(
        member_id: uuid.UUID | None = None,
        shift_scheduled_id: uuid.UUID | None = None,
        **kwargs,
    ) -> MemberShiftScheduled:
        # Auto-create member and shift if not provided
        if member_id is None:
            member = member_factory()
            member_id = member.id

        if shift_scheduled_id is None:
            scheduled = shift_scheduled_factory()
            shift_scheduled_id = scheduled.id

        link = MemberShiftScheduled(
            member_id=member_id, shift_scheduled_id=shift_scheduled_id, **kwargs
        )
        session.add(link)
        session.commit()
        session.refresh(link)
        return link

    return _create_member_shift_scheduled
