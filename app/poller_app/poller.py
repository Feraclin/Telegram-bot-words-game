import asyncio
import logging
from asyncio import Task


from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import UpdateObj
from app.web.config import ConfigEnv, config


class Poller:
    def __init__(self, cfg: ConfigEnv):
        self.logger = logging.getLogger("poller")
        logging.basicConfig(level=logging.INFO)
        self._task: Task | None = None
        self.TgClient = TgClient(token=cfg.tg_token.tg_token)
        self.rabbitMQ = RabbitMQ(host=cfg.rabbitmq.host,
                                 port=cfg.rabbitmq.port,
                                 user=cfg.rabbitmq.user,
                                 password=cfg.rabbitmq.password)

    async def _worker(self):
        offset = 0
        while True:
            print("poller")
            res = await self.TgClient.get_updates_in_objects(offset=offset, timeout=20)
            for u in res.result:
                offset = u.update_id + 1
                upd = UpdateObj.Schema().dump(u)
                self.logger.info(u)
                print(u)
                await self.rabbitMQ.send_event(message=upd)
                await asyncio.sleep(1 / 20)

    async def start(self):
        self._task = asyncio.create_task(self._worker())
        await self.rabbitMQ.connect()

    async def stop(self):
        await self.rabbitMQ.disconnect()
        if self._task:
            self._task.cancel()


if __name__ == "__main__":

    poller = Poller(cfg=config)

    loop = asyncio.new_event_loop()

    try:
        loop.create_task(poller.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(poller.stop())
