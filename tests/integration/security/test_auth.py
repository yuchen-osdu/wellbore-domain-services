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

import requests
import pytest

payload = {}

wellbore_api_group_prefix = 'ddms/v2'

def build_url(base_url: str, path: str):
    return f"{base_url}/{wellbore_api_group_prefix}{path}"


@pytest.fixture
def skip_if_gcp_environment(base_url):
    """
        In GCP environment there is no AuthorizationPolicy set. Certain tests may fail on GCP
        and this fixture aims to skip a test case when targeted environment is GCP.
    """
    response = requests.request("GET", build_url(base_url, "/about"), verify=False)
    assert response.status_code == 200
    about_response = response.json()

    if about_response.get("cloudEnvironment") == "gcp":
        pytest.skip('skipped on this cloud provider because no AuthorizationPolicy in place')


# Test for expired token
def test_expired_token_returns_40X(base_url, check_cert, token):
    url = build_url(base_url, "/about")
    headers = {
        'Authorization': 'REMOVED_FOR_CICD_SCAN'
    }
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 401
    
# Test for no token on some paths where JWT token is NOT required due to the AuthorizationPolicy. Test to ensure headers are present for docs endpoint
def test_notoken_paths_returns_20X_docs(base_url, check_cert, token):
    
    url = f"{base_url}/docs"
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 200
    assert 'content-security-policy' in response.headers

# Test for no token on some paths where JWT token is NOT required due to the AuthorizationPolicy
@pytest.mark.parametrize("path", ["docs", "openapi.json", f"{wellbore_api_group_prefix}/about"])
def test_notoken_paths_returns_20X(base_url, check_cert, token, path):

    url = f"{base_url}/{path}"
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 200

# Test for no token on some paths where JWT token is required due to the AuthorizationPolicy
@pytest.mark.parametrize("path", ["version", "nonExistingPath"])
def test_notoken_returns_40X(base_url, check_cert, token, skip_if_gcp_environment, path):

    url = build_url(base_url, f"/{path}")
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 403
    assert "access denied" in response.text


# Test for invalid token
def test_invalid_token_returns_40X(base_url, check_cert, token):
    url = build_url(base_url, "/about")
    blank = {}
    token_invalid = token[0:len(token) - 10]
    headers = {
        'Authorization': f"REMOVED_FOR_CICD_SCAN'
    }

    response = requests.request("GET", url, headers=headers, data=blank, verify=check_cert)
    assert response.status_code == 401


# Test for unauthorized issuer
def test_invalid_issuer_token_returns_40X(base_url, check_cert, token):
    url = build_url(base_url, "/about")
    blank = {}
    headers = {
        'Authorization': 'REMOVED_FOR_CICD_SCAN'
    }
    response = requests.request("GET", url, headers=headers, data=blank, verify=check_cert)
    assert response.status_code == 401
