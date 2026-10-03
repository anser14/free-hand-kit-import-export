FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE /package/
COPY src /package/src
RUN python -m pip wheel --no-deps --wheel-dir /tmp/wheels /package \
    && python -m pip install /tmp/wheels/freehand_kit_import_export-*.whl "psycopg[binary]" gunicorn

COPY examples/production_demo /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir --parents /app/private-media \
    && chown --recursive appuser:appuser /app

USER appuser
