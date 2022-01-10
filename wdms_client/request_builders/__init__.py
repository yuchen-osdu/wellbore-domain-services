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

from typing import Union, List
from .wdms import about
from .wdms import version
from .wdms import status
from .wdms import crud
from .wdms import error_cases
from .wdms import model_extensibility
from .wdms import recursive_delete
from .wdms import search_apis
from deepdiff import DeepDiff

request_path_dict = {
    "crud.well.get_well":
        crud.well.build_request_get_well,
    "crud.well.delete_well":
        crud.well.build_request_delete_well,
    "crud.well.get_well_specific_version":
        crud.well.build_request_get_well_specific_version,
    "crud.well.get_versions_of_well":
        crud.well.build_request_get_versions_of_well,
    "crud.well.create_well":
        crud.well.build_request_create_well,
    "crud.wellbore.delete_wellbore":
        crud.wellbore.build_request_delete_wellbore,
    "crud.wellbore.get_wellbore_specific_version":
        crud.wellbore.build_request_get_wellbore_specific_version,
    "crud.wellbore.get_wellbore":
        crud.wellbore.build_request_get_wellbore,
    "crud.wellbore.get_versions_of_wellbore":
        crud.wellbore.build_request_get_versions_of_wellbore,
    "crud.wellbore.create_wellbore":
        crud.wellbore.build_request_create_wellbore,
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
    "crud.logset.get_versions_of_logset":
        crud.logset.build_request_get_versions_of_logset,
    "crud.logset.get_logset_specific_version":
        crud.logset.build_request_get_logset_specific_version,
    "crud.logset.get_logset":
        crud.logset.build_request_get_logset,
    "crud.logset.delete_logset":
        crud.logset.build_request_delete_logset,
    "crud.logset.create_logset":
        crud.logset.build_request_create_logset,
    "crud.marker.delete_marker":
        crud.marker.build_request_delete_marker,
    "crud.marker.get_versions_of_marker":
        crud.marker.build_request_get_versions_of_marker,
    "crud.marker.get_marker":
        crud.marker.build_request_get_marker,
    "crud.marker.get_marker_specific_version":
        crud.marker.build_request_get_marker_specific_version,
    "crud.marker.create_marker":
        crud.marker.build_request_create_marker,
    "crud.trajectory.get_versions_of_trajectory":
        crud.trajectory.build_request_get_versions_of_trajectory,
    "crud.trajectory.get_trajectory":
        crud.trajectory.build_request_get_trajectory,
    "crud.trajectory.get_trajectory_specific_version":
        crud.trajectory.build_request_get_trajectory_specific_version,
    "crud.trajectory.delete_trajectory":
        crud.trajectory.build_request_delete_trajectory,
    "crud.trajectory.create_trajectory":
        crud.trajectory.build_request_create_trajectory,
    "crud.log.delete_log":
        crud.log.build_request_delete_log,
    "crud.log.get_versions_of_log":
        crud.log.build_request_get_versions_of_log,
    "crud.log.get_log_bulk_data":
        crud.log.build_request_get_log_bulk_data,
    "crud.log.get_log":
        crud.log.build_request_get_log,
    "crud.log.get_log_specific_version":
        crud.log.build_request_get_log_specific_version,
    "crud.log.create_log":
        crud.log.build_request_create_log,
    "crud.log.add_log_bulk_data":
        crud.log.build_request_add_log_bulk_data,
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
    "recursive_delete.setup.recusive_del_setup_end":
        recursive_delete.setup.build_request_recursive_del_setup_end,
    "recursive_delete.setup.recusive_del_setup_create_well":
        recursive_delete.setup.build_request_recursive_del_setup_create_well,
    "recursive_delete.setup.recusive_del_setup_check_state_start":
        recursive_delete.setup.build_request_recursive_del_setup_check_state_start,
    "recursive_delete.setup.recusive_del_setup_create_logs":
        recursive_delete.setup.build_request_recursive_del_setup_create_logs,
    "recursive_delete.setup.recusive_del_setup_create_logset":
        recursive_delete.setup.build_request_recursive_del_setup_create_logset,
    "recursive_delete.setup.recusive_del_setup_create_wellbore":
        recursive_delete.setup.build_request_recursive_del_setup_create_wellbore,
    "recursive_delete.setup.recusive_del_setup_create_record_refs":
        recursive_delete.setup.build_request_recursive_del_setup_create_record_refs,
    "recursive_delete.delete_well.check_logset_is_deleted":
        recursive_delete.delete_well.build_request_check_logset_is_deleted,
    "recursive_delete.delete_well.recursive_delete_well":
        recursive_delete.delete_well.build_request_recursive_delete_well,
    "recursive_delete.delete_well.check_log_is_deleted":
        recursive_delete.delete_well.build_request_check_log_is_deleted,
    "recursive_delete.delete_well.check_wellbore_is_deleted":
        recursive_delete.delete_well.build_request_check_wellbore_is_deleted,
    "search_apis.setup.seach_tests_setup_end":
        search_apis.setup.build_request_seach_tests_setup_end,
    "search_apis.setup.seach_tests_setup_create_logsets":
        search_apis.setup.build_request_seach_tests_setup_create_logsets,
    "search_apis.setup.seach_tests_setup_create_record_refs":
        search_apis.setup.build_request_seach_tests_setup_create_record_refs,
    "search_apis.setup.seach_tests_setup_create_logs":
        search_apis.setup.build_request_seach_tests_setup_create_logs,
    "search_apis.setup.seach_tests_setup_create_wellbore":
        search_apis.setup.build_request_seach_tests_setup_create_wellbore,
    "search_apis.setup.seach_tests_setup_create_markers":
        search_apis.setup.build_request_seach_tests_setup_create_markers,
    "search_apis.setup.seach_tests_setup_start":
        search_apis.setup.build_request_seach_tests_setup_start,
    "search_apis.search.search_logs_by_logset_id":
        search_apis.search.build_request_search_logs_by_logset_id,
    "search_apis.search.search_markers_by_wellbore_id":
        search_apis.search.build_request_search_markers_by_wellbore_id,
    "search_apis.search.search_wellbores_by_geo_polygon":
        search_apis.search.build_request_search_wellbores_by_geo_polygon,
    "search_apis.search.search_logs_by_wellbore_id":
        search_apis.search.build_request_search_logs_by_wellbore_id,
    "search_apis.search.search_logset_by_wellbores_attribute":
        search_apis.search.build_request_search_logset_by_wellbores_attribute,
    "search_apis.search.search_logs_by_wellbores_attribute":
        search_apis.search.build_request_search_logs_by_wellbores_attribute,
    "search_apis.search.search_wellbores_by_bounding_box":
        search_apis.search.build_request_search_wellbores_by_bounding_box,
    "search_apis.search.search_wellbores_by_distance":
        search_apis.search.build_request_search_wellbores_by_distance,
    "search_apis.search.search_logs_by_logsets_attribute":
        search_apis.search.build_request_search_logs_by_logsets_attribute,
    "search_apis.search.search_logset_by_wellbore_id":
        search_apis.search.build_request_search_logset_by_wellbore_id,
    "about":
        about.build_request_about,
    "version":
        version.build_request_version,
    "status":
        status.build_request_status,
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
    if kind == "osdu_well":
        return crud.osdu_well.get_cleaned_ref_and_res()
    if kind == "osdu_welllog":
        return crud.osdu_welllog.get_cleaned_ref_and_res()
    if kind == "osdu_wellboretrajectory":
        return crud.osdu_wellboretrajectory.get_cleaned_ref_and_res()
    if kind == "osdu_wellboremarkerset":
        return crud.osdu_wellboremarkerset.get_cleaned_ref_and_res()


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
