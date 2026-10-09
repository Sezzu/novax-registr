"""Persist channel publication, cover and participant count without losing registrations."""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Direct ADD COLUMN preserves the parent table and its cascading children.
    # SQLite batch recreation would DROP events and cascade-delete registrations.
    for column in (
        sa.Column('cover_image', sa.Text(), nullable=True),
        sa.Column('registration_opens_at', sa.BigInteger(), nullable=True),
        sa.Column('participant_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('channel_message_id', sa.BigInteger(), nullable=True),
        sa.Column('channel_chat_id', sa.String(80), nullable=True),
        sa.Column('publication_status', sa.String(16), nullable=False, server_default='unpublished'),
        sa.Column('channel_is_photo', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('channel_last_edit', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('channel_content_hash', sa.String(64), nullable=True),
    ):
        op.add_column('events', column)
    op.execute(sa.text('UPDATE events SET participant_count = (SELECT COUNT(*) FROM registrations WHERE registrations.event_id = events.id AND registrations.active = true)'))


def downgrade():
    # Python 3.12's SQLite supports native DROP COLUMN; keep cascading children.
    for name in ('channel_content_hash', 'channel_last_edit', 'channel_is_photo', 'publication_status',
                 'channel_chat_id', 'channel_message_id', 'participant_count', 'registration_opens_at', 'cover_image'):
        op.drop_column('events', name)
