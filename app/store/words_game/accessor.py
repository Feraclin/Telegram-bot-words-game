from sqlalchemy import select, insert, update, func
from sqlalchemy.dialects.postgresql import insert as psg_insert

from app.base.base_accessor import BaseAccessor
from app.words_game.models import GameSession, User, City
from random import choice, randint


class WGAccessor(BaseAccessor):

    async def select_active_session_by_id(self, user_id: int) -> GameSession | None:

        query = select(GameSession).where(GameSession.user_id == user_id, GameSession.status == True)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_gamesession(self, user_id: int) -> GameSession:

        query = insert(GameSession).values(user_id=user_id, status=True)
        res = await self.app.database.execute_query(query)
        return res.scalar()

    async def update_gamesession(self,
                                 game_id: int,
                                 status: bool = True,
                                 next_letter: str | None = None) -> GameSession | None:
        query = update(GameSession).where(GameSession.id == game_id).values(status=status,
                                                                            next_start_letter=next_letter)\
            .returning(GameSession)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_user(self, user_id: int, username: str) -> None:
        query = psg_insert(User).values(id=user_id, username=username).returning(User)
        query = query.on_conflict_do_nothing()
        res = (await self.app.database.execute_query(query)).scalar()
        if res:
            return res
        else:
            return await self.select_user_by_id(user_id)

    async def select_user_by_id(self, user_id: int) -> User | None:
        query = select(User).where(User.id == user_id)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_city_by_first_letter(self, letter: str | None = None) -> str | None:
        if not letter:

            letter = choice(list("АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ"))
        query = select(func.count(City.id)).where(City.name.like(f"{letter}%"))
        city_count = (await self.app.database.execute_query(query)).scalar()
        query = select(City).where(City.name.like(f"{letter}%")).offset(randint(0, city_count)).limit(1)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def get_city_by_name(self, name: str) -> str | None:
        queue = select(City).where(City.name == name)
        res = await self.app.database.execute_query(queue)
        print(a := res.scalar_one_or_none())
        return a
