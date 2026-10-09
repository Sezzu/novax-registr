FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 10001 --create-home bot && mkdir /app/data && chown bot:bot /app/data
COPY --chown=bot:bot . .
USER bot
CMD ["sh", "-c", "alembic upgrade head && exec python -m app.main"]
