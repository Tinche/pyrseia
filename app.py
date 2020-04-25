from tests.calculator import Calculator

from pyrseia import server
from pyrseia.starlette import create_starlette_app
from starlette.requests import Request

app = create_starlette_app(server(Calculator, Request))
