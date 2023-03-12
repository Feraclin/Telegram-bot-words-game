from sqlalchemy import desc, select, func

from app.web.app import View
from app.web.mixins import AuthRequiredMixin
from app.web.utils import json_response
from app.words_game.models import GameSession, City, User, GameSettings
from app.words_game.schemes import (
    GameSessionListResponseSchema,
    PlayerListResponseSchema,
    CityListResponseSchema,
    UserSchema,
    CitySchema,
    PaginationSchema,
    GameSessionSchema,
    GameSettingsSchema,
    PaginationSchemaGames,
)

from aiohttp_apispec import docs, response_schema, querystring_schema, request_schema


class GameSessionView(AuthRequiredMixin, View):
    @docs(tags=["game"], summary="List Game Sessions", description="List all game sessions")
    @querystring_schema(PaginationSchemaGames)
    @response_schema(GameSessionListResponseSchema, 200)
    async def get(self):
        page = int(self.request.query.get("page", "1"))
        per_page = int(self.request.query.get("per_page", "20"))
        offset = (page - 1) * per_page
        stmt = select(GameSession).order_by(GameSession.id).limit(per_page).offset(offset)
        game_sessions = await self.request.app.database.execute_query(stmt)
        game_sessions = game_sessions.scalars().all()
        game_sessions = [GameSessionSchema().dump(i) for i in game_sessions]
        stmt = select(func.count(GameSession.id))
        total_count = await self.request.app.database.execute_query(stmt)
        total_count = total_count.scalar()
        total_pages = (total_count + per_page - 1) // per_page
        return json_response(data={"game_sessions": game_sessions, "total_pages": total_pages})


class PlayerView(AuthRequiredMixin, View):
    @docs(tags=["game"], summary="List Players", description="List all players")
    @response_schema(PlayerListResponseSchema, 200)
    async def get(self):
        stmt = select(User).order_by(User.id)
        players = await self.request.app.database.execute_query(stmt)
        players = [UserSchema().dump(i) for i in players.scalars().all()]
        return json_response(data={"users": players})


class CityView(AuthRequiredMixin, View):
    @docs(tags=["game"], summary="List Cities", description="List all cities")
    @querystring_schema(PaginationSchema)
    @response_schema(CityListResponseSchema, 200)
    async def get(self):
        page = int(self.request.query.get("page", "1"))
        per_page = int(self.request.query.get("per_page", "20"))
        stmt = select(City).order_by(desc(City.id)).limit(per_page).offset((page - 1) * per_page)
        cities = await self.request.app.database.execute_query(stmt)
        cities = [CitySchema().dump(i) for i in cities.scalars().all()]
        return json_response(data={"cities": cities})


class GameSettingsView(AuthRequiredMixin, View):
    @docs(tags=["game"], summary="Get Game Settings", description="Get game settings")
    @response_schema(GameSettingsSchema, 200)
    async def get(self):
        game_settings = GameSettings.get_instance(self.request.app.database.session)
        return json_response(data={"game_settings": GameSettingsSchema().dump(game_settings)})

    @docs(tags=["game"], summary="Update Game Settings", description="Update game settings")
    @request_schema(GameSettingsSchema)
    @response_schema(GameSettingsSchema, 200)
    async def post(self):
        data = await self.request.json()
        game_settings = GameSettings.get_instance(self.request.app.database.session)
        game_settings.response_time = data.get("response_time", game_settings.response_time)
        game_settings.anonymous_poll = data.get("anonymous_poll", game_settings.anonymous_poll)
        game_settings.poll_time = data.get("poll_time", game_settings.poll_time)
        await self.request.app.database.add_query(game_settings)
        return json_response(data={"game_settings": GameSettingsSchema().dump(game_settings)})
