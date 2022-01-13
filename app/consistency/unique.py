from typing import Any, List, Optional, Set, Tuple


class DuplicatedIdError:
    pass


def get_unique_ids(object_list: List[Any], attr_name: str) -> Tuple[Set[str], Optional[DuplicatedIdError]]:
    """Check that the value of an attribute of all objects in a list are unique

    Args:
        object_list (List[Any]):  objects whose specified attribute must be unique
        attr_name: the name of the attribute to check for each object of the list passed as argument

    Returns:
        The values of the attribute specified for each object passed in argument if they are all unique
        otherwise an empty set and a DuplicatedIdError
    """

    ids = set()

    # check all curve ids are unique
    if object_list:
        # expression generator fetch attribute  and  evaluate on demand if attribute value is duplicated
        is_id_duplicated = (getattr(obj, attr_name) in ids or ids.add(getattr(obj, attr_name)) for obj in object_list)
        if any(is_id_duplicated):
            return set(), DuplicatedIdError()

    return ids, None
