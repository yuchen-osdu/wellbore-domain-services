# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass
from typing import Optional, Callable, Any, Dict, List
import logging
import os

__all__ = ['Config',
           'ConfigurationContainer',
           'check_environment',
           'cloud_provider_additional_environment',
           'validator_path_must_exist']

logger = logging.getLogger('configuration')


@dataclass
class EnvVar:
    key: str
    description: str = ''
    secret: bool = False
    default: Optional[str] = None
    value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None  # if value not in the given list, it's reassigned to None
    is_mandatory: bool = False
    factory: Optional[Callable[[str], Any]] = None  # transform input value into the target
    validator: Optional[Callable[[Any], int]] = None  # value is always check if None

    def load(self, environment_dict):
        value = environment_dict.get(self.key, self.default)
        if self.factory is not None and value is not None:
            value = self.factory(value)
        if self.allowed_values is None or value in self.allowed_values:
            self.value = value

    def __call__(self):
        return self.value

    def __str__(self):
        return f'{self.key} = {self.printable_value}'

    def __bool__(self):
        if self.value is None:
            return False
        return True if self.validator is None else self.validator(self.value)

    @property
    def printable_value(self) -> str:
        if self.value is None:
            return 'UNDEFINED'
        if self.secret:
            return '*****'
        return str(self.value)


