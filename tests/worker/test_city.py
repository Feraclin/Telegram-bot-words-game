
from unittest.mock import patch

import bson

from app.worker_app.worker import Worker
from tests.conftest import IncomingMessage
from tests.poller.fixtures import *


class TestCity:

    async def test_get_city(self, worker: Worker, city):
        city_ = await worker.words_game.get_city_by_name(name=city.name)
        assert city_ is not None
        assert city_.name == city.name
        assert city_.id == city.id

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

    async def test_city_from_player(self, worker: Worker, game, city):

        with patch.object(target=worker.words_game,
                          attribute="select_active_session_by_id",
                          return_value=game) as mock:
            upd = UpdateObj.Schema().load({
                                           "message": {"text": "Москва",
                                                       "message_id": 1,
                                                       "date": 1,
                                                       "chat": {"type": "group",
                                                                "id": game.chat_id},
                                                       "from": {"id": game.chat_id,
                                                                "username": "test",
                                                                "first_name": city.name[0]}}})
            await worker.check_city(upd=upd)
            assert mock.call_count == 1

    async def test_stop_game(self, worker: Worker, game):
        with patch.object(target=worker.words_game,
                          attribute="select_active_session_by_id",
                          return_value=game) as mock:
            upd = UpdateObj.Schema().load({
                                           "message": {"text": "/stop",
                                                       "message_id": 1,
                                                       "date": 1,
                                                       "chat": {"type": "group",
                                                                "id": game.chat_id},
                                                       "from": {"id": game.chat_id,
                                                                "username": "test",
                                                                "first_name": "Test"}}})
            await worker.stop_game(upd=upd)
            assert mock.call_count == 1

    async def test_pick_city(self, worker: Worker, game, city):
        with patch.object(target=worker.words_game,
                          attribute="select_active_session_by_id",
                          return_value=game) as mock:
            with patch.object(target=worker.words_game,
                              attribute="set_city_to_used",
                              return_value=game) as mock1:
                await worker.pick_city(user_id=game.chat_id,
                                       chat_id=game.chat_id,
                                       username="test",
                                       letter=city.name[0])
                assert mock.call_count == 1
                assert mock1.call_count == 0

    async def test_check_city(self, worker: Worker, game, city):
        with patch.object(target=worker.words_game,
                          attribute="select_active_session_by_id",
                          return_value=game) as mock:
            with patch.object(target=worker.words_game,
                              attribute="get_city_by_name",
                              return_value=city) as mock_city:
                upd = UpdateObj.Schema().load({
                    "message": {"text": "Москва",
                                "message_id": 1,
                                "date": 1,
                                "chat": {"type": "group",
                                         "id": game.chat_id},
                                "from": {"id": game.chat_id,
                                         "username": "test",
                                         "first_name": "Test"}}})
                await worker.check_city(upd=upd)
                assert mock.call_count == 1
                assert mock_city.call_count == 1

    async def test_bot_looser(self, worker: Worker, game):
        with patch.object(target=worker.words_game,
                          attribute="update_game_session",
                          return_value=game) as mock:
            upd = UpdateObj.Schema().load({
                "message": {"text": "Москва",
                            "message_id": 1,
                            "date": 1,
                            "chat": {"type": "group",
                                     "id": game.chat_id},
                            "from": {"id": game.chat_id,
                                     "username": "test",
                                     "first_name": "Test"}}})
            await worker.bot_looser(game_session_id=game.id)
            assert mock.call_count == 1


