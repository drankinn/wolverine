
class ServiceMessage(object):
    """
    Blueprint for messages returning from services. We want all the services
    building up results and returning them, as well as errors in a uniform
    way.
    """

    def __init__(self):
        self.data = []
        self.errors = []

    def has_error(self):
        """
        @:return Boolean:   True if errors exist
        """
        return len(self.errors) > 0

    def err(self, msg):
        """
        @:param msg:        An error message to add
        """
        self.errors.append(msg)

    def response(self):
        """
        Builds a result with only the desired fields
        @:returns dict:     The structure understood by the services
        """
        return {
            'errors': self.errors,
            'data': self.data
        }