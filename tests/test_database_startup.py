import sqlite3
import pytest
from sqlalchemy.exc import OperationalError
from app.database import connect, initialize_database
from app.diagnostics import error_context


@pytest.mark.asyncio
async def test_direct_start_creates_directory_and_migrates(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / 'nested' / 'bot.db'
    engine, _ = connect(f'sqlite+aiosqlite:///{path}')
    try:
        await initialize_database(engine)
        with sqlite3.connect(path) as db:
            db.execute("UPDATE events SET description='Preserve me' WHERE id=1")
        await initialize_database(engine)
        with sqlite3.connect(path) as db:
            assert db.execute('SELECT version_num FROM alembic_version').fetchone() == ('002',)
            assert db.execute('SELECT description FROM events WHERE id=1').fetchone() == ('Preserve me',)
    finally:
        await engine.dispose()


@pytest.mark.parametrize('message,reason', [
    ('no such table: events', 'missing_table'),
    ('no such column: events.cover_image', 'missing_column'),
    ('unable to open database file', 'cannot_open_database'),
    ('attempt to write a readonly database', 'read_only_database'),
    ('database is locked', 'database_locked'),
])
def test_safe_database_diagnostics(message, reason):
    exc = OperationalError('SELECT secret', {'nick': 'PrivatePlayer'}, sqlite3.OperationalError(message))
    result = error_context(exc)
    assert result == {'error_type': 'OperationalError', 'database_reason': reason}
    assert 'PrivatePlayer' not in str(result)
    assert 'SELECT' not in str(result)
