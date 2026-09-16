FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir . \
    && addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 10000

CMD ["sh", "-c", "exec python -m uvicorn gestion_boutiques.main:app --app-dir src --host 0.0.0.0 --port ${PORT:-10000} --workers ${WEB_CONCURRENCY:-1}"]