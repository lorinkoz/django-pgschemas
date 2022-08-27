FROM python:3.10.4-slim

WORKDIR /app

RUN apt update && \
    apt install -y gcc libpq-dev python3-dev libffi-dev musl-dev python3-pip && \
    apt autoremove -y && apt autoclean -y

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV POETRY_VIRTUALENVS_CREATE 0

RUN pip install poetry gunicorn uvicorn

COPY . .

RUN poetry install
