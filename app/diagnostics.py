"""Safe database diagnostics: never emit queries, parameters or connection URLs."""
def error_context(exc):
    result = {'error_type': type(exc).__name__}
    original = getattr(exc, 'orig', exc)
    message = str(original).lower()
    reasons = (
        ('no such table', 'missing_table'),
        ('no such column', 'missing_column'),
        ('has no column named', 'missing_column'),
        ('unable to open database', 'cannot_open_database'),
        ('readonly', 'read_only_database'),
        ('read-only', 'read_only_database'),
        ('database is locked', 'database_locked'),
        ('permission denied', 'permission_denied'),
        ('connection refused', 'connection_refused'),
    )
    for fragment, reason in reasons:
        if fragment in message:
            result['database_reason'] = reason
            break
    return result


def framework_context(record):
    # aiogram polling puts the exception into LogRecord.args, without exc_info.
    args = record.args if isinstance(record.args, tuple) else ()
    exc = next((arg for arg in args if isinstance(arg, BaseException)), None)
    if exc is None and record.exc_info:
        exc = record.exc_info[1]
    result = error_context(exc) if exc else {}
    kind = type(exc).__name__ if exc else next((arg for arg in args if isinstance(arg, str) and arg.startswith('Telegram')), None)
    if kind:
        result['error_type'] = kind
    result['event'] = 'telegram_polling_retry' if str(record.msg).startswith('Sleep for') else 'framework_event'
    reasons = {
        'TelegramConflictError': ('telegram_polling_conflict', 'Оставьте один запущенный экземпляр бота; остановите локальный бот и дубли на хостинге.'),
        'TelegramNetworkError': ('telegram_network_failed', 'Проверьте доступ хостинга к api.telegram.org.'),
        'TelegramUnauthorizedError': ('telegram_token_rejected', 'Проверьте BOT_TOKEN в настройках хостинга.'),
        'TelegramRetryAfter': ('telegram_rate_limited', 'Telegram ограничил частоту запросов; бот повторит попытку.'),
        'TelegramBadRequest': ('telegram_request_rejected', 'Telegram отклонил запрос; проверьте настройки и обработчик.'),
    }
    if kind in reasons:
        result['event'], result['hint'] = reasons[kind]
    return result
