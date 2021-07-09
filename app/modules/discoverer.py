
# Load extension modules [alpha version]
import importlib
import sys

from app.conf import Config
from app.helper import logger


discovered_routers = []


def get_routers():
    if len(discovered_routers) == 0:
        load_modules()
    return discovered_routers


def load_modules():
    discovered_modules = []

    extension_modules = Config.extension_modules.value
    if extension_modules:
        discovered_modules = extension_modules.split(',')

    logger.get_logger().info(f'Discovered modules: {discovered_modules}')
    for name in discovered_modules:
        load_extension(name)


def load_extension(name):
    log = logger.get_logger()
    try:
        log.info(f'Loading `{name}` extension')
        module = importlib.import_module(name)

        can_run, message = module.can_run()
        if not can_run:
            log.info(f'Skipped `{name}`. {message}')
            return

        router = module.router
        if not router.prefix:
            raise AttributeError('Router prefix cannot be empty')
        if not router.tags:
            raise AttributeError('Router tags cannot be empty')

        discovered_routers.append(router)

        log.info(f'Done. `{name}` loaded')
    except AttributeError as error:
        log.warning(f'Failed to load `{name}` extension. Module not configured properly. {error}')
    except ModuleNotFoundError as error:
        log.warning(f'Failed to load `{name}` extension. Module not found. {error}')
    except ValueError as error:
        log.warning(f'Failed to load `{name}` extension. {error}')
    except NameError as error:
        log.warning(f'Failed to load `{name}` extension. Missing module configuration. {error}')
    except:
        log.warning(f'Failed to load `{name}` extension. {sys.exc_info()[0]}')
