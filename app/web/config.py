import typing
from dataclasses import dataclass
from dotenv import dotenv_values, find_dotenv

import yaml

if typing.TYPE_CHECKING:
    from app.web.app import Application

found_dotenv = find_dotenv(filename='.env')
config_env = dotenv_values(found_dotenv)


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
    port: str
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


def setup_config(app: "Application", config_path: str):
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    app.config = Config(
        session=SessionConfig(
            key=raw_config["session"]["key"],
        ),
        admin=AdminConfig(
            email=raw_config["admin"]["email"],
            password=raw_config["admin"]["password"],
        ),
        bot=BotConfig(
            token=raw_config["bot"]["token"],
            group_id=raw_config["bot"]["group_id"],
            tg_token=config_env['BOT_TOKEN_TG']
        ),
        database=DatabaseConfig(**raw_config["database"]),
        rabbitmq=RabbitMQ(
            host=raw_config["rabbitmq"]["host"],
            port=raw_config["rabbitmq"]["port"],
            user=raw_config["rabbitmq"]["user"],
            password=raw_config["rabbitmq"]["password"],
        ),
        yandex_dict=YandexDictConfig(
            token=config_env['YANDEX_DICT_TOKEN'],
        ),
    )


@dataclass
class ConfigEnv:
    database: DatabaseConfig = None
    rabbitmq: RabbitMQ = None
    yandex_dict: YandexDictConfig = None
    tg_token: TgConfig = None


config = ConfigEnv(
    database=DatabaseConfig(
        host=config_env.get("DATABASE_DEFAULT_HOST"),
        port=config_env.get("DATABASE_DEFAULT_PORT"),
        user=config_env.get("DATABASE_DEFAULT_USER"),
        password=config_env.get("DATABASE_DEFAULT_PASS"),
        database=config_env.get("DATABASE_DEFAULT_DB"),
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
