# Copyright 2022 Schlumberger
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


from fastapi import Request


class RequestDependencySetter:
    """
    class used to get the value associated with the key provided.
    see https://fastapi.tiangolo.com/advanced/advanced-dependencies/#a-callable-instance
     """
    def __init__(self, key: str, value):
        self._key = key
        self._value = value

    async def __call__(self, request: Request):
        request.state.dependencies[self._key] = self._value


class RequestDependencyMetaClass(type):
    """
    meta class in order to ease injection on dependency for routes that are meant to be re-use and customized.
    Dependency should be declared this way:
    ````
    class MyDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
        default = default_value
    ````

    meta class `RequestDependencyMetaClass` will setup the class `MyDependency` by adding 2 methods:
        * `with_value` as static method that meant to be used to set the dependency value
        * `__call__` that will to be used to get the dependency on the route side (consumer)

    note: The dependency value is stored inside the request.state.dependencies
    (see https://www.starlette.io/requests/#other-state).
    The `key` is automatically generated and the default set to None if not defined.

    Usage example:
        1- Declare dependency class as described above:
            ````
            class MyIntValueDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
                default = 42
            ````

        2- Declare dependency in the route and use it:
            ````
            @router.get('/value')
            async def get_value(
                resolved_value: int = Depends(MyIntValueDependency())
            ):
                return {"value": int_value}

            ````

        3- Set value when router in mounted:
            ````
            # set value to 1
            wdms_app.include_router(router, prefix='test-1', dependencies=[
                Depends(MyIntValueDependency.with_value(1))
            ])

            # set value to 1337
            wdms_app.include_router(router, prefix='test-1337', dependencies=[
                Depends(MyIntValueDependency.with_value(1337))
            ])

            # value not set => default value
            wdms_app.include_router(router, prefix='test-default')

            ````

        4- then response will be:

        GET 'test-1/value' ==> {"value": 1}
        GET 'test-1337/value' ==> {"value": 1337}
        GET 'test-default/value' ==> {"value": 42}

    note: if no default value is declared or set to `None` then the dependency value must be set using `with_value`
    otherwise the dependency resolution with raise a `RuntimeError` exception.
    """

    def __new__(mcs, name, bases, class_dict):
        class_obj = super().__new__(mcs, name, bases, class_dict)
        key = str(class_obj)
        default = class_dict.get('default', None)

        async def dependency_call_func(self, request: Request):
            if default is None and key not in request.state.dependencies:
                raise RuntimeError(f"dependency {key} not set")
            return request.state.dependencies.get(key, default)

        # Consumer part: __call__ method to called as regular fastAPI Depend from class
        setattr(class_obj, "__call__", dependency_call_func)

        # Producer part: adding `with_value` method, allowing to inject the dependency value
        setattr(class_obj, "with_value", lambda value: RequestDependencySetter(key, value))
        return class_obj


class RequestDependencyBase:
    """ mainly for IDE resolver"""

    @staticmethod
    def with_value(_) -> RequestDependencySetter:
        pass

    async def __call__(self, request: Request):
        pass


# TODO migrate other dependencies ValidateKindRecordDependency, BulkURIAccessDependency, EnableStatisticDependency ...

