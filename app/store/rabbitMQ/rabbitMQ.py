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
logging.basicConfig(level=logging.INFO)


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
        self.logger = logging.getLogger("rabbit")

    async def connect(self, *_: list, **__: dict) -> None:
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

        self.connection_ = connection
        self.exchange = auth_exchange
        self.logger.info(f"action=setup_rabbitmq, status=success")

    async def disconnect(self, *_: list, **__: dict) -> None:
        if self.connection_:
            await self.connection_.close()
        self.logger.info("action=close_rabbitmq, status=success")

    async def send_event(
        self,
        message: Dict,
        routing_key: str,
        delay: int = 0,
    ) -> None:
        """Publish a message serialized to json to auth exchange."""
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

    async def listen_events(self,
                            routing_key: list[str],
                            queue_name: str,
                            on_message_func=None) -> None:
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

            await queue.consume(
                on_message_func if on_message_func else self.on_message)

            self.logger.info(" [*] Waiting for messages. To exit press CTRL+C")
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

    async def on_message(self, message):
        print("message received")
        self.logger.info("Message body is: %r" % bson.loads(message.body))


if __name__ == "__main__":
    host_test = config_env.get("RABBITMQ_DEFAULT_HOST")
    port_test = config_env.get("RABBITMQ_DEFAULT_PORT")
    user_test = config_env.get("RABBITMQ_DEFAULT_USER")
    password_test = config_env.get("RABBITMQ_DEFAULT_PASS")

    producer = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)
    producer1 = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)
    consumer = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)
    consumer1 = RabbitMQ(host=host_test, port=port_test, user=user_test, password=password_test)

    message1 = {"message": "hello world"}
    message2 = {"message": "hello world 2"}
    message3 = {"message": "hello world 3"}
    message4 = {"message": "hello world 4"}
    message5 = {"message": "hello world 5"}

    async def main():
        await producer.connect()
        await producer1.connect()
        await consumer.connect()
        await consumer1.connect()

        await producer.send_event(message1, delay=0)
        await producer1.send_event(message2, delay=5000)
        await producer.send_event(message3, delay=2000)
        await producer1.send_event(message4, delay=3000)
        await producer.send_event(message5, delay=15000)
        await producer1.send_event(message1, delay=0, routing_key="tg_bot_sender")
        await producer.send_event(message2, delay=5000, routing_key="tg_bot_sender")
        await producer1.send_event(message3, delay=2000, routing_key="tg_bot_sender")
        await producer.send_event(message4, delay=3000, routing_key="tg_bot_sender")
        await producer1.send_event(message5, delay=15000, routing_key="tg_bot_sender")
        await consumer.listen_events()
        await consumer.listen_events(routing_key="tg_bot_sender")
        await producer.disconnect()
        await consumer.disconnect()
        await producer1.disconnect()
        await consumer1.disconnect()

    asyncio.run(main())
