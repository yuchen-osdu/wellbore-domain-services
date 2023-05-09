# Know schemas

Put in  `known_schemas` folder the list of the schemas WDMS will load directly at startup.  
Doing this will prevent from doing useless calls to schema service (unknown schemas are retrieved using a call to schema service).

## Expected format

The schemas should be self contained, i.e. without external references.  
Schema service GET /schema/{id} returns the schemas in the expected format.

## How to get those files using schema service

Example for Wellbore 1.2.0 schemas

`
curl -X 'GET' \
  'https://api.example.com/api/schema-service/v1/schema/osdu%3Awks%3Amaster-data--Well%3A1.2.0' -H 'accept: application/json' -H 'data-partition-id: opendes' -H 'Authorization: my_bearer'
`

replacing `api.example.com` by the actual OSDU deployment URL