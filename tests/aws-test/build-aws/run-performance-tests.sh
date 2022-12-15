#!/usr/bin/env bash
# from tests/aws-test/build-aws/ goes up to the tests dir.
cd ../../../

svc_url=$WELLBORE_DDMS_URL
tenant='opendes'
acl_domain='example.com'
legal_tag='opendes-wellddmstestlegaltag'
svctoken=$(python3 tests/aws-test/build-aws/aws_jwt_client.py)

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
cd tests/performance

for filename in scripts/*.js; do 
  test_name=$(basename $filename .js)

  k6 run \
    -e API_BASE_URL=$WELLBORE_DDMS_URL \
    -e DATA_PARTITION_ID=$tenant \
    -e LEGAL_TAG=$legal_tag \
    -e ACL_DOMAIN=$acl_domain \
    -e TOKEN=$svctoken \
    --vus 100 \
    --iterations 100 \
    $filename \
    --out json=${test_name}_test_results.json
done

echo Delete legaltag after Integration Tests...
curl --location --request DELETE "$LEGAL_URL"'legaltags/opendes-wellddmstestlegaltag' \
--header 'Authorization: Bearer '"$svctoken" \
--header 'data-partition-id: opendes' \
--header 'Content-Type: application/json'
