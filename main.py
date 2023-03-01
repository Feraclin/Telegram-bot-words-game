import asyncio
import os

from aiohttp.web_runner import AppRunner, TCPSite

from app.worker_app.worker import Worker
from app.poller_app.poller import Poller
from app.web.config import config
from app.web.app import setup_app as aiohttp_app
from aiohttp.web import _run_app

app = aiohttp_app(config_path=os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "config.yml"))


if __name__ == "__main__":

    # runner = AppRunner(app)
    # site = TCPSite(runner, "localhost", 8080)
    poller = Poller(cfg=config)
    worker = Worker(cfg=config)

    loop = asyncio.new_event_loop()
    try:
        loop.create_task(poller.start())
        loop.create_task(worker.start())
        # loop.create_task(runner.setup())
        # loop.create_task(site.start())
        loop.create_task(_run_app(app, host="localhost", port=8080))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.create_task(poller.stop())
        loop.create_task(worker.stop())
        # loop.create_task(runner.cleanup())
        for t in (tasks_ := asyncio.all_tasks(loop)):
            t.cancel()
        loop.run_until_complete(asyncio.gather(*tasks_, return_exceptions=True))

