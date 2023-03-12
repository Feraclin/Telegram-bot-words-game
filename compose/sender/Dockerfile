FROM builder AS sender

WORKDIR /code

COPY ./app/sender_app/ /code/app/sender_app/
COPY ./app/store/ /code/app/sender_app/app/store/
COPY ./app/web/config.py/ /code/app/sender_app/app/web/
COPY ./app/admin/ /code/app/sender_app/app/admin
COPY ./app/words_game/ /code/app/sender_app/app/words_game