from typing import Tuple, Optional
import re

from pydantic import constr


OSDU_RECORD_ID_WITH_VERSION_REGEX = re.compile(r"^(?P<record_id>[\w\-\.]+:[^\:]+:[\w\-\.\:\%]+):(?P<version>([0-9])*)$")
""" regex for a record id with version. The format is [record_id]:[version]. The version is always a int """

OSDU_RECORD_ID_REGEX = re.compile(r"^[\w\-\.]+:[^\:]+:[\w\-\.\:\%]+$")


def split_record_id_version(record_id: str) -> Tuple[Optional[str], Optional[int]]:
    """
    split record id and version. If record id without version, then the version returned is None
    if input is invalid, then returns (None, None)
    e.g.
        >>> split_record_id_version('namespace:master-data--custom-type:c7c421a7:123456')
        ('namespace:master-data--custom-type:c7c421a7', 123456)
        >>> split_record_id_version('namespace:master-data--custom-type:c7c421a7')
        ('namespace:master-data--custom-type:c7c421a7', None)
        >>> split_record_id_version('invalid-record')
        (None, None)
        >>> split_record_id_version('invalid-record:123456')
        (None, None)
    """
    match = OSDU_RECORD_ID_WITH_VERSION_REGEX.match(record_id)
    if not match:
        return record_id if OSDU_RECORD_ID_REGEX.match(record_id) else None, None
    version = match["version"]
    return match["record_id"], None if not version else int(version)


# specific record_id model regex
OSDU_WELL_REGEX = re.compile(r"^[\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+$")
OSDU_WELLBORE_REGEX = re.compile(r"^[\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+$")
OSDU_WELLLOG_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellLog:[\w\-\.\:\%]+$")
OSDU_WELLBORETRAJECTORY_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellboreTrajectory:[\w\-\.\:\%]+$")
OSDU_WELLBOREMARKERSET_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellboreMarkerSet:[\w\-\.\:\%]+$")
