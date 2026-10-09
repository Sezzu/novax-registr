from html import escape

TITLE = 'Королевская Битва NovaX'
PARTICIPATE = '⚔️ Буду участвовать'
COMMANDS = [('start', 'Открыть бота'), ('events', 'События NovaX'), ('my_registration', 'Мои регистрации'),
            ('privacy', 'Обработка данных'), ('delete_me', 'Удалить мои данные'), ('admin', 'Администрирование'),
            ('publish_event', 'Опубликовать ивент'), ('channel_test', 'Проверить публикацию в канале')]
WELCOME = '⚔️ <b>NovaX — New era</b>\n\nАрена ждёт. Выбери событие и присоединяйся к битве.'
EVENTS_TITLE = '⚔️ <b>События NovaX</b>\n\nВыбирай свою следующую битву.'
NO_EVENTS = 'Новые события появятся здесь. Загляни чуть позже.'
HOME_BUTTONS = {'events': '⚔️ События', 'mine': '✅ Моё участие', 'privacy': '🔒 Мои данные'}
OTHER_EVENTS = '◀️ Другие события'
MISSING = 'Событие не найдено.'
CLOSED = 'Регистрация закрыта или событие уже началось.'
NO_TIME = 'Время уточняется администратором'
NICK = '👤 <b>Напиши свой Minecraft-ник</b>\n\n3–16 символов: латинские буквы, цифры и знак _.'
TEAM = '⚔️ <b>Как ты будешь играть?</b>'
REMINDERS = '🔔 <b>Напомнить перед началом?</b>'
INVALID = 'Некорректные данные. Проверь формат и попробуй снова.'
DENIED = 'Доступ разрешён только администраторам.'
CANCELLED = 'Участие отменено. Напоминания отключены.'
EMPTY = 'Активных регистраций нет.'
DELETED = 'Данные удалены. Незавершённый опрос также сброшен.'
PRIVACY = ('Храним Telegram ID, ник, ответы, согласие на напоминания и источник первого перехода. '
           'Ники видны только тебе и администраторам, включая их CSV-экспорт. '
           'Имя, телефон и возраст не собираем. /delete_me удаляет данные и отключает напоминания. '
           'Администратор отвечает за удаление ранее выгруженных CSV и сообщений рассылок.')
TEAMS = {'team': '👥 Уже есть команда', 'looking': '🔎 Ищу команду', 'solo': '⚔️ Один'}
BUTTONS = {'join': PARTICIPATE, 'edit': '✏️ Изменить данные', 'cancel': '❌ Отменить участие',
           'rules': '📋 Правила', 'public': '👥 Статистика участников', 'arrive': '🚀 Захожу на сервер'}
YES = '🔔 Да'
NO = 'Без напоминаний'
CONFIRM = '✅ Отправить'
PUBLISH = '✅ Опубликовать'
EDIT_POST = '✏️ Изменить'
ABORT = '❌ Отмена'
REGISTERED_RULES = '📋 Открыть правила'
CHANNEL_ACCESS_ERROR = 'Бот не может публиковать в канале. Добавьте его в администраторы и разрешите публикацию сообщений.'
CHANNEL_ACCESS_OK = '✅ Канал доступен для публикации.'
CHANNEL_TEST_POST = '🧪 <b>NovaX · проверка канала</b>\n\nКнопка ниже открывает карточку события в боте.'
CHANNEL_TEST_SENT = '✅ Тестовый пост опубликован в канале.\nmessage_id: <code>{id}</code>'
PUBLISHED = '✅ Ивент опубликован в канале.\nmessage_id: <code>{id}</code>'
ALREADY_PUBLISHED = 'Этот ивент уже опубликован или отправка уже выполняется. Повторный пост не создан.'
PUBLICATION_UNCERTAIN = 'Результат отправки неизвестен. Проверьте канал; повторная отправка заблокирована, чтобы избежать дубля.'
PUBLICATION_FAILED = 'Пост не отправлен. Проверьте доступ к каналу и повторите предпросмотр.'
EDIT_PROMPT = '✏️ <b>Что изменить в ивенте?</b>\n\nПосле изменения появится новый предпросмотр.'
EDIT_VALUE = 'Введите новое значение для поля «{field}». Чтобы отменить, нажмите /abort.'
EDIT_COVER = 'Отправьте изображение 16:9 или HTTPS-ссылку на обложку. Чтобы убрать обложку, отправьте «без обложки».'
COVER_RATIO_ERROR = 'Для обложки нужен формат 16:9. Отправьте широкое изображение.'
REMOVE_COVER = 'без обложки'
EDIT_LABELS = {'date': '🗓 Дата', 'time': '⏰ Время', 'timezone': '🌍 Часовой пояс', 'description': '📝 Описание',
               'ip': '🎮 IP сервера', 'versions': '🧩 Версии', 'rules': '📋 Правила', 'cover_image': '🖼 Обложка',
               'registration_opens_at': '🚪 Открытие регистрации'}
