# Copyright 2024 Schlumberger
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

from typing import Union, List
from .wdms import about
from .wdms import version
from .wdms import crud
from .wdms import error_cases
from .wdms import model_extensibility
from .wdms import recursive_delete
from ..request_runner import Request
from deepdiff import DeepDiff

request_path_dict = {
    "crud.osdu_wellbore.delete_osdu_wellbore":
        crud.osdu_wellbore.build_request_delete_osdu_wellbore,
    "crud.osdu_wellbore.get_osdu_wellbore_specific_version":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_specific_version,
    "crud.osdu_wellbore.get_osdu_wellbore":
        crud.osdu_wellbore.build_request_get_osdu_wellbore,
    "crud.osdu_wellbore.get_versions_of_osdu_wellbore":
        crud.osdu_wellbore.build_request_get_versions_of_osdu_wellbore,
    "crud.osdu_wellbore.create_osdu_wellbore":
        crud.osdu_wellbore.build_request_create_osdu_wellbore,

    "crud.osdu_wellbore_100.delete_osdu_wellbore_100":
        crud.osdu_wellbore.build_request_delete_osdu_wellbore_100,
    "crud.osdu_wellbore_100.get_osdu_wellbore_100_specific_version":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_100_specific_version,
    "crud.osdu_wellbore_100.get_osdu_wellbore_100":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_100,
    "crud.osdu_wellbore_100.get_versions_of_osdu_wellbore_100":
        crud.osdu_wellbore.build_request_get_versions_of_osdu_wellbore_100,
    "crud.osdu_wellbore_100.create_osdu_wellbore_100":
        crud.osdu_wellbore.build_request_create_osdu_wellbore_100,

    "crud.osdu_wellbore_111.delete_osdu_wellbore_111":
        crud.osdu_wellbore.build_request_delete_osdu_wellbore_111,
    "crud.osdu_wellbore_111.get_osdu_wellbore_111_specific_version":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_111_specific_version,
    "crud.osdu_wellbore_111.get_osdu_wellbore_111":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_111,
    "crud.osdu_wellbore_111.get_versions_of_osdu_wellbore_111":
        crud.osdu_wellbore.build_request_get_versions_of_osdu_wellbore_111,
    "crud.osdu_wellbore_111.create_osdu_wellbore_111":
        crud.osdu_wellbore.build_request_create_osdu_wellbore_111,

    "crud.osdu_wellbore_120.delete_osdu_wellbore_120":
        crud.osdu_wellbore.build_request_delete_osdu_wellbore_120,
    "crud.osdu_wellbore_120.get_osdu_wellbore_120_specific_version":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_120_specific_version,
    "crud.osdu_wellbore_120.get_osdu_wellbore_120":
        crud.osdu_wellbore.build_request_get_osdu_wellbore_120,
    "crud.osdu_wellbore_120.get_versions_of_osdu_wellbore_120":
        crud.osdu_wellbore.build_request_get_versions_of_osdu_wellbore_120,
    "crud.osdu_wellbore_120.create_osdu_wellbore_120":
        crud.osdu_wellbore.build_request_create_osdu_wellbore_120,

    "crud.osdu_well.delete_osdu_well":
        crud.osdu_well.build_request_delete_osdu_well,
    "crud.osdu_well.get_osdu_well_specific_version":
        crud.osdu_well.build_request_get_osdu_well_specific_version,
    "crud.osdu_well.get_osdu_well":
        crud.osdu_well.build_request_get_osdu_well,
    "crud.osdu_well.get_versions_of_osdu_well":
        crud.osdu_well.build_request_get_versions_of_osdu_well,
    "crud.osdu_well.create_osdu_well":
        crud.osdu_well.build_request_create_osdu_well,

    "crud.osdu_well_100.delete_osdu_well_100":
        crud.osdu_well.build_request_delete_osdu_well_100,
    "crud.osdu_well_100.get_osdu_well_100_specific_version":
        crud.osdu_well.build_request_get_osdu_well_100_specific_version,
    "crud.osdu_well_100.get_osdu_well_100":
        crud.osdu_well.build_request_get_osdu_well_100,
    "crud.osdu_well_100.get_versions_of_osdu_well_100":
        crud.osdu_well.build_request_get_versions_of_osdu_well_100,
    "crud.osdu_well_100.create_osdu_well_100":
        crud.osdu_well.build_request_create_osdu_well_100,

    "crud.osdu_well_110.delete_osdu_well_110":
        crud.osdu_well.build_request_delete_osdu_well_110,
    "crud.osdu_well_110.get_osdu_well_110_specific_version":
        crud.osdu_well.build_request_get_osdu_well_110_specific_version,
    "crud.osdu_well_110.get_osdu_well_110":
        crud.osdu_well.build_request_get_osdu_well_110,
    "crud.osdu_well_110.get_versions_of_osdu_well_110":
        crud.osdu_well.build_request_get_versions_of_osdu_well_110,
    "crud.osdu_well_110.create_osdu_well_110":
        crud.osdu_well.build_request_create_osdu_well_110,

    "crud.osdu_welllog.delete_osdu_welllog":
        crud.osdu_welllog.build_request_delete_osdu_welllog,
    "crud.osdu_welllog.get_osdu_welllog_specific_version":
        crud.osdu_welllog.build_request_get_osdu_welllog_specific_version,
    "crud.osdu_welllog.get_osdu_welllog":
        crud.osdu_welllog.build_request_get_osdu_welllog,
    "crud.osdu_welllog.get_versions_of_osdu_welllog":
        crud.osdu_welllog.build_request_get_versions_of_osdu_welllog,
    "crud.osdu_welllog.create_osdu_welllog":
        crud.osdu_welllog.build_request_create_osdu_welllog,
    "crud.unknown_kind_osdu_welllog.create_osdu_welllog":
        crud.osdu_welllog.build_request_create_osdu_unknown_kind_welllog,

    "crud.osdu_wellboretrajectory.delete_osdu_wellboretrajectory":
        crud.osdu_wellboretrajectory.build_request_delete_osdu_wellboretrajectory,
    "crud.osdu_wellboretrajectory.get_osdu_wellboretrajectory_specific_version":
        crud.osdu_wellboretrajectory.build_request_get_osdu_wellboretrajectory_specific_version,
    "crud.osdu_wellboretrajectory.get_osdu_wellboretrajectory":
        crud.osdu_wellboretrajectory.build_request_get_osdu_wellboretrajectory,
    "crud.osdu_wellboretrajectory.get_versions_of_osdu_wellboretrajectory":
        crud.osdu_wellboretrajectory.build_request_get_versions_of_osdu_wellboretrajectory,
    "crud.osdu_wellboretrajectory.create_osdu_wellboretrajectory":
        crud.osdu_wellboretrajectory.build_request_create_osdu_wellboretrajectory,

    "crud.osdu_wellboremarkerset.delete_osdu_wellboremarkerset":
        crud.osdu_wellboremarkerset.build_request_delete_osdu_wellboremarkerset,
    "crud.osdu_wellboremarkerset.get_osdu_wellboremarkerset_specific_version":
        crud.osdu_wellboremarkerset.build_request_get_osdu_wellboremarkerset_specific_version,
    "crud.osdu_wellboremarkerset.get_osdu_wellboremarkerset":
        crud.osdu_wellboremarkerset.build_request_get_osdu_wellboremarkerset,
    "crud.osdu_wellboremarkerset.get_versions_of_osdu_wellboremarkerset":
        crud.osdu_wellboremarkerset.build_request_get_versions_of_osdu_wellboremarkerset,
    "crud.osdu_wellboremarkerset.create_osdu_wellboremarkerset":
        crud.osdu_wellboremarkerset.build_request_create_osdu_wellboremarkerset,

    "crud.osdu_wellboreintervalset_100.delete_osdu_wellboreintervalset_100":
        crud.osdu_wellboreintervalset.build_request_delete_osdu_wellboreintervalset_100,
    "crud.osdu_wellboreintervalset_100.get_osdu_wellboreintervalset_100_specific_version":
        crud.osdu_wellboreintervalset.build_request_get_osdu_wellboreintervalset_100_specific_version,
    "crud.osdu_wellboreintervalset_100.get_osdu_wellboreintervalset_100":
        crud.osdu_wellboreintervalset.build_request_get_osdu_wellboreintervalset_100,
    "crud.osdu_wellboreintervalset_100.get_versions_of_osdu_wellboreintervalset_100":
        crud.osdu_wellboreintervalset.build_request_get_versions_of_osdu_wellboreintervalset_100,
    "crud.osdu_wellboreintervalset_100.create_osdu_wellboreintervalset_100":
        crud.osdu_wellboreintervalset.build_request_create_osdu_wellboreintervalset_100,

    "crud.osdu_welllogacquisition.delete_osdu_welllogacquisition":
        crud.osdu_welllogacquisition.build_request_delete_osdu_welllogacquisition,
    "crud.osdu_welllogacquisition.get_osdu_welllogacquisition_specific_version":
        crud.osdu_welllogacquisition.build_request_get_osdu_welllogacquisition_specific_version,
    "crud.osdu_welllogacquisition.get_osdu_welllogacquisition":
        crud.osdu_welllogacquisition.build_request_get_osdu_welllogacquisition,
    "crud.osdu_welllogacquisition.get_versions_of_osdu_welllogacquisition":
        crud.osdu_welllogacquisition.build_request_get_versions_of_osdu_welllogacquisition,
    "crud.osdu_welllogacquisition.create_osdu_welllogacquisition":
        crud.osdu_welllogacquisition.build_request_create_osdu_welllogacquisition,

    "crud.osdu_ppfgdataset.delete_osdu_ppfgdataset":
        crud.osdu_ppfgdataset.build_request_delete_osdu_ppfgdataset,
    "crud.osdu_ppfgdataset.get_osdu_ppfgdataset_specific_version":
        crud.osdu_ppfgdataset.build_request_get_osdu_ppfgdataset_specific_version,
    "crud.osdu_ppfgdataset.get_osdu_ppfgdataset":
        crud.osdu_ppfgdataset.build_request_get_osdu_ppfgdataset,
    "crud.osdu_ppfgdataset.get_versions_of_osdu_ppfgdataset":
        crud.osdu_ppfgdataset.build_request_get_versions_of_osdu_ppfgdataset,
    "crud.osdu_ppfgdataset.create_osdu_ppfgdataset":
        crud.osdu_ppfgdataset.build_request_create_osdu_ppfgdataset,

    "crud.log.delete_log":
        crud.log.build_request_delete_log,
    "crud.log.get_versions_of_log":
        crud.log.build_request_get_versions_of_log,
    "crud.log.get_log":
        crud.log.build_request_get_log,
    "crud.log.get_log_specific_version":
        crud.log.build_request_get_log_specific_version,
    "crud.log.create_log":
        crud.log.build_request_create_log,

    "crud.dips.get_dipset":
        crud.dips.build_request_get_dipset,
    "crud.dips.query_dips":
        crud.dips.build_request_query_dips,
    "crud.dips.delete_dip":
        crud.dips.build_request_delete_dip,
    "crud.dips.create_dips":
        crud.dips.build_request_create_dips,
    "crud.dips.create__dipset":
        crud.dips.build_request_create__dipset,
    "crud.dips.insert_dips":
        crud.dips.build_request_insert_dips,
    "crud.dips.get_dip_from_index":
        crud.dips.build_request_get_dip_from_index,
    "crud.dips.delete_dipset":
        crud.dips.build_request_delete_dipset,
    "crud.dips.patch_dip":
        crud.dips.build_request_patch_dip,
    "crud.dips.get_dips":
        crud.dips.build_request_get_dips,

    "error_cases.create_log_with_invalid_data_should_422":
        error_cases.build_request_create_log_with_invalid_data_should_422,
    "model_extensibility.clean_up_delete_log":
        model_extensibility.build_request_clean_up_delete_log,
    "model_extensibility.create_log_with_extra_fields":
        model_extensibility.build_request_create_log_with_extra_fields,
    "recursive_delete.setup.recusive_del_setup_check_state_start":
        recursive_delete.setup.build_request_recursive_del_setup_check_state_start,
    "recursive_delete.setup.recusive_del_setup_create_logs":
        recursive_delete.setup.build_request_recursive_del_setup_create_logs,
    "recursive_delete.delete_well.check_log_is_deleted":
        recursive_delete.delete_well.build_request_check_log_is_deleted,

    "about":
        about.build_request_about,
    "version":
        version.build_request_version,
}


