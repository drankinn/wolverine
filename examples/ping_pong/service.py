import asyncio
import logging
from wolverine.module.controller import zhelpers

logger = logging.getLogger(__name__)


class PingPongService(object):

    def __init__(self, **options):
        self.delay = options.pop('delay', 1)
        self.routing = options.pop('routing', False)
        self.name = 'ping'
        self.options = {}

    def ping(self, data):
        if logger.getEffectiveLevel() == logging.DEBUG:
            zhelpers.dump(data)
        yield from asyncio.sleep(self.delay)
        return data

    def ping1(self, data):
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug('--ping1 handler--')
            zhelpers.dump(data)
        yield from asyncio.sleep(self.delay)
        return data

    def ping2(self, data):
        if logger.getEffectiveLevel() == logging.DEBUG:
            logger.debug('--ping1 handler--')
            zhelpers.dump(data)
        yield from asyncio.sleep(self.delay)
        return data