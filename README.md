
### миграции

poetry run alembic revision --autogenerate -m "name"
poetry run alembic upgrade --head

### тестовое покрытие

 poetry run pytest --cov=app --cov-report=html
