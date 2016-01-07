
from wolverine.test import TestMicroApp


def test_app_init(event_loop):
    app = TestMicroApp(event_loop)
    assert(app.config != None)
    app.run()
    assert(app.router != None)
    print(app.modules.keys())
    assert 'registry' in app.modules.keys()
    assert 'router' in app.modules.keys()
    event_loop.run_until_complete(app.stop('SIGINT'))
