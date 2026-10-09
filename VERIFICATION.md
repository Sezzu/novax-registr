# Проверка обновления NovaX

8 октября 2026, Python 3.12.10.

- Автоматические тесты: **57 passed**. Проверены миграции с сохранением существующих регистраций, deep link, права канала, публикация и фото-fallback, повторные и конкурирующие подтверждения, сохранение message_id, счётчик с интервалом 300 секунд, отложенное открытие регистрации и прежние функции.
- Миграция 002 применена к текущей базе. Перед обновлением сохранена локальная резервная копия. Существующие административные функции сохранены.
- Telegram подтвердил: @NovaXreg_bot — администратор @NovaXMC с can_post_messages=True.
- До запрета отправок команда /channel_test создала тестовый пост, message_id=1005. После запрета новые сообщения в канал не отправлялись. Анонс ивента НЕ опубликован: publication_status=unpublished, channel_message_id=NULL.
- В настоящем личном чате проверены карточка /start event_1, три вопроса, сохранение NovaX_QA, повторный вход без дубликата и /stats с одним активным участником. После проверки тестовое участие отменено; participant_count=0.
- Регистрация настроена на 8 октября 2026, 22:00 Europe/Moscow. Время битвы 11 октября пока не задано; владелец укажет его позже через /edit_event.
- Реальные скриншоты: screenshots/preview-private.jpg, event-card.jpg, registration-complete.jpg, admin-stats.jpg. Это предпросмотр в личном чате, а не опубликованный анонс. Скриншот канального поста не получен: ранее отправленный тестовый пост не отображается в проверенном просмотре канала; повторная публикация запрещена владельцем.
- Обложка создана встроенным imagegen, сохранена в assets/royal-battle.png. Промпт и сведения — assets/COVER.md.
- Docker и живой PostgreSQL не проверялись. В ходе живой проверки одна сетевая ошибка Telegram обработана понятным ответом без падения бота.

Токен и рабочая база не входят в архив. Текущий бот перезапущен и работает из существующего проекта; повторный start.bat одновременно с ним запускать не нужно.

## Исправление настройки хостинга — 9 октября 2026

Валидатор DEFAULT_TIMEZONE нормализует Moscow/Москва/МСК/MSK в Europe/Moscow и превращает неизвестный пояс в понятную ошибку Pydantic. Добавлены 7 тестов. Проверка: 64 passed. Доступа к хостингу нет; настройки в его панели не изменялись.

2026-10-09: automatic startup migrations and safe database diagnostics: 70 tests passed in 11.69s. Fresh database created from arbitrary working directory; repeat upgrade preserves event data. Hosting itself was not accessed.

2026-10-09: Inline admin panel and polling diagnostics: full suite 74 passed (10.61s); after timezone presets, handler and logging checks 5 passed (4.18s). Callback messages use bot authors, authorization uses callback actor. No live Telegram messages sent. Hosting diagnosis remains unverified until new logs arrive.
