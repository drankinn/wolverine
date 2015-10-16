import asyncio
import logging

logger = logging.getLogger(__name__)


class MicroModule(object):

    def __init__(self):
        self.name = self.__class__.__name__

    def register_app(self, app):
        self.app = app
        logger.debug('registering ' + self.name + ' with app')

    def run(self):
        logger.debug('running module ' + self.name)

    @asyncio.coroutine
    def stop(self):
        logger.debug('closing module ' + self.name)

