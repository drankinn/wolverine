import asyncio
from asyncio.futures import InvalidStateError
from uuid import uuid1
import aiozmq
import types
import zmq
from wolverine.modules import MicroModule
from wolverine.modules.zhelpers import event_description


class ZMQMicroModule(MicroModule):
    bind_types = {
        "observer": zmq.ROUTER,
        'provider': zmq.DEALER
    }

    def __init__(self):
        super(ZMQMicroModule, self).__init__()
        # self.streams = {}

    def run(self):
        print('running module', self.name)

    @asyncio.coroutine
    def exit(self):
        print('closing module', self.name)
        for key in self.router.clients.keys():
            yield from self.app.registry.deregister(key,
                                                    register_type='service')
        self.router.exit()

    def _connect_client(self, name, func, **options):
        port = options.pop('port', '9210')
        address = options.pop('address', 'tcp://127.0.0.1')
        uri = address + ':' + str(port)
        print("-" * 20)
        print('client connect for service:', name)
        service_id = str(uuid1())[:7]
        service_name = name + ':' + service_id
        try:
            client = yield from aiozmq.create_zmq_stream(
                zmq.DEALER)
            # self.streams['client:' + service_name] = client
            yield from client.transport.enable_monitor()
            self.app.loop.create_task(
                self.monitor_stream(name, client))
            yield from client.transport.bind(uri)
            self.router.add_client(client, service_name)
        except Exception as ex:
            print('failed to bind zqm socket for dealer', service_name)
            print(ex)
            return

        service_opts = {
            'service_id': service_name,
            'address': address,
            'port': int(port),
            'tags': ['DEALER_BIND'],
            'check_ttl': '12s',
            'ttl_ping': 10

        }
        up = yield from self.app.registry.register(name,
                                                   register_type='service',
                                                   **service_opts)
        if up:
            print('service ping registered with consul')
            # health = yield from self.app.registry.agent.checks()
            # print(health)
        else:
            print('failed to register with consul... ')
            print('shutting down zqm dealer', name)
            client.close()
            return
        try:
            response = func()
            if isinstance(response, types.GeneratorType):
                yield from response
        except aiozmq.ZmqStreamClosed:
            print('stream closed')
        except Exception as e:
            print(e)
            print('client closing')
            # client.close()

    @asyncio.coroutine
    def _connect_service(self, name, func, **options):
        route = name + '/' + options.pop('route', ".*")
        self.router.add_service_handler(route, func)
        bind_type = options.pop('bind_type', zmq.ROUTER)
        listen_type = options.pop('listen_type', 'kv')

        @self.app.registry.listen(name, listen_type=listen_type, **options)
        def discover_service(data):
            print("-" * 20)
            print('service:', name)
            print("route:", route)
            try:
                data = self.app.registry.unwrap(data, listen_type)
                if data and 'passing' in data:
                    new = list(set(data['passing'].keys()) -
                               set(self.router.servers.keys()))
                    removed = list(set(self.router.servers.keys()) -
                                   set(data['passing'].keys()))
                    for key in new:
                        s = data['passing'][key]
                        address = s.pop('Address', '')
                        port = s.pop('Port', '')
                        uri = address + ':' + str(port)
                        service = yield from \
                            self.zmq_service(key, uri, bind_type)
                        self.router.add_server(key, service)
                    for key in removed:
                        self.router.remove_server(key)
            except Exception as e:
                print('service binding error:', e)

    @asyncio.coroutine
    def zmq_service(self, service_name, address, bind_type):
        server = yield from aiozmq.create_zmq_stream(bind_type)
        yield from server.transport.enable_monitor()
        yield from server.transport.connect(address)
        print('zmq stream ', bind_type, 'registered at', address)
        self.app.loop.create_task(self.monitor_stream(service_name, server))

        def run():
            alive = True
            while alive:
                try:
                    work = yield from server.read()
                    yield from self.handle_data(work, service_name)
                except aiozmq.ZmqStreamClosed:
                    print("zmq stream", bind_type, 'closed')
                    alive = False
                except Exception as ex:
                    print(service_name, 'work halted for:', ex)

        self.app.loop.create_task(run())
        return server

    @asyncio.coroutine
    def monitor_stream(self, name, stream):
        print('monitoring stream', name)
        try:
            while True:
                event = yield from stream.read_event()
                event = event_description(event.event)
                print('stream', name, 'event:', event)
        except aiozmq.ZmqStreamClosed:
            print('monitoring closed for stream ', name)

    @asyncio.coroutine
    def handle_data(self, d, service_name):
        state = 0
        try:
            responses = self.router.handle_service(d)
            state = 1
            for response in responses['data']:
                if isinstance(response, types.GeneratorType):
                    response = yield from response
                if response:
                    ret = self.router.reply(response, service_name)
                    if isinstance(ret, types.GeneratorType):
                        yield from ret
                    state = 2
            for error in responses['errors']:
                if isinstance(error, types.GeneratorType):
                    error = yield from error
                if error:
                    state = -1
                    self.router.reply(error, service_name)
                    state = -2
        except aiozmq.ZmqStreamClosed:
            print('stream closed')
        except InvalidStateError:
            print('invalid state')
        except Exception as e:
            print(e)
        finally:
            print('state: ', state)
