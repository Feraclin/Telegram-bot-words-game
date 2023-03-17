from aiohttp.web_runner import AppRunner, TCPSite

from app.sender_app.sender import Sender
from app.worker_app.worker import Worker
from app.poller_app.poller import Poller
from app.web.config import config
from app.web.app import setup_app as aiohttp_app
from starter import starter

app = aiohttp_app()


class CustomAppRunner:
    def __init__(self, app_):
        self.runner = AppRunner(app_)

    async def start(self):
        await self.runner.setup()
        site = TCPSite(self.runner, port=8090)
        await site.start()

    async def stop(self):
        await self.runner.cleanup()


if __name__ == "__main__":

    runner = CustomAppRunner(app)
    poller = Poller(cfg=config)
    worker = Worker(cfg=config)
    sender = Sender(cfg=config)
    starter(start_tasks=[poller.start, worker.start, sender.start, runner.start],
            stop_tasks=[poller.stop, worker.stop, sender.stop, runner.stop])
