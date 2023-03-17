from aiohttp.web import run_app
from app.web.app import setup_app as aiohttp_app

app = aiohttp_app()

if __name__ == '__main__':
    run_app(app, port=8000)
