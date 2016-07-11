import asyncio
import functools
import logging

import pytest

from wolverine.module import MicroModule
from wolverine.test import TestMicroApp

LOG_FORMAT = "\n%(asctime)s %(levelname)s" \
             " %(name)s:%(lineno)s %(message)s"

logging.basicConfig(level='DEBUG', format=LOG_FORMAT)

logger = logging.getLogger(__name__)
#@pytest.mark.asyncio
#def test_micro_module(event_loop):
#    app = TestMicroApp(loop=event_loop)
#    module = MicroModule()
#    module.name = 'mod'
#    module.register_app(app)
#    assert module.app == app
#    module.app_run()
#    event_loop.run_until_complete(module.app_stop())
#    assert module.name == 'mod'


@pytest.mark.asyncio
async def test_module_states():
    module = MicroModule()
    assert module.state == MicroModule.STOPPED
    module.configure()
    assert module.state == MicroModule.CONFIGURED
    await module.init()
    assert module.state == MicroModule.READY