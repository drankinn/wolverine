from wolverine.module import MicroModule
from wolverine.test import TestMicroApp


def test_micro_module(event_loop):
    app = TestMicroApp(loop=event_loop)
    module = MicroModule()
    module.name = 'mod'
    module.register_app(app)
    assert module.app == app
    module.app_run()
    event_loop.run_until_complete(module.app_stop())
    assert module.name == 'mod'