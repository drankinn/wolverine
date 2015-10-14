import asyncio


def ping_pong(mode, options):
    """Run a ping and pong service across a zmq dealer/router device

    :param mode: either client or server
    :param port: any arbitrary port.  must not be in use if running the client
    :return:  yo momma
    """
    from wolverine import MicroApp
    from wolverine.discovery.consul import consul_client
    loop = asyncio.get_event_loop()

    app = MicroApp(loop=loop,
                   registry=consul_client(loop=loop))

    if 'client' == mode:
        for i in range(int(options.concurrent)):
            if options.async:
                app.register_module(
                    async_ping_client(int(options.port) + i,
                                      delay=int(options.delay),
                                      times=int(options.times)))
            else:
                app.register_module(
                    blocking_ping_client(int(options.port) + i,
                                         delay=int(options.delay),
                                         times=int(options.times)))
    if 'client-router' == mode:
        for i in range(int(options.concurrent)):
            app.register_module(ping_router_client(int(options.port) + i,
                                                   delay=int(options.delay),
                                                   times=int(options.times)))
    if 'server' == mode:
        for i in range(int(options.concurrent)):
            app.register_module(pong_service(delay=int(options.delay)))
    if 'server-router' == mode:
        for i in range(int(options.concurrent)):
            app.register_module(pong_router_service(delay=int(options.delay)))
    app.run()


def pong_service(delay=1):
    from wolverine.modules.zmq import ZMQMicroModule
    from wolverine.modules import zhelpers
    module = ZMQMicroModule()

    @module.handler('ping', listen_type='health', handler_type='server')
    def pong(data):
        zhelpers.dump(data)
        yield from asyncio.sleep(delay)
        return data

    return module


def pong_router_service(delay=1):
    from wolverine.modules.zmq import ZMQMicroModule
    from wolverine.modules import zhelpers
    module = ZMQMicroModule()

    @module.handler('ping', route='ping1', listen_type='health',
                    handler_type='server')
    def pong(data):
        print('--ping1 handler--')
        zhelpers.dump(data)
        yield from asyncio.sleep(delay)
        return data

    @module.handler('ping', route='ping2', listen_type='health',
                    handler_type='server')
    def pong2(data):
        print('--ping2 handler--')
        zhelpers.dump(data)
        yield from asyncio.sleep(delay)
        return data

    return module


def blocking_ping_client(port, delay=1, times=-1):
    from wolverine.modules.zmq import ZMQMicroModule
    module = ZMQMicroModule()

    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
        'tags': ['DEALER_BIND'],
        'service_id': 'ping' + str(port)
    }

    @module.client('ping', **ping_opts)
    def ping():
        count = 1
        while count <= times or times <= 0:
            yield from asyncio.sleep(delay)
            data = (b'data', b'message', str(count).encode('utf-8'))
            print("ping", count)
            response = yield from module.router.send(data, 'ping')
            print('response:', response)
            count += 1
        yield from module.app.exit('SIGTERM')

    return module


def async_ping_client(port, delay, times=-1):
    from wolverine.modules.zmq import ZMQMicroModule
    module = ZMQMicroModule()

    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
        'tags': ['DEALER_BIND'],
        'service_id': 'ping' + str(port)
    }

    @module.client('ping', **ping_opts)
    def ping():
        count = 1
        while count <= times or times <= 0:
            yield from asyncio.sleep(delay)
            data = (b'data', b'message', str(count).encode('utf-8'))
            yield from module.router.send(data, 'ping', async=True)
            count += 1
        # yield from module.app.exit('SIGTERM')
    return module


def ping_router_client(port, delay=1, times=-1):
    from wolverine.modules.zmq import ZMQMicroModule
    module = ZMQMicroModule()

    ping_opts = {
        'address': 'tcp://127.0.0.1',
        'port': port,
        'tags': ['DEALER_BIND'],
        'service_id': 'ping' + str(port)
    }

    @module.handler('ping', handler_type='client', **ping_opts)
    def ping(client):
        @asyncio.coroutine
        def callback():
            alive = True
            pong_count = 0
            while alive:
                data = yield from client.read()
                pong_count += 1
                print('ponged', pong_count)
                print('data:', data)
                if pong_count == times * 2:
                    alive = False
                    module.app.exit('SIGTERM')

        module.app.loop.create_task(callback())

        count = 1
        while count <= times or times <= 0:
            yield from asyncio.sleep(delay)
            data = (b'data', b'message', str(count).encode('utf-8'))
            print("ping", count)
            yield from module.router.send(data, 'ping/ping1')
            data = (b'data2', b'message2', str(count).encode('utf-8'))
            yield from module.router.send(data, 'ping/ping2')
            count += 1

    return module
