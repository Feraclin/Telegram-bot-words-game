from sqlalchemy import select, insert, update
from sqlalchemy.dialects.postgresql import insert as psg_insert

from app.base.base_accessor import BaseAccessor
from app.words_game.models import GameSession, User


class WGAccessor(BaseAccessor):

    async def select_active_session_by_id(self, user_id: int) -> GameSession | None:
        query = select(User).where(User.id == user_id)
        user = (await self.app.database.execute_query(query)).scalar_one_or_none()
        query = select(GameSession).where(GameSession.user_id == user.id, GameSession.status == True)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_gamesession(self, user_id: int) -> GameSession:
        query = select(User).where(User.id == user_id)
        user = (await self.app.database.execute_query(query)).scalar_one_or_none()
        query = insert(GameSession).values(user_id=user.id, status=True)
        res = await self.app.database.execute_query(query)
        return res.scalar()

    async def update_gamesession(self, game_id: int, status: bool) -> GameSession:
        query = update(GameSession).where(GameSession.id == game_id, GameSession.status == status)
        res = await self.app.database.execute_query(query)
        return res.scalar()

    async def create_user(self, user_id: int, username: str) -> None:
        query = psg_insert(User).values(user_id=user_id, username=username).returning(User)
        query = query.on_conflict_do_nothing()
        res = (await self.app.database.execute_query(query)).scalar()
        if res:
            return res
        else:
            return await self.select_user_by_id(user_id)

    async def select_user_by_id(self, user_id: int) -> User | None:
        query = select(User).where(User.user_id == user_id)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()
