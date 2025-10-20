import uuid
from datetime import datetime, timezone

from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy.orm import validates


class Shift(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    seconds_since_midnight: int = Field(default=0, nullable=False)
    duration_seconds: int = Field(default=3600, nullable=False)
    # 0 Sunday -> 6 Saturday
    days: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    description: str = Field(default='', nullable=False)

    @validates("duration_seconds")
    def validate_duration_seconds(self, _, duration_seconds):
        if not duration_seconds or duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")

    @validates("seconds_since_midnight")
    def validate_seconds_since_midnight(self, _, seconds_since_midnight):
        if seconds_since_midnight is None or seconds_since_midnight < 0 or seconds_since_midnight > 86400:
            raise ValueError("seconds_since_midnight must be between 0 and 86400")