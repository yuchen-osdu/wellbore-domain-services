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


def build_request(path: Union[str, List[str]], sep: str = ".") -> "RequestRunner":
    path = path.split(sep) if isinstance(path, str) else path
    n_path = ".".join([p.lower().replace(" ", "_") for p in path])
    if n_path == "crud.well.get_well":
        return crud.well.build_request_get_well()
    if n_path == "crud.well.delete_well":
        return crud.well.build_request_delete_well()
    if n_path == "crud.well.get_well_specific_version":
        return crud.well.build_request_get_well_specific_version()
    if n_path == "crud.well.get_versions_of_well":
        return crud.well.build_request_get_versions_of_well()
    if n_path == "crud.well.create_well":
        return crud.well.build_request_create_well()
    if n_path == "crud.wellbore.delete_wellbore":
        return crud.wellbore.build_request_delete_wellbore()
    if n_path == "crud.wellbore.get_wellbore_specific_version":
        return crud.wellbore.build_request_get_wellbore_specific_version()
    if n_path == "crud.wellbore.get_wellbore":
        return crud.wellbore.build_request_get_wellbore()
    if n_path == "crud.wellbore.get_versions_of_wellbore":
        return crud.wellbore.build_request_get_versions_of_wellbore()
    if n_path == "crud.wellbore.create_wellbore":
        return crud.wellbore.build_request_create_wellbore()
    if n_path == "crud.osdu_wellbore.delete_osdu_wellbore":
        return crud.osdu_wellbore.build_request_delete_osdu_wellbore()
    if n_path == "crud.osdu_wellbore.get_osdu_wellbore_specific_version":
        return crud.osdu_wellbore.build_request_get_osdu_wellbore_specific_version()
    if n_path == "crud.osdu_wellbore.get_osdu_wellbore":
        return crud.osdu_wellbore.build_request_get_osdu_wellbore()
    if n_path == "crud.osdu_wellbore.get_versions_of_osdu_wellbore":
        return crud.osdu_wellbore.build_request_get_versions_of_osdu_wellbore()
    if n_path == "crud.osdu_wellbore.create_osdu_wellbore":
        return crud.osdu_wellbore.build_request_create_osdu_wellbore()
    if n_path == "crud.osdu_well.delete_osdu_well":
        return crud.osdu_well.build_request_delete_osdu_well()
    if n_path == "crud.osdu_well.get_osdu_well_specific_version":
        return crud.osdu_well.build_request_get_osdu_well_specific_version()
    if n_path == "crud.osdu_well.get_osdu_well":
        return crud.osdu_well.build_request_get_osdu_well()
    if n_path == "crud.osdu_well.get_versions_of_osdu_well":
        return crud.osdu_well.build_request_get_versions_of_osdu_well()
    if n_path == "crud.osdu_well.create_osdu_well":
        return crud.osdu_well.build_request_create_osdu_well()
    if n_path == "crud.osdu_welllog.delete_osdu_welllog":
        return crud.osdu_welllog.build_request_delete_osdu_welllog()
    if n_path == "crud.osdu_welllog.get_osdu_welllog_specific_version":
        return crud.osdu_welllog.build_request_get_osdu_welllog_specific_version()
    if n_path == "crud.osdu_welllog.get_osdu_welllog":
        return crud.osdu_welllog.build_request_get_osdu_welllog()
    if n_path == "crud.osdu_welllog.get_versions_of_osdu_welllog":
        return crud.osdu_welllog.build_request_get_versions_of_osdu_welllog()
    if n_path == "crud.osdu_welllog.create_osdu_welllog":
        return crud.osdu_welllog.build_request_create_osdu_welllog()
    if n_path == "crud.logset.get_versions_of_logset":
        return crud.logset.build_request_get_versions_of_logset()
    if n_path == "crud.logset.get_logset_specific_version":
        return crud.logset.build_request_get_logset_specific_version()
    if n_path == "crud.logset.get_logset":
        return crud.logset.build_request_get_logset()
    if n_path == "crud.logset.delete_logset":
        return crud.logset.build_request_delete_logset()
    if n_path == "crud.logset.create_logset":
        return crud.logset.build_request_create_logset()
    if n_path == "crud.marker.delete_marker":
        return crud.marker.build_request_delete_marker()
    if n_path == "crud.marker.get_versions_of_marker":
        return crud.marker.build_request_get_versions_of_marker()
    if n_path == "crud.marker.get_marker":
        return crud.marker.build_request_get_marker()
    if n_path == "crud.marker.get_marker_specific_version":
        return crud.marker.build_request_get_marker_specific_version()
    if n_path == "crud.marker.create_marker":
        return crud.marker.build_request_create_marker()
    if n_path == "crud.trajectory.get_versions_of_trajectory":
        return crud.trajectory.build_request_get_versions_of_trajectory()
    if n_path == "crud.trajectory.get_trajectory":
        return crud.trajectory.build_request_get_trajectory()
    if n_path == "crud.trajectory.get_trajectory_specific_version":
        return crud.trajectory.build_request_get_trajectory_specific_version()
    if n_path == "crud.trajectory.delete_trajectory":
        return crud.trajectory.build_request_delete_trajectory()
    if n_path == "crud.trajectory.create_trajectory":
        return crud.trajectory.build_request_create_trajectory()
    if n_path == "crud.log.delete_log":
        return crud.log.build_request_delete_log()
    if n_path == "crud.log.get_versions_of_log":
        return crud.log.build_request_get_versions_of_log()
    if n_path == "crud.log.get_log_bulk_data":
        return crud.log.build_request_get_log_bulk_data()
    if n_path == "crud.log.get_log":
        return crud.log.build_request_get_log()
    if n_path == "crud.log.get_log_specific_version":
        return crud.log.build_request_get_log_specific_version()
    if n_path == "crud.log.create_log":
        return crud.log.build_request_create_log()
    if n_path == "crud.log.add_log_bulk_data":
        return crud.log.build_request_add_log_bulk_data()
    if n_path == "crud.dips.get_dipset":
        return crud.dips.build_request_get_dipset()
    if n_path == "crud.dips.query_dips":
        return crud.dips.build_request_query_dips()
    if n_path == "crud.dips.delete_dip":
        return crud.dips.build_request_delete_dip()
    if n_path == "crud.dips.create_dips":
        return crud.dips.build_request_create_dips()
    if n_path == "crud.dips.create__dipset":
        return crud.dips.build_request_create__dipset()
    if n_path == "crud.dips.insert_dips":
        return crud.dips.build_request_insert_dips()
    if n_path == "crud.dips.get_dip_from_index":
        return crud.dips.build_request_get_dip_from_index()
    if n_path == "crud.dips.delete_dipset":
        return crud.dips.build_request_delete_dipset()
    if n_path == "crud.dips.patch_dip":
        return crud.dips.build_request_patch_dip()
    if n_path == "crud.dips.get_dips":
        return crud.dips.build_request_get_dips()
    if n_path == "error_cases.create_log_with_invalid_data_should_422":
        return error_cases.build_request_create_log_with_invalid_data_should_422()
    if n_path == "model_extensibility.get_log_check_for_extra_fields":
        return model_extensibility.build_request_get_log_check_for_extra_fields()
    if n_path == "model_extensibility.clean_up_delete_log":
        return model_extensibility.build_request_clean_up_delete_log()
    if n_path == "model_extensibility.create_log_with_extra_fields":
        return model_extensibility.build_request_create_log_with_extra_fields()
    if n_path == "recursive_delete.setup.recusive_del_setup_end":
        return recursive_delete.setup.build_request_recursive_del_setup_end()
    if n_path == "recursive_delete.setup.recusive_del_setup_create_well":
        return recursive_delete.setup.build_request_recursive_del_setup_create_well()
    if n_path == "recursive_delete.setup.recusive_del_setup_check_state_start":
        return recursive_delete.setup.build_request_recursive_del_setup_check_state_start()
    if n_path == "recursive_delete.setup.recusive_del_setup_create_logs":
        return recursive_delete.setup.build_request_recursive_del_setup_create_logs()
    if n_path == "recursive_delete.setup.recusive_del_setup_create_logset":
        return recursive_delete.setup.build_request_recursive_del_setup_create_logset()
    if n_path == "recursive_delete.setup.recusive_del_setup_create_wellbore":
        return recursive_delete.setup.build_request_recursive_del_setup_create_wellbore()
    if n_path == "recursive_delete.setup.recusive_del_setup_create_record_refs":
        return recursive_delete.setup.build_request_recursive_del_setup_create_record_refs()
    if n_path == "recursive_delete.delete_well.check_logset_is_deleted":
        return recursive_delete.delete_well.build_request_check_logset_is_deleted()
    if n_path == "recursive_delete.delete_well.recursive_delete_well":
        return recursive_delete.delete_well.build_request_recursive_delete_well()
    if n_path == "recursive_delete.delete_well.check_log_is_deleted":
        return recursive_delete.delete_well.build_request_check_log_is_deleted()
    if n_path == "recursive_delete.delete_well.check_wellbore_is_deleted":
        return recursive_delete.delete_well.build_request_check_wellbore_is_deleted()
    if n_path == "search_apis.setup.seach_tests_setup_end":
        return search_apis.setup.build_request_seach_tests_setup_end()
    if n_path == "search_apis.setup.seach_tests_setup_create_logsets":
        return search_apis.setup.build_request_seach_tests_setup_create_logsets()
    if n_path == "search_apis.setup.seach_tests_setup_create_record_refs":
        return search_apis.setup.build_request_seach_tests_setup_create_record_refs()
    if n_path == "search_apis.setup.seach_tests_setup_create_logs":
        return search_apis.setup.build_request_seach_tests_setup_create_logs()
    if n_path == "search_apis.setup.seach_tests_setup_create_wellbore":
        return search_apis.setup.build_request_seach_tests_setup_create_wellbore()
    if n_path == "search_apis.setup.seach_tests_setup_create_markers":
        return search_apis.setup.build_request_seach_tests_setup_create_markers()
    if n_path == "search_apis.setup.seach_tests_setup_start":
        return search_apis.setup.build_request_seach_tests_setup_start()
    if n_path == "search_apis.search.search_logs_by_logset_id":
        return search_apis.search.build_request_search_logs_by_logset_id()
    if n_path == "search_apis.search.search_markers_by_wellbore_id":
        return search_apis.search.build_request_search_markers_by_wellbore_id()
    if n_path == "search_apis.search.search_wellbores_by_geo_polygon":
        return search_apis.search.build_request_search_wellbores_by_geo_polygon()
    if n_path == "search_apis.search.search_logs_by_wellbore_id":
        return search_apis.search.build_request_search_logs_by_wellbore_id()
    if n_path == "search_apis.search.search_logset_by_wellbores_attribute":
        return search_apis.search.build_request_search_logset_by_wellbores_attribute()
    if n_path == "search_apis.search.search_logs_by_wellbores_attribute":
        return search_apis.search.build_request_search_logs_by_wellbores_attribute()
    if n_path == "search_apis.search.search_wellbores_by_bounding_box":
        return search_apis.search.build_request_search_wellbores_by_bounding_box()
    if n_path == "search_apis.search.search_wellbores_by_distance":
        return search_apis.search.build_request_search_wellbores_by_distance()
    if n_path == "search_apis.search.search_logs_by_logsets_attribute":
        return search_apis.search.build_request_search_logs_by_logsets_attribute()
    if n_path == "search_apis.search.search_logset_by_wellbore_id":
        return search_apis.search.build_request_search_logset_by_wellbore_id()
    if n_path == "about":
        return about.build_request_about()
    if n_path == "version":
        return version.build_request_version()
    if n_path == "status":
        return status.build_request_status()

    raise ValueError(f'No request matches the path {n_path}')


def get_cleaned_ref_and_res(kind: str, res_dict: dict) -> (dict, dict):
    if kind =="osdu_wellbore":
        return crud.osdu_wellbore.get_cleaned_ref_and_res(res_dict)
    if kind =="osdu_well":
        return crud.osdu_well.get_cleaned_ref_and_res(res_dict)
    if kind =="osdu_welllog":
        return crud.osdu_welllog.get_cleaned_ref_and_res(res_dict)
