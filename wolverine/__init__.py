import asyncio
from configparser import ConfigParser
import logging
import importlib
import os
import signal
import functools
import types
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
        self.modules = {}
        self.loop = loop or asyncio.get_event_loop()

        def _exit(sig_name):
            self.loop.create_task(self.stop(sig_name))

        for sig in self.SIG_NAMES:
            self.loop.add_signal_handler(getattr(signal, sig),
                                         functools.partial(_exit,
                                                           sig))

    def register_module(self, module):
        logger.info("registering module" + module.name)
        module.register_app(self)
        self.modules[module.name] = module

    def _get_module_class(self, app_var):
        _path = self.config['APP'][app_var]
        module_name, class_name = _path.rsplit(".", 1)
        _module = importlib.import_module(module_name)
        return getattr(_module, class_name)()

    def _load_registry(self):
        registry = self._get_module_class('REGISTRY')
        self.register_module(registry)

    def _load_router(self):
        router = self._get_module_class('ROUTER')
        self.register_module(router)

    def run(self):
        self.config.read(self.config_file)
        self.name = self.config['APP'].get('NAME', 'Spooky Ash')
        print('-'*20)
        print('   --', self.name, '--')
        print('-'*20)
        print('')

        def _run():
            self._load_registry()
            self._load_router()

            for key, module in self.modules.items():
                ret = module.run()
                if isinstance(ret, types.GeneratorType):
                    yield from ret
        self.loop.create_task(_run())
        self.loop.run_forever()
        logger.info('closing loop')
        try:
            self.loop.close()
        except Exception:
            logger.error('boom', exc_info=True)

    def stop(self, sig_name):
        if sig_name in self.SIG_NAMES:
            for key, module in self.modules.items():
                yield from module.stop()
            tasks = asyncio.Task.all_tasks(self.loop)
            for task in tasks:
                try:
                    task.cancel()
                except Exception:
                    logger.error('failed to cancel task', exc_info=True)
            self.loop.stop()

    def __getattr__(self, item):
        if item in self.modules.keys():
            return self.modules[item]
        else:
            raise AttributeError('no module' + item + 'in the app')

