import ast
import asyncio
from asyncio.futures import InvalidStateError
import logging
from uuid import uuid1
import aiozmq
import msgpack
import types
import zmq
from . import MicroController
from .zhelpers import event_description, unpack

logger = logging.getLogger(__name__)


class ZMQMicroController(MicroController):
    bind_types = {
        "observer": zmq.ROUTER,
        'provider': zmq.DEALER
    }

    def __init__(self):
        super(ZMQMicroController, self).__init__()

    @asyncio.coroutine
    def stop(self):
        logger.info('closing module ' + self.name)

    def connect_client(self, name, func, **options):
        port = options.pop('port', '1800')
        tags = options.pop('tags', ['version:1'])
        version = '1'
        for tag in tags:
            tag_name = tag.split(':')[0]
            if tag_name == 'version' and len(tag.split(':')) > 0:
                version = tag.split(':')[1]
        async = options.pop('async', False)
        address = options.pop('address', 'tcp://0.0.0.0')
        uri = address + ':' + str(port)
        logger.info('client connect for service: ' + name)
        default_service_id = str(uuid1())[:8] + '_' + version
        service_id = options.pop('service_id', default_service_id)
        service_name = name + ':' + service_id
        check_ttl = options.pop('ttl', 12)
        ttl_ping = options.pop('ttl_ping', 10)
        try:
            client = yield from aiozmq.create_zmq_stream(
                zmq.DEALER)
            # self.streams['client:' + service_name] = client
            yield from client.transport.enable_monitor()
            self.app.loop.create_task(
                self.monitor_stream(name, client))
            yield from client.transport.bind(uri)

        except Exception as ex:
            logger.error('failed to bind zqm socket for dealer ' +
                         service_name,
                         exc_info=True)
            return

        service_opts = {
            'service_id': service_name,
            'address': address,
            'port': int(port),
            'tags': tags,
            'check_ttl': str(check_ttl) + 's',
            'ttl_ping': int(ttl_ping)

        }
        up = yield from self.app.router.add_client(client, name,
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
        try:
            while True:
                response = yield from client.read()
                correlation_id = response[0].decode('utf-8')
                if correlation_id in self.app.router.async_req_queue:
                    future = self.app.router.async_req_queue[correlation_id]
                    if not future.cancelled():
                        data = msgpack.unpackb(response[-1], encoding='utf-8')
                        if not future.done():
                            future.set_result(data)
        except aiozmq.ZmqStreamClosed:
            logger.info('closing client read buffer')

    @asyncio.coroutine
    def connect_data(self, name, func, **options):
        listen_type = options.pop('listen_type', 'kv')

        @self.app.registry.listen(name, listen_type=listen_type,
                                  **options)
        def discover_data(packet):
            try:
                index, data_set = packet
                logger.debug('data set: ' + str(data_set))
                if data_set is None:
                    data_set = []
                params = []
                for data in data_set:
                    value = data['Value']
                    if isinstance(value, bytes):
                        value = unpack(value)
                    value = ast.literal_eval(value)
                    params.append(value)
                func(params)
            except Exception:
                logger.error('kv data handling exception', exc_info=True)

    @asyncio.coroutine
    def connect_service(self, name, service):
        try:
            options = service.options
        except Exception:
            options = {}
        try:
            options['tag'] = 'version:' + str(service.version)
        except Exception:
            options['tag'] = 'version:1'
        bind_type = options.pop('bind_type', zmq.ROUTER)
        listen_type = options.pop('listen_type', 'health')

        @self.app.registry.listen(name, listen_type=listen_type,
                                  singleton=True, **options)
        def discover_service(data):

            try:
                data = self.app.registry.unwrap(data, listen_type)
                if data and 'passing' in data:
                    new = list(set(data['passing'].keys()) -
                               set(self.app.router.servers.keys()))
                    removed = list(set(self.app.router.servers.keys()) -
                                   set(data['passing'].keys()))
                    logger.info('\n' +
                                '-' * 20 +
                                '\n     discovery\n' +
                                'service:' + name +
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
                            self.bind_service(key, uri, bind_type)
                        self.app.router.add_server(key, service)
                    for key in removed:
                        logger.info('removed handler for ' + key)
                        self.app.router.remove_server(key)
            except Exception as e:
                logger.error('service binding error:', exc_info=True)

    @asyncio.coroutine
    def bind_service(self, service_name, address, bind_type):
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
                    pass
                #   logger.error(service_name + ' work halted', exc_info=True)

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
            state = 1
            response = self.app.router.handle_service(d)
            if isinstance(response, types.GeneratorType):
                response = yield from response
            ret = self.app.router.reply(response, service_name)
            if isinstance(ret, types.GeneratorType):
                yield from ret
            state = 2
        except aiozmq.ZmqStreamClosed:
            logger.info('stream closed')
        except InvalidStateError:
            logger.info('invalid state')
        except Exception:
            logger.error('failure while handling data',
                         extra={'service_name': service_name,
                                'data': d},
                         exc_info=True)
        finally:
            if state != 2:
                logger.error('service handler reached invalid state',
                             extra={'state': 2})
