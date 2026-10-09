import re
from html import escape
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from app.database.models import Event, Registration
from app.services.events import available
from app.keyboards import event_keyboard, teams, consent, buttons, home
from app import texts as t

router = Router()


class Survey(StatesGroup):
    nick = State()
    team = State()
    reminders = State()


def parse_event_payload(payload):
    match = re.fullmatch(r'event_([1-9]\d{0,17})(?:_([A-Za-z0-9]+))?', payload)
    return (int(match[1]), match[2]) if match else None


async def show(message, eid, service, sessions):
    async with sessions() as s:
        e = await s.get(Event, eid)
    if not e:
        await message.answer(t.MISSING)
        return
    r = await service.get(message.chat.id, eid)
    stats = await service.stats(eid)
    if r and r.active:
        await message.answer(t.confirmation(e, r), reply_markup=event_keyboard(eid, True))
    else:
        await message.answer(t.card(e, stats['active']), reply_markup=event_keyboard(eid))
        if not available(e):
            await message.answer(t.registration_notice(e))


@router.message(CommandStart())
async def start(message, state: FSMContext, service, sessions, settings):
    await state.clear()
    parts = (message.text or '').split(maxsplit=1)
    match = parse_event_payload(parts[1]) if len(parts) == 2 else None
    if not match:
        await message.answer(t.WELCOME, reply_markup=(buttons([[('⚙️ Управление сервером', 'adm:home')]] + [[(label, f'home:{key}')] for key, label in t.HOME_BUTTONS.items()]) if message.from_user.id in settings.admins else home()))
        return
    eid, source = match
    async with sessions() as s:
        exists = await s.get(Event, eid)
    if exists:
        await service.ensure(message.from_user.id, eid, source=source or ('channel' if exists.channel_message_id else 'unknown'))
    await show(message, eid, service, sessions)


@router.message(Command('events'))
async def events(message, sessions):
    async with sessions() as s:
        rows = list(await s.scalars(select(Event).order_by(Event.date, Event.id)))
    await message.answer(t.EVENTS_TITLE if rows else t.NO_EVENTS,
        reply_markup=buttons([[(f'⚔️ {t.date_text(e.date)} · {e.time or t.NO_TIME}', f'view:{e.id}')] for e in rows]) if rows else home())


@router.message(Command('my_registration'))
async def mine(message, service, sessions):
    async with sessions() as s:
        ids = list(await s.scalars(select(Registration.event_id).where(Registration.user_id == message.chat.id, Registration.active.is_(True))))
    if not ids:
        await message.answer(t.EMPTY)
    for eid in ids:
        await show(message, eid, service, sessions)


@router.message(Command('privacy'))
async def privacy(message):
    await message.answer(t.PRIVACY)


@router.message(Command('delete_me'))
async def delete_me(message, state: FSMContext, service):
    await state.clear()
    await service.delete_user(message.from_user.id)
    await message.answer(t.DELETED)


@router.message(Command('abort'))
async def abort(message, state: FSMContext):
    await state.clear()
    await message.answer(t.ABORTED)


@router.callback_query(F.data.in_({'events:list', 'home:events', 'home:mine', 'home:privacy'}))
async def navigate(callback, sessions, service):
    await callback.answer()
    if callback.data in {'events:list', 'home:events'}:
        await events(callback.message, sessions)
    elif callback.data == 'home:mine':
        await mine(callback.message, service, sessions)
    else:
        await privacy(callback.message)


@router.callback_query(F.data.regexp(r'^(view|join|edit|cancel|rules|public|arrive):\d+$'))
async def action(callback, state: FSMContext, service, sessions):
    action, value = callback.data.split(':')
    eid = int(value)
    async with sessions() as s:
        e = await s.get(Event, eid)
    if not e:
        await callback.answer(t.MISSING, show_alert=True)
        return
    await callback.answer()
    if action == 'view':
        await show(callback.message, eid, service, sessions)
    elif action in {'join', 'edit'}:
        if not available(e):
            await callback.message.answer(t.registration_notice(e))
            return
        r = await service.get(callback.from_user.id, eid)
        if action == 'join' and r and r.active:
            await show(callback.message, eid, service, sessions)
            return
        await service.ensure(callback.from_user.id, eid, begin=True)
        await state.clear()
        await state.set_state(Survey.nick)
        await state.update_data(eid=eid)
        await callback.message.answer(t.NICK)
    elif action == 'cancel':
        await service.cancel(callback.from_user.id, eid)
        await state.clear()
        await callback.message.answer(t.CANCELLED)
    elif action == 'rules':
        await callback.message.answer(escape(e.rules) if e.rules else t.RULES_PENDING)
    elif action == 'public':
        await callback.message.answer(t.public_stats(await service.stats(eid)))
    else:
        await callback.message.answer(t.ARRIVED)


@router.message(Survey.nick, F.text, ~F.text.startswith('/'))
async def nick(message, state: FSMContext):
    value = message.text.strip()
    if not re.fullmatch(r'[A-Za-z0-9_]{3,16}', value):
        await message.answer(t.NICK)
        return
    await state.update_data(nick=value)
    await state.set_state(Survey.team)
    await message.answer(t.TEAM, reply_markup=teams())


@router.callback_query(Survey.team, F.data.in_({'team:team', 'team:looking', 'team:solo'}))
async def team(callback, state: FSMContext):
    await callback.answer()
    await state.update_data(team=callback.data.split(':')[1])
    await state.set_state(Survey.reminders)
    await callback.message.answer(t.REMINDERS, reply_markup=consent())


@router.callback_query(Survey.reminders, F.data.in_({'consent:yes', 'consent:no'}))
async def reminders(callback, state: FSMContext, service, sessions):
    await callback.answer()
    data = await state.get_data()
    try:
        r = await service.save(callback.from_user.id, data['eid'], data['nick'], data['team'], callback.data == 'consent:yes')
    except ValueError:
        await state.clear()
        await callback.message.answer(t.CLOSED)
        return
    await state.clear()
    async with sessions() as s:
        e = await s.get(Event, data['eid'])
    await callback.message.answer(t.confirmation(e, r), reply_markup=event_keyboard(e.id, True))


@router.callback_query()
async def stale(callback):
    await callback.answer(t.EXPIRED, show_alert=True)


@router.message()
async def fallback(message):
    await message.answer(t.WELCOME, reply_markup=home())
