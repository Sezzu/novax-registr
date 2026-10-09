import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from alembic import context
from app.database import connect
from app.database.models import Base

load_dotenv()
url = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///data/novax.db')


def configure(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=connection.dialect.name == 'sqlite')
    with context.begin_transaction():
        context.run_migrations()


async def online():
    engine, _ = connect(url)
    async with engine.connect() as connection:
        await connection.run_sync(configure)
    await engine.dispose()


if context.is_offline_mode():
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif context.config.attributes.get('connection') is not None:
    configure(context.config.attributes['connection'])
else:
    asyncio.run(online())
