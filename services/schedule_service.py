import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ortools.sat.python import cp_model
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select
from db import engine

from models import (
    Member,
    MemberGroupShift,
    MemberShiftScheduled,
    Shift,
    ShiftConstraint,
    ShiftScheduled,
)


MAX_HOURS_IN_2_DAYS = 32


def schedule_shifts(start: datetime, end: datetime):
    with Session(engine) as session:
        members = session.exec(
            select(Member).options(selectinload(Member.requests))
        ).all()
        shifts = session.exec(select(Shift)).all()
        shift_constraints = session.exec(select(ShiftConstraint)).all()

    members_dict = {k: member for k, member in enumerate(members)}
    all_members = members_dict.keys()

    shifts_dict = {k: shift for k, shift in enumerate(shifts)}
    all_shifts = shifts_dict.keys()
    shift_requirements = {k: shift.members_required for k, shift in shifts_dict.items()}

    num_days = (end - start).days
    days_dict = {
        k: d for k, d in enumerate([start + timedelta(days=x) for x in range(num_days)])
    }
    all_days = range(num_days)

    # Build set of (member_key, day, shift_key) where time-off requests overlap shifts
    request_overlaps: set[tuple[int, int, int]] = set()

    for member_key, member in members_dict.items():
        for request in member.requests:
            # Clip request to scheduling window
            effective_start = max(request.start_at, start)
            effective_end = min(request.end_at, end)

            # Skip if request is entirely outside window
            if effective_start >= effective_end:
                continue

            # Iterate through all days in request range
            current_date = effective_start.date()
            end_date = effective_end.date()

            while current_date <= end_date:
                # Find day index in our scheduling window
                day_key = None
                for d_idx, d_date in days_dict.items():
                    if d_date.date() == current_date:
                        day_key = d_idx
                        break

                if day_key is not None and day_key in all_days:
                    # Check each shift for overlap
                    for shift_key, shift in shifts_dict.items():
                        # Skip if shift doesn't occur on this weekday
                        if str(current_date.weekday()) not in shift.days:
                            continue

                        # Build shift datetime range for this specific day (naive datetime)
                        day_start = datetime.combine(current_date, datetime.min.time())
                        shift_start = day_start + timedelta(
                            seconds=shift.seconds_since_midnight
                        )
                        shift_end = shift_start + timedelta(
                            seconds=shift.duration_seconds
                        )

                        # Check for any overlap using interval intersection
                        if max(shift_start, effective_start) < min(
                            shift_end, effective_end
                        ):
                            request_overlaps.add((member_key, day_key, shift_key))

                current_date += timedelta(days=1)

    # Debug output to verify overlap detection
    print(f"\n🔍 Found {len(request_overlaps)} request-shift overlaps")
    if request_overlaps:
        print("Sample overlaps (member, day, shift):")
        for overlap in list(request_overlaps)[:5]:
            m, d, s = overlap
            print(
                f"  - Member: {members_dict[m].name}, Day: {d}, Shift: {shifts_dict[s].description}"
            )

    model = cp_model.CpModel()

    shifts = {}
    working_hours = {}
    for m in all_members:
        for d in all_days:
            for s in all_shifts:
                shifts[(m, d, s)] = model.new_bool_var(f"shift_m{m}_d{d}_s{s}")
                working_hours[(m, d, s)] = model.new_int_var(
                    0, 24, f"working_hours_m{m}_d{d}_s{s}"
                )

    for d in range(num_days - 1):
        for m in all_members:
            model.add(
                sum(
                    [
                        working_hours[(m, d, s)] + working_hours[(m, d + 1, s)]
                        for s in all_shifts
                    ]
                )
                <= MAX_HOURS_IN_2_DAYS
            )

    for d in all_days:
        for s in all_shifts:
            if str(days_dict[d].weekday()) in shifts_dict[s].days:
                model.add(
                    sum(shifts[(m, d, s)] for m in all_members) == shift_requirements[s]
                )
            else:
                model.add(sum(shifts[(m, d, s)] for m in all_members) == 0)

    for m in all_members:
        for shift_constraint in shift_constraints:
            from_shift_key = find_key_in_dict(shift_constraint.shift_id, shifts_dict)
            to_shift_key = find_key_in_dict(
                shift_constraint.linked_shift_id, shifts_dict
            )
            within = shift_constraint.within_last_shifts
            for d in range(num_days - within):
                if from_shift_key != to_shift_key:
                    model.add(
                        shifts[(m, d, from_shift_key)] + shifts[(m, d, to_shift_key)]
                        <= 1
                    )
                for i in range(within):
                    model.add(
                        shifts[(m, d, from_shift_key)]
                        + shifts[(m, d + i + 1, to_shift_key)]
                        <= 1
                    )

    with Session(engine) as session:
        shift_eligibility = {
            shift_key: [
                member_key
                for member_key, member in members_dict.items()
                if session.exec(
                    select(MemberGroupShift)
                    .where(MemberGroupShift.member_group_id == member.member_group_id)
                    .where(MemberGroupShift.shift_id == shift.id)
                ).first()
            ]
            for shift_key, shift in shifts_dict.items()
        }

    # Constraint: members can only work shifts they're eligible for
    for m in all_members:
        for d in all_days:
            for s in all_shifts:
                if m not in shift_eligibility[s]:
                    model.add(shifts[(m, d, s)] == 0)
                else:
                    (
                        model.add(
                            working_hours[(m, d, s)]
                            == (shifts_dict[s].duration_seconds // 3600)
                        ).only_enforce_if(shifts[(m, d, s)])
                    )

    # Soft fairness constraint: minimize the difference in shift counts
    # among members eligible for the same shift type
    fairness_penalties = []
    diffs = []
    for s in all_shifts:
        eligible_members = shift_eligibility[s]
        if len(eligible_members) > 1:
            # Count total shifts of type s each eligible member works
            member_shift_counts = {}
            for m in eligible_members:
                count_vars = []
                for d in all_days:
                    count_vars.append(shifts[(m, d, s)])
                member_shift_counts[m] = sum(count_vars)

            # Create variables for min and max shift counts among eligible members
            min_count = model.new_int_var(0, num_days, f"min_count_shift_{s}")
            max_count = model.new_int_var(0, num_days, f"max_count_shift_{s}")

            for m in eligible_members:
                model.add(min_count <= member_shift_counts[m])
                model.add(max_count >= member_shift_counts[m])

            # Create penalty variable for the difference
            diff = model.new_int_var(0, num_days, f"diff_shift_{s}")
            diffs.append(diff)
            model.add(diff == max_count - min_count)
            fairness_penalties.append(diff)

    # Minimize the total fairness penalty
    model.minimize(sum(fairness_penalties))

    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 1

    # Phase 1: Solve for minimizing fairness penalties
    status = solver.solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Add hints from Phase 1 solution for all shift assignment variables
        for m in all_members:
            for d in all_days:
                for s in all_shifts:
                    model.add_hint(shifts[(m, d, s)], solver.value(shifts[(m, d, s)]))

        # Hint fairness penalty variables
        for diff in diffs:
            model.add_hint(diff, solver.value(diff))

        # Lock in fairness objective as constraint
        model.add(sum(fairness_penalties) <= round(solver.objective_value))

        # Phase 2: Minimize scheduling members during time-off requests
        # Use pre-computed overlap set for accurate time-of-day overlap detection
        request_violations = []
        for m, d, s in request_overlaps:
            violation = model.new_bool_var(f"request_violation_m{m}_d{d}_s{s}")
            request_violations.append(violation)
            model.add(violation == shifts[(m, d, s)])

        print(
            f"\n📊 Phase 2: Minimizing {len(request_violations)} potential request violations"
        )
        model.minimize(sum(request_violations))
        status2 = solver.solve(model)

        if status2 == cp_model.OPTIMAL or status2 == cp_model.FEASIBLE:
            print("\n✓ Solution found!")
            return solver, shifts, members_dict, shifts_dict, days_dict
        else:
            print("❌ No solution found in phase 2.")
            return None, None, None, None, None
    else:
        print("❌ No solution found in phase 1.")
        return None, None, None, None, None


def save_schedule(
    solver,
    shifts,
    members_dict: dict[int, Member],
    shifts_dict: dict[int, Shift],
    days_dict: dict[int, datetime],
):
    """
    Save the scheduling solution to the database.

    Creates ShiftScheduled instances and MemberShiftScheduled assignments
    based on the solver's solution.
    """
    with Session(engine) as session:
        # Track created ShiftScheduled instances by (day, shift) to avoid duplicates
        scheduled_shifts_cache = {}
        member_assignments = 0

        # Iterate through all possible assignments
        for (m, d, s), var in shifts.items():
            if solver.value(var) == 1:
                member = members_dict[m]
                shift = shifts_dict[s]
                day_start = days_dict[d]

                # Create unique key for this scheduled shift instance
                cache_key = (d, s)

                # Create ShiftScheduled if not already created for this day/shift
                if cache_key not in scheduled_shifts_cache:
                    # Calculate start and end times
                    shift_start = day_start + timedelta(
                        seconds=shift.seconds_since_midnight
                    )
                    shift_end = shift_start + timedelta(seconds=shift.duration_seconds)

                    # Create ShiftScheduled instance
                    scheduled_shift = ShiftScheduled(
                        start_at=shift_start,
                        end_at=shift_end,
                        description=shift.description,
                        shift_id=shift.id,
                    )
                    session.add(scheduled_shift)
                    session.flush()  # Get the ID assigned

                    scheduled_shifts_cache[cache_key] = scheduled_shift
                else:
                    scheduled_shift = scheduled_shifts_cache[cache_key]

                # Create member assignment
                assignment = MemberShiftScheduled(
                    member_id=member.id,
                    shift_scheduled_id=scheduled_shift.id,
                )
                session.add(assignment)
                member_assignments += 1

        session.commit()

        print(f"\n✓ Created {len(scheduled_shifts_cache)} ShiftScheduled instances")
        print(f"✓ Created {member_assignments} member assignments")


def find_key_in_dict(obj_id: uuid.UUID, model_dict: dict[int, Member | Shift]) -> int:
    for k, obj in model_dict.items():
        if obj.id == obj_id:
            return k
    raise ValueError("No such object")


def _generate_ics_content(
    events: list[tuple[ShiftScheduled, str, str]],
) -> str:
    """
    Generate ICS calendar content from a list of events.

    Args:
        events: List of tuples (shift, uid_suffix, summary)
            - shift: ShiftScheduled instance
            - uid_suffix: Unique identifier suffix for the event
            - summary: Event summary/title

    Returns:
        ICS formatted calendar content as string
    """
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Healthy Shifts//Schedule Export//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for shift, uid_suffix, summary in events:
        # Format as floating time (no timezone - displays in user's local timezone)
        dtstart = shift.start_at.replace(tzinfo=None).strftime("%Y%m%dT%H%M%S")
        dtend = shift.end_at.replace(tzinfo=None).strftime("%Y%m%dT%H%M%S")

        ics_lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid_suffix}@healthyshifts.local",
                f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{summary}",
                "END:VEVENT",
            ]
        )

    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines) + "\r\n"


