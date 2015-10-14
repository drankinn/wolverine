import asyncio
import re


class MicroRouter(object):

    def __init__(self):
        self.service_handlers = {}
        self.client_handlers = {}
        self.clients = {}
        self.servers = {}

    def exit(self):
        for service_name in list(self.servers.keys()):
            self.remove_server(service_name)
        for client_name in list(self.clients.keys()):
            self.remove_client(client_name)
        self.service_handlers = {}
        print("router exited")

    def add_client(self, client, name):
        if name not in self.clients.keys():
            self.clients[name] = client
        else:
            print('warning: not overriding a client with route', name)

    def remove_client(self, name):
        if name in self.clients.keys():
            self.clients[name].close()
            del self.clients[name]

    def add_server(self, name, service):
        if name not in self.servers.keys():
            self.servers[name] = service
            return True
        else:
            print('service', name, 'already registered')
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
            print('removing all handlers for route ', handler)
            print('removed', len(self.service_handlers[handler]), 'handlers')
            del self.service_handlers[handler]

    def add_client_handler(self, route, func):
        if route not in self.client_handlers.keys():
            self.client_handlers[route] = []
        self.client_handlers[route].append(func)

    def remove_client_handler(self, handler):
        if handler in self.service_handlers.keys():
            print('removing all handlers for route ', handler)
            print('removed', len(self.service_handlers[handler]), 'handlers')
            del self.service_handlers[handler]

    def handle_service(self, data):
        route = '.*'
        if len(data) > 0:
            route = data[1]
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
            print('no matching route for', route)
        return result

    def reply(self, data, name):
        if name in self.servers.keys():
            client = self.servers[name]
            client.write(data)
            yield from client.drain()

    def send(self, data, route='.*', **options):
        async = options.pop('async', False)
        service = route.split('/')[0]
        if len(route.split('/')) < 2:
            route += '/'
        links = {x.split(':')[0]: x.split(':')[1] for x in self.clients.keys()}
        if service in links.keys():
            service_name = service + ':' + links[service]
            client = self.clients[service_name]
            data = (bytes(route, encoding='utf-8'),) + data
            client.write(data)
            yield from client.drain()
            if not async:
                # need to make this async anyways and give them back a future
                try:
                    data = yield from client.read()
                    return data
                except Exception as e:
                    print(e)
