from datetime import timedelta
from unittest.mock import AsyncMock
from sqlalchemy import select
from app.database.models import Event, Delivery
from app.services.events import starts
from app.services.reminders import Reminders
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import SendMessage


async def test_no_duplicates_after_restart(db):
    sessions, service = db
    await service.save(10, 1, 'Steve', 'team', True)
    await service.save(20, 1, 'Alex', 'solo', False)
    bot = AsyncMock()
    async with sessions() as s:
        e = await s.get(Event, 1)
    now = starts(e) - timedelta(minutes=15)
    await Reminders(sessions, bot).tick(now)
    await Reminders(sessions, bot).tick(now)
    assert bot.send_message.await_count == 1
    assert bot.send_message.call_args.args[0] == 10
    assert 'mcnovax.space' in bot.send_message.call_args.args[1]


async def test_all_three_and_cancellation(db):
    sessions, service = db
    await service.save(10, 1, 'Steve', 'team', True)
    bot = AsyncMock()
    async with sessions() as s:
        e = await s.get(Event, 1)
    start = starts(e)
    worker = Reminders(sessions, bot)
    await worker.tick(start.replace(hour=9))
    await worker.tick(start - timedelta(hours=2))
    await worker.tick(start - timedelta(minutes=15))
    await worker.tick(start)
    assert bot.send_message.await_count == 3
    await service.save(20, 1, 'Alex', 'solo', True)
    await service.cancel(20, 1)
    await worker.tick(start - timedelta(minutes=15))
    assert bot.send_message.await_count == 3


async def test_ambiguous_error_not_retried(db):
    sessions, service = db
    await service.save(10, 1, 'Steve', 'team', True)
    bot = AsyncMock()
    bot.send_message.side_effect = TelegramNetworkError(method=SendMessage(chat_id=10, text='x'), message='network')
    async with sessions() as s:
        e = await s.get(Event, 1)
    now = starts(e) - timedelta(minutes=15)
    await Reminders(sessions, bot).tick(now)
    await Reminders(sessions, bot).tick(now)
    assert bot.send_message.await_count == 1
    async with sessions() as s:
        assert (await s.scalar(select(Delivery))).status == 'failed'
