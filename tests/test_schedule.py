from datetime import datetime, timedelta, timezone
import pytest
from app.database.models import Event
from app.services.events import available, opening_timestamp


async def test_scheduled_opening_and_unknown_event_time(db):
    sessions, registrations = db
    async with sessions.begin() as s:
        e = await s.get(Event, 1)
        e.time = None
        e.registration_opens_at = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        assert not available(e)
    with pytest.raises(ValueError):
        await registrations.save(10, 1, 'Steve', 'solo', False)
    async with sessions.begin() as s:
        e = await s.get(Event, 1)
        e.registration_opens_at = int((datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp())
        assert available(e)
    await registrations.save(10, 1, 'Steve', 'solo', False)
    assert (await registrations.stats(1))['active'] == 1


def test_moscow_opening_timestamp():
    stamp = opening_timestamp('2026-10-08T22:00', 'Europe/Moscow')
    assert datetime.fromtimestamp(stamp, timezone.utc).isoformat() == '2026-10-08T19:00:00+00:00'
