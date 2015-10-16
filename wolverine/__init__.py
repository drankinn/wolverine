import asyncio
from configparser import ConfigParser
import logging
import importlib
import os
import signal
import functools
from .discovery import MicroRegistry

logger = logging.getLogger(__name__)


class MicroApp(object):
    SIG_NAMES = ('SIGINT', 'SIGTERM', 'SIGHUP')

    _default_registry = MicroRegistry

    def __init__(self, loop=None, config_file='settings.ini'):
        self.name = ''
        self.config_file = config_file
        default_settings = os.path.join(__path__[0],
                                        'settings.ini')
        self.config = ConfigParser()
        self.config.read(default_settings)

        self.tasks = []
        self.modules = []
        self.registry = self.router = None
        self.loop = loop or asyncio.get_event_loop()

        def _exit(sig_name):
            self.loop.create_task(self.exit(sig_name))

        for sig in self.SIG_NAMES:
            self.loop.add_signal_handler(getattr(signal, sig),
                                         functools.partial(_exit,
                                                           sig))

    def register_module(self, module):
        logger.info("registering module" + module.name)
        module.register_app(self)
        self.modules.append(module)

    def _load_part(self, app_var):
        _path = self.config['APP'][app_var]
        module_name, class_name = _path.rsplit(".", 1)
        _module = importlib.import_module(module_name)
        return getattr(_module, class_name)()

    def _load_registry(self):
        self.registry = self._load_part('REGISTRY')
        self.registry.register_app(self)

    def _load_router(self):
        self.router = self._load_part('ROUTER')
        self.router.register_app(self)

    def run(self):
        self.name = self.config['APP'].get('NAME', 'Spooky Ash')
        self.config.read(self.config_file)
        print('-'*20)
        print('   --', self.name, '--')
        print('-'*20)
        print('')

        self._load_registry()
        self._load_router()

        self.registry.run()
        for module in self.modules:
            module.run()
        self.loop.run_forever()
        logger.info('closing loop')
        try:
            self.loop.close()
        except Exception:
            logger.error('boom', exc_info=True)

    def exit(self, sig_name):
        if sig_name in self.SIG_NAMES:
            for module in self.modules:
                yield from module.exit()
            tasks = asyncio.Task.all_tasks(self.loop)
            for task in tasks:
                try:
                    task.cancel()
                except Exception:
                    logger.error('failed to cancel task', exc_info=True)
            self.loop.stop()

