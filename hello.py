from db import SQLModel, engine
from ortools.sat.python import cp_model


def main():
    print("Hello from healthy-shifts!")
    SQLModel.metadata.create_all(engine)

    num_nurses = 6
    num_shifts = 2
    num_days = 7
    all_nurses = range(num_nurses)
    all_shifts = range(num_shifts)
    all_days = range(num_days)

    model = cp_model.CpModel()

    shifts = {}
    for n in all_nurses:
        for d in all_days:
            for s in all_shifts:
                shifts[(n, d, s)] = model.new_bool_var(f"shift_n{n}_d{d}_s{s}")

    # Shift requirements: shift 0 needs 2 nurse, shift 1 needs 3 nurses
    shift_requirements = {0: 2, 1: 3}
    for d in all_days:
        for s in all_shifts:
            model.add(sum(shifts[(n, d, s)] for n in all_nurses) == shift_requirements[s])

    # Constraint: no nurse works shift 0 on consecutive days
    for n in all_nurses:
        for d in range(num_days - 1):
            model.add(shifts[(n, d, 0)] + shifts[(n, d + 1, 0)] <= 1)

    # Define which nurses can work which shifts
    # Nurses 0 and 1 can only do shift 0
    # Nurses 2 and 3 can only do shift 1
    # Nurses 4 and 5 can do both shift 0 and shift 1
    shift_eligibility = {
        0: [0, 1, 4, 5],  # Nurses eligible for shift 0
        1: [2, 3, 4, 5],  # Nurses eligible for shift 1
    }

    # Constraint: nurses can only work shifts they're eligible for
    for n in all_nurses:
        for d in all_days:
            for s in all_shifts:
                if n not in shift_eligibility[s]:
                    model.add(shifts[(n, d, s)] == 0)

    # Soft fairness constraint: minimize the difference in shift counts
    # among nurses eligible for the same shift type
    fairness_penalties = []

    for s in all_shifts:
        eligible_nurses = shift_eligibility[s]
        if len(eligible_nurses) > 1:
            # Count total shifts of type s each eligible nurse works
            nurse_shift_counts = {}
            for n in eligible_nurses:
                count_vars = []
                for d in all_days:
                    count_vars.append(shifts[(n, d, s)])
                nurse_shift_counts[n] = sum(count_vars)

            # Create variables for min and max shift counts among eligible nurses
            min_count = model.new_int_var(0, num_days, f"min_count_shift_{s}")
            max_count = model.new_int_var(0, num_days, f"max_count_shift_{s}")

            for n in eligible_nurses:
                model.add(min_count <= nurse_shift_counts[n])
                model.add(max_count >= nurse_shift_counts[n])

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
        print("Solution found:")
        for d in all_days:
            print(f"Day {d}")
            for n in all_nurses:
                is_working = False
                for s in all_shifts:
                    if solver.value(shifts[(n, d, s)]):
                        is_working = True
                        print(f"  Nurse {n} works shift {s}")
                if not is_working:
                    print(f"  Nurse {n} does not work")

        # Print statistics: shifts per nurse per category
        print("\n" + "="*50)
        print("Shift Statistics by Nurse:")
        print("="*50)
        for n in all_nurses:
            shift_counts = {}
            for s in all_shifts:
                count = sum(solver.value(shifts[(n, d, s)]) for d in all_days)
                shift_counts[s] = count

            total = sum(shift_counts.values())
            print(f"Nurse {n}: Shift 0: {shift_counts[0]}, Shift 1: {shift_counts[1]}, Total: {total}")
    else:
        print("No solution found.")

if __name__ == "__main__":
    main()
