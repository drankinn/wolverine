import asyncio
import logging
import os
import functools
from examples.ping_pong.service import PingPongService
from wolverine.module.controller import zhelpers
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
                        async=options.async))

    if 'pong' == mode:
        app.register_module(
            pong_controller(delay=int(options.delay),
                            routing=options.routing))
    if 'pong2' == mode:
        app.register_module(
            pong_controller(delay=int(options.delay),
                            routing=options.routing))
    app.run()


def pong_controller(**options):
    service = PingPongService(**options)
    module = ZMQMicroController()
    module.register_service(service)
    return module


def pong_service(**options):

    delay = options.pop('delay', 1)
    routing = options.pop('routing', False)

    module = ZMQMicroController()

    if not routing:
        @module.handler('ping', listen_type='health', handler_type='server')
        def pong(data):
            if logger.getEffectiveLevel() == logging.DEBUG:
                zhelpers.dump(data)
            yield from asyncio.sleep(delay)
            return data
    else:
        @module.handler('ping', route='ping1', listen_type='health',
                        handler_type='server')
        def pong1(data):
            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.debug('--ping1 handler--')
                zhelpers.dump(data)
            yield from asyncio.sleep(delay)
            return data

        @module.handler('ping', route='ping2', listen_type='health',
                        handler_type='server')
        def pong2(data):
            if logger.getEffectiveLevel() == logging.DEBUG:
                logger.debug('--ping2 handler--')
                zhelpers.dump(data)
            yield from asyncio.sleep(delay)
            return data
    return module


def ping_client(port, **options):
    delay = options.pop('delay', 1)
    times = options.pop('times', -1)
    routing = options.pop('routing', False)
    async = options.pop('async', False)
    module = ZMQMicroController()
    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
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
                                                      future=future)
                    future.add_done_callback(get_result)
                    if routing:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        future2 = asyncio.Future()
                        tasks.append(future2)
                        yield from module.app.router.send(data2, 'ping/ping2',
                                                          future=future2)
                        future2.add_done_callback(get_result)

                else:
                    response = yield from module.app.router.send(data,
                                                             'ping/ping1')
                    logger.info('response:' + str(response))
                    if routing and send_count < times:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        response = yield from module.app.router.send(data2,
                                                                 'ping/ping2')
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

