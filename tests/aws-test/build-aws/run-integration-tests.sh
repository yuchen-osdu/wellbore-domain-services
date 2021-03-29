echo "**********Current Dir ***********************"
echo $(pwd)
echo $(ls)

echo "*********Am I at tests dir???**********"
cd ../../../
echo $(pwd)
echo $(ls)

pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install --upgrade pip
pip install wheel pytest pytest-cov
pip install -r requirements.txt
pip install -r requirements_dev.txt

svc_url=$WELLBORE_DDMS_URL
tenant='opendes'
acl_domain='testing.com' 
legal_tag='opendes-sdmstestlegaltag'
svctoken=$(python tests/aws-test/build-aws/aws_jwt_client.py)

cd tests/integration

python gen_postman_env.py --token $svctoken --base_url $svc_url --cloud_provider "aws" --acl_domain $acl_domain --legal_tag $legal_tag --data_partition $tenant

pytest ./functional --environment="./generated/postman_environment.json" --filter-tag=basic