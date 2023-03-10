FROM builder as poller
WORKDIR /code
COPY ./app/poller_app/  /code/app/poller_app/
COPY ./app/store/rabbitMQ/  /code/app/poller_app/app/store/rabbitMQ/
COPY ./app/store/tg_api/   /code/app/poller_app/app/store/tg_api/
COPY ./app/web/config.py/ /code/app/poller_app/app/web/
