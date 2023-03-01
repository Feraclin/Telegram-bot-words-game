import asyncio

from dotenv import find_dotenv, dotenv_values

from app.store.tg_api.client import TgClient

found_dotenv = find_dotenv(filename='.env')
config_env = dotenv_values(found_dotenv)
token_tg = config_env['BOT_TOKEN_TG']


class EchoBot:
    flag: bool = True
    task_: asyncio.Task | None = None

    async def run_echo(self, token: str = token_tg):
        c = TgClient(token=token)

        offset = 0
        while self.flag:
            res = await c.get_updates_in_objects(offset=offset, timeout=10)
            for item in res.result:
                print(item)
                offset = item.update_id + 1
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
        loop.create_task(echo.start(token=token_tg))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        for task in asyncio.all_tasks(loop):
            task.cancel()
        loop.run_until_complete(echo.stop())
