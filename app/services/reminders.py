from app.diagnostics import error_context
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.database.models import Event, Registration, Delivery
from app.services.events import starts
from app.services.telegram import send
from app.keyboards import buttons
from app import texts as t


class Reminders:
    def __init__(self, sessions, bot, morning_hour=9):
        self.sessions, self.bot, self.morning_hour = sessions, bot, morning_hour

    async def tick(self, now=None):
        now = now or datetime.now(timezone.utc)
        async with self.sessions() as s:
            events = list(await s.scalars(select(Event)))
        for e in events:
            start = starts(e)
            if not start or now >= start:
                continue
            local = start.astimezone(ZoneInfo(e.timezone))
            morning = local.replace(hour=self.morning_hour, minute=0, second=0).astimezone(timezone.utc)
            schedule = [('morning', morning, min(morning + timedelta(hours=1), start)),
                        ('two_hours', start - timedelta(hours=2), start - timedelta(hours=2) + timedelta(minutes=10)),
                        ('fifteen', start - timedelta(minutes=15), start)]
            for kind, due, expires in schedule:
                if not due <= now < expires:
                    continue
                async with self.sessions() as s:
                    users = list(await s.scalars(select(Registration.user_id).where(Registration.event_id == e.id, Registration.active.is_(True), Registration.reminders.is_(True))))
                for uid in users:
                    try:
                        async with self.sessions.begin() as s:
                            r = await s.scalar(select(Registration).where(Registration.event_id == e.id, Registration.user_id == uid))
                            if not r or not r.active or not r.reminders:
                                continue
                            s.add(Delivery(event_id=e.id, user_id=uid, kind=kind))
                    except IntegrityError:
                        continue
                    markup = buttons([[(t.BUTTONS['arrive'], f'arrive:{e.id}')]]) if kind == 'fifteen' else None
                    ok = await send(self.bot, uid, t.reminder(e, kind), reply_markup=markup)
                    async with self.sessions.begin() as s:
                        await s.execute(update(Delivery).where(Delivery.event_id == e.id, Delivery.user_id == uid, Delivery.kind == kind).values(status='sent' if ok else 'failed'))

    async def run(self):
        while True:
            try:
                await self.tick()
            except Exception as exc:
                logging.getLogger('novax').warning('reminder_cycle_failed', extra=error_context(exc))
            await asyncio.sleep(20)
