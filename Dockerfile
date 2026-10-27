FROM python:3.10.4-slim

WORKDIR /app

RUN apt update && \
    apt install -y gcc libpq-dev python3-dev libffi-dev musl-dev && \
    apt autoremove -y && apt autoclean -y

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV UV_PROJECT_ENVIRONMENT=/usr/local

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . .

RUN uv sync --frozen --group dev --inexact
RUN uv pip install --python /usr/local/bin/python psycopg gunicorn uvicorn
