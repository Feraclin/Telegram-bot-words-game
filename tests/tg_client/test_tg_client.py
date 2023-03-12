from unittest.mock import Mock

import pytest
from aioresponses import aioresponses

from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import SendMessageResponse
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
async def test_send_message(tg_client, mock_response, get_updates_response, get_updates_response_dict):
    mock_response.post(
            f"{tg_client.get_url('sendMessage')}",
            payload={"ok": True,
                     "result": get_updates_response_dict["result"][0]["message"]},
            status=200,
        )
    response = await tg_client.send_message(chat_id=get_updates_response.result[0].message.chat.id,
                                            text=get_updates_response.result[0].message.text)
    assert response == SendMessageResponse.Schema().load(data={"ok": True,
                                                               "result": get_updates_response_dict["result"][0][
                                                                   "message"]})


@pytest.mark.asyncio
async def test_send_keyboard(tg_client, mock_response, get_updates_response, get_updates_response_dict):
    keyboard = {"inline_keyboard": [[{"text": "Button", "callback_data": "test"}]]}
    result = get_updates_response_dict["result"][0]["message"]
    result["reply_markup"] = keyboard
    mock_response.post(
            f"{tg_client.get_url('sendMessage')}",
            payload={"ok": True, "result": result},
            status=200,
        )
    response = await tg_client.send_keyboard(chat_id=get_updates_response.result[0].message.chat.id,
                                             text=get_updates_response.result[0].message.text,
                                             keyboard=keyboard)
    assert response.result.message_id == 1
    assert response.result.reply_markup == keyboard
    assert response == SendMessageResponse.Schema().load(data={"ok": True,
                                                               "result": result})


@pytest.mark.asyncio
async def test_send_poll(tg_client, mock_response, get_updates_response, get_updates_response_dict):
    result = get_updates_response_dict["result"][0]["message"]
    options_send = ["Option 1", "Option 2"]
    options = [{'text': 'Option 1', 'voter_count': 0},
               {'text': 'Option 2', 'voter_count': 2}]
    result["poll"]["options"] = options
    result["poll"]["question"] = "test question"
    mock_response.post(
            f"{tg_client.get_url('sendPoll')}",
            payload={"ok": True, "result": result},
            status=200,
        )
    response = await tg_client.send_poll(chat_id=123,
                                         question="test question",
                                         options=options_send)
    assert response == SendMessageResponse.Schema().load(data={"ok": True,
                                                               "result": result})


@pytest.mark.asyncio
async def test_remove_inline_keyboard(tg_client, mock_response, get_updates_response, get_updates_response_dict):
    result = get_updates_response_dict["result"][0]["message"]
    mock_response.post(
            f"{tg_client.get_url('editMessageReplyMarkup')}",
            payload={"ok": True, "result": result},
            status=200,
        )
    response = await tg_client.remove_inline_keyboard(chat_id=get_updates_response.result[0].message.chat.id,
                                                      message_id=get_updates_response.result[0].message.message_id)
    assert response == SendMessageResponse.Schema().load(data={"ok": True,
                                                               "result": result})


@pytest.mark.asyncio
async def test_stop_poll(tg_client, mock_response, get_updates_response, get_updates_response_dict):
    result = get_updates_response_dict["result"][0]["message"]
    options = [{'text': 'Option 1', 'voter_count': 0},
               {'text': 'Option 2', 'voter_count': 2}]
    result["poll"]["options"] = options
    result["poll"]["question"] = "test question"
    mock_response.post(
            f"{tg_client.get_url('stopPoll')}",
            payload={"ok": True, "result": result},
            status=200,
        )
    result["poll"]["total_voter_count"] = 10
    response = await tg_client.stop_poll(chat_id=get_updates_response.result[0].message.chat.id,
                                         message_id=get_updates_response.result[0].message.message_id)
    assert response.result.poll.total_voter_count == 10


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
