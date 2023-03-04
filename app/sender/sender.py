import asyncio
import logging
from dataclasses import dataclass, field

import bson

from app.store.tg_api.client import TgClient

from app.web.config import ConfigEnv
from app.store.words_game.accessor import WGAccessor
from app.store.database.database import Database
from app.store.rabbitMQ.rabbitMQ import RabbitMQ


@dataclass
class Sender:
    tg_client: TgClient = field(init=False)
    database: Database = field(init=False)
    rabbitMQ: RabbitMQ = field(init=False)
    cfg: ConfigEnv = field(kw_only=True)
    _tasks: list[asyncio.Task] = field(default_factory=list)
    concurrent_workers: int = field(kw_only=True, default=1)
    logger: logging.Logger = logging.getLogger("worker")

    def __post_init__(self):
        self.tg_client = TgClient(token=self.cfg.tg_token.tg_token)
        self.database = Database(cfg=self.cfg)
        self.words_game = WGAccessor(database=self.database)
        self.rabbitMQ = RabbitMQ(
            host=self.cfg.rabbitmq.host,
            port=self.cfg.rabbitmq.port,
            user=self.cfg.rabbitmq.user,
            password=self.cfg.rabbitmq.password,
        )

    async def on_message(self, message):
        upd = bson.loads(message.body)
        print(upd)
        await self.handle_update(upd)

    async def start(self):
        await self.database.connect()
        await self.rabbitMQ.connect()
        self._tasks = [asyncio.create_task(self._worker_rabbit()) for _ in range(self.concurrent_workers)]

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await self.rabbitMQ.disconnect()
        await self.database.disconnect()

    async def _worker_rabbit(self):
        await self.rabbitMQ.listen_events(on_message_func=self.on_message, routing_key="tg_bot_sender")

    async def handle_update(self, upd: dict):
        match upd.get("type_"):
            case  "test_delay":
                await self.tg_client.send_message(chat_id=upd["chat_id"],
                                                  text=upd["text"])
