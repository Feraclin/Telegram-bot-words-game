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
                        if upd.message.chat.type == 'private':
                            await self.tg_client.send_keyboard_to_player(
                                upd.message.chat.id,
                                mentinion=f'Check keyboard',
                                keyboard=keyboard)
                        else:
                            await self.chose_your_team(upd)
                    case '/yes' if upd.message.chat.type == 'private':
                        await self.start_game(upd)
                    case '/stop' if upd.message.chat.type == 'private':
                        await self.stop_game(user_id=upd.message.from_.id,
                                             chat_id=upd.message.chat.id,
                                             username=upd.message.from_.username)
                    case '/ping':
                        await self.tg_client.send_message(
                            upd.message.chat.id,
                            text=f'{upd.message.from_.username} /pong')
                    case _:
                        if game := await self.app.store.words_game.select_active_session_by_id(user_id=upd.message.from_.id):
                            await self.check_cityname(user_id=upd.message.from_.id,
                                                      chat_id=upd.message.chat.id,
                                                      username=upd.message.from_.username,
                                                      city_name=upd.message.text)
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

    async def start_game(self, upd: UpdateObj) -> None:
        if await self.app.store.words_game.select_active_session_by_id(upd.message.from_.id):
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id,
                text=f'{upd.message.from_.username} тебе не много?')
            return
        user = await self.app.store.words_game.create_user(user_id=upd.message.from_.id,
                                                           username=upd.message.from_.username)
        await self.app.store.words_game.create_gamesession(user_id=user.id,
                                                           chat_id=upd.message.chat.id,
                                                           chat_type=upd.message.chat.type)
        await self.tg_client.send_message(
            chat_id=upd.message.chat.id,
            text=f"{upd.message.from_.username} let's play")
        if upd.message.chat.type == 'private':
            await self.pick_cityname(user_id=upd.message.from_.id,
                                     chat_id=upd.message.chat.id,
                                     username=upd.message.from_.username)
        else:
            await self.chose_your_team(chat_id=upd.message.chat.id,)

    async def stop_game(self, user_id: int, chat_id: int, username: str) -> None:
        if game := await self.app.store.words_game.select_active_session_by_id(user_id):
            await self.app.store.words_game.update_gamesession(game_id=game.id,
                                                               status=False)
            await self.tg_client.send_message(
                chat_id=chat_id,
                text=f'{username} sad troumbone')

    async def pick_cityname(self,
                            user_id: int,
                            chat_id: int,
                            username: str,
                            letter: str|None = None) -> None:

        game = await self.app.store.words_game.select_active_session_by_id(user_id)
        city = await self.app.store.words_game.get_city_by_first_letter(letter=letter, game_session_id=game.id)

        first_letter = (city.name[-1] if city.name[-1] not in 'ьыъйё' else city.name[-2]).capitalize()

        await self.app.store.words_game.update_gamesession(game_id=game.id,
                                                           next_letter=first_letter)
        await self.app.store.words_game.set_city_to_used(city_id=city.id,
                                                         game_session_id=game.id)
        await self.tg_client.send_message(
                chat_id=chat_id,
                text=f"""{username} {city.name}
                Тебе на {first_letter}""")

    async def check_cityname(self,
                             user_id: int,
                             chat_id: int,
                             username: str,
                             city_name: str) -> None:
        if city := await self.app.store.words_game.get_city_by_name(city_name.strip('/').capitalize()):
            letter = (city.name[-1] if city.name[-1] not in 'ьыъйё' else city.name[-2]).capitalize()

            game = await self.app.store.words_game.select_active_session_by_id(user_id)

            if await self.app.store.words_game.check_city_in_used(city_id=city.id,
                                                                  game_session_id=game.id):
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f'{username} {city.name}, Был такой город.')
                return
            if game.next_start_letter == city_name[1]:
                await self.app.store.words_game.update_gamesession(game_id=game.id,
                                                                   next_letter=letter)
                await self.app.store.words_game.set_city_to_used(city_id=city.id,
                                                                 game_session_id=game.id)
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f'{username} {city.name} Есть такой город. Мне на {letter}')
                await self.pick_cityname(user_id=user_id,
                                         chat_id=chat_id,
                                         username=username,
                                         letter=letter)
            else:
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f'{username} {city.name} на {city.name[0]}, а тебе на {game.next_start_letter}')
        else:
            await self.tg_client.send_message(
                chat_id=chat_id,
                text=f'{username} {city_name} Нет такого города')

    async def chose_your_team(self, upd: UpdateObj) -> None:
        keyboard = {'inline_keyboard': [
            [{"text": "Yes", 'callback_data': '/yes'},
             {"text": "No", 'callback_data': '/no'}]
        ],
            "resize_keyboard": True,
            "one_time_keyboard": True
        }
        await self.tg_client.send_keyboard(upd.message.chat.id,
                                           text=f'Будешь играть?',
                                           keyboard=keyboard)
