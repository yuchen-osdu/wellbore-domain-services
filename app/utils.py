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

import asyncio
from time import perf_counter, process_time
from typing import Optional, Callable, List, Tuple, Union, NamedTuple
from functools import lru_cache, wraps
import contextvars
from os import path, makedirs
import tempfile
import json
from logging import INFO

from aiohttp import ClientSession
import dask
from dask.utils import parse_bytes, format_bytes
from dask.distributed import Client as DaskDistributedClient
from distributed import system, LocalCluster
from distributed.deploy.utils import nprocesses_nthreads

from app.model.user import User
from app.injector.app_injector import AppInjector
from app.conf import Config

POOL_EXECUTOR_MAX_WORKER = 4
HOUR = 3600  # in seconds


@lru_cache()
def get_http_client_session(key: str = 'GLOBAL'):
    return ClientSession(json_serialize=json.dumps)


class DaskException(Exception):
    pass


class DaskClient:
    # singleton of DaskDistributedClient class
    client: DaskDistributedClient = None

    # Ensure access to critical section is done for only one coroutine
    lock_client: asyncio.Lock = None

    # Minimal amount of memory required for a Dask worker to not get bad performances
    min_worker_memory_recommended = parse_bytes(Config.min_worker_memory.value)

    # Amount of memory Reserved for fastApi server + ProcessPoolExecutors
    memory_leeway = parse_bytes('600Mi')

    @staticmethod
    async def create() -> DaskDistributedClient:
        if not DaskClient.lock_client:
            DaskClient.lock_client = asyncio.Lock()

        if not DaskClient.client:
            async with DaskClient.lock_client:
                if not DaskClient.client:
                    from app.helper.logger import get_logger
                    logger = get_logger()
                    logger.info(f"Dask client initialization started...")

                    n_workers, threads_per_worker, worker_memory_limit = DaskClient._get_dask_configuration(logger)
                    logger.info(f"Dask client worker configuration: {n_workers} workers running with "
                                f"{format_bytes(worker_memory_limit)} of RAM and {threads_per_worker} threads each")

                    # Ensure memory used by workers is freed regularly despite memory leak
                    dask.config.set({'distributed.worker.lifetime.duration': HOUR * 24})
                    dask.config.set({'distributed.worker.lifetime.stagger': HOUR * 1})
                    dask.config.set({'distributed.worker.lifetime.restart': True})
                    logger.info(f"Dask cluster configuration - "
                                f"worker lifetime: {dask.config.get('distributed.worker.lifetime.duration')}s. "
                                f"stagger: {dask.config.get('distributed.worker.lifetime.stagger')}s.")

                    cluster = await LocalCluster(
                        asynchronous=True,
                        processes=True,
                        threads_per_worker=threads_per_worker,
                        n_workers=n_workers,
                        memory_limit=worker_memory_limit,
                        dashboard_address=None
                    )

                    # A worker could be killed when executing a task if lifetime duration elapsed,
                    # "cluster.adapt(min=N, max=N)" ensure the respawn of workers if it happens
                    cluster.adapt(minimum=n_workers, maximum=n_workers)
                    DaskClient.client = await DaskDistributedClient(cluster, asynchronous=True)

                    get_logger().info(f"Dask client initialized : {DaskClient.client}")
        return DaskClient.client

    @staticmethod
    def _get_system_memory():
        return system.MEMORY_LIMIT

    @staticmethod
    def _available_memory_for_workers():
        """ Return amount of RAM available for Dask's workers after withdrawing RAM required by server itself """
        return max(0, (DaskClient._get_system_memory() - DaskClient.memory_leeway))

    @staticmethod
    def _recommended_workers_and_threads():
        """ Return the recommended numbers of worker and threads according the cpus available provided by Dask """
        return nprocesses_nthreads()

    @staticmethod
    def _get_dask_configuration(logger):
        """
        Return recommended Dask workers configuration
        """
        n_workers, threads_per_worker = DaskClient._recommended_workers_and_threads()
        available_memory_bytes = DaskClient._available_memory_for_workers()
        worker_memory_limit = int(available_memory_bytes / n_workers)

        logger.info(f"Dask client - system.MEMORY_LIMIT: {format_bytes(DaskClient._get_system_memory())} "
                    f"- available_memory_bytes: {format_bytes(available_memory_bytes)} "
                    f"- min_worker_memory_recommended: {format_bytes(DaskClient.min_worker_memory_recommended)} "
                    f"- computed worker_memory_limit: {format_bytes(worker_memory_limit)} for {n_workers} workers")

        if DaskClient.min_worker_memory_recommended > worker_memory_limit:
            n_workers = available_memory_bytes // DaskClient.min_worker_memory_recommended
            if not n_workers >= 1:
                min_memory = DaskClient.min_worker_memory_recommended + DaskClient.memory_leeway
                message = f'Not enough memory available to start Dask worker. ' \
                          f'Please, consider upgrading container memory to {format_bytes(min_memory)}'
                logger.error(f"Dask client - {message} - "
                             f'n_workers: {n_workers} threads_per_worker: {threads_per_worker}, '
                             f'available_memory_bytes: {available_memory_bytes} ')
                raise DaskException(message)

            worker_memory_limit = available_memory_bytes / n_workers
            logger.warning(f"Dask client - available RAM is too low. Reducing number of workers "
                           f"to {n_workers} running with {format_bytes(worker_memory_limit)} of RAM")

        return n_workers, threads_per_worker, worker_memory_limit

    @staticmethod
    async def close():
        if not DaskClient.lock_client:
            return

        async with DaskClient.lock_client:
            if DaskClient.client:
                # closing the cluster (started independently from the client)
                cluster = await DaskClient.client.cluster
                await cluster.close()
                await DaskClient.client.close()  # or shutdown
                DaskClient.client = None


