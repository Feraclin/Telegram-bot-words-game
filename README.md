### Запуск

main.py общая точка входа для Poller, Worker и Aiohttp

для запуска игры команда /play в приватном чате запускается игра в города, в групповом чате формируется команда для игры в слова

для игры в города требуется база городов скрипт расположен app/store/database/city.sql

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