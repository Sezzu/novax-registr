import json
import logging
from aiogram.exceptions import TelegramConflictError, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.methods import GetUpdates
from app.main import SafeFormatter
from app.handlers.middleware import Guard
from aiogram.types import CallbackQuery, Chat, Message, User
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest


@pytest.mark.parametrize('exception,event', [
    (TelegramConflictError, 'telegram_polling_conflict'),
    (TelegramNetworkError, 'telegram_network_failed'),
    (TelegramUnauthorizedError, 'telegram_token_rejected'),
])
def test_polling_logs_identify_error_without_secrets(exception, event):
    error = exception(GetUpdates(), 'PrivatePlayer SECRET_TOKEN https://secret.example')
    record = logging.LogRecord('aiogram.dispatcher', logging.ERROR, '', 0,
        'Failed to fetch updates - %s: %s', (type(error).__name__, error), None)
    text = SafeFormatter().format(record)
    result = json.loads(text)
    assert result['event'] == event
    assert result['error_type'] == exception.__name__
    assert result['hint']
    assert 'SECRET_TOKEN' not in text and 'PrivatePlayer' not in text


@pytest.mark.asyncio
async def test_fast_callbacks_not_discarded():
    user = User(id=99, is_bot=False, first_name='Admin')
    message = Message(message_id=1, date=datetime.now(timezone.utc), chat=Chat(id=99, type='private'), from_user=user)
    callback = CallbackQuery(id='1', from_user=user, chat_instance='x', message=message, data='adm:home')
    guard = Guard()
    handler = AsyncMock()
    await guard(handler, callback, {})
    await guard(handler, callback, {})
    assert handler.await_count == 2
