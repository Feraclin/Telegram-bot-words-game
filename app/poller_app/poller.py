import asyncio
import logging
from asyncio import Task

from constnant import get_update_timeout
from app.store.rabbitMQ.rabbitMQ import RabbitMQ
from app.store.tg_api.client import TgClient
from app.store.tg_api.schemes import UpdateObj
from app.web.config import ConfigEnv


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
        """
        Метод для опроса обновлений в Telegram и отправки их в RabbitMQ.
        """
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
        """
        Метод для запуска опроса и открытия соединения с RabbitMQ.
        """
        self._task = asyncio.create_task(self._poll())
        await self.rabbitMQ.connect()

    async def stop(self):
        """
        Метод для остановки опроса и закрытия соединения с RabbitMQ.
        """
        self.is_stop = True
        self.timeout = 1
        await self.rabbitMQ.disconnect()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
