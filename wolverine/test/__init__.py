import logging
from wolverine import MicroApp

logger = logging.getLogger(__name__)


class TestMicroApp(MicroApp):

    def __init__(self, loop=None, config_file='aa'):
        super(TestMicroApp, self).__init__(loop, config_file)

    def _run(self):
        logger.info('test app running')