BACK_PREVIEW = '◀️ К предпросмотру'
POST_UPDATED = '✅ Изменения сохранены. Данные в опубликованном посте обновятся в течение пяти минут.'
ADMIN_HELP = '''Администрирование:
/create YYYY-MM-DD | HH:MM | Europe/Moscow | описание
/set ID поле значение
Поля: date, time, timezone, description, ip, versions, rules, cover_image
/open ID — открыть; /close ID — закрыть
/stats ID; /export ID
/publish_event [ID] — предпросмотр ближайшего ивента
/publish ID — тот же предпросмотр
/edit_event [ID] — изменить детали и время ивента
/channel_test — тестовый пост с кнопкой
/broadcast ID текст — предпросмотр рассылки
/abort — сбросить опрос/предпросмотр'''
SAVED = 'Сохранено. ID события: {id}'
PREVIEW = 'Предпросмотр перед отправкой:\n\n{text}'
SENT = 'Отправлено: {sent}. Не доставлено: {failed}.'
NOT_READY = 'Для открытия регистрации укажите будущую дату события и описание.'
RULES_PENDING = '📋 Правила ивента появятся здесь перед стартом. Администратор ещё уточняет детали.'
OPENING_FORMAT = 'Введите дату и время открытия регистрации: YYYY-MM-DDTHH:MM (в часовом поясе события).'
NO_CHANNEL = 'CHANNEL_ID не настроен.'
EXPIRED = 'Предпросмотр устарел. Сформируй новый.'
BUSY = 'Подожди секунду перед следующим действием.'
ERROR = 'Не удалось выполнить действие. Попробуй позже.'
ABORTED = 'Действие отменено.'
ARRIVED = 'Отлично! Фактическую явку администратор отмечает отдельно.'
MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']


def date_text(value):
    from datetime import date
    d = date.fromisoformat(value)
    return f'{d.day} {MONTHS[d.month - 1]} {d.year}'


def card(e, count):
    return (f'⚔️ <b>{TITLE}</b>\n\nДо начала: <b>{time_left(e)}</b>\n\n'
            f'🗓 {date_text(e.date)}, {escape(e.time or NO_TIME)} {escape(e.timezone)}\n'
            f'🎮 <code>{escape(e.ip)}</code>\nВерсии: {escape(e.versions)}\n'
            f'👥 Подтвердили участие: <b>{int(count)}</b>\n\nГотов выйти на арену?')


def time_left(e):
    from datetime import datetime, timezone
    from app.services.events import starts
    start = starts(e)
    if not start:
        return NO_TIME
    seconds = int((start - datetime.now(timezone.utc)).total_seconds())
    if seconds <= 0:
        return 'событие уже началось'
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    return (f'{days} дн. ' if days else '') + f'{hours} ч. {minutes} мин.' if seconds >= 60 else 'меньше минуты'


def registration_notice(e):
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    stamp = getattr(e, 'registration_opens_at', None)
    if stamp and stamp > datetime.now(timezone.utc).timestamp():
        local = datetime.fromtimestamp(stamp, ZoneInfo(e.timezone))
        return f'🚪 Регистрация откроется {date_text(local.date().isoformat())} в {local:%H:%M} {escape(e.timezone)}.'
    return CLOSED


CHANNEL_INTRO = 'Возрождение продолжается. Игроки снова выйдут на арену.'


def channel_post(e, count):
    description = e.description if e.description and e.description != DEFAULT_DESCRIPTION else CHANNEL_INTRO
    if len(description) > 200:
        description = description[:197] + '…'
    return (f'⚔️ <b>КОРОЛЕВСКАЯ БИТВА NOVAX</b>\n\n{escape(description)}\n\n'
            f'🗓 <b>{date_text(e.date)}</b>\n⏰ <b>{escape(e.time or NO_TIME)} {escape(e.timezone)}</b>\n'
            f'👥 Команды до 4 человек\n🗡 4 легендарных оружия\n🎮 <code>{escape(e.ip)}</code>\n\n'
            f'Уже участвуют: <b>{int(count)} игроков</b>\n\n'
            'Нажми кнопку, ответь на короткий опрос и получи напоминание перед началом.')


def confirmation(e, r):
    reminder = 'Мы напомним перед стартом.' if r.reminders else 'Напоминания отключены.'
    return (f'✅ <b>Ты в списке участников</b>\n\n👤 Ник: <b>{escape(r.nick)}</b>\n'
            f'👥 Команда: {TEAMS[r.team]}\n🗓 {date_text(e.date)}, {escape(e.time or NO_TIME)} {escape(e.timezone)}\n'
            f'🎮 <code>{escape(e.ip)}</code>\n\nПодготовь клиент заранее. {reminder}')


def stats(s):
    return (f"Открыли: {s['opened']}\nНачали: {s['started']}\nЗавершили (уникальные): {s['completed']}\n"
            f"Активных: {s['active']}\nОтмен: {s['cancellations']}\nНапоминания: {s['reminders']}\n"
            f"Есть команда / ищут / одни: {s['team']} / {s['looking']} / {s['solo']}\n"
            f"Источники: {s['sources']}\nКонверсия в завершение: {s['conversion']:.1f}%")


def public_stats(s):
    return f"Участников: {s['active']}\nЕсть команда: {s['team']}\nИщут команду: {s['looking']}\nИграют одни: {s['solo']}"


def reminder(e, kind):
    label = {'morning': 'Сегодня', 'two_hours': 'Через 2 часа', 'fifteen': 'Через 15 минут'}[kind]
    return f'{label} — {TITLE}!\n⏰ {escape(e.time)} {escape(e.timezone)}\n🎮 {escape(e.ip)}'
CSV_HEADER = ['telegram_id', 'minecraft_nick', 'team_status', 'reminders', 'source']
DEFAULT_DESCRIPTION = 'Отдельный формат ивентов сервера NovaX — New era.'
DEFAULT_RULES = ''
