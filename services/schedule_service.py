import uuid
from datetime import datetime
from sqlmodel import select
from models import Member, Shift, ShiftConstraint, MemberGroupShift
from db import Session, engine
from ortools.sat.python import cp_model


def schedule_shifts(start: datetime, end: datetime):
    with Session(engine) as session:
        members = session.exec(select(Member)).all()
        shifts = session.exec(select(Shift)).all()
        shift_constraints = session.exec(select(ShiftConstraint)).all()

    members_dict = {k: member for k, member in enumerate(members)}
    all_members = members_dict.keys()

    shifts_dict = {k: shift for k, shift in enumerate(shifts)}
    print(shifts_dict)
    all_shifts = shifts_dict.keys()
    shift_requirements = {k: shift.members_required for k, shift in shifts_dict.items()}

    num_days = (end - start).days
    all_days = range(num_days)

    model = cp_model.CpModel()

    shifts = {}
    for n in all_members:
        for d in all_days:
            for s in all_shifts:
                shifts[(n, d, s)] = model.new_bool_var(f"shift_n{n}_d{d}_s{s}")

    for d in all_days:
        for s in all_shifts:
            model.add(
                sum(shifts[(n, d, s)] for n in all_members) == shift_requirements[s]
            )

    for n in all_members:
        for shift_constraint in shift_constraints:
            from_shift_key = find_key_in_dict(shift_constraint.shift_id, shifts_dict)
            to_shift_key = find_key_in_dict(
                shift_constraint.linked_shift_id, shifts_dict
            )
            within = shift_constraint.within_last_shifts
            for d in range(num_days - within):
                for i in range(within):
                    model.add(
                        shifts[(n, d, from_shift_key)]
                        + shifts[(n, d + i + 1, to_shift_key)]
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
    for n in all_members:
        for d in all_days:
            for s in all_shifts:
                if n not in shift_eligibility[s]:
                    model.add(shifts[(n, d, s)] == 0)

    # Soft fairness constraint: minimize the difference in shift counts
    # among members eligible for the same shift type
    fairness_penalties = []

    for s in all_shifts:
        eligible_members = shift_eligibility[s]
        if len(eligible_members) > 1:
            # Count total shifts of type s each eligible member works
            member_shift_counts = {}
            for n in eligible_members:
                count_vars = []
                for d in all_days:
                    count_vars.append(shifts[(n, d, s)])
                member_shift_counts[n] = sum(count_vars)

            # Create variables for min and max shift counts among eligible members
            min_count = model.new_int_var(0, num_days, f"min_count_shift_{s}")
            max_count = model.new_int_var(0, num_days, f"max_count_shift_{s}")

            for n in eligible_members:
                model.add(min_count <= member_shift_counts[n])
                model.add(max_count >= member_shift_counts[n])

            # Create penalty variable for the difference
            diff = model.new_int_var(0, num_days, f"diff_shift_{s}")
            model.add(diff == max_count - min_count)
            fairness_penalties.append(diff)

    # Minimize the total fairness penalty
    model.minimize(sum(fairness_penalties))

    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 1

    status = solver.solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("\n✓ Solution found!")
        print("=" * 80)

        for d in all_days:
            print(f"\n📅 Day {d + 1}")
            print("-" * 80)

            # Group by shifts for better readability
            for s in all_shifts:
                shift = shifts_dict[s]
                assigned_members = []
                for n in all_members:
                    if solver.value(shifts[(n, d, s)]):
                        assigned_members.append(members_dict[n].name)

                if assigned_members:
                    print(f"\n  {shift.description}:")
                    for member_name in assigned_members:
                        print(f"    • {member_name}")

        # Print statistics: shifts per member per category
        print("\n" + "=" * 80)
        print("📊 Shift Statistics by Member")
        print("=" * 80)

        for n in all_members:
            member = members_dict[n]
            shift_counts = {}
            for s in all_shifts:
                count = sum(solver.value(shifts[(n, d, s)]) for d in all_days)
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
        print("❌ No solution found.")


def find_key_in_dict(obj_id: uuid.UUID, model_dict: dict[int, Member | Shift]) -> int:
    for k, obj in model_dict.items():
        if obj.id == obj_id:
            return k
    raise ValueError("No such object")
