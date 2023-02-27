from sqlalchemy import select, insert, update, func, delete
from sqlalchemy.dialects.postgresql import insert as psg_insert

from app.base.base_accessor import BaseAccessor
from app.words_game.models import GameSession, User, City, UsedCity, Team
from random import choice, randint


class WGAccessor(BaseAccessor):

    async def select_active_session_by_id(self,
                                          user_id: int | None = None,
                                          chat_id: int | None = None) -> GameSession | None:
        if user_id:
            query = select(GameSession).where(GameSession.user_id == user_id,
                                              GameSession.status == True)
        elif chat_id:
            query = select(GameSession).where(GameSession.chat_id == chat_id,
                                              GameSession.status == True)
        else:
            return None
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_game_session(self,
                                  user_id: int,
                                  chat_id: int,
                                  chat_type: str) -> GameSession:

        query = insert(GameSession).values(user_id=user_id,
                                           chat_id=chat_id,
                                           game_type=chat_type,
                                           status=True)
        res = await self.app.database.execute_query(query)
        return res.scalar()

    async def update_game_session(self,
                                  game_id: int,
                                  status: bool = True,
                                  next_letter: str | None = None,
                                  words: str | None = None) -> GameSession | None:
        if words:
            query = update(GameSession).where(GameSession.id == game_id).values(status=status,
                                                                                next_start_letter=next_letter,
                                                                                words=words)\
                .returning(GameSession)
        else:
            query = update(GameSession).where(GameSession.id == game_id).values(status=status,
                                                                                next_start_letter=next_letter) \
                .returning(GameSession)
        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def delete_game_session(self, chat_id: int) -> None:
        query = delete(GameSession).where(GameSession.chat_id == chat_id)

        res = await self.app.database.execute_query(query)
        return res.scalar()

    async def add_user_to_game_session(self,
                                       game_id: int,
                                       user_id: int) -> GameSession | None:
        query = update(GameSession).where(GameSession.id == game_id).values(next_user_id=user_id).returning(GameSession)

        res = await self.app.database.execute_query(query)
        return res.scalar_one_or_none()

    async def create_user(self,
                          user_id: int,
                          username: str) -> None:

        query = psg_insert(User).values(id=user_id,
                                        username=username).returning(User)
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

    async def get_city_by_first_letter(self,
                                       game_session_id: int,
                                       letter: str | None = None,
                                       city_count: int | None = None) -> City | None:
        if not letter:

            letter = choice(list("АБВГДЕЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ"))
        query = select(func.count(City.id)).where(City.name.like(f"{letter}%"))
        city_count = city_count if city_count else (await self.app.database.execute_query(query)).scalar()
        query = select(City).where(City.name.like(f"{letter}%")).offset(randint(0, city_count)).limit(1)
        res = await self.app.database.execute_query(query)
        city = res.scalar_one_or_none()
        if not city:
            return city
        elif await self.check_city_in_used(city.id, game_session_id):
            return await self.get_city_by_first_letter(game_session_id=game_session_id,
                                                       letter=letter,
                                                       city_count=city_count)
        else:
            return city

    async def get_city_by_name(self, name: str) -> str | None:
        queue = select(City).where(City.name == name)
        res = await self.app.database.execute_query(queue)
        a = res.scalar()
        return a

    async def check_city_in_used(self, city_id: int, game_session_id: int) -> bool:
        queue = select(UsedCity).where(UsedCity.city_id == city_id, UsedCity.game_session_id == game_session_id)
        res = await self.app.database.execute_query(queue)
        double_city = res.scalar_one_or_none()

        return True if double_city else False

    async def set_city_to_used(self, city_id: int, game_session_id: int) -> None:

        queue = insert(UsedCity).values(city_id=city_id, game_session_id=game_session_id)
        await self.app.database.execute_query(queue)
        return

    async def add_user_to_team(self, user_id: int, game_id: int) -> None:
        query = psg_insert(Team).values(player_id=user_id, game_sessions_id=game_id)
        query = query.on_conflict_do_nothing()
        await self.app.database.execute_query(query)
        return

    async def get_team_by_game_id(self, game_session_id: int) -> list[int]:
        query = select(Team.player_id).where(Team.game_sessions_id == game_session_id, Team.life > 0)
        res = await self.app.database.execute_query(query)
        team_lst = res.scalars().all()
        return team_lst

    async def remove_life_from_player(self,
                                      game_id: int,
                                      player_id: int) -> None:
        query = update(Team).where(Team.game_sessions_id == game_id,
                                   Team.player_id == player_id).values(life=Team.life - 1)
        await self.app.database.execute_query(query)