def export_member_ics(
    session: Session,
    member_id: uuid.UUID,
    start: datetime,
    end: datetime,
    output_dir: str,
) -> None:
    """
    Export scheduled shifts for a single member to an ICS file.

    Args:
        session: Database session
        member_id: UUID of the member
        start: Start date for filtering shifts (inclusive)
        end: End date for filtering shifts (exclusive)
        output_dir: Directory to write the ICS file
    """
    # Get member
    member = session.exec(select(Member).where(Member.id == member_id)).first()
    if not member:
        raise ValueError(f"Member with id {member_id} not found")

    # Query scheduled shifts for this member within date range
    query = (
        select(ShiftScheduled)
        .join(
            MemberShiftScheduled,
            ShiftScheduled.id == MemberShiftScheduled.shift_scheduled_id,
        )
        .where(MemberShiftScheduled.member_id == member_id)
        .where(ShiftScheduled.start_at >= start)
        .where(ShiftScheduled.start_at < end)
        .order_by(ShiftScheduled.start_at)
    )

    shifts = session.exec(query).all()

    # Prepare events for ICS generation
    events = [(shift, str(shift.id), shift.description) for shift in shifts]

    # Generate ICS content using shared helper
    ics_content = _generate_ics_content(events)

    # Write to file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ics_file = output_path / f"{member.email}.ics"
    # Write in binary mode to ensure CRLF line endings are preserved across platforms
    ics_file.write_bytes(ics_content.encode("utf-8"))


