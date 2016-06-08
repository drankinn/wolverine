import ast
import json
import logging

import asyncio

from aiohttp.web import Response
from wolverine.module import MicroModule

logger = logging.getLogger(__name__)


class GatewayWebModule(MicroModule):

    def __init__(self):
        super().__init__()
        self.app = None
        self.tasks = []

    def init(self):
        logger.info('Gateway web router run')
        self.app.web.add_route('GET', '/', self.hello)
        self.app.web.add_route('GET', '/service', self.get_services)
        self.app.web.add_route('GET', '/service/{service}',
                               self.get_service_routes)
        self.app.web.add_route('POST',
                               '/service/{service}/{route}/{version}',
                               self.post_to_route)

    @asyncio.coroutine
    def get_services(self, request):
        services = self.app.gateway.client_services
        data = json.dumps(services)
        return Response(text=data)

    @asyncio.coroutine
    def get_service_routes(self, request):
        service_name = request.match_info['service']
        servers = self.app.gateway.client_services.get(service_name, {})
        data = json.dumps(servers)
        return Response(text=data)

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
            self.tasks.append(future)
            service_request = yield from self.app.router.send(data, route,
                                                              version=version,
                                                              future=future)
            service_data = yield from service_request
            body = bytes(str(service_data), encoding='utf-8')
        except Exception as ex:
            logger.error('error reading web console request', exc_info=True)
            data = {'error': 'invalid request'}
            body = bytes(str(data), encoding='utf-8')
        return Response(body=body)

    @asyncio.coroutine
    def hello(self, request):
        return Response(body=b"Hello, world")

