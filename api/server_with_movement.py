from __future__ import annotations

from api import server
from api.movement_opportunity_route import install_movement_opportunity_route


app = server.app

install_movement_opportunity_route(app)
