import asyncio
import signal

from aiohttp.web_runner import AppRunner, TCPSite

from app.sender_app.sender import Sender
from app.worker_app.worker import Worker
from app.poller_app.poller import Poller
from app.web.config import config
from app.web.app import setup_app as aiohttp_app

app = aiohttp_app()


async def start_runner(runner: AppRunner) -> None:
    await runner.setup()
    site = TCPSite(runner, port=8090)
    await site.start()


async def handle_sigterm():
    raise KeyboardInterrupt()


def main():
    loop = asyncio.new_event_loop()
    runner = AppRunner(app)
    poller = Poller(cfg=config)
    worker = Worker(cfg=config)
    sender = Sender(cfg=config)

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(s, lambda: asyncio.create_task(handle_sigterm()))

    try:

        loop.create_task(poller.start())
        loop.create_task(worker.start())
        loop.create_task(sender.start())
        loop.create_task(start_runner(runner))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:

        loop.create_task(poller.stop())
        loop.create_task(worker.stop())
        loop.create_task(sender.stop())
        loop.create_task(runner.cleanup())

        for t in (tasks_ := asyncio.all_tasks(loop)):
            t.cancel()

        loop.run_until_complete(asyncio.gather(*tasks_, return_exceptions=True))


if __name__ == "__main__":
    main()
