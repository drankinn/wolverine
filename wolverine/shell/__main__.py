from configparser import ConfigParser
import datetime
import logging
from consul import Consul
import os

logger = logging.getLogger(__name__)


def execfile(pythonrc):
    with open(pythonrc) as f:
        startup_code = compile(f.read(), pythonrc, 'exec')
        exec(startup_code)


def shell():

    import code
    import wolverine.shell
    default_settings = os.path.join(wolverine.shell.__path__[0],
                                    'settings.ini')
    config = ConfigParser()
    config.read([default_settings, 'settings.ini'])
    config.read('settings.ini')
    # Set up a dictionary to serve as the environment for the shell, so
    # that tab completion works on objects that are imported at runtime.
    # See ticket 5082.

    imported_objects = {'datetime': datetime, 'config': config}
    try:
        imported_objects['consul'] = Consul(**config['DISCOVERY'])
    except Exception:
        logger.error('could not connect to consul')

    try:  # Try activating rlcompleter, because it's handy.
        import readline
    except ImportError:
        pass
    else:
        # We don't have to wrap the following import in a 'try', because
        # we already know 'readline' was imported successfully.
        import rlcompleter
        readline.set_completer(rlcompleter.Completer(imported_objects).complete)
        readline.parse_and_bind("tab:complete")

    # We want to honor both $PYTHONSTARTUP and .pythonrc.py, so follow system
    # conventions and get $PYTHONSTARTUP first then import user.
    pythonrc = os.environ.get("PYTHONSTARTUP")
    if pythonrc and os.path.isfile(pythonrc):
        try:
            execfile(pythonrc)
        except NameError:
                pass
    code.interact(local=imported_objects)


if __name__ == '__main__':
    shell()




