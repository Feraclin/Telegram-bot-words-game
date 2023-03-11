import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select, insert, update, func, delete
from sqlalchemy.dialects.postgresql import insert as psg_insert
from sqlalchemy.exc import IntegrityError

from app.words_game.models import (
    GameSession,
    User,
    City,
    UsedCity,
    UserGameSession,
    Words,
    WordsInGame,
    GameSettings,
)
from random import choice, randint

if TYPE_CHECKING:
    from app.store import Database


@dataclass
class WGAccessor:
    """
    Класс для работы с базой данных игры "Города" и "Слова".
    Методы класса WGAccessor:

    select_active_session_by_id - получение активной игровой сессии по id пользователя или id чата.
    create_game_session - создание игровой сессии.
    update_game_session - обновление игровой сессии.
    delete_game_session - удаление игровой сессии.
    change_next_user_to_game_session - изменение следующего пользователя в игровой сессии.
    create_user - создание пользователя с указанным id и именем.
    select_user_by_id - получение пользователя по id.
    update_user - обновление пользователя с указанным id, добавление указанного количества очков.
    get_city_by_first_letter - получение города по первой букве.
        Если не указана буква, выбирается случайная.
        Если не указано количество городов, выбирается все города, начинающиеся на указанную букву.
    get_city_by_name - получение города по имени.
    check_city_in_used - проверка использовался ли город в игре.
    set_city_to_used - установка города как использованный в игре.
    get_city_list_by_session_id - получение списка городов, которые использовались в игре.
    add_user_to_team - добавление игрока в команду.
    update_team - обновление игрока в команде с указанным id, добавление указанного количества очков и раундов.
    get_team_by_game_id - получение списка игроков, которые использовались в игре.
    remove_life_from_player - удаление жизни игрока.
    get_game_session_by_poll_id - получение игрока в игре по id команды.
    get_list_words_by_game_id - получение списка слов в игре.
    add_word - добавление слова.
    get_word_by_word - получение слова по слову.
    add_used_word - добавление слова в использованное в игре.
    get_player_list - получение списка игроков в игре.
    get_game_settings - получение настроек игры.

    """

    database: "Database"
    logger: logging.Logger = logging.getLogger("words_game")

    async def get_session_by_id(
        self, user_id: int | None = None, chat_id: int | None = None, is_active: bool = True
    ) -> GameSession | None:
        """
        Получение активной игровой сессии по id пользователя или id чата.

        :param user_id: id пользователя
        :param chat_id: id чата
        :param is_active: статус игровой сессии
        :return: активная игровая сессия
        """
        if user_id:
            query = select(GameSession).where(
                GameSession.creator_id == user_id, GameSession.is_active == is_active
            )
        elif chat_id:
            query = select(GameSession).where(
                GameSession.chat_id == chat_id, GameSession.is_active == is_active
            )
        else:
            return None
        res = await self.database.execute_query(query)
        res = res.scalars().all()
        return res[-1] if res else None

    async def create_game_session(self, user_id: int, chat_id: int, chat_type: str) -> GameSession:
        """
        Создание игровой сессии.

        :param user_id: id создателя сессии
        :param chat_id: id чата
        :param chat_type: тип чата
        :return: созданная игровая сессия
        """
        query = insert(GameSession).values(
            creator_id=user_id, chat_id=chat_id, game_type=chat_type, is_active=True
        )
        res = await self.database.execute_query(query)
        return res.scalar()

    async def update_game_session(
        self,
        game_id: int,
        status: bool = True,
        next_letter: str | None = None,
        words: list[str] | None = None,
        poll_id: int | None = None,
        next_user_id: int | None = None,
    ) -> GameSession | None:
        """
        Обновление игровой сессии.

        :param game_id: id игровой сессии
        :param status: статус игровой сессии
        :param next_letter: следующая буква
        :param words: список использованных слов
        :param poll_id: id опроса
        :param next_user_id: id следующего пользователя
        :return: обновленная игровая сессия
        """
        query = (
            update(GameSession)
            .where(GameSession.id == game_id)
            .values(
                is_active=status,
                next_start_letter=next_letter if next_letter else GameSession.next_start_letter,
                words=words if words else GameSession.words,
                current_poll_id=poll_id if poll_id else GameSession.current_poll_id,
                next_user_id=next_user_id if next_user_id else GameSession.next_user_id,
            )
            .returning(GameSession)
        )
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def delete_game_session(self, chat_id: int) -> None:
        """
        Удаление игровой сессии.

        :param chat_id: id чата
        """
        query = delete(GameSession).where(GameSession.chat_id == chat_id)

        res = await self.database.execute_query(query)
        return res.scalar()

    async def change_next_user_to_game_session(
        self, game_id: int, user_id: int
    ) -> GameSession | None:
        """
        Изменение следующего пользователя в игровой сессии.

        :param game_id: id игровой сессии
        :param user_id: id пользователя
        :return: обновленная игровая сессия
        """
        query = (
            update(GameSession)
            .where(GameSession.id == game_id, GameSession.is_active == True)
            .values(next_user_id=user_id)
            .returning(GameSession)
        )

        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_user(self, user_id: int, username: str) -> User | None:
        """
        Создание пользователя.

        :param user_id: id пользователя
        :param username: имя пользователя
        :return: созданный пользователь
        """
        query = psg_insert(User).values(id=user_id, username=username).returning(User)
        query = query.on_conflict_do_nothing()
        res = (await self.database.execute_query(query)).scalar()
        if res:
            return res
        else:
            return await self.select_user_by_id(user_id)

    async def select_user_by_id(self, user_id: int) -> User | None:
        """
        Получение пользователя по id.

        :param user_id: id пользователя
        :return: пользователь
        """
        query = select(User).where(User.id == user_id)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def update_user(self, user_id: int, point) -> User | None:
        """
        Обновление пользователя.

        :param user_id: id пользователя
        :param point: количество очков
        :return: обновленный пользователь
        """
        query = update(User).where(User.id == user_id).values(total_point=User.total_point + point)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_city_by_first_letter(
        self, game_session_id: int, letter: str | None = None, city_count: int | None = None
    ) -> City | None:
        """
        Получение города по первой букве.

        :param game_session_id: id игровой сессии
        :param letter: первая буква
        :param city_count: количество городов
        :return: город
        """
        if not letter:
            letter = choice(list("АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ"))
        query = select(func.count(City.id)).where(City.name.like(f"{letter}%"))
        city_count = (
            city_count if city_count else (await self.database.execute_query(query)).scalar()
        )
        query = (
            select(City).where(City.name.like(f"{letter}%")).offset(randint(0, city_count)).limit(1)
        )
        res = await self.database.execute_query(query)
        city = res.scalar_one_or_none()
        if not city:
            return city
        elif await self.check_city_in_used(city.id, game_session_id):
            return await self.get_city_by_first_letter(
                game_session_id=game_session_id, letter=letter, city_count=city_count
            )
        else:
            return city

    async def get_city_by_name(self, name: str) -> City | None:
        """
        Получение города по имени.

        :param name: имя города
        :return: город
        """
        query = select(City).where(City.name == name)
        res = await self.database.execute_query(query)
        city = res.scalar()
        return city

    async def check_city_in_used(self, city_id: int, game_session_id: int) -> bool:
        """
        Проверка использовался ли город в игре.

        :param city_id: id города
        :param game_session_id: id игровой сессии
        :return: True, если город использовался, иначе False
        """
        query = select(UsedCity).where(
            UsedCity.city_id == city_id, UsedCity.game_session_id == game_session_id
        )
        res = await self.database.execute_query(query)
        double_city = res.scalar_one_or_none()

        return True if double_city else False

    async def set_city_to_used(self, city_id: int, game_session_id: int) -> None:
        """
        Установка города как использованный в игре.

        :param city_id: id города
        :param game_session_id: id игровой сессии
        """
        query = insert(UsedCity).values(city_id=city_id, game_session_id=game_session_id)
        await self.database.execute_query(query)
        return

    async def get_city_list_by_session_id(self, game_session_id: int) -> list[City]:
        """
        Получение списка городов, которые использовались в игре.

        :param game_session_id: id игровой сессии
        :return: список городов
        """
        query = select(UsedCity).where(UsedCity.game_session_id == game_session_id)

        res = await self.database.execute_query(query)
        cities = res.scalars().all()
        return [city.city for city in cities]

    async def add_user_to_team(self, user_id: int, game_id: int) -> None:
        """
        Добавление игрока в команду.

        :param user_id:
        :param game_id:
        :return:
        """
        query = psg_insert(UserGameSession).values(player_id=user_id, game_sessions_id=game_id)
        query = query.on_conflict_do_nothing()
        await self.database.execute_query(query)
        return

    async def update_team(
        self, game_session_id: int, user_id: int, point: int = 0, round_: int = 0
    ) -> None:
        """
        Обновление Игрока в команде.

        :param game_session_id:
        :param user_id:
        :param point:
        :param round_:
        :return:
        """
        query = (
            update(UserGameSession)
            .where(
                UserGameSession.game_sessions_id == game_session_id,
                UserGameSession.player_id == user_id,
            )
            .values(
                point=UserGameSession.point + point,
                round_=UserGameSession.round_ + round_,
            )
        )
        await self.database.execute_query(query)

    async def get_team_by_game_id(self, game_session_id: int) -> list[int]:
        """
        Получение списка игроков, которые использовались в игре.

        :param game_session_id: id игровой сессии
        :return: список игроков
        """
        query = (
            select(UserGameSession.player_id, func.min(UserGameSession.round_))
            .where(
                UserGameSession.game_sessions_id == game_session_id,
                UserGameSession.life > 0,
            )
            .group_by(UserGameSession.player_id)
        )

        res = await self.database.execute_query(query)
        team_lst = res.scalars().all()
        return team_lst

    async def remove_life_from_player(self, game_id: int, player_id: int, round_: int = 0) -> None:
        """
        Удаление жизни игрока.

        :param game_id:
        :param player_id:
        :param round_:
        :return:
        """
        query = (
            update(UserGameSession)
            .where(
                UserGameSession.game_sessions_id == game_id, UserGameSession.player_id == player_id
            )
            .values(life=UserGameSession.life - 1, round_=UserGameSession.round_ + round_)
        )
        await self.database.execute_query(query)

    async def get_game_session_by_poll_id(self, poll_id: int) -> GameSession | None:
        """
        Получение игрока в игре по id команды.

        :param poll_id: id команды
        :return: игрока
        """
        query = select(GameSession).where(GameSession.current_poll_id == poll_id)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_list_words_by_game_id(self, game_session_id: int) -> list[str]:
        """
        Получение списка слов в игре.

        :param game_session_id: id игровой сессии
        :return: список слов
        """
        query = select(WordsInGame).where(WordsInGame.game_session_id == game_session_id)
        res = await self.database.execute_query(query)
        words_lst = res.scalars().all()
        return [word.word.word for word in words_lst]

    async def add_word(self, word: str) -> None:
        """
        Добавление слова.

        :param word:
        :return:
        """
        query = psg_insert(Words).values(word=word.capitalize()).returning(Words)
        query.on_conflict_do_nothing()
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_word_by_word(self, word: str) -> Words | None:
        """
        Получение слова по слову.

        :param word:
        :return: слова
        """
        query = select(Words).where(Words.word == word.capitalize())
        res = await self.database.execute_query(query)
        return res.scalar()

    async def add_used_word(self, game_session_id: int, word: str) -> None:
        """
        Добавление слова в использованное в игре.

        :param game_session_id: id игровой сессии
        :param word: слово
        :return:
        """
        try:
            word_id = await self.add_word(word)
        except IntegrityError:
            self.logger.error("Word already used")
            word_id = None
        if word_id is None:
            word_id = await self.get_word_by_word(word)
        query = insert(WordsInGame).values(word_id=word_id.id, game_session_id=game_session_id)
        await self.database.execute_query(query)

    async def get_player_list(self, game_session_id: int) -> list:
        """
        Получение списка игроков в игре.

        :param game_session_id: id игровой сессии
        :return: список игроков
        """
        query = select(UserGameSession).where(UserGameSession.game_sessions_id == game_session_id)
        res = await self.database.execute_query(query)
        players = [(player.player.username, player.point) for player in res.scalars().all()]
        return players

    async def get_game_settings(self):
        """
        Получение настроек игры.

        :return: настроек игры
        """
        query = select(GameSettings)
        res = await self.database.execute_query(query)
        return res.scalar_one()

    async def get_player_life(self, player_id: int, game_session_id: int) -> int:
        """
        Получение жизни игрока.

        :param player_id: id игрока
        :param game_session_id: id игровой сессии
        """
        query = select(UserGameSession.life).where(
            UserGameSession.player_id == player_id,
            UserGameSession.game_sessions_id == game_session_id,
        )
        res = await self.database.execute_query(query)
        return res.scalar()
