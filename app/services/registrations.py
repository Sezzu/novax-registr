import re
from collections import Counter
from sqlalchemy import select, delete, update, func
from sqlalchemy.exc import IntegrityError
from app.database.models import User, Event, Registration, Referral, Delivery, AdminAction
from app.services.events import available

SOURCES = {'channel', 'tiktok', 'youtube', 'friend', 'unknown'}


class Registrations:
    def __init__(self, sessions):
        self.sessions = sessions

    @staticmethod
    async def recount(s, eid):
        await s.flush()
        count = select(func.count(Registration.id)).where(Registration.event_id == eid, Registration.active.is_(True)).scalar_subquery()
        await s.execute(update(Event).where(Event.id == eid).values(participant_count=count))

    async def ensure(self, uid, eid, source=None, begin=False):
        for attempt in range(3):
            try:
                async with self.sessions.begin() as s:
                    if not await s.get(User, uid):
                        s.add(User(id=uid))
                        await s.flush()
                    if source is not None:
                        found = await s.scalar(select(Referral).where(Referral.user_id == uid, Referral.event_id == eid))
                        if not found:
                            s.add(Referral(user_id=uid, event_id=eid, source=source if source in SOURCES else 'unknown'))
                    if begin:
                        r = await s.scalar(select(Registration).where(Registration.user_id == uid, Registration.event_id == eid))
                        if not r:
                            s.add(Registration(user_id=uid, event_id=eid))
                return
            except IntegrityError:
                if attempt == 2:
                    raise

    async def get(self, uid, eid):
        async with self.sessions() as s:
            return await s.scalar(select(Registration).where(Registration.user_id == uid, Registration.event_id == eid))

    async def save(self, uid, eid, nick, team, reminders):
        if not re.fullmatch(r'[A-Za-z0-9_]{3,16}', nick) or team not in {'team', 'looking', 'solo'} or type(reminders) is not bool:
            raise ValueError('Invalid answers')
        await self.ensure(uid, eid, begin=True)
        async with self.sessions.begin() as s:
            e = await s.scalar(select(Event).where(Event.id == eid).with_for_update())
            if not e or not available(e):
                raise ValueError('Closed event')
            r = await s.scalar(select(Registration).where(Registration.user_id == uid, Registration.event_id == eid).with_for_update())
            r.nick, r.team, r.reminders, r.active, r.completed = nick, team, reminders, True, True
            await s.flush()
            await self.recount(s, eid)
            return r

    async def cancel(self, uid, eid):
        async with self.sessions.begin() as s:
            await s.scalar(select(Event).where(Event.id == eid).with_for_update())
            await s.execute(update(Registration).where(Registration.user_id == uid, Registration.event_id == eid,
                Registration.active.is_(True)).values(active=False, reminders=False,
                cancellations=Registration.cancellations + 1))
            await self.recount(s, eid)

    async def delete_user(self, uid):
        async with self.sessions.begin() as s:
            eids = sorted(await s.scalars(select(Registration.event_id).where(Registration.user_id == uid)))
            for eid in eids:
                await s.scalar(select(Event).where(Event.id == eid).with_for_update())
            for model in (Delivery, Referral, Registration):
                await s.execute(delete(model).where(model.user_id == uid))
            await s.execute(delete(AdminAction).where(AdminAction.admin_id == uid))
            await s.execute(delete(User).where(User.id == uid))
            for eid in eids:
                await self.recount(s, eid)

    async def stats(self, eid):
        async with self.sessions() as s:
            regs = list(await s.scalars(select(Registration).where(Registration.event_id == eid)))
            refs = list(await s.scalars(select(Referral).where(Referral.event_id == eid)))
        active = [r for r in regs if r.active]
        teams = Counter(r.team for r in active)
        completed = sum(r.completed for r in regs)
        return dict(opened=len(refs), started=len(regs), completed=completed, active=len(active),
                    cancellations=sum(r.cancellations for r in regs), reminders=sum(r.reminders for r in active),
                    team=teams['team'], looking=teams['looking'], solo=teams['solo'],
                    sources=dict(Counter(r.source for r in refs)),
                    conversion=100 * sum(r.completed and r.user_id in {f.user_id for f in refs} for r in regs) / len(refs) if refs else 0)
