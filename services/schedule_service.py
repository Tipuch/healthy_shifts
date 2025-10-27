import uuid
from datetime import datetime, timedelta
from sqlmodel import select
from sqlalchemy.orm import selectinload
from models import Member, Shift, ShiftConstraint, MemberGroupShift
from db import Session, engine
from ortools.sat.python import cp_model


def schedule_shifts(start: datetime, end: datetime):
    with Session(engine) as session:
        members = session.exec(select(Member).options(selectinload(Member.requests))).all()
        shifts = session.exec(select(Shift)).all()
        shift_constraints = session.exec(select(ShiftConstraint)).all()

    members_dict = {k: member for k, member in enumerate(members)}
    all_members = members_dict.keys()

    shifts_dict = {k: shift for k, shift in enumerate(shifts)}
    all_shifts = shifts_dict.keys()
    shift_requirements = {k: shift.members_required for k, shift in shifts_dict.items()}

    num_days = (end - start).days
    days_dict = {k: d for k, d in enumerate([start + timedelta(days=x) for x in range(num_days)])}
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
                        shift_start = day_start + timedelta(seconds=shift.seconds_since_midnight)
                        shift_end = shift_start + timedelta(seconds=shift.duration_seconds)

                        # Check for any overlap using interval intersection
                        if max(shift_start, effective_start) < min(shift_end, effective_end):
                            request_overlaps.add((member_key, day_key, shift_key))

                current_date += timedelta(days=1)

    # Debug output to verify overlap detection
    print(f"\n🔍 Found {len(request_overlaps)} request-shift overlaps")
    if request_overlaps:
        print("Sample overlaps (member, day, shift):")
        for overlap in list(request_overlaps)[:5]:
            m, d, s = overlap
            print(f"  - Member: {members_dict[m].name}, Day: {d}, Shift: {shifts_dict[s].description}")

    model = cp_model.CpModel()

    shifts = {}
    for m in all_members:
        for d in all_days:
            for s in all_shifts:
                shifts[(m, d, s)] = model.new_bool_var(f"shift_m{m}_d{d}_s{s}")


    for d in all_days:
        for s in all_shifts:
            if str((days_dict[d].weekday() + 1) % 7) in shifts_dict[s].days:
                model.add(
                    sum(shifts[(m, d, s)] for m in all_members) == shift_requirements[s]
                )

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
                        shifts[(m, d, from_shift_key)]
                        + shifts[(m, d, to_shift_key)]
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
        for (m, d, s) in request_overlaps:
            violation = model.new_bool_var(f"request_violation_m{m}_d{d}_s{s}")
            request_violations.append(violation)
            model.add(violation == shifts[(m, d, s)])

        print(f"\n📊 Phase 2: Minimizing {len(request_violations)} potential request violations")
        model.minimize(sum(request_violations))
        status2 = solver.solve(model)

        if status2 == cp_model.OPTIMAL or status2 == cp_model.FEASIBLE:
            print("\n✓ Solution found!")
            print("=" * 80)

            # Filter for a specific member
            filter_member_name = "Dr. Sarah Johnson"
            print(f"\n🔍 Showing schedule for: {filter_member_name}")
            print("=" * 80)

            for d in all_days:
                day_has_shifts = False
                shift_output = []

                # Collect shifts for filtered member on this day
                for s in all_shifts:
                    shift = shifts_dict[s]
                    for m in all_members:
                        if members_dict[m].name == filter_member_name and solver.value(shifts[(m, d, s)]):
                            shift_output.append(f"  • {shift.description}")
                            day_has_shifts = True

                # Only print day if the member has shifts
                if day_has_shifts:
                    print(f"\n📅 Day {d + 1}")
                    print("-" * 80)
                    for shift_line in shift_output:
                        print(shift_line)

            # Print statistics: shifts per member per category
            print("\n" + "=" * 80)
            print("📊 Shift Statistics by Member")
            print("=" * 80)

            for m in all_members:
                member = members_dict[m]
                shift_counts = {}
                for s in all_shifts:
                    count = sum(solver.value(shifts[(m, d, s)]) for d in all_days)
                    shift_counts[s] = count

                total = sum(shift_counts.values())

                # Build a readable shift breakdown
                shift_breakdown = []
                for s in all_shifts:
                    shift_name = shifts_dict[s].description.replace(" Shift", "")
                    shift_breakdown.append(f"{shift_name}: {shift_counts[s]}")

                shift_details = ", ".join(shift_breakdown)
                print(f"{member.name}: {shift_details} | Total: {total}")
        else:
            print("❌ No solution found in phase 2.")
    else:
        print("❌ No solution found in phase 1.")


def find_key_in_dict(obj_id: uuid.UUID, model_dict: dict[int, Member | Shift]) -> int:
    for k, obj in model_dict.items():
        if obj.id == obj_id:
            return k
    raise ValueError("No such object")
