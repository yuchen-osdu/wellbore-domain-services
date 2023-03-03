# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http:#www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script executes the test and copies reports to the provided output directory
# To call this script from the service working directory
# ./dist/testing/tests/integration/build-aws/run-tests.sh "./reports/"
echo '********* Running Wellbore DDMS integration tests  *********'

SCRIPT_SOURCE_DIR=$(dirname "$0")
echo "$SCRIPT_SOURCE_DIR"

pushd "$SCRIPT_SOURCE_DIR"/../../../
echo $(pwd)
python3 -m venv env
source env/bin/activate
python3 -m pip install -r ./tests/aws-test/build-aws/requirements.txt
python3 -m pip install -r ./tests/aws-test/build-aws/requirements_dev.txt
rm -rf test-reports/
mkdir test-reports

export AWS_COGNITO_AUTH_PARAMS_USER=${ADMIN_USER} #set by env script
export AWS_COGNITO_AUTH_PARAMS_PASSWORD=${ADMIN_PASSWORD} #set by codebuild 
tenant='opendes'
acl_domain='example.com'
legal_tag='opendes-wellddmstestlegaltag'
token=$(python3 tests/aws-test/build-aws/aws_jwt_client.py)

echo 'Register Legal tag before Integration Tests ...'
curl --location --request POST "$LEGAL_URL"'legaltags' \
  --header 'accept: application/json' \
  --header 'authorization: Bearer '"$token" \
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

python3 gen_postman_env.py --token $token --base_url $WELLBORE_DDMS_URL --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=!search -p no:randomly

TEST_EXIT_CODE=$?

echo Delete legaltag after Integration Tests...
curl --location --request DELETE "$LEGAL_URL"'legaltags/opendes-wellddmstestlegaltag' \
--header 'Authorization: Bearer '"$token" \
--header 'data-partition-id: opendes' \
--header 'Content-Type: application/json'

deactivate


exit $TEST_EXIT_CODE
