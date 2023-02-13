# Структура бота из статьи https://habr.com/ru/company/kts/blog/598575/

import asyncio
from typing import TYPE_CHECKING

import aio_pika
import bson
from sqlalchemy.exc import IntegrityError

from app.store.tg_api.accessor import TgClient
from app.store.tg_api.schemes import UpdateObj

if TYPE_CHECKING:
    from app.web.app import Application


class Worker:
    def __init__(self, token: str, concurrent_workers: int, app: 'Application'):
        self.tg_client = TgClient(token)
        self.app = app
        self.concurrent_workers = concurrent_workers
        self._tasks: list[asyncio.Task] = []

    async def handle_update(self, upd: UpdateObj):
        self.app.logger.info(
            f"worker text: {upd.message.text}" if upd.message else f'worker text: {upd.callback_query.message.text}')
        if upd.message:
            try:
                match upd.message.text:
                    case '/start':
                        await self.tg_client.send_message(
                            upd.message.chat.id,
                            text=f'{upd.message.from_.username} /pong')
                    case '/stop':
                        await self.tg_client.send_message(
                            upd.message.chat.id,
                            text=f'{upd.message.from_.username} /pong')
                    case '/ping':
                        await self.tg_client.send_message(
                            upd.message.chat.id,
                            text=f'{upd.message.from_.username} /pong')
            except IntegrityError as e:
                self.app.logger.info(f'start {e}')

    async def _worker_rabbit(self):
        try:
            channel = await self.app.rabbitMQ.connection_.channel()
            await channel.set_qos(prefetch_count=100)

            auth_exchange = await channel.declare_exchange(name="auth",
                                                           type=aio_pika.ExchangeType.TOPIC,
                                                           durable=True)

            queue = await channel.declare_queue(name=f"tg_bot",
                                                durable=True, )
            await queue.bind(auth_exchange, routing_key="tg_bot")

            await queue.consume(self.on_message, no_ack=True)

            print(" [*]worker.rabbit Waiting for messages")
            await asyncio.Future()
        except asyncio.CancelledError as e:
            self.app.logger.info(f'rabbit_worker asyncio {e}')
        except Exception as e:
            self.app.logger.info(f'rabbit_worker {e}')

    async def on_message(self, message):
        upd = UpdateObj.Schema().load(bson.loads(message.body))
        print("worker.rabbit is: %r" % upd)
        await self.handle_update(upd)

    async def start(self):
        self._tasks = [asyncio.create_task(self._worker_rabbit()) for _ in range(1)]

    async def stop(self):
        for t in self._tasks:
            t.cancel()