def _setup_temp_dir() -> str:
    tmpdir = tempfile.gettempdir()
    if not tmpdir.endswith('wdmsosdu'):
        tmpdir = path.join(tmpdir, 'wdmsosdu')
        makedirs(tmpdir, exist_ok=True)
        tempfile.tempdir = tmpdir
    return tmpdir


WDMS_TEMP_DIR = _setup_temp_dir()


def get_wdms_temp_dir():
    return WDMS_TEMP_DIR


async def async_with_cache(cache, key: str, fn_coroutine, *args, **kwargs):
    try:
        return cache[key]
    except KeyError:
        pass  # key not found
    v = await fn_coroutine(*args, **kwargs)
    try:
        cache[key] = v
    except ValueError:
        pass  # value too large
    return v


class Context:
    """
    Immutable object to provide contextual information a long request processing
    """
    __slots__ = [
        '_tracer',
        '_logger',
        '_correlation_id',
        '_request_id',
        '_dev_mode',
        '_auth',
        '_partition_id',
        '_app_key',
        '_api_key',
        '_user',
        '_app_injector',
        '_attr_dict',
        '_x_user_id'
    ]

    def __init__(self,
                 tracer=None,
                 logger=None,
                 correlation_id: Optional[str] = None,
                 request_id: Optional[str] = None,
                 dev_mode: bool = Config.dev_mode.value,
                 auth=None,
                 partition_id: Optional[str] = None,
                 app_key: Optional[str] = None,
                 api_key: Optional[str] = None,
                 user: Optional[User] = None,
                 app_injector: Optional[AppInjector] = None,
                 x_user_id: Optional[str] = None,
                 **keys):

        self._tracer = tracer
        self._logger = logger
        self._correlation_id = correlation_id
        self._request_id = request_id
        self._dev_mode = dev_mode
        self._auth = auth
        self._partition_id = partition_id
        self._app_key = app_key
        self._api_key = api_key
        self._user = user
        self._app_injector = app_injector
        self._x_user_id = x_user_id

        # pass
        self._attr_dict = keys or {}

    __ctx_var = contextvars.ContextVar('_wdms_internal_context_var')
    """
    contextvar is natively supported in asyncio, we can take advantage of this of easily get the current context (by
    the way it may hide the potential dependency)
    """

    @classmethod
    def current(cls) -> 'Context':
        return cls.__ctx_var.get()

    @classmethod
    def clear_current(cls):
        cls.__ctx_var.set(Context())

    def set_current(self):
        Context.__ctx_var.set(self)

    @classmethod
    def set_current_with_value(cls, tracer=None, logger=None, correlation_id=None, request_id=None, auth=None,
                               partition_id=None, app_key=None, api_key=None, user=None, app_injector=None,
                               dev_mode=Config.dev_mode.value, x_user_id=None,
                               **keys) -> 'Context':
        """
        clone the current context with the given values, set the new ctx as current and returns it
        :return:
        """
        current = cls.current()
        assert current is not None, 'no existing current context'
        new_ctx = current.with_value(tracer=tracer,
                                     logger=logger,
                                     correlation_id=correlation_id,
                                     request_id=request_id,
                                     auth=auth,
                                     partition_id=partition_id,
                                     app_key=app_key,
                                     api_key=api_key,
                                     user=user,
                                     app_injector=app_injector,
                                     dev_mode=dev_mode,
                                     x_user_id=x_user_id,
                                     **keys)
        new_ctx.set_current()
        return new_ctx

    def get(self, key, default=None):
        if key in self._attr_dict:
            return self._attr_dict[key]
        if hasattr(self, '_' + key):
            return getattr(self, '_' + key)
        return default

    def __getitem__(self, key):
        if key in self._attr_dict:
            return self._attr_dict[key]

        if hasattr(self, '_' + key):
            return getattr(self, '_' + key)
        raise KeyError(key + ' is unknown')

    def __copy__(self):
        return self.__class__(
            tracer=self._tracer,
            logger=self._logger,
            correlation_id=self._correlation_id,
            request_id=self._request_id,
            dev_mode=self._dev_mode,
            auth=self._auth,
            partition_id=self._partition_id,
            app_key=self._app_key,
            api_key=self._api_key,
            user=self._user,
            app_injector=self._app_injector,
            x_user_id=self._x_user_id,
            **self._attr_dict)

    def with_correlation_id(self, correlation_id):
        clone = self.__copy__()
        clone._correlation_id = correlation_id
        return clone

    def with_request_id(self, request_id):
        clone = self.__copy__()
        clone._request_id = request_id
        return clone

    def with_auth(self, auth):
        clone = self.__copy__()
        clone._auth = auth
        return clone

    def with_partition_id(self, partition_id):
        clone = self.__copy__()
        clone._partition_id = partition_id
        return clone

    def with_x_user_id(self, x_user_id):
        clone = self.__copy__()
        clone._x_user_id = x_user_id
        return clone

    def with_user(self, user):
        clone = self.__copy__()
        clone._user = user
        return clone

    def with_app_key(self, app_key):
        clone = self.__copy__()
        clone._app_key = app_key
        return clone

    def with_api_key(self, api_key):
        clone = self.__copy__()
        clone._api_key = api_key
        return clone

    def with_injector(self, app_injector):
        clone = self.__copy__()
        clone._app_injector = app_injector
        return clone

    def with_value(self, tracer=None, logger=None, correlation_id=None, request_id=None, auth=None,
                   partition_id=None, app_key=None, api_key=None, user=None, app_injector=None,
                   dev_mode=Config.dev_mode.value, x_user_id=None, **keys) -> 'Context':
        """ Clone context, adding all keys in future logs """
        cloned = self.__class__(
            tracer=tracer or self._tracer,
            logger=logger or self._logger,
            correlation_id=correlation_id or self._correlation_id,
            request_id=request_id or self._request_id,
            dev_mode=dev_mode or self._dev_mode,
            auth=auth or self._auth,
            partition_id=partition_id or self._partition_id,
            app_key=app_key or self._app_key,
            api_key=api_key or self._api_key,
            user=user or self._user,
            app_injector=app_injector or self._app_injector,
            x_user_id=x_user_id or self._x_user_id,
            **self._attr_dict)

        if keys is not None:
            cloned._attr_dict.update(keys)
        return cloned

    @property
    def tracer(self):
        return self._tracer

    @property
    def logger(self):
        return self._logger

    @property
    def correlation_id(self) -> Optional[str]:
        return self._correlation_id

    @property
    def request_id(self) -> Optional[str]:
        return self._request_id

    @property
    def dev_mode(self) -> bool:
        return self._dev_mode

    @property
    def auth(self):
        return self._auth

    @property
    def partition_id(self) -> Optional[str]:
        return self._partition_id

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def app_key(self) -> Optional[str]:
        return self._app_key

    @property
    def user(self) -> Optional[User]:
        return self._user

    @property
    def app_injector(self) -> Optional[AppInjector]:
        return self._app_injector

    @property
    def x_user_id(self) -> Optional[str]:
        return self._x_user_id

    def __dict__(self):
        return {
            "tracer": self.tracer,
            "logger": self.logger,
            "correlation_id": self.correlation_id,
            "request_id": self.request_id,
            "dev_mode": self.dev_mode,
            "partition_id": self.partition_id,
            "app_key": self.app_key,
            "api_key": self.api_key,
            "x_user_id": self.x_user_id,
        }

    def __repr__(self):
        return json.dumps(self.__dict__())


