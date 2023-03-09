import pytest

from app.store.tg_api.schemes import UpdateObj, Message
from app.worker_app.worker import Worker


class TestCity:

    async def test_get_city(self, worker: Worker):
        city = await worker.words_game.get_city_by_name(name="Москва")
        assert city is not None
        assert city.name == "Москва"
        assert city.id == 17288

    async def test_get_wrong_city(self, worker: Worker):
        city = await worker.words_game.get_city_by_name(name="Масква")
        assert city is None

    async def test_city_from_player(self, worker: Worker, game):
        upd = UpdateObj.Schema().load({
                                       "message": {"text": "Москва",
                                                   "message_id": 1,
                                                   "date": 1,
                                                   "chat": {"type": "group",
                                                            "id": 999999},
                                                   "from": {"id": 999999,
                                                            "username": "test",
                                                            "first_name": "test"}}})

        await worker.check_city(upd=upd)

