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
import pandas as pd
import requests
from .variables import Variables, CmdLineSpecialVar
from typing import Any, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
from os import linesep
from math import floor
from munch import munchify
import warnings
import logging
import os
import json
import uuid
from io import BytesIO

logger = logging.getLogger()


def current_test():
    cur_test = os.environ.get('PYTEST_CURRENT_TEST', '')
    return cur_test.split('::')[-1].replace(' (call)', '').strip()


def make_correlation_id():
    return f'wdms_e2e/{uuid.uuid4()}'


@dataclass
class Request:
    method: str
    url: str
    name: str = ''
    description: str = ''
    payload: Any = None
    """ support same than requests.request, Dictionary, list of tuples, bytes, or file-like object but variables
      resolution will only occurs for string or dict """

    headers: Dict[str, str] = field(default_factory=dict)

    def __str__(self):
        r_str = f'{self.name}{linesep}' if self.name else ''
        r_str += f'URL: [{self.method.upper()}] {self.url}){linesep}'
        r_str += f'headers: {linesep}'
        for k, v in self.headers.items():
            if k.lower() in ['authorization', 'apikey', 'appkey']:
                v = v[:12] + '******' + v[-5:]
            r_str += f'    - {k}: {v}{linesep}'
        if self.payload:
            r_str += f'body: -------------------------------------------{linesep}'
            r_str += str(self.payload)
            r_str += f'-------------------------------------------{linesep}'
        r_str += linesep
        return r_str

    def get_body_obj(self):
        """ only valid for json body """
        if not self.payload:
            return munchify({})
        if isinstance(self.payload, str):
            return munchify(json.loads(self.payload))
        if isinstance(self.payload, dict):
            return munchify(self.payload)
        if isinstance(self.payload, bytes):
            return munchify(json.load(BytesIO(self.payload)))
        if hasattr(self.payload, 'read'):
            return munchify(json.load(self.payload))
        return munchify({})


@dataclass
class RunResult:
    start_ts: datetime
    end_ts: datetime
    request: Request
    response: Any

    def assert_ok(self):
        """ assert for any error (see requests.raise_for_status() )"""
        try:
            self.response.raise_for_status()
        except requests.HTTPError:
            logger.error('Error on call:')
            logger.error(str(self))
            raise

    def assert_status_code(self, expected_code):
        """ assert for a specific code """
        if int(expected_code) != self.response.status_code:
            logger.error(f'Unexpected status code: actual={self.response.status_code}, expected={expected_code}')
            logger.error(str(self))

        assert int(expected_code) == self.response.status_code,\
            f'unexpected status code, actual={self.response.status_code}, expected={expected_code}'

    @property
    def ok(self):
        return self.response.ok

    @property
    def elapsed(self):
        return floor((self.end_ts - self.start_ts).total_seconds() * 1000)

    def get_response_obj(self):
        return munchify(self.response.json())

    @property
    def summary(self):
        return f'{self.start_ts} ({self.elapsed} ms) [code={self.response.status_code}] - {self.request.method.upper()} {self.request.url}'

    def __str__(self):
        r_str = f'[{self.response.status_code}] - {self.request.name or self.request.url}{linesep}'
        r_str += f'start: [{self.start_ts}], end: {self.end_ts}, elapsed: {self.elapsed} ms{linesep}'
        r_str += f'{linesep}============ REQUEST =============== {linesep}'
        r_str += str(self.request)
        r_str += f'{linesep}============ RESPONSE =============== {linesep}'
        r_str += f'headers: {linesep}'
        for k, v in self.response.headers.items():
            if k.lower() in ['authorization', 'apikey', 'appkey']:
                v = v[:12] + '******' + v[-5:]
            r_str += f'    - {k}: {v}{linesep}'
        r_str += f'body: -------------------------------------------{linesep}'
        response_text = self.response.text
        if response_text:
            r_str += response_text
        else:
            r_str += '(no body)'
        r_str += linesep
        return r_str


