from wolverine.module.service import MicroService, ServiceMessage, ServiceDef
from wolverine.test import TestMicroApp


class TestService(object):

    def test_micro_service(event_loop):
        app = TestMicroApp(loop=event_loop)
        options = {'op_1': 'test', 'op_2': True}
        service = MicroService(app, name='test', version=2, **options)
        assert service.name == 'test'
        assert service.version == 2
        assert service.options['op_1'] == 'test'
        assert service.options['op_2']

    def test_service_message(self):
        message = ServiceMessage()
        message.data = [{'name': 'test', 'version': 1}]
        assert message.has_error() != True
        message.err({'exception': 'failed', 'severity': 'high'})
        assert message.has_error()
        assert message.response() == {
            'data': [{'name': 'test', 'version': 1}],
            'errors': [{'exception': 'failed', 'severity': 'high'}]
        }

    def test_service_def(self):
        service = ServiceDef(name='test', version='2')
        service.routes.append('test/method')
        assert service.fqn() == 'wolverine:service/test/2'
        assert str(service) == str({
            'name': 'test',
            'routes': ['test/method'],
            'version': '2'
        })