FROM builder AS sender

WORKDIR /code
COPY /migrations/ /code/app/sender_app/migrations/
COPY alembic.ini /code/app/sender_app/

RUN poetry install --no-interaction --no-ansi

COPY ./app/sender_app/ /code/app/sender_app/
COPY ./app/store/ /code/app/sender_app/app/store/
COPY ./app/web/config.py/ /code/app/sender_app/app/web/
COPY ./app/admin/ /code/app/sender_app/app/admin

CMD ["python", "/code/app/sender_app/main.py"]