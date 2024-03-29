import asyncio
import logging
from random import choice

import bson
from aio_pika.abc import AbstractIncomingMessage
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError
from constant import help_msg, faq_group, faq_solo
from app.store.tg_api.schemes import UpdateObj
from app.words_game.models import GameSession, GameSettings

from app.web.config import ConfigEnv
from app.store.words_game.accessor import WGAccessor
from app.store.database.database import Database
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.yandex_dict_api.accessor import YandexDictAccessor


class BaseMixin:
    def __init__(self, cfg: ConfigEnv, concurrent_workers: int = 1):
        self.cfg = cfg
        self._tasks = []
        self.concurrent_workers = concurrent_workers
        self.database = Database(cfg=self.cfg)
        self.words_game = WGAccessor(database=self.database)
        self.rabbitMQ = RabbitMQ(
            host=self.cfg.rabbitmq.host,
            port=self.cfg.rabbitmq.port,
            user=self.cfg.rabbitmq.user,
            password=self.cfg.rabbitmq.password,
        )
        self.yandex_dict = YandexDictAccessor(token=self.cfg.yandex_dict.token)
        self.logger = logging.getLogger("worker")
        self.routing_key_worker = "worker"
        self.routing_key_sender = "sender"
        self.routing_key_poller = "poller"
        self.queue_name = "tg_bot"
        self.game_settings: GameSettings | None = None

    async def statistics(self, upd: UpdateObj, game: GameSession | None = None) -> None:
        raise NotImplementedError


