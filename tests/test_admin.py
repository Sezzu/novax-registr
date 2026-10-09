from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from app.handlers.admin import command, confirm
from app.handlers.middleware import is_admin
from app.configuration import Settings


@pytest.mark.parametrize('cmd', ['admin', 'create', 'set', 'open', 'close', 'stats', 'export', 'publish', 'publish_event', 'edit_event', 'channel_test', 'broadcast'])
async def test_commands_denied(cmd):
    settings = Settings(bot_token='123:secret', admin_ids='99', _env_file=None)
    message = SimpleNamespace(from_user=SimpleNamespace(id=10), text=f'/{cmd} 1', answer=AsyncMock())
    sessions, service, state, bot = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    await command(message, settings, sessions, service, state, bot)
    message.answer.assert_awaited_once()
    assert not sessions.mock_calls and not service.mock_calls and not bot.mock_calls
    assert is_admin(99, settings) and not is_admin(10, settings)


async def test_confirm_denied():
    settings = Settings(bot_token='123:secret', admin_ids='99', _env_file=None)
    callback = SimpleNamespace(from_user=SimpleNamespace(id=10), answer=AsyncMock())
    sessions, state, bot = AsyncMock(), AsyncMock(), AsyncMock()
    await confirm(callback, settings, state, sessions, bot)
    assert not sessions.mock_calls and not state.mock_calls and not bot.mock_calls


async def test_confirm_stale():
    settings = Settings(bot_token='123:secret', admin_ids='99', _env_file=None)
    callback = SimpleNamespace(from_user=SimpleNamespace(id=99), data='confirm:x', answer=AsyncMock())
    state = AsyncMock()
    state.get_data.return_value = {}
    bot, sessions = AsyncMock(), AsyncMock()
    await confirm(callback, settings, state, sessions, bot)
    assert not bot.mock_calls and not sessions.mock_calls
