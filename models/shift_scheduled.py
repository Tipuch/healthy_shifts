import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Relationship


class MemberShiftScheduled(SQLModel, table=True):
    __tablename__ = "member_shift_scheduled"

    member_id: uuid.UUID = Field(foreign_key="member.id", primary_key=True)
    shift_scheduled_id: uuid.UUID = Field(foreign_key="shift_scheduled.id", primary_key=True)


class ShiftScheduled(SQLModel, table=True):
    __tablename__ = "shift_scheduled"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    start_at: datetime = Field(nullable=False)
    end_at: datetime = Field(nullable=False)
    description: str = Field(default='', nullable=False)
    shift_id: uuid.UUID = Field(index=True, foreign_key="shift.id", nullable=False)
    member_ids: list["Member"] = Relationship(back_populates="shifts_scheduled", link_model=MemberShiftScheduled)
