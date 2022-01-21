#!/usr/bin/env bash
# from tests/aws-test/build-aws/ goes up to the tests dir.
cd ../../../

# Install venv for python3
which apt-get && sudo apt-get install -y python3 python3-pip python3-venv || echo "Not Ubuntu, skipping"
which yum && sudo yum install -y python3 python3-pip python3-venv || echo "Not RHEL, skipping"

python3 -m venv env
source env/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip install -r requirements_dev.txt
python3 -m pip install wheel pytest pytest-cov

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
cd tests/integration

python3 gen_postman_env.py --token $svctoken --base_url $svc_url --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=!search

echo Delete legaltag after Integration Tests...
curl --location --request DELETE "$LEGAL_URL"'legaltags/opendes-wellddmstestlegaltag' \
--header 'Authorization: Bearer '"$svctoken" \
--header 'data-partition-id: opendes' \
--header 'Content-Type: application/json'
