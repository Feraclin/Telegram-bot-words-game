from pprint import pprint

import pytest

from app.store.tg_api.schemes import UpdateObj, Message
from app.worker_app.worker import Worker


class TestCity:

    async def test_get_city(self, worker: Worker):
        city = await worker.words_game.get_city_by_name(name="Москва")
        assert city is not None
        assert city.name == "Москва"
        assert city.id == 1

    async def test_get_wrong_city(self, worker: Worker):
        city = await worker.words_game.get_city_by_name(name="Масква")
        assert city is None

    async def test_get_game_session_by_chat_id(self, worker: Worker, game):
        game_session = await worker.words_game.select_active_session_by_id(chat_id=game.chat_id)
        assert game_session is not None
        assert game_session.chat_id == game.chat_id

    def test_game_creation(self, game):
        assert game.id is not None
        print(f"Test passed for game with id {game.id}")

    async def test_city_from_player(self, worker: Worker, game):
        print("Session ID in test_city_from_player:", id(worker.database.session))
        upd = UpdateObj.Schema().load({
                                       "message": {"text": "Москва",
                                                   "message_id": 1,
                                                   "date": 1,
                                                   "chat": {"type": "group",
                                                            "id": game.chat_id},
                                                   "from": {"id": game.chat_id,
                                                            "username": "test",
                                                            "first_name": "test"}}})
        await worker.check_city(upd=upd)
