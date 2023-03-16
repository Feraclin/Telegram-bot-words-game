import asyncio
from unittest.mock import patch, MagicMock, Mock, AsyncMock

import bson
import pytest

from app.sender_app.messages import keyboards
from app.sender_app.sender import Sender
from app.web.config import config as cfg


@pytest.fixture
def sender():
    return Sender(cfg=cfg)


@pytest.fixture
async def message():
    message = MagicMock()
    message.ack = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_on_message(sender, message):
    upd = {"type_": "message", "chat_id": 123456, "text": "Test message"}
    message.body = bson.dumps(upd)
    with patch.object(sender, 'handle_update') as mock_handle:
        await sender.on_message(message)
        assert mock_handle.called
        mock_handle.assert_called_once_with(upd)
    assert message.ack.called


@pytest.mark.asyncio
async def test_start_stop(sender):
    with patch.object(sender.rabbitMQ, 'connect') as mock_connect, \
            patch.object(sender, '_worker_rabbit') as mock_worker, \
            patch.object(sender.rabbitMQ, 'disconnect') as mock_disconnect:
        await sender.start()
        assert mock_connect.called
        assert len(sender._tasks) == sender.concurrent_workers
        await sender.stop()
        await asyncio.sleep(0.1)
        assert all(task_.cancelled() for task_ in sender._tasks)
        assert mock_disconnect.called


@pytest.mark.asyncio
async def test_worker_rabbit(sender, message):
    with patch.object(sender.rabbitMQ, 'listen_events') as mock_listen:
        await sender._worker_rabbit()
        assert mock_listen.called
        mock_listen.assert_called_once_with(
            on_message_func=sender.on_message,
            queue_name=sender.queue_name,
            routing_key=[sender.routing_key_sender],
        )


@pytest.mark.asyncio
async def test_send_message(sender):
    chat_id = 123456
    text = "Test message"
    message = {"type_": "message", "chat_id": chat_id, "text": text, 'force_reply': True}
    with patch.object(sender.tg_client, 'send_message') as mock_send:
        await sender.handle_update(message)
        assert mock_send.called
        mock_send.assert_called_once_with(**{'chat_id': chat_id, 'text': text, 'force_reply': True})


@pytest.mark.asyncio
async def test_send_message_keyboard(sender):
    chat_id = 123456
    text = "Test message with keyboard"
    keyboard_name = "keyboard_team"
    message = {"type_": "message_keyboard", "chat_id": chat_id, "text": text, "keyboard": keyboard_name}
    with patch.object(sender.tg_client, 'send_keyboard') as mock_send:
        await sender.handle_update(message)
        assert mock_send.called
        mock_send.assert_called_once_with(**{'chat_id': chat_id, 'text': text, 'keyboard': keyboards.get(keyboard_name)})

@pytest.mark.asyncio
async def test_send_callback_alert(sender):
    callback_id = "12345"
    text = "Test callback alert"
    message = {"type_": "callback_alert", "callback_id": callback_id, "text": text}
    with patch.object(sender.tg_client, 'send_callback_alert') as mock_send:
        await sender.handle_update(message)
        assert mock_send.called
        mock_send.assert_called_once_with(**{'callback_id': callback_id, 'text': text})


@pytest.mark.asyncio
async def test_send_poll(sender):
    chat_id = 123456
    question = "Test poll question"
    options = ["Option 1", "Option 2", "Option 3"]
    anonymous = True
    message = {"type_": "send_poll", "chat_id": chat_id, "question": question, "options": options, "anonymous": anonymous, "period": 10}
    with patch.object(sender.tg_client, 'send_poll') as mock_send:
        with patch.object(sender.rabbitMQ, 'send_event') as mock_send_event:
            await sender.handle_update(message)
            assert mock_send.called
            mock_send.assert_called_once_with(**{'chat_id': chat_id, 'question': question, 'options': options, 'anonymous': anonymous, 'period': 10})
            mock_send_event.called
            assert mock_send_event.call_args[1]["delay"] == 12000

@pytest.mark.asyncio
async def test_check_poll(sender):
    poll_id = "12345"
    message_id = "67890"
    message = {"type_": "send_poll_answer", "poll_id": poll_id, "poll_message_id": message_id}
    with patch.object(sender, 'check_poll') as mock_check:
        await sender.handle_update(message)
        assert mock_check.called
        mock_check.assert_called_once_with(message)
