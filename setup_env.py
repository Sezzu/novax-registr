"""Interactive first-launch configuration; never prints the bot token."""
from pathlib import Path
import re
from dotenv import dotenv_values, set_key
from getpass import getpass


def main():
    path = Path(__file__).resolve().parent / '.env'
    if not path.exists():
        path.write_text('BOT_TOKEN=\nBOT_USERNAME=\nADMIN_IDS=\nCHANNEL_ID=\nDEFAULT_TIMEZONE=Europe/Moscow\nDATABASE_URL=sqlite+aiosqlite:///data/novax.db\nMORNING_HOUR=9\n', encoding='utf-8')
    values = dotenv_values(path)
    token = values.get('BOT_TOKEN') or ''
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]{30,}', token):
        token = getpass('BotFather token (hidden): ').strip()
        if not re.fullmatch(r'\d+:[A-Za-z0-9_-]{30,}', token):
            raise ValueError('Invalid token format')
        set_key(str(path), 'BOT_TOKEN', token)
    admins = values.get('ADMIN_IDS') or ''
    if not re.fullmatch(r'[1-9]\d*(?:\s*,\s*[1-9]\d*)*', admins) or admins == '123456789':
        admins = input('Your Telegram numeric ID (multiple admins: comma-separated): ').strip()
        if not re.fullmatch(r'[1-9]\d*(?:\s*,\s*[1-9]\d*)*', admins):
            raise ValueError('ADMIN_IDS must contain positive numeric Telegram IDs')
        set_key(str(path), 'ADMIN_IDS', admins)
    print('Configuration ready. Channel publishing can be configured via CHANNEL_ID in .env.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, EOFError, KeyboardInterrupt) as error:
        print('Configuration cancelled or invalid input.' if not isinstance(error, ValueError) else str(error))
        raise SystemExit(1)
