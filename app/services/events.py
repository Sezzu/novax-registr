import re
from datetime import datetime, timezone, date
from zoneinfo import ZoneInfo


def starts(e):
    if not e.time:
        return None
    naive = datetime.fromisoformat(f'{e.date}T{e.time}')
    zone = ZoneInfo(e.timezone)
    local = naive.replace(tzinfo=zone)
    if local.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != naive:
        raise ValueError('Nonexistent local time')
    if local.utcoffset() != naive.replace(tzinfo=zone, fold=1).utcoffset():
        raise ValueError('Ambiguous local time')
    return local.astimezone(timezone.utc)


def available(e):
    start = starts(e)
    now = datetime.now(timezone.utc)
    scheduled = getattr(e, 'registration_opens_at', None)
    future = start > now if start else date.fromisoformat(e.date) > now.astimezone(ZoneInfo(e.timezone)).date()
    return e.opened and future and (scheduled is None or scheduled <= now.timestamp())


def can_open(e):
    start = starts(e)
    now = datetime.now(timezone.utc)
    return bool(e.description.strip()) and (start > now if start else date.fromisoformat(e.date) > now.astimezone(ZoneInfo(e.timezone)).date())


def opening_timestamp(value, zone):
    local = datetime.fromisoformat(value)
    if local.tzinfo is not None:
        return int(local.timestamp())
    dummy = type('Schedule', (), {'date': local.date().isoformat(), 'time': local.strftime('%H:%M'), 'timezone': zone})()
    return int(starts(dummy).timestamp())


def validate_event(e):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', e.date):
        raise ValueError('Invalid date format')
    datetime.strptime(e.date, '%Y-%m-%d')
    ZoneInfo(e.timezone)
    if e.time and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', e.time):
        raise ValueError('Invalid time')
    starts(e)
    if not re.fullmatch(r'[a-zA-Z0-9.-]+(?::\d{1,5})?', e.ip):
        raise ValueError('Invalid IP')
    if ':' in e.ip and not 1 <= int(e.ip.rsplit(':', 1)[1]) <= 65535:
        raise ValueError('Invalid port')
    if len(e.ip) > 255 or not 1 <= len(e.versions) <= 255 or len(e.description) > 1800 or len(e.rules) > 3000:
        raise ValueError('Invalid length')
    cover = getattr(e, 'cover_image', None)
    if cover and len(cover) > 2048:
        raise ValueError('Invalid cover length')
    if cover and not cover.startswith(('https://', 'http://')) and ('/' in cover or '\\' in cover or '.' in cover):
        from pathlib import Path
        path = Path(cover).resolve()
        if not path.is_relative_to(Path('assets').resolve()) or path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            raise ValueError('Cover must be an image in assets/')
