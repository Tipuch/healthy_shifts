"""
Tests for ICS calendar export functionality.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlmodel import Session

from services.schedule_service import export_all_members_ics, export_member_ics


class TestICSExport:
    """Test suite for ICS calendar export operations."""

    def test_export_individual_member_ics(
        self,
        session: Session,
        member_factory,
        shift_scheduled_factory,
        member_shift_scheduled_factory,
        tmp_path: Path,
    ):
        """Test exporting ICS file for a single member."""
        # Arrange
        member = member_factory(name="John Doe", email="john@example.com")

        # Create scheduled shifts for the member
        start_date = datetime(2025, 1, 20, 9, 0, tzinfo=timezone.utc)
        shift1 = shift_scheduled_factory(
            start_at=start_date,
            end_at=start_date + timedelta(hours=8),
            description="Morning Shift",
        )
        shift2 = shift_scheduled_factory(
            start_at=start_date + timedelta(days=1),
            end_at=start_date + timedelta(days=1, hours=8),
            description="Day Shift",
        )

        # Assign shifts to member
        member_shift_scheduled_factory(
            member_id=member.id, shift_scheduled_id=shift1.id
        )
        member_shift_scheduled_factory(
            member_id=member.id, shift_scheduled_id=shift2.id
        )

        # Act
        output_dir = tmp_path / "ics_exports"
        export_member_ics(
            session=session,
            member_id=member.id,
            start=start_date,
            end=start_date + timedelta(days=7),
            output_dir=str(output_dir),
        )

        # Assert
        ics_file = output_dir / f"{member.email}.ics"
        assert ics_file.exists(), "ICS file should be created"

        # Read and verify ICS content
        content = ics_file.read_text()

        # Verify ICS format
        assert content.startswith("BEGIN:VCALENDAR"), "Should start with VCALENDAR"
        assert "VERSION:2.0" in content, "Should have version 2.0"
        assert "PRODID:" in content, "Should have PRODID"
        assert "BEGIN:VEVENT" in content, "Should contain at least one event"
        assert "END:VEVENT" in content, "Should end event properly"
        assert "END:VCALENDAR" in content, "Should end with VCALENDAR"

        # Verify shift details are in the ICS
        assert "Morning Shift" in content, "Should contain shift description"
        assert "Day Shift" in content, "Should contain second shift description"

    def test_export_all_members_ics(
        self,
        session: Session,
        member_factory,
        shift_scheduled_factory,
        member_shift_scheduled_factory,
        tmp_path: Path,
    ):
        """Test exporting ICS files for all members including global file."""
        # Arrange
        member1 = member_factory(name="Alice Smith", email="alice@example.com")
        member2 = member_factory(name="Bob Jones", email="bob@example.com")

        # Create scheduled shifts
        start_date = datetime(2025, 1, 20, 9, 0, tzinfo=timezone.utc)
        shift1 = shift_scheduled_factory(
            start_at=start_date,
            end_at=start_date + timedelta(hours=8),
            description="Morning Shift",
        )
        shift2 = shift_scheduled_factory(
            start_at=start_date + timedelta(days=1),
            end_at=start_date + timedelta(days=1, hours=8),
            description="Evening Shift",
        )

        # Assign shifts to members
        member_shift_scheduled_factory(
            member_id=member1.id, shift_scheduled_id=shift1.id
        )
        member_shift_scheduled_factory(
            member_id=member2.id, shift_scheduled_id=shift2.id
        )

        # Act
        output_dir = tmp_path / "ics_exports_all"
        export_all_members_ics(
            session=session,
            start=start_date,
            end=start_date + timedelta(days=7),
            output_dir=str(output_dir),
        )

        # Assert - Individual member files exist
        alice_ics = output_dir / "alice@example.com.ics"
        bob_ics = output_dir / "bob@example.com.ics"
        assert alice_ics.exists(), "Alice's ICS file should be created"
        assert bob_ics.exists(), "Bob's ICS file should be created"

        # Assert - Global file exists
        global_ics = output_dir / "all_members.ics"
        assert global_ics.exists(), "Global ICS file should be created"

        # Assert - Verify Alice's file content
        alice_content = alice_ics.read_text()
        assert "BEGIN:VCALENDAR" in alice_content
        assert "Morning Shift" in alice_content
        assert "Evening Shift" not in alice_content, "Should not contain Bob's shift"

        # Assert - Verify Bob's file content
        bob_content = bob_ics.read_text()
        assert "BEGIN:VCALENDAR" in bob_content
        assert "Evening Shift" in bob_content
        assert "Morning Shift" not in bob_content, "Should not contain Alice's shift"

        # Assert - Verify global file content
        global_content = global_ics.read_text()
        assert "BEGIN:VCALENDAR" in global_content
        assert "VERSION:2.0" in global_content
        assert "Morning Shift - Alice Smith" in global_content
        assert "Evening Shift - Bob Jones" in global_content

    def test_ics_format_validation(
        self,
        session: Session,
        member_factory,
        shift_scheduled_factory,
        member_shift_scheduled_factory,
        tmp_path: Path,
    ):
        """Test that generated ICS files have correct RFC 5545 format."""
        # Arrange
        member = member_factory(name="Test User", email="test@example.com")
        start_date = datetime(2025, 2, 15, 14, 30, tzinfo=timezone.utc)
        shift = shift_scheduled_factory(
            start_at=start_date,
            end_at=start_date + timedelta(hours=4),
            description="Test Event",
        )
        member_shift_scheduled_factory(member_id=member.id, shift_scheduled_id=shift.id)

        # Act
        output_dir = tmp_path / "ics_validation"
        export_member_ics(
            session=session,
            member_id=member.id,
            start=start_date,
            end=start_date + timedelta(days=1),
            output_dir=str(output_dir),
        )

        # Assert
        ics_file = output_dir / "test@example.com.ics"
        # Read with newline='' to preserve original line endings
        content = ics_file.read_text(newline="")

        # Verify line endings (should be CRLF)
        assert "\r\n" in content, "Should use CRLF line endings"

        # Split into lines for detailed validation
        lines = content.split("\r\n")

        # Verify calendar structure
        assert lines[0] == "BEGIN:VCALENDAR", "First line must be BEGIN:VCALENDAR"
        assert lines[-1] == "", "File should end with empty line after final CRLF"
        assert lines[-2] == "END:VCALENDAR", "Second to last line must be END:VCALENDAR"

        # Verify required calendar properties
        assert any("VERSION:2.0" in line for line in lines), "Must have VERSION:2.0"
        assert any("PRODID:" in line for line in lines), "Must have PRODID"
        assert any("CALSCALE:GREGORIAN" in line for line in lines), (
            "Should have CALSCALE"
        )
        assert any("METHOD:PUBLISH" in line for line in lines), "Should have METHOD"

        # Find event section
        event_start = None
        event_end = None
        for i, line in enumerate(lines):
            if line == "BEGIN:VEVENT":
                event_start = i
            if line == "END:VEVENT":
                event_end = i
                break

        assert event_start is not None, "Must have BEGIN:VEVENT"
        assert event_end is not None, "Must have END:VEVENT"
        assert event_start < event_end, "BEGIN:VEVENT must come before END:VEVENT"

        # Verify required event properties
        event_lines = lines[event_start : event_end + 1]
        assert any("UID:" in line for line in event_lines), "Event must have UID"
        assert any("DTSTAMP:" in line for line in event_lines), (
            "Event must have DTSTAMP"
        )
        assert any("DTSTART:" in line for line in event_lines), (
            "Event must have DTSTART"
        )
        assert any("DTEND:" in line for line in event_lines), "Event must have DTEND"
        assert any("SUMMARY:" in line for line in event_lines), (
            "Event must have SUMMARY"
        )

        # Verify datetime format (YYYYMMDDTHHMMSSZ for UTC)
        dtstart_line = [line for line in event_lines if line.startswith("DTSTART:")][0]
        dtstart_value = dtstart_line.split(":")[1]
        assert len(dtstart_value) == 16, "DTSTART should be in YYYYMMDDTHHMMSSZ format"
        assert dtstart_value.endswith("Z"), "DTSTART should end with Z for UTC"
        assert dtstart_value == "20250215T143000Z", "DTSTART should match start time"

        dtend_line = [line for line in event_lines if line.startswith("DTEND:")][0]
        dtend_value = dtend_line.split(":")[1]
        assert dtend_value == "20250215T183000Z", "DTEND should match end time"

        # Verify SUMMARY contains the description
        summary_line = [line for line in event_lines if line.startswith("SUMMARY:")][0]
        assert "Test Event" in summary_line, "SUMMARY should contain event description"
