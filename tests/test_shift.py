"""
Tests for Shift model CRUD operations.
"""

import uuid
from datetime import datetime

import pytest
from sqlmodel import Session, select

from models import Shift


class TestShiftCRUD:
    """Test suite for Shift Create, Read, Update, Delete operations."""

    def test_create_shift(self, session: Session):
        """Test creating a new shift."""
        # Arrange - 9:00 AM for 8 hours on Monday and Wednesday
        seconds_9am = 9 * 3600
        duration_8h = 8 * 3600

        # Act
        shift = Shift(
            seconds_since_midnight=seconds_9am,
            duration_seconds=duration_8h,
            days=["1", "3"],  # Monday, Wednesday
            description="Morning shift",
            members_required=1,
        )
        session.add(shift)
        session.commit()
        session.refresh(shift)

        # Assert
        assert shift.id is not None
        assert isinstance(shift.id, uuid.UUID)
        assert shift.seconds_since_midnight == seconds_9am
        assert shift.duration_seconds == duration_8h
        assert shift.days == ["1", "3"]
        assert shift.description == "Morning shift"
        assert isinstance(shift.created_at, datetime)
        assert isinstance(shift.updated_at, datetime)

    def test_create_shift_with_factory(self, shift_factory):
        """Test creating a shift using the factory fixture."""
        # Act
        shift = shift_factory(
            seconds_since_midnight=32400,  # 9:00 AM
            duration_seconds=28800,  # 8 hours
            days=["1", "2", "3", "4", "5"],  # Weekdays
            description="Weekday morning shift",
        )

        # Assert
        assert shift.id is not None
        assert shift.seconds_since_midnight == 32400
        assert shift.duration_seconds == 28800
        assert len(shift.days) == 5
        assert shift.description == "Weekday morning shift"

    def test_create_shift_with_defaults(self, session: Session):
        """Test creating a shift with default values."""
        # Act
        shift = Shift(members_required=1)
        session.add(shift)
        session.commit()
        session.refresh(shift)

        # Assert
        assert shift.seconds_since_midnight == 0  # Midnight
        assert shift.duration_seconds == 3600  # 1 hour
        assert shift.days == []
        assert shift.members_required == 1
        assert shift.description == ""

    def test_read_shift(self, session: Session, shift_factory):
        """Test reading a shift from the database."""
        # Arrange
        created_shift = shift_factory(
            seconds_since_midnight=14400,  # 4:00 AM
            duration_seconds=21600,  # 6 hours
            days=["0", "6"],  # Sunday, Saturday (weekend)
            description="Weekend early shift",
        )

        # Act
        statement = select(Shift).where(Shift.id == created_shift.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.id == created_shift.id
        assert result.seconds_since_midnight == 14400
        assert result.duration_seconds == 21600
        assert result.days == ["0", "6"]
        assert result.description == "Weekend early shift"

    def test_read_all_shifts(self, session: Session, shift_factory):
        """Test reading multiple shifts."""
        # Arrange
        shift_factory(description="Shift 1")
        shift_factory(description="Shift 2")
        shift_factory(description="Shift 3")

        # Act
        statement = select(Shift)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        descriptions = {shift.description for shift in results}
        assert descriptions == {"Shift 1", "Shift 2", "Shift 3"}

    def test_update_shift(self, session: Session, shift_factory):
        """Test updating a shift's information."""
        # Arrange
        shift = shift_factory(
            seconds_since_midnight=28800,  # 8:00 AM
            duration_seconds=14400,  # 4 hours
            days=["1"],
            description="Old description",
        )
        original_id = shift.id

        # Act
        shift.seconds_since_midnight = 36000  # 10:00 AM
        shift.duration_seconds = 18000  # 5 hours
        shift.days = ["1", "3", "5"]
        shift.description = "New description"
        session.add(shift)
        session.commit()
        session.refresh(shift)

        # Assert
        assert shift.id == original_id
        assert shift.seconds_since_midnight == 36000
        assert shift.duration_seconds == 18000
        assert shift.days == ["1", "3", "5"]
        assert shift.description == "New description"

    def test_delete_shift(self, session: Session, shift_factory):
        """Test deleting a shift."""
        # Arrange
        shift = shift_factory(description="To be deleted")
        shift_id = shift.id

        # Act
        session.delete(shift)
        session.commit()

        # Assert
        statement = select(Shift).where(Shift.id == shift_id)
        result = session.exec(statement).first()
        assert result is None


class TestShiftTimeHandling:
    """Test suite for Shift time-related functionality."""

    def test_shift_seconds_since_midnight_boundary_values(self, session: Session):
        """Test boundary values for seconds_since_midnight."""
        # Test midnight (0 seconds)
        shift_midnight = Shift(seconds_since_midnight=0, members_required=1)
        session.add(shift_midnight)

        # Test end of day (86399 seconds = 23:59:59)
        shift_end_of_day = Shift(seconds_since_midnight=86399, members_required=1)
        session.add(shift_end_of_day)

        session.commit()
        session.refresh(shift_midnight)
        session.refresh(shift_end_of_day)

        # Assert
        assert shift_midnight.seconds_since_midnight == 0
        assert shift_end_of_day.seconds_since_midnight == 86399

    def test_shift_duration_positive_values(self, session: Session):
        """Test that duration_seconds must be positive."""
        # Duration must be positive integer (PositiveInt)
        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(Shift(duration_seconds=0))
            session.commit()

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(Shift(duration_seconds=-1))
            session.commit()

    def test_shift_various_durations(self, shift_factory):
        """Test shifts with various duration values."""
        # 30 minute shift
        shift_30min = shift_factory(duration_seconds=1800)
        assert shift_30min.duration_seconds == 1800

        # 12 hour shift
        shift_12h = shift_factory(duration_seconds=43200)
        assert shift_12h.duration_seconds == 43200

        # 24 hour shift
        shift_24h = shift_factory(duration_seconds=86400)
        assert shift_24h.duration_seconds == 86400


class TestShiftDaysHandling:
    """Test suite for Shift days field functionality."""

    def test_shift_single_day(self, shift_factory):
        """Test shift with a single day."""
        shift = shift_factory(days=["2"])  # Tuesday only
        assert shift.days == ["2"]
        assert len(shift.days) == 1

    def test_shift_multiple_days(self, shift_factory):
        """Test shift with multiple days."""
        shift = shift_factory(days=["1", "2", "3", "4", "5"])  # Weekdays
        assert len(shift.days) == 5
        assert "1" in shift.days
        assert "5" in shift.days

    def test_shift_all_days(self, shift_factory):
        """Test shift with all days of the week."""
        all_days = ["0", "1", "2", "3", "4", "5", "6"]
        shift = shift_factory(days=all_days)
        assert len(shift.days) == 7
        assert shift.days == all_days

    def test_shift_weekend_only(self, shift_factory):
        """Test shift for weekend only."""
        shift = shift_factory(days=["0", "6"])  # Sunday, Saturday
        assert len(shift.days) == 2
        assert "0" in shift.days
        assert "6" in shift.days

    def test_shift_empty_days(self, shift_factory):
        """Test shift with no days specified."""
        shift = shift_factory(days=[])
        assert shift.days == []
        assert len(shift.days) == 0

    def test_shift_days_stored_as_json(self, session: Session, shift_factory):
        """Test that days are properly stored and retrieved as JSON."""
        # Arrange
        days = ["1", "3", "5"]
        shift = shift_factory(days=days)

        # Act - retrieve from database
        statement = select(Shift).where(Shift.id == shift.id)
        retrieved_shift = session.exec(statement).first()

        # Assert
        assert retrieved_shift.days == days
        assert isinstance(retrieved_shift.days, list)


class TestShiftValidation:
    """Test suite for Shift validation and constraints."""

    def test_shift_seconds_since_midnight_must_be_non_negative(self, session: Session):
        """Test that seconds_since_midnight cannot be negative."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(Shift(seconds_since_midnight=-1))
            session.commit()

    def test_shift_description_defaults_to_empty(self, session: Session):
        """Test that description defaults to empty string."""
        shift = Shift(members_required=1)
        session.add(shift)
        session.commit()
        session.refresh(shift)

        assert shift.description == ""

    def test_shift_description_can_be_set(self, shift_factory):
        """Test that description can be set to various values."""
        shift1 = shift_factory(description="Morning shift")
        assert shift1.description == "Morning shift"

        shift2 = shift_factory(description="")
        assert shift2.description == ""

        shift3 = shift_factory(description="Long description " * 50)
        assert len(shift3.description) > 100


class TestShiftQueryPatterns:
    """Test suite for common Shift query patterns."""

    def test_query_shifts_by_day(self, session: Session, shift_factory):
        """Test querying shifts that occur on a specific day."""
        # Arrange
        shift_factory(days=["1"], description="Monday only")
        shift_factory(days=["2"], description="Tuesday only")
        shift_factory(days=["1", "3"], description="Mon & Wed")

        # Act - Find all shifts that include Monday
        statement = select(Shift)
        all_shifts = session.exec(statement).all()
        monday_shifts = [s for s in all_shifts if "1" in s.days]

        # Assert
        assert len(monday_shifts) == 2
        descriptions = {s.description for s in monday_shifts}
        assert descriptions == {"Monday only", "Mon & Wed"}

    def test_query_shifts_by_time_range(self, session: Session, shift_factory):
        """Test querying shifts by time of day."""
        # Arrange - Create morning, afternoon, and evening shifts
        shift_factory(
            seconds_since_midnight=28800,  # 8:00 AM
            description="Morning",
        )
        shift_factory(
            seconds_since_midnight=43200,  # 12:00 PM
            description="Afternoon",
        )
        shift_factory(
            seconds_since_midnight=61200,  # 5:00 PM
            description="Evening",
        )

        # Act - Query shifts starting between 8 AM and 1 PM
        statement = select(Shift).where(
            Shift.seconds_since_midnight >= 28800,  # >= 8:00 AM
            Shift.seconds_since_midnight <= 46800,  # <= 1:00 PM
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        descriptions = {s.description for s in results}
        assert descriptions == {"Morning", "Afternoon"}
