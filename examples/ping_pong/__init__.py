import asyncio
import logging
from uuid import uuid1
import functools
import os
from examples.ping_pong.service import PingPongService
from wolverine.module.controller.zmq import ZMQMicroController

logger = logging.getLogger(__name__)


def ping_pong(mode, options):
    """Run a ping and pong service across a zmq dealer/router device

    :param mode: either client or server
    :param port: any arbitrary port.  must not be in use if running the client
    :return:  yo momma
    """
    from wolverine import MicroApp
    loop = asyncio.get_event_loop()
    config_file = os.path.join(__path__[0], 'settings.ini')
    app = MicroApp(loop=loop, config_file=config_file)

    if 'ping' == mode:
        app.register_module(
            ping_client(int(options.port),
                        delay=int(options.delay),
                        times=int(options.times),
                        routing=options.routing,
                        async=options.async,
                        version=options.version))

    if 'pong' == mode:
        app.register_module(
            pong_controller(app, delay=int(options.delay),
                            routing=options.routing,
                            version=options.version))
    if 'pong2' == mode:
        app.register_module(
            pong_server(delay=int(options.delay),
                        routing=options.routing))
    if 'gateway' == mode:
        app.register_module(gateway())
    app.run()


def gateway():
    module = ZMQMicroController()
    gateway_id = str(uuid1())[:8]
    global gw_port
    gw_port = 1986

    @module.data('service:', recurse=True)
    def ping_pong_data(data):
        service_names = []
        for d in data:
            service_id = gateway_id + '_' + d['version']
            service_name = d['name'] + ':' + service_id
            service_names.append(service_name)
            if service_name not in module.app.router.clients.keys():
                create_client(d)
        removed = list(set(module.app.router.clients.keys()) -
                       set(service_names))
        for service_name in removed:
            logger.debug('removing client for service ' + service_name)
            module.app.loop.create_task(
                module.app.router.remove_client(service_name))

    def create_client(data):
        global gw_port
        service_id = gateway_id + '_' + data['version']
        service_name = data['name'] + ':' + service_id
        gw_port += 1
        options = {
            'service_id': service_id,
            'port': gw_port,
            'tags': ['version:' + data['version']],
            'async': True
        }
        route = data['routes'][0]
        module.app.loop.create_task(
            module.connect_client(data['name'],
                                  functools.partial(
                                      callback, route, service_name,
                                      data['version']),
                                  **options))
        logger.debug('data: ' + str(data))

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

    def callback(route, service_name, version):
        calls = []
        data = {'message': service_name}
        try:
            up = True
            while up:
                yield from asyncio.sleep(1)
                future = asyncio.Future()
                logger.debug('sending ' + str(data) + ' to ' + route +
                             ' version ' + version)
                up = yield from module.app.router.send(data, route, version=version,
                                                  future=future)
                if up:
                    logger.debug('sent success')
                    future.add_done_callback(read_data)
                    calls.append(future)
                else:
                    logger.debug('sent failed')
                    future.cancel()
            module.app.loop.create_task(
                client_done(
                    asyncio.wait(calls, timeout=10), service_name))
        except Exception:
            pass
        return

    return module


def pong_controller(app, **options):
    pong_service = PingPongService(app, **options)
    module = ZMQMicroController()
    module.register_service(pong_service)
    return module


def pong_server(**options):
    delay = options.pop('delay', 1)
    routing = options.pop('routing', False)

    module = ZMQMicroController()

    if not routing:
        @module.handler('ping', listen_type='health', handler_type='server')
        def pong(data):
            logger.debug(str(data))
            yield from asyncio.sleep(delay)
            return data
    else:
        @module.handler('ping', route='ping1', listen_type='health',
                        handler_type='server')
        def pong1(data):
            logger.debug('--ping1 handler--')
            logger.debug(str(data))
            yield from asyncio.sleep(delay)
            return data

        @module.handler('ping', route='ping2', listen_type='health',
                        handler_type='server')
        def pong2(data):
            logger.debug('--ping2 handler--')
            logger.debug(str(data))
            yield from asyncio.sleep(delay)
            return data
    return module


def ping_client(port, **options):
    delay = options.pop('delay', 1)
    times = options.pop('times', -1)
    routing = options.pop('routing', False)
    async = options.pop('async', False)
    module = ZMQMicroController()
    version = options.pop('version', '1')
    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
        'tags': ['version:' + version],
    }

    def get_result(future):
        data = future.result()
        logger.info('response:' + str(data))

    def finish(results):
        done, pending = yield from results
        logger.error('DONE: ' + str(len(done)))
        logger.error('PENDING:' + str(len(pending)))
        for fail in pending:
            logger.error('task never finished... ' + fail.result())
        module.app.loop.create_task(module.app.stop('SIGTERM'))

    @module.client('ping', async=async, **ping_opts)
    def ping():
        send_count = 1
        tasks = []
        try:
            while send_count <= times or times <= 0:
                yield from asyncio.sleep(delay)
                data = {'message': send_count}
                logger.info('sending ' + str(data) + ' to ping/ping1')
                if async:
                    future = asyncio.Future()
                    tasks.append(future)
                    yield from module.app.router.send(data, 'ping/ping1',
                                                      version=version,
                                                      future=future)
                    future.add_done_callback(get_result)
                    if routing:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        future2 = asyncio.Future()
                        tasks.append(future2)
                        yield from module.app.router.send(data2, 'ping/ping2',
                                                          version=version,
                                                          future=future2)
                        future2.add_done_callback(get_result)

                else:
                    response = yield from \
                        module.app.router.send(data, 'ping/ping1',
                                               version=version)
                    logger.info('response:' + str(response))
                    if routing and send_count < times:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        response = yield from \
                            module.app.router.send(data2,
                                                   'ping/ping2',
                                                   version=version)
                        logger.info('response:' + str(response))
                send_count += 1
            if async:
                module.app.loop.create_task(
                    finish(asyncio.wait(tasks, timeout=10)))
            else:
                module.app.loop.create_task(module.app.stop('SIGTERM'))
        except asyncio.CancelledError:
            logger.debug('ping client killed')

    return module
