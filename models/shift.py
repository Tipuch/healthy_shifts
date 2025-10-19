import uuid
from datetime import datetime, timezone

from pydantic.v1 import NonNegativeInt, PositiveInt
from sqlmodel import SQLModel, Field, Column, JSON


class Shift(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default=datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), nullable=False
    )
    seconds_since_midnight: NonNegativeInt = Field(default=0, nullable=False)
    duration_seconds: PositiveInt = Field(default=3600, nullable=False)
    # 0 Sunday -> 6 Saturday
    days: list[str] = Field(default_factory=list, sa_column=Column(JSON), nullable=False)
    description: str = Field(default='', nullable=False)