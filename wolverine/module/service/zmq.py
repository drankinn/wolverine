import asyncio
from asyncio.futures import InvalidStateError
import logging
from uuid import uuid1
import aiozmq
import msgpack
import types
import zmq
from . import MicroService
from .zhelpers import event_description

logger = logging.getLogger(__name__)


class ZMQMicroService(MicroService):
    bind_types = {
        "observer": zmq.ROUTER,
        'provider': zmq.DEALER
    }

    def __init__(self):
        super(ZMQMicroService, self).__init__()

    @asyncio.coroutine
    def stop(self):
        logger.info('closing module ' + self.name)
        for key in self.router.clients.keys():
            try:
                yield from \
                    self.app.registry.deregister(key, register_type='service')
            except Exception:
                logger.error('failed to deregister client' + key,
                             exc_info=True)

    def connect_client(self, name, func, **options):
        port = options.pop('port', '9210')
        async = options.pop('async', False)
        address = options.pop('address', 'tcp://127.0.0.1')
        uri = address + ':' + str(port)
        logger.info('client connect for service: ' + name)
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
            logger.error('failed to bind zqm socket for dealer ' +
                         service_name,
                         exc_info=True)
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
            logger.info('service ' + name +
                        ' registered with consul with id ' +
                        service_name)
        else:
            logger.error('failed to register client ' + service_name +
                         ' with consul... ')
            logger.error('shutting down zqm dealer ' + name)
            client.close()
            return
        if async:
            self.app.loop.create_task(self.connect_client_handler(client))
        try:
            response = func()
            if isinstance(response, types.GeneratorType):
                yield from response
        except aiozmq.ZmqStreamClosed:
            logger.info('stream closed')
        except Exception:
            logger.error('failed in client callback', exc_info=True)
            logger.error('client closing')
            client.close()

    def connect_client_handler(self, client):
        while True:
            response = yield from client.read()
            correlation_id = response[0].decode('utf-8')
            if correlation_id in self.router.async_req_queue:
                future = self.router.async_req_queue[correlation_id]
                if not future.cancelled():
                    data = msgpack.unpackb(response[-1], encoding='utf-8')
                    future.set_result(data)

    @asyncio.coroutine
    def connect_service(self, name, func, **options):
        route = name + '/' + options.pop('route', ".*")
        self.router.add_service_handler(route, func)
        bind_type = options.pop('bind_type', zmq.ROUTER)
        listen_type = options.pop('listen_type', 'kv')

        @self.app.registry.listen(name, listen_type=listen_type,
                                  singleton=True, **options)
        def discover_service(data):

            try:
                data = self.app.registry.unwrap(data, listen_type)
                if data and 'passing' in data:
                    new = list(set(data['passing'].keys()) -
                               set(self.router.servers.keys()))
                    removed = list(set(self.router.servers.keys()) -
                                   set(data['passing'].keys()))
                    logger.info('\n' +
                                '-' * 20 +
                                '\n     discovery\n' +
                                'service:' + name + ', route:' + route +
                                '\nnew: ' + str(len(new)) +
                                ' removed: ' + str(len(removed)) +
                                '\n' +
                                '-' * 20)

                    for key in new:
                        logger.info('registering new handler for ' + key)
                        s = data['passing'][key]
                        address = s.pop('Address', '')
                        port = s.pop('Port', '')
                        uri = address + ':' + str(port)
                        service = yield from \
                            self.connect_service_handler(key, uri, bind_type)
                        self.router.add_server(key, service)
                    for key in removed:
                        logger.info('removed handler for ' + key)
                        self.router.remove_server(key)
            except Exception as e:
                logger.error('service binding error:', exc_info=True)

    @asyncio.coroutine
    def connect_service_handler(self, service_name, address, bind_type):
        server = yield from aiozmq.create_zmq_stream(bind_type)
        yield from server.transport.enable_monitor()
        yield from server.transport.connect(address)
        logger.info('zmq stream ' + service_name + ' registered at ' + address)
        self.app.loop.create_task(self.monitor_stream(service_name, server))

        def run():
            alive = True
            while alive:
                try:
                    work = yield from server.read()
                    self.app.loop.create_task(
                        self.handle_service_data(work, service_name))
                except aiozmq.ZmqStreamClosed:
                    logger.info('zmq stream ' + service_name + ' closed')
                    alive = False
                except Exception:
                    logger.error(service_name + ' work halted', exc_info=True)

        self.app.loop.create_task(run())
        return server

    @asyncio.coroutine
    def monitor_stream(self, name, stream):
        logger.debug('monitoring stream' + name)
        try:
            while True:
                event = yield from stream.read_event()
                event = event_description(event.event)
                logger.debug('stream ' + name + ' event:' + event)
        except aiozmq.ZmqStreamClosed:
            logger.debug('monitoring closed for stream ' + name)

    @asyncio.coroutine
    def handle_service_data(self, d, service_name):
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
            logger.info('stream closed')
        except InvalidStateError:
            logger.info('invalid state')
        except Exception:
            logger.error('failure while handling data',
                         extra={'name': service_name,
                                'data': d},
                         exc_info=True)
        finally:
            if state != 2:
                logger.error('service handler reached invalid state',
                             extra={'state': 2})
