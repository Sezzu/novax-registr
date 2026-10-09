import pytest
from pydantic import ValidationError
from app.configuration import Settings


@pytest.mark.parametrize('value', ['Moscow', 'moscow', ' Москва ', 'МСК', 'MSK', 'Europe/Moscow'])
def test_moscow_timezone(value):
    settings = Settings(bot_token='123456:secret', admin_ids='99', default_timezone=value, _env_file=None)
    assert settings.default_timezone == 'Europe/Moscow'


def test_unknown_timezone_is_validation_error():
    with pytest.raises(ValidationError, match='например Europe/Moscow'):
        Settings(bot_token='123456:secret', admin_ids='99', default_timezone='Not/AZone', _env_file=None)
