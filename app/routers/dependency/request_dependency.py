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

# TODO do async __call__ to avoid to have run inside a thread pool


class RequestDependencySetter:
    def __init__(self, key: str, value):
        self._key = key
        self._value = value

    def __call__(self, request: Request):
        request.state.dependencies[self._key] = self._value


class RequestDependencyMetaClass(type):
    def __new__(mcs, name, bases, class_dict):
        class_obj = super().__new__(mcs, name, bases, class_dict)
        key = str(class_obj)
        default = class_dict.get('default', None)

        def dependency_call_func(self, request: Request):
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

    def __call__(self, request: Request):
        pass


# TODO migrate other dependencies


# def do_nothing(*args, **kwargs):
#     pass
#
#
# ValidateRecordFunc = Callable[['Record'], None]
#

# class ValidateRecordDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
#     default = do_nothing
#     value_type = ValidateRecordFunc
#
#
# def validate_kind_match_type(record: 'Record', entity_type: OSDUEntityFullType):
#     if not is_kind_match_entity_type(record.kind, entity_type.value):
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
#                             detail="Record is not an OSDU " + entity_type.value)
#
#
# class BulkURIAccessDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
#     value_type = Type['BulkIdAccess']
#
#
# class EnableStatisticDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
#     default = False
#
#
# class ValidateDataframeOnWriteDependency(RequestDependencyBase, metaclass=RequestDependencyMetaClass):
#     default = no_validation
