from datetime import datetime, timedelta, timezone
import pytest_asyncio
from app.database import connect
from app.database.models import Base, Event
from app.services.registrations import Registrations


@pytest_asyncio.fixture
async def db(tmp_path):
    engine, sessions = connect(f'sqlite+aiosqlite:///{tmp_path / "test.db"}')
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    async with sessions.begin() as s:
        s.add(Event(id=1, date=future.strftime('%Y-%m-%d'), time='18:00', timezone='UTC',
                    description='Battle', ip='mcnovax.space', versions='Java 1.21.4', rules='Rules', opened=True))
    yield sessions, Registrations(sessions)
    await engine.dispose()
