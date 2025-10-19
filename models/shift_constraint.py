import uuid

from sqlmodel import SQLModel, Field
from pydantic import PositiveInt


class ShiftConstraint(SQLModel, table=True):
    __tablename__ = "shift_constraint"

    shift_id: uuid.UUID = Field(foreign_key="shift.id", primary_key=True)
    linked_shift_id: uuid.UUID = Field(foreign_key="shift.id", primary_key=True)
    # 1 would prevent if member was assigned in the last linked shift,
    # 2 if member was assigned within the last 2 linked shifts etc...
    within_last_shifts: PositiveInt = Field(default=1, nullable=False)