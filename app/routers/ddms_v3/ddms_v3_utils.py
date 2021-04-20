import re
from app.converter.converter_utils import ConverterUtils

OSDU_WELLBORE_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELLBORE_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+$')
OSDU_WELL_VERSION_REGEX = re.compile(r'^([\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+):([0-9]*)$')
OSDU_WELL_REGEX = re.compile(r'^[\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+$')
DELFI_REGEX = re.compile(r'^[\w\-\.]+:[\w\-\.]+:[\w\-\.]+$')


class DMSV3RouterUtils:
    @staticmethod
    def is_osdu_wellbore_id(entity_id: str) -> bool:
        return OSDU_WELLBORE_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_well_id(entity_id: str) -> bool:
        return OSDU_WELL_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_versionned_entity_id(entity_regexp, entity_id: str) -> (bool, str, str):
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
    def is_osdu_versionned_wellbore_id(entity_id: str) -> (bool, str, str):
        return DMSV3RouterUtils.is_osdu_versionned_entity_id(OSDU_WELLBORE_VERSION_REGEX, entity_id)

    @staticmethod
    def is_osdu_versionned_well_id(entity_id: str) -> (bool, str, str):
        return DMSV3RouterUtils.is_osdu_versionned_entity_id(OSDU_WELL_VERSION_REGEX, entity_id)

    @staticmethod
    def is_delfi_id(entity_id: str) -> bool:
        return DELFI_REGEX.match(entity_id) is not None

    @staticmethod
    def is_osdu_entity_fake_id(entity_id: str) -> (bool, str):
        try:
            delfi_id = ConverterUtils.decode_id(entity_id)
            return DMSV3RouterUtils.is_delfi_id(delfi_id), delfi_id
        except ValueError as e:
            return False, None

