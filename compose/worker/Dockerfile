FROM builder as worker

WORKDIR /code

COPY ./app/worker_app/ /code/app/worker_app/
COPY ./app/store/ /code/app/worker_app/app/store/
COPY ./app/web/config.py/ /code/app/worker_app/app/web/
COPY ./app/words_game/ /code/app/worker_app/app/words_game
COPY ./app/admin/ /code/app/worker_app/app/admin
COPY ./app/admin/ /code/app/worker_app/app/admin
COPY ./starter.py /code/app/worker_app/
