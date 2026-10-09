import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    bot_token: SecretStr
    admin_ids: str
    database_url: str = 'sqlite+aiosqlite:///data/novax.db'
    channel_id: str = ''
    bot_username: str = ''
    default_timezone: str = 'Europe/Moscow'
    morning_hour: int = Field(default=9, ge=0, le=23)

    @field_validator('channel_id')
    @classmethod
    def validate_channel(cls, value):
        value = value.strip()
        if value and not re.fullmatch(r'@[A-Za-z][A-Za-z0-9_]{4,31}|-100\d+', value):
            raise ValueError('CHANNEL_ID must be @username or -100...')
        return value

    @field_validator('default_timezone')
    @classmethod
    def validate_timezone(cls, value):
        value = value.strip()
        if value.casefold() in {'moscow', 'москва', 'мск', 'msk'}:
            value = 'Europe/Moscow'
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError('DEFAULT_TIMEZONE: укажите часовой пояс IANA, например Europe/Moscow') from exc
        return value

    @property
    def channel_target(self):
        return int(self.channel_id) if self.channel_id.startswith('-100') else self.channel_id

    @property
    def admins(self):
        return {int(value.strip()) for value in self.admin_ids.split(',') if value.strip()}
