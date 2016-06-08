import os
import sys

from wolverine.module import MicroModule

try:
    import jinja2
    from aiohttp_jinja2 import setup
except:
    pass

__all__ = ('JinjaModule',)


class JinjaModule(MicroModule):

    def __init__(self):
        super().__init__()
        self.name = 'jinja'
        self.template_folder = '/tmp/templates'

    def init(self):
        self.read_config()
        setup(self.app.web,
              loader=jinja2.FileSystemLoader(self.template_folder))

    def read_config(self):
        config = self.app.config[self.name.upper()]
        self.template_folder = config.get('templates', '/tmp/templates')
