import asyncio
import json
import logging
from uuid import uuid1
from aiohttp import web as aio_web
import functools
import msgpack
import os
from wolverine.module.controller.zmq import ZMQMicroController

logger = logging.getLogger(__name__)


class WebGatewayModule(ZMQMicroController):
    def __init__(self):
        super(WebGatewayModule, self).__init__()
        self.name = 'gateway'
        self.gw_port = 1986
        self.gateway_id = str(uuid1())[:8]
        self.default_settings = os.path.join(__path__[0],
                                             'settings.ini')
        self.http = aio_web.Application()
        self.http_handler = self.http.make_handler()

        self.client_services = {}

    def register_app(self, app):
        self.app = app
        app.config.read(self.default_settings)
        self.bind_service_data()

    def run(self):
        logger.info('running the web gateway')
        self.srv = self.app.loop.create_server(
            self.http_handler, '0.0.0.0', 8080)
        self.app.loop.create_task(self.srv)
        super(WebGatewayModule, self).run()
        self.http.router.add_route('GET', '/', self.hello)
        self.http.router.add_route('GET', '/service', self.get_services)
        self.http.router.add_route('GET', '/service/{service}',
                                   self.get_service_routes)

    def stop(self):
        yield from self.http_handler.finish_connections(1.0)
        yield from self.http.finish()

    def bind_service_data(self):
        @self.data('service:', recurse=True)
        def service_data(data):
            service_names = []
            for d in data:
                service_id = self.gateway_id + '_' + d['version']
                service_name = d['name'] + ':' + service_id
                service_names.append(service_name)
                if service_name not in self.app.router.clients.keys():
                    self.create_client(d)
                    if d['name'] not in self.client_services:
                        self.client_services[d['name']] = {}
                    self.client_services[d['name']][service_name] = d

            removed = list(set(self.app.router.clients.keys()) -
                           set(service_names))
            for service_name in removed:
                logger.debug('removing client for service ' + service_name)
                del self.client_services[list(service_name.split(':'))[0]][
                    service_name]
                self.app.loop.create_task(
                    self.app.router.remove_client(service_name))

    def create_client(self, data):
        service_id = self.gateway_id + '_' + data['version']
        service_name = data['name'] + ':' + service_id
        self.gw_port += 1
        options = {
            'service_id': service_id,
            'port': self.gw_port,
            'tags': ['version:' + data['version']],
            'async': True
        }
        route = data['routes'][0]
        self.app.loop.create_task(
            self.connect_client(data['name'],
                                functools.partial(
                                    self.callback, route, service_name,
                                    data['version']),
                                **options))
        logger.debug('data: ' + str(data))

    def callback(self, route, service_name, version):
        def read_data(future):
            data = future.result()
            logger.info('response: ' + str(data))

        def client_done(results, service_name):
            try:
                done, pending = yield from results
                logger.error('DONE: ' + str(len(done)))
                logger.error('PENDING:' + str(len(pending)))
            except Exception:
                logger.error('an error')
            logger.debug('service ' + service_name + ' is done')

        calls = []
        data = {'message': service_name}
        try:
            up = True
            while up:
                yield from asyncio.sleep(1)
                future = asyncio.Future()
                logger.debug('sending ' + str(data) + ' to ' + route +
                             ' version ' + version)
                up = yield from self.app.router.send(data, route,
                                                     version=version,
                                                     future=future)
                if up:
                    logger.debug('sent success')
                    future.add_done_callback(read_data)
                    calls.append(future)
                else:
                    logger.debug('sent failed')
                    future.cancel()
            self.app.loop.create_task(
                client_done(
                    asyncio.wait(calls, timeout=10), service_name))
        except Exception:
            pass
        return

    @asyncio.coroutine
    def get_services(self, request):
        services = self.client_services
        data = json.dumps(services)
        return aio_web.Response(text=data)

    @asyncio.coroutine
    def get_service_routes(self, request):
        service_name = request.match_info['service']
        servers = self.client_services.get(service_name, {})
        data = json.dumps(servers)
        return aio_web.Response(text=data)

    @asyncio.coroutine
    def hello(self, request):
        return aio_web.Response(body=b"Hello, world")
