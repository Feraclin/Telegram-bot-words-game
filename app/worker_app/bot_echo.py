import asyncio
import logging

from app.store.tg_api.client import TgClient
from app.web.config import config


class EchoBot:
    flag: bool = True
    task_: asyncio.Task | None = None
    logger: logging.Logger = logging.getLogger(__name__)

    async def run_echo(self, token: str = token_tg):
        c = TgClient(token=token)

        offset = 0
        while self.flag:
            res = await c.get_updates_in_objects(offset=offset, timeout=10)
            for item in res.result:
                offset = item.update_id + 1
                self.logger.info(f'New update: {item}')
                if item.message:
                    if item.message.text == 'stop':
                        loop.stop()
                    await c.send_message(item.message.chat.id, item.message.text)
                elif item.callback_query:
                    await c.send_message(item.callback_query.from_.id, item.callback_query.from_.first_name)

    async def start(self, token: str = token_tg):
        self.task_ = asyncio.create_task(self.run_echo(token=token))

    async def stop(self):
        self.flag = False
        if self.task_:
            self.task_.cancel()


if __name__ == '__main__':
    echo = EchoBot()
    loop = asyncio.new_event_loop()
    try:
        loop.create_task(echo.start(token=config.tg_token.tg_token))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(echo.stop())
