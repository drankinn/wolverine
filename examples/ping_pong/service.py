import asyncio
import logging

logger = logging.getLogger(__name__)


class PingPongService(object):

    def __init__(self, **options):
        self.delay = options.pop('delay', 1)
        self.routing = options.pop('routing', False)
        self.name = 'ping'
        self.options = {}

    def ping1(self, data):
        logger.debug('--ping1 handler--')
        logger.debug('data: ' + data)
        yield from asyncio.sleep(self.delay)
        return data

    def ping(self, data):
        logger.debug('data: ' + data)
        yield from asyncio.sleep(self.delay)
        return data

    def ping2(self, data):
        logger.debug('--ping1 handler--')
        logger.debug('data: ' + data)
        yield from asyncio.sleep(self.delay)
        return data

