import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.methods import SendPhoto, SendMessage
from sqlalchemy import select
from app.configuration import Settings
from app.database.models import Event
from app.services.channel import Publisher, check_channel, ChannelError, AlreadyPublished, event_link
from app.handlers.user import parse_event_payload
from app import texts as t


def fake_bot():
    me = SimpleNamespace(id=123, username='NovaXDemoBot')
    bot = AsyncMock()
    bot.get_me.return_value = me
    bot.me.return_value = me
    bot.get_chat.return_value = SimpleNamespace(id=-10012345, type='channel', title='NovaX')
    bot.get_chat_member.return_value = SimpleNamespace(status='administrator', can_post_messages=True)
    bot.send_message.return_value = SimpleNamespace(message_id=42)
    bot.send_photo.return_value = SimpleNamespace(message_id=43)
    return bot


def config(channel='@NovaXMC'):
    return Settings(bot_token='123456:secret', admin_ids='99', channel_id=channel, _env_file=None)


@pytest.mark.parametrize('payload,expected', [('event_1', (1, None)), ('event_99_channel', (99, 'channel')),
    ('event_0', None), ('anything', None), ('event_999999999999999999999999', None)])
def test_deep_link_parsing(payload, expected):
    assert parse_event_payload(payload) == expected


async def test_generated_deep_link():
    assert await event_link(fake_bot(), 123) == 'https://t.me/NovaXDemoBot?start=event_123'


@pytest.mark.parametrize('status,permission,chat_type', [('member', False, 'channel'),
    ('administrator', False, 'channel'), ('administrator', True, 'supergroup')])
async def test_permissions_rejected(status, permission, chat_type):
    bot = fake_bot()
    bot.get_chat.return_value.type = chat_type
    bot.get_chat_member.return_value.status = status
    bot.get_chat_member.return_value.can_post_messages = permission
    with pytest.raises(ChannelError, match='Бот не может публиковать'):
        await check_channel(bot, config())
    bot.send_message.assert_not_awaited()


async def test_permissions_and_numeric_id():
    bot = fake_bot()
    access = await check_channel(bot, config('-10012345'))
    assert access.id == -10012345
    bot.get_chat.assert_awaited_once_with(-10012345)


async def test_publish_once_and_persist_after_restart(db):
    sessions, _ = db
    bot = fake_bot()
    post = await Publisher(sessions, bot, config()).publish(1)
    assert post.message_id == 42
    with pytest.raises(AlreadyPublished):
        await Publisher(sessions, bot, config()).publish(1)
    bot.send_message.assert_awaited_once()
    assert bot.send_message.call_args.kwargs['parse_mode'] == 'HTML'
    button = bot.send_message.call_args.kwargs['reply_markup'].inline_keyboard[0][0]
    assert button.text == '⚔️ Буду участвовать'
    assert button.url.endswith('start=event_1')
    async with sessions() as s:
        e = await s.get(Event, 1)
        assert e.channel_message_id == 42 and e.publication_status == 'published'


async def test_concurrent_publish_no_duplicate(db):
    sessions, _ = db
    bot = fake_bot()
    results = await asyncio.gather(*(Publisher(sessions, bot, config()).publish(1) for _ in range(2)), return_exceptions=True)
    assert sum(isinstance(item, AlreadyPublished) for item in results) == 1
    bot.send_message.assert_awaited_once()


async def test_photo_and_fallback(db):
    sessions, _ = db
    bot = fake_bot()
    async with sessions.begin() as s:
        (await s.get(Event, 1)).cover_image = 'https://example.org/cover.jpg'
    bot.send_photo.side_effect = TelegramBadRequest(method=SendPhoto(chat_id=-10012345, photo='x'), message='failed to get HTTP URL content')
    post = await Publisher(sessions, bot, config()).publish(1)
    assert post.message_id == 42
    bot.send_photo.assert_awaited_once()
    bot.send_message.assert_awaited_once()


async def test_photo_publication(db):
    sessions, _ = db
    bot = fake_bot()
    async with sessions.begin() as s:
        (await s.get(Event, 1)).cover_image = 'https://example.org/cover.jpg'
    await Publisher(sessions, bot, config()).publish(1)
    bot.send_message.assert_not_awaited()
    async with sessions() as s:
        assert (await s.get(Event, 1)).channel_is_photo


async def test_uncertain_network_result_never_repeated(db):
    sessions, _ = db
    bot = fake_bot()
    bot.send_message.side_effect = TelegramNetworkError(method=SendMessage(chat_id=-10012345, text='x'), message='network')
    with pytest.raises(ChannelError):
        await Publisher(sessions, bot, config()).publish(1)
    with pytest.raises(AlreadyPublished):
        await Publisher(sessions, bot, config()).publish(1)
    bot.send_message.assert_awaited_once()


async def test_counter_refresh_throttle_and_delete(db):
    sessions, registrations = db
    bot = fake_bot()
    publisher = Publisher(sessions, bot, config())
    await publisher.publish(1)
    await registrations.save(10, 1, 'Steve', 'team', True)
    async with sessions() as s:
        e = await s.get(Event, 1)
        assert e.participant_count == 1
        initial = e.channel_last_edit
    await publisher.refresh(initial + 299)
    bot.edit_message_text.assert_not_awaited()
    await publisher.refresh(initial + 300)
    bot.edit_message_text.assert_awaited_once()
    assert '1 игроков' in bot.edit_message_text.call_args.args[0]
    await registrations.delete_user(10)
    async with sessions() as s:
        assert (await s.get(Event, 1)).participant_count == 0
    await publisher.refresh(initial + 301)
    assert bot.edit_message_text.await_count == 1
    await publisher.refresh(initial + 600)
    assert bot.edit_message_text.await_count == 2


async def test_photo_caption_refresh(db):
    sessions, registrations = db
    bot = fake_bot()
    async with sessions.begin() as s:
        (await s.get(Event, 1)).cover_image = 'https://example.org/cover.jpg'
    publisher = Publisher(sessions, bot, config())
    await publisher.publish(1)
    await registrations.save(10, 1, 'Steve', 'team', True)
    await publisher.refresh(int(time.time()) + 301)
    bot.edit_message_caption.assert_awaited_once()


def test_html_escaping():
    e = SimpleNamespace(date='2026-10-11', time='18:00', timezone='Europe/Moscow', ip='<server>', description='<evil>&', participant_count=2)
    post = t.channel_post(e, 2)
    assert '&lt;evil&gt;&amp;' in post and '&lt;server&gt;' in post
    assert '<evil>' not in post
