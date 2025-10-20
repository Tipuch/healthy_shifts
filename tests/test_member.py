"""
Tests for Member model CRUD operations and relationships.
"""

import uuid
from datetime import datetime

import pytest
from sqlmodel import Session, select

from models import Member


class TestMemberCRUD:
    """Test suite for Member Create, Read, Update, Delete operations."""

    def test_create_member(self, session: Session, member_group_factory):
        """Test creating a new member."""
        # Arrange
        member_group = member_group_factory(name="Engineering")

        # Act
        member = Member(
            name="John Doe",
            email="john.doe@example.com",
            member_group_id=member_group.id
        )
        session.add(member)
        session.commit()
        session.refresh(member)

        # Assert
        assert member.id is not None
        assert isinstance(member.id, uuid.UUID)
        assert member.name == "John Doe"
        assert member.email == "john.doe@example.com"
        assert member.member_group_id == member_group.id
        assert isinstance(member.created_at, datetime)
        assert isinstance(member.updated_at, datetime)

    def test_create_member_with_factory(self, member_factory):
        """Test creating a member using the factory fixture."""
        # Act
        member = member_factory(name="Jane Smith", email="jane@example.com")

        # Assert
        assert member.id is not None
        assert member.name == "Jane Smith"
        assert member.email == "jane@example.com"
        assert member.member_group_id is not None

    def test_read_member(self, session: Session, member_factory):
        """Test reading a member from the database."""
        # Arrange
        created_member = member_factory(name="Alice Brown", email="alice@example.com")

        # Act
        statement = select(Member).where(Member.id == created_member.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.id == created_member.id
        assert result.name == "Alice Brown"
        assert result.email == "alice@example.com"

    def test_read_all_members(self, session: Session, member_factory):
        """Test reading multiple members."""
        # Arrange
        member_factory(name="Member 1", email="m1@example.com")
        member_factory(name="Member 2", email="m2@example.com")
        member_factory(name="Member 3", email="m3@example.com")

        # Act
        statement = select(Member)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        member_emails = {member.email for member in results}
        assert member_emails == {"m1@example.com", "m2@example.com", "m3@example.com"}

    def test_update_member(self, session: Session, member_factory):
        """Test updating a member's information."""
        # Arrange
        member = member_factory(name="Old Name", email="old@example.com")
        original_id = member.id
        original_created_at = member.created_at

        # Act
        member.name = "New Name"
        member.email = "new@example.com"
        session.add(member)
        session.commit()
        session.refresh(member)

        # Assert
        assert member.id == original_id
        assert member.name == "New Name"
        assert member.email == "new@example.com"
        assert member.created_at == original_created_at

    def test_delete_member(self, session: Session, member_factory):
        """Test deleting a member."""
        # Arrange
        member = member_factory(name="To Delete", email="delete@example.com")
        member_id = member.id

        # Act
        session.delete(member)
        session.commit()

        # Assert
        statement = select(Member).where(Member.id == member_id)
        result = session.exec(statement).first()
        assert result is None


class TestMemberRelationships:
    """Test suite for Member relationships with other models."""

    def test_member_belongs_to_member_group(self, session: Session, member_group_factory, member_factory):
        """Test that a member is associated with a member group."""
        # Arrange
        member_group = member_group_factory(name="Sales Team")
        member = member_factory(
            name="Sales Person",
            email="sales@example.com",
            member_group_id=member_group.id
        )

        # Act
        statement = select(Member).where(Member.id == member.id)
        retrieved_member = session.exec(statement).first()

        # Assert
        assert retrieved_member is not None
        assert retrieved_member.member_group_id == member_group.id

    def test_member_group_can_have_multiple_members(self, session: Session, member_group_factory, member_factory):
        """Test that a member group can have multiple members."""
        # Arrange
        member_group = member_group_factory(name="Development Team")
        member_factory(name="Dev 1", email="dev1@example.com", member_group_id=member_group.id)
        member_factory(name="Dev 2", email="dev2@example.com", member_group_id=member_group.id)
        member_factory(name="Dev 3", email="dev3@example.com", member_group_id=member_group.id)

        # Act
        statement = select(Member).where(Member.member_group_id == member_group.id)
        members = session.exec(statement).all()

        # Assert
        assert len(members) == 3
        member_names = {member.name for member in members}
        assert member_names == {"Dev 1", "Dev 2", "Dev 3"}

    def test_query_members_by_group(self, session: Session, member_group_factory, member_factory):
        """Test querying members by their member group."""
        # Arrange
        group1 = member_group_factory(name="Group 1")
        group2 = member_group_factory(name="Group 2")

        member_factory(name="Member 1", email="m1@example.com", member_group_id=group1.id)
        member_factory(name="Member 2", email="m2@example.com", member_group_id=group1.id)
        member_factory(name="Member 3", email="m3@example.com", member_group_id=group2.id)

        # Act
        statement = select(Member).where(Member.member_group_id == group1.id)
        group1_members = session.exec(statement).all()

        # Assert
        assert len(group1_members) == 2
        assert all(m.member_group_id == group1.id for m in group1_members)


class TestMemberConstraints:
    """Test suite for Member validation and constraints."""

    def test_member_email_must_be_unique(self, session: Session, member_group_factory):
        """Test that member emails must be unique."""
        # Arrange
        member_group = member_group_factory(name="Test Group")
        member1 = Member(
            name="Member 1",
            email="duplicate@example.com",
            member_group_id=member_group.id
        )
        session.add(member1)
        session.commit()

        # Act & Assert
        member2 = Member(
            name="Member 2",
            email="duplicate@example.com",
            member_group_id=member_group.id
        )
        session.add(member2)
        with pytest.raises(Exception):  # SQLite IntegrityError
            session.commit()

    def test_member_requires_name(self, session: Session, member_group_factory):
        """Test that a member requires a name field."""
        # Arrange
        member_group = member_group_factory(name="Test Group")

        # Act & Assert
        with pytest.raises(Exception):
            session.add(Member(email="test@example.com", member_group_id=member_group.id))
            session.commit()


    def test_member_requires_email(self, session: Session, member_group_factory):
        """Test that a member requires an email field."""
        # Arrange
        member_group = member_group_factory(name="Test Group")

        # Act & Assert
        with pytest.raises(Exception):
            session.add(Member(name="Test Member", member_group_id=member_group.id))
            session.commit()

    def test_member_validates_email(self, session: Session, member_group_factory):
        """Test that a member requires an email field."""
        # Arrange
        member_group = member_group_factory(name="Test Group")

        # Act & Assert
        with pytest.raises(Exception):
            session.add(Member(name="Test Member", email="testexample.com", member_group_id=member_group.id))
            session.commit()

    def test_member_requires_member_group_id(self, session: Session):
        """Test that a member requires a member_group_id."""
        # Act & Assert
        with pytest.raises(Exception):
            session.add(Member(name="Test Member", email="test@example.com"))
            session.commit()

    def test_member_foreign_key_constraint(self, session: Session):
        """Test that member_group_id must reference an existing member group."""
        # Arrange
        non_existent_group_id = uuid.uuid4()

        # Act & Assert
        member = Member(
            name="Test Member",
            email="test@example.com",
            member_group_id=non_existent_group_id
        )
        session.add(member)
        with pytest.raises(Exception):  # Foreign key constraint violation
            session.commit()
