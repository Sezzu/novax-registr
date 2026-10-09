from app.diagnostics import error_context
import logging
import time
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from app import texts as t


def is_admin(uid, settings):
    return uid in settings.admins


class Guard(BaseMiddleware):
    def __init__(self):
        self.last = {}

    async def __call__(self, handler, event, data):
        if not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return
        chat = event.chat if isinstance(event, Message) else (event.message.chat if event.message else None)
        if not chat or chat.type != 'private':
            return
        uid = event.from_user.id
        now = time.monotonic()
        if isinstance(event, Message) and now - self.last.get(uid, 0) < 0.7:
            if isinstance(event, CallbackQuery):
                await event.answer(t.BUSY)
            return
        if isinstance(event, Message):
            self.last[uid] = now
        if len(self.last) > 10000:
            self.last = {key: value for key, value in self.last.items() if now - value < 60}
        try:
            return await handler(event, data)
        except Exception as exc:
            logging.getLogger('novax').error('handler_failed', extra=error_context(exc))
            if isinstance(event, CallbackQuery):
                await event.answer(t.ERROR, show_alert=True)
            else:
                await event.answer(t.ERROR)
