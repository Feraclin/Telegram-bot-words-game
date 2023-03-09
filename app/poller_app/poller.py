import asyncio
import logging
from asyncio import Task

from app.poller_app.constnant import get_update_timeout
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import UpdateObj
from app.web.config import ConfigEnv, config


class Poller:
    def __init__(self, cfg: ConfigEnv, timeout: int = 20):
        self.logger = logging.getLogger("poller")
        logging.basicConfig(level=logging.INFO)
        self._task: Task | None = None
        self.TgClient = TgClient(token=cfg.tg_token.tg_token)
        self.rabbitMQ = RabbitMQ(
            host=cfg.rabbitmq.host,
            port=cfg.rabbitmq.port,
            user=cfg.rabbitmq.user,
            password=cfg.rabbitmq.password,
        )
        self.is_stop = False
        self.timeout = timeout

    async def _poll(self):

        offset = 0
        while not self.is_stop:

            self.logger.info("Polling...")
            res = await self.TgClient.get_updates_in_objects(offset=offset, timeout=self.timeout)

            for u in res.result:

                offset = u.update_id + 1
                upd = UpdateObj.Schema().dump(u)
                await self.rabbitMQ.send_event(message=upd, routing_key="poller")
                await asyncio.sleep(get_update_timeout)

    async def start(self):
        self._task = asyncio.create_task(self._poll())
        await self.rabbitMQ.connect()

    async def stop(self):
        self.is_stop = True
        await self.rabbitMQ.disconnect()
        if self._task:
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None


if __name__ == "__main__":
    poller = Poller(cfg=config)

    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(poller.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(poller.stop())
        loop.close()
