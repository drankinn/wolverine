
class MicroRegistry(object):

    def __init__(self, **kwargs):
        pass

    def register_app(self, app):
        pass

    def register(self, key, value, **options):
        pass

    def deregister(self, key, **options):
        pass

    def listen(self, name, **options):
        pass

    def lookup(self, name, **options):
        pass

    def run(self):
        pass

    def unwrap(self, data, data_type=None):
        pass
