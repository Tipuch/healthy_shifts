from datetime import datetime, timedelta, timezone
from db import SQLModel, engine, Session
from models import Member, MemberGroup, Shift, ShiftConstraint
from services.schedule_service import schedule_shifts


def main():
    print("Hello from healthy-shifts!")

    # Drop all tables and recreate (start fresh)
    print("Dropping existing tables...")
    SQLModel.metadata.drop_all(engine)
    print("Creating tables...")
    SQLModel.metadata.create_all(engine)

    # Create dummy data
    with Session(engine) as session:
        # Create MemberGroup
        doctors_group = MemberGroup(name="Doctors")
        session.add(doctors_group)
        session.commit()
        session.refresh(doctors_group)

        # Create 30 Members (doctors) with realistic names
        doctor_names = [
            "Dr. Sarah Johnson",
            "Dr. Michael Chen",
            "Dr. Emily Rodriguez",
            "Dr. James Wilson",
            "Dr. Maria Garcia",
            "Dr. David Kim",
            "Dr. Jennifer Lee",
            "Dr. Robert Taylor",
            "Dr. Lisa Anderson",
            "Dr. William Brown",
            "Dr. Amanda Martinez",
            "Dr. Christopher Davis",
            "Dr. Jessica Miller",
            "Dr. Daniel White",
            "Dr. Michelle Thompson",
            "Dr. Matthew Harris",
            "Dr. Rebecca Clark",
            "Dr. Joshua Lewis",
            "Dr. Laura Walker",
            "Dr. Andrew Hall",
            "Dr. Rachel Young",
            "Dr. Kevin Allen",
            "Dr. Nicole King",
            "Dr. Brian Wright",
            "Dr. Stephanie Lopez",
            "Dr. Eric Hill",
            "Dr. Angela Scott",
            "Dr. Ryan Green",
            "Dr. Melissa Adams",
            "Dr. Justin Baker",
        ]

        members = []
        for i, name in enumerate(doctor_names):
            email = f"doctor{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=doctors_group.id)
            members.append(member)
            session.add(member)

        session.commit()

        # Create 3 Shifts (Morning, Evening, Night)
        # Morning: 6am-2pm (8 hours)
        morning_shift = Shift(
            description="Morning Shift",
            seconds_since_midnight=6 * 3600,  # 6am = 21600 seconds
            duration_seconds=8 * 3600,  # 8 hours = 28800 seconds
            members_required=20,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days of week
        )
        session.add(morning_shift)

        # Evening: 2pm-10pm (8 hours)
        evening_shift = Shift(
            description="Evening Shift",
            seconds_since_midnight=14 * 3600,  # 2pm = 50400 seconds
            duration_seconds=8 * 3600,  # 8 hours = 28800 seconds
            members_required=20,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days of week
        )
        session.add(evening_shift)

        # Night: 10pm-6am (8 hours)
        night_shift = Shift(
            description="Night Shift",
            seconds_since_midnight=22 * 3600,  # 10pm = 79200 seconds
            duration_seconds=8 * 3600,  # 8 hours = 28800 seconds
            members_required=10,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days of week
        )
        session.add(night_shift)

        session.commit()
        session.refresh(morning_shift)
        session.refresh(evening_shift)
        session.refresh(night_shift)

        # Create ShiftConstraint: Night shift cannot be assigned within 2 occurrences
        night_constraint = ShiftConstraint(
            shift_id=night_shift.id,
            linked_shift_id=night_shift.id,
            within_last_shifts=1,
        )
        session.add(night_constraint)
        session.commit()

        print("✓ Created 1 MemberGroup")
        print(f"✓ Created {len(members)} Members")
        print("✓ Created 3 Shifts (Morning, Evening, Night)")
        print("✓ Created ShiftConstraint (Night shift restriction)")

    # Run the scheduler for the next 30 days
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=30)

    print(f"\nRunning scheduler from {start_date.date()} to {end_date.date()}...")
    schedule_shifts(start_date, end_date)


if __name__ == "__main__":
    main()
