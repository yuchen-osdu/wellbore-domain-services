from typing import Any, List, Optional, Set, Tuple


class DuplicatedIdError:
    pass


def get_unique_ids(object_list: List[Any], attr_name: str) -> Tuple[Set[str], Optional[DuplicatedIdError]]:
    ids = set()

    # check all curve ids are unique
    if object_list:
        # expression generator fetch attribut   and   evaluate on demand if attribut value is duplicated
        is_id_duplicated = (getattr(obj, attr_name) in ids or ids.add(getattr(obj, attr_name)) for obj in object_list)
        if any(is_id_duplicated):
            return {}, DuplicatedIdError()

    return ids, None
