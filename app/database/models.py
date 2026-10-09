from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10))
    time: Mapped[str | None] = mapped_column(String(5))
    timezone: Mapped[str] = mapped_column(String(80), default='Europe/Moscow')
    description: Mapped[str] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(String(255), default='mcnovax.space')
    versions: Mapped[str] = mapped_column(String(255), default='Java 1.21.4')
    rules: Mapped[str] = mapped_column(Text)
    opened: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_image: Mapped[str | None] = mapped_column(Text)
    registration_opens_at: Mapped[int | None] = mapped_column(BigInteger)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, server_default='0')
    channel_message_id: Mapped[int | None] = mapped_column(BigInteger)
    channel_chat_id: Mapped[str | None] = mapped_column(String(80))
    publication_status: Mapped[str] = mapped_column(String(16), default='unpublished', server_default='unpublished')
    channel_is_photo: Mapped[bool] = mapped_column(Boolean, default=False, server_default='0')
    channel_last_edit: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0')
    channel_content_hash: Mapped[str | None] = mapped_column(String(64))


class Registration(Base):
    __tablename__ = 'registrations'
    __table_args__ = (UniqueConstraint('event_id', 'user_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id', ondelete='CASCADE'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    nick: Mapped[str | None] = mapped_column(String(16))
    team: Mapped[str | None] = mapped_column(String(16))
    reminders: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    cancellations: Mapped[int] = mapped_column(Integer, default=0)


class Referral(Base):
    __tablename__ = 'referral_sources'
    __table_args__ = (UniqueConstraint('event_id', 'user_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id', ondelete='CASCADE'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    source: Mapped[str] = mapped_column(String(16))


class Delivery(Base):
    __tablename__ = 'reminder_deliveries'
    __table_args__ = (UniqueConstraint('event_id', 'user_id', 'kind'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('events.id', ondelete='CASCADE'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    kind: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default='claimed')


class AdminAction(Base):
    __tablename__ = 'admin_actions'
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(32))
    event_id: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[int] = mapped_column(BigInteger)
