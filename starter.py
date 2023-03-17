import asyncio
import platform
import signal


def starter(start_tasks: list[asyncio.coroutines], stop_tasks: list[asyncio.coroutines]):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    async def handle_sigterm():
        raise KeyboardInterrupt()

    if platform.system() == "Linux":
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(s, lambda: asyncio.create_task(handle_sigterm()))

    try:

        for t in start_tasks:
            loop.create_task(t())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            stop_tasks = [loop.create_task(t()) for t in stop_tasks]
            loop.run_until_complete(asyncio.gather(*stop_tasks))
        except KeyboardInterrupt:
            pass
        finally:
            if not loop.is_closed():
                loop.close()