def get_ctx() -> Context:
    return Context.current()


def get_or_create_ctx() -> Context:
    """
    This method aims to be used in middleware, where the order of Context creation is not guaranteed
    :return an empty Context with default values
    """
    try:
        return get_ctx()
    except LookupError:
        ctx = Context()
        ctx.set_current()
    return ctx


def load_schema_example(file_name: str):
    with open(path.join(path.dirname(path.realpath(__file__)), 'model_examples', file_name), 'r') as json_file:
        return json.load(json_file)  # this parse the content and returns a dictionary


def make_log_captured_timing_handler(level=INFO):
    def log_captured_timing(tag, wall, cpu):
        Context.current().logger.log(level, f"Timing of {tag}, wall={wall:.5f}s, cpu={cpu:.5f}s")

    return log_captured_timing


default_capture_timing_handlers = [make_log_captured_timing_handler(INFO)]


def capture_timings(tag, handlers=default_capture_timing_handlers):
    """ basic timing decorator, get both wall and cpu """

    def decorate(target):

        if asyncio.iscoroutinefunction(target):

            @wraps(target)
            async def async_inner(*args, **kwargs):
                start_perf = perf_counter()
                start_process = process_time()
                try:
                    return await target(*args, **kwargs)
                finally:
                    perf_elapsed = perf_counter() - start_perf
                    process_elapsed = process_time() - start_process
                    for handler in handlers:
                        handler(tag=tag, wall=perf_elapsed, cpu=process_elapsed)

            return async_inner

        @wraps(target)
        def sync_inner(*args, **kwargs):
            start_perf = perf_counter()
            start_process = process_time()
            try:
                return target(*args, **kwargs)
            finally:
                perf_elapsed = perf_counter() - start_perf
                process_elapsed = process_time() - start_process
                for handler in handlers:
                    handler(tag=tag, wall=perf_elapsed, cpu=process_elapsed)

        return sync_inner

    return decorate


