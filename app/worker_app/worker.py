import asyncio
import logging
from dataclasses import dataclass, field
from random import choice

import bson
from sqlalchemy.exc import IntegrityError
from app.worker_app.constant import help_msg
from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import UpdateObj, SendMessageResponse
from app.words_game.models import GameSession

from app.web.config import ConfigEnv
from app.store.words_game.accessor import WGAccessor
from app.store.database.database import Database
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.yandex_dict_api.accessor import YandexDictAccessor


@dataclass
class Worker:
    tg_client: TgClient = field(init=False)
    database: Database = field(init=False)
    words_game: WGAccessor = field(init=False)
    rabbitMQ: RabbitMQ = field(init=False)
    yandex_dict: YandexDictAccessor = field(init=False)
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
        self.yandex_dict = YandexDictAccessor(token=self.cfg.yandex_dict.token)

    async def handle_update(self, upd: UpdateObj):
        if upd.message:
            try:
                match upd.message.text:
                    case "/play":
                        keyboard = {
                            "keyboard": [[{"text": "/yes"}, {"text": "/no"}]],
                            "resize_keyboard": True,
                            "one_time_keyboard": True,
                            "selective": True,
                            "input_field_placeholder": "You wanna play?",
                        }
                        if upd.message.chat.type == "private":
                            await self.tg_client.send_keyboard_to_player(
                                upd.message.chat.id, text=f"Check keyboard", keyboard=keyboard
                            )
                        else:
                            await self.chose_your_team(upd)
                    case "/yes" if upd.message.chat.type == "private":
                        await self.start_game(upd)
                    case "/stop":
                        await self.stop_game(upd=upd)
                    case "/ping":
                        await self.tg_client.send_message(
                            upd.message.chat.id, text=f"{upd.message.from_.username} /pong"
                        )
                    case "/help":
                        await self.tg_client.send_message(upd.message.chat.id, text=help_msg)
                    case "/poll":
                        poll = await self.tg_client.send_poll(
                            chat_id=upd.message.chat.id,
                            question="Вот что я умею?",
                            answers=["yes", "no", "maybe"],
                            anonymous=True,
                            period=5,
                        )

                        await asyncio.sleep(10)

                        stop_poll = await self.tg_client.remove_inline_keyboard(
                            chat_id=upd.message.chat.id, message_id=poll.result.message_id
                        )
                        print(stop_poll)

                    case "/reply":
                        await self.tg_client.send_message(
                            chat_id=upd.message.chat.id,
                            text=f"@{upd.message.from_.username} reply",
                            force_reply=True,
                        )
                    case "/inline_keyboard":
                        keyboard = {
                            "inline_keyboard": [
                                [
                                    {"text": "Yes", "callback_data": "/yes"},
                                    {"text": "No", "callback_data": "/no"},
                                ]
                            ],
                            "resize_keyboard": True,
                            "one_time_keyboard": True,
                        }
                        inline_message = await self.tg_client.send_keyboard(
                            upd.message.chat.id, text=f"Будешь играть?", keyboard=keyboard
                        )

                        await asyncio.sleep(5)

                        await self.tg_client.remove_inline_keyboard(
                            chat_id=inline_message.result.chat.id,
                            message_id=inline_message.result.message_id,
                        )

                    case _ if upd.message.chat.type != "private" and await self.words_game.select_active_session_by_id(
                        chat_id=upd.message.chat.id
                    ):
                        await self.check_word(upd=upd)

                    case _ if await self.words_game.select_active_session_by_id(
                        user_id=upd.message.from_.id
                    ):
                        await self.check_city(
                            user_id=upd.message.from_.id,
                            chat_id=upd.message.chat.id,
                            username=upd.message.from_.username,
                            city_name=upd.message.text,
                        )
            except IntegrityError as e:
                self.logger.info(f"start {e}")
        elif upd.callback_query:
            try:
                match upd.callback_query.data:
                    case "/yes":
                        await self.add_to_team(upd)
                    case _:
                        pass
            except IntegrityError as e:
                self.logger.info(f"callback {e}")
        elif upd.poll and upd.poll.is_closed is True:
            try:
                await self.check_poll(upd)
            except IntegrityError as e:
                self.logger.info(f"poll {e}")

    async def _worker_rabbit(self):
        await self.rabbitMQ.listen_events(on_message_func=self.on_message)

    async def on_message(self, message):
        upd = UpdateObj.Schema().load(bson.loads(message.body))
        # print("worker.rabbit is: %r" % upd)
        await self.handle_update(upd)

    async def start(self):
        await self.database.connect()
        await self.rabbitMQ.connect()
        self._tasks = [asyncio.create_task(self._worker_rabbit()) for _ in range(1)]

    async def stop(self):
        for t in self._tasks:
            t.cancel()
        await self.rabbitMQ.disconnect()
        await self.database.disconnect()

    async def start_game(self, upd: UpdateObj) -> None:
        if await self.words_game.select_active_session_by_id(upd.message.from_.id):
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id, text=f"{upd.message.from_.username} тебе не много?"
            )
            return
        user = await self.words_game.create_user(
            user_id=upd.message.from_.id, username=upd.message.from_.username
        )
        await self.words_game.create_game_session(
            user_id=user.id, chat_id=upd.message.chat.id, chat_type=upd.message.chat.type
        )
        await self.tg_client.send_message(
            chat_id=upd.message.chat.id, text=f"{upd.message.from_.username} let's play"
        )
        if upd.message.chat.type == "private":
            await self.pick_city(
                user_id=upd.message.from_.id,
                chat_id=upd.message.chat.id,
                username=upd.message.from_.username,
            )
        else:
            await self.chose_your_team(upd=upd)

    async def stop_game(self, upd: UpdateObj) -> None:
        if game := await self.words_game.select_active_session_by_id(chat_id=upd.message.chat.id):
            await self.words_game.update_game_session(game_id=game.id, status=False)
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id, text=f"{upd.message.from_.username} sad trombone"
            )

    async def pick_city(
        self, user_id: int, chat_id: int, username: str, letter: str | None = None
    ) -> None:
        game = await self.words_game.select_active_session_by_id(user_id)
        city = await self.words_game.get_city_by_first_letter(
            letter=letter, game_session_id=game.id
        )
        if not city:
            return await self.bot_looser(game_session_id=game.id)
        first_letter = (
            city.name[-1] if city.name[-1] not in "ьыъйё" else city.name[-2]
        ).capitalize()

        await self.words_game.update_game_session(game_id=game.id, next_letter=first_letter)
        await self.words_game.set_city_to_used(city_id=city.id, game_session_id=game.id)
        await self.tg_client.send_message(
            chat_id=chat_id,
            text=f"""{username} {city.name}
                Тебе на {first_letter}""",
        )

    async def check_city(self, user_id: int, chat_id: int, username: str, city_name: str) -> None:
        if city := await self.words_game.get_city_by_name(city_name.strip("/")):
            letter = (city.name[-1] if city.name[-1] not in "ьыъйё" else city.name[-2]).capitalize()

            game = await self.words_game.select_active_session_by_id(user_id)

            if await self.words_game.check_city_in_used(city_id=city.id, game_session_id=game.id):
                await self.tg_client.send_message(
                    chat_id=chat_id, text=f"{username} {city.name}, Был такой город."
                )
                return
            if game.next_start_letter == city_name[1]:
                await self.words_game.update_game_session(game_id=game.id, next_letter=letter)
                await self.words_game.set_city_to_used(city_id=city.id, game_session_id=game.id)
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f"{username} {city.name} Есть такой город. Мне на {letter}",
                )
                await self.pick_city(
                    user_id=user_id, chat_id=chat_id, username=username, letter=letter
                )
            else:
                await self.tg_client.send_message(
                    chat_id=chat_id,
                    text=f"{username} {city.name} на {city.name[0]}, а тебе на {game.next_start_letter}",
                )
        else:
            await self.tg_client.send_message(
                chat_id=chat_id, text=f"{username} {city_name} Нет такого города"
            )

    async def chose_your_team(self, upd: UpdateObj) -> None:
        keyboard = {
            "inline_keyboard": [
                [{"text": "Yes", "callback_data": "/yes"}, {"text": "No", "callback_data": "/no"}]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": True,
        }
        await self.words_game.create_game_session(
            user_id=upd.message.from_.id,
            chat_id=upd.message.chat.id,
            chat_type=upd.message.chat.type,
        )
        inline_message = await self.tg_client.send_keyboard(
            upd.message.chat.id, text=f"Будешь играть?", keyboard=keyboard
        )
        await asyncio.sleep(5)

        await self.tg_client.remove_inline_keyboard(
            chat_id=inline_message.result.chat.id, message_id=inline_message.result.message_id
        )

    async def add_to_team(self, upd: UpdateObj) -> None:
        game = await self.words_game.select_active_session_by_id(
            chat_id=upd.callback_query.message.chat.id
        )
        if game:
            await self.words_game.add_user_to_team(
                game_id=game.id,
                user_id=upd.callback_query.from_.id,
            )
            await self.tg_client.send_callback_alert(
                callback_id=upd.callback_query.id,
                text=f"{upd.callback_query.from_.username} теперь ты в игре",
            )

            await asyncio.sleep(delay=5)

            await self.pick_leader(game=game)

    async def pick_leader(self, game: GameSession, player: int = None):
        team = await self.words_game.get_team_by_game_id(game_session_id=game.id)

        if not team:
            await self.words_game.update_game_session(game_id=game.id, status=False)
            return await self.tg_client.send_message(
                chat_id=game.chat_id, text="Игорьков больше нет"
            )

        player = await self.words_game.select_user_by_id(choice(team) if not player else player)

        game.next_user_id = player.id
        await self.words_game.change_next_user_to_game_session(game_id=game.id, user_id=player.id)
        if game.next_start_letter:
            await self.tg_client.send_message(
                chat_id=game.chat_id,
                text=f"@{player.username} назови слово на букву {game.next_start_letter}",
                force_reply=True,
            )
        else:
            await self.tg_client.send_message(
                chat_id=game.chat_id, text=f"@{player.username} назови слово", force_reply=True
            )

    async def check_word(self, upd: UpdateObj) -> None:
        word = upd.message.text.strip("/")
        game = await self.words_game.select_active_session_by_id(chat_id=upd.message.chat.id)
        check = False
        if game.next_user_id != upd.message.from_.id:
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id,
                text=f"{upd.message.from_.first_name} Не твой ход минус жизнь",
            )
            await self.words_game.remove_life_from_player(
                game_id=game.id, player_id=upd.message.from_.id
            )
        elif game.next_start_letter and game.next_start_letter.lower() != word[0].lower():
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id,
                text=f"{upd.message.from_.username} "
                f"Надо слово на букву {game.next_start_letter}",
            )
        elif game.words and word in game.words:
            await self.tg_client.send_message(
                chat_id=upd.message.chat.id, text=f"Слово {word} уже было"
            )
        else:
            check = await self.yandex_dict.check_word_(text=word)

            if not check:
                await self.words_poll(word=word, game=game, upd=upd)
                return
        if not check:
            await self.words_game.remove_life_from_player(
                game_id=game.id, player_id=upd.message.from_.id
            )
            await self.pick_leader(game=game, player=upd.message.from_.id)
        else:
            await self.right_word(game=game, word=word)

    async def right_word(self, game: GameSession, word: str):
        await self.words_game.update_team(
            game_session_id=game.id, user_id=game.next_user_id, point=1, round_=1
        )
        await self.tg_client.send_message(chat_id=game.chat_id, text=f"{word} - правильно")
        last_letter = word[-1] if word[-1] not in "ьыъйё" else word[-2]
        if game.words:
            game.words.append(word)
        else:
            game.words = [
                word,
            ]
        await self.words_game.update_game_session(
            game_id=game.id, next_letter=last_letter, words=game.words
        )
        game.next_start_letter = last_letter
        await self.pick_leader(game=game)

    async def bot_looser(self, game_session_id: int) -> None:
        game = await self.words_game.update_game_session(game_id=game_session_id, status=False)
        await self.tg_client.send_message(
            chat_id=game.chat_id, text=f"Удивительно, я проиграл, опять слово на Ы"
        )

    async def words_poll(self, upd: UpdateObj, word: str, game: GameSession) -> None:
        poll = await self.tg_client.send_poll(
            chat_id=upd.message.chat.id,
            question=f"Граждане примем ли мы {word} как допустимое слово?",
            answers=["Yes", "No", "Слово?"],
            anonymous=False,
        )
        await self.words_game.update_game_session(game_id=game.id, poll_id=poll.result.poll.id)

        await asyncio.sleep(10)

        stop_poll = await self.tg_client.remove_inline_keyboard(
            chat_id=upd.message.chat.id, message_id=poll.result.message_id
        )

        fake_upd = SendMessageResponse.Schema().dump(stop_poll)

        fake_upd = UpdateObj.Schema().load(fake_upd.get("result"))
        await self.check_poll(fake_upd)

    async def check_poll(self, upd: UpdateObj) -> None:
        game = await self.words_game.get_game_session_by_poll_id(poll_id=upd.poll.id)
        if not game:
            return
        word = upd.poll.question.split()[4]
        answers = upd.poll.options
        yes = 0
        no = 0
        for ans in answers:
            match ans.text:
                case "Yes":
                    yes = ans.voter_count
                case "No":
                    no = ans.voter_count
        if yes > no:
            return await self.right_word(word=word, game=game)
        else:
            await self.tg_client.send_message(
                chat_id=game.chat_id, text=f"{word} - нет такого слова"
            )
            await self.pick_leader(game=game, player=game.next_user_id)
