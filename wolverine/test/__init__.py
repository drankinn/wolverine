import logging
from wolverine import MicroApp

logger = logging.getLogger(__name__)


class TestMicroApp(MicroApp):

    def _run(self):
        logger.info('test app running')
