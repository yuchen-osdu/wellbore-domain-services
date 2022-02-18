import asyncio
import re
from typing import List, Tuple

from fastapi import HTTPException, Request
from odes_storage import UnexpectedResponse
from odes_storage.models import Record
from pydantic import validate_model
from starlette import status

from app.bulk_persistence import BulkURI
from app.model.entity_utils import get_kind_meta
from app.model.log_bulk import LogBulkHelper
from app.model.osdu_model import (
    Well,
    Wellbore,
    WellboreMarkerSet,
    WellboreMarkerSet110,
    WellboreTrajectory,
    WellboreTrajectory110,
    WellLog,
    WellLog110,
)
from app.routers.bulk.bulk_uri_dependencies import BulkIdAccess, BULK_URI_FIELD
from app.routers.record_utils import fetch_record
from app.utils import Context, get_ctx

OSDU_WELL_VERSION_REGEX = re.compile(r"^([\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+):([0-9]*)$")
OSDU_WELL_REGEX = re.compile(r"^[\w\-\.]+:master-data\-\-Well:[\w\-\.\:\%]+$")

OSDU_WELLBORE_VERSION_REGEX = re.compile(r"^([\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+):([0-9]*)$")
OSDU_WELLBORE_REGEX = re.compile(r"^[\w\-\.]+:master-data\-\-Wellbore:[\w\-\.\:\%]+$")

OSDU_WELLLOG_VERSION_REGEX = re.compile(r"^([\w\-\.]+:work-product-component\-\-WellLog:[\w\-\.\:\%]+):([0-9]*)$")
OSDU_WELLLOG_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellLog:[\w\-\.\:\%]+$")

OSDU_WELLBORETRAJECTORY_VERSION_REGEX = re.compile(
    r"^([\w\-\.]+:work-product-component\-\-WellboreTrajectory:[\w\-\.\:\%]+):([0-9]*)$"
)
OSDU_WELLBORETRAJECTORY_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellboreTrajectory:[\w\-\.\:\%]+$")

OSDU_WELLBOREMARKERSET_VERSION_REGEX = re.compile(
    r"^([\w\-\.]+:work-product-component\-\-WellboreMarkerSet:[\w\-\.\:\%]+):([0-9]*)$"
)
OSDU_WELLBOREMARKERSET_REGEX = re.compile(r"^[\w\-\.]+:work-product-component\-\-WellboreMarkerSet:[\w\-\.\:\%]+$")

