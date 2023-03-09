import asyncio

import pytest
from unittest.mock import Mock, patch

from app.poller_app.constnant import get_update_timeout
from app.poller_app.poller import Poller
from app.web.config import ConfigEnv, config as cfg
from fixtures import *


@pytest.fixture
def poller():
    return Poller(cfg=cfg, timeout=1)


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()


@pytest.mark.asyncio
async def test_poller_start_stop(poller):
    with patch.object(poller.rabbitMQ, 'connect') as mock_connect:
        with patch.object(poller.rabbitMQ, 'disconnect') as mock_disconnect:
            await poller.start()
            assert poller._task is not None
            assert mock_connect.called
            await poller.stop()
            assert poller._task is None
            assert mock_disconnect.called


@pytest.mark.asyncio
async def test_poller_poll(poller, get_updates_response):
    with patch.object(poller.TgClient, 'get_updates_in_objects') as mock_get_updates:
        with patch.object(poller.rabbitMQ, 'send_event') as mock_send_event:
            mock_get_updates.return_value = get_updates_response
            task = asyncio.create_task(poller._poll())
            await asyncio.sleep(get_update_timeout)
            poller.is_stop = True
            task.cancel()
            assert mock_get_updates.called
            assert mock_send_event.called