def validator_path_must_exist(path: str):
    return os.path.exists(path)


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

    service_name: EnvVar = EnvVar(
        key='SERVICE_NAME',
        description='Display name of the service when exporting entries for logging and tracing',
        default='os-wellbore-ddms---local'
    )

    environment_name: EnvVar = EnvVar(
        key='ENVIRONMENT_NAME',
        description='Environment name',
        default='undefined'
    )

    cloud_provider: EnvVar = EnvVar(
        key='CLOUD_PROVIDER',
        description='Short name of the current cloud provider environment, must be "aws" or "gcp" or "az" or "ibm',
        default=None,
        is_mandatory=True,
        allowed_values=['aws', 'gcp', 'az', 'local', 'ibm'],
        factory=lambda x: x.lower()
    )

    service_host_search: EnvVar = EnvVar(
        key='SERVICE_HOST_SEARCH',
        description='Back-end for search service',
        is_mandatory=True)
  
    service_host_storage: EnvVar = EnvVar(
        key='SERVICE_HOST_STORAGE',
        description='Back-end for storage service',
        is_mandatory=True)

    de_client_config_timeout: EnvVar = EnvVar(
        key='DE_CLIENT_CFG_TIMEOUT',
        description='set connect, read, write, and pool timeouts (in seconds) for all DE client.',
        default='10',
        factory=lambda x: int(x))

    de_client_config_max_connection: EnvVar = EnvVar(
        key='DE_CLIENT_CFG_MAX_CONNECTION',
        description='maximum number of allowable connections, 0 to always allow.',
        default='1000',
        factory=lambda x: int(x))

    de_client_config_max_keepalive: EnvVar = EnvVar(
        key='DE_CLIENT_CFG_MAX_KEEPALIVE',
        description='number of allowable keep-alive connections, 0 to always allow.',
        default='500',
        factory=lambda x: int(x))

    de_client_backoff_max_tries: EnvVar = EnvVar(
        key='DE_CLIENT_BACKOFF_MAX_RETRIES',
        description="""The maximum number of attempts to make before giving
            up. Once exhausted, the exception will be allowed to escape.
            The default value of None means their is no limit to the
            number of tries.""",
        default='4',
        factory=lambda x: int(x))

    de_client_backoff_max_wait: EnvVar = EnvVar(
        key='DE_CLIENT_BACKOFF_MAX_WAIT',
        description="""The maximum wait in second between retry. """,
        default='5',
        factory=lambda x: int(x))

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
        default='/api/os-wellbore-ddms')

    custom_catalog_timeout: EnvVar = EnvVar(
        key='CUSTOM_CATALOG_TIMEOUT',
        description='Timeout to invalidate custom catalog in seconds',
        default='300',
        factory=lambda x: int(x))

    modules: EnvVar = EnvVar(
        key='MODULES',
        description="""Comma separated list of module names to load.""",
        default="log_recognition.routers.log_recognition") # Add modules to the list once they are refactored, so that they are included

    min_worker_memory: EnvVar = EnvVar(
        key='MIN_WORKER_MEMORY',
        description='Min amount of memory for one worker',
        default="512Mi")

    dask_data_ipc: EnvVar = EnvVar(
        key='DASK_DATA_IPC',
        description='Specify data IPC type between main process and dask workers',
        default='dask_native',
        allowed_values=['dask_native', 'local_file'],
        factory=lambda x: x.lower()
    )

    max_columns_return: EnvVar = EnvVar(
        key='MAX_COLUMNS_RETURN',
        description='Max number of columns that can be returned per data request',
        default="500",
        factory=lambda x: int(x))

    max_columns_per_chunk_write: EnvVar = EnvVar(
        key='MAX_COLUMNS_PER_CHUNK_WRITE',
        description='Max number of columns that can be write per chunk',
        default="500",
        factory=lambda x: int(x))

    _environment_dict: Dict = os.environ

    _contextual_loader: Callable = None

    def add(self, name: str, value: Any, *, override: bool = False):
        """ add a custom """
        if not override and name in self.__dict__:
            raise KeyError(name + ' already exists')
        self.__setattr__(name, value)

    def add_from_env(self,
                     env_var_key: str,
                     attribute_name: Optional[str] = None,
                     is_mandatory: bool = False,
                     description: str = '',
                     secret: bool = False,
                     default: Optional[str] = None,
                     allowed_values: Optional[List[Any]] = None,
                     factory: Optional[Callable[[str], Any]] = None,
                     validator: Optional[Callable[[Any], int]] = None,
                     *, override: bool = False) -> Optional:
        env_var = EnvVar(key=env_var_key,
                         description=description,
                         secret=secret,
                         default=default,
                         factory=factory,
                         allowed_values=allowed_values,
                         is_mandatory=is_mandatory,
                         validator=validator)
        env_var.load(self._environment_dict)
        self.add(attribute_name or env_var_key, env_var, override=override)
        return env_var.value

    @classmethod
    def with_load_all(cls, environment_dict=os.environ, contextual_loader=None):
        inst = cls(_environment_dict=environment_dict,
                   _contextual_loader=contextual_loader)
        inst.reload()
        return inst

    def reload(self, environment_dict=None):
        if environment_dict is not None:
            self._environment_dict = environment_dict

        # loop for EnvVar and load them all
        for var in self.env_vars():
            var.load(self._environment_dict)

        if self._contextual_loader is not None:
            self._contextual_loader(self)

    def __getitem__(self, name):
        """ look for any declared attribute and env var key """
        attribute = self.get_env_or_attribute(name)
        if attribute is None:  # fallback into environment dict
            return self._environment_dict[name]

        return attribute.value if isinstance(attribute, EnvVar) else attribute

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def get_env_or_attribute(self, name) -> Optional[EnvVar]:
        if name in self.__dict__:
            return self.__getattribute__(name)
        return next((v for v in self.env_vars() if v.key == name), None)

    def __contains__(self, name) -> bool:
        if name in self.__dict__:
            return True
        return any([v.key == name for v in self.env_vars()])

    def __repr__(self):
        return ', '.join([f'{k}={v}' for k, v in self.as_printable_dict().items()])

    def as_printable_dict(self) -> Dict[str, str]:
        return {
            name:
                att.printable_value if isinstance(att, EnvVar)
                else att for name, att in self.__dict__.items()
            if not name.startswith('_')}

    def env_vars(self):
        """ generator of all env vars only """
        for name, attribute in self.__dict__.items():
            if isinstance(attribute, EnvVar):
                yield attribute


