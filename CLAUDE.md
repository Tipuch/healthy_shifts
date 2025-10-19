# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Healthy Shifts is a shift scheduling system built with Python, SQLModel, and SQLite. The system manages member shifts, shift constraints, member requests (time-off/availability), and scheduled shifts with member assignments.

## Development Commands

This project uses `uv` for dependency management. Python 3.14+ is required.

### Setup
```bash
uv sync                 # Install dependencies
```

### Running the Application
```bash
python hello.py         # Initialize database and run main application
```

### Testing
```bash
uv run pytest           # Run all tests
uv run pytest path/to/test_file.py  # Run a single test file
```

### Code Quality
```bash
uv run ruff check       # Run linting
uv run ruff format      # Format code
uv run bandit -r .      # Run security checks
```

## Architecture

### Database Layer

The application uses SQLModel (built on SQLAlchemy) with SQLite. Database setup is in `db.py`:
- `engine`: SQLAlchemy engine pointing to `database.db`
- `get_session()`: Async generator for database sessions

All models are imported in `db.py` and the database schema is created via `SQLModel.metadata.create_all(engine)` in `hello.py`.

### Data Models

Located in `models/` directory. All models use UUID primary keys and track `created_at`/`updated_at` timestamps.

**Core Entities:**
- `MemberGroup`: Groups that members belong to
- `Member`: Individual team members with name, email, and member_group_id foreign key
- `Shift`: Recurring shift templates with time-of-day (`seconds_since_midnight`), duration, and days of week (JSON array)
- `ShiftScheduled`: Concrete shift instances with start/end datetimes, linked to a `Shift` template and assigned members
- `MemberRequest`: Time-off or availability requests from members (start_at, end_at)
- `ShiftConstraint`: Defines scheduling rules between shifts (e.g., prevent assigning same member within last N occurrences of a linked shift)

**Relationships:**
- `ShiftScheduled` ↔ `Member`: Many-to-many via `MemberShiftScheduled` link table
- `Member` → `MemberGroup`: Many-to-one
- `MemberRequest` → `Member`: Many-to-one
- `ShiftScheduled` → `Shift`: Many-to-one (scheduled instance of template)
- `ShiftConstraint`: Self-referential on `Shift` to define inter-shift rules

### Key Design Patterns

1. **Shift Templates vs Instances**: `Shift` models define recurring patterns (e.g., "Monday 9am-5pm"), while `ShiftScheduled` represents concrete occurrences with actual dates and assigned members.

2. **Constraint System**: `ShiftConstraint` allows defining rules like "don't assign member to this shift if they worked the linked shift in the last N occurrences" using `within_last_shifts` counter.

3. **Time Representation**: Shift templates use `seconds_since_midnight` for time-of-day and `days` JSON array for weekdays. Scheduled shifts use full `datetime` for `start_at`/`end_at`.

## Notes

- All datetime fields use UTC timezone
- The `days` field in `Shift` stores weekdays as JSON array (0=Sunday, 6=Saturday)
- UUIDs are auto-generated using `uuid.uuid4()` for all primary keys