entity_names = {
    "well": "master-data--Well",
    "wellbore": "master-data--Wellbore",
    "welllog": "work-product-component--WellLog",
    "trajectory": "work-product-component--WellboreTrajectory",
    "marker": "work-product-component--WellboreMarkerSet",
}


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
    def raise_if_not_osdu_right_entity_kind(record, state):
        version = state.version if hasattr(state, 'version') else None
        entity = state.entity_type if hasattr(state, 'entity_type') else None
        if entity and record and version == "V3":
            kind_elements = get_kind_meta(record.kind)
            entity_in_kind = kind_elements.entity_type
            if entity.value in entity_names:
                matches = entity_names[entity.value] == entity_in_kind
                if not matches:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                        detail="Record is not an OSDU " + entity.value)

    @staticmethod
    def validate_record_against_kinds_schema(records: List[Record]):
        """
        Check the schema specified in the kind is a supported model and validate the record against it.

        Even the entity is valid against the current model version, it might be not valid against the schema specifed
        in its kind.  For instance a field data.ReferenceCurveID in a wellLog is valid against the current api model
        WellLog:1.1.0 but it's not valid against the wellLog:1.0.0 schema. So we need to validate it manually.

         supported model by entity_type:version:
            -  master-data--Well:1.0.0
            -  master-data--Wellbore:1.0.0
            -  work-product-component--WellLog:1.0.0
            -  work-product-component--WellLog:1.1.0
            -  work-product-component--WellboreMarkerSet:1.0.0
            -  work-product-component--WellboreMarkerSet:1.1.0
            -  work-product-component--WellboreTrajectory:1.0.0
            -  work-product-component--WellboreTrajectory:1.1.0

        Args:
            records (Record): entity object to be verified

        Returns:

        Raises:
            HTTPException in case record is not valid against the schema specified in it kind or
             entity_type and version is not supported
        """

        supported_models = {
            "master-data--Well": {"1.0.0": Well},
            "master-data--Wellbore": {"1.0.0": Wellbore},
            "work-product-component--WellLog": {"1.0.0": WellLog, "1.1.0": WellLog110},
            "work-product-component--WellboreMarkerSet": {"1.0.0": WellboreMarkerSet, "1.1.0": WellboreMarkerSet110},
            "work-product-component--WellboreTrajectory": {"1.0.0": WellboreTrajectory, "1.1.0": WellboreTrajectory110}
        }

        for idx, r in enumerate(records):
            kind = get_kind_meta(r.kind)

            if kind.entity_type not in supported_models or kind.version not in supported_models[kind.entity_type]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Entity {kind.entity_type}:{kind.version} not supported",
                )

            # In case client is posting a valid entity against a backward compatible schema older than api model
            # the pydantic model adds all optional fields of the current model  with their default value and the entity
            # will not be valid against it own schema.
            # As workaround, we convert the entity to a dict in order to remove those fields which were not set
            # by the client before validation
            _, _, validationError = validate_model(
                model=supported_models[kind.entity_type][kind.version],
                input_data=r.dict(exclude_none=True, exclude_unset=True, by_alias=True),
            )

            if validationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Record[{idx}] validation against schema '{kind.entity_type}:{kind.version}' failed: {str(validationError)}",
                )

    @staticmethod
    async def _raise_if_invalid_bulk_uri_task(index_record: int, record: Record, bulk_uri_access: BulkIdAccess):

        """
            record : Record which is tried to be created or updated gave in entry
            record_id : Record's id of the given record
            bulk_uri : Record's Bulk URI of the given record
            old_record : If "record" has a record_id, old_record is the previous version of this record
            old_bulk_uri : Previous version record's Bulk URI

            Use cases:
                * NO Bulk URI + NO record_id :                                                 200 create
                * NO Bulk URI + record_id + NO old_record :                                    200 create
                * Bulk URI + record_id + old_record + old_bulk_uri + matching Bulk URI:        200 update
                * NO Bulk URI + record_id + old_record + NO old_bulk_uri:                      200 update
                * NO Bulk URI + record_id + old_record + old_bulk_uri:                         400 Err
                * Bulk URI + NO record_id :                                                    400 Err
                * Bulk URI + record_id + NO old_record :                                       400 Err
                * Bulk URI + record_id + old_record + old_bulk_uri + NO matching Bulk URI:     400 Err
                * Bulk URI + record_id + old_record + NO old_bulk_uri:                         400 Err
        """

        ctx: Context = get_ctx()

        bulk_uri = bulk_uri_access.get_bulk_uri(record=record)

        if not record.id:
            if not bulk_uri:
                # Record creation
                return
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Record[{index_record}] error : no Bulk URI can be specified without record id",
                )

        # Get record's previous version
        try:
            previous_version_record = await fetch_record(ctx, record.id)
        except UnexpectedResponse as e:
            if e.status_code == status.HTTP_404_NOT_FOUND:
                # record has no previous versions
                if not bulk_uri:
                    return
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Record[{index_record}] error : no Bulk URI can be specified, given record_id has no previous version",
                )
            else:
                raise e

        # Get bulkURI's old version if it exist
        previous_version_bulk_uri = bulk_uri_access.get_bulk_uri(record=previous_version_record)
        if not previous_version_bulk_uri and bulk_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Record[{index_record}] error : no Bulk URI can be specified, given record_id has no bulkURI in "
                       f"its previous version",
            )

        if bulk_uri != previous_version_bulk_uri:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Record[{index_record}] error : Bulk URI isn't matching with the previous version one",
            )
        # Record update

    @staticmethod
    async def raise_if_invalid_bulk_uri(records, bulk_uri_access: BulkIdAccess):
        """
        Check of BulkURIs in the given records on create/update welllog and trajectory APIs.

        The property ExtensionProperties.wdms.bulkURI is "internal" to the wdms service.
        User can't be allowed to "set" incorrect value, which could lead to invalid records.

         Supported use case:
            In case of Update, the bulk URI must match the current/previous one. If not, we will raise an error.

        Args:
            records (Record): Entity object to be verified
            bulk_uri_access: Bulk uri access

        Returns:

        Raises:
            HTTPException in case record has not valid BulkURI
        """

        await asyncio.gather(
            *[DMSV3RouterUtils._raise_if_invalid_bulk_uri_task(index_record, record, bulk_uri_access) for index_record, record in enumerate(records)])
