# ── stage 1: install dependencies ────────────────────────────────────────────
FROM python:3.12-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install --only main --no-root

# ── stage 2: final image ──────────────────────────────────────────────────────
FROM python:3.12-alpine AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv ./.venv

COPY manage.py ./
COPY simple_mirror/ ./simple_mirror/
COPY mirror/ ./mirror/
COPY accounts/ ./accounts/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
