"""
Tests for ShiftScheduled model CRUD operations and relationships.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from models import MemberShiftScheduled, ShiftScheduled


class TestShiftScheduledCRUD:
    """Test suite for ShiftScheduled Create, Read, Update, Delete operations."""

    def test_create_shift_scheduled(self, session: Session, shift_factory):
        """Test creating a new scheduled shift."""
        # Arrange
        shift = shift_factory(description="Template Shift")
        start = datetime(2025, 1, 20, 9, 0)
        end = datetime(2025, 1, 20, 17, 0)

        # Act
        scheduled = ShiftScheduled(
            start_at=start,
            end_at=end,
            shift_id=shift.id,
            description="Scheduled instance"
        )
        session.add(scheduled)
        session.commit()
        session.refresh(scheduled)

        # Assert
        assert scheduled.id is not None
        assert isinstance(scheduled.id, uuid.UUID)
        assert scheduled.start_at == start
        assert scheduled.end_at == end
        assert scheduled.shift_id == shift.id
        assert scheduled.description == "Scheduled instance"
        assert isinstance(scheduled.created_at, datetime)
        assert isinstance(scheduled.updated_at, datetime)

    def test_create_shift_scheduled_with_factory(self, shift_scheduled_factory):
        """Test creating a scheduled shift using the factory fixture."""
        # Act
        start = datetime(2025, 2, 15, 8, 0)
        end = datetime(2025, 2, 15, 16, 0)
        scheduled = shift_scheduled_factory(
            start_at=start,
            end_at=end,
            description="Factory created"
        )

        # Assert
        assert scheduled.id is not None
        assert scheduled.start_at == start
        assert scheduled.end_at == end
        assert scheduled.shift_id is not None
        assert scheduled.description == "Factory created"

    def test_read_shift_scheduled(self, session: Session, shift_scheduled_factory):
        """Test reading a scheduled shift from the database."""
        # Arrange
        created = shift_scheduled_factory(description="Test scheduled shift")

        # Act
        statement = select(ShiftScheduled).where(ShiftScheduled.id == created.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.id == created.id
        assert result.start_at == created.start_at
        assert result.end_at == created.end_at
        assert result.shift_id == created.shift_id

    def test_read_all_shift_scheduled(self, session: Session, shift_scheduled_factory):
        """Test reading multiple scheduled shifts."""
        # Arrange
        shift_scheduled_factory(description="Shift 1")
        shift_scheduled_factory(description="Shift 2")
        shift_scheduled_factory(description="Shift 3")

        # Act
        statement = select(ShiftScheduled)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        descriptions = {s.description for s in results}
        assert descriptions == {"Shift 1", "Shift 2", "Shift 3"}

    def test_update_shift_scheduled(self, session: Session, shift_scheduled_factory):
        """Test updating a scheduled shift's information."""
        # Arrange
        scheduled = shift_scheduled_factory(description="Original")
        original_id = scheduled.id
        new_start = scheduled.start_at + timedelta(hours=1)
        new_end = scheduled.end_at + timedelta(hours=1)

        # Act
        scheduled.start_at = new_start
        scheduled.end_at = new_end
        scheduled.description = "Updated"
        session.add(scheduled)
        session.commit()
        session.refresh(scheduled)

        # Assert
        assert scheduled.id == original_id
        assert scheduled.start_at == new_start
        assert scheduled.end_at == new_end
        assert scheduled.description == "Updated"

    def test_delete_shift_scheduled(self, session: Session, shift_scheduled_factory):
        """Test deleting a scheduled shift."""
        # Arrange
        scheduled = shift_scheduled_factory(description="To delete")
        scheduled_id = scheduled.id

        # Act
        session.delete(scheduled)
        session.commit()

        # Assert
        statement = select(ShiftScheduled).where(ShiftScheduled.id == scheduled_id)
        result = session.exec(statement).first()
        assert result is None


class TestShiftScheduledRelationships:
    """Test suite for ShiftScheduled relationships."""

    def test_shift_scheduled_belongs_to_shift(self, session: Session, shift_factory, shift_scheduled_factory):
        """Test that a scheduled shift is linked to a shift template."""
        # Arrange
        shift_template = shift_factory(description="Template")
        scheduled = shift_scheduled_factory(
            shift_id=shift_template.id,
            description="Instance"
        )

        # Act
        statement = select(ShiftScheduled).where(ShiftScheduled.id == scheduled.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.shift_id == shift_template.id


class TestShiftScheduledMemberAssignment:
    """Test suite for member assignment to scheduled shifts."""

    def test_assign_member_to_scheduled_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test assigning a member to a scheduled shift."""
        # Arrange
        member = member_factory(name="John Doe", email="john@example.com")
        scheduled = shift_scheduled_factory(description="Morning Shift")

        # Act
        link = MemberShiftScheduled(
            member_id=member.id,
            shift_scheduled_id=scheduled.id
        )
        session.add(link)
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.shift_scheduled_id == scheduled.id
        )
        results = session.exec(statement).all()
        assert len(results) == 1
        assert results[0].member_id == member.id

    def test_assign_multiple_members_to_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test assigning multiple members to the same scheduled shift."""
        # Arrange
        member1 = member_factory(name="Member 1", email="m1@example.com")
        member2 = member_factory(name="Member 2", email="m2@example.com")
        member3 = member_factory(name="Member 3", email="m3@example.com")
        scheduled = shift_scheduled_factory(description="Team Shift")

        # Act
        session.add(MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=scheduled.id))
        session.add(MemberShiftScheduled(member_id=member2.id, shift_scheduled_id=scheduled.id))
        session.add(MemberShiftScheduled(member_id=member3.id, shift_scheduled_id=scheduled.id))
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.shift_scheduled_id == scheduled.id
        )
        results = session.exec(statement).all()
        assert len(results) == 3
        assigned_member_ids = {link.member_id for link in results}
        assert assigned_member_ids == {member1.id, member2.id, member3.id}

    def test_member_assigned_to_multiple_shifts(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test that a member can be assigned to multiple scheduled shifts."""
        # Arrange
        member = member_factory(name="Busy Person", email="busy@example.com")
        shift1 = shift_scheduled_factory(description="Morning")
        shift2 = shift_scheduled_factory(description="Afternoon")
        shift3 = shift_scheduled_factory(description="Evening")

        # Act
        session.add(MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift1.id))
        session.add(MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift2.id))
        session.add(MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift3.id))
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member.id
        )
        results = session.exec(statement).all()
        assert len(results) == 3

    def test_unassign_member_from_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test removing a member assignment from a scheduled shift."""
        # Arrange
        member = member_factory(name="Temp Worker", email="temp@example.com")
        scheduled = shift_scheduled_factory(description="Temporary Assignment")
        link = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=scheduled.id)
        session.add(link)
        session.commit()

        # Act
        session.delete(link)
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member.id,
            MemberShiftScheduled.shift_scheduled_id == scheduled.id
        )
        result = session.exec(statement).first()
        assert result is None


class TestShiftScheduledConstraints:
    """Test suite for ShiftScheduled validation and constraints."""

    def test_shift_scheduled_requires_start_at(self, session: Session, shift_factory):
        """Test that a scheduled shift requires a start time."""
        shift = shift_factory()
        end = datetime.now(timezone.utc) + timedelta(hours=8)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(ShiftScheduled(end_at=end, shift_id=shift.id))
            session.commit()

    def test_shift_scheduled_requires_end_at(self, session: Session, shift_factory):
        """Test that a scheduled shift requires an end time."""
        shift = shift_factory()
        start = datetime.now(timezone.utc)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(ShiftScheduled(start_at=start, shift_id=shift.id))
            session.commit()

    def test_shift_scheduled_requires_shift_id(self, session: Session):
        """Test that a scheduled shift requires a shift_id."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=8)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(ShiftScheduled(start_at=start, end_at=end))
            session.commit()

    def test_shift_scheduled_foreign_key_constraint(self, session: Session):
        """Test that shift_id must reference an existing shift."""
        non_existent_shift_id = uuid.uuid4()
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=8)

        scheduled = ShiftScheduled(
            start_at=start,
            end_at=end,
            shift_id=non_existent_shift_id
        )
        session.add(scheduled)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()


class TestShiftScheduledQueryPatterns:
    """Test suite for common ShiftScheduled query patterns."""

    def test_query_shifts_by_date_range(
        self, session: Session, shift_scheduled_factory
    ):
        """Test querying scheduled shifts within a date range."""
        # Arrange
        shift_scheduled_factory(
            start_at=datetime(2025, 1, 20, 9, 0),
            end_at=datetime(2025, 1, 20, 17, 0),
            description="Jan 20"
        )
        shift_scheduled_factory(
            start_at=datetime(2025, 1, 25, 9, 0),
            end_at=datetime(2025, 1, 25, 17, 0),
            description="Jan 25"
        )
        shift_scheduled_factory(
            start_at=datetime(2025, 2, 1, 9, 0),
            end_at=datetime(2025, 2, 1, 17, 0),
            description="Feb 1"
        )

        # Act - Query shifts in January
        statement = select(ShiftScheduled).where(
            ShiftScheduled.start_at >= datetime(2025, 1, 1),
            ShiftScheduled.start_at < datetime(2025, 2, 1)
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        descriptions = {s.description for s in results}
        assert descriptions == {"Jan 20", "Jan 25"}

    def test_query_shifts_by_specific_date(
        self, session: Session, shift_scheduled_factory
    ):
        """Test querying scheduled shifts on a specific date."""
        # Arrange
        target_date = datetime(2025, 1, 20)
        shift_scheduled_factory(
            start_at=datetime(2025, 1, 20, 9, 0),
            end_at=datetime(2025, 1, 20, 17, 0),
            description="Target day morning"
        )
        shift_scheduled_factory(
            start_at=datetime(2025, 1, 20, 18, 0),
            end_at=datetime(2025, 1, 20, 23, 0),
            description="Target day evening"
        )
        shift_scheduled_factory(
            start_at=datetime(2025, 1, 21, 9, 0),
            end_at=datetime(2025, 1, 21, 17, 0),
            description="Different day"
        )

        # Act
        next_day = target_date + timedelta(days=1)
        statement = select(ShiftScheduled).where(
            ShiftScheduled.start_at >= target_date,
            ShiftScheduled.start_at < next_day
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        descriptions = {s.description for s in results}
        assert descriptions == {"Target day morning", "Target day evening"}