class OpenApiResponse(NamedTuple):
    status: int
    name: str
    mimetype: str = 'application/json'
    description: str = ''
    schema: Optional[dict] = None
    example: Optional[dict] = None


# NOSONAR
class __OpenApiHandler:
    def __init__(self):
        self._handlers = {}

    def set(self, operation_id: str, *,
            request_body: Optional[dict] = None,
            schemas: Optional[dict] = None,
            responses: Optional[Union[dict, List[OpenApiResponse]]] = None) -> Callable:
        handlers = []
        if request_body is not None:
            handlers.append(lambda openapi, oid: self._set_request_body(openapi, oid, request_body))

        if responses is not None:
            if isinstance(responses, dict):
                handlers.append(lambda openapi, oid: self._append_responses(openapi, oid, responses))
            else:
                responses_dict = {
                    str(r.status): {
                        'description': r.description,
                        'content': {
                            r.mimetype:
                                {'schema': {'$ref': '#/components/schemas/' + r.name}, 'example': r.example}
                                if r.example else {'schema': {'$ref': '#/components/schemas/' + r.name}}
                        }
                    } for r in responses
                }
                schemas = schemas or {}
                schemas.update({r.name: r.schema for r in responses})
                handlers.append(lambda openapi, oid: self._append_responses(openapi, oid, responses_dict))

        if schemas is not None:
            handlers.append(lambda openapi, _: self._append_schemas(openapi, schemas))

        def decorator(func: Callable) -> Callable:
            self._handlers.setdefault(operation_id, []).extend(handlers)
            return func

        return decorator

    def __getitem__(self, operation_id: str) -> Optional[List[Callable]]:
        return self._handlers.get(operation_id, None)

    def __call__(self, openapi_schema: dict, operation_ids: List[str]):
        for operation_id in operation_ids:
            if operation_id is not None and operation_id in self._handlers:
                for handler in self._handlers[operation_id]:
                    handler(openapi_schema, operation_id)

    @classmethod
    def operation_from_id(cls, openapi_schema: dict, operation_id: str) -> Optional[dict]:
        for path, path_node in openapi_schema['paths'].items():
            for method, method_node in path_node.items():
                if method_node.get('operationId', '') == operation_id:
                    return method_node
        return None

    @classmethod
    def _set_request_body(cls, openapi_schema: dict, operation_id: str, request_body: dict):
        method_node = cls.operation_from_id(openapi_schema, operation_id)
        if request_body is not None:
            method_node['requestBody'] = request_body

    @classmethod
    def _append_responses(cls, openapi_schema: dict, operation_id: str, responses: dict):
        method_node = cls.operation_from_id(openapi_schema, operation_id)
        method_node.setdefault('responses', {}).update(responses)

    @classmethod
    def _append_schemas(cls, openapi_schema: dict, schemas: Union[dict, List[Tuple[str, dict]]]):
        openapi_schema['components'].setdefault('schemas', {}).update(
            schemas if isinstance(schemas, dict) else {name: schema for name, schema in schemas}
        )


OpenApiHandler = __OpenApiHandler()

dask.config.set({'temporary_directory': get_wdms_temp_dir()})
