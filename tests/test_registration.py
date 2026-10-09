import asyncio
import pytest
from sqlalchemy import select, func
from app.database.models import Registration, Event, User, Referral, Delivery


async def test_repeat_registration(db):
    sessions, service = db
    await service.save(10, 1, 'Steve', 'team', True)
    await service.save(10, 1, 'Steve', 'team', True)
    async with sessions() as s:
        assert await s.scalar(select(func.count()).select_from(Registration)) == 1
    assert (await service.stats(1))['active'] == 1


async def test_concurrent_registration(db):
    _, service = db
    await asyncio.gather(*(service.save(10, 1, 'Steve', 'team', True) for _ in range(2)))
    assert (await service.stats(1))['active'] == 1


async def test_edit(db):
    _, service = db
    r = await service.save(10, 1, 'Steve', 'team', True)
    edited = await service.save(10, 1, 'Alex_1', 'looking', False)
    assert edited.id == r.id
    assert (edited.nick, edited.team, edited.reminders) == ('Alex_1', 'looking', False)


async def test_cancel_and_rejoin(db):
    _, service = db
    await service.save(10, 1, 'Steve', 'team', True)
    await service.cancel(10, 1)
    await service.cancel(10, 1)
    stats = await service.stats(1)
    assert stats['active'] == stats['reminders'] == 0
    assert stats['cancellations'] == 1
    await service.save(10, 1, 'Steve', 'solo', False)
    assert (await service.stats(1))['active'] == 1


async def test_stats_and_first_source(db):
    _, service = db
    await service.ensure(10, 1, source='channel')
    await service.ensure(10, 1, source='friend')
    await service.ensure(20, 1, source='tiktok', begin=True)
    await service.ensure(30, 1, source='garbage')
    await service.save(10, 1, 'Steve', 'team', True)
    await service.save(30, 1, 'Alex', 'solo', False)
    await service.cancel(30, 1)
    stats = await service.stats(1)
    assert (stats['opened'], stats['started'], stats['completed'], stats['active']) == (3, 3, 2, 1)
    assert stats['sources'] == {'channel': 1, 'tiktok': 1, 'unknown': 1}
    assert stats['reminders'] == stats['team'] == stats['cancellations'] == 1
    assert stats['conversion'] == pytest.approx(200 / 3)


@pytest.mark.parametrize('nick', ['ab', 'a'*17, 'Ник', 'bad-name', '<script>'])
async def test_bad_nick(db, nick):
    with pytest.raises(ValueError):
        await db[1].save(10, 1, nick, 'team', True)


async def test_closed(db):
    sessions, service = db
    async with sessions.begin() as s:
        (await s.get(Event, 1)).opened = False
    with pytest.raises(ValueError):
        await service.save(10, 1, 'Steve', 'team', True)


async def test_delete(db):
    sessions, service = db
    await service.ensure(10, 1, source='channel')
    await service.save(10, 1, 'Steve', 'team', True)
    async with sessions.begin() as s:
        s.add(Delivery(event_id=1, user_id=10, kind='morning', status='sent'))
    await service.delete_user(10)
    async with sessions() as s:
        assert await s.get(User, 10) is None
        for model in (Registration, Referral, Delivery):
            assert await s.scalar(select(func.count()).select_from(model)) == 0
