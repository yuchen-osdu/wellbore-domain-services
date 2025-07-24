import asyncio
from typing import List

from fastapi import HTTPException, Request
from odes_storage import UnexpectedResponse
from odes_storage.models import Record
from starlette import status

from app.model.entity_utils import get_kind_meta
from app.routers.bulk.bulk_routes_dependencies import BulkIdAccess
from app.routers.record_utils import fetch_record
from app.context import Context, get_ctx


entity_names = {
    "well": "master-data--Well",
    "wellbore": "master-data--Wellbore",
    "welllog": "work-product-component--WellLog",
    "trajectory": "work-product-component--WellboreTrajectory",
    "marker": "work-product-component--WellboreMarkerSet",
    "wellboreintervalset": "work-product-component--WellboreIntervalSet",
    "ppfgdatset" : "work-product-component--PPFGDataset",
    "wellpressuretestrawmeasurement" : "work-product-component--WellPressureTestRawMeasurement"
}


class DMSV3RouterUtils:

    @staticmethod
    def raise_if_not_osdu_right_entity_kind(record, state, status_code: int = status.HTTP_400_BAD_REQUEST):
        version = state.version if hasattr(state, 'version') else None
        entity = state.entity_type if hasattr(state, 'entity_type') else None
        if entity and record and version == "V3":
            kind_elements = get_kind_meta(record.kind)
            entity_in_kind = kind_elements.entity_type
            if entity.value in entity_names:
                matches = entity_names[entity.value] == entity_in_kind
                if not matches:
                    raise HTTPException(status_code=status_code,
                                        detail="Record is not an OSDU " + entity.value)

    @staticmethod
    def raise_if_not_osdu_right_entities_kind(records: List[Record], state):
        for record in records:
            DMSV3RouterUtils.raise_if_not_osdu_right_entity_kind(record, state
                                                                 , status.HTTP_422_UNPROCESSABLE_ENTITY
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
        bulk_uri = bulk_uri.encode() if bulk_uri.is_valid() else None

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
        previous_version_bulk_uri = previous_version_bulk_uri.encode() if previous_version_bulk_uri.is_valid() else None
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
        Check of BulkURIs in the given records on create/update welllog, trajectory and PPFGDataset APIs.

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

def get_api_config(request: Request):
    if not getattr(request.state, "api_config", None):
        raise RuntimeError("api_config dependency is not defined")
    return request.state.api_config