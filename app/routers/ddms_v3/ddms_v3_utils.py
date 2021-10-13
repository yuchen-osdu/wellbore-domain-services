import re
from app.converter.converter_utils import ConverterUtils
from typing import Tuple, Optional

OSDU_WELL_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELL_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+$')

OSDU_WELLBORE_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLBORE_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+$')

OSDU_WELLLOG_VERSION_REGEX = re.compile(r'^([\w\-\.]+:work-product-component\-\-WellLog:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLLOG_REGEX = re.compile(r'^[\w\-\.]+:work-product-component\-\-WellLog:[\w\-\.\:\%]+$')

OSDU_WELLBORETRAJECTORY_VERSION_REGEX = re.compile(
    r'^([\w\-\.]+:work-product-component\-\-WellboreTrajectory:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLBORETRAJECTORY_REGEX = re.compile(
    r'^[\w\-\.]+:work-product-component\-\-WellboreTrajectory:[\w\-\.\:\%]+$')

OSDU_WELLBOREMARKERSET_VERSION_REGEX = re.compile(
    r'^([\w\-\.]+:work-product-component\-\-WellboreMarkerSet:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLBOREMARKERSET_REGEX = re.compile(
    r'^[\w\-\.]+:work-product-component\-\-WellboreMarkerSet:[\w\-\.\:\%]+$')

entities_regex = [["Wells", OSDU_WELL_VERSION_REGEX, OSDU_WELL_REGEX],
            ["Wellbores", OSDU_WELLBORE_VERSION_REGEX, OSDU_WELLBORE_REGEX],
            ["welllogs", OSDU_WELLLOG_VERSION_REGEX, OSDU_WELLLOG_REGEX],
            ["wellboretrajectories", OSDU_WELLBORETRAJECTORY_VERSION_REGEX, OSDU_WELLBORETRAJECTORY_REGEX],
            ["wellboremarkersets", OSDU_WELLBOREMARKERSET_VERSION_REGEX, OSDU_WELLBOREMARKERSET_REGEX]]

class DMSV3RouterUtils:
    @staticmethod
    def is_osdu_wellbore_id(entity_id: str) -> bool:
        return OSDU_WELLBORE_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_well_id(entity_id: str) -> bool:
        return OSDU_WELL_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_versioned_entity_id(entity_regexp, entity_id: str) -> Tuple[bool, str, str]:
        """
        :param entity_regexp: regexp to test the entity (one regexp per entity)
        :param entity_id: id of the entity to test
        :return: The first item of the tuple True if the entity is and osdu versioned entity
        The second parameter is the osdu entity id without the version or None
        The third is the version of osdu entity or None
        """
        matches = entity_regexp.match(entity_id)
        if matches is None:
            return False, None, None
        return True, matches.group(1), matches.group(2)

    @staticmethod
    def get_id_without_version(entity_regexp, entity_id: str) -> str:
        is_versioned, id_without_version, _ = DMSV3RouterUtils.is_osdu_versioned_entity_id(entity_regexp, entity_id)
        return id_without_version if is_versioned else entity_id

    @staticmethod
    def is_osdu_versioned_wellbore_id(entity_id: str) -> Tuple[bool, str, str]:
        return DMSV3RouterUtils.is_osdu_versioned_entity_id(OSDU_WELLBORE_VERSION_REGEX, entity_id)

    @staticmethod
    def is_osdu_versioned_well_id(entity_id: str) -> Tuple[bool, str, str]:
        return DMSV3RouterUtils.is_osdu_versioned_entity_id(OSDU_WELL_VERSION_REGEX, entity_id)

    @staticmethod
    def is_osdu_right_entity_id(url: str, entity_id: str) -> Optional[str]:
        for entity_regex in entities_regex:
            if "/ddms/v3/"+entity_regex[0]+"/" in url:
                matches = entity_regex[1].match(entity_id)  # versioned entity id
                if matches is None:
                    matches = entity_regex[2].match(entity_id)  # entity id not versioned
                return entity_id if matches else None


