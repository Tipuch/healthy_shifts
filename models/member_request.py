import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class MemberRequest(SQLModel, table=True):
    __tablename__ = "member_request"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    start_at: datetime = Field(nullable=False)
    end_at: datetime = Field(nullable=False)
    description: str = Field(default='', nullable=False)
    member_id: uuid.UUID = Field(index=True, foreign_key="member.id", nullable=False, min_length=1)