class CityGameMixin(BaseMixin):
    """
    Вариант игры в города для одного игрока
    Методы:
    start_game: Метод для запуска игры в города для одного игрока.
    stop_game: Метод для остановки игры в города для одного игрока.
    pick_city: Метод для выбора города игроком.
    check_city: Метод для проверки города игроком.
    bot_looser: Метод для обработки поражения бота в игре в города.
    """

    async def statistics(self, upd: UpdateObj, game: GameSession | None = None) -> None:
        pass

    async def start_game(self, upd: UpdateObj) -> None:
        """
        Метод start_game для запуска игры в города для одного игрока.

        :param upd:
        :return:
        """
        if await self.words_game.get_session_by_id(upd.message.from_.id):
            message_game_exist = {
                "type_": "message",
                "chat_id": upd.message.from_.id,
                "text": f"{upd.message.from_.username} игра уже в процессе",
            }

            await self.rabbitMQ.send_event(
                message=message_game_exist, routing_key=self.routing_key_sender
            )
            return

        user = await self.words_game.create_user(
            user_id=upd.message.from_.id, username=upd.message.from_.username
        )

        await self.words_game.create_game_session(
            user_id=user.id, chat_id=upd.message.chat.id, chat_type=upd.message.chat.type
        )

        message_game_start = {
            "type_": "message",
            "chat_id": upd.message.from_.id,
            "text": f"{upd.message.from_.username} let's play",
        }

        await self.rabbitMQ.send_event(
            message=message_game_start, routing_key=self.routing_key_sender
        )

        await self.pick_city(
            user_id=upd.message.from_.id,
            chat_id=upd.message.chat.id,
            username=upd.message.from_.username,
        )

    async def stop_game(self, upd: UpdateObj) -> None:
        """
        Метод stop_game для остановки игры в города для одного игрока.

        :param upd:
        :return:
        """
        if game := await self.words_game.get_session_by_id(chat_id=upd.message.chat.id):
            await self.words_game.update_game_session(game_id=game.id, status=False)
            await self.statistics(upd, game=game)

    async def pick_city(
        self, user_id: int, chat_id: int, username: str, letter: str | None = None
    ) -> None:
        """
        Метод pick_city для выбора города ботом.

        :param user_id: id игрока
        :param chat_id: id чата
        :param username: ник игрока
        :param letter: первая буква города
        :return:
        """
        self.logger.info(f"pick_city: {username} {letter}")
        game = await self.words_game.get_session_by_id(user_id)

        city = await self.words_game.get_city_by_first_letter(
            letter=letter, game_session_id=game.id
        )
        self.logger.info(f"city: {city}")
        if not city:
            return await self.bot_looser(game_session_id=game.id)

        first_letter = (
            city.name[-1] if city.name[-1] not in "ьыъйё" else city.name[-2]
        ).capitalize()

        await self.words_game.update_game_session(game_id=game.id, next_letter=first_letter)

        await self.words_game.set_city_to_used(city_id=city.id, game_session_id=game.id)

        message_city_start_letter = {
            "type_": "message",
            "chat_id": chat_id,
            "text": f"""{username} {city.name} \nТебе на {first_letter}""",
        }
        await self.rabbitMQ.send_event(
            message=message_city_start_letter, routing_key=self.routing_key_sender
        )

    async def check_city(self, upd: UpdateObj) -> None:
        """
        Метод check_city для проверки наличия города в игре и существование города.

        :param upd:
        :return:
        """
        if city := await self.words_game.get_city_by_name(upd.message.text.strip("/")):
            letter_num, letter = -1, None
            while abs(letter_num) < len(city.name):
                if city.name[letter_num] not in "ьыъйё":
                    letter = city.name[letter_num].capitalize()
                    break
                else:
                    letter_num -= 1

            game = await self.words_game.get_session_by_id(upd.message.from_.id)

            if await self.words_game.check_city_in_used(city_id=city.id, game_session_id=game.id):
                message_city_exist = {
                    "type_": "message",
                    "chat_id": upd.message.chat.id,
                    "text": f"{upd.message.from_.username} {city.name} уже есть",
                }

                await self.rabbitMQ.send_event(
                    message=message_city_exist, routing_key=self.routing_key_sender
                )
                return

            if game.next_start_letter == city.name[0]:
                await self.words_game.update_game_session(game_id=game.id, next_letter=letter)
                await self.words_game.set_city_to_used(city_id=city.id, game_session_id=game.id)

                message_right_city = {
                    "type_": "message",
                    "chat_id": upd.message.chat.id,
                    "text": f"{upd.message.from_.username} "
                    f"{city.name} Есть такой город. Мне на {letter}",
                }

                await self.rabbitMQ.send_event(
                    message=message_right_city, routing_key=self.routing_key_sender
                )

                await self.pick_city(
                    user_id=upd.message.from_.id,
                    chat_id=upd.message.chat.id,
                    username=upd.message.from_.username,
                    letter=letter,
                )

            else:
                message_wrong_start_letter = {
                    "type_": "message",
                    "chat_id": upd.message.chat.id,
                    "text": f"{upd.message.from_.username} "
                    f"{city.name} на {city.name[0]}, а тебе на {game.next_start_letter}",
                }

                await self.rabbitMQ.send_event(
                    message=message_wrong_start_letter, routing_key=self.routing_key_sender
                )

        else:
            message_city_not_found = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": f"{upd.message.from_.username} {upd.message.text} Нет такого города",
            }

            await self.rabbitMQ.send_event(
                message=message_city_not_found, routing_key=self.routing_key_sender
            )

    async def bot_looser(self, game_session_id: int) -> None:
        """
        Метод поражения бота и завершения игры

        :param game_session_id: id игры
        :return:
        """
        game = await self.words_game.update_game_session(game_id=game_session_id, status=False)
        message_loose = {"type_": "message", "chat_id": game.chat_id, "text": "Увы, я проиграл"}
        await self.rabbitMQ.send_event(message=message_loose, routing_key=self.routing_key_sender)


