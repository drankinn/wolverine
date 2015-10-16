import asyncio
import logging
import os
import functools
from wolverine.module.service import zhelpers
from wolverine.module.service.zmq import ZMQMicroService

logger = logging.getLogger(__name__)


def ping_pong(mode, options):
    """Run a ping and pong service across a zmq dealer/router device

    :param mode: either client or server
    :param port: any arbitrary port.  must not be in use if running the client
    :return:  yo momma
    """
    from wolverine import MicroApp
    loop = asyncio.get_event_loop()
    import examples.ping_pong
    config_file = os.path.join(examples.ping_pong.__path__[0], 'settings.ini')
    app = MicroApp(loop=loop, config_file=config_file)

    if 'client' == mode:
        app.register_module(
            ping_client(int(options.port),
                        delay=int(options.delay),
                        times=int(options.times),
                        routing=options.routing,
                        async=options.async))

    if 'server' == mode:
        app.register_module(
            pong_service(delay=int(options.delay),
                         routing=options.routing))
    app.run()


def pong_service(**options):

    delay = options.pop('delay', 1)
    routing = options.pop('routing', False)

    module = ZMQMicroService()

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
    module = ZMQMicroService()

    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
        'tags': ['DEALER_BIND'],
        'service_id': 'ping' + str(port)
    }

    def get_result(count, future):
        data = future.result()
        logger.info('response:' + str(data))
        logger.info('response count:' + str(count))
        if data['message'] == times == count:
            module.app.loop.create_task(module.app.stop('SIGTERM'))

    @module.client('ping', async=async, **ping_opts)
    def ping():
        send_count = 1
        try:
            while send_count <= times or times <= 0:
                yield from asyncio.sleep(delay)
                data = {'message': send_count}
                logger.info('sending ' + str(data) + ' to ping/ping1')
                if async:
                    future = asyncio.Future()
                    yield from module.router.send(data, 'ping/ping1',
                                                  future=future)
                    future.add_done_callback(
                        functools.partial(get_result, send_count))
                    if routing:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        future2 = asyncio.Future()
                        yield from module.router.send(data2, 'ping/ping2',
                                                      future=future2)
                        future2.add_done_callback(
                            functools.partial(get_result, send_count))

                else:
                    response = yield from module.router.send(data,
                                                             'ping/ping1')
                    logger.info('response:' + str(response))
                    if routing and send_count < times:
                        send_count += 1
                        data2 = {'message': send_count}
                        logger.info('sending ' + str(data2) + 'to ping/ping2')
                        response = yield from module.router.send(data2,
                                                                 'ping/ping2')
                        logger.info('response:' + str(response))
                send_count += 1
            if not async:
                module.app.loop.create_task(module.app.stop('SIGTERM'))
        except asyncio.CancelledError:
            logger.debug('ping client killed')
    return module
