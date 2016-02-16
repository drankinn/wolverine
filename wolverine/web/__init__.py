import logging
import os
from aiohttp.web import Application
from .jinja import *
from wolverine.module import MicroModule

__all__ = (jinja.__all__,)

logger = logging.getLogger(__name__)


class WebModule(MicroModule, Application):

    def __init__(self):
        super().__init__()
        self.name = 'web'
        self.default_settings = os.path.join(__path__[0],
                                             'settings.ini')

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)

    def read_config(self):
        config = self.app.config[self.name.upper()]
        self.http_host = config.get('HTTP_HOST')
        self.http_port = config.get('HTTP_PORT')
        self.static_folder = config.get('STATIC', '/tmp/')

    def run(self):
        logger.info('running the web console')
        self.read_config()
        self.router.add_static('/static', self.static_folder)

    def create_server(self):
        self.http_handler = self.make_handler()
        self.srv = self.app.loop.create_server(
            self.http_handler, self.http_host, self.http_port)
        self.app.loop.create_task(self.srv)

    def stop_server(self):
        yield from self.http_handler.finish_connections(1.0)
        yield from self.shutdown()

    def add_route(self, *args, **kwargs):
        return self.router.add_route(*args, **kwargs)