class WordGameMixin(BaseMixin):
    """
    Вариант игры в слова для команды
    Методы:
    chose_your_team: Метод для выбора команды игроком.
    add_to_team: Метод для добавления игрока в команду.
    pick_leader: Метод для выбора лидера команды.
    check_word: Метод для проверки слова игроком.
    right_word: Метод для обработки правильного слова в игре в города.
    words_poll: Метод для обработки голосования за слово в игре в города.
    stop_game_group: Метод для остановки игры в города для группы игроков.
    """

    async def statistics(self, upd: UpdateObj, game: GameSession | None = None) -> None:
        pass

    async def chose_your_team(self, upd: UpdateObj) -> None:
        """
        Метод формирования игры в слова для команды и самой команды

        :param upd:
        :return:
        """
        if await self.words_game.get_session_by_id(chat_id=upd.message.chat.id):
            return
        async with asyncio.Lock():
            await self.words_game.create_game_session(
                user_id=upd.message.from_.id,
                chat_id=upd.message.chat.id,
                chat_type=upd.message.chat.type,
                response_time=self.game_settings.response_time,
                anonymous_poll=self.game_settings.anonymous_poll,
                poll_time=self.game_settings.poll_time,
                life=self.game_settings.life,
            )


        message_create_team = {
            "type_": "message_keyboard",
            "chat_id": upd.message.chat.id,
            "text": "Будешь играть в игру?",
            "keyboard": "keyboard_team",
            "live_time": 5,
        }

        await self.rabbitMQ.send_event(
            message=message_create_team, routing_key=self.routing_key_sender
        )

    async def add_to_team(self, upd: UpdateObj) -> None:
        """
        Метод добавления игрока в игру

        :param upd:
        :return:
        """
        game = await self.words_game.get_session_by_id(chat_id=upd.callback_query.message.chat.id)
        player = await self.words_game.create_user(user_id=upd.callback_query.from_.id,
                                                   username=upd.callback_query.from_.username)

        if game:
            await self.words_game.add_user_to_team(
                game_id=game.id,
                user_id=upd.callback_query.from_.id,
                life=game.life,
            )
            message_add_to_team = {
                "type_": "callback_alert",
                "text": f"{upd.callback_query.from_.username} теперь ты в игре",
                "callback_id": upd.callback_query.id,
            }

            await self.rabbitMQ.send_event(
                message=message_add_to_team, routing_key=self.routing_key_sender
            )

    async def pick_leader(self, game: GameSession, player_id: int = None):
        """
        Метод выбора игрока для ответа
        (для исключения подстав среди игроков в
        каждом раунде игрок выбирается случайно из еще не игравших в раунде)

        :param game: игра
        :param player_id: игрок ID
        :return:
        """
        if game is None:
            return
        team = await self.words_game.get_team_by_game_id(
            game_session_id=game.id, player_id=game.next_user_id
        )
        if len(team) == 0:
            await self.stop_game_group(game=game)
            return
        if len(team) == 1:
            """
            Если остался 1 игрок с 1 жизнью, то игра окончена
            """
            player_id = team[0]
            player_life = await self.words_game.get_player(
                player_id=player_id, game_session_id=game.id
            )
            if player_life == 1:
                await self.stop_game_group(game=game)
                return

        player_id = await self.words_game.select_user_by_id(
            choice(team) if not player_id else player_id
        )

        game.next_user_id = player_id.id

        await self.words_game.change_next_user_to_game_session(
            game_id=game.id, user_id=player_id.id
        )

        text = (
            f"@{player_id.username} назови слово на букву {game.next_start_letter}"
            if game.next_start_letter
            else f"@{player_id.username} назови слово"
        )

        message_say_word = {
            "type_": "message",
            "chat_id": game.chat_id,
            "text": text,
            "force_reply": True,
        }
        await self.rabbitMQ.send_event(
            message=message_say_word, routing_key=self.routing_key_sender
        )
        player_id = await self.words_game.get_player(
            player_id=player_id.id, game_session_id=game.id
        )
        message_slow_player = {
            "type_": "slow_player",
            "chat_id": game.chat_id,
            "user_id": player_id.player_id,
            "round": player_id.round_,
            "game_id": game.id,
        }

        await self.rabbitMQ.send_event(
            message=message_slow_player,
            routing_key=self.routing_key_worker,
            delay=game.response_time * 1000 if game.response_time else 15000,
        )

    async def check_word(self, upd: UpdateObj) -> None:
        """
        Метод проверки слова на существование в словаре или вызове голосования

        :param upd:
        :return:
        """
        word = upd.message.text.strip("/").capitalize()
        game = await self.words_game.get_session_by_id(chat_id=upd.message.chat.id)
        check = False
        if game.next_user_id != upd.message.from_.id:
            """
            Удаление жизни игрока в случае несовпадения id игрока и id текущего игрока
            """
            message_wrong_user = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": f"{upd.message.from_.first_name} " f"Не твой ход минус жизнь",
            }
            await self.rabbitMQ.send_event(
                message=message_wrong_user, routing_key=self.routing_key_sender
            )

            await self.words_game.remove_life_from_player(
                game_id=game.id, player_id=upd.message.from_.id
            )
        elif game.next_start_letter and game.next_start_letter.lower() != word[0].lower():
            """
            Слово не начинается с буквы с которой закончилось прошлое
            """
            message_wrong_start_letter = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": f"{upd.message.from_.username} "
                f"Надо слово на букву {game.next_start_letter}",
            }
            await self.rabbitMQ.send_event(
                message=message_wrong_start_letter, routing_key=self.routing_key_sender
            )
            return await self.pick_leader(game=game)
        elif word in await self.words_game.get_list_words_by_game_id(game_session_id=game.id):
            """
            Слово уже было
            """
            message_already_word = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": f"{upd.message.from_.username} " f"Слово {word} уже было",
            }
            await self.rabbitMQ.send_event(
                message=message_already_word, routing_key=self.routing_key_sender
            )
            return await self.pick_leader(game=game)
        else:
            """
            Проверка слова в словаре
            """
            check = await self.yandex_dict.check_word_(text=word)

            if not check:
                """
                Проверка слова в словаре не удалась, голосование
                """
                await self.words_poll(word=word, game=game, upd=upd)
                return
        if not check:
            """
            Проверка слова в словаре не удалась, голосование не удалось
            """
            await self.words_game.remove_life_from_player(
                game_id=game.id, player_id=upd.message.from_.id, round_=1
            )
            message_no_word = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": f"{upd.message.from_.username} " f"Нет такого слова",
            }

            await self.rabbitMQ.send_event(
                message=message_no_word, routing_key=self.routing_key_sender
            )

            await self.pick_leader(game=game)
        else:
            await self.right_word(game=game, word=word)

    async def right_word(self, game: GameSession, word: str):
        """
        Подтверждение правильного слова и выбор новой первой буквы

        :param game: игра
        :param word: слово
        :return:
        """
        await self.words_game.update_team(
            game_session_id=game.id, user_id=game.next_user_id, point=1, round_=1
        )

        letter_num, last_letter = -1, None
        while abs(letter_num) < len(word):
            if word[letter_num] not in "ьыъйё":
                last_letter = word[letter_num].capitalize()
                break
            else:
                letter_num -= 1

        message_right_word = {
            "type_": "message",
            "chat_id": game.chat_id,
            "text": f"{word} - правильно",
        }
        await self.rabbitMQ.send_event(
            message=message_right_word, routing_key=self.routing_key_sender
        )

        await self.words_game.add_used_word(game_session_id=game.id, word=word)

        await self.words_game.update_game_session(game_id=game.id, next_letter=last_letter)

        game.next_start_letter = last_letter

        await self.pick_leader(game=game)

    async def words_poll(self, upd: UpdateObj, word: str, game: GameSession) -> None:
        """
        Метод отправки голосования

        :param upd:
        :param word: слово
        :param game: игра
        :return:
        """
        poll_message = {
            "type_": "send_poll",
            "chat_id": upd.message.chat.id,
            "question": f"Граждане примем ли мы {word} как допустимое слово?",
            "options": ["Yes", "No", "Слово?"],
            "anonymous": game.anonymous_poll if game.anonymous_poll else False,
            "game_id": game.id,
            "period": game.poll_time if game.poll_time else 10,
        }

        await self.rabbitMQ.send_event(message=poll_message, routing_key=self.routing_key_sender)

    async def stop_game_group(
        self, upd: UpdateObj | None = None, game: GameSession | None = None
    ) -> None:
        """
        Метод остановки игры

        :param upd: обновление сообщения
        :param game: игра
        :return:
        """
        if not upd and not game:
            return
        if not game:
            game = await self.words_game.get_session_by_id(chat_id=upd.message.chat.id)
        if not game:
            return
        await self.words_game.update_game_session(game_id=game.id, status=False)
        await self.words_game.update_total_points_to_user(game_id=game.id)
        await self.statistics(upd=upd, game=game)


