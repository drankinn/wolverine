import asyncio

from wolverine.module.controller import MicroController
from wolverine.module.service import MicroService, ServiceMessage
from wolverine.test import TestMicroApp


def test_controller_service(event_loop):
    app = TestMicroApp(loop=event_loop)
    ctrl = MicroController()
    service = TestService(app)
    ctrl.register_service(service)
    app.register_module(ctrl)
    assert len(ctrl.services) == 1
    app.run()


def test_controller_service_handler(event_loop):
    app = TestMicroApp(loop=event_loop)
    ctrl = MicroController()
    options = {}

    @ctrl.handler('test', **options)
    def handler(data):
        pass
    app.register_module(ctrl)
    app.run()


def test_controller_client(event_loop):
    app = TestMicroApp(loop=event_loop)
    ctrl = MicroController()
    async = True
    test_opts = {
        'address': 'tcp://test.local',
        'port': '1337',
        'tags': ['version:1']
    }

    @ctrl.client('test', async=async, **test_opts)
    def test_handler():
        pass
    app.register_module(ctrl)
    app.run()


def test_controller_data(event_loop):
    app = TestMicroApp(loop=event_loop)
    ctrl = MicroController()
    options = {}

    @ctrl.data(name='test', **options)
    def data_handler(data):
        pass
    app.register_module(ctrl)
    app.run()


class TestService(MicroService):

    def __init__(self, app, **options):
        self.delay = options.pop('delay', 1)
        self.routing = options.pop('routing', False)
        super(TestService, self).__init__(app, 'test', **options)

    def version(self, data):
        yield from asyncio.sleep(self.delay)
        return 1

    def ping(self, data):
        yield from asyncio.sleep(self.delay)
        response = ServiceMessage()
        response.data = data
        return response