import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field


class Member(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    name: str = Field(index=True, max_length=500, nullable=False)
    email: str = Field(unique=True, max_length=500, nullable=False)
    member_group_id: uuid.UUID = Field(index=True, foreign_key="member_group.id", nullable=False)
