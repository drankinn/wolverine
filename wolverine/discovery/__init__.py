import asyncio

from functools import wraps

from wolverine.module import MicroModule


class MicroRegistry(MicroModule):

    def __init__(self):
        super(MicroRegistry, self).__init__()
        self.name = 'registry'

    @asyncio.coroutine
    def register(self, key, value=None, **options):
        print('\nkey', key)
        print('value', value)
        print(options)
        return True

    @asyncio.coroutine
    def deregister(self, key, **options):
        pass

    def listen(self, name, **options):
        def decor(func):
            @wraps(func)
            def wrapped():
                func()
            return wrapped
        return decor

    def unwrap(self, data, data_type=None):
        pass