def cloud_provider_additional_environment(config: ConfigurationContainer):
    provider = config.cloud_provider.value
    if provider == 'az':
        config.add_from_env(attribute_name='az_ai_instrumentation_key',
                            env_var_key='AZ_AI_INSTRUMENTATION_KEY',
                            description='azure app insights instrumentation key',
                            secret=True,
                            is_mandatory=True,
                            override=True)

        config.add_from_env(attribute_name='az_logger_level',
                            env_var_key='AZ_LOGGER_LEVEL',
                            description='azure logger level',
                            default='INFO',
                            secret=False,
                            is_mandatory=False,
                            override=True)

        config.add_from_env(attribute_name='az_default_container',
                            env_var_key='AZ_DEFAULT_CONTAINER',
                            description='default name for az container',
                            default='wdms-osdu',
                            is_mandatory=True,
                            override=True)

    if provider == 'gcp':
        config.add_from_env(attribute_name='default_data_tenant_project_id',
                            env_var_key='OS_WELLBORE_DDMS_DATA_PROJECT_ID',
                            description='GCP data tenant ID',
                            default='logstore-dev',
                            is_mandatory=True,
                            override=True)

        config.add_from_env(attribute_name='default_data_tenant_credentials',
                            env_var_key='OS_WELLBORE_DDMS_DATA_PROJECT_CREDENTIALS',
                            description='path to the key file of the SA to access the data tenant',
                            is_mandatory=False,
                            override=True,
                            validator=validator_path_must_exist,
                            default=None)

        config.add_from_env(attribute_name='service_host_storage',
                            env_var_key='SERVICE_HOST_STORAGE',
                            description='Back-end for storage service',
                            is_mandatory=False,
                            override=True,
                            default='http://storage/api/storage')

        config.add_from_env(attribute_name='service_host_search',
                            env_var_key='SERVICE_HOST_SEARCH',
                            description='Back-end for search service',
                            is_mandatory=False,
                            override=True,
                            default='http://search/api/search')

    if provider == 'ibm':
        config.add_from_env(attribute_name='default_data_tenant_project_id',
                            env_var_key='OS_WELLBORE_DDMS_DATA_PROJECT_ID',
                            description='IBM data tenant ID',
                            default='logstore-ibm',
                            is_mandatory=True,
                            override=True)
    if provider == 'aws':
        config.add_from_env(attribute_name='aws_region',
                            env_var_key='AWS_REGION',
                            description='AWS data tenant ID',
                            default='us-east-1',
                            is_mandatory=True,
                            override=True)
        config.add_from_env(attribute_name='aws_env',
                            env_var_key='ENVIRONMENT',
                            description='AWS ResourcePrefix',
                            default='osdu-',
                            is_mandatory=True,
                            override=True)
# Global config instance
Config = ConfigurationContainer.with_load_all(contextual_loader=cloud_provider_additional_environment)


def check_environment(configuration):
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

    mandatory_variables = [v for v in configuration.env_vars()
                           if v.is_mandatory and not v]
    errors = [f'env var {v.key} ({v.description}) is undefined or invalid, current value={os.environ.get(v.key)}'
              for v in mandatory_variables]

    logger_level = logger.warning if configuration.dev_mode.value else logger.error
    for err in errors:
        logger_level(err)

    # handle errors, in no dev mode exit immediately
    if any(errors):
        if configuration.dev_mode.value:
            logger.error('!!! The current environment is not correctly setup to run the service, see logs !!!')
        else:  # just abort
            raise RuntimeError('Incorrect environment: ' + ', '.join(errors))


AUTHORIZATION_HEADER_NAME = 'Authorization'
APP_KEY_HEADER_NAME = 'appKey'
APP_ID_HEADER_NAME = 'x-app-id'
CORRELATION_ID_HEADER_NAME = 'correlation-id'
REQUEST_ID_HEADER_NAME = 'Request-ID'
PARTITION_ID_HEADER_NAME = 'data-partition-id'
MODULES_PATH_PREFIX = 'app.modules'
X_USER_ID_HEADER_NAME = 'x-user-id'
