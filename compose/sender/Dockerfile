FROM python:3.11-alpine3.17

ARG YOUR_ENV

ENV YOUR_ENV=dev \
      # python:
      PYTHONFAULTHANDLER=1 \
      PYTHONUNBUFFERED=1 \
      PYTHONHASHSEED=random \
      PYTHONDONTWRITEBYTECODE=1 \
      # pip:
      PIP_NO_CACHE_DIR=1 \
      PIP_DISABLE_PIP_VERSION_CHECK=1 \
      PIP_DEFAULT_TIMEOUT=100 \
      PIP_ROOT_USER_ACTION=ignore \
      # poetry:
      POETRY_VERSION=1.4.0 \
      POETRY_NO_INTERACTION=1 \
      POETRY_CACHE_DIR='/var/cache/pypoetry' \
      POETRY_HOME='/usr/local'

RUN apk add --no-cache bash

RUN pip install "poetry==$POETRY_VERSION"

ENV PATH="$PATH:$POETRY_HOME/bin"

WORKDIR /code
COPY poetry.lock pyproject.toml alembic.ini /code/
COPY /migrations/ /code/app/sender_app/migrations/
COPY alembic.ini /code/app/sender_app/


RUN poetry install --no-interaction --no-ansi

COPY ./app/sender_app/ /code/app/sender_app/
COPY ./app/store/ /code/app/sender_app/app/store/
COPY ./app/web/config.py/ /code/app/sender_app/app/web/
COPY ./app/admin/ /code/app/sender_app/app/admin
