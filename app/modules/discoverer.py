
# Load modules [alpha version]
import importlib
import sys

from app.conf import Config, MODULES_PATH_PREFIX
from app.helper import logger


discovered_routers = []


def reset_routers():
    global discovered_routers
    discovered_routers = []


def get_routers():
    if len(discovered_routers) == 0:
        load_modules()
    return discovered_routers


def load_modules():
    discovered_modules = []

    modules = Config.modules.value
    if modules:
        discovered_modules = modules.split(',')

    logger.get_logger().info(f'Discovered modules: {discovered_modules}')
    for name in discovered_modules:
        load_module(name)


def load_module(name):
    log = logger.get_logger()
    try:
        log.info(f'Loading `{name}` module')
        module = importlib.import_module(f'{MODULES_PATH_PREFIX}.{name}')

        router = module.router
        if not router.prefix:
            raise AttributeError('Router prefix cannot be empty')
        if not router.tags:
            raise AttributeError('Router tags cannot be empty')

        discovered_routers.append(router)

        log.info(f'Done. `{name}` loaded')
    except AttributeError as error:
        log.warning(f'Failed to load `{name}` module. Module not configured properly. {error}')
    except ModuleNotFoundError as error:
        log.warning(f'Failed to load `{name}` module. Module not found. {error}')
    except ValueError as error:
        log.warning(f'Failed to load `{name}` module. {error}')
    except NameError as error:
        log.warning(f'Failed to load `{name}` module. Missing module configuration. {error}')
    except:
        log.warning(f'Failed to load `{name}` module. {sys.exc_info()[0]}')
