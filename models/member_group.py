import uuid
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class MemberGroup(SQLModel, table=True):
    __tablename__ = "member_group"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    name: str = Field(index=True, max_length=500, nullable=False, min_length=1)
