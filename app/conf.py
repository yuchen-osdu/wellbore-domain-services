from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict
import logging

__all__ = ['Config', 'ConfigurationContainer', 'check_environment', 'InvalidConfigurationException']

logger = logging.getLogger('configuration')


class InvalidConfigurationException(Exception):
    pass


@dataclass
class EnvVar:
    key: str
    description: str = ''
    secret: bool = False
    default: Optional[str] = None
    value: Optional[Any] = None
    factory: Optional[Callable[[str], Any]] = None  # transform input value into the target

    def load(self):
        import os
        value = os.environ.get(self.key, self.default)
        self.value = value if self.factory is None else self.factory(value)

    def __call__(self):
        return self.value

    def __str__(self):
        return f'{self.key} = {self.printable_value}'

    def __bool__(self):
        return self.value is not None

    @property
    def printable_value(self) -> str:
        if not self:
            return 'UNDEFINED'
        if self.secret:
            return '*****'
        return str(self.value)


@dataclass(repr=False, eq=False)
class ConfigurationContainer:
    """
    Gather any static environment variables and other variable. It's possible to add other at runtime or override them.
    Add method also add it as attribute of the current instance.
    Environment variable are declared as type EnvVar, then to access the value must do:
        config.env_var_attribute.value
    Environment variable can be get also by the key of this environment variable. For instance if declared like that:

        path_env_var: EnvVar = EnvVar(key='PATH')

    then the value can be access:

        path_value = config.path_env_var.value
        path_value = config['path_env_var']
        path_value = config['PATH']

    use env_var.printable_value instead of env_var.value when the goal is to log/display it.
    """
    service_host_entitlements: EnvVar = EnvVar(
        key='SERVICE_HOST_ENTITLEMENTS',
        description='Back-end for entitlements service',
        default=None)

    service_host_search: EnvVar = EnvVar(
        key='SERVICE_HOST_SEARCH',
        description='Back-end for search service',
        default=None)

    service_host_storage: EnvVar = EnvVar(
        key='SERVICE_HOST_STORAGE',
        description='Back-end for storage service',
        default=None)

    optional_routes: EnvVar = EnvVar(
        key='OS_WELLBORE_DDMS_SHOW_OPTIONAL_ROUTES',
        description='show optional routes for development purposes',
        default='false',
        factory=lambda x: x.lower() == 'true' or x == '1')

    default_data_tenant_project_id: EnvVar = EnvVar(
        key='OS_WELLBORE_DDMS_DATA_PROJECT_ID',
        description='Data tenant ID',
        default='UNDEFINED')

    default_data_tenant_credentials: EnvVar = EnvVar(
        key='OS_WELLBORE_DDMS_DATA_PROJECT_CREDENTIALS',
        description='path to the key file of the SA to access the data tenant')

    build_details: EnvVar = EnvVar(
        key='OS_WELLBORE_DDMS_BUILD_DETAILS',
        description='contains optional extra information of the build, format is the multiple "key=value" separated'
                    'by ;',
        default='')

    dev_mode: EnvVar = EnvVar(
        key='OS_WELLBORE_DDMS_DEV_MODE',
        description='dev mode',
        default='false',
        factory=lambda x: x.lower() == 'true' or x == '1')

    openapi_prefix: EnvVar = EnvVar(
        key='OPENAPI_PREFIX',
        description='specify the base path for the openapi doc, in case deployed beind a proxy',
        default='/')

    def add(self, name: str, value: Any, *, override: bool = False):
        """ add a custom """
        if not override and name in self.__dict__:
            raise KeyError(name + ' already exists')
        self.__setattr__(name, value)

    def add_from_env(self,
                     env_var_key: str,
                     attribute_name: Optional[str] = None,
                     optional: bool = True,
                     description: str = '',
                     secret: bool = False,
                     default: Optional[str] = None,
                     factory: Optional[Callable[[str], Any]] = None,
                     *, override: bool = False) -> Optional:
        env_var = EnvVar(key=env_var_key, description=description, secret=secret, default=default, factory=factory)
        env_var.load()
        self.add(attribute_name or env_var_key, env_var, override=override)
        return env_var.value


    @classmethod
    def with_load_all(cls):
        inst = cls()
        # loop for EnvVar and load them all
        for var in inst.env_vars():
            var.load()

        return inst

    def __getitem__(self, name):
        """ look for any declared attribute and env var key """
        if name in self.__dict__:
            attribute = self.__getattribute__(name)
        else:
            attribute = next(v for v in self.env_vars() if v.key == name)
        return attribute.value if isinstance(attribute, EnvVar) else attribute

    def get(self, name, default=None):
        if name in self:
            return self[name]
        return default

    def get_env(self, name) -> Optional[EnvVar]:
        if name in self.__dict__:
            attribute = self.__getattribute__(name)
        else:
            attribute = next(v for v in self.env_vars() if v.key == name)
        return attribute if isinstance(attribute, EnvVar) else None

    def __contains__(self, name) -> bool:
        if name in self.__dict__:
            return True
        return any([v.key == name for v in self.env_vars()])

    def __repr__(self):
        return ', '.join([f'{k}={v}' for k, v in self.as_printable_dict().items()])

    def as_printable_dict(self) -> Dict[str, str]:
        return {name: att.printable_value if isinstance(att, EnvVar) else att for name, att in self.__dict__.items()}

    def env_vars(self):
        """ generator of all env vars only """
        for name, attribute in self.__dict__.items():
            if isinstance(attribute, EnvVar):
                yield attribute


# Global config instance
Config = ConfigurationContainer.with_load_all()


def check_environment(configuration):
    import os.path
    """
    The goal is to fail fast and provide meaningfully report in case of error to ease any fix/debug
    We may generalize and isolate this in each module (some implementation may need specific setup,
    e.g. some Azure impl may require an dedicated env var to some valid file).
    For now keep every rules here and review it later.

    By default, in dev_mode log only. In not dev mode
    """
    logger.info('Environment configuration:')
    for k, v in configuration.as_printable_dict().items():
        logger.info(f'   - {k} = {v}')

    # check for mandatory undefined env var
    errors = [
        f'env var {v.key} ({v.description}) is undefined' for v in [
            configuration.default_data_tenant_project_id,
            configuration.default_data_tenant_credentials]
        if not v]

    # check path exists
    errors.extend([
        f'file {v.value} not found path set in {v.key} ({v.description})' for v in [
            configuration.default_data_tenant_credentials]
        if not v or not os.path.exists(v.value)
    ])

    logger_level = logger.warning if configuration.dev_mode.value else logger.error
    for err in errors:
        logger_level(err)

    # handle errors, in no dev mode exit immediately
    if any(errors):
        if configuration.dev_mode.value:
            logger.error('!!! The current environment is not correctly setup to run the service, see logs !!!')
        else:  # just abort
            raise RuntimeError('Incorrect environment: ' + ', '.join(errors))


