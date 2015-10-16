import asyncio
import logging
import uuid
import msgpack
import re
from wolverine.module import MicroModule

logger = logging.getLogger(__name__)


class MicroRouter(MicroModule):

    def __init__(self):
        super(MicroRouter, self).__init__()
        self.name = 'router'
        self.service_handlers = {}
        self.client_handlers = {}
        self.clients = {}
        self.servers = {}
        self.async_req_queue = {}

    @asyncio.coroutine
    def stop(self):
        for service_name in list(self.servers.keys()):
            self.remove_server(service_name)
        for client_name in list(self.clients.keys()):
            self.remove_client(client_name)
        self.service_handlers = {}
        logger.info("router exited")

    def add_client(self, client, name):
        if name not in self.clients.keys():
            self.clients[name] = client
        else:
            logger.warning('not overriding a client with route ' + name)

    def remove_client(self, name):
        if name in self.clients.keys():
            try:
                self.clients[name].close()
            except Exception:
                logger.error('error closing client ' + name, exc_info=True)
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
        return self._handle_service(route, data)

    def _handle_service(self, route, data):
        result = {'data': [], 'errors': []}
        if isinstance(route, bytes):
            route = route.decode('utf-8')
        found = False
        for key, handlers in self.service_handlers.items():
            pattern = re.compile(key)
            if pattern.match(route):
                found = True
                for func in handlers:
                    try:
                        result['data'].append(func(data))
                    except Exception as ex:
                        result['errors'].append(ex)
        if not found:
            logger.info('no matching route for' + route)
        return result

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

    def send(self, data, route='.*', **options):
        future = options.pop('future', None)
        service = route.split('/')[0]
        if len(route.split('/')) < 2:
            route += '/'
        links = {x.split(':')[0]: x.split(':')[1] for x in self.clients.keys()}
        if service in links.keys():
            service_name = service + ':' + links[service]
            client = self.clients[service_name]
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
