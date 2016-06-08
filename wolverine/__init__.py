import asyncio
import logging
import importlib
import signal

from wolverine.module import MicroModule
from .discovery import MicroRegistry

logger = logging.getLogger(__name__)


class MicroApp(MicroModule):

    def __init__(self, loop=None, config_file='settings.ini'):
        super().__init__()
        self.name = ''
        self.config_file = config_file
        self.tasks = []
        self.modules = {}
        self._loop = loop
        self.running = False

    def __call__(self):
        """gunicorn compatibility"""
        return self

    @property
    def loop(self):
        if not self._loop:
            self._loop = asyncio.get_event_loop()
        return self._loop

    def register_module(self, module):
        logger.info("registering module [" + module.name + "]")
        module.add_config_dependency(self)
        self.modules[module.name] = module

    def _get_module_class(self, app_var):
        _path = self.config['APP'][app_var]
        module_name, class_name = _path.rsplit(".", 1)
        _module = importlib.import_module(module_name)
        return getattr(_module, class_name)()

    async def run(self):
        """
        Registers the internal modules.
        Loads the user defined configuration (if any)
        then gives each module a chance to execute their run method
        lastly calls the _run method to start the loop.
        """
        if self.running:
            return
        self.configure()
        self.running = True
        self.config.read(self.config_file)
        self.config.read(self.config_file)

        for key, module in self.modules.items():
            module.init()

        print('')
        self.name = self.config['APP'].get('NAME', 'Spooky Ash')
        print('-' * 20)
        print('   --', self.name, '--')
        print('-' * 20)
        print('')
        self.init_signals()

    def init_signals(self):
        self.loop.add_signal_handler(signal.SIGQUIT, self.handle_exit)
        self.loop.add_signal_handler(signal.SIGTERM, self.handle_exit)
        self.loop.add_signal_handler(signal.SIGINT, self.handle_exit)
        self.loop.add_signal_handler(signal.SIGABRT, self.handle_exit)

    def handle_exit(self):
        asyncio.ensure_future(self.shutdown())
        print(1)

    async def shutdown(self):
        print(2)
        await self.stop()
        tasks = asyncio.Task.all_tasks(self.loop)
        for task in tasks:
            try:
                task.cancel()
            except Exception:
                pass
        self.loop.stop()
        print(4)

    async def stop(self):
        print(3)
        for key, module in self.modules.items():
            await module.app_stop()
        self.running = False

    def __getattr__(self, item):
        if item in self.modules.keys():
            return self.modules[item]
        else:
            raise AttributeError('no module named "' + item + '" in the app')
