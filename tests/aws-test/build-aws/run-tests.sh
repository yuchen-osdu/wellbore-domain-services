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
# ./dist/testing/integration/build-aws/run-tests.sh "./reports/"
echo '********* Running Wellbore DDMS integration tests  *********'

echo $(pwd)

AWS_COGNITO_PWD=$ADMIN_PASSWORD
AWS_COGNITO_USER=$ADMIN_USER
client_id=$AWS_COGNITO_CLIENT_ID
svc_url=$WELLBORE_DDMS_URL
tenant='opendes'
acl_domain='testing.com' 
legal_tag='opendes-sdmstestlegaltag'

#### RUN INTEGRATION TEST #########################################################################

echo 'Generating token...'
token=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id $client_id --auth-parameters USERNAME=$AWS_COGNITO_USER,PASSWORD=$AWS_COGNITO_PWD --output=text --query AuthenticationResult.{AccessToken:AccessToken})

#### RUN INTEGRATION TEST #########################################################################

cd deployment/osdu-core/os-wellbore-domain-services/testing

pip install -r ./aws-test/build-aws/requirements.txt
rm -rf test-reports/
mkdir test-reports

cd indexation

schemaFiles=$(ls *.json)
for schemaFile in $schemaFiles 
do
    echo "loading $schemaFile: "
    schema=$(sed "s/DATA_PARTITION_TAG/${tenant}/" ${schemaFile})
    echo $schema | head -c 100
    echo "..."

    curl \
    --location \
    --request POST "${AWS_BASE_URL}/api/storage/v2/schemas" \
    --header "Content-Type: application/json" \
    --header "data-partition-id: ${tenant}" \
    --header "Authorization: Bearer ${token}" \
    --data-raw "${schema}"

    echo ""
    echo "---"
done
cd ..

cd integration

acl_domain='testing.com' 
legal_tag='opendes-sdmstestlegaltag'

python gen_postman_env.py --token $token --base_url $svc_url --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=basic

TEST_EXIT_CODE=$?
exit $TEST_EXIT_CODE