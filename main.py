import asyncio
import signal

from aiohttp.web_runner import AppRunner, TCPSite

from app.sender.sender import Sender
from app.worker_app.worker import Worker
from app.poller_app.poller import Poller
from app.web.config import config
from app.web.app import setup_app as aiohttp_app

app = aiohttp_app()


if __name__ == "__main__":
    runner = AppRunner(app)
    poller = Poller(cfg=config)
    worker = Worker(cfg=config)
    sender = Sender(cfg=config)

    async def start_runner(run: AppRunner) -> None:
        await run.setup()
        site = TCPSite(run, "localhost", 8090)
        await site.start()

    def stop_all(loop):
        loop.stop()
        loop.create_task(poller.stop())
        loop.create_task(worker.stop())
        loop.create_task(sender.stop())
        loop.create_task(runner.cleanup())
        tasks_ = asyncio.all_tasks(loop)
        for t in tasks_:
            t.cancel()
        loop.run_until_complete(asyncio.gather(*tasks_, return_exceptions=True))

    loop = asyncio.new_event_loop()
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
        stop_all(loop)
        loop.close()

    for signame in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(getattr(signal, signame), lambda: asyncio.create_task(stop_all(loop)))
