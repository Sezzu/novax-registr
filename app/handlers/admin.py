import asyncio
import csv
import io
import secrets
import time
from html import escape
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from sqlalchemy import select
from app.database.models import Event, Registration, Referral, AdminAction
from app.handlers.middleware import is_admin
from app.services.events import validate_event, starts, can_open, opening_timestamp
from app.services.telegram import send
from app.keyboards import approve, edit_fields, buttons
from app.services.channel import Publisher, ChannelError, AlreadyPublished, send_post
from app import texts as t
from datetime import datetime, timezone
from zoneinfo import ZoneInfoNotFoundError

router = Router()
FIELDS = {'date', 'time', 'timezone', 'description', 'ip', 'versions', 'rules', 'cover_image', 'registration_opens_at'}


def apply_field(e, field, value):
    if field == 'registration_opens_at':
        value = opening_timestamp(value, e.timezone)
    elif field == 'cover_image' and value and value.lower() == t.REMOVE_COVER:
        value = None
    setattr(e, field, value)
    validate_event(e)
    if e.opened and not can_open(e):
        e.opened = False


class PostEdit(StatesGroup):
    value = State()
    broadcast = State()
    create_date = State()


async def selected_event(sessions, arg='', timezone_name='Europe/Moscow'):
    async with sessions() as s:
        if arg.strip():
            return await s.get(Event, int(arg.strip()))
        from zoneinfo import ZoneInfo
        today = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
        upcoming = await s.scalar(select(Event).where(Event.date >= today).order_by(Event.date, Event.id).limit(1))
        return upcoming or await s.scalar(select(Event).order_by(Event.date.desc(), Event.id.desc()).limit(1))


async def publication_preview(message, state, e, bot):
    token = secrets.token_hex(8)
    await state.clear()
    await state.update_data(preview={'token': token, 'eid': e.id, 'cmd': 'publish', 'at': time.time(), 'event': snapshot(e)})
    await send_post(bot, message.chat.id, e, approve(token, publication=True))


def snapshot(e):
    return {field: getattr(e, field) for field in sorted(FIELDS | {'opened'})}


async def authorized(event, settings):
    if is_admin(event.from_user.id, settings):
        return True
    await event.answer(t.DENIED)
    return False


def audit(s, uid, action, eid):
    s.add(AdminAction(admin_id=uid, action=action, event_id=eid, timestamp=int(time.time())))


@router.message(Command('admin', 'create', 'set', 'open', 'close', 'stats', 'export', 'publish', 'publish_event', 'edit_event', 'channel_test', 'broadcast'))
async def command(message, settings, sessions, service, state: FSMContext, bot):
    if not await authorized(message, settings):
        return
    parts = message.text.split(maxsplit=1)
    cmd = parts[0].split('@')[0][1:]
    arg = parts[1] if len(parts) > 1 else ''
    if cmd == 'admin':
        await state.clear()
        await admin_home(message, sessions)
        return
    try:
        if cmd in {'publish', 'publish_event', 'edit_event', 'channel_test'}:
            e = await selected_event(sessions, arg, settings.default_timezone)
            if not e:
                await message.answer(t.MISSING)
                return
            if cmd == 'channel_test':
                try:
                    post = await Publisher(sessions, bot, settings).test(e.id)
                    await message.answer(t.CHANNEL_TEST_SENT.format(id=post.message_id))
                    async with sessions.begin() as s:
                        audit(s, message.from_user.id, cmd, e.id)
                except ChannelError as exc:
                    await message.answer(str(exc))
                return
            if cmd == 'edit_event' or e.publication_status == 'published':
                await state.clear()
                await state.update_data(edit_eid=e.id, edit_published=e.publication_status == 'published')
                await message.answer(t.EDIT_PROMPT, reply_markup=edit_fields(e.id))
                return
            if e.publication_status not in {'unpublished', 'failed'}:
                await message.answer(t.ALREADY_PUBLISHED if e.publication_status != 'uncertain' else t.PUBLICATION_UNCERTAIN)
                return
            await publication_preview(message, state, e, bot)
            return
        if cmd == 'create':
            date, clock, zone, description = [p.strip() for p in arg.split('|', 3)]
            zone = zone if zone and zone != '-' else settings.default_timezone
            e = Event(date=date, time=clock, timezone=zone, description=description, ip='mcnovax.space', versions='Java 1.21.4', rules='', opened=False)
            validate_event(e)
            async with sessions.begin() as s:
                s.add(e)
                await s.flush()
                audit(s, message.from_user.id, cmd, e.id)
            await message.answer(t.SAVED.format(id=e.id))
            return
        if cmd == 'stats' and not arg.strip():
            closest = await selected_event(sessions, timezone_name=settings.default_timezone)
            if not closest:
                await message.answer(t.MISSING)
                return
            arg = str(closest.id)
        arguments = arg.split(maxsplit=1)
        eid = int(arguments[0])
        async with sessions() as s:
            e = await s.get(Event, eid)
        if not e:
            await message.answer(t.MISSING)
            return
        if cmd in {'set', 'open', 'close'}:
            async with sessions.begin() as s:
                e = await s.get(Event, eid)
                if cmd == 'set':
                    field, value = arguments[1].split(maxsplit=1)
                    if field not in FIELDS:
                        raise ValueError('Invalid field')
                    apply_field(e, field, value.strip())
                else:
                    if cmd == 'open' and not can_open(e):
                        await message.answer(t.NOT_READY)
                        return
                    e.opened = cmd == 'open'
                audit(s, message.from_user.id, cmd, eid)
            await message.answer(t.SAVED.format(id=eid))
        elif cmd == 'stats':
            await message.answer(escape(t.stats(await service.stats(eid))))
        elif cmd == 'export':
            async with sessions.begin() as s:
                rows = list(await s.scalars(select(Registration).where(Registration.event_id == eid, Registration.active.is_(True))))
                refs = {r.user_id: r.source for r in await s.scalars(select(Referral).where(Referral.event_id == eid))}
                audit(s, message.from_user.id, cmd, eid)
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(t.CSV_HEADER)
            for r in rows:
                writer.writerow([r.user_id, r.nick, t.TEAMS[r.team], r.reminders, refs.get(r.user_id, 'unknown')])
            await message.answer_document(BufferedInputFile(output.getvalue().encode('utf-8-sig'), filename=f'novax-{eid}.csv'))
        else:
            text = escape(arguments[1].strip())
            if not text or len(text) > 3000:
                raise ValueError('Invalid length')
            token = secrets.token_hex(8)
            await state.clear()
            await state.update_data(preview={'token': token, 'eid': eid, 'cmd': cmd, 'text': text, 'at': time.time(), 'event': snapshot(e)})
            await message.answer(t.PREVIEW.format(text=text), reply_markup=approve(token))
    except (ValueError, IndexError, KeyError, ZoneInfoNotFoundError):
        await message.answer(t.INVALID + '\n\n' + t.ADMIN_HELP)


@router.callback_query(F.data.startswith('confirm:'))
async def confirm(callback, settings, state: FSMContext, sessions, bot):
    if not await authorized(callback, settings):
        return
    data = (await state.get_data()).get('preview')
    if not data or data['token'] != callback.data.split(':')[1] or time.time() - data['at'] > 600:
        await callback.answer(t.EXPIRED, show_alert=True)
        return
    await state.clear()
    await callback.answer()
    async with sessions.begin() as s:
        audit(s, callback.from_user.id, data['cmd'], data['eid'])
        exists = await s.get(Event, data['eid'])
    if not exists:
        await callback.message.answer(t.MISSING)
        return
    if data['cmd'] == 'publish' and snapshot(exists) != data['event']:
        await callback.message.answer(t.EXPIRED)
        return
    sent = failed = 0
    if data['cmd'] == 'publish':
        try:
            post = await Publisher(sessions, bot, settings).publish(data['eid'])
            await callback.message.answer(t.PUBLISHED.format(id=post.message_id))
        except (ChannelError, AlreadyPublished) as exc:
            await callback.message.answer(str(exc))
        return
    else:
        async with sessions() as s:
            ids = list(await s.scalars(select(Registration.user_id).where(Registration.event_id == data['eid'], Registration.active.is_(True))))
        for uid in ids:
            async with sessions() as s:
                r = await s.scalar(select(Registration).where(Registration.user_id == uid, Registration.event_id == data['eid']))
            if not r or not r.active:
                continue
            ok = await send(bot, uid, data['text'])
            sent += int(ok)
            failed += int(not ok)
            await asyncio.sleep(0.05)
    await callback.message.answer(t.SENT.format(sent=sent, failed=failed))


@router.callback_query(F.data.startswith('postedit:'))
async def choose_edit(callback, settings, state: FSMContext):
    if not await authorized(callback, settings):
        return
    data = (await state.get_data()).get('preview')
    if not data or data['cmd'] != 'publish' or data['token'] != callback.data.split(':')[1] or time.time() - data['at'] > 600:
        await callback.answer(t.EXPIRED, show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await state.update_data(edit_eid=data['eid'])
    await callback.message.answer(t.EDIT_PROMPT, reply_markup=edit_fields(data['eid']))


@router.callback_query(F.data.regexp(r'^(field|preview):\d+(?::[a-z_]+)?$'))
async def edit_field(callback, settings, state: FSMContext, sessions, bot):
    if not await authorized(callback, settings):
        return
    parts = callback.data.split(':')
    eid = int(parts[1])
    if (await state.get_data()).get('edit_eid') != eid:
        await callback.answer(t.EXPIRED, show_alert=True)
        return
    e = await selected_event(sessions, str(eid))
    if not e:
        await callback.answer(t.MISSING, show_alert=True)
        return
    if e.publication_status not in {'unpublished', 'failed'} and not ((await state.get_data()).get('edit_published') and e.publication_status == 'published'):
        await state.clear()
        await callback.answer(t.ALREADY_PUBLISHED, show_alert=True)
        return
    await callback.answer()
    if parts[0] == 'preview':
        if e.publication_status == 'published':
            await state.set_state(None)
            await callback.message.answer(t.channel_post(e, e.participant_count), reply_markup=edit_fields(e.id))
            return
        await publication_preview(callback.message, state, e, bot)
        return
    field = parts[2] if len(parts) == 3 else ''
    if field not in FIELDS:
        await callback.message.answer(t.INVALID)
        return
    await state.update_data(edit_field=field)
    await state.set_state(PostEdit.value)
    prompt = t.EDIT_COVER if field == 'cover_image' else t.OPENING_FORMAT if field == 'registration_opens_at' else t.EDIT_VALUE.format(field=t.EDIT_LABELS[field])
    if field == 'date':
        prompt += '\nФормат: ГГГГ-ММ-ДД, например 2026-10-11.'
    elif field == 'time':
        prompt += '\nФормат: ЧЧ:ММ, например 20:00.'
    rows = []
    if field == 'timezone':
        rows = [[('🇷🇺 Москва', f'preset:{eid}:moscow'), ('🌍 UTC', f'preset:{eid}:utc')]]
    elif field == 'cover_image':
        rows = [[('🗑 Убрать обложку', f'preset:{eid}:remove_cover')]]
    await callback.message.answer(prompt, reply_markup=buttons(rows + [[('◀️ К событию', f'adm:event:{eid}')]]))


@router.message(PostEdit.value, F.text | F.photo)
async def edit_value(message, settings, state: FSMContext, sessions, bot):
    if not await authorized(message, settings):
        return
    if message.text and message.text.startswith('/'):
        await message.answer(t.INVALID)
        return
    data = await state.get_data()
    field, eid = data['edit_field'], data['edit_eid']
    if message.photo:
        if field != 'cover_image':
            await message.answer(t.INVALID)
            return
        photo = message.photo[-1]
        if abs(photo.width / photo.height - 16 / 9) > 0.04:
            await message.answer(t.COVER_RATIO_ERROR)
            return
        value = photo.file_id
    else:
        value = message.text.strip()
        if field == 'cover_image' and value.lower() == t.REMOVE_COVER:
            value = None
    try:
        async with sessions.begin() as s:
            e = await s.get(Event, eid)
            if not e:
                await state.clear()
                await message.answer(t.MISSING)
                return
            if e.publication_status not in {'unpublished', 'failed'} and not (data.get('edit_published') and e.publication_status == 'published'):
                await state.clear()
                await message.answer(t.ALREADY_PUBLISHED)
                return
            apply_field(e, field, value)
            audit(s, message.from_user.id, 'edit_preview', eid)
        if e.publication_status == 'published':
            await state.set_state(None)
            await message.answer(t.POST_UPDATED, reply_markup=edit_fields(e.id))
        else:
            await state.set_state(None)
            await message.answer('✅ Изменения сохранены', reply_markup=edit_fields(e.id))
    except (ValueError, ZoneInfoNotFoundError):
        await message.answer(t.INVALID)


@router.callback_query(F.data == 'abort')
async def abort(callback, state: FSMContext):
    await state.clear()
    await callback.answer(t.ABORTED)


async def admin_home(message, sessions):
    async with sessions() as s:
        rows = list(await s.scalars(select(Event).order_by(Event.date.desc(), Event.id.desc())))
    await message.answer('⚙️ <b>Управление NovaX</b>\n\nВыберите событие или создайте новое.',
        reply_markup=buttons([[(f'⚔️ {t.date_text(e.date)} · {e.time or t.NO_TIME}', f'adm:event:{e.id}')] for e in rows]
            + [[('➕ Создать событие', 'adm:create')]]))


async def admin_card(message, e):
    await message.answer(f'⚙️ <b>Событие №{e.id}</b>\n🗓 {escape(e.date)} · {escape(e.time or t.NO_TIME)}\n'
        f'🌍 {escape(e.timezone)}\n👥 Участников: {e.participant_count}\n'
        f'Регистрация: {"открыта" if e.opened else "закрыта"}', reply_markup=buttons([
        [('✏️ Настройки события', f'adm:edit:{e.id}')],
        [('👀 Предпросмотр / публикация', f'adm:publish:{e.id}')],
        [('🔓 Открыть регистрацию', f'adm:open:{e.id}'), ('🔒 Закрыть', f'adm:close:{e.id}')],
        [('📊 Статистика', f'adm:stats:{e.id}'), ('📥 Скачать участников', f'adm:export:{e.id}')],
        [('📣 Сообщение участникам', f'adm:broadcast:{e.id}')],
        [('◀️ Все события', 'adm:home')]]))


@router.callback_query(F.data.startswith('adm:'))
async def admin_menu(callback, settings, sessions, service, state: FSMContext, bot):
    if not await authorized(callback, settings):
        return
    await callback.answer()
    await state.clear()
    parts = callback.data.split(':')
    action = parts[1]
    if action == 'home':
        await admin_home(callback.message, sessions)
        return
    if action == 'create':
        await state.set_state(PostEdit.create_date)
        await callback.message.answer('🗓 Введите дату нового события: ГГГГ-ММ-ДД',
            reply_markup=buttons([[('❌ Отмена', 'adm:home')]]))
        return
    if len(parts) != 3 or not parts[2].isdigit():
        return
    eid = int(parts[2])
    e = await selected_event(sessions, str(eid))
    if not e:
        await callback.message.answer(t.MISSING)
        return
    if action == 'event':
        await admin_card(callback.message, e)
    elif action == 'edit':
        await state.update_data(edit_eid=eid, edit_published=e.publication_status == 'published')
        await callback.message.answer(t.EDIT_PROMPT, reply_markup=edit_fields(eid))
    elif action == 'broadcast':
        await state.update_data(broadcast_eid=eid)
        await state.set_state(PostEdit.broadcast)
        await callback.message.answer('📣 Введите сообщение для участников. Перед отправкой покажу предпросмотр.',
            reply_markup=buttons([[('❌ Отмена', f'adm:event:{eid}')]]))
    elif action in {'publish', 'open', 'close', 'stats', 'export'}:
        # Reuse existing audited commands with the actual administrator identity.
        message = callback.message.model_copy(update={'from_user': callback.from_user, 'text': f'/{action} {eid}'})
        await command(message, settings, sessions, service, state, bot)
        if action in {'open', 'close', 'stats', 'export'}:
            await admin_card(callback.message, await selected_event(sessions, str(eid)))


@router.message(PostEdit.broadcast, F.text)
async def broadcast_value(message, settings, sessions, service, state: FSMContext, bot):
    if not await authorized(message, settings):
        return
    eid = (await state.get_data())['broadcast_eid']
    proxy = message.model_copy(update={'text': f'/broadcast {eid} {message.text}'})
    await command(proxy, settings, sessions, service, state, bot)


@router.message(PostEdit.create_date, F.text)
async def create_date(message, settings, sessions, state: FSMContext):
    if not await authorized(message, settings):
        return
    try:
        e = Event(date=message.text.strip(), time=None, timezone=settings.default_timezone,
            description='Новое событие NovaX', ip='mcnovax.space', versions='Java 1.21.4', rules='', opened=False)
        validate_event(e)
    except (ValueError, ZoneInfoNotFoundError):
        await message.answer('Введите корректную дату в формате ГГГГ-ММ-ДД.')
        return
    async with sessions.begin() as s:
        s.add(e)
        await s.flush()
        audit(s, message.from_user.id, 'create', e.id)
    await state.clear()
    await state.update_data(edit_eid=e.id, edit_published=False)
    await message.answer('✅ Событие создано. Настройте его поля:', reply_markup=edit_fields(e.id))


@router.callback_query(F.data.startswith('preset:'))
async def field_preset(callback, settings, state: FSMContext, sessions, bot):
    if not await authorized(callback, settings):
        return
    parts = callback.data.split(':')
    data = await state.get_data()
    options = {'moscow': ('timezone', 'Europe/Moscow'), 'utc': ('timezone', 'UTC'),
               'remove_cover': ('cover_image', t.REMOVE_COVER)}
    option = options.get(parts[-1])
    if len(parts) != 3 or not option or str(data.get('edit_eid')) != parts[1] or data.get('edit_field') != option[0] or await state.get_state() != PostEdit.value.state:
        await callback.answer(t.EXPIRED, show_alert=True)
        return
    await callback.answer()
    message = callback.message.model_copy(update={'from_user': callback.from_user, 'text': option[1], 'photo': None})
    await edit_value(message, settings, state, sessions, bot)
