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
import datetime
import jwt

payload = {}


def test_expired_token_returns_40X(base_url, check_cert, token):
    url = f"{base_url}/about"
    token_expired = jwt.encode({"email":"nobody@example.com", "exp":datetime.datetime.utcnow() - datetime.timedelta(seconds=300)}, key="secret", algorithm="HS256")
    headers = {
        'Authorization': f"Bearer {token_expired}"
    }
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 401
    

def test_content_security_header_docs(base_url, check_cert, token):
    
    url = f"{base_url}/docs"
    headers = {
        'Authorization': f"Bearer {token}"
    }
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 200
    assert 'content-security-policy' in response.headers


# Test for no token on some paths where JWT token is required due to the AuthorizationPolicy
@pytest.mark.parametrize("path", ["docs", "openapi.json", "about", "version", "nonExistingPath"])
def test_notoken_returns_403(base_url, check_cert, token, path):

    url = f"{base_url}/{path}"
    headers = {}
    response = requests.request("GET", url, headers=headers, data=payload, verify=check_cert)
    assert response.status_code == 403
    assert "access denied" in response.text


def test_invalid_token_returns_40X(base_url, check_cert, token):
    url = f"{base_url}/about"
    blank = {}
    token_invalid = token[0:len(token) - 10]
    headers = {
        'Authorization': f"Bearer {token_invalid}"
    }

    response = requests.request("GET", url, headers=headers, data=blank, verify=check_cert)
    assert response.status_code == 401


# Test for unauthorized issuer
def test_invalid_issuer_token_returns_40X(base_url, check_cert, token):
    url = f"{base_url}/about"
    blank = {}
    token_no_iss = jwt.encode({"email": "nobody@example.com"}, key="secret", algorithm="HS256")
    headers = {
        'Authorization': f"Bearer {token_no_iss}"
    }
    response = requests.request("GET", url, headers=headers, data=blank, verify=check_cert)
    assert response.status_code in [401, 403]
