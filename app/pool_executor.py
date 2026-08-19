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

import concurrent.futures
from functools import partial
import asyncio

POOL_EXECUTOR_MAX_WORKER = 4

def get_pool_executor():
    if get_pool_executor._pool is None:
        get_pool_executor._pool = concurrent.futures.ThreadPoolExecutor(POOL_EXECUTOR_MAX_WORKER)
    return get_pool_executor._pool


get_pool_executor._pool = None


async def run_in_pool_executor(func, *args, **kwargs):
    pool = get_pool_executor()
    loop = asyncio.get_running_loop()
    func = partial(func, *args, **kwargs)
    return await loop.run_in_executor(pool, func=func)
