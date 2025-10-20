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
        """Test that within_last_shifts must be a positive integer."""
        shift1 = shift_factory()
        shift2 = shift_factory()

        # Test zero value
        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(
                ShiftConstraint(
                    shift_id=shift1.id, linked_shift_id=shift2.id, within_last_shifts=0
                )
            )
            session.commit()

        # Test negative value
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
