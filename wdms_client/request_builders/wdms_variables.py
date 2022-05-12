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
  "dipsetKind": "{{authorityKind}}:wks:dipSet:1.0.0",
  "wellKind": "{{authorityKind}}:wks:well:1.0.2",
  "wellboreKind": "{{authorityKind}}:wks:wellbore:1.0.6",
  "logSetKind": "{{authorityKind}}:wks:logSet:1.0.5",
  "markerKind": "{{authorityKind}}:wks:marker:1.0.4",
  "trajectoryKind": "{{authorityKind}}:wks:trajectory:1.0.5",
  "trajectory_data": {"name": "{{prefix_data_entity_name}}_trajectory"},
  "logKind": "{{authorityKind}}:wks:log:1.0.5",
  "authorityKind": "{{data_partition}}",
  "osduWellboreKind": "osdu:wks:master-data--Wellbore:1.0.0",
  "osduWellKind": "osdu:wks:master-data--Well:1.0.0",
  "osduWellLogKind": "osdu:wks:work-product-component--WellLog:1.2.0",
  "osduWellboreTrajectoryKind": "osdu:wks:work-product-component--WellboreTrajectory:1.1.0",
  "osduWellboreMarkerSetKind": "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
  "acl_domain": "p4d.cloud.slb-ds.com",
  "acl_owner": "data.default.owners@{{data_partition}}.{{acl_domain}}",
  "acl_viewer": "data.default.viewers@{{data_partition}}.{{acl_domain}}",
  "legal_tag": "opendes-public-usa-dataset-1",
  "data_partition": "",
  "prefix_data_entity_name": "wdms_e2e",
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

