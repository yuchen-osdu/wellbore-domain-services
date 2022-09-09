
from logging import INFO
from functools import wraps
import asyncio
from time import perf_counter, process_time

from app.helper.logger import get_logger

from contextlib import contextmanager


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


@contextmanager
def timeit(tag: str, level=INFO):
    start_perf = perf_counter()
    start_process = process_time()

    yield

    perf_elapsed = perf_counter() - start_perf
    process_elapsed = process_time() - start_process
    get_logger().log(level, f"Timing of {tag}, wall={perf_elapsed:.5f}s, cpu={process_elapsed:.5f}s")
