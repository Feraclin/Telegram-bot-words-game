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
    database: "Database"
    logger: logging.Logger = logging.getLogger("words_game")

    async def select_active_session_by_id(
        self, user_id: int | None = None, chat_id: int | None = None
    ) -> GameSession | None:
        if user_id:
            query = select(GameSession).where(
                GameSession.creator_id == user_id, GameSession.is_active == True
            )
        elif chat_id:
            query = select(GameSession).where(
                GameSession.chat_id == chat_id, GameSession.is_active == True
            )
        else:
            return None
        res = await self.database.execute_query(query)
        return res.scalar()

    async def create_game_session(self, user_id: int, chat_id: int, chat_type: str) -> GameSession:
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
        query = delete(GameSession).where(GameSession.chat_id == chat_id)

        res = await self.database.execute_query(query)
        return res.scalar()

    async def change_next_user_to_game_session(
        self, game_id: int, user_id: int
    ) -> GameSession | None:
        query = (
            update(GameSession)
            .where(GameSession.id == game_id, GameSession.is_active == True)
            .values(next_user_id=user_id)
            .returning(GameSession)
        )

        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_user(self, user_id: int, username: str) -> User | None:
        query = psg_insert(User).values(id=user_id, username=username).returning(User)
        query = query.on_conflict_do_nothing()
        res = (await self.database.execute_query(query)).scalar()
        if res:
            return res
        else:
            return await self.select_user_by_id(user_id)

    async def select_user_by_id(self, user_id: int) -> User | None:
        query = select(User).where(User.id == user_id)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def update_user(self, user_id: int, point) -> User | None:
        query = update(User).where(User.id == user_id).values(total_point=User.total_point + point)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_city_by_first_letter(
        self, game_session_id: int, letter: str | None = None, city_count: int | None = None
    ) -> City | None:
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
        query = select(City).where(City.name == name)
        res = await self.database.execute_query(query)
        city = res.scalar()
        return city

    async def check_city_in_used(self, city_id: int, game_session_id: int) -> bool:
        query = select(UsedCity).where(
            UsedCity.city_id == city_id, UsedCity.game_session_id == game_session_id
        )
        res = await self.database.execute_query(query)
        double_city = res.scalar_one_or_none()

        return True if double_city else False

    async def set_city_to_used(self, city_id: int, game_session_id: int) -> None:
        query = insert(UsedCity).values(city_id=city_id, game_session_id=game_session_id)
        await self.database.execute_query(query)
        return

    async def get_city_list_by_session_id(self, game_session_id: int) -> list[City]:
        query = select(UsedCity).where(UsedCity.game_session_id == game_session_id)

        res = await self.database.execute_query(query)
        cities = res.scalars().all()
        return [city.city for city in cities]

    async def add_user_to_team(self, user_id: int, game_id: int) -> None:
        query = psg_insert(UserGameSession).values(player_id=user_id, game_sessions_id=game_id)
        query = query.on_conflict_do_nothing()
        await self.database.execute_query(query)
        return

    async def update_team(
        self, game_session_id: int, user_id: int, point: int = 0, round_: int = 0
    ) -> None:
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
        query = (
            update(UserGameSession)
            .where(
                UserGameSession.game_sessions_id == game_id, UserGameSession.player_id == player_id
            )
            .values(life=UserGameSession.life - 1, round_=UserGameSession.round_ + round_)
        )
        await self.database.execute_query(query)

    async def get_game_session_by_poll_id(self, poll_id: int) -> GameSession | None:
        query = select(GameSession).where(GameSession.current_poll_id == poll_id)
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_list_words_by_game_id(self, game_session_id: int) -> list[str]:
        query = select(WordsInGame).where(WordsInGame.game_session_id == game_session_id)
        res = await self.database.execute_query(query)
        words_lst = res.scalars().all()
        return [word.word.word for word in words_lst]

    async def add_word(self, word: str) -> None:
        query = psg_insert(Words).values(word=word.capitalize()).returning(Words)
        query.on_conflict_do_nothing()
        res = await self.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_word_by_word(self, word: str) -> Words | None:
        query = select(Words).where(Words.word == word.capitalize())
        res = await self.database.execute_query(query)
        return res.scalar()

    async def add_used_word(self, game_session_id: int, word: str) -> None:
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
        query = select(UserGameSession).where(UserGameSession.game_sessions_id == game_session_id)
        res = await self.database.execute_query(query)
        players = [(player.player.username, player.point) for player in res.scalars().all()]
        return players

    def get_game_settings(self):
        query = select(GameSettings)
        res = await self.database.execute_query(query)
        return res.scalar_one()
