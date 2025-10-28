import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session, validates
from sqlmodel import Field, Relationship, SQLModel, select

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

    def display_schedule(
        self,
        session: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        """
        Display this member's scheduled shifts in a formatted, grouped-by-date view.

        Args:
            session: Database session for querying
            start_date: Optional start date filter (inclusive)
            end_date: Optional end date filter (exclusive)

        Returns:
            Formatted string showing shifts grouped by date with 24-hour times
        """
        from .shift_scheduled import MemberShiftScheduled, ShiftScheduled

        # Query all scheduled shifts for this member
        query = (
            select(ShiftScheduled)
            .join(
                MemberShiftScheduled,
                ShiftScheduled.id == MemberShiftScheduled.shift_scheduled_id,
            )
            .where(MemberShiftScheduled.member_id == self.id)
        )

        # Apply date filters if provided
        if start_date:
            query = query.where(ShiftScheduled.start_at >= start_date)
        if end_date:
            query = query.where(ShiftScheduled.start_at < end_date)

        # Order by start time
        query = query.order_by(ShiftScheduled.start_at)

        scheduled_shifts = session.exec(query).all()

        if not scheduled_shifts:
            return f"No scheduled shifts found for {self.name}"

        # Group shifts by date
        from collections import defaultdict

        shifts_by_date = defaultdict(list)
        for shift in scheduled_shifts:
            date_key = shift.start_at.date()
            shifts_by_date[date_key].append(shift)

        # Build output string
        output = []
        output.append(f"\nSchedule for {self.name}")
        output.append("=" * 80)

        for date in sorted(shifts_by_date.keys()):
            # Format: 2025-01-15 Wednesday
            weekday = date.strftime("%A")
            output.append(f"\n{date} {weekday}")

            for shift in shifts_by_date[date]:
                # Format times in 24-hour format
                start_time = shift.start_at.strftime("%H:%M")
                end_time = shift.end_at.strftime("%H:%M")

                # Check if shift spans to next day
                if shift.end_at.date() > shift.start_at.date():
                    end_time += " (next day)"

                output.append(f"  {start_time} - {end_time} | {shift.description}")

        output.append("")
        return "\n".join(output)
