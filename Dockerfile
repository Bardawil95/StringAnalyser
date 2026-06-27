# syntax=docker/dockerfile:1

# Pinned uv binary, copied into our image below (reproducible builds).
FROM ghcr.io/astral-sh/uv:0.11.7 AS uv

# Shared base for the test and production stages.
FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy
COPY --from=uv /uv /uvx /bin/
WORKDIR /app

# =========================================================
# TEST STAGE - quality gates (lint, format, types, tests)
# Built explicitly in CI via `--target test-env`. If any
# step fails, the build fails. Dev tools ARE installed here.
# =========================================================
FROM base AS test-env
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv run ruff check .
RUN uv run ruff format --check .
RUN uv run mypy .
RUN uv run pytest

# =========================================================
# PRODUCTION STAGE - lean runtime image, no dev tools.
# =========================================================
FROM base AS production
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Create the non-root user, then copy code already owned by it in one pass
# (COPY --chown avoids a second chown layer that would duplicate every file).
RUN useradd --create-home appuser
COPY --chown=appuser:appuser . .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

USER appuser

# Production WSGI server (not Flask's dev server). Multiple workers, each
# calling the create_app factory via `app.main:create_app()`.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app.main:create_app()"]
