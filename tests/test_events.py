from types import SimpleNamespace
import pytest
from app.services.events import validate_event


@pytest.mark.parametrize('date,clock,zone', [
    ('2026-02-30', '18:00', 'UTC'), ('2026-10-11', '25:00', 'UTC'),
    ('2026-03-29', '02:30', 'Europe/Berlin'), ('2026-10-25', '02:30', 'Europe/Berlin'),
])
def test_invalid_dates(date, clock, zone):
    with pytest.raises(ValueError):
        validate_event(SimpleNamespace(date=date, time=clock, timezone=zone, ip='mcnovax.space', versions='Java 1.21.4', description='Battle', rules='Rules'))
