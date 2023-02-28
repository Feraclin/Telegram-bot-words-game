
### миграции

poetry run alembic revision --autogenerate -m "name"
poetry run alembic upgrade --head

### тестовое покрытие

poetry run pytest --cov=app --cov-report=html

### aiohttp-devtools

poetry run adev runserver .

### примеры команд
Список команд:
/play - запустить игру,
/stop - остановить игру,
/ping проверка работы,
/help - справка.