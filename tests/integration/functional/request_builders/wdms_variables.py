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


variables_dict = {
  "base_url": "https://open.opendes.cloud.slb-ds.com/api/os-wellbore-ddms",
  "token": "",
  "cloud_provider": "local",
  "base_url_entity": "logs",
  "entity_kind": "{{logKind}}",
  "dipsetKind": "{{data_partition}}:wks:dipSet:1.0.0",
  "wellKind": "{{data_partition}}:wks:well:1.0.2",
  "wellboreKind": "{{data_partition}}:wks:wellbore:1.0.6",
  "logSetKind": "{{data_partition}}:wks:logSet:1.0.5",
  "markerKind": "{{data_partition}}:wks:marker:1.0.4",
  "trajectoryKind": "{{data_partition}}:wks:trajectory:1.0.5",
  "trajectory_data": {"name": "wdms_e2e_trajectory"},
  "logKind": "{{data_partition}}:wks:log:1.0.5",
  "osduWellboreKind": "{{data_partition}}:wks:master-data--Wellbore:1.0.0",
  "osduWellKind": "{{data_partition}}:wks:master-data--Well:1.0.0",
  "osduWellLogKind": "{{data_partition}}:wks:work-product-component--WellLog:1.0.0",
  "osduWellboreTrajectoryKind": "{{data_partition}}:wks:work-product-component--WellboreTrajectory:1.0.0",
  "acl_domain": "p4d.cloud.slb-ds.com",
  "acl_owner": "data.default.owners@{{data_partition}}.{{acl_domain}}",
  "acl_viewer": "data.default.viewers@{{data_partition}}.{{acl_domain}}",
  "legal_tag": "opendes-public-usa-dataset-1",
  "data_partition": "",
  "data": {},
  "search_record_version": "0001",
  "record_acl": {
                    "owners": ["{{acl_owner}}"],
                    "viewers": ["{{acl_viewer}}"]
                },
  "record_legal": {
                    "legaltags": ["{{legal_tag}}"],
                    "otherRelevantDataCountries": ["US", "FR"]
                },
  "header_connection": "close"
}

