"""
Tests for MemberShiftScheduled link table CRUD operations and relationships.
"""

import uuid

import pytest
from sqlmodel import Session, select

from models import MemberShiftScheduled, Member, ShiftScheduled


class TestMemberShiftScheduledCRUD:
    """Test suite for MemberShiftScheduled Create, Read, Update, Delete operations."""

    def test_create_member_shift_scheduled(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test creating a member-shift assignment."""
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
        session.refresh(link)

        # Assert
        assert link.member_id == member.id
        assert link.shift_scheduled_id == scheduled.id

    def test_create_member_shift_scheduled_with_factory(
        self, member_shift_scheduled_factory
    ):
        """Test creating an assignment using the factory fixture."""
        # Act
        link = member_shift_scheduled_factory()

        # Assert
        assert link.member_id is not None
        assert link.shift_scheduled_id is not None

    def test_read_member_shift_scheduled(
        self, session: Session, member_shift_scheduled_factory
    ):
        """Test reading a member-shift assignment."""
        # Arrange
        created = member_shift_scheduled_factory()

        # Act
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == created.member_id,
            MemberShiftScheduled.shift_scheduled_id == created.shift_scheduled_id
        )
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.member_id == created.member_id
        assert result.shift_scheduled_id == created.shift_scheduled_id

    def test_read_all_member_shift_scheduled(
        self, session: Session, member_shift_scheduled_factory
    ):
        """Test reading multiple assignments."""
        # Arrange
        link1 = member_shift_scheduled_factory()
        link2 = member_shift_scheduled_factory()
        link3 = member_shift_scheduled_factory()

        # Act
        statement = select(MemberShiftScheduled)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3

    def test_delete_member_shift_scheduled(
        self, session: Session, member_shift_scheduled_factory
    ):
        """Test deleting a member-shift assignment."""
        # Arrange
        link = member_shift_scheduled_factory()
        member_id = link.member_id
        shift_id = link.shift_scheduled_id

        # Act
        session.delete(link)
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member_id,
            MemberShiftScheduled.shift_scheduled_id == shift_id
        )
        result = session.exec(statement).first()
        assert result is None


class TestMemberShiftScheduledRelationships:
    """Test suite for MemberShiftScheduled relationships."""

    def test_link_connects_member_and_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test that the link properly connects a member and scheduled shift."""
        # Arrange
        member = member_factory(name="Jane Doe", email="jane@example.com")
        scheduled = shift_scheduled_factory(description="Evening Shift")

        # Act
        link = MemberShiftScheduled(
            member_id=member.id,
            shift_scheduled_id=scheduled.id
        )
        session.add(link)
        session.commit()

        # Assert - Verify link exists
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member.id
        )
        result = session.exec(statement).first()
        assert result is not None
        assert result.shift_scheduled_id == scheduled.id

    def test_multiple_members_assigned_to_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test assigning multiple members to the same shift."""
        # Arrange
        member1 = member_factory(name="Member 1", email="m1@example.com")
        member2 = member_factory(name="Member 2", email="m2@example.com")
        member3 = member_factory(name="Member 3", email="m3@example.com")
        scheduled = shift_scheduled_factory(description="Team Shift")

        # Act
        link1 = MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=scheduled.id)
        link2 = MemberShiftScheduled(member_id=member2.id, shift_scheduled_id=scheduled.id)
        link3 = MemberShiftScheduled(member_id=member3.id, shift_scheduled_id=scheduled.id)
        session.add_all([link1, link2, link3])
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.shift_scheduled_id == scheduled.id
        )
        results = session.exec(statement).all()
        assert len(results) == 3
        member_ids = {link.member_id for link in results}
        assert member_ids == {member1.id, member2.id, member3.id}

    def test_member_assigned_to_multiple_shifts(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test assigning a member to multiple shifts."""
        # Arrange
        member = member_factory(name="Busy Worker", email="busy@example.com")
        shift1 = shift_scheduled_factory(description="Shift 1")
        shift2 = shift_scheduled_factory(description="Shift 2")
        shift3 = shift_scheduled_factory(description="Shift 3")

        # Act
        link1 = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift1.id)
        link2 = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift2.id)
        link3 = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift3.id)
        session.add_all([link1, link2, link3])
        session.commit()

        # Assert
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member.id
        )
        results = session.exec(statement).all()
        assert len(results) == 3
        shift_ids = {link.shift_scheduled_id for link in results}
        assert shift_ids == {shift1.id, shift2.id, shift3.id}

    def test_delete_link_does_not_delete_member(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test that deleting a link doesn't delete the member."""
        # Arrange
        member = member_factory(name="Test Member", email="test@example.com")
        scheduled = shift_scheduled_factory(description="Test Shift")
        link = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=scheduled.id)
        session.add(link)
        session.commit()

        # Act
        session.delete(link)
        session.commit()

        # Assert - Member should still exist
        statement = select(Member).where(Member.id == member.id)
        result = session.exec(statement).first()
        assert result is not None
        assert result.name == "Test Member"

    def test_delete_link_does_not_delete_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test that deleting a link doesn't delete the scheduled shift."""
        # Arrange
        member = member_factory(name="Test Member", email="test@example.com")
        scheduled = shift_scheduled_factory(description="Test Shift")
        link = MemberShiftScheduled(member_id=member.id, shift_scheduled_id=scheduled.id)
        session.add(link)
        session.commit()

        # Act
        session.delete(link)
        session.commit()

        # Assert - Scheduled shift should still exist
        statement = select(ShiftScheduled).where(ShiftScheduled.id == scheduled.id)
        result = session.exec(statement).first()
        assert result is not None
        assert result.description == "Test Shift"


