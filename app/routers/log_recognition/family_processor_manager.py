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

import importlib.resources as pkg_resources  # for loading resources in a package folder
import json
from dataclasses import dataclass
from datetime import datetime
from fastapi import status
import far.catalogs as catalogs

from far import family_processor as family_processor
from far.family_processor.family_processor import FamilyProcessor as FamilyProcessor
from odes_storage.exceptions import UnexpectedResponse

from app.clients.storage_service_client import get_storage_record_service
from app.context import Context
from app.helper.traces_ot import get_tracer
_tracer = get_tracer()


@dataclass
class ProcessorItem:
    processor: FamilyProcessor
    creation_date: datetime


FIXED_RECORD_ID = ":doc:" + "WDMS catalog".encode('utf-8').hex()
# This name should not match any existing partition id
DEFAULT_CATALOG_NAME = "default_WDMS_catalog"


class FamilyProcessorManager:
    def __init__(self, catalog_lifetime: int):
        """

        :param catalog_lifetime: lifetime (in seconds) for a cached catalog. Could be replaced in the future by a
        message mechanism (from DE if new catalog is uploaded or from one pod to the others via redis)
        """

        self._catalog_lifetime = catalog_lifetime
        self._processors = {DEFAULT_CATALOG_NAME: ProcessorItem(
            processor=family_processor.make_family_processor(), creation_date=datetime.now())}

    @staticmethod
    @_tracer.start_as_current_span('_get_catalogs_from_de')
    async def _get_catalogs_from_de(ctx: Context, partition_id: str):

        storage_client = await get_storage_record_service(ctx)
        record_id = f"{partition_id}{FIXED_RECORD_ID}"
        try:
            catalogs_record = await storage_client.get_record(record_id, ctx.partition_id)
        except UnexpectedResponse as e:
            if e.status_code != status.HTTP_404_NOT_FOUND:
                raise
            return None, None, None

        rules_catalog = catalogs_record.data.get("family_catalog", None)
        unit_catalog_str = pkg_resources.read_text(catalogs, 'CompatibleUnits.json')
        unit_catalog = json.loads(unit_catalog_str)
        main_family_catalog = {"LogFiles": {}}
        main_families = catalogs_record.data.get("main_family_catalog", None)
        if main_families is None:
            main_families = []
        main_family_catalog["LogFiles"]["loginfo"] = main_families

        return rules_catalog, unit_catalog, main_family_catalog

    @staticmethod
    @_tracer.start_as_current_span('_create_processor')
    async def _create_processor(ctx: Context, client_id: str) -> FamilyProcessor:
        rules_catalog, unit_catalog, main_family_catalog = await FamilyProcessorManager._get_catalogs_from_de(
            ctx, client_id)
        if rules_catalog is None:
            return None
        return family_processor.make_user_family_processor(rules_catalog, unit_catalog, main_family_catalog)

    def get_default_processor(self):
        return self._processors.get(DEFAULT_CATALOG_NAME).processor

    @_tracer.start_as_current_span('get_processor')
    async def get_processor(self, ctx: Context, client_id: str = DEFAULT_CATALOG_NAME):
        processor_item = self._processors.get(client_id, None)
        if processor_item is None:
            processor = await FamilyProcessorManager._create_processor(ctx, client_id)
            if processor is None:
                # When catalog is not found for given partition Id, fallback to the default catalog
                processor = self.get_default_processor()
            processor_item = ProcessorItem(processor=processor, creation_date=datetime.now())
            self._processors[client_id] = processor_item
        if (datetime.now() - processor_item.creation_date).seconds >= self._catalog_lifetime:
            # regenerate the client
            self._processors[client_id] = None
            return await self.get_processor(ctx, client_id)
        return processor_item.processor
