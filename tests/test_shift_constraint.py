"""
Tests for ShiftConstraint model CRUD operations and relationships.
"""

import uuid

import pytest
from sqlmodel import Session, select

from models import ShiftConstraint


class TestShiftConstraintCRUD:
    """Test suite for ShiftConstraint Create, Read, Update, Delete operations."""

    def test_create_shift_constraint(self, session: Session, shift_factory):
        """Test creating a new shift constraint."""
        # Arrange
        shift1 = shift_factory(description="Primary Shift")
        shift2 = shift_factory(description="Linked Shift")

        # Act
        constraint = ShiftConstraint(
            shift_id=shift1.id, linked_shift_id=shift2.id, within_last_shifts=2
        )
        session.add(constraint)
        session.commit()
        session.refresh(constraint)

        # Assert
        assert constraint.shift_id == shift1.id
        assert constraint.linked_shift_id == shift2.id
        assert constraint.within_last_shifts == 2

    def test_create_shift_constraint_with_factory(self, shift_constraint_factory):
        """Test creating a shift constraint using the factory fixture."""
        # Act
        constraint = shift_constraint_factory(within_last_shifts=3)

        # Assert
        assert constraint.shift_id is not None
        assert constraint.linked_shift_id is not None
        assert constraint.within_last_shifts == 3

    def test_create_shift_constraint_with_default_within_last_shifts(
        self, session: Session, shift_factory
    ):
        """Test creating a constraint with default within_last_shifts value."""
        # Arrange
        shift1 = shift_factory()
        shift2 = shift_factory()

        # Act
        constraint = ShiftConstraint(shift_id=shift1.id, linked_shift_id=shift2.id)
        session.add(constraint)
        session.commit()
        session.refresh(constraint)

        # Assert
        assert constraint.within_last_shifts == 1  # Default value

    def test_read_shift_constraint(self, session: Session, shift_constraint_factory):
        """Test reading a shift constraint from the database."""
        # Arrange
        created = shift_constraint_factory(within_last_shifts=5)

        # Act
        statement = select(ShiftConstraint).where(
            ShiftConstraint.shift_id == created.shift_id,
            ShiftConstraint.linked_shift_id == created.linked_shift_id,
        )
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.shift_id == created.shift_id
        assert result.linked_shift_id == created.linked_shift_id
        assert result.within_last_shifts == 5

    def test_read_all_shift_constraints(
        self, session: Session, shift_constraint_factory
    ):
        """Test reading multiple shift constraints."""
        # Arrange
        shift_constraint_factory(within_last_shifts=1)
        shift_constraint_factory(within_last_shifts=2)
        shift_constraint_factory(within_last_shifts=3)

        # Act
        statement = select(ShiftConstraint)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        within_values = {c.within_last_shifts for c in results}
        assert within_values == {1, 2, 3}

    def test_update_shift_constraint(self, session: Session, shift_constraint_factory):
        """Test updating a shift constraint's within_last_shifts value."""
        # Arrange
        constraint = shift_constraint_factory(within_last_shifts=2)
        original_shift_id = constraint.shift_id
        original_linked_id = constraint.linked_shift_id

        # Act
        constraint.within_last_shifts = 5
        session.add(constraint)
        session.commit()
        session.refresh(constraint)

        # Assert
        assert constraint.shift_id == original_shift_id
        assert constraint.linked_shift_id == original_linked_id
        assert constraint.within_last_shifts == 5

    def test_delete_shift_constraint(self, session: Session, shift_constraint_factory):
        """Test deleting a shift constraint."""
        # Arrange
        constraint = shift_constraint_factory()
        shift_id = constraint.shift_id
        linked_id = constraint.linked_shift_id

        # Act
        session.delete(constraint)
        session.commit()

        # Assert
        statement = select(ShiftConstraint).where(
            ShiftConstraint.shift_id == shift_id,
            ShiftConstraint.linked_shift_id == linked_id,
        )
        result = session.exec(statement).first()
        assert result is None


