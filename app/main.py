import asyncio
import json
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import BotCommand
from app.configuration import Settings
from app.database import connect, initialize_database
from app.diagnostics import error_context, framework_context
from app.handlers import admin, user
from app.handlers.middleware import Guard
from app.services.registrations import Registrations
from app.services.reminders import Reminders
from app.services.channel import Publisher, check_channel, ChannelError
from app.services.telegram import send
from app import texts as t


class SafeFormatter(logging.Formatter):
    def format(self, record):
        details = framework_context(record) if record.name != 'novax' else {}
        return json.dumps({'level': record.levelname,
                           'event': details.get('event', record.getMessage() if record.name == 'novax' else 'framework_event'),
                           'error_type': details.get('error_type', getattr(record, 'error_type', None)),
                           'database_reason': details.get('database_reason', getattr(record, 'database_reason', None)),
                           'hint': details.get('hint')}, ensure_ascii=False)



async def main():
    handler = logging.StreamHandler()
    handler.setFormatter(SafeFormatter())
    logging.basicConfig(level=logging.WARNING, handlers=[handler])
    settings = Settings()
    if not settings.admins:
        raise ValueError('ADMIN_IDS must not be empty')
    engine = None
    try:
        engine, sessions = connect(settings.database_url)
        await initialize_database(engine)
    except Exception as exc:
        logging.getLogger('novax').error('database_startup_failed', extra=error_context(exc))
        if engine is not None:
            await engine.dispose()
        raise SystemExit('База данных не готова. Проверьте DATABASE_URL, доступ на запись и миграции; причина указана в database_reason.') from None
    bot = Bot(settings.bot_token.get_secret_value(), default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=MemoryStorage(), events_isolation=SimpleEventIsolation(), fsm_strategy=FSMStrategy.USER_IN_CHAT)
    # Serializes all updates for a user, including confirmation double-clicks.
    guard = Guard()
    dp.message.outer_middleware(guard)
    dp.callback_query.outer_middleware(guard)
    dp.include_router(admin.router)
    dp.include_router(user.router)
    reminder_task = None
    channel_task = None
    try:
        try:
            access = await check_channel(bot, settings)
            logging.getLogger('novax').warning('channel_access_verified')
        except ChannelError as exc:
            for uid in settings.admins:
                await send(bot, uid, str(exc))
        await bot.delete_webhook(drop_pending_updates=False)
        await bot.set_my_commands([BotCommand(command=name, description=description) for name, description in t.COMMANDS])
        reminder_task = asyncio.create_task(Reminders(sessions, bot, settings.morning_hour).run())
        channel_task = asyncio.create_task(Publisher(sessions, bot, settings).run())
        await dp.start_polling(bot, settings=settings, sessions=sessions, service=Registrations(sessions), close_bot_session=False)
    finally:
        if reminder_task:
            reminder_task.cancel()
            await asyncio.gather(reminder_task, return_exceptions=True)
        if channel_task:
            channel_task.cancel()
            await asyncio.gather(channel_task, return_exceptions=True)
        await bot.session.close()
        await engine.dispose()


if __name__ == '__main__':
    asyncio.run(main())
