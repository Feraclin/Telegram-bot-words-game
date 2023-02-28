import asyncio
import logging
from asyncio import Task

import aiohttp
from dotenv import find_dotenv, dotenv_values

from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.tg_api.accessor import TgClient
from app.store.tg_api.schemes import UpdateObj, GetUpdatesResponse


class Poller:
    def __init__(self, token: str, host: str, port: str, user: str, password: str):
        self.logger = logging.getLogger("poller")
        logging.basicConfig(level=logging.INFO)
        self._task: Task | None = None
        self.TgClient = TgClient(token=token)
        self.rabbitMQ = RabbitMQ(host=host, port=port, user=user, password=password)

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

    found_dotenv = find_dotenv(filename=".env")
    config_env = dotenv_values(found_dotenv)
    host = config_env.get("RABBITMQ_DEFAULT_HOST")
    port = config_env.get("RABBITMQ_DEFAULT_PORT")
    user = config_env.get("RABBITMQ_DEFAULT_USER")
    password = config_env.get("RABBITMQ_DEFAULT_PASS")
    token = config_env.get("BOT_TOKEN_TG")

    poller = Poller(token=token, host=host, port=port, user=user, password=password)

    loop = asyncio.new_event_loop()

    try:
        loop.create_task(poller.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(poller.stop())
