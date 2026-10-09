from pathlib import Path
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import event


def connect(url):
    parsed = make_url(url)
    if parsed.get_backend_name() == 'sqlite' and parsed.database not in (None, '', ':memory:'):
        Path(parsed.database).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(url)
    if url.startswith('sqlite'):
        @event.listens_for(engine.sync_engine, 'connect')
        def pragma(connection, _):
            cursor = connection.cursor()
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.execute('PRAGMA busy_timeout=10000')
            cursor.close()
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def initialize_database(engine):
    """Apply versioned migrations before accepting updates; preserve existing data."""
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'migrations'))

    def upgrade(connection):
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')

    async with engine.begin() as connection:
        await connection.run_sync(upgrade)
