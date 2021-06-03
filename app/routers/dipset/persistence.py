# Copyright 2021 Schlumberger
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

import math
from typing import List, NamedTuple, Tuple, Union

import pandas as pd
import numpy as np
from fastapi import HTTPException, status
from odes_storage import UnexpectedResponse

from app.clients.storage_service_client import get_storage_record_service
from app.model import entity_utils
from app.model.entity_utils import Entity
from app.model.model_curated import (
    ToOneRelationship,
    ValueWithUnit,
    dipset,
    dipsetrelationships,
    log,
    logchannel,
    logData,
    logRelationships,
)
from app.model.model_utils import from_record, to_record
from app.routers.dipset.dip_model import Dip
from app.bulk_persistence import get_dataframe, create_and_store_dataframe, BulkId

async def create_missing_logs(ctx, my_dipset: dipset):
    """
        Creates missing log in storage  and update dipset record accordingly
        return dispset record
    """

    # TODO error management log creation failed

    class LogMeta(NamedTuple):
        name: str
        unit: str
        family_type: str
        family: str
        format: str
        data_type: str
        dipset_relationships: str

    log_meta = {
        "reference": LogMeta(
            name="reference",
            unit="meter",
            family_type="Reference",
            family="Measured Depth",
            format="float64",
            data_type="number",
            dipset_relationships="referenceLog",
        ),
        "azimuth": LogMeta(
            name="trueDipAzimuth",
            unit="dega",
            family_type="Formation Geometry",
            family="True Dip Azimuth",
            format="float32",
            data_type="number",
            dipset_relationships="trueDipAzimuthLog",
        ),
        "inclination": LogMeta(
            name="trueDipInclination",
            unit="dega",
            family_type="Formation Geometry",
            family="True Dip Inclination",
            format="float32",
            data_type="number",
            dipset_relationships="trueDipInclinationLog",
        ),
        "xCoordinate": LogMeta(
            name="xCoordinate",
            unit="meter",
            family_type="Reference",
            family="X Coordinate",
            format="float32",
            data_type="number",
            dipset_relationships="xCoordinateLog",
        ),
        "yCoordinate": LogMeta(
            name="yCoordinate",
            unit="meter",
            family_type="Reference",
            family="Y Coordinate",
            format="float32",
            data_type="number",
            dipset_relationships="yCoordinateLog",
        ),
        "zCoordinate": LogMeta(
            name="zCoordinate",
            unit="meter",
            family_type="Reference",
            family="Z Coordinate",
            format="float32",
            data_type="number",
            dipset_relationships="zCoordinateLog",
        ),
        "quality": LogMeta(
            name="quality",
            unit="unitless",
            family_type="Borehole Image",
            family="Dip Quality",
            format="float32",
            data_type="number",
            dipset_relationships="qualityLog",
        ),
        "classification": LogMeta(
            name="classification",
            unit="unitless",
            family_type="Borehole Image",
            family="Dip classification",
            format="",
            data_type="string",
            dipset_relationships="classificationLog",
        ),
    }

    def create_log_record(meta: LogMeta) -> log:
        log_channel = logchannel(
            name=meta.name,
            dimension=1,
            unitKey=meta.unit,
            dataType=meta.data_type,
            family=meta.family,
            familyType=meta.family_type,
        )
        if meta.format:
            log_channel.format = meta.format

        dip_kind_metadata = entity_utils.get_kind_meta(my_dipset.kind)
        log_kind = entity_utils.get_kind(
            dip_kind_metadata.authority,
            dip_kind_metadata.source,
            Entity.LOG)

        return log(
            acl=my_dipset.acl,
            legal=my_dipset.legal,
            kind=log_kind,
            data=logData(name=f"name", operation="wddms_dipset", log=log_channel,
                         relationships=logRelationships(logSet=ToOneRelationship(id=my_dipset.id))),
        )

    # Add data.relationships  to the dipset record
    if not my_dipset.data.relationships:
        # according to the schema data.relationships is not mandatory
        # where as data.relationships.wellbore is mandatory
        # since we will add relationships to the log we must set a relationships.wellbore
        # TODO force the client to set a wellbore.
        my_dipset.data.relationships = dipsetrelationships(wellbore="")

    # Find missing logs to be created
    records = [
        to_record(create_log_record(meta))
        for k, meta in log_meta.items()
        if getattr(my_dipset.data.relationships, meta.dipset_relationships, None) is None
    ]

    # Create logs
    if len(records) > 0:
        storage_client = await get_storage_record_service(ctx)
        # Creating logs
        # TODO check create log responses (should have the right update_record_responses number of logs)
        create_logs_response = await storage_client.create_or_update_records(
            data_partition_id=ctx.partition_id, record=records
        )

        # TODO doesn't work in case only some log need to be created!!!!!
        # Update dipset
        for idx, (k, meta) in enumerate(log_meta.items()):
            setattr(
                my_dipset.data.relationships,
                meta.dipset_relationships,
                ToOneRelationship(id=create_logs_response.record_ids[idx]),
            )