class TestShiftConstraintRelationships:
    """Test suite for ShiftConstraint relationships."""

    def test_shift_constraint_links_two_shifts(
        self, session: Session, shift_factory, shift_constraint_factory
    ):
        """Test that a constraint properly links two shifts."""
        # Arrange
        morning_shift = shift_factory(
            seconds_since_midnight=28800,  # 8 AM
            description="Morning Shift",
        )
        evening_shift = shift_factory(
            seconds_since_midnight=57600,  # 4 PM
            description="Evening Shift",
        )

        # Act
        constraint = shift_constraint_factory(
            shift_id=morning_shift.id,
            linked_shift_id=evening_shift.id,
            within_last_shifts=1,
        )

        # Assert
        assert constraint.shift_id == morning_shift.id
        assert constraint.linked_shift_id == evening_shift.id

    def test_shift_can_have_multiple_constraints(self, session: Session, shift_factory):
        """Test that a shift can have multiple constraints linking to different shifts."""
        # Arrange
        primary_shift = shift_factory(description="Primary")
        linked1 = shift_factory(description="Linked 1")
        linked2 = shift_factory(description="Linked 2")
        linked3 = shift_factory(description="Linked 3")

        # Act - Create multiple constraints from primary shift
        constraint1 = ShiftConstraint(
            shift_id=primary_shift.id, linked_shift_id=linked1.id, within_last_shifts=1
        )
        constraint2 = ShiftConstraint(
            shift_id=primary_shift.id, linked_shift_id=linked2.id, within_last_shifts=2
        )
        constraint3 = ShiftConstraint(
            shift_id=primary_shift.id, linked_shift_id=linked3.id, within_last_shifts=3
        )
        session.add_all([constraint1, constraint2, constraint3])
        session.commit()

        # Assert
        statement = select(ShiftConstraint).where(
            ShiftConstraint.shift_id == primary_shift.id
        )
        results = session.exec(statement).all()
        assert len(results) == 3

    def test_shift_can_be_linked_by_multiple_shifts(
        self, session: Session, shift_factory
    ):
        """Test that a shift can be the target of multiple constraints."""
        # Arrange
        target_shift = shift_factory(description="Target")
        source1 = shift_factory(description="Source 1")
        source2 = shift_factory(description="Source 2")

        # Act
        constraint1 = ShiftConstraint(
            shift_id=source1.id, linked_shift_id=target_shift.id, within_last_shifts=1
        )
        constraint2 = ShiftConstraint(
            shift_id=source2.id, linked_shift_id=target_shift.id, within_last_shifts=2
        )
        session.add_all([constraint1, constraint2])
        session.commit()

        # Assert
        statement = select(ShiftConstraint).where(
            ShiftConstraint.linked_shift_id == target_shift.id
        )
        results = session.exec(statement).all()
        assert len(results) == 2

    def test_bidirectional_constraints(self, session: Session, shift_factory):
        """Test creating bidirectional constraints between two shifts."""
        # Arrange
        shift_a = shift_factory(description="Shift A")
        shift_b = shift_factory(description="Shift B")

        # Act - Create constraints in both directions
        constraint_a_to_b = ShiftConstraint(
            shift_id=shift_a.id, linked_shift_id=shift_b.id, within_last_shifts=1
        )
        constraint_b_to_a = ShiftConstraint(
            shift_id=shift_b.id, linked_shift_id=shift_a.id, within_last_shifts=1
        )
        session.add_all([constraint_a_to_b, constraint_b_to_a])
        session.commit()

        # Assert
        statement = select(ShiftConstraint)
        results = session.exec(statement).all()
        assert len(results) == 2

    def test_self_referential_constraint(self, session: Session, shift_factory):
        """Test creating a constraint where a shift references itself."""
        # Arrange
        shift = shift_factory(description="Self-referencing")

        # Act - Create constraint where shift links to itself
        constraint = ShiftConstraint(
            shift_id=shift.id, linked_shift_id=shift.id, within_last_shifts=2
        )
        session.add(constraint)
        session.commit()

        # Assert
        statement = select(ShiftConstraint).where(
            ShiftConstraint.shift_id == shift.id,
            ShiftConstraint.linked_shift_id == shift.id,
        )
        result = session.exec(statement).first()
        assert result is not None
        assert result.shift_id == shift.id
        assert result.linked_shift_id == shift.id