class RequestRunner:

    def __init__(self, rq: Request):
        self.request_prototype = rq
        self.runs: List[RunResult] = []
        self._no_env = Variables()

    def call(self,
             env: Variables = None,
             headers=None,
             *,
             assert_status=None,
             params=None,
             dry_run=False,
             **kwargs) -> RunResult:
        """
        :param env: variables to use and substituted in the request
        :param headers: additional headers to set, will update and replace the ones in the original if same
        :param assert_status: If not None, will assert the http status code is the one provided
        :param params: optional Dictionary or bytes to be sent in the query
        :param dry_run: optional dry_run
        :param kwargs: any variables to set for this call only, with override the one in 'env' parameter.
        :return: RunResult, contains both request and response objects
        """
        if kwargs:
            env = env.copy()
            env.update(**kwargs)

        error_for_retry = CmdLineSpecialVar.get_retry_on_error(env) or []
        nb_attempt = 4
        for _ in range(nb_attempt):
            result = self._inner_call(env, headers, params, dry_run)
            if result.response.status_code in error_for_retry and result.response.status_code >= 500:
                from time import sleep
                warnings.warn(UserWarning(f'{result.response.status_code} returned from ' + result.response.url))
                logger.warning(f'{result.response.status_code} status code, retry in 10s')
                sleep(10)
                continue
            break

        if assert_status:
            result.assert_status_code(assert_status)
        return result

    def _make_headers(self, env: Variables = None, headers=None):
        result_hrd = self.request_prototype.headers.copy()

        # update from hrd from cmd line
        result_hrd.update(CmdLineSpecialVar.get_headers(env))

        # put correlation_id
        result_hrd['correlation-id'] = make_correlation_id()

        # override by headers provided
        result_hrd.update(headers or {})

        # resolve from environment
        return env.resolve(result_hrd)

    def _inner_call(self, env: Variables = None, headers=None, params=None, dry_run=False) -> RunResult:
        env = env or self._no_env
        rq = Request(method=self.request_prototype.method,
                     url=env.resolve(self.request_prototype.url))

        rq.headers = self._make_headers(env, headers)

        if self.request_prototype.payload is not None:
            rq.payload = env.resolve(self.request_prototype.payload)

        timeout = CmdLineSpecialVar.get_timeout_request(env) or 0
        timeout = None if timeout == 0 else float(timeout) / 1000.  # input is in ms, requests expected float seconds

        start_ts = datetime.now()
        log_level = CmdLineSpecialVar.get_log_request_level(env)
        if log_level >= 1:
            logger.info(f'{current_test()} => {rq.name} {rq.method.upper()} {rq.url}')

        verify = not CmdLineSpecialVar.get_disable_ssl_validation(env)

        if isinstance(rq.payload, dict) or isinstance(rq.payload, list):
            rq.payload = json.dumps(rq.payload)

        if isinstance(rq.payload, pd.DataFrame):
            # auto serializer pandas dataframe to parquet
            rq.payload = rq.payload.to_parquet(engine="pyarrow")
            rq.headers['Content-Type'] = 'application/x-parquet'

        if dry_run:
            response = requests.Response()
            response.status_code = 200
            response.request = rq
            response.raw = BytesIO(b'*** dry run ***')
        else:
            response = requests.request(rq.method, rq.url,
                                        data=rq.payload,
                                        headers=rq.headers,
                                        timeout=timeout,
                                        verify=verify,
                                        params=params)
        rq.headers = response.request.headers
        result = RunResult(start_ts=start_ts, end_ts=datetime.now(), request=rq, response=response)

        if log_level == 1:
            logger.info(f'{current_test()} <= {rq.name} status_code={result.response.status_code} '
                        f'({result.elapsed} ms), cid={rq.headers.get("correlation-id", "[none]")}')
        elif log_level > 1:
            logger.info(f'{current_test()} <= ')
            logger.info(result)

        self.runs.append(result)
        return result

    def __str__(self):
        if not self.runs:
            return 'no run, request prototype =' + linesep + str(self.request_prototype)
        r_str = f'{len(self.runs)} run(s) for {self.request_prototype.name or self.request_prototype.url}:{linesep}{linesep}'
        for count, run in enumerate(self.runs):
            r_str += f'# run {count +1}: {linesep}'
            r_str += str(run)
            r_str += linesep + linesep + linesep
        return r_str


def make_basic_request_proto(method: str, url: str, *, name=None, payload=None, content_type='application/json'):
    headers = {
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}'
        }
    if payload is not None and content_type:
        headers['Content-Type'] = content_type

    return Request(
        name=name or f"{method} - {url}",
        method=method,
        url=url,
        headers=headers,
        payload=payload
    )


def make_basic_wdms_request_proto(method: str, path: str, *, name=None, payload=None, content_type='application/json'):
    return make_basic_request_proto(method, "{{base_url}}" + path, name=name, payload=payload, content_type=content_type)
