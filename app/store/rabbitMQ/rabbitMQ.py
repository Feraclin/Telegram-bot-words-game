import asyncio
import logging

from typing import TYPE_CHECKING, Dict, Optional

import aio_pika
import aiormq
import bson
from aio_pika import ExchangeType, Connection

from app.web.config import config_env

if TYPE_CHECKING:
    from app.web.app import Application

logger = logging.getLogger(__name__)


class RabbitMQ:
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

    async def connect(self, *_: list, **__: dict) -> None:
        """
        Open connection to RabbitMQ and declare auth exchange,
        try to reconnect every 10 seconds if there is a problem.
        """
        loop = asyncio.get_event_loop()
        try:
            connection = await aio_pika.connect_robust(self.url, loop=loop)
        except (ConnectionError, aiormq.exceptions.IncompatibleProtocolError) as e:
            logger.error(f"action=setup_rabbitmq, status=fail, retry=10s, {e}")
            await asyncio.sleep(10)
            await self.connect()
            return None

        channel = await connection.channel()
        auth_exchange = await channel.declare_exchange(
            name="auth-delayed",
            type=aio_pika.ExchangeType.X_DELAYED_MESSAGE,
            durable=True,
            arguments={"x-delayed-type": "direct"},
        )

        self.connection_ = connection
        self.exchange = auth_exchange
        # self.listener = asyncio.create_task(self.listen_events())
        logger.info(f"action=setup_rabbitmq, status=success")

    async def disconnect(self, *_: list, **__: dict) -> None:
        if self.connection_:
            await self.connection_.close()
        logger.info("action=close_rabbitmq, status=success")

    async def send_event(
        self,
        message: Dict,
        routing_key: str = "tg_bot",
        delay: int = 0,
    ) -> None:
        """Publish a message serialized to json to auth exchange."""

        await self.exchange.publish(
            aio_pika.Message(
                body=bson.dumps(message),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                headers={"x-delay": delay},
            ),
            routing_key=routing_key,
        )

    async def listen_events(self, routing_key: str = "tg_bot", on_message_func=None) -> None:
        try:
            channel = await self.connection_.channel()
            await channel.set_qos(prefetch_count=100)

            auth_exchange = await channel.declare_exchange(
                name="auth-delayed",
                type=aio_pika.ExchangeType.X_DELAYED_MESSAGE,
                durable=True,
                arguments={"x-delayed-type": "direct"},
            )

            queue = await channel.declare_queue(
                name=f"tg_bot",
                durable=True,
            )
            await queue.bind(auth_exchange, routing_key=routing_key)

            await queue.consume(on_message_func if on_message_func else self.on_message, no_ack=True)

            print(" [*] Waiting for messages. To exit press CTRL+C")
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

    @staticmethod
    async def on_message(message):
        logger.info("Message body is: %r" % bson.loads(message.body))


if __name__ == "__main__":
    host_test = config_env.get("RABBITMQ_DEFAULT_HOST")
    port_test = config_env.get("RABBITMQ_DEFAULT_PORT")
    user_test = config_env.get("RABBITMQ_DEFAULT_USER")
    password_test = config_env.get("RABBITMQ_DEFAULT_PASS")

    producer = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)
    consumer = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)

    message1 = {"message": "hello world"}
    message2 = {"message": "hello world 2"}
    message3 = {"message": "hello world 3"}
    message4 = {"message": "hello world 4"}
    message5 = {"message": "hello world 5"}

    async def main():
        await producer.connect()
        await consumer.connect()
        await producer.send_event(message1, delay=0)
        await producer.send_event(message2, delay=5000)
        await producer.send_event(message3, delay=2000)
        await producer.send_event(message4, delay=3000)
        await producer.send_event(message5, delay=15000)
        await consumer.listen_events()
        await producer.disconnect()
        await consumer.disconnect()

    asyncio.run(main())
