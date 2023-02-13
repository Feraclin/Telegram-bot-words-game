import os

from app.web.app import setup_app as aiohttp_app
from aiohttp.web import run_app


app = aiohttp_app(config_path=os.path.join(
                os.path.dirname(os.path.realpath(__file__)), "config.yml"))


if __name__ == "__main__":
    run_app(app)
