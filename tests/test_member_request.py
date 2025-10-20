"""
Tests for MemberRequest model CRUD operations and relationships.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session, select

from models import Member, MemberRequest


class TestMemberRequestCRUD:
    """Test suite for MemberRequest Create, Read, Update, Delete operations."""

    def test_create_member_request(self, session: Session, member_factory):
        """Test creating a new member request."""
        # Arrange
        member = member_factory(name="John Doe", email="john@example.com")
        start = datetime(2025, 2, 1, 0, 0)
        end = datetime(2025, 2, 3, 0, 0)

        # Act
        request = MemberRequest(
            start_at=start, end_at=end, member_id=member.id, description="Vacation"
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        # Assert
        assert request.id is not None
        assert isinstance(request.id, uuid.UUID)
        assert request.start_at == start
        assert request.end_at == end
        assert request.member_id == member.id
        assert request.description == "Vacation"
        assert isinstance(request.created_at, datetime)
        assert isinstance(request.updated_at, datetime)

    def test_create_member_request_with_factory(self, member_request_factory):
        """Test creating a member request using the factory fixture."""
        # Act
        start = datetime(2025, 3, 10, 9, 0)
        end = datetime(2025, 3, 12, 17, 0)
        request = member_request_factory(
            start_at=start, end_at=end, description="Doctor appointment"
        )

        # Assert
        assert request.id is not None
        assert request.start_at == start
        assert request.end_at == end
        assert request.member_id is not None
        assert request.description == "Doctor appointment"

    def test_read_member_request(self, session: Session, member_request_factory):
        """Test reading a member request from the database."""
        # Arrange
        created = member_request_factory(description="Time off request")

        # Act
        statement = select(MemberRequest).where(MemberRequest.id == created.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.id == created.id
        assert result.start_at == created.start_at
        assert result.end_at == created.end_at
        assert result.member_id == created.member_id
        assert result.description == "Time off request"

    def test_read_all_member_requests(self, session: Session, member_request_factory):
        """Test reading multiple member requests."""
        # Arrange
        member_request_factory(description="Request 1")
        member_request_factory(description="Request 2")
        member_request_factory(description="Request 3")

        # Act
        statement = select(MemberRequest)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        descriptions = {r.description for r in results}
        assert descriptions == {"Request 1", "Request 2", "Request 3"}

    def test_update_member_request(self, session: Session, member_request_factory):
        """Test updating a member request's information."""
        # Arrange
        request = member_request_factory(description="Original request")
        original_id = request.id
        new_start = request.start_at + timedelta(days=1)
        new_end = request.end_at + timedelta(days=1)

        # Act
        request.start_at = new_start
        request.end_at = new_end
        request.description = "Updated request"
        session.add(request)
        session.commit()
        session.refresh(request)

        # Assert
        assert request.id == original_id
        assert request.start_at == new_start
        assert request.end_at == new_end
        assert request.description == "Updated request"

    def test_delete_member_request(self, session: Session, member_request_factory):
        """Test deleting a member request."""
        # Arrange
        request = member_request_factory(description="To be cancelled")
        request_id = request.id

        # Act
        session.delete(request)
        session.commit()

        # Assert
        statement = select(MemberRequest).where(MemberRequest.id == request_id)
        result = session.exec(statement).first()
        assert result is None


