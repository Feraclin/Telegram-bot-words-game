import asyncio
import logging

from typing import TYPE_CHECKING, Dict, Optional

import aio_pika
import aiormq
import bson
from aio_pika import ExchangeType, Connection

if TYPE_CHECKING:
    from app.web.app import Application
logging.basicConfig(level=logging.INFO)


class RabbitMQ:
    """
    RabbitMQ client
    Методы:

    connect - подключение к RabbitMQ
    disconnect - отключение от RabbitMQ
    send_event - отправка сообщения
    listen_events - прослушивание событий
    """
    def __init__(
        self,
        app: Optional["Application"] = None,
        host: str | None = None,
        port: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.host = host if host else app.config.rabbitmq.host
        self.port = port if port else app.config.rabbitmq.port
        self.user = user if user else app.config.rabbitmq.user
        self.password = password if password else app.config.rabbitmq.password
        self.url = f"amqp://{self.user}:{self.password}@{self.host}:{self.port}/"

        self.exchange: ExchangeType | None = None
        self.connection_: Connection | None = None
        self.listener: asyncio.Task | None = None
        self.app = app
        self.logger = logging.getLogger("rabbit")
        self.channel: aio_pika.RobustChannel | None = None

    async def connect(self) -> None:
        """
        Подключение к RabbitMQ
        """
        loop = asyncio.get_event_loop()
        try:
            connection = await aio_pika.connect_robust(self.url, loop=loop)

        except (ConnectionError, aiormq.exceptions.IncompatibleProtocolError) as e:
            self.logger.error(f"action=setup_rabbitmq, status=fail, retry=10s, {e}")
            await asyncio.sleep(10)
            await self.connect()
            return None

        channel = await connection.channel(publisher_confirms=True)
        auth_exchange = await channel.declare_exchange(
            name="auth-delayed",
            type=aio_pika.ExchangeType.X_DELAYED_MESSAGE,
            durable=True,
            arguments={"x-delayed-type": "direct"},
        )
        self.channel = channel
        self.connection_ = connection
        self.exchange = auth_exchange
        self.logger.info("action=setup_rabbitmq, status=success")

    async def disconnect(self) -> None:
        """
        Отключение от RabbitMQ
        """
        if self.channel:
            await self.channel.close()
            self.channel = None
        if self.connection_:
            await self.connection_.close()
            self.connection_ = None
        self.logger.info("action=close_rabbitmq, status=success")

    async def send_event(
        self,
        message: Dict,
        routing_key: str,
        delay: int = 0,
    ) -> None:

        """
        Отправка сообщения
        :param message: словарь с сообщением
        :param routing_key: роутинг ключ
        :param delay: время жизни сообщения
        """
        self.logger.info(f"action=send_event, status=success, message={message}")

        await self.exchange.publish(
            aio_pika.Message(
                body=bson.dumps(message),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-delay": delay},
            ),
            routing_key=routing_key,
            mandatory=False,
        )

    async def listen_events(
        self, routing_key: list[str], queue_name: str, on_message_func=None
    ) -> None:
        """
        Прослушивание событий
        :param routing_key: роутинг ключ
        :param queue_name: имя очереди
        :param on_message_func: функция, которая будет вызвана при получении сообщения
        """
        self.logger.info(f"action=listen_events, status=success, routing_key={routing_key}, queue_name={queue_name}")

        try:
            channel = await self.connection_.channel()
            await channel.set_qos(prefetch_count=1)

            auth_exchange = await channel.declare_exchange(
                name="auth-delayed",
                type=aio_pika.ExchangeType.X_DELAYED_MESSAGE,
                durable=True,
                arguments={"x-delayed-type": "direct"},
            )

            queue = await channel.declare_queue(
                name=queue_name,
                durable=True,
            )
            for key in routing_key:
                await queue.bind(auth_exchange, routing_key=key)

            await queue.consume(on_message_func if on_message_func else self.on_message)

            self.logger.info(" [*] Waiting for messages. To exit press CTRL+C")
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

    async def on_message(self, message):
        """
        Функция, которая будет вызвана при получении сообщения
        :param message: сообщение
        """
        self.logger.info("Message body is: %r" % bson.loads(message.body))
