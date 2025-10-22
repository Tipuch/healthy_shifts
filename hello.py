from datetime import datetime, timedelta, timezone
from db import SQLModel, engine, Session
from models import Member, MemberGroup, MemberGroupShift, Shift, ShiftConstraint
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
        # Create MemberGroups (Medical Specialties)
        psychiatry = MemberGroup(name="Psychiatry")
        ent = MemberGroup(name="ENT")
        internal_medicine = MemberGroup(name="Internal Medicine")

        session.add(psychiatry)
        session.add(ent)
        session.add(internal_medicine)
        session.commit()
        session.refresh(psychiatry)
        session.refresh(ent)
        session.refresh(internal_medicine)

        # Create Members (Doctors by specialty)
        psychiatry_doctors = [
            "Dr. Sarah Johnson",
            "Dr. Michael Chen",
            "Dr. Emily Rodriguez",
            "Dr. James Wilson",
        ]

        ent_doctors = [
            "Dr. Maria Garcia",
            "Dr. David Kim",
            "Dr. Jennifer Lee",
            "Dr. Robert Taylor",
        ]

        im_doctors = [
            "Dr. Lisa Anderson",
            "Dr. William Brown",
            "Dr. Amanda Martinez",
            "Dr. Christopher Davis",
            "Dr. Jessica Miller",
        ]

        members = []

        # Add Psychiatry doctors
        for i, name in enumerate(psychiatry_doctors):
            email = f"psych{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=psychiatry.id)
            members.append(member)
            session.add(member)

        # Add ENT doctors
        for i, name in enumerate(ent_doctors):
            email = f"ent{i + 1}@hospital.com"
            member = Member(name=name, email=email, member_group_id=ent.id)
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

        # Create Shifts
        # Specialty-specific shifts
        psych_clinic = Shift(
            description="Psychiatry Clinic",
            seconds_since_midnight=9 * 3600,  # 9am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["1", "2", "3", "4", "5"],  # Mon-Fri
        )
        session.add(psych_clinic)

        ent_clinic = Shift(
            description="ENT Clinic",
            seconds_since_midnight=9 * 3600,  # 9am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["1", "2", "3", "4", "5"],  # Mon-Fri
        )
        session.add(ent_clinic)

        im_clinic = Shift(
            description="Internal Medicine Clinic",
            seconds_since_midnight=9 * 3600,  # 9am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["1", "2", "3", "4", "5"],  # Mon-Fri
        )
        session.add(im_clinic)

        # Shared shifts
        er_shift = Shift(
            description="ER",
            seconds_since_midnight=7 * 3600,  # 7am
            duration_seconds=12 * 3600,  # 12 hours
            members_required=3,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(er_shift)

        ward_shift = Shift(
            description="Ward",
            seconds_since_midnight=8 * 3600,  # 8am
            duration_seconds=8 * 3600,  # 8 hours
            members_required=2,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(ward_shift)

        on_call_shift = Shift(
            description="On-Call",
            seconds_since_midnight=22 * 3600,  # 10pm
            duration_seconds=8 * 3600,  # 8 hours
            members_required=1,
            days=["0", "1", "2", "3", "4", "5", "6"],  # All days
        )
        session.add(on_call_shift)

        session.commit()
        session.refresh(psych_clinic)
        session.refresh(ent_clinic)
        session.refresh(im_clinic)
        session.refresh(er_shift)
        session.refresh(ward_shift)
        session.refresh(on_call_shift)

        # Create many-to-many relationships between MemberGroups and Shifts
        # Specialty-specific shifts
        session.add(
            MemberGroupShift(member_group_id=psychiatry.id, shift_id=psych_clinic.id)
        )
        session.add(MemberGroupShift(member_group_id=ent.id, shift_id=ent_clinic.id))
        session.add(
            MemberGroupShift(
                member_group_id=internal_medicine.id, shift_id=im_clinic.id
            )
        )

        # Shared shifts - all groups
        for shift in [er_shift, ward_shift, on_call_shift]:
            session.add(
                MemberGroupShift(member_group_id=psychiatry.id, shift_id=shift.id)
            )
            session.add(MemberGroupShift(member_group_id=ent.id, shift_id=shift.id))
            session.add(
                MemberGroupShift(
                    member_group_id=internal_medicine.id, shift_id=shift.id
                )
            )

        session.commit()

        # Create ShiftConstraint: On-call shift cannot be assigned within 1 occurrence
        on_call_constraint = ShiftConstraint(
            shift_id=on_call_shift.id,
            linked_shift_id=on_call_shift.id,
            within_last_shifts=1,
        )
        session.add(on_call_constraint)
        session.commit()

        print("✓ Created 3 MemberGroups (Psychiatry, ENT, Internal Medicine)")
        print(
            f"✓ Created {len(members)} Members ({len(psychiatry_doctors)} Psychiatry, {len(ent_doctors)} ENT, {len(im_doctors)} IM)"
        )
        print("✓ Created 6 Shifts (3 specialty clinics + 3 shared shifts)")
        print("✓ Created MemberGroupShift associations")
        print("✓ Created ShiftConstraint (On-call restriction)")

    # Run the scheduler for the next 30 days
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=30)

    print(f"\nRunning scheduler from {start_date.date()} to {end_date.date()}...")
    schedule_shifts(start_date, end_date)


if __name__ == "__main__":
    main()