class TestMemberRequestRelationships:
    """Test suite for MemberRequest relationships."""

    def test_member_request_belongs_to_member(
        self, session: Session, member_factory, member_request_factory
    ):
        """Test that a member request is linked to a member."""
        # Arrange
        member = member_factory(name="Jane Doe", email="jane@example.com")
        request = member_request_factory(
            member_id=member.id, description="Jane's vacation"
        )

        # Act
        statement = select(MemberRequest).where(MemberRequest.id == request.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.member_id == member.id

    def test_member_can_have_multiple_requests(
        self, session: Session, member_factory, member_request_factory
    ):
        """Test that a member can have multiple requests."""
        # Arrange
        member = member_factory(name="Busy Member", email="busy@example.com")

        # Create multiple requests for the same member
        member_request_factory(
            member_id=member.id,
            start_at=datetime(2025, 2, 1),
            end_at=datetime(2025, 2, 3),
            description="February vacation",
        )
        member_request_factory(
            member_id=member.id,
            start_at=datetime(2025, 3, 15),
            end_at=datetime(2025, 3, 16),
            description="March appointment",
        )
        member_request_factory(
            member_id=member.id,
            start_at=datetime(2025, 4, 20),
            end_at=datetime(2025, 4, 22),
            description="April conference",
        )

        # Act
        statement = select(MemberRequest).where(MemberRequest.member_id == member.id)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        descriptions = {r.description for r in results}
        assert descriptions == {
            "February vacation",
            "March appointment",
            "April conference",
        }

    def test_query_requests_by_member(
        self, session: Session, member_factory, member_request_factory
    ):
        """Test querying requests for a specific member."""
        # Arrange
        member1 = member_factory(name="Member 1", email="m1@example.com")
        member2 = member_factory(name="Member 2", email="m2@example.com")

        member_request_factory(member_id=member1.id, description="M1-R1")
        member_request_factory(member_id=member1.id, description="M1-R2")
        member_request_factory(member_id=member2.id, description="M2-R1")

        # Act
        statement = select(MemberRequest).where(MemberRequest.member_id == member1.id)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        descriptions = {r.description for r in results}
        assert descriptions == {"M1-R1", "M1-R2"}

    def test_delete_member_request_does_not_delete_member(
        self, session: Session, member_factory, member_request_factory
    ):
        """Test that deleting a request doesn't delete the associated member."""
        # Arrange
        member = member_factory(name="Test Member", email="test@example.com")
        request = member_request_factory(
            member_id=member.id, description="Test request"
        )

        # Act
        session.delete(request)
        session.commit()

        # Assert - member should still exist
        statement = select(Member).where(Member.id == member.id)
        result = session.exec(statement).first()
        assert result is not None
        assert result.name == "Test Member"


class TestMemberRequestConstraints:
    """Test suite for MemberRequest validation and constraints."""

    def test_member_request_requires_start_at(self, session: Session, member_factory):
        """Test that a member request requires a start time."""
        member = member_factory()
        end = datetime.now(timezone.utc) + timedelta(days=1)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(MemberRequest(end_at=end, member_id=member.id))
            session.commit()

    def test_member_request_requires_end_at(self, session: Session, member_factory):
        """Test that a member request requires an end time."""
        member = member_factory()
        start = datetime.now(timezone.utc)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(MemberRequest(start_at=start, member_id=member.id))
            session.commit()

    def test_member_request_requires_member_id(self, session: Session):
        """Test that a member request requires a member_id."""
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=1)

        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(MemberRequest(start_at=start, end_at=end))
            session.commit()

    def test_member_request_foreign_key_constraint(self, session: Session):
        """Test that member_id must reference an existing member."""
        non_existent_member_id = uuid.uuid4()
        start = datetime.now(timezone.utc)
        end = start + timedelta(days=1)

        request = MemberRequest(
            start_at=start, end_at=end, member_id=non_existent_member_id
        )
        session.add(request)
        with pytest.raises(Exception):  # Foreign key constraint
            session.commit()


class TestMemberRequestQueryPatterns:
    """Test suite for common MemberRequest query patterns."""

    def test_query_requests_by_date_range(
        self, session: Session, member_request_factory
    ):
        """Test querying member requests within a date range."""
        # Arrange
        member_request_factory(
            start_at=datetime(2025, 1, 10),
            end_at=datetime(2025, 1, 12),
            description="Early January",
        )
        member_request_factory(
            start_at=datetime(2025, 1, 20),
            end_at=datetime(2025, 1, 22),
            description="Mid January",
        )
        member_request_factory(
            start_at=datetime(2025, 2, 1),
            end_at=datetime(2025, 2, 3),
            description="Early February",
        )

        # Act - Query requests starting in January
        statement = select(MemberRequest).where(
            MemberRequest.start_at >= datetime(2025, 1, 1),
            MemberRequest.start_at < datetime(2025, 2, 1),
        )
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 2
        descriptions = {r.description for r in results}
        assert descriptions == {"Early January", "Mid January"}
