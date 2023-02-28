import typing

from app.store.bot_tg.bot_tg import TgBotAccessor
from app.store.database.database import Database
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.words_game.accessor import WGAccessor
from app.store.yandex_dict_api.accessor import YandexDictAccessor

if typing.TYPE_CHECKING:
    from app.web.app import Application


class Store:
    def __init__(self, app: "Application"):

        from app.store.admin.accessor import AdminAccessor
        from app.store.quiz.accessor import QuizAccessor


        self.quizzes = QuizAccessor(app)
        self.admins = AdminAccessor(app)
        self.words_game = WGAccessor(app)
        self.yandex_dict = YandexDictAccessor(app)
        self.tg_bot = TgBotAccessor(token=app.config.bot.tg_token, n=1, app=app)


def setup_store(app: "Application"):
    app.rabbitMQ = RabbitMQ(app)
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_startup.append(app.rabbitMQ.connect)
    app.on_cleanup.append(app.database.disconnect)
    app.on_cleanup.append(app.rabbitMQ.disconnect)
    app.store = Store(app)
