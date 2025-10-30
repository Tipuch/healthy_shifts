import uuid

from sqlalchemy.orm import validates
from sqlmodel import Field, PrimaryKeyConstraint, SQLModel


class ShiftConstraint(SQLModel, table=True):
    __tablename__ = "shift_constraint"

    shift_id: uuid.UUID = Field(
        foreign_key="shift.id", primary_key=True, nullable=False
    )
    linked_shift_id: uuid.UUID = Field(
        foreign_key="shift.id", primary_key=True, nullable=False
    )
    # 1 would prevent if member was assigned in the last linked shift,
    # 2 if member was assigned within the last 2 linked shifts etc...
    # if value is 0 then we prevent assignment to both shifts in the same day.
    within_last_shifts: int = Field(default=1, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("shift_id", "linked_shift_id"),)

    @validates("within_last_shifts")
    def validate_within_last_shifts(self, _, within_last_shifts):
        if within_last_shifts is None or within_last_shifts < 0:
            raise ValueError("within_last_shifts must be 0 or greater")

    @staticmethod
    def _shifts_overlap_on_day(
        start_a: int, duration_a: int, start_b: int, duration_b: int
    ) -> bool:
        """
        Check if two shifts overlap on the same day based on time ranges.

        Args:
            start_a: seconds_since_midnight for shift A
            duration_a: duration_seconds for shift A
            start_b: seconds_since_midnight for shift B
            duration_b: duration_seconds for shift B

        Returns:
            True if the time ranges overlap, False otherwise
        """
        end_a = start_a + duration_a
        end_b = start_b + duration_b

        # Overlaps if: start of one is before end of other AND vice versa
        # Equivalent to: max(start_a, start_b) < min(end_a, end_b)
        return max(start_a, start_b) < min(end_a, end_b)

    @staticmethod
    def _check_cross_day_overlap(
        start_a: int, duration_a: int, start_b: int, day_a: int, day_b: int
    ) -> tuple[bool, bool]:
        """
        Check if shift A crosses midnight and overlaps with shift B on the next day.

        Args:
            start_a: seconds_since_midnight for shift A
            duration_a: duration_seconds for shift A
            start_b: seconds_since_midnight for shift B
            day_a: weekday for shift A (0=Sunday, 6=Saturday)
            day_b: weekday for shift B

        Returns:
            Tuple of (crosses_midnight, overlaps_next_day_shift)
        """
        end_a = start_a + duration_a
        crosses_midnight = end_a > 86400

        if not crosses_midnight:
            return False, False

        # Check if day_b is the next day after day_a
        next_day = (day_a + 1) % 7
        if day_b != next_day:
            return True, False

        # Calculate spillover time into next day
        spillover_end = end_a - 86400

        # Shift B overlaps if it starts before spillover ends
        overlaps = start_b < spillover_end

        return True, overlaps

    @classmethod
    def generate_from_overlaps(cls, session) -> dict[str, int]:
        """
        Analyze all Shift templates and automatically generate ShiftConstraint records
        for overlapping shifts.

        Args:
            session: SQLModel database session

        Returns:
            Dictionary with counts: {"created": X, "updated": Y, "unchanged": Z}
        """
        from sqlmodel import select
        from .shift import Shift

        # Initialize counters
        created_count = 0
        updated_count = 0
        unchanged_count = 0

        # Fetch all shifts
        shifts = session.exec(select(Shift)).all()

        # Collect detected constraints: (shift_id, linked_shift_id, within_last_shifts)
        detected_constraints: set[tuple] = set()

        # Iterate through all unique pairs of shifts
        for i, shift_a in enumerate(shifts):
            for shift_b in shifts[i + 1 :]:
                # Check for same-day overlaps
                common_days = set(shift_a.days) & set(shift_b.days)

                for _ in common_days:
                    if cls._shifts_overlap_on_day(
                        shift_a.seconds_since_midnight,
                        shift_a.duration_seconds,
                        shift_b.seconds_since_midnight,
                        shift_b.duration_seconds,
                    ):
                        # Same-day overlap: bidirectional with within_last_shifts=0
                        detected_constraints.add((shift_a.id, shift_b.id, 0))
                        detected_constraints.add((shift_b.id, shift_a.id, 0))
                        break  # Only need to detect once per pair

                # Check for cross-day overlaps (shift A into shift B)
                for day_a_str in shift_a.days:
                    day_a = int(day_a_str)
                    for day_b_str in shift_b.days:
                        day_b = int(day_b_str)

                        crosses, overlaps = cls._check_cross_day_overlap(
                            shift_a.seconds_since_midnight,
                            shift_a.duration_seconds,
                            shift_b.seconds_since_midnight,
                            day_a,
                            day_b,
                        )

                        if crosses and overlaps:
                            # Cross-day overlap: unidirectional A -> B with within_last_shifts=1
                            detected_constraints.add((shift_a.id, shift_b.id, 1))

                # Check for cross-day overlaps (shift B into shift A)
                for day_b_str in shift_b.days:
                    day_b = int(day_b_str)
                    for day_a_str in shift_a.days:
                        day_a = int(day_a_str)

                        crosses, overlaps = cls._check_cross_day_overlap(
                            shift_b.seconds_since_midnight,
                            shift_b.duration_seconds,
                            shift_a.seconds_since_midnight,
                            day_b,
                            day_a,
                        )

                        if crosses and overlaps:
                            # Cross-day overlap: unidirectional B -> A with within_last_shifts=1
                            detected_constraints.add((shift_b.id, shift_a.id, 1))

        # Fetch existing constraints
        existing_constraints = {}
        for constraint in session.exec(select(cls)).all():
            key = (constraint.shift_id, constraint.linked_shift_id)
            existing_constraints[key] = constraint

        # Process detected constraints
        for shift_id, linked_shift_id, within_last in detected_constraints:
            key = (shift_id, linked_shift_id)

            if key in existing_constraints:
                existing = existing_constraints[key]
                if existing.within_last_shifts != within_last:
                    existing.within_last_shifts = within_last
                    session.add(existing)
                    updated_count += 1
                else:
                    unchanged_count += 1
            else:
                new_constraint = cls(
                    shift_id=shift_id,
                    linked_shift_id=linked_shift_id,
                    within_last_shifts=within_last,
                )
                session.add(new_constraint)
                created_count += 1

        session.commit()

        return {
            "created": created_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
        }