class TestMemberShiftScheduledConstraints:
    """Test suite for MemberShiftScheduled validation and constraints."""

    def test_link_foreign_key_member_id(
        self, session: Session, shift_scheduled_factory
    ):
        """Test that member_id must reference an existing member."""
        scheduled = shift_scheduled_factory()
        non_existent_member_id = uuid.uuid4()

        link = MemberShiftScheduled(
            member_id=non_existent_member_id,
            shift_scheduled_id=scheduled.id
        )
        session.add(link)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()

    def test_link_foreign_key_shift_scheduled_id(
        self, session: Session, member_factory
    ):
        """Test that shift_scheduled_id must reference an existing scheduled shift."""
        member = member_factory()
        non_existent_shift_id = uuid.uuid4()

        link = MemberShiftScheduled(
            member_id=member.id,
            shift_scheduled_id=non_existent_shift_id
        )
        session.add(link)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()


class TestMemberShiftScheduledQueryPatterns:
    """Test suite for common MemberShiftScheduled query patterns."""

    def test_query_shifts_for_member(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test querying all shifts assigned to a specific member."""
        # Arrange
        member = member_factory(name="Worker", email="worker@example.com")
        shift1 = shift_scheduled_factory(description="Shift 1")
        shift2 = shift_scheduled_factory(description="Shift 2")
        shift_scheduled_factory(description="Shift 3")

        # Assign member to shifts 1 and 2
        session.add(MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift1.id))
        session.add(MemberShiftScheduled(member_id=member.id, shift_scheduled_id=shift2.id))
        session.commit()

        # Act
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member.id
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        shift_ids = {link.shift_scheduled_id for link in results}
        assert shift_ids == {shift1.id, shift2.id}

    def test_query_members_for_shift(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test querying all members assigned to a specific shift."""
        # Arrange
        shift = shift_scheduled_factory(description="Popular Shift")
        member1 = member_factory(name="M1", email="m1@example.com")
        member2 = member_factory(name="M2", email="m2@example.com")
        member3 = member_factory(name="M3", email="m3@example.com")

        # Assign members to shift
        session.add(MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=shift.id))
        session.add(MemberShiftScheduled(member_id=member2.id, shift_scheduled_id=shift.id))
        session.add(MemberShiftScheduled(member_id=member3.id, shift_scheduled_id=shift.id))
        session.commit()

        # Act
        statement = select(MemberShiftScheduled).where(
            MemberShiftScheduled.shift_scheduled_id == shift.id
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        member_ids = {link.member_id for link in results}
        assert member_ids == {member1.id, member2.id, member3.id}

    def test_count_shifts_per_member(
        self, session: Session, member_factory, shift_scheduled_factory
    ):
        """Test counting how many shifts each member is assigned to."""
        # Arrange
        member1 = member_factory(name="Member 1", email="m1@example.com")
        member2 = member_factory(name="Member 2", email="m2@example.com")
        shift1 = shift_scheduled_factory(description="S1")
        shift2 = shift_scheduled_factory(description="S2")
        shift3 = shift_scheduled_factory(description="S3")

        # Member 1: 3 shifts, Member 2: 1 shift
        session.add_all([
            MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=shift1.id),
            MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=shift2.id),
            MemberShiftScheduled(member_id=member1.id, shift_scheduled_id=shift3.id),
            MemberShiftScheduled(member_id=member2.id, shift_scheduled_id=shift1.id),
        ])
        session.commit()

        # Act
        statement1 = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member1.id
        )
        member1_shifts = session.exec(statement1).all()

        statement2 = select(MemberShiftScheduled).where(
            MemberShiftScheduled.member_id == member2.id
        )
        member2_shifts = session.exec(statement2).all()

        # Assert
        assert len(member1_shifts) == 3
        assert len(member2_shifts) == 1
