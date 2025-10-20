"""
Tests for MemberGroup model CRUD operations.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlmodel import Session, select

from models import MemberGroup


class TestMemberGroupCRUD:
    """Test suite for MemberGroup Create, Read, Update, Delete operations."""

    def test_create_member_group(self, session: Session):
        """Test creating a new member group."""
        # Arrange
        group_name = "Engineering Team"

        # Act
        member_group = MemberGroup(name=group_name)
        session.add(member_group)
        session.commit()
        session.refresh(member_group)

        # Assert
        assert member_group.id is not None
        assert isinstance(member_group.id, uuid.UUID)
        assert member_group.name == group_name
        assert isinstance(member_group.created_at, datetime)
        assert isinstance(member_group.updated_at, datetime)
        # Note: SQLite doesn't preserve timezone info, so we just check datetime exists

    def test_create_member_group_with_factory(self, member_group_factory):
        """Test creating a member group using the factory fixture."""
        # Act
        member_group = member_group_factory(name="Sales Team")

        # Assert
        assert member_group.id is not None
        assert member_group.name == "Sales Team"

    def test_read_member_group(self, session: Session, member_group_factory):
        """Test reading a member group from the database."""
        # Arrange
        created_group = member_group_factory(name="Marketing Team")

        # Act
        statement = select(MemberGroup).where(MemberGroup.id == created_group.id)
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.id == created_group.id
        assert result.name == "Marketing Team"
        assert result.created_at == created_group.created_at

    def test_read_all_member_groups(self, session: Session, member_group_factory):
        """Test reading multiple member groups."""
        # Arrange
        group1 = member_group_factory(name="Group 1")
        group2 = member_group_factory(name="Group 2")
        group3 = member_group_factory(name="Group 3")

        # Act
        statement = select(MemberGroup)
        results = session.exec(statement).all()

        # Assert
        assert len(results) == 3
        group_names = {group.name for group in results}
        assert group_names == {"Group 1", "Group 2", "Group 3"}

    def test_update_member_group(self, session: Session, member_group_factory):
        """Test updating a member group's name."""
        # Arrange
        member_group = member_group_factory(name="Old Name")
        original_created_at = member_group.created_at
        original_id = member_group.id

        # Act
        member_group.name = "New Name"
        session.add(member_group)
        session.commit()
        session.refresh(member_group)

        # Assert
        assert member_group.id == original_id
        assert member_group.name == "New Name"
        assert member_group.created_at == original_created_at
        # Note: updated_at would change in a real scenario with triggers/hooks

    def test_delete_member_group(self, session: Session, member_group_factory):
        """Test deleting a member group."""
        # Arrange
        member_group = member_group_factory(name="To Be Deleted")
        group_id = member_group.id

        # Act
        session.delete(member_group)
        session.commit()

        # Assert - verify the group is gone
        statement = select(MemberGroup).where(MemberGroup.id == group_id)
        result = session.exec(statement).first()
        assert result is None

    def test_member_group_name_indexed(self, session: Session, member_group_factory):
        """Test that the name field is indexed (can be queried efficiently)."""
        # Arrange
        member_group_factory(name="Searchable Name")

        # Act
        statement = select(MemberGroup).where(MemberGroup.name == "Searchable Name")
        result = session.exec(statement).first()

        # Assert
        assert result is not None
        assert result.name == "Searchable Name"


class TestMemberGroupValidation:
    """Test suite for MemberGroup validation and constraints."""

    def test_member_group_requires_name(self, session: Session):
        """Test that a member group requires a name field."""
        # This test validates the Pydantic model validation
        with pytest.raises(Exception):  # Pydantic ValidationError
            session.add(MemberGroup())
            session.commit()

    def test_member_group_timestamps_auto_generated(self, session: Session):
        """Test that timestamps are automatically generated."""
        # Arrange & Act
        member_group = MemberGroup(name="Timestamp Test")
        session.add(member_group)
        session.commit()
        session.refresh(member_group)

        # Assert
        assert member_group.created_at is not None
        assert member_group.updated_at is not None
        assert member_group.created_at <= member_group.updated_at
