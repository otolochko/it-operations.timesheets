FROM python:3.12.7-slim AS wheels

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12.7-slim

WORKDIR /app

COPY requirements.txt .
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --chown=app:app . .

USER app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