def export_all_members_ics(
    session: Session,
    start: datetime,
    end: datetime,
    output_dir: str,
) -> None:
    """
    Export scheduled shifts for all members to ICS files.

    Creates one ICS file per member and one global ICS file with all shifts.

    Args:
        session: Database session
        start: Start date for filtering shifts (inclusive)
        end: End date for filtering shifts (exclusive)
        output_dir: Directory to write the ICS files
    """
    # Get all members
    members = session.exec(select(Member)).all()

    # Export individual files for each member
    for member in members:
        export_member_ics(session, member.id, start, end, output_dir)

    # Create global ICS file with all shifts for all members
    query = (
        select(ShiftScheduled, Member)
        .join(
            MemberShiftScheduled,
            ShiftScheduled.id == MemberShiftScheduled.shift_scheduled_id,
        )
        .join(Member, MemberShiftScheduled.member_id == Member.id)
        .where(ShiftScheduled.start_at >= start)
        .where(ShiftScheduled.start_at < end)
        .order_by(ShiftScheduled.start_at)
    )

    results = session.exec(query).all()

    # Prepare events for ICS generation (global file with member names)
    events = [
        (shift, f"{shift.id}-{member.id}", f"{shift.description} - {member.name}")
        for shift, member in results
    ]

    # Generate ICS content using shared helper
    ics_content = _generate_ics_content(events)

    # Write global file
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    ics_file = output_path / "all_members.ics"
    # Write in binary mode to ensure CRLF line endings are preserved across platforms
    ics_file.write_bytes(ics_content.encode("utf-8"))
