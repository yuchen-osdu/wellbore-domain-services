
variables_dict = {
  "base_url": "https://open.opendes.cloud.slb-ds.com/api/os-wellbore-ddms",
  "token": "",
  "cloud_provider": "local",
  "dipsetKind": "{{data_partition}}:wks:dipSet:1.0.0",
  "wellKind": "{{data_partition}}:wks:well:1.0.2",
  "wellboreKind": "{{data_partition}}:wks:wellbore:1.0.6",
  "logSetKind": "{{data_partition}}:wks:logSet:1.0.5",
  "markerKind": "{{data_partition}}:wks:marker:1.0.4",
  "trajectoryKind": "{{data_partition}}:wks:trajectory:1.0.5",
  "logKind": "{{data_partition}}:wks:log:1.0.5",
  "acl_domain": "p4d.cloud.slb-ds.com",
  "acl_owner": "data.default.owners@{{data_partition}}.{{acl_domain}}",
  "acl_viewer": "data.default.viewers@{{data_partition}}.{{acl_domain}}",
  "legal_tag": "opendes-public-usa-dataset-1",
  "data_partition": "",
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