def dip_to_series(dip: Dip) -> pd.Series:
    # TODO performance and code duplication with dips_to_df
    data = {}
    for member, _ in dip.__fields__.items():
        data[member] = None
        if getattr(dip, member, None) is not None:
            if isinstance(getattr(dip, member), ValueWithUnit):
                data[member] = getattr(dip, member).value
            else:
                data[member] = getattr(dip, member)

    s = pd.Series(data)
    return s

def _check_attributes(row: pd.Series, attribute_key: str, attribute_unit: str):
    types_data = [int, float, np.int64, np.float64]
    return (ValueWithUnit(unitKey=attribute_unit, value=row[attribute_key])
            if type(row[attribute_key]) in types_data and not math.isnan(row[attribute_key])
            else None)

def series_to_dip(row: pd.Series):
    # TODO refactor, error prone
    return Dip(
        reference=_check_attributes(row, "reference", "meter"),
        azimuth=_check_attributes(row, "azimuth", "dega"),
        inclination=_check_attributes(row, "inclination", "dega"),
        quality=_check_attributes(row, "quality", "unitless"),
        xCoordinate=_check_attributes(row, "xCoordinate", "meter"),
        yCoordinate=_check_attributes(row, "yCoordinate", "meter"),
        zCoordinate=_check_attributes(row, "zCoordinate", "meter"),
        classification=row.get("classification"),
    )


def dips_to_df(dips: List[Dip]) -> pd.DataFrame:
    # TODO performance and code duplication with dip_to_series

    data = {}
    for member, _ in dips[0].__fields__.items():
        data[member] = []
        for dip in dips:
            v = None
            if getattr(dip, member, None) is not None:
                if isinstance(getattr(dip, member), ValueWithUnit):
                    v = getattr(dip, member).value
                else:
                    v = getattr(dip, member)
            data[member].append(v)

    return pd.DataFrame(data)


def df_to_dips(dataframe: pd.DataFrame) -> List[Dip]:
    return [series_to_dip(row) for index, row in dataframe.iterrows()]


#TODO refactor duplicate with trajectory
async def write_bulk(ctx, dataframe: pd.DataFrame) -> str:
    bulk_id = await create_and_store_dataframe(ctx, dataframe)
    return BulkId.bulk_urn_encode(bulk_id)


async def write_dipset_data(ctx, dataframe: pd.DataFrame, ds: Union[dipset, str]) -> dipset:
    # TODO input validation & error management

    my_dipset = await fetch_dipset(ctx, ds) if not isinstance(ds, dipset) else ds

    # Sort data by reference and azimuth
    dataframe.sort_values(by=["reference", "azimuth"], inplace=True, ignore_index=True)

    # Write data in storage and update dipset bulk URI
    my_dipset.data.bulkURI = await write_bulk(ctx, dataframe)

    # Create or update logs
    await create_missing_logs(ctx, my_dipset)

    # Update dipset record
    storage_client = await get_storage_record_service(ctx)
    await storage_client.create_or_update_records(
        data_partition_id=ctx.partition_id, record=[to_record(my_dipset)]
    )

    return my_dipset


async def read_dipset_data(ctx, ds: Union[dipset, str]) -> Tuple[dipset, pd.DataFrame]:
    """Gets the bulk data for the dipset

    Create or update the log associated to the dipset and return the updated dipset

    Args:
    Union[dipset, str]: dipset record or dipset ID to get the bulkd data

    Returns:
    Tuple[dipset, pandas.DataFrame]: updated dipset record and dataframe containing bulkd data for the specified record

    Raises:
    HTTPException: 404 record is not found
    """
    my_dipset = await fetch_dipset(ctx, ds) if not isinstance(ds, dipset) else ds

    if my_dipset.data is None or my_dipset.data.bulkURI is None: # what about empty string ?
        return my_dipset, pd.DataFrame()

    # Fetch data
    df = await get_dataframe(ctx, BulkId.bulk_urn_decode(my_dipset.data.bulkURI))

    return my_dipset, df


async def fetch_dipset(ctx, dipsetid: str) -> dipset:
    """Fetch the dipset record
    check dip logs and create the missing one"""
    # TODO error management fetch dipset
    # TODO input validation  dipset record should have data, data.relationships, data.relationships.wellbore

    storage_client = await get_storage_record_service(ctx)
    try:  # TODO creating a custom exception for instance RecordNotFoundException
        storage_record = await storage_client.get_record(id=dipsetid,
                           data_partition_id=ctx.partition_id)
    except UnexpectedResponse as unexpected_response:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(unexpected_response))

    return from_record(dipset, storage_record)
