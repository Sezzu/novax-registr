"""Initial portable schema and first NovaX event."""
from alembic import op
import sqlalchemy as sa
from app import texts as t

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users', sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=False))
    events = op.create_table('events',
        sa.Column('id', sa.Integer(), primary_key=True), sa.Column('date', sa.String(10), nullable=False),
        sa.Column('time', sa.String(5)), sa.Column('timezone', sa.String(80), nullable=False),
        sa.Column('description', sa.Text(), nullable=False), sa.Column('ip', sa.String(255), nullable=False),
        sa.Column('versions', sa.String(255), nullable=False), sa.Column('rules', sa.Text(), nullable=False),
        sa.Column('opened', sa.Boolean(), nullable=False))
    op.create_table('registrations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nick', sa.String(16)), sa.Column('team', sa.String(16)),
        sa.Column('reminders', sa.Boolean(), nullable=False), sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False), sa.Column('cancellations', sa.Integer(), nullable=False),
        sa.UniqueConstraint('event_id', 'user_id'))
    op.create_table('referral_sources',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source', sa.String(16), nullable=False), sa.UniqueConstraint('event_id', 'user_id'))
    op.create_table('reminder_deliveries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.Integer(), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False), sa.Column('status', sa.String(16), nullable=False),
        sa.UniqueConstraint('event_id', 'user_id', 'kind'))
    op.create_table('admin_actions', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('admin_id', sa.BigInteger(), nullable=False), sa.Column('action', sa.String(32), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False), sa.Column('timestamp', sa.BigInteger(), nullable=False))
    op.bulk_insert(events, [dict(date='2026-10-11', time=None, timezone='Europe/Moscow',
        description=t.DEFAULT_DESCRIPTION, ip='mcnovax.space', versions='Java 1.21.4', rules=t.DEFAULT_RULES, opened=False)])


def downgrade():
    for name in ('admin_actions', 'reminder_deliveries', 'referral_sources', 'registrations', 'events', 'users'):
        op.drop_table(name)
