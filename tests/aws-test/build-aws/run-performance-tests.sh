#!/usr/bin/env bash
# from tests/aws-test/build-aws/ goes up to the tests dir.
cd ../../../

svc_url=$WELLBORE_DDMS_URL
tenant='opendes'
acl_domain='example.com'
legal_tag='opendes-wellddmstestlegaltag'
svctoken=$(python3 tests/aws-test/build-aws/aws_jwt_client.py)

cd tests/performance
mkdir -p results

echo 'Register Legal tag before Integration Tests ...'
curl --location --request POST "$LEGAL_URL"'legaltags' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer '"$svctoken" \
  --header 'content-type: application/json' \
  --header 'data-partition-id: opendes' \
  --data '{
        "name": "wellddmstestlegaltag",
        "description": "legal tag for Wellbore DMS Service Integration tests",
        "properties": {
            "countryOfOrigin":["US"],
            "contractId":"A1234",
            "expirationDate":"2099-01-25",
            "dataType":"Public Domain Data", 
            "originator":"MyCompany",
            "securityClassification":"Public",
            "exportClassification":"EAR99",
            "personalData":"No Personal Data"
        }
}'

independent_test_list=(
  writeMarkers
  writeWellbores
  writeWellLogMetadata
)

dependent_test_list=(
  writeWellLogData
  readMarkers
  readWellbores
  readWellLogData
  readWellLogMetadata
)

# Perform writes before search/read so environment is guaranteed to have data loaded provided the writes were successful
for test in ${independent_test_list[@]}; do 
  k6 run \
    -e API_BASE_URL=$WELLBORE_DDMS_URL \
    -e DATA_PARTITION_ID=$tenant \
    -e LEGAL_TAG=$legal_tag \
    -e ACL_DOMAIN=$acl_domain \
    -e TOKEN=$svctoken \
    --vus 100 \
    --iterations 100 \
    scripts/${test}.js \
    --out json=results/${test}_test_results.json
done

curl --location --request POST "$SEARCH_URL"'query' \
  --header 'Content-Type: application/json' \
  --header 'data-partition-id: opendes' \
  --header 'authorization: Bearer '"$svctoken" \
  --data-raw '
  {
      "kind": "opendes:osdu:marker:1.0.4"
  }' \
  | jq '.results[].id' | jq -s . > data/wellbore.json

curl --location --request POST "$SEARCH_URL"'query' \
  --header 'Content-Type: application/json' \
  --header 'data-partition-id: opendes' \
  --header 'authorization: Bearer '"$svctoken" \
  --data-raw '
  {
      "kind": "opendes:osdu:marker:1.0.4"
  }' \
  | jq '.results[].id' | jq -s . > data/marker.json

curl --location --request POST "$SEARCH_URL"'query' \
  --header 'Content-Type: application/json' \
  --header 'data-partition-id: opendes' \
  --header 'authorization: Bearer '"$svctoken" \
  --data-raw '
  {
      "kind": "opendes:wks:work-product-component--WellLog:1.1.0"
  }' \
  | jq '.results[].id' | jq -s . > data/welllog.json

for test in ${dependent_test_list[@]}; do 
  k6 run \
    -e API_BASE_URL=$WELLBORE_DDMS_URL \
    -e DATA_PARTITION_ID=$tenant \
    -e LEGAL_TAG=$legal_tag \
    -e ACL_DOMAIN=$acl_domain \
    -e TOKEN=$svctoken \
    --vus 100 \
    --iterations 100 \
    scripts/${test}.js \
    --out json=results/${test}_test_results.json
done

echo Delete legaltag after Integration Tests...
curl --location --request DELETE "$LEGAL_URL"'legaltags/opendes-wellddmstestlegaltag' \
--header 'Authorization: Bearer '"$svctoken" \
--header 'data-partition-id: opendes' \
--header 'Content-Type: application/json'
