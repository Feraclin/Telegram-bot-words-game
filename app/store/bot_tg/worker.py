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
                        keyboard = {'keyboard': [[{"text": "/yes"}, {"text": "/no"}]],
                                    "resize_keyboard": True,
                                    "one_time_keyboard": True,
                                    "selective": True,
                                    'input_field_placeholder': "You wanna play?"
                                    }
                        await self.tg_client.send_keyboard_to_player(
                            upd.message.chat.id,
                            mentinion=f'{upd.message.from_.username} check keyboard',
                            keyboard=keyboard)
                    case '/yes':
                        await self.start_game(user_id=upd.message.from_.id,
                                              username=upd.message.from_.username,
                                              chat_id=upd.message.chat.id)
                    case '/stop':
                        await self.stop_game(user_id=upd.message.from_.id,
                                             chat_id=upd.message.chat.id)
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
            print(t)
            t.cancel()

    async def start_game(self, user_id: int, username: str, chat_id: int) -> None:
        if await self.app.store.words_game.select_active_session_by_id(user_id):
            await self.tg_client.send_message(
                chat_id=chat_id,
                text=f'{username} тебе не много?')
            return
        user = await self.app.store.words_game.create_user(user_id=user_id,
                                                           username=username)
        await self.app.store.words_game.create_gamesession(user_id=user.id)
        await self.tg_client.send_message(
            chat_id=chat_id,
            text=f"{username} let's play")

    async def stop_game(self, user_id: int, chat_id: int) -> None:
        if game := await self.app.store.words_game.select_active_session_by_id(user_id):
            await self.app.store.words_game.update_gamesession(game_id=game.id,
                                                               status=False)

