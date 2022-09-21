
from logging import INFO
from functools import wraps, partial
import asyncio
from time import perf_counter, process_time

from app.context import get_or_create_ctx
from app.helper.logger import get_logger

from contextlib import contextmanager


def log_timings(tag, wall, cpu, level=INFO):
    ctx = get_or_create_ctx()
    get_logger().log(
        level,
        f"[cid {ctx.correlation_id if ctx is not None else '-'}] Timing of {tag}, wall={wall:.5f}s, cpu={cpu:.5f}s"
    )


default_capture_timing_handlers = [partial(log_timings, level=INFO)]


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
    """
    log timings of a block. Must used with context manager:

    with timeit("operation label"):
        ...
    """
    start_perf = perf_counter()
    start_process = process_time()

    yield

    wall = perf_counter() - start_perf
    cpu = process_time() - start_process
    log_timings(tag, wall, cpu, level)
