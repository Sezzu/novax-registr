import asyncio
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest, TelegramNetworkError, TelegramServerError


async def send(bot, uid, text, **kwargs):
    for _ in range(3):
        try:
            await bot.send_message(uid, text, **kwargs)
            return True
        except TelegramRetryAfter as exc:
            await asyncio.sleep(exc.retry_after)
        except (TelegramForbiddenError, TelegramBadRequest):
            return False
        except (TelegramNetworkError, TelegramServerError):
            # Delivery may have reached Telegram: do not retry an ambiguous send.
            return False
    return False