class Worker(CityGameMixin, WordGameMixin):
    """
    Класс Worker для обработки логики игры и связи с внешними сервисами.

    cfg: Объект конфигурации.
    concurrent_workers: Количество одновременных рабочих процессов.
    _tasks: Список задач для выполнения одновременно.
    database: Объект базы данных для взаимодействия с базой данных игры.
    words_game: Объект-аксессор для взаимодействия с сервисом Words Game.
    rabbitMQ: Объект RabbitMQ для связи с другими сервисами.
    yandex_dict: Объект-аксессор для взаимодействия с API Яндекс.Словаря.
    logger: Объект логгера для записи событий.
    routing_key_worker: Ключ маршрутизации для сообщений рабочего процесса.
    routing_key_sender: Ключ маршрутизации для сообщений отправителя.
    routing_key_poller: Ключ маршрутизации для сообщений опросника.
    queue_name: Название очереди для прослушивания.
    game_settings: Объект настроек игры.

    Список методов для класса Worker:

    setup_settings: Метод для настройки настроек игры.
    handle_update: Метод для обработки входящих сообщений Telegram.
    handle_callback: Метод для обработки входящих callback от Telegram.
    handle_poll_answer: Метод для обработки ответа на опрос от Telegram
    on_message: Метод для обработки входящих сообщений от Telegram.
    start: Метод для запуска рабочих процессов и подключения к базе данных и RabbitMQ.
    stop: Метод для остановки рабочих процессов и отключения от RabbitMQ и базы данных.
    statistics: Метод для получения статистики игры.

    """

    async def setup_settings(self):
        """
        Инициализация настроек игры.
        :return:
        """
        self.game_settings = await GameSettings.get_instance(self.database.session)

    async def _worker_rabbit(self):
        """
        Метод для прослушивания событий RabbitMQ.
        :return:
        """
        await self.rabbitMQ.listen_events(
            on_message_func=self.on_message,
            routing_key=[self.routing_key_worker, self.routing_key_poller],
            queue_name=self.queue_name,
        )

    async def on_message(self, message: AbstractIncomingMessage):
        """
        Обработка сообщений из очереди RabbitMQ.

        :param message:
        :return:
        """
        if message.routing_key == "poller":
            try:
                upd: UpdateObj = UpdateObj.Schema().load(bson.loads(message.body))
            except ValidationError as e:
                self.logger.info(f"validation {e}")
                return
            if upd.message:
                await self.handle_message(upd)
            elif upd.callback_query:
                await self.handle_callback_query(upd)
            elif upd.poll_answer:
                await self.handle_poll_answer(upd)
        elif message.routing_key == self.routing_key_worker:
            text = bson.loads(message.body)
            match text["type_"]:
                case "pick_leader":
                    game = await self.words_game.get_session_by_id(chat_id=text["chat_id"])
                    await self.pick_leader(game=game)
                case "poll_result":
                    game = await self.words_game.get_session_by_id(chat_id=text["chat_id"])
                    if game:
                        result = None
                        if not text["poll_type"]:
                            result = await self.words_game.check_not_anonim_poll(
                                game_session_id=game.id
                            )
                        await self.words_game.update_game_session(game_id=game.id, poll_id=None)
                        if text["poll_result"] == "yes" or result:
                            await self.right_word(game=game, word=text["word"])
                        else:
                            await self.pick_leader(game=game)
                case "slow_player":
                    game = await self.words_game.get_session_by_id(chat_id=text["chat_id"])
                    if game is None:
                        return await message.ack()
                    player = await self.words_game.get_player(
                        game_session_id=game.id, player_id=text["user_id"]
                    )
                    if player is None:
                        return await message.ack()
                    if (
                        game.current_poll_id is None
                        and game.next_user_id == text["user_id"]
                        and player.round_ == text["round"]
                    ):
                        await self.words_game.remove_life_from_player(
                            game_id=game.id, player_id=text["user_id"], round_=1
                        )
                        await self.pick_leader(game=game)
                case "poll_id":
                    game = await self.words_game.get_session_by_id(chat_id=text["chat_id"])
                    if game:
                        await self.words_game.update_game_session(
                            game_id=game.id, poll_id=text["poll_id"]
                        )
                case _:
                    self.logger.info(f"unknown type {text['type_']}")
        await message.ack()

    async def handle_message(self, upd: UpdateObj):
        """
        Обработка сообщений.

        :param upd: Объект обновления.
        :return:
        """

        async def handle_ping(self, upd: UpdateObj):
            """Обработка команды /ping.

            :param self: Экземпляр класса.
            :param upd: Объект обновления.
            :return:
            """

            message_ping = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": "/pong",
            }

            await self.rabbitMQ.send_event(
                message=message_ping, routing_key=self.routing_key_sender
            )

        async def handle_help(self, upd: UpdateObj):
            """Обработка команды /help.

            :param self: Экземпляр класса.
            :param upd: Объект обновления.
            :return:
            """

            message_help = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": help_msg,
            }
            await self.rabbitMQ.send_event(
                message=message_help, routing_key=self.routing_key_sender
            )

        async def handle_last(self, upd: UpdateObj):
            """Обработка команды /last.

            :param self: Экземпляр класса.
            :param upd: Объект обновления.
            :return:
            """

            game = await self.words_game.get_session_by_id(chat_id=upd.message.chat.id)
            if game is None:
                message_last_letter = {
                    "type_": "message",
                    "chat_id": upd.message.chat.id,
                    "text": "Игра не начата",
                }
            else:
                if upd.message.chat.type != "private":
                    thing = "Слово"
                else:
                    thing = "Город"
                message_last_letter = {
                    "type_": "message",
                    "chat_id": upd.message.chat.id,
                    "text": f"{thing} на букву {game.next_start_letter}",
                }

            await self.rabbitMQ.send_event(
                message=message_last_letter, routing_key=self.routing_key_sender
            )

        async def handle_faq(self, upd: UpdateObj):
            """Обработка команды /faq.
            :param self: Экземпляр класса.
            :param upd: Объект обновления.
            :return:
            """
            if upd.message.chat.type != "private":
                await self.rabbitMQ.send_event(
                    message={
                        "type_": "message",
                        "chat_id": upd.message.chat.id,
                        "text": faq_group.format(response=self.game_settings.response_time, life=3),
                    },
                    routing_key=self.routing_key_sender,
                )
            else:
                await self.rabbitMQ.send_event(
                    message={"type_": "message", "chat_id": upd.message.chat.id, "text": faq_solo},
                    routing_key=self.routing_key_sender,
                )

        try:
            match upd.message.text.split("@")[0]:
                case "/play" if upd.message.chat.type == "private":
                    await self.start_game(upd=upd)
                case "/play" if upd.message.chat.type != "private":
                    await self.chose_your_team(upd)
                case "/stop" if upd.message.chat.type == "private":
                    await self.stop_game(upd=upd)
                case "/stop":
                    await self.stop_game_group(upd=upd)
                case "/ping":
                    await handle_ping(self, upd)
                case "/help" if upd.message.chat.type != "private":
                    await handle_help(self, upd)
                case "/last" if upd.message.chat.type == "private":
                    await handle_last(self, upd)

                case "/stat":
                    await self.statistics(upd=upd)
                case "/faq":
                    await handle_faq(self, upd=upd)
                case _ if upd.message.chat.type != "private" and await self.words_game.get_session_by_id(
                    chat_id=upd.message.chat.id
                ):
                    await self.check_word(upd=upd)
                case _ if await self.words_game.get_session_by_id(chat_id=upd.message.from_.id):
                    await self.check_city(upd=upd)
        except IntegrityError as e:
            self.logger.info(f"message {e}")

    async def handle_callback_query(self, upd: UpdateObj):
        """
        Обработка callback-запросов.

        :param upd: Объект обновления.
        :return:
        """
        try:
            match upd.callback_query.data:
                case "/yes":
                    await self.add_to_team(upd)
                case _:
                    pass
        except IntegrityError as e:
            self.logger.info(f"callback {e}")

    async def start(self):
        """
        Метод start для запуска рабочих процессов и подключения к базе данных и RabbitMQ.
        """
        await self.database.connect()
        await self.rabbitMQ.connect()
        await self.setup_settings()
        self._tasks = [
            asyncio.create_task(self._worker_rabbit()) for _ in range(self.concurrent_workers)
        ]

    async def stop(self):
        """
        Метод stop для остановки рабочих процессов и отключения от базы данных и RabbitMQ.
        """
        for t in self._tasks:
            t.cancel()
        await self.rabbitMQ.disconnect()
        await self.database.disconnect()

    async def statistics(self, upd, game: GameSession | None = None):
        """
        Метод для вывода статистики игры.

        :param upd: Объект обновления.
        :param game: Объект игры.
        :return:
        """
        if game is None:
            game = await self.words_game.get_session_by_id(
                chat_id=upd.message.chat.id, is_active=True
            )
        if game is None:
            game = await self.words_game.get_session_by_id(
                chat_id=upd.message.chat.id, is_active=False
            )
        if game is None:
            messages_statistics = {
                "type_": "message",
                "chat_id": upd.message.chat.id,
                "text": "Игр нет",
            }
            await self.rabbitMQ.send_event(
                message=messages_statistics, routing_key=self.routing_key_sender
            )
            return
        if game.game_type == "private":
            cities = await self.words_game.get_city_list_by_session_id(game_session_id=game.id)

            messages_played_city = {
                "type_": "message",
                "chat_id": game.chat_id,
                "text": f"В этой игре участвовали: {' - '.join(city.name for city in cities)}",
            }

            await self.rabbitMQ.send_event(
                message=messages_played_city, routing_key=self.routing_key_sender
            )
        elif game.game_type != "private":
            team_lst = await self.words_game.get_player_list(game_session_id=game.id)

            message_no_team = {
                "type_": "message",
                "chat_id": game.chat_id,
                "text": f"Игра окончена. "
                f"Данные игры:\nВремя на ответ - {game.response_time}. \n"
                f"Вид опроса - {['Не анонимный', 'Анонимный'][game.anonymous_poll]}. \n"
                f"Время на опроса - {game.poll_time}. \n"
                f"Статистика игроков: {' - '.join(f'@{player[0]} - {player[1]}' for player in team_lst)}",
            }
            await self.rabbitMQ.send_event(
                message=message_no_team, routing_key=self.routing_key_sender
            )

    async def handle_poll_answer(self, upd: UpdateObj):
        """
        Обработка ответа на опрос.
        :param upd: Объект обновления.
        :return:
        """
        poll_id = upd.poll_answer.poll_id
        player_id = upd.poll_answer.user.id
        game = await self.words_game.get_game_session_by_poll_id(poll_id=poll_id)
        if game:
            if upd.poll_answer.option_ids:
                answer = {0: True, 1: False}.get(upd.poll_answer.option_ids[0], None)
            else:
                answer = None

            await self.words_game.set_player_poll_answer(
                player_id=player_id, game_session_id=game.id, answer=answer
            )
