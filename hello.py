import random
from datetime import datetime, timedelta

import sqlalchemy

from db import Session, SQLModel, engine
from models import (Member, MemberGroup, MemberGroupShift, MemberRequest,
                    Shift, ShiftConstraint)
from services.schedule_service import save_schedule, schedule_shifts, export_all_members_ics


def main():
    print("Hello from healthy-shifts!")

    # Drop all tables and recreate (start fresh)
    print("Dropping existing tables...")
    SQLModel.metadata.drop_all(engine)
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)

    # Create dummy data
    with Session(engine) as session:
        # Create MemberGroups (Medical Specialties)
        surgery = MemberGroup(name="Surgery")
        pediatry = MemberGroup(name="Pediatry")
        obstetrics = MemberGroup(name="Obstetrics")
        internal_medicine = MemberGroup(name="Internal Medicine")

        session.add(surgery)
        session.add(pediatry)
        session.add(obstetrics)
        session.add(internal_medicine)
        session.commit()
        session.refresh(surgery)
        session.refresh(pediatry)
        session.refresh(obstetrics)
        session.refresh(internal_medicine)

        # Create Members (Doctors by specialty)
        surgery_doctors = [
            "Dr. Sarah Johnson",
            "Dr. Michael Chen",
            "Dr. Emily Rodriguez",
            "Dr. James Wilson",
        ]

        pediatry_doctors = [
            "Dr. Maria Garcia",
            "Dr. David Kim",
        ]

        obstetrics_doctors = [
            "Dr. Jennifer Lee",
            "Dr. Robert Taylor",
        ]

        im_doctors = [
            "Dr. Lisa Anderson",
            "Dr. William Brown",
            "Dr. Amanda Martinez",
        ]

        members = []

        # Add Surgery doctors
        for i, name in enumerate(surgery_doctors):
            email = f"surgery{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=surgery.id)
            members.append(member)
            session.add(member)

        # Add Pediatry doctors
        for i, name in enumerate(pediatry_doctors):
            email = f"pediatry{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=pediatry.id)
            members.append(member)
            session.add(member)

        # Add Obstetrics doctors
        for i, name in enumerate(obstetrics_doctors):
            email = f"obstetrics{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=obstetrics.id)
            members.append(member)
            session.add(member)

        # Add Internal Medicine doctors
        for i, name in enumerate(im_doctors):
            email = f"im{i + 1}@hospital.com"
            member = Member(
                name=name, email=email, member_group_id=internal_medicine.id
            )
            members.append(member)
            session.add(member)

        session.commit()

        # Create dummy vacation requests (single-day time-off)
        # Select 2-3 random members for vacation requests
        num_requests = random.randint(2, 3)
        selected_members = random.sample(members, num_requests)

        start_date = datetime.now()

        for member in selected_members:
            # Random day within the 30-day scheduling window
            days_offset = random.randint(0, 29)
            vacation_start = start_date + timedelta(days=days_offset)
            vacation_end = vacation_start + timedelta(days=1)

            request = MemberRequest(
                member_id=member.id,
                start_at=vacation_start,
                end_at=vacation_end,
                description="Vacation day",
            )
            session.add(request)

        session.commit()

        print(f"✓ Created {num_requests} vacation requests for random members")

        # Create Shifts
        # Dedicated weekday night shifts for each group (16:00 for 16 hours, Mon-Fri)
        surgery_weekday_night = Shift(
            description="Surgery Weekday Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=16 * 3600,  # 16 hours
            members_required=1,
            days=["0", "1", "2", "3", "4"],  # Mon-Fri
        )
        session.add(surgery_weekday_night)

        pediatry_weekday_night = Shift(
            description="Pediatry Weekday Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=16 * 3600,  # 16 hours
            members_required=1,
            days=["0", "1", "2", "3", "4"],  # Mon-Fri
        )
        session.add(pediatry_weekday_night)

        obstetrics_weekday_night = Shift(
            description="Obstetrics Weekday Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=16 * 3600,  # 16 hours
            members_required=1,
            days=["0", "1", "2", "3", "4"],  # Mon-Fri
        )
        session.add(obstetrics_weekday_night)

        im_weekday_night = Shift(
            description="Internal Medicine Weekday Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=16 * 3600,  # 16 hours
            members_required=1,
            days=["0", "1", "2", "3", "4"],  # Mon-Fri
        )
        session.add(im_weekday_night)

        # Dedicated weekend night shifts for each group (08:00 for 24 hours, Sat-Sun)
        surgery_weekend_night = Shift(
            description="Surgery Weekend Night",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=24 * 3600,  # 24 hours
            members_required=1,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(surgery_weekend_night)

        pediatry_weekend_night = Shift(
            description="Pediatry Weekend Night",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=24 * 3600,  # 24 hours
            members_required=1,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(pediatry_weekend_night)

        obstetrics_weekend_night = Shift(
            description="Obstetrics Weekend Night",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=24 * 3600,  # 24 hours
            members_required=1,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(obstetrics_weekend_night)

        im_weekend_night = Shift(
            description="Internal Medicine Weekend Night",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=24 * 3600,  # 24 hours
            members_required=1,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(im_weekend_night)

        # Shared ER shifts (all days)
        er_morning = Shift(
            description="ER Morning",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(er_morning)

        er_evening = Shift(
            description="ER Evening",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(er_evening)

        er_night = Shift(
            description="ER Night",
            seconds_since_midnight=0 * 3600,  # 12am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(er_night)

        # Shared OPD shifts
        opd_weekday_night = Shift(
            description="OPD Weekday Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=8 * 3600,  # 8 hours
            members_required=2,
            days=["0", "1", "2", "3", "4"],  # Mon-Fri
        )
        session.add(opd_weekday_night)

        opd_weekend_day = Shift(
            description="OPD Weekend Day",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=2,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(opd_weekend_day)

        opd_weekend_night = Shift(
            description="OPD Weekend Night",
            seconds_since_midnight=16 * 3600,  # 4pm
            duration_seconds=8 * 3600,  # 8 hours
            members_required=2,
            days=["5", "6"],  # Sat-Sun
        )
        session.add(opd_weekend_night)

        session.commit()

        # Refresh all shift objects
        session.refresh(surgery_weekday_night)
        session.refresh(pediatry_weekday_night)
        session.refresh(obstetrics_weekday_night)
        session.refresh(im_weekday_night)
        session.refresh(surgery_weekend_night)
        session.refresh(pediatry_weekend_night)
        session.refresh(obstetrics_weekend_night)
        session.refresh(im_weekend_night)
        session.refresh(er_morning)
        session.refresh(er_evening)
        session.refresh(er_night)
        session.refresh(opd_weekday_night)
        session.refresh(opd_weekend_day)
        session.refresh(opd_weekend_night)

        # Create many-to-many relationships between MemberGroups and Shifts
        # Dedicated weekday night shifts - one per group
        session.add(
            MemberGroupShift(
                member_group_id=surgery.id, shift_id=surgery_weekday_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=pediatry.id, shift_id=pediatry_weekday_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=obstetrics.id, shift_id=obstetrics_weekday_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=internal_medicine.id, shift_id=im_weekday_night.id
            )
        )

        # Dedicated weekend night shifts - one per group
        session.add(
            MemberGroupShift(
                member_group_id=surgery.id, shift_id=surgery_weekend_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=pediatry.id, shift_id=pediatry_weekend_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=obstetrics.id, shift_id=obstetrics_weekend_night.id
            )
        )
        session.add(
            MemberGroupShift(
                member_group_id=internal_medicine.id, shift_id=im_weekend_night.id
            )
        )

        # Shared ER and OPD shifts - all groups
        for shift in [
            er_morning,
            er_evening,
            er_night,
            opd_weekday_night,
            opd_weekend_day,
            opd_weekend_night,
        ]:
            session.add(MemberGroupShift(member_group_id=surgery.id, shift_id=shift.id))
            session.add(
                MemberGroupShift(member_group_id=pediatry.id, shift_id=shift.id)
            )
            session.add(
                MemberGroupShift(member_group_id=obstetrics.id, shift_id=shift.id)
            )
            session.add(
                MemberGroupShift(
                    member_group_id=internal_medicine.id, shift_id=shift.id
                )
            )

        session.commit()

        # Create ShiftConstraints

        # 1. Prevent two night shifts in a row (within_last_shifts=1)
        night_shifts = [
            surgery_weekday_night,
            pediatry_weekday_night,
            obstetrics_weekday_night,
            im_weekday_night,
            surgery_weekend_night,
            pediatry_weekend_night,
            obstetrics_weekend_night,
            im_weekend_night,
            er_night,
            er_evening,
            opd_weekday_night,
            opd_weekend_night,
        ]
        same_shift_pairs = [
            (surgery_weekday_night, surgery_weekend_night),
            (surgery_weekend_night, surgery_weekday_night),
            (pediatry_weekday_night, pediatry_weekend_night),
            (pediatry_weekend_night, pediatry_weekday_night),
            (obstetrics_weekday_night, obstetrics_weekend_night),
            (obstetrics_weekend_night, obstetrics_weekday_night),
            (im_weekday_night, im_weekend_night),
            (im_weekend_night, im_weekday_night),
            (opd_weekend_night, opd_weekday_night),
            (opd_weekday_night, opd_weekend_night),
        ]
        consecutive_constraints = 0
        for shift in night_shifts:
            for linked_shift in night_shifts:
                if (
                    shift.id == linked_shift.id
                    or (shift, linked_shift) in same_shift_pairs
                ):
                    constraint = ShiftConstraint(
                        shift_id=shift.id,
                        linked_shift_id=linked_shift.id,
                        within_last_shifts=1,
                    )
                    session.add(constraint)
                    session.commit()
                    consecutive_constraints += 1

        # 2. Prevent overlapping shifts on the same day (within_last_shifts=0)
        overlapping_pairs = []

        # Weekday dedicated night shifts overlap with weekday ER/OPD shifts
        weekday_dedicated = [
            surgery_weekday_night,
            pediatry_weekday_night,
            obstetrics_weekday_night,
            im_weekday_night,
        ]
        weekday_shared = [er_evening, er_night, opd_weekday_night]

        for ded_shift in weekday_dedicated:
            for shared_shift in weekday_shared:
                overlapping_pairs.append((ded_shift, shared_shift))
                overlapping_pairs.append((shared_shift, ded_shift))

        # ER Evening overlaps with OPD Weekday Night on weekdays
        overlapping_pairs.append((er_evening, opd_weekday_night))
        overlapping_pairs.append((opd_weekday_night, er_evening))

        # Weekend dedicated night shifts (24hrs) overlap with ALL weekend shifts
        weekend_dedicated = [
            surgery_weekend_night,
            pediatry_weekend_night,
            obstetrics_weekend_night,
            im_weekend_night,
        ]
        weekend_shared = [
            er_morning,
            er_evening,
            er_night,
            opd_weekend_day,
            opd_weekend_night,
        ]

        for ded_shift in weekend_dedicated:
            for shared_shift in weekend_shared:
                overlapping_pairs.append((ded_shift, shared_shift))
                overlapping_pairs.append((shared_shift, ded_shift))

        # ER Morning overlaps with OPD Weekend Day on weekends
        overlapping_pairs.append((er_morning, opd_weekend_day))
        overlapping_pairs.append((opd_weekend_day, er_morning))

        # ER Evening overlaps with OPD Weekend Night on weekends
        overlapping_pairs.append((er_evening, opd_weekend_night))
        overlapping_pairs.append((opd_weekend_night, er_evening))

        overlap_constraints = 0
        for shift, linked_shift in overlapping_pairs:
            if shift.id == surgery_weekend_night.id and linked_shift.id == er_night.id:
                continue
            constraint = ShiftConstraint(
                shift_id=shift.id,
                linked_shift_id=linked_shift.id,
                within_last_shifts=0,
            )
            session.add(constraint)
            overlap_constraints += 1
        constraint = ShiftConstraint(
            shift_id=surgery_weekend_night.id,
            linked_shift_id=er_night.id,
            within_last_shifts=1,
        )
        session.add(constraint)
        overlap_constraints += 1
        session.commit()

        print(
            "✓ Created 4 MemberGroups (Surgery, Pediatry, Obstetrics, Internal Medicine)"
        )
        print(
            f"✓ Created {len(members)} Members ({len(surgery_doctors)} Surgery, {len(pediatry_doctors)} Pediatry, {len(obstetrics_doctors)} Obstetrics, {len(im_doctors)} IM)"
        )
        print("✓ Created 15 Shifts (8 dedicated group shifts + 7 shared shifts)")
        print("✓ Created MemberGroupShift associations")
        print(
            f"✓ Created {consecutive_constraints} ShiftConstraints (prevent consecutive night shifts)"
        )
        print(
            f"✓ Created {overlap_constraints} ShiftConstraints (prevent overlapping shifts on same day)"
        )

    # Run the scheduler for the next 30 days (use clean date at midnight)
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=30)

    print(f"\nRunning scheduler from {start_date.date()} to {end_date.date()}...")
    solver, shifts, members_dict, shifts_dict, days_dict = schedule_shifts(
        start_date, end_date
    )

    # Save the schedule to database if solution was found
    if solver is not None:
        save_schedule(solver, shifts, members_dict, shifts_dict, days_dict)
        export_all_members_ics(session, start_date, end_date, "./output")

    # Verification: Check that time-off requests were respected
    print("\n" + "=" * 80)
    print("VERIFICATION: Time-Off Request Overlap Detection")
    print("=" * 80)

    with Session(engine) as session:
        from sqlmodel import select

        from models import MemberShiftScheduled, ShiftScheduled

        # Get all time-off requests
        statement = select(MemberRequest, Member).join(Member)
        requests = session.exec(statement).all()

        print("\nTime-off Requests Created:")
        for request, member in requests:
            day_offset = (request.start_at - start_date).days + 1
            print(f"  {member.name}: Day {day_offset} ({request.start_at.date()})")

        print("\nChecking if members with time-off were scheduled:")
        all_passed = True
        examples = []

        for request, member in requests:
            # Get all shift assignments for this member
            stmt = (
                select(MemberShiftScheduled, ShiftScheduled, Shift)
                .join(
                    ShiftScheduled,
                    MemberShiftScheduled.shift_scheduled_id == ShiftScheduled.id,
                )
                .join(Shift, ShiftScheduled.shift_id == Shift.id)
                .where(MemberShiftScheduled.member_id == member.id)
            )

            assignments = session.exec(stmt).all()

            # Check for overlap: shift overlaps request if shift_start < request_end AND shift_end > request_start
            overlapping_shifts = []
            for mss, ss, shift in assignments:
                if ss.start_at < request.end_at and ss.end_at > request.start_at:
                    overlapping_shifts.append(shift.description)

            day = (request.start_at - start_date).days + 1

            if overlapping_shifts:
                print(
                    f"  ❌ FAIL: {member.name} IS scheduled during time-off (Day {day}): {', '.join(overlapping_shifts)}"
                )
                all_passed = False
            else:
                print(
                    f"  ✓ PASS: {member.name} is NOT scheduled during time-off (Day {day})"
                )
                examples.append((member.name, day))

        print("\n" + "=" * 80)
        if all_passed:
            print("✅ SUCCESS: All time-off requests were respected!")
        else:
            print("❌ FAILURE: Some members were scheduled during time-off")
        print("=" * 80)

        # Demonstrate display_schedule() method
        if solver is not None:
            # Get first member from the database
            first_member = session.exec(select(Member)).first()
            if first_member:
                schedule_output = first_member.display_schedule(session)
                print(schedule_output)


if __name__ == "__main__":
    main()
