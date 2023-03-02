import os
import typing
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

if typing.TYPE_CHECKING:
    from app.web.app import Application

env_name = '.env'

BASE_DIR = Path(__file__).resolve().parent.parent.parent
print(BASE_DIR)

dotenv_file = os.path.join(BASE_DIR, env_name)
if os.path.isfile(dotenv_file):
    load_dotenv(dotenv_file)

# else:
#     raise Exception
config_env = os.environ
print(config_env)


@dataclass
class SessionConfig:
    key: str


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class BotConfig:
    token: str
    group_id: int
    tg_token: str | None = None


@dataclass
class TgConfig:
    tg_token: str


@dataclass
class DatabaseConfig:
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class RabbitMQ:
    user: str
    password: str
    host: str
    port: str


@dataclass
class YandexDictConfig:
    token: str


@dataclass
class Config:
    admin: AdminConfig
    session: SessionConfig = None
    bot: BotConfig = None
    database: DatabaseConfig = None
    rabbitmq: RabbitMQ = None
    yandex_dict: YandexDictConfig = None


def setup_config(app: "Application"):

    app.config = config


@dataclass
class ConfigEnv:
    admin: AdminConfig
    session: SessionConfig = None
    database: DatabaseConfig = None
    rabbitmq: RabbitMQ = None
    yandex_dict: YandexDictConfig = None
    tg_token: TgConfig = None


config = ConfigEnv(
    admin=AdminConfig(
        email=config_env.get('EMAIL'),
        password=config_env.get('PASSWORD')
    ),
    session=SessionConfig(
        key=config_env.get("SESSION_KEY")
    ),
    database=DatabaseConfig(
        host=config_env.get("POSTGRES_DEFAULT_HOST"),
        port=int(config_env.get("POSTGRES_DEFAULT_PORT")),
        user=config_env.get("POSTGRES_DEFAULT_USER"),
        password=config_env.get("POSTGRES_DEFAULT_PASS"),
        database=config_env.get("POSTGRES_DEFAULT_DB"),
    ),
    rabbitmq=RabbitMQ(
        host=config_env.get("RABBITMQ_DEFAULT_HOST"),
        port=config_env.get("RABBITMQ_DEFAULT_PORT"),
        user=config_env.get("RABBITMQ_DEFAULT_USER"),
        password=config_env.get("RABBITMQ_DEFAULT_PASS"),
    ),
    yandex_dict=YandexDictConfig(
        token=config_env['YANDEX_DICT_TOKEN'],
    ),
    tg_token=TgConfig(tg_token=config_env['BOT_TOKEN_TG'])
)


print(config)