def build_request(path: Union[str, List[str]], sep: str = ".") -> "RequestRunner":
    path = path.split(sep) if isinstance(path, str) else path
    n_path = ".".join([p.lower().replace(" ", "_") for p in path])
    if n_path not in request_path_dict:
        raise ValueError(f'No request matches the path {n_path}')

    return request_path_dict[n_path]()


def get_cleaned_ref_and_res(kind: str) -> dict:
    if kind == "osdu_wellbore":
        return crud.osdu_wellbore.get_cleaned_ref_and_res()
    if kind == "osdu_wellbore_100":
        return crud.osdu_wellbore.get_cleaned_ref_and_res_100()
    if kind == "osdu_wellbore_111":
        return crud.osdu_wellbore.get_cleaned_ref_and_res_111()
    if kind == "osdu_wellbore_120":
        return crud.osdu_wellbore.get_cleaned_ref_and_res_120()
    if kind == "osdu_well":
        return crud.osdu_well.get_cleaned_ref_and_res()
    if kind == "osdu_well_100":
        return crud.osdu_well.get_cleaned_ref_and_res_100()
    if kind == "osdu_well_110":
        return crud.osdu_well.get_cleaned_ref_and_res_110()
    if kind == "osdu_welllog":
        return crud.osdu_welllog.get_cleaned_ref_and_res()
    if kind == "osdu_wellboretrajectory":
        return crud.osdu_wellboretrajectory.get_cleaned_ref_and_res()
    if kind == "osdu_wellboremarkerset":
        return crud.osdu_wellboremarkerset.get_cleaned_ref_and_res()
    if kind == "osdu_wellboreintervalset_100":
        return crud.osdu_wellboreintervalset.get_cleaned_ref_and_res()
    if kind == "osdu_welllogacquisition":
        return crud.osdu_welllogacquisition.get_cleaned_ref_and_res()
    if kind == "osdu_ppfgdataset":
        return crud.osdu_ppfgdataset.get_cleaned_ref_and_res()


def diff_records(ref, res):
    return DeepDiff(ref, res, exclude_paths=[
        "root['acl']",
        "root['id']",
        "root['kind']",
        "root['legal']",
        "root['version']",
        "root['createTime']",
        "root['createUser']",
        "root['modifyUser']",
        "root['modifyTime']"
    ])


def diff_record_against_ref(kind: str, res_dict: dict):
    ref = get_cleaned_ref_and_res(kind)
    return diff_records(ref, res_dict)


def make_base_request_proto(method: str, path: str, name=None, payload=None, content_type='application/json'):
    import json
    if payload is not None and not isinstance(payload, str) and content_type == 'application/json':
        payload = json.dumps(payload)

    return Request(
        name=name or f"{method} - {path}",
        method=method,
        url='{{base_url}}' + path,
        headers={
            'accept': 'application/json',
            'data-partition-id': '{{data_partition}}',
            'Connection': '{{header_connection}}',
            'Authorization': 'Bearer {{token}}',
            'Content-Type': content_type
        },
        payload=payload
    )