class TestWorker:
    async def test_on_message_poller(self, worker: Worker, mocker, update_obj):
        mock_handle_update = mocker.patch.object(target=worker, attribute="handle_message")
        message = IncomingMessage(
            body=bson.dumps(UpdateObj.Schema().dump(update_obj)),
            routing_key="poller"
        )
        await worker.on_message(message=message)
        assert mock_handle_update.call_count == 1

    async def test_on_message_pick_leader(self, worker: Worker, game, mocker):
        mock_select_active_session_by_id = mocker.patch.object(
            target=worker.words_game,
            attribute="select_active_session_by_id",
            return_value=game
        )
        mock_pick_leader = mocker.patch.object(target=worker, attribute="pick_leader")
        message = IncomingMessage(bson.dumps({"type_": "pick_leader", "chat_id": game.chat_id}),
                                  worker.routing_key_worker)
        await worker.on_message(message=message)
        assert mock_select_active_session_by_id.call_count == 1
        assert mock_pick_leader.call_count == 1

    async def test_on_message_poll_result_yes(self, worker: Worker, game, mocker):
        mock_select_active_session_by_id = mocker.patch.object(
            target=worker.words_game,
            attribute="select_active_session_by_id",
            return_value=game
        )
        mock_update_game_session = mocker.patch.object(
            target=worker.words_game,
            attribute="update_game_session"
        )
        mock_right_word = mocker.patch.object(target=worker, attribute="right_word")
        message = IncomingMessage(
            body=bson.dumps({
                "type_": "poll_result",
                "chat_id": game.chat_id,
                "poll_id": 123,
                "poll_result": "yes",
                "word": "test"
            }),
            routing_key=worker.routing_key_worker
        )
        await worker.on_message(message=message)
        assert mock_select_active_session_by_id.call_count == 1
        assert mock_update_game_session.call_count == 1
        assert mock_right_word.call_count == 1

    async def test_on_message_poll_result_no(self, worker: Worker, game, mocker):
        mock_select_active_session_by_id = mocker.patch.object(
            target=worker.words_game,
            attribute="select_active_session_by_id",
            return_value=game
        )
        mock_pick_leader = mocker.patch.object(target=worker, attribute="pick_leader")
        message = IncomingMessage(
            body=bson.dumps({
                "type_": "poll_result",
                "chat_id": game.chat_id,
                "poll_id": 123,
                "poll_result": "no"
            }),
            routing_key=worker.routing_key_worker
        )
        await worker.on_message(message=message)
        assert mock_select_active_session_by_id.call_count == 1
        assert mock_pick_leader.call_count == 1

    async def test_on_message_slow_player(self, worker: Worker, game, mocker):
        mock_select_active_session_by_id = mocker.patch.object(
            target=worker.words_game,
            attribute="select_active_session_by_id",
            return_value=game
        )
        mock_remove_life_from_player = mocker.patch.object(
            target=worker.words_game,
            attribute="remove_life_from_player"
        )
        mock_pick_leader = mocker.patch.object(target=worker, attribute="pick_leader")
        message = IncomingMessage(
            body=bson.dumps({
                "type_": "slow_player",
                "chat_id": game.chat_id,
                "user_id": game.next_user_id
            }),
            routing_key=worker.routing_key_worker
        )
        await worker.on_message(message=message)
        assert mock_select_active_session_by_id.call_count == 1
        assert mock_remove_life_from_player.call_count == 1
        assert mock_pick_leader.call_count == 1

    async def test_on_message_unknown_type(self, worker: Worker, mocker):
        mock_logger_info = mocker.patch.object(target=worker.logger, attribute="info")
        message = IncomingMessage(
            body=bson.dumps({"type_": "unknown"}),
            routing_key=worker.routing_key_worker
        )
        await worker.on_message(message=message)
        assert mock_logger_info.call_count == 1


# class TestWord:
#     async def test_add_to_team(self, worker: Worker, game, user2):
#         with patch.object(
#             target=worker.words_game,
#             attribute="select_active_session_by_id",
#             return_value=game
#         ) as mock_select_active_session_by_id:
#             with patch.object(target=worker.words_game,
#                               attribute="add_user_to_team") as mock_add_user_to_team:
#                 message = IncomingMessage(
#                     body=bson.dumps({
#                         "callback_query": {
#                             "id": "1",
#                             "from": {"id": user2.id, "username": user2.username, "first_name": "Test"},
#                             "message": {
#                                 "message_id": 1,
#                                 "date": 1,
#                                 "chat": {"type": "group", "id": game.chat_id},
#                             },
#                             "data": "team_1"
#                         }
#                     }),
#                     routing_key=worker.routing_key_worker
#                 )
#                 await worker.add_to_team(upd=UpdateObj.Schema().load(message.body))
#                 assert mock_select_active_session_by_id.call_count == 1
#                 assert mock_add_user_to_team.call_count == 1
#                 assert mock_add_user_to_team.call_args[1]["game_id"] == game.id
#                 assert mock_add_user_to_team.call_args[1]["user_id"] == user2.id

    # async def test_pick_leader(self, worker: Worker, game, mocker):
    #     mock_select_active_session_by_id = mocker.patch.object(
    #         target=worker.words_game,
    #         attribute="select_active_session_by_id",
    #         return_value=game
    #     )
    #     mock_get_team_by_game_id = mocker.patch.object(target=worker.words_game, attribute="get_team_by_game_id")
    #     mock_select_user_by_id = mocker.patch.object(target=worker.words_game, attribute="select_user_by_id")
    #     mock_change_next_user_to_game_session = mocker.patch.object(
    #         target=worker.words_game,
    #         attribute="change_next_user_to_game_session"
    #     )
    #     message = IncomingMessage(
    #         body=bson.dumps({
    #             "type_": "pick_leader",
    #             "chat_id": game.chat_id
    #         }),
    #         routing_key=worker.routing_key_worker
    #     )
    #     await worker.pick_leader(game=game)