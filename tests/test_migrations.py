import os
import subprocess
import sys
import sqlite3
from pathlib import Path


def test_migrations(tmp_path):
    path = tmp_path / 'migration.db'
    env = {**os.environ, 'DATABASE_URL': f'sqlite+aiosqlite:///{path}'}
    root = Path(__file__).resolve().parents[1]
    for _ in range(2):
        subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=root, env=env, check=True, capture_output=True)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT date,time,opened FROM events').fetchall() == [('2026-10-11', None, 0)]
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('002',)
    subprocess.run([sys.executable, '-m', 'alembic', 'check'], cwd=root, env=env, check=True, capture_output=True)


def test_existing_registrations_preserved(tmp_path):
    path = tmp_path / 'old.db'
    env = {**os.environ, 'DATABASE_URL': f'sqlite+aiosqlite:///{path}'}
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', '001'], cwd=root, env=env, check=True, capture_output=True)
    with sqlite3.connect(path) as connection:
        connection.execute('INSERT INTO users(id) VALUES(123)')
        connection.execute("INSERT INTO registrations(event_id,user_id,nick,team,reminders,active,completed,cancellations) VALUES(1,123,'ExistingPlayer','team',1,1,1,0)")
    subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], cwd=root, env=env, check=True, capture_output=True)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT nick,active FROM registrations').fetchone() == ('ExistingPlayer', 1)
        assert connection.execute('SELECT participant_count FROM events').fetchone() == (1,)
