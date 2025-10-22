import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel, PrimaryKeyConstraint


if TYPE_CHECKING:
    from models import Shift


class MemberGroupShift(SQLModel, table=True):
    __tablename__ = "member_group_shift"

    member_group_id: uuid.UUID = Field(
        foreign_key="member_group.id", primary_key=True, nullable=False
    )
    shift_id: uuid.UUID = Field(
        foreign_key="shift.id", primary_key=True, nullable=False
    )

    __table_args__ = (PrimaryKeyConstraint("member_group_id", "shift_id"),)


class MemberGroup(SQLModel, table=True):
    __tablename__ = "member_group"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    name: str = Field(index=True, max_length=500, nullable=False, min_length=1)

    shifts: list["Shift"] = Relationship(
        back_populates="member_groups", link_model=MemberGroupShift
    )
