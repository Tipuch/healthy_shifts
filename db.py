from models import Member, MemberGroup, MemberRequest, Shift, ShiftConstraint, ShiftScheduled
from sqlmodel import SQLModel, Session, create_engine

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url)


async def get_session():
    with Session(engine) as session:
        yield session