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

from os import path, makedirs
import tempfile
import json
from logging import INFO

from aiohttp import ClientSession
import dask

from .helper.logger import get_logger
from .bulk_persistence import get_temp_dir

POOL_EXECUTOR_MAX_WORKER = 4


@lru_cache()
def get_http_client_session(key: str = 'GLOBAL'):
    return ClientSession(json_serialize=json.dumps)


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


def load_schema_example(file_name: str):
    with open(path.join(path.dirname(path.realpath(__file__)), 'model_examples', file_name), 'r') as json_file:
        return json.load(json_file)  # this parse the content and returns a dictionary


def make_log_captured_timing_handler(level=INFO):
    def log_captured_timing(tag, wall, cpu):
        get_logger().log(level, f"Timing of {tag}, wall={wall:.5f}s, cpu={cpu:.5f}s")

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

