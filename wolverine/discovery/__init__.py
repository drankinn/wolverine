from wolverine.module import MicroModule


class MicroRegistry(MicroModule):

    def __init__(self):
        super(MicroRegistry, self).__init__()
        self.name = 'registry'

    def register(self, key, value, **options):
        pass

    def deregister(self, key, **options):
        pass

    def listen(self, name, **options):
        pass

    def unwrap(self, data, data_type=None):
        pass
