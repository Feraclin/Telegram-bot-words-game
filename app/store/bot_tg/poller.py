# Структура бота из статьи https://habr.com/ru/company/kts/blog/598575/

import asyncio
from asyncio import Task
from typing import Optional, TYPE_CHECKING

from app.store.tg_api.accessor import TgClient
from app.store.tg_api.schemes import UpdateObj

if TYPE_CHECKING:
    from app.web.app import Application


class Poller:
    def __init__(self, token: str, app: 'Application'):
        self.tg_client = TgClient(token)
        self._task: Optional[Task] = None
        self.app = app

    async def _worker(self):
        offset = 0
        while True:
            print('poller')
            res = await self.tg_client.get_updates_in_objects(offset=offset, timeout=20)
            for u in res.result:

                offset = u.update_id + 1

                if u.message is None and u.callback_query is None:
                    continue
                print(f"worker text: {u.message.text}" if u.message else f'worker text:{u.callback_query}')
                upd = UpdateObj.Schema().dump(u)
                self.app.logger.info(u)
                await self.app.rabbitMQ.send_event(message=upd)
                await asyncio.sleep(1/20)

    async def start(self):
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._task:
            self._task.cancel()
