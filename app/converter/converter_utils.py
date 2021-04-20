import urllib

import dateutil.parser

SEP = "benderseparator"
EMPTY = "benderempty"
BENDINGCONTEXT = "bending_context"
WDMS_FRAGMENT = "wdms"
DELFI_SOURCE = "delfi_source_entity"


class ConverterUtils:
    @staticmethod
    def kind_transform(wks_kind: str, osdu_kind) -> str:
        if wks_kind is None:
            return None
        kind_as_list = wks_kind.split(sep=":")
        kind_as_list[1] = "osdu"
        kind_as_list[2] = osdu_kind[0]
        kind_as_list[3] = osdu_kind[1]
        return ":".join(kind_as_list)

    @staticmethod
    def wellbore_kind_transform(wks_kind: str) -> str:
        return ConverterUtils.kind_transform(wks_kind, ["Wellbore", "1.0.0"])

    @staticmethod
    def well_kind_transform(wks_kind: str) -> str:
        return ConverterUtils.kind_transform(wks_kind, ["Well", "1.0.0"])

    @staticmethod
    def decode_id(osdu_id: str) -> str:
        """
        decode osdu style id to delfi id
        """
        if osdu_id is None:
            return None
        return bytes.fromhex(osdu_id.split(":")[2]).decode()

    @staticmethod
    def fix_id(delfi_id: str, osdu_type: str) -> str:
        if delfi_id is None:
            return None
        # Id will have the OSDU style but not pointing on an actual osdu item
        # it will still be a delfi item - to be used with a get_as api
        # TODO find a way to make delfi id match the osdu format
        # TODO encode the delfi
        id_as_list = delfi_id.split(sep=":")
        encoded_str = delfi_id.encode().hex()
        res_as_list = []
        res_as_list.append(id_as_list[0])
        res_as_list.append(osdu_type)
        res_as_list.append(encoded_str)
        res_as_list.append("")
        return ":".join(res_as_list)

    @staticmethod
    def lookup(input_params: str, osdu_type: str) -> str:
        # returns the id of the corresponding osdu type
        # TODO implement this lookup with a cache
        # Some of the lookup have fixed values such as WellboreTrajectoryType (Vertical, Directional, Horizontal),
        # reference-data--VerticalMeasurementType,UnitOfMeasure
        # Other have to be found in storage and stored in a cache
        if input_params is None:
            return None
        input_params = input_params.split(SEP)
        namespace = input_params[0]
        delfi_value = input_params[1]
        if delfi_value == EMPTY:
            return None
        # TODO lookup in catalog, put results in cache, insert if needed

        ret = f"{namespace}:{osdu_type}:{urllib.parse.quote(delfi_value)}:"
        return ret

    @staticmethod
    def find_in_meta(metas: [dict], search_attribute: str, search_value: str, returned_attribute: str) -> str:
        if metas is None:
            return EMPTY
        for meta_item in metas:
            if meta_item.get(search_attribute, EMPTY) == search_value:
                return meta_item.get(returned_attribute, EMPTY)
        return EMPTY

    @staticmethod
    def date_to_datetime(in_date: str) -> str:
        return (
            dateutil.parser.parse(in_date).strftime("%Y-%m-%dT%H:%M:%S.%f")
            if in_date
            else None
        )

    @staticmethod
    def remove_none_from_dict(in_dict: dict) -> dict:
        new_dict = {}
        for k, v in in_dict.items():
            if isinstance(v, dict):
                v = ConverterUtils.remove_none_from_dict(v)
            if v is not None:
                new_dict[k] = v
        return new_dict or None

    @staticmethod
    def _is_value_keepable(value):
        """
        Utilitary function returning True is we keep the value
        Value can be bool, string, numerical, list, dict, ...
        Rejected values are EMPTY, None, [], {}, ()
        None and [], {}, () are evaluated as false (but not equal to False)
        value == False allow to keep boolean false values
        :param v:
        :return: True is we keep the value
        """
        return value != EMPTY and (value or value == False)

    @staticmethod
    def remove_none(in_obj):
        # This method can be optimized in python 3.8 with assignment expression PEP572 := https://stackoverflow.com/questions/4097518/intermediate-variable-in-a-list-comprehension-for-simultaneous-filtering-and-tra
        #(x or x == False) keep x if x is not not None or if x a non empty container
        if isinstance(in_obj, (list, tuple, set)):
            return type(in_obj)(ConverterUtils.remove_none(x) for x in in_obj if ConverterUtils._is_value_keepable(x) and (
                        ConverterUtils.remove_none(x) or ConverterUtils.remove_none(x) == False))
        elif isinstance(in_obj, dict):
            return type(in_obj)(
                (ConverterUtils.remove_none(k), ConverterUtils.remove_none(v)) for k, v in in_obj.items()
                if k is not None and ConverterUtils._is_value_keepable(v)
                and (ConverterUtils.remove_none(k) or ConverterUtils.remove_none(k) == False)
                and (ConverterUtils.remove_none(v) or ConverterUtils.remove_none(v) == False)
                )
        else:
            return in_obj