class TestShiftConstraintValidation:
    """Test suite for ShiftConstraint validation and constraints."""

    def test_shift_constraint_within_last_shifts_must_be_positive(
        self, session: Session, shift_factory
    ):
        """Test that within_last_shifts must be non-negative (>= 0)."""
        shift1 = shift_factory()
        shift2 = shift_factory()

        # Test zero value is allowed (prevents assignment to both shifts in the same day)
        constraint_zero = ShiftConstraint(
            shift_id=shift1.id, linked_shift_id=shift2.id, within_last_shifts=0
        )
        session.add(constraint_zero)
        session.commit()
        session.refresh(constraint_zero)
        assert constraint_zero.within_last_shifts == 0

        # Test negative value is rejected
        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(
                ShiftConstraint(
                    shift_id=shift1.id, linked_shift_id=shift2.id, within_last_shifts=-1
                )
            )
            session.commit()

    def test_shift_constraint_foreign_key_shift_id(
        self, session: Session, shift_factory
    ):
        """Test that shift_id must reference an existing shift."""
        shift = shift_factory()
        non_existent_id = uuid.uuid4()

        constraint = ShiftConstraint(
            shift_id=non_existent_id, linked_shift_id=shift.id, within_last_shifts=1
        )
        session.add(constraint)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()

    def test_shift_constraint_foreign_key_linked_shift_id(
        self, session: Session, shift_factory
    ):
        """Test that linked_shift_id must reference an existing shift."""
        shift = shift_factory()
        non_existent_id = uuid.uuid4()

        constraint = ShiftConstraint(
            shift_id=shift.id, linked_shift_id=non_existent_id, within_last_shifts=1
        )
        session.add(constraint)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()


