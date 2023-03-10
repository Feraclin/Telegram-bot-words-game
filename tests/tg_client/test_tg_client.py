import pytest
from aioresponses import aioresponses

from store.tg_api.client import TgClient
from store.tg_api.schemes import SendMessageResponse
from tests.poller.fixtures import *

@pytest.fixture(autouse=True)
async def mock_response():
    with aioresponses(passthrough=["http://127.0.0.1"]) as responses_mock:
        yield responses_mock


@pytest.fixture
def tg_client():
    return TgClient(token="test_token")


@pytest.mark.asyncio
async def test_get_updates(tg_client, mock_response):

    mock_response.get(
        f"{tg_client.get_url('getUpdates')}",
        payload={"result": []},
        status=200,
    )
    response = await tg_client.get_updates()
    assert response == {"result": []}


@pytest.mark.asyncio
async def test_get_updates_in_objects(tg_client, mock_response, get_updates_response):
    mock_response.get(
            f"{tg_client.get_url('getUpdates')}",
            payload=GetUpdatesResponse.Schema().dump(get_updates_response),
            status=200,
        )
    response = await tg_client.get_updates_in_objects()
    assert response.result == get_updates_response.result


@pytest.mark.asyncio
async def test_get_me(tg_client, mock_response):
    mock_response.get(
            f"{tg_client.get_url('getMe')}",
            payload={"ok": True, "result": {"id": 123456789, "is_bot": True}},
            status=200,
        )
    response = await tg_client.get_me()
    assert response == {"ok": True, "result": {"id": 123456789, "is_bot": True}}


@pytest.mark.asyncio
async def test_send_message(tg_client, mock_response, get_updates_response, message):
    pprint(GetUpdatesResponse.Schema().dump(get_updates_response)["result"])
    pprint(SendMessageResponse.Schema().dump(get_updates_response.result[0].message))
    # mock_response.post(
    #         f"{tg_client.get_url('sendMessage')}",
    #         payload={"ok": True, "result": {"message": SendMessageResponse.Schema().dump(get_updates_response)}},
    #         status=200,
    #     )
    #
    # response = await tg_client.send_message(chat_id=123, text="test message")
    # assert response.result.message_id == 123


@pytest.mark.asyncio
async def test_send_keyboard(tg_client, mock_response):
    keyboard = {"inline_keyboard": [[{"text": "Button", "callback_data": "test"}]]}
    mock_response.post(
            f"{tg_client.get_url('sendMessage')}",
            payload={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
    response = await tg_client.send_keyboard(chat_id=123, text="test message", keyboard=keyboard)
    assert response.result.message_id == 123


@pytest.mark.asyncio
async def test_send_keyboard_to_player(tg_client, mock_response):
    keyboard = {"inline_keyboard": [[{"text": "Button", "callback_data": "test"}]]}
    mock_response.post(
            f"{tg_client.get_url('sendMessage')}",
            payload={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
    response = await tg_client.send_keyboard_to_player(chat_id=123, text="test message", keyboard=keyboard)
    assert response.result.message_id == 123


@pytest.mark.asyncio
async def test_send_poll(tg_client, mock_response):
    options = ["option1", "option2"]
    mock_response.post(
            f"{tg_client.get_url('sendPoll')}",
            payload={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
    response = await tg_client.send_poll(chat_id=123, question="test question", options=options)
    assert response.result.message_id == 123


@pytest.mark.asyncio
async def test_remove_inline_keyboard(tg_client, mock_response):
    mock_response.post(
            f"{tg_client.get_url('editMessageReplyMarkup')}",
            payload={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
    response = await tg_client.remove_inline_keyboard(message_id=123, chat_id=456)
    assert response.result.message_id == 123


@pytest.mark.asyncio
async def test_stop_poll(tg_client):
    mock_response.post(
            f"{tg_client.get_url('stopPoll')}",
            payload={"ok": True, "result": {"total_voter_count": 10}},
            status=200,
        )
    response = await tg_client.stop_poll(chat_id=123, message_id=456)
    assert response.result.total_voter_count == 10


@pytest.mark.asyncio
async def test_send_callback_alert(tg_client, mock_response):
    mock_response.post(
            f"{tg_client.get_url('answerCallbackQuery')}",
            payload={},
            status=200,
        )
    response = await tg_client.send_callback_alert(callback_id="test",
                                                   text="test text")
    assert response == 200


@pytest.mark.asyncio
async def test_edit_message_text(tg_client, mock_response):
    mock_response.post(
            f"{tg_client.get_url('editMessageText')}",
            payload={"ok": True, "result": {"message_id": 123}},
            status=200,
        )
    response = await tg_client.edit_message_text(chat_id=123, message_id=456)
    assert response.result.message_id == 123
