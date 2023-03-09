import asyncio

import aio_pika
import bson
import pytest
from unittest.mock import patch, AsyncMock, AsyncMock
from app.web.config import config as cfg
from app.store.rabbitMQ.rabbitMQ import RabbitMQ

@pytest.fixture()
def rabbitmq():
    rabbitmq = RabbitMQ(
        host=cfg.rabbitmq.host,
        port=cfg.rabbitmq.port,
        user=cfg.rabbitmq.user,
        password=cfg.rabbitmq.password,
    )
    rabbitmq.logger = AsyncMock()
    return rabbitmq

@pytest.mark.asyncio
async def test_connect(rabbitmq):
    mock_connection = AsyncMock()
    with patch('aio_pika.connect_robust', return_value=mock_connection):
        await rabbitmq.connect()
        assert rabbitmq.connection_ == mock_connection


@pytest.mark.asyncio
async def test_disconnect(rabbitmq):
    mock_connection = AsyncMock()
    mock_connection.close = AsyncMock(return_value=None)
    rabbitmq.connection_ = mock_connection
    await rabbitmq.disconnect()
    assert rabbitmq.connection_ is None


@pytest.mark.asyncio
async def test_send_event(rabbitmq):
    mock_exchange = AsyncMock()
    rabbitmq.exchange = mock_exchange
    message = {'foo': 'bar'}
    routing_key = 'test'
    await rabbitmq.send_event(message, routing_key)
    mock_exchange.publish.assert_called_once_with(
        aio_pika.Message(
            body=bson.dumps(message),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            headers={"x-delay": 0},
        ),
        routing_key=routing_key,
        mandatory=False,
    )


@pytest.mark.asyncio
async def test_listen_events(rabbitmq):
    mock_queue = AsyncMock()
    mock_queue.consume = AsyncMock(return_value=asyncio.sleep(0))
    mock_channel = AsyncMock()
    mock_channel.declare_exchange = AsyncMock(return_value=asyncio.sleep(0))
    mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
    mock_connection = AsyncMock()
    mock_connection.channel = AsyncMock(return_value=mock_channel)
    rabbitmq.connection_ = mock_connection
    routing_key = ['test']
    queue_name = 'test_queue'
    await rabbitmq.listen_events(routing_key, queue_name)
    mock_channel.set_qos.assert_called_once_with(prefetch_count=1)
    mock_channel.declare_exchange.assert_called_once_with(
        name="auth-delayed",
        type=aio_pika.ExchangeType.X_DELAYED_MESSAGE,
        durable=True,
        arguments={"x-delayed-type": "direct"},
    )
    mock_channel.declare_queue.assert_called_once_with(
        name=queue_name,
        durable=True,
    )
    mock_queue.bind.assert_called_once_with(mock_channel.declare_exchange.return_value, routing_key=routing_key[0])
    mock_queue.consume.assert_called_once_with(rabbitmq.on_message)


@pytest.mark.asyncio
async def test_on_message(rabbitmq):
    mock_message = AsyncMock()
    mock_message.body = bson.dumps({'foo': 'bar'})
    rabbitmq.logger = AsyncMock()
    await rabbitmq.on_message(mock_message)
    rabbitmq.logger.info.assert_called_once_with("Message body is: {'foo': 'bar'}")
