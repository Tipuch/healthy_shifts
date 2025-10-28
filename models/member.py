import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.orm import validates
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .member_request import MemberRequest


class Member(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    name: str = Field(index=True, max_length=500, nullable=False, min_length=1)
    email: str = Field(
        unique=True, index=True, max_length=500, nullable=False, min_length=5
    )
    member_group_id: uuid.UUID = Field(
        index=True, foreign_key="member_group.id", nullable=False, min_length=1
    )
    requests: list["MemberRequest"] = Relationship(back_populates="member")

    @validates("email")
    def validate_email(self, _, address):
        if "@" not in address:
            raise ValueError("failed simple email validation")
        return address