class TestShiftConstraintQueryPatterns:
    """Test suite for common ShiftConstraint query patterns."""

    def test_query_constraints_for_shift(
        self, session: Session, shift_factory, shift_constraint_factory
    ):
        """Test querying all constraints for a specific shift."""
        # Arrange
        primary = shift_factory(description="Primary")
        linked1 = shift_factory(description="Linked 1")
        linked2 = shift_factory(description="Linked 2")

        shift_constraint_factory(
            shift_id=primary.id, linked_shift_id=linked1.id, within_last_shifts=1
        )
        shift_constraint_factory(
            shift_id=primary.id, linked_shift_id=linked2.id, within_last_shifts=2
        )

        # Create constraint for different shift (should not be returned)
        other = shift_factory(description="Other")
        shift_constraint_factory(shift_id=other.id, linked_shift_id=linked1.id)

        # Act
        statement = select(ShiftConstraint).where(
            ShiftConstraint.shift_id == primary.id
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        linked_ids = {c.linked_shift_id for c in results}
        assert linked_ids == {linked1.id, linked2.id}

    def test_query_constraints_by_within_last_shifts(
        self, session: Session, shift_constraint_factory
    ):
        """Test querying constraints by within_last_shifts value."""
        # Arrange
        shift_constraint_factory(within_last_shifts=1)
        shift_constraint_factory(within_last_shifts=1)
        shift_constraint_factory(within_last_shifts=2)
        shift_constraint_factory(within_last_shifts=3)

        # Act
        statement = select(ShiftConstraint).where(
            ShiftConstraint.within_last_shifts == 1
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        assert all(c.within_last_shifts == 1 for c in results)

    def test_query_constraints_by_threshold(
        self, session: Session, shift_constraint_factory
    ):
        """Test querying constraints with within_last_shifts above a threshold."""
        # Arrange
        shift_constraint_factory(within_last_shifts=1)
        shift_constraint_factory(within_last_shifts=2)
        shift_constraint_factory(within_last_shifts=3)
        shift_constraint_factory(within_last_shifts=5)

        # Act - Find constraints with within_last_shifts >= 3
        statement = select(ShiftConstraint).where(
            ShiftConstraint.within_last_shifts >= 3
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        within_values = {c.within_last_shifts for c in results}
        assert within_values == {3, 5}


class TestShiftConstraintAutoGeneration:
    """Test suite for automatic constraint generation from overlapping shifts."""

    def test_detect_same_day_time_overlap_no_overlap(self):
        """Test that non-overlapping time ranges return False."""
        # Morning shift: 8am-12pm (28800-43200)
        # Afternoon shift: 1pm-5pm (46800-61200)
        overlap = ShiftConstraint._shifts_overlap_on_day(
            start_a=28800, duration_a=14400, start_b=46800, duration_b=14400
        )
        assert overlap is False

    def test_detect_same_day_time_overlap_partial(self):
        """Test that partially overlapping time ranges return True."""
        # Shift A: 9am-5pm (32400-61200)
        # Shift B: 3pm-11pm (54000-82800)
        # Overlap: 3pm-5pm
        overlap = ShiftConstraint._shifts_overlap_on_day(
            start_a=32400, duration_a=28800, start_b=54000, duration_b=28800
        )
        assert overlap is True

    def test_detect_same_day_time_overlap_complete_containment(self):
        """Test that one shift completely contains another."""
        # Shift A: 8am-8pm (28800-72000) - 12 hours
        # Shift B: 10am-2pm (36000-50400) - 4 hours
        overlap = ShiftConstraint._shifts_overlap_on_day(
            start_a=28800, duration_a=43200, start_b=36000, duration_b=14400
        )
        assert overlap is True

    def test_detect_same_day_time_overlap_identical(self):
        """Test that identical time ranges overlap."""
        # Both shifts: 9am-5pm
        overlap = ShiftConstraint._shifts_overlap_on_day(
            start_a=32400, duration_a=28800, start_b=32400, duration_b=28800
        )
        assert overlap is True

    def test_detect_same_day_time_overlap_adjacent_no_overlap(self):
        """Test that adjacent but non-overlapping shifts return False."""
        # Shift A: 9am-5pm (ends at 61200)
        # Shift B: 5pm-9pm (starts at 61200)
        overlap = ShiftConstraint._shifts_overlap_on_day(
            start_a=32400, duration_a=28800, start_b=61200, duration_b=14400
        )
        assert overlap is False

    def test_detect_cross_day_overlap_shift_crosses_midnight(self):
        """Test detecting when a shift crosses midnight into another shift."""
        # Shift A: Monday 11pm-1am (82800 + 7200 = 90000, crosses midnight)
        # Shift B: Tuesday 12am-8am (0 + 28800 = 28800)
        # Next day from Monday (1) is Tuesday (2)
        crosses, overlaps_next = ShiftConstraint._check_cross_day_overlap(
            start_a=82800,
            duration_a=7200,  # 11pm for 2 hours
            start_b=0,  # 12am
            day_a=1,
            day_b=2,  # Monday -> Tuesday
        )
        assert crosses is True
        assert overlaps_next is True

    def test_detect_cross_day_overlap_no_midnight_crossing(self):
        """Test that shifts not crossing midnight return False."""
        # Shift A: Monday 9am-5pm (no midnight crossing)
        # Shift B: Tuesday 9am-5pm
        crosses, overlaps_next = ShiftConstraint._check_cross_day_overlap(
            start_a=32400,
            duration_a=28800,  # 9am for 8 hours
            start_b=32400,
            day_a=1,
            day_b=2,
        )
        assert crosses is False
        assert overlaps_next is False

    def test_detect_cross_day_overlap_crosses_but_no_overlap(self):
        """Test shift crosses midnight but doesn't overlap next shift."""
        # Shift A: Monday 11pm-12:30am (82800 + 5400 = 88200, ends at 12:30am)
        # Shift B: Tuesday 8am-4pm (starts at 28800)
        # Spillover ends before Shift B starts
        crosses, overlaps_next = ShiftConstraint._check_cross_day_overlap(
            start_a=82800,
            duration_a=5400,  # 11pm for 1.5 hours
            start_b=28800,  # 8am
            day_a=1,
            day_b=2,
        )
        assert crosses is True
        assert overlaps_next is False

    def test_detect_cross_day_overlap_sunday_to_monday(self):
        """Test wraparound from Sunday (0) to Monday (1)."""
        # Shift A: Sunday 11pm-1am
        # Shift B: Monday 12am-8am
        crosses, overlaps_next = ShiftConstraint._check_cross_day_overlap(
            start_a=82800,
            duration_a=7200,
            start_b=0,
            day_a=0,
            day_b=1,  # Sunday -> Monday
        )
        assert crosses is True
        assert overlaps_next is True

    def test_detect_cross_day_overlap_not_consecutive_days(self):
        """Test that non-consecutive days return False for overlap."""
        # Shift A: Monday 11pm-1am (crosses into Tuesday)
        # Shift B: Wednesday 12am-8am (not the next day)
        crosses, overlaps_next = ShiftConstraint._check_cross_day_overlap(
            start_a=82800,
            duration_a=7200,
            start_b=0,
            day_a=1,
            day_b=3,  # Monday -> Wednesday (not consecutive)
        )
        assert crosses is True
        assert overlaps_next is False

    def test_generate_from_overlaps_same_day_bidirectional(
        self, session: Session, shift_factory
    ):
        """Test generating bidirectional constraints for same-day overlaps."""
        # Arrange - Create two shifts that overlap on Monday
        shift_a = shift_factory(
            seconds_since_midnight=32400,  # 9am
            duration_seconds=28800,  # 8 hours (9am-5pm)
            days=["1"],  # Monday
            description="Morning Shift",
        )
        shift_b = shift_factory(
            seconds_since_midnight=46800,  # 1pm
            duration_seconds=21600,  # 6 hours (1pm-7pm)
            days=["1"],  # Monday
            description="Afternoon Shift",
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result["created"] == 2
        assert result["updated"] == 0
        assert result["unchanged"] == 0

        # Verify bidirectional constraints created
        constraints = session.exec(select(ShiftConstraint)).all()
        assert len(constraints) == 2

        # Check constraint A -> B
        constraint_ab = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_a.id,
                ShiftConstraint.linked_shift_id == shift_b.id,
            )
        ).first()
        assert constraint_ab is not None
        assert constraint_ab.within_last_shifts == 0

        # Check constraint B -> A
        constraint_ba = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_b.id,
                ShiftConstraint.linked_shift_id == shift_a.id,
            )
        ).first()
        assert constraint_ba is not None
        assert constraint_ba.within_last_shifts == 0

    def test_generate_from_overlaps_cross_day_unidirectional(
        self, session: Session, shift_factory
    ):
        """Test generating unidirectional constraints for cross-day overlaps."""
        # Arrange - Create shift that crosses midnight into another shift
        shift_a = shift_factory(
            seconds_since_midnight=82800,  # 11pm
            duration_seconds=7200,  # 2 hours (11pm-1am)
            days=["1"],  # Monday
            description="Night Shift",
        )
        shift_b = shift_factory(
            seconds_since_midnight=0,  # 12am
            duration_seconds=28800,  # 8 hours (12am-8am)
            days=["2"],  # Tuesday
            description="Early Morning Shift",
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert - Should create only unidirectional constraint
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["unchanged"] == 0

        # Verify unidirectional constraint A -> B
        constraint_ab = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_a.id,
                ShiftConstraint.linked_shift_id == shift_b.id,
            )
        ).first()
        assert constraint_ab is not None
        assert constraint_ab.within_last_shifts == 1

        # Verify no reverse constraint B -> A
        constraint_ba = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_b.id,
                ShiftConstraint.linked_shift_id == shift_a.id,
            )
        ).first()
        assert constraint_ba is None

    def test_generate_from_overlaps_updates_existing_constraints(
        self, session: Session, shift_factory, shift_constraint_factory
    ):
        """Test that existing constraints are updated if overlap type changes."""
        # Arrange - Create two overlapping shifts
        shift_a = shift_factory(
            seconds_since_midnight=32400,
            duration_seconds=28800,
            days=["1"],
            description="Shift A",
        )
        shift_b = shift_factory(
            seconds_since_midnight=46800,
            duration_seconds=21600,
            days=["1"],
            description="Shift B",
        )

        # Create existing constraint with WRONG value (should be 0 for same-day)
        shift_constraint_factory(
            shift_id=shift_a.id,
            linked_shift_id=shift_b.id,
            within_last_shifts=2,  # Wrong value
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result["created"] == 1  # B -> A constraint created
        assert result["updated"] == 1  # A -> B constraint updated
        assert result["unchanged"] == 0

        # Verify updated constraint has correct value
        constraint_ab = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_a.id,
                ShiftConstraint.linked_shift_id == shift_b.id,
            )
        ).first()
        assert constraint_ab.within_last_shifts == 0

    def test_generate_from_overlaps_idempotent(self, session: Session, shift_factory):
        """Test that running generate_from_overlaps multiple times is idempotent."""
        # Arrange
        _shift_a = shift_factory(
            seconds_since_midnight=32400,
            duration_seconds=28800,
            days=["1"],
        )
        _shift_b = shift_factory(
            seconds_since_midnight=46800,
            duration_seconds=21600,
            days=["1"],
        )

        # Act - Run twice
        result1 = ShiftConstraint.generate_from_overlaps(session)
        result2 = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result1["created"] == 2
        assert result1["updated"] == 0
        assert result1["unchanged"] == 0

        assert result2["created"] == 0
        assert result2["updated"] == 0
        assert result2["unchanged"] == 2

        # Verify still only 2 constraints
        constraints = session.exec(select(ShiftConstraint)).all()
        assert len(constraints) == 2

    def test_generate_from_overlaps_no_shifts(self, session: Session):
        """Test that method handles empty shift list gracefully."""
        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["unchanged"] == 0

    def test_generate_from_overlaps_single_shift(self, session: Session, shift_factory):
        """Test that single shift creates no constraints."""
        # Arrange
        shift_factory(seconds_since_midnight=32400, duration_seconds=28800)

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result["created"] == 0

    def test_generate_from_overlaps_no_overlaps(self, session: Session, shift_factory):
        """Test shifts on different days with no overlaps."""
        # Arrange - Different days, no midnight crossing
        shift_factory(
            seconds_since_midnight=32400,
            duration_seconds=28800,
            days=["1"],  # Monday
        )
        shift_factory(
            seconds_since_midnight=32400,
            duration_seconds=28800,
            days=["3"],  # Wednesday
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert
        assert result["created"] == 0

    def test_generate_from_overlaps_sunday_to_monday_wraparound(
        self, session: Session, shift_factory
    ):
        """Test Sunday night shift extending into Monday morning."""
        # Arrange
        shift_sunday = shift_factory(
            seconds_since_midnight=82800,  # 11pm
            duration_seconds=7200,  # 2 hours
            days=["0"],  # Sunday
            description="Sunday Night",
        )
        shift_monday = shift_factory(
            seconds_since_midnight=0,  # 12am
            duration_seconds=28800,  # 8 hours
            days=["1"],  # Monday
            description="Monday Morning",
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert - Unidirectional Sunday -> Monday
        assert result["created"] == 1

        constraint = session.exec(
            select(ShiftConstraint).where(
                ShiftConstraint.shift_id == shift_sunday.id,
                ShiftConstraint.linked_shift_id == shift_monday.id,
            )
        ).first()
        assert constraint is not None
        assert constraint.within_last_shifts == 1

    def test_generate_from_overlaps_multiple_overlaps_same_shift(
        self, session: Session, shift_factory
    ):
        """Test shift that overlaps with multiple other shifts."""
        # Arrange - Create shift A that overlaps with both B and C
        _shift_a = shift_factory(
            seconds_since_midnight=36000,  # 10am
            duration_seconds=28800,  # 8 hours (10am-6pm)
            days=["1"],
            description="Long Shift",
        )
        _shift_b = shift_factory(
            seconds_since_midnight=32400,  # 9am
            duration_seconds=14400,  # 4 hours (9am-1pm)
            days=["1"],
            description="Morning Shift",
        )
        _shift_c = shift_factory(
            seconds_since_midnight=54000,  # 3pm
            duration_seconds=14400,  # 4 hours (3pm-7pm)
            days=["1"],
            description="Afternoon Shift",
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert - Should create bidirectional constraints for all pairs
        # A<->B (2), A<->C (2), B<->C (0, they don't overlap) = 4 total
        assert result["created"] == 4

    def test_generate_from_overlaps_shift_on_multiple_days(
        self, session: Session, shift_factory
    ):
        """Test shift that runs on multiple days of the week."""
        # Arrange
        _shift_a = shift_factory(
            seconds_since_midnight=32400,
            duration_seconds=28800,
            days=["1", "2", "3"],  # Mon, Tue, Wed
            description="Weekday Shift",
        )
        _shift_b = shift_factory(
            seconds_since_midnight=46800,
            duration_seconds=21600,
            days=["2"],  # Tuesday only
            description="Tuesday Shift",
        )

        # Act
        result = ShiftConstraint.generate_from_overlaps(session)

        # Assert - Should detect overlap on Tuesday (same-day bidirectional)
        assert result["created"] == 2

        # Verify bidirectional constraints
        constraints = session.exec(select(ShiftConstraint)).all()
        assert len(constraints) == 2
        assert all(c.within_last_shifts == 0 for c in constraints)
