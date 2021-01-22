# Indexation schemas

Indexation schemas are required to be able to query on some custom properties. Otherwise these fields are not indexed
 and only generic one are. Schema must be registered once for each data partition. This will eventually
 be part of the data provisioning but for the time being they are 'manually' registered. 

## schema
* [log.json](./log.json)
* [logSet.json](./logSet.json)
* [marker.json](./marker.json)
* [trajectory.json](./trajectory.json)
* [wellbore.json](./wellbore.json)
* [dipSet.json](./dipSet.json)

All schemas but dipSet come from [data-management/wke-schema repository](https://slb-swt.visualstudio.com/data-management/_git/wke-schema?path=%2Fdomains%2Fwell%2Fjson_schema)
and were put here manually (no sync). The dipSet has been created for the needs of WDMS v2.

We may update them to be adapted to wdms v2 needs (for instance, bulk reference instead of DELFI logstore id, or bulk at
 logset level ...). Potentially we'll adopt OSDU schemas instead of WKS defined by Schlumberger ([OSDU WellLog.json](https://gitlab.opengroup.org/osdu/json-schemas/-/blob/master/Generated/work-product-component/WellLog.json)). 


**WARNING**: The "kind" inside the json should be updated to correspond to the data partition:

e.g.
```
{
    "kind": "DATA_PARTITION_TAG:wks:log:1.0.5",
    "schema": ...
}
```
in case of data partition = `opendes` is must be updated to
```
{
    "kind": "opendes:wks:log:1.0.5",
    "schema": ...
}
```

 
## Commands

### Token
see [here](https://dev.azure.com/slb-des-ext-collaboration/open-data-ecosystem/_wiki/wikis/open-data-ecosystem.wiki/553/Authentication?anchor=get-an-sauth-token-from-an-sauth-service-account---sauth-v2) for token generation.


### cURL

given TOKEN, BASE_URL and DATA_PARTITION

```
curl \
--location \
--request GET "$BASE_URL/api/storage/v2/schemas/$DATA_PARTITION:wks:wellbore:1.0.6' \
--header "accept: application/json" \
--header "data-partition-id: $DATA_PARTITION" \
--header "Authorization: Bearer $TOKEN"
```