from app.diagnostics import error_context
import asyncio
import hashlib
import logging
import time
from pathlib import Path
from dataclasses import dataclass
from aiogram.types import FSInputFile
from aiogram.utils.deep_linking import create_start_link
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramRetryAfter, TelegramNetworkError, TelegramServerError
from sqlalchemy import select, update
from app.database.models import Event
from app.keyboards import channel
from app import texts as t


class ChannelError(Exception):
    pass


class AlreadyPublished(ChannelError):
    pass


@dataclass
class ChannelAccess:
    id: int
    title: str


async def check_channel(bot, settings):
    if not settings.channel_id:
        raise ChannelError(t.CHANNEL_ACCESS_ERROR)
    try:
        me = await bot.get_me()
        chat = await bot.get_chat(settings.channel_target)
        if chat.type != 'channel':
            raise ChannelError(t.CHANNEL_ACCESS_ERROR)
        member = await bot.get_chat_member(chat.id, me.id)
        if member.status not in {'administrator', 'creator'} or (member.status != 'creator' and not member.can_post_messages):
            raise ChannelError(t.CHANNEL_ACCESS_ERROR)
        return ChannelAccess(chat.id, chat.title or '')
    except TelegramAPIError as exc:
        logging.getLogger('novax').warning('channel_access_failed', extra=error_context(exc))
        raise ChannelError(t.CHANNEL_ACCESS_ERROR) from None


async def event_link(bot, eid):
    return await create_start_link(bot, f'event_{eid}')


def image_input(value):
    if value.startswith(('https://', 'http://')):
        return value
    path = Path(value)
    if path.is_file():
        return FSInputFile(path)
    if '/' not in value and '\\' not in value and len(value) > 30:
        return value  # Telegram file_id.
    raise FileNotFoundError('Cover not found')


def content_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


async def api_call(call):
    for attempt in range(3):
        try:
            return await call()
        except TelegramRetryAfter as exc:
            if attempt == 2:
                raise
            await asyncio.sleep(exc.retry_after)


async def send_post(bot, target, e, markup, text=None):
    text = text or t.channel_post(e, e.participant_count)
    if e.cover_image:
        try:
            photo = image_input(e.cover_image)
            message = await api_call(lambda: bot.send_photo(target, photo=photo, caption=text, parse_mode='HTML', reply_markup=markup))
            return message, True
        except (FileNotFoundError, TelegramBadRequest):
            # A rejected photo was not delivered; text fallback is safe.
            pass
    message = await api_call(lambda: bot.send_message(target, text, parse_mode='HTML', reply_markup=markup))
    return message, False


class Publisher:
    def __init__(self, sessions, bot, settings):
        self.sessions, self.bot, self.settings = sessions, bot, settings

    async def publish(self, eid):
        access = await check_channel(self.bot, self.settings)
        markup = channel(await event_link(self.bot, eid))
        async with self.sessions.begin() as s:
            claimed = await s.execute(update(Event).where(Event.id == eid,
                Event.publication_status.in_(['unpublished', 'failed']), Event.channel_message_id.is_(None)
            ).values(publication_status='publishing'))
            if claimed.rowcount != 1:
                raise AlreadyPublished(t.ALREADY_PUBLISHED)
            e = await s.get(Event, eid)
        text = t.channel_post(e, e.participant_count)
        try:
            message, is_photo = await send_post(self.bot, access.id, e, markup, text)
        except (TelegramNetworkError, TelegramServerError):
            async with self.sessions.begin() as s:
                await s.execute(update(Event).where(Event.id == eid).values(publication_status='uncertain'))
            raise ChannelError(t.PUBLICATION_UNCERTAIN) from None
        except (TelegramAPIError, OSError):
            async with self.sessions.begin() as s:
                await s.execute(update(Event).where(Event.id == eid).values(publication_status='failed'))
            raise ChannelError(t.PUBLICATION_FAILED) from None
        async with self.sessions.begin() as s:
            await s.execute(update(Event).where(Event.id == eid).values(publication_status='published',
                channel_message_id=message.message_id, channel_chat_id=str(access.id), channel_is_photo=is_photo,
                channel_last_edit=int(time.time()), channel_content_hash=content_hash(text)))
        return message

    async def test(self, eid):
        access = await check_channel(self.bot, self.settings)
        markup = channel(await event_link(self.bot, eid))
        return await api_call(lambda: self.bot.send_message(access.id, t.CHANNEL_TEST_POST,
                             parse_mode='HTML', reply_markup=markup))

    async def refresh(self, now=None):
        now = int(time.time()) if now is None else now
        async with self.sessions() as s:
            events = list(await s.scalars(select(Event).where(Event.publication_status == 'published',
                Event.channel_message_id.is_not(None), Event.channel_last_edit <= now - 300)))
        for e in events:
            text = t.channel_post(e, e.participant_count)
            if content_hash(text) == e.channel_content_hash:
                continue
            async with self.sessions.begin() as s:
                claim = await s.execute(update(Event).where(Event.id == e.id, Event.channel_last_edit <= now - 300,
                    Event.publication_status == 'published').values(channel_last_edit=now))
                if claim.rowcount != 1:
                    continue
            target = int(e.channel_chat_id) if e.channel_chat_id.lstrip('-').isdigit() else e.channel_chat_id
            markup = channel(await event_link(self.bot, e.id))
            try:
                if e.channel_is_photo:
                    await self.bot.edit_message_caption(chat_id=target, message_id=e.channel_message_id,
                        caption=text, parse_mode='HTML', reply_markup=markup)
                else:
                    await self.bot.edit_message_text(text, chat_id=target, message_id=e.channel_message_id,
                        parse_mode='HTML', reply_markup=markup)
            except TelegramRetryAfter as exc:
                async with self.sessions.begin() as s:
                    await s.execute(update(Event).where(Event.id == e.id).values(channel_last_edit=max(now, now + exc.retry_after - 300)))
                continue
            except TelegramBadRequest as exc:
                if 'message is not modified' not in exc.message.lower():
                    logging.getLogger('novax').warning('channel_edit_rejected', extra=error_context(exc))
                    continue
            except TelegramAPIError as exc:
                logging.getLogger('novax').warning('channel_edit_failed', extra=error_context(exc))
                continue
            async with self.sessions.begin() as s:
                await s.execute(update(Event).where(Event.id == e.id).values(channel_content_hash=content_hash(text)))

    async def run(self):
        while True:
            try:
                await self.refresh()
            except Exception as exc:
                logging.getLogger('novax').warning('channel_refresh_failed', extra=error_context(exc))
            await asyncio.sleep(20)
