import asyncio
from configparser import ConfigParser

import logging
from asyncio.locks import Event

import os

logger = logging.getLogger(__name__)


class MicroModule(object):

    """
        definition of the basic module with life-cycle methods
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.configured = Event()  # flag is set once configured.
        self.ready = Event()  # allows other modules to depend on this module
        self.config_dependencies = []
        self.init_dependencies = []
        self.config_task = None
        self.init_task = None
        self.config = ConfigParser()
        super().__init__()

    def add_config_dependency(self, dep):
        if dep.configured not in self.init_dependencies:
            self.config_dependencies.append(dep.configured)

    def add_init_depencency(self, dep):
        if dep.ready not in self.init_dependencies:
            self.init_dependencies.append(dep.ready)

    def configure(self):
        """
          first step:
          handles loading default settings and getting a handle to the app

        """
        default_settings = os.path.join(__path__[0], self.name + '.ini')
        self.config.read(default_settings)
        if not self.config_task:
            logger.debug('configuring module' + self.name)
            self.config_task = asyncio.ensure_future(
                trigger_on_deps(self.config_dependencies,self.configured))
        if not self.configured.is_set():
            self.configured.set()

    async def init(self):
        """
            second step:
            do any processing required before being ran.
            calls configure if the config event isn't set
            loads any resources ie thread pools, db connections etc...


        """
        if not self.configured.is_set():
            self.configure()
        await self.configured.wait()
        logger.debug('initializing module ' + self.name)
        self.ready.set()

    async def stop(self):
        """
            freeze the module so that further processing is blocked until
            restarted.
            This should clean up any resources not involved in maintaining state
            thus a restart should pick up where it left off
        """
        logger.debug('closing module ' + self.name)
        self.ready.clear()

    def requires_init(self):
        if not self.ready.is_set():
            asyncio.ensure_future(self.init())
        async def init(func):
            await self.ready()
            await func
        return init

async def trigger_on_deps(deps, event):
        for dep in deps:
            await dep.wait()
        event.set()