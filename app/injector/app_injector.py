from abc import ABC, abstractmethod
from typing import Type, Any, Optional
import asyncio


class AppInjector(ABC):
    """
    A basic class to handle dependency injection. Module is responsible of managing the lifetime (e.g. new instance or
    single instance or some ttl ...)
    """

    def __init__(self):
        self._factory_dict = {}

    def register(self, interface: Type, factory_coroutine):
        assert asyncio.iscoroutinefunction(factory_coroutine), 'only coroutine is expected'
        self._factory_dict[self._key_from_type(interface)] = factory_coroutine

    async def get(self, interface: Type, *args, **kwargs) -> Any:
        """
        :param interface: interface require
        :param kwargs: parameters are passed as it to the factory func
        :return:
        """
        factory_coroutine = self._factory_dict[self._key_from_type(interface)]
        return await factory_coroutine(*args, **kwargs)

    @staticmethod
    def _key_from_type(t: Type) -> str:
        return str(t)


class AppInjectorModule(ABC):

    @abstractmethod
    def configure(self, injector: AppInjector):
        raise NotImplementedError('AppInjectorModule.configure is abstract')
