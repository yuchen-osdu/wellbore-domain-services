## Authentication (JWT) tests

Run integration tests for authentication which checks for common misconfigurations in JWT signing and validation:

- expired token
- missing token
- unsigned token
- self-signed token
- invalid token

## Setup Pre-Requisities

```bash
pip install -r requirements_dev.txt
```

## Run Security Tests Locally

### Pass Options to Test

The tests expect the following arguments in order to run and these can be set when running `pytest test_auth.py`
- base_url: url of the api that is being tested
- check_cert: boolean to skip the cert validation
    - For False - pass in an empty string
    - For True - pass in "True"
- token: valid token

### Run Tests

Run the python script with arguments: 

```bash
# set options 
export base_url="<appurl>"
export check_cert="<boolean to skip the cert validation>"
export token="<valid token>"

# navigate to the security integration tests directory
cd tests/integration/security

# run the tests
pytest test_auth.py --base_url $base_url --check_cert $check_cert --token $token
```

### Notes

Issues encountered: 

- Depending on the run environment, the pyjwt and jwt can have conflicts. https://github.com/jpadilla/pyjwt/issues/374
- pyjwt needs cryptography package to use RS256 signing algorithm https://github.com/jpadilla/pyjwt/issues/230
- pip does not collect the correct packages with older python versions or when "use python version 3.X" task is missing