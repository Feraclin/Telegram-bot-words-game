import asyncio
import logging
from .messages import keyboards

import bson

from app.store.tg_api.client import TgClient


from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.web.config import ConfigEnv


class Sender:
    """
    Класс Sender отвечает за отправку сообщений в Telegram.

    Атрибуты:
    - cfg: объект ConfigEnv с конфигурационными параметрами
    - concurrent_workers: количество одновременных работников
    - _tasks: список объектов asyncio.Task для запуска работников
    - logger: объект logging.Logger для логирования сообщений
    - tg_client: объект TgClient для работы с Telegram API
    - rabbitMQ: объект RabbitMQ для отправки сообщений в очередь
    - routing_key_worker: ключ маршрутизации для работников
    - routing_key_sender: ключ маршрутизации для отправителя
    - queue_name: имя очереди для отправки сообщений

    Методы:
    - __init__(self, cfg: ConfigEnv, concurrent_workers: int = 1): конструктор класса
    - on_message(self, message): метод-обработчик для получения сообщений из очереди
    - start(self): метод для запуска отправителя
    - stop(self): метод для остановки отправителя
    - _worker_rabbit(self): метод для запуска работника для получения сообщений из очереди
    - handle_update(self, upd: dict): метод для обработки обновлений из Telegram
    - check_poll(self, upd: dict): метод для проверки результатов опроса
    """

    def __init__(self, cfg: ConfigEnv, concurrent_workers: int = 1):
        """
        Конструктор класса Sender.

        Параметры:
        - cfg: объект ConfigEnv с конфигурационными параметрами
        - concurrent_workers: количество одновременных работников
        """
        self.cfg = cfg
        self.concurrent_workers = concurrent_workers
        self._tasks = []
        self.logger = logging.getLogger("sender")
        self.tg_client = TgClient(token=self.cfg.tg_token.tg_token)
        self.rabbitMQ = RabbitMQ(
            host=self.cfg.rabbitmq.host,
            port=self.cfg.rabbitmq.port,
            user=self.cfg.rabbitmq.user,
            password=self.cfg.rabbitmq.password,
        )
        self.routing_key_worker = "worker"
        self.routing_key_sender = "sender"
        self.queue_name = "tg_bot_sender"

    async def on_message(self, message):
        """
        Метод-обработчик для получения сообщений из очереди.

        Параметры:
        - message: объект aio-pika.Message с полученным сообщением
        """
        upd = bson.loads(message.body)
        await self.handle_update(upd)
        await message.ack()

    async def start(self):
        """
        Метод для пуска Sender и запуска работника для получения сообщений из очереди RabbitMQ.
        """
        await self.rabbitMQ.connect()
        self._tasks = [
            asyncio.create_task(self._worker_rabbit()) for _ in range(self.concurrent_workers)
        ]

    async def stop(self):
        """
        Метод для остановки Sender и остановки работника для получения
        сообщений из очереди RabbitMQ.
        """
        for task_ in self._tasks:
            task_.cancel()
        await self.rabbitMQ.disconnect()

    async def _worker_rabbit(self):
        """
        Работник для получения сообщений из очереди.
        """
        await self.rabbitMQ.listen_events(
            on_message_func=self.on_message,
            queue_name=self.queue_name,
            routing_key=[self.routing_key_sender],
        )

    async def handle_update(self, upd: dict):
        """
        Метод для обработки обновлений из Telegram.

        Параметры:
        - upd: словарь с обновлением из Telegram
        """
        match upd.get("type_"):
            case "message":
                """
                Обработка сообщения.
                """
                await self.tg_client.send_message(
                    chat_id=upd["chat_id"],
                    text=upd["text"],
                    force_reply=upd.get("force_reply", False),
                )
            case "message_keyboard":
                """
                Обработка сообщения с клавиатурой.
                """
                keyboard = await self.tg_client.send_keyboard(
                    chat_id=upd["chat_id"], text=upd["text"], keyboard=keyboards[upd["keyboard"]]
                )
                if upd.get("live_time", None):
                    upd["keyboard_message_id"] = keyboard.result.message_id
                    upd["type_"] = "message_inline_remove_keyboard"
                    await self.rabbitMQ.send_event(
                        message=upd,
                        routing_key=self.routing_key_sender,
                        delay=upd["live_time"] * 1000,
                    )
            case "message_inline_remove_keyboard":
                """
                Обработка сообщения с inline клавиатурой.
                """
                await self.tg_client.remove_inline_keyboard(
                    chat_id=upd["chat_id"], message_id=upd["keyboard_message_id"]
                )
                message = {"type_": "pick_leader", "chat_id": upd["chat_id"]}
                await self.rabbitMQ.send_event(message=message, routing_key=self.routing_key_worker)
            case "callback_alert":
                """
                Обработка callback alert.
                """
                await self.tg_client.send_callback_alert(
                    callback_id=upd["callback_id"],
                    text=upd["text"],
                )
            case "send_poll":
                """
                Отправка опроса в чат.
                """
                poll = await self.tg_client.send_poll(
                    chat_id=upd["chat_id"],
                    question=upd["question"],
                    options=upd["options"],
                    anonymous=upd["anonymous"],
                    period=upd.get("period", 10),
                )
                upd["type_"] = "send_poll_answer"
                upd["poll_message_id"] = poll.result.message_id
                upd["poll_id"] = poll.result.poll.id
                await self.rabbitMQ.send_event(
                    message={
                        "type_": "poll_id",
                        "poll_id": poll.result.poll.id,
                        "chat_id": upd["chat_id"],
                    },
                    routing_key=self.routing_key_worker,
                )
                await self.rabbitMQ.send_event(
                    message=upd,
                    routing_key=self.routing_key_sender,
                    delay=(upd.get("period", 10) + 2) * 1000,
                )
            case "send_poll_answer":
                """
                Проверка ответов на опрос.
                """
                await self.check_poll(upd)
            case _:
                """
                Обработка неизвестного типа сообщения.
                """
                self.logger.error(f"Unknown type: {upd['type_']}")

    async def check_poll(self, upd: dict):
        """
        Проверка ответов на опрос и отправка результата в RabbitMQ.
        """
        poll = await self.tg_client.remove_inline_keyboard(
            chat_id=upd["chat_id"],
            message_id=upd["poll_message_id"],
        )
        word = poll.result.poll.question.split()[4]
        answers = poll.result.poll.options
        yes = 0
        no = 0
        for ans in answers:
            match ans.text:
                case "Yes":
                    yes = ans.voter_count
                case "No":
                    no = ans.voter_count

        if yes > no:
            res_poll = "yes"
        else:
            res_poll = "no"

            await self.tg_client.send_message(
                chat_id=upd["chat_id"], text=f"{word} - нет такого слова"
            )
        message_poll_result = {
            "type_": "poll_result",
            "chat_id": upd["chat_id"],
            "poll_id": upd["poll_id"],
            "poll_result": res_poll,
            "word": word,
        }

        await self.rabbitMQ.send_event(
            message=message_poll_result, routing_key=self.routing_key_worker
        )
