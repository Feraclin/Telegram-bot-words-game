import typing

from app.admin.views import AdminCurrentView
from app.words_game.views import GameSessionView, PlayerView, CityView

if typing.TYPE_CHECKING:
    from app.web.app import Application


def setup_routes(app: "Application"):
    app.router.add_view("/game_sessions", GameSessionView)
    app.router.add_view("/players", PlayerView)
    app.router.add_view("/cities", CityView)
