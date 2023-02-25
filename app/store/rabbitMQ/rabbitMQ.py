import asyncio
import logging
from typing import TYPE_CHECKING, Dict

import aio_pika
import aiormq
import bson
from aio_pika import ExchangeType, Connection

from app.store.tg_api.schemes import UpdateObj

if TYPE_CHECKING:
    from app.web.app import Application

logger = logging.getLogger(__name__)


class RabbitMQ:
    def __init__(self, app: 'Application' = None, host: str|None = None):
        self.url = f"amqp://{app.config.rabbitmq.user}:{app.config.rabbitmq.password}@{app.config.rabbitmq.host}:{app.config.rabbitmq.port}/" if app else f"amqp://user:pass@{host}/"
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
            connection = await aio_pika.connect_robust(self.url,
                                                       loop=loop)
        except (ConnectionError, aiormq.exceptions.IncompatibleProtocolError) as e:
            logger.error(f"action=setup_rabbitmq, status=fail, retry=10s, {e}")
            await asyncio.sleep(10)
            await self.connect()
            return None

        channel = await connection.channel()
        auth_exchange = await channel.declare_exchange(name="auth", type=aio_pika.ExchangeType.TOPIC, durable=True)

        self.connection_ = connection
        self.exchange = auth_exchange
        # self.listener = asyncio.create_task(self.listen_events())
        logger.info(f"action=setup_rabbitmq, status=success")

    async def disconnect(self, *_: list, **__: dict) -> None:
        if self.connection_:
            await self.connection_.close()
        logger.info("action=close_rabbitmq, status=success")

    async def send_event(self,
                         message: Dict,
                         routing_key: str = 'tg_bot',
                         ) -> None:
        """ Publish a message serialized to json to auth exchange. """

        await self.exchange.publish(
            aio_pika.Message(
                body=bson.dumps(message),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )

    async def listen_events(self) -> None:
        try:
            channel = await self.connection_.channel()
            await channel.set_qos(prefetch_count=100)

            auth_exchange = await channel.declare_exchange(name="auth",
                                                           type=aio_pika.ExchangeType.TOPIC,
                                                           durable=True)

            queue = await channel.declare_queue(name=f"tg_bot",
                                                durable=True,)
            await queue.bind(auth_exchange, routing_key="tg_bot")

            await queue.consume(self.on_message, no_ack=True)

            print(" [*] Waiting for messages. To exit press CTRL+C")
            await asyncio.Future()
        except asyncio.CancelledError:
            pass

    @staticmethod
    async def on_message(message):
        print("Message body is: %r" % UpdateObj.Schema().load(bson.loads(message.body)))
