import asyncio
import logging
from asyncio import Task

from .constnant import get_update_timeout
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import UpdateObj
from app.web.config import ConfigEnv, config


class Poller:
    """
    Класс Poller отвечает за опрос обновлений в Telegram и отправку их в RabbitMQ.

    Атрибуты:
    - logger: объект logging.Logger для логирования сообщений
    - _task: объект asyncio.Task для запуска опроса в фоновом режиме
    - TgClient: объект TgClient для работы с Telegram API
    - rabbitMQ: объект RabbitMQ для отправки сообщений в очередь

    Методы:
    - __init__(self, cfg: ConfigEnv): конструктор класса
    - _poll(self): метод для опроса обновлений в Telegram и отправки их в RabbitMQ
    - start(self): метод для запуска опроса
    - stop(self): метод для остановки опроса и закрытия соединения с RabbitMQ
    """

    def __init__(self, cfg: ConfigEnv):
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

    async def _poll(self):
        """
        Метод для опроса обновлений в Telegram и отправки их в RabbitMQ.
        """
        offset = 0
        while True:
            self.logger.info("Polling...")
            res = await self.TgClient.get_updates_in_objects(offset=offset, timeout=20)
            for u in res.result:
                offset = u.update_id + 1
                upd = UpdateObj.Schema().dump(u)
                await self.rabbitMQ.send_event(message=upd, routing_key="poller")
                await asyncio.sleep(get_update_timeout)

    async def start(self):
        """
        Метод для запуска опроса и открытия соединения с RabbitMQ.
        """
        self._task = asyncio.create_task(self._poll())
        await self.rabbitMQ.connect()

    async def stop(self):
        """
        Метод для остановки опроса и закрытия соединения с RabbitMQ.
        """
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
