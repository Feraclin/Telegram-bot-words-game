import asyncio
import signal

from poller import Poller
from app.web.config import config


if __name__ == "__main__":
    poller = Poller(cfg=config)
    loop = asyncio.new_event_loop()

    async def handle_sigterm(*args):
        for task_ in asyncio.all_tasks(loop=loop):
            task_.cancel()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda: asyncio.create_task(handle_sigterm()))

    try:
        loop.create_task(poller.start())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        tasks = asyncio.all_tasks(loop=loop)
        for task in tasks:
            task.cancel()
        loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        loop.run_until_complete(poller.stop())
        loop.close()
