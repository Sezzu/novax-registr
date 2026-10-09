from datetime import datetime, timezone
from unittest.mock import AsyncMock
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import Update, Message, Chat, User, CallbackQuery
from aiogram.methods import SendMessage
from app.configuration import Settings
from app.handlers import user, admin
from types import SimpleNamespace


async def test_complete_user_and_admin_flow(db):
    sessions, service = db
    bot = Bot('123456:abcdefghijklmnopqrstuvwxyz123456789')
    bot.session = AsyncMock()
    bot.session.return_value = True
    async def session_reply(bot, method, **kwargs):
        return SimpleNamespace(message_id=123) if isinstance(method, SendMessage) else True
    bot.session.side_effect = session_reply
    bot.get_me = AsyncMock(return_value=User(id=123456, is_bot=True, first_name='NovaX', username='NovaXDemoBot'))
    bot.get_chat = AsyncMock(return_value=SimpleNamespace(id=-10012345, type='channel', title='NovaX'))
    bot.get_chat_member = AsyncMock(return_value=SimpleNamespace(status='administrator', can_post_messages=True))
    dp = Dispatcher(storage=MemoryStorage(), events_isolation=SimpleEventIsolation())
    dp.include_router(admin.router)
    dp.include_router(user.router)
    settings = Settings(bot_token='123456:secret', admin_ids='99', channel_id='@novax', _env_file=None)
    counter = 0

    async def feed(text=None, callback=None, uid=10):
        nonlocal counter
        counter += 1
        actor = User(id=uid, is_bot=False, first_name='Not stored')
        message = Message(message_id=counter, date=datetime.now(timezone.utc), chat=Chat(id=uid, type='private'),
                          from_user=(User(id=123456, is_bot=True, first_name='NovaX') if callback else actor), text=text or 'card')
        update = Update(update_id=counter, message=message) if callback is None else Update(update_id=counter,
            callback_query=CallbackQuery(id=str(counter), from_user=actor, chat_instance='x', data=callback, message=message))
        await dp.feed_update(bot, update, settings=settings, sessions=sessions, service=service)

    await feed('/start event_1_channel')
    await feed(callback='join:1')
    await feed('Invalid-nick')
    assert not (await service.get(10, 1)).active
    await feed('Steve')
    await feed(callback='team:looking')
    await feed(callback='consent:yes')
    assert (await service.get(10, 1)).nick == 'Steve'
    await feed(callback='consent:yes')  # stale button
    assert (await service.stats(1))['active'] == 1
    await feed(callback='edit:1')
    await feed('Alex_1')
    await feed(callback='team:solo')
    await feed(callback='consent:no')
    assert (await service.get(10, 1)).nick == 'Alex_1'
    assert not (await service.get(10, 1)).reminders
    await feed(callback='public:1')
    public = bot.session.call_args.args[1]
    assert isinstance(public, SendMessage) and 'Alex_1' not in public.text

    # Broadcast must not send anything to the participant before confirmation.
    bot.session.reset_mock()
    await feed('/broadcast 1 Hello NovaX', uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert all(method.chat_id == 99 for method in sent)
    preview = sent[-1]
    token = preview.reply_markup.inline_keyboard[0][0].callback_data
    await feed(callback=token, uid=10)  # participant cannot confirm
    await feed(callback=token, uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert sum(method.chat_id == 10 and method.text == 'Hello NovaX' for method in sent) == 1

    await feed(callback=token, uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert sum(method.chat_id == 10 and method.text == 'Hello NovaX' for method in sent) == 1

    bot.session.reset_mock()
    await feed('/publish 1', uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert all(method.chat_id == 99 for method in sent)
    publish_token = sent[-1].reply_markup.inline_keyboard[0][0].callback_data
    await feed(callback=publish_token, uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    post = next(method for method in sent if method.chat_id == -10012345)
    assert post.reply_markup.inline_keyboard[0][0].url == 'https://t.me/NovaXDemoBot?start=event_1'
    await feed(callback=publish_token, uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert sum(method.chat_id == -10012345 for method in sent) == 1

    await feed(callback='cancel:1')
    assert (await service.stats(1))['active'] == 0
    await feed('/delete_me')
    assert await service.get(10, 1) is None
    await feed('/close 1', uid=99)
    from app.database.models import Event
    async with sessions() as s:
        assert not (await s.get(Event, 1)).opened
    await feed('/set 1 ip play.novax.example:25565', uid=99)
    await feed('/open 1', uid=99)
    async with sessions() as s:
        e = await s.get(Event, 1)
        assert e.opened and e.ip == 'play.novax.example:25565'
    # Inline administration must work even when the callback message author is a bot.
    await feed('/start', uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert any(button.callback_data == 'adm:home' for row in sent[-1].reply_markup.inline_keyboard for button in row)
    await feed(callback='adm:home', uid=99)
    await feed(callback='adm:event:1', uid=99)
    await feed(callback='adm:close:1', uid=99)
    async with sessions() as s:
        assert not (await s.get(Event, 1)).opened
    await feed(callback='adm:open:1', uid=10)  # denied
    async with sessions() as s:
        assert not (await s.get(Event, 1)).opened
    await feed(callback='adm:open:1', uid=99)
    await feed(callback='adm:stats:1', uid=99)
    await feed(callback='adm:export:1', uid=99)
    await feed(callback='adm:edit:1', uid=99)
    await feed(callback='field:1:ip', uid=99)
    await feed('inline.novax.example', uid=99)
    async with sessions() as s:
        assert (await s.get(Event, 1)).ip == 'inline.novax.example'
    await feed(callback='adm:edit:1', uid=99)
    await feed(callback='field:1:timezone', uid=99)
    await feed(callback='preset:1:moscow', uid=99)
    async with sessions() as s:
        assert (await s.get(Event, 1)).timezone == 'Europe/Moscow'
    await feed(callback='adm:create', uid=99)
    await feed('invalid-date', uid=99)
    await feed('2027-10-11', uid=99)
    async with sessions() as s:
        created = await s.get(Event, 2)
        assert created.date == '2027-10-11' and not created.opened
    await feed(callback='field:2:time', uid=99)
    await feed('20:00', uid=99)
    async with sessions() as s:
        assert (await s.get(Event, 2)).time == '20:00'
    # Returning to settings must not publish a channel post.
    bot.session.reset_mock()
    await feed(callback='adm:event:2', uid=99)
    await feed(callback='adm:publish:2', uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert all(method.chat_id == 99 for method in sent)
    await feed(callback='abort', uid=99)
    await feed(callback='adm:broadcast:2', uid=99)
    await feed('Inline broadcast preview', uid=99)
    sent = [call.args[1] for call in bot.session.call_args_list if isinstance(call.args[1], SendMessage)]
    assert sent[-1].reply_markup.inline_keyboard[0][0].callback_data.startswith('confirm:')
    await dp.storage.close()
