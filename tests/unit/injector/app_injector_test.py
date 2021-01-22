from app.injector.app_injector import AppInjector, AppInjectorModule, WithLifeTime
import pytest
import uuid


class A:
    def foo(self) -> str:
        return 'A'


class B(A):
    def foo(self) -> str:
        return 'B'


class Custom(A):
    def __init__(self, value: str = 'Custom'):
        self.value = value

    def foo(self) -> str:
        return self.value


async def builder_b():
    return B()


async def builder_custom(value: str):
    return Custom(value)


class AppInjectorModuleTesting(AppInjectorModule):
    def __init__(self, coro):
        self.coro = coro

    def configure(self, injector: AppInjector):
        injector.register(A, self.coro)


@pytest.mark.asyncio
async def test_app_injector2():
    injector = AppInjector()

    async def builder():
        return 'tt'
    injector.register(str, builder)

    obj = await injector.get(str)
    print(obj)


@pytest.mark.asyncio
async def test_app_injector():
    injector = AppInjector()

    async def builder():
        return B()
    injector.register(A, builder)

    instance: A = await injector.get(A)
    assert instance.foo() == B().foo()


@pytest.mark.asyncio
async def test_app_injector_known_should_raise():
    with pytest.raises(Exception):
        injector = AppInjector()
        await injector.get(A)


@pytest.mark.asyncio
async def test_app_injector_module():
    injector = AppInjector()
    AppInjectorModuleTesting(builder_b).configure(injector)
    instance: A = await injector.get(A)
    assert instance.foo() == B().foo()

    AppInjectorModuleTesting(builder_custom).configure(injector)
    instance = await injector.get(A, value='my_value')
    assert instance.foo() == 'my_value'


@pytest.mark.asyncio
async def test_app_injector_lifetime():
    class Inner:
        def __init__(self):
            self.value = uuid.uuid4()

    async def build_fn():
        return Inner()

    # default is transient
    injector_default = AppInjector()
    injector_default.register(Inner, build_fn)

    i1 = await injector_default.get(Inner)
    i2 = await injector_default.get(Inner)

    assert i1.value != i2.value

    # transient
    injector_transient = AppInjector()
    injector_transient.register(Inner, build_fn, WithLifeTime.Transient())

    i1 = await injector_transient.get(Inner)
    i2 = await injector_transient.get(Inner)

    assert i1.value != i2.value

    # singleton
    injector_singleton = AppInjector()
    injector_singleton.register(Inner, build_fn, WithLifeTime.Singleton())

    i1 = await injector_singleton.get(Inner)
    i2 = await injector_singleton.get(Inner)

    assert i1.value == i2.value
