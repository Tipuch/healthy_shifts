import uuid

from sqlmodel import SQLModel, Field, PrimaryKeyConstraint
from sqlalchemy.orm import validates


class ShiftConstraint(SQLModel, table=True):
    __tablename__ = "shift_constraint"

    shift_id: uuid.UUID = Field(foreign_key="shift.id", primary_key=True, nullable=False)
    linked_shift_id: uuid.UUID = Field(foreign_key="shift.id", primary_key=True, nullable=False)
    # 1 would prevent if member was assigned in the last linked shift,
    # 2 if member was assigned within the last 2 linked shifts etc...
    within_last_shifts: int = Field(default=1, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("shift_id", "linked_shift_id"),
    )

    @validates("within_last_shifts")
    def validate_within_last_shifts(self, _, within_last_shifts):
        if not within_last_shifts or within_last_shifts <= 0:
            raise ValueError("within_last_shifts must be greater than 0")