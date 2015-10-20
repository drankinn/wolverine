import asyncio
from collections import OrderedDict
import logging
import uuid
import msgpack
import re
import types
from wolverine.module import MicroModule
from wolverine.module.controller.zhelpers import unpackb, packb, dump
from wolverine.module.service import ServiceMessage

logger = logging.getLogger(__name__)


class MicroRouter(MicroModule):

    def __init__(self):
        super(MicroRouter, self).__init__()
        self.name = 'router'
        self.service_handlers = OrderedDict()
        self.client_handlers = {}
        self.clients = {}
        self.servers = {}
        self.async_req_queue = {}

    def run(self):
        pass
        # self.sort_handlers()

    def sort_handlers(self):
        """sort the service handlers by key length from shortest to longest"""
        d = self.service_handlers.copy()
        sorted_handlers = OrderedDict(
            sorted(d.items(), key=lambda t: len(t[0])))
        self.service_handlers = sorted_handlers

    @asyncio.coroutine
    def stop(self):
        for service_name in list(self.servers.keys()):
            self.remove_server(service_name)
        for key in list(self.clients.keys()):
            yield from self.remove_client(key)
        self.service_handlers = {}
        logger.info("router exited")

    @asyncio.coroutine
    def add_client(self, client, name, **options):
        service_id = options.get('service_id', name)
        if service_id not in self.clients.keys():
            self.clients[service_id] = client
            up = yield from self.app.registry.register(name,
                                                       register_type='service',
                                                       **options)
            return up
        else:
            logger.warning('not overriding a client with route ' + name)
            return True

    def remove_client(self, name):
        if name in self.clients.keys():
            try:
                self.clients[name].close()
            except Exception:
                logger.error('error closing client ' + name, exc_info=True)
            try:
                yield from \
                    self.app.registry.deregister(name, register_type='service')
            except Exception:
                logger.error('failed to deregister client' + name,
                             exc_info=True)
            del self.clients[name]

    def add_server(self, name, service):
        if name not in self.servers.keys():
            self.servers[name] = service
            return True
        else:
            logger.warning('service ' + name + ' already registered')
            return False

    def remove_server(self, name):
        if name in self.servers.keys():
            self.servers[name].close()
            del self.servers[name]

    def add_service_handler(self, route, func):
        if route not in self.service_handlers.keys():
            self.service_handlers[route] = []
        self.service_handlers[route].append(func)

    def remove_service_handler(self, handler):
        if handler in self.service_handlers.keys():
            logger.info('removing all handlers for route ' + handler)
            logger.info('removed ' + str(len(self.service_handlers[handler])) +
                        ' handlers')
            del self.service_handlers[handler]

    def add_client_handler(self, route, func):
        if route not in self.client_handlers.keys():
            self.client_handlers[route] = []
        self.client_handlers[route].append(func)

    def remove_client_handler(self, handler):
        if handler in self.service_handlers.keys():
            logger.info('removing all handlers for route ' + handler)
            logger.info('removed ' + str(len(self.service_handlers[handler])) +
                        'handlers')
            del self.service_handlers[handler]

    def handle_service(self, data):
        route = data[-2]
        logger.info('handling data for route ' + route.decode('utf-8'))
        if logger.getEffectiveLevel() == logging.DEBUG:
            dump(data)
        return self._handle_service(route, data)

    def _handle_service(self, route, data):
        result = {'data': [], 'errors': []}
        if isinstance(route, bytes):
            route = route.decode('utf-8')
        found = False
        for key, handlers in self.service_handlers.items():
            pattern = re.compile(key)
            if pattern.match(route):
                req = unpackb(data[-1])
                found = True
                logger.info('handler: ' + key)
                for func in handlers:
                    try:
                        response = func(req)
                        if isinstance(response, types.GeneratorType):
                            response = yield from response
                        if isinstance(response, ServiceMessage):
                            if response.has_error():
                                result['errors'].append(response.errors)
                            response = response.data
                        if response is not None:
                            result['data'].append(response)
                    except Exception as ex:
                        logger.error('failed in handling data: ', exc_info=True)
                        logger.error('failed in data handling')
                        result['errors'].append("{0}".format(ex))
                break
        if not found:
            logger.info('no matching route for ' + route)

        packet = data[:-1] + [packb(result)]
        return packet

    def reply(self, data, name):
        if name in self.servers.keys():
            client = self.servers[name]
            client.write(data)
            yield from client.drain()

    def _send(self, data, client):
        client.write(data)
        yield from client.drain()
        data = yield from client.read()
        return data

    @asyncio.coroutine
    def _send_async(self, data, client, correlation_id, future):
        self.async_req_queue[correlation_id] = future
        client.write(data)
        yield from client.drain()
        return future

    def send(self, data, route='.*', version='1', **options):
        client = None
        future = options.pop('future', None)
        service = route.split('/')[0]
        if len(route.split('/')) < 2:
            route += '/'
        for c_client_id, c_client in self.clients.items():
            c_service, c_service_id = c_client_id.split(':')
            c_version = c_service_id.split('_')[1]
            if service == c_service and version == c_version:
                client = c_client
                break
        if client:
            correlation_id = str(uuid.uuid1())[:8]
            b_data = msgpack.packb(data, use_bin_type=True)
            packet = (bytes(correlation_id, encoding='utf-8'),
                      bytes(route, encoding='utf-8'),
                      b_data)
            if not future:
                response = yield from self._send(packet, client)
                response = msgpack.unpackb(response[-1])
            else:
                response = yield from self._send_async(packet, client,
                                                       correlation_id, future)
            return response
        else:
            return None
