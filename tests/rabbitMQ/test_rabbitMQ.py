import asyncio

import bson
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.web.config import config


@pytest.fixture
def rabbitmq():
    return RabbitMQ(host=config.rabbitmq.host,
                    port=config.rabbitmq.port,
                    user=config.rabbitmq.user,
                    password=config.rabbitmq.password)


@pytest.mark.asyncio
async def test_connect(rabbitmq):
    await rabbitmq.connect()
    assert rabbitmq.connection_ is not None


@pytest.mark.asyncio
async def test_disconnect(rabbitmq):
    await rabbitmq.connect()
    await rabbitmq.disconnect()
    assert rabbitmq.connection_ is None


@pytest.mark.asyncio
async def test_send_event(rabbitmq):
    await rabbitmq.connect()
    message = {"key": "value"}
    routing_key = "test"
    delay = 0
    await rabbitmq.send_event(message, routing_key, delay)
    assert rabbitmq.channel.publisher_confirms == 1


@pytest.mark.asyncio
async def test_on_message(rabbitmq):
    with patch.object(rabbitmq.logger, "info") as mock_logger:
        message = AsyncMock()
        text = {"key": "value"}
        message.body = bson.dumps(text)
        await rabbitmq.on_message(message)
        mock_logger.assert_called_once_with("Message body is: %r" % text)
