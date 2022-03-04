from typing import Any, List, Optional, Set, Tuple


class DuplicatedIdError:
    pass


def get_unique_attr_values(object_list: List[Any], attr_name: str) -> Tuple[Set[str], Optional[DuplicatedIdError]]:
    """Get the values of an attribute of all objects if all values are unique

    Args:
        object_list (List[Any]):  objects whose specified attribute must be unique
        attr_name: the name of the attribute to get for each objects

    Returns:
        The values of the attribute specified for each objects  if they are all unique
        otherwise an empty set and a DuplicatedIdError
    """

    values = set()

    # check all curve ids are unique
    if object_list:
        for obj in object_list:
            value = getattr(obj, attr_name)
            if value:
                if value in values:
                    return values, DuplicatedIdError()
                else:
                    values.add(value)

    return values, None
