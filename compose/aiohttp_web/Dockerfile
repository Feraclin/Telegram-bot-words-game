FROM python:3.11

RUN apt update && apt -y install gettext-base

COPY ./app/poller_app .

RUN pip install poetry && poetry install

EXPOSE 8080