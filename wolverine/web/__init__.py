import ast
import asyncio
import json
import logging
import os
from aiohttp import web as aio_web
from wolverine.module import MicroModule

logger = logging.getLogger(__name__)


class WebModule(MicroModule):

    def __init__(self):
        super(WebModule, self).__init__()
        self.name = 'web_console'
        self.default_settings = os.path.join(__path__[0],
                                             'settings.ini')
        self.http = aio_web.Application()
        self.http_handler = self.http.make_handler()
        self.http_tasks = []

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)

    def read_config(self):
        config = self.app.config[self.name.upper()]
        self.http_host = config.get('HTTP_HOST')
        self.http_port = config.get('HTTP_PORT')

    def run(self):
        logger.info('running the web console')
        self.read_config()
        self.srv = self.app.loop.create_server(
            self.http_handler, self.http_host, self.http_port)
        self.app.loop.create_task(self.srv)
        self.http.router.add_route('GET', '/', self.hello)
        self.http.router.add_route('GET', '/service', self.get_services)
        self.http.router.add_route('GET', '/service/{service}',
                                   self.get_service_routes)
        self.http.router.add_route('POST',
                                   '/service/{service}'
                                   '/{route}/{version}',
                                   self.post_to_route)

    def stop(self):
        yield from self.http_handler.finish_connections(1.0)
        yield from self.http.finish()

    @asyncio.coroutine
    def get_services(self, request):
        services = self.app.gateway.client_services
        data = json.dumps(services)
        return aio_web.Response(text=data)

    @asyncio.coroutine
    def get_service_routes(self, request):
        service_name = request.match_info['service']
        servers = self.app.gateway.client_services.get(service_name, {})
        data = json.dumps(servers)
        return aio_web.Response(text=data)

    @asyncio.coroutine
    def post_to_route(self, request):
        try:
            service_name = request.match_info['service']
            route_name = request.match_info['route']
            route = service_name + '/' + route_name
            version = request.match_info['version']
            data_str = yield from request.content.read()
            data = ast.literal_eval(data_str.decode('utf-8'))
            future = asyncio.Future()
            self.http_tasks.append(future)
            service_request = yield from self.app.router.send(data, route,
                                                              version=version,
                                                              future=future)
            service_data = yield from service_request
            body = bytes(str(service_data), encoding='utf-8')
        except Exception as ex:
            logger.error('error reading web console request', exc_info=True)
            data = {'error': 'invalid request'}
            body = bytes(str(data), encoding='utf-8')
        return aio_web.Response(body=body)

    @asyncio.coroutine
    def hello(self, request):
        return aio_web.Response(body=b"Hello, world")
