# Wellbore DDMS performance test :
This folder contains the scripts to run wellbore ddms performance tests. Wellbore ddms uses an open-source K6 to run the performance tests and the script is written in plain Javascript. for more information about K6 head to [K6 Documentaion](https://k6.io/docs/)

### Getting started :
Before running the tests, make sure you have the K6 CLI installed locally you can make sure you do by running `k6 version` the console output should look like: `k6 v0.26.2 (2020-03-18T11:45:39+0000/v0.26.2-0-g459da79e, go1.13.8, windows/amd64)`.
If you don't have the K6 CLI installed, you can install it by going to [K6 Getting Started / Installation](https://k6.io/docs/getting-started/installation).

### Test scripts :
| Script name | Description | API |
| - | - | - |
| `readLogMetadata.js`  | Retrieves a log metadata | **GET**  /ddms/v2/log |
| `writeLogMetadata.js` | Creates a log metadata   | **POST** /ddms/v2/log |
| `readLogData.js`      | Retrieves a log bulkdata | **GET**   /ddms/v2/log/{logid}/data |
| `writeLogData.js`     | Creates a log bulkdata   | **POST** /ddms/v2/log/{logid}/data |
| `readMarkers.js`      | Retrieves a marker       | **GET**   /ddms/v2/markers/{markerid} |
| `writeMarkers.js`     | Creates a marker         | **POST** /ddms/v2/markers  |
| `readWellbores.js`    | Retrieves a wellbore     | **GET**   /ddms/v2/wellbores/{wellboreid} |
| `writeWellbores.js`   | Creates a wellbore       | **POST** /ddms/v2/wellbores |

The `common.js` file contains functions to help with tests

### Test variables :
For the test scripts to run properly we need to pass some variables to the tests (auth tokens, data partition id, legal tags, ...). To pass a variable to a K6 script, you can do it by adding `-e SOME_VAR=SOME_VAL`. Example : `k6 run script.js -e SOME_VAR=SOME_VAL`. To learn more about environment variables and k6 [K6 / Environment variables
](https://k6.io/docs/using-k6/environment-variables).

Here is a list of the environment variables used by wellbore ddms scripts :
| Name | Description |
| - | - |
| `API_BASE_URL` | The base URL of the API |
| `DATA_PARTITION_ID` | The data partition id used for the test |
| `ACL_DOMAIN` | The domain name for the access control list |
| `LEGAL_TAG` | The legal tags used for the test |
| `TOKEN` | The authentication token (in form of JWT) to make authenticated requests |

### Test data :
In the folder `data` you might have noticed some JSON files. These JSON files contain valid record ids, these ids are used by the read scripts.

| File name | Description |
| - | - |
| `log.json` | A JSON file contains an array of valid log records |
| `marker.json` | A JSON file contains an array of valid markers records |
| `wellbore.json` | A JSON file contains an array of valid wellbores records |

This data is very important for the read tests to work without it those tests will fail

### Running the tests :
To run a test all you need to do is to run `k6 run #script_name.js#` with the environment variables we specified earlier. You can also specify the number of concurrent users and/or the number of iterations per test cycle.

#### Detailed example :
To run a write log metadata test with 100 concurrent users and 100 iterations (**Note**: the number of iterations should be greater than the number of concurrent users - also called VUS or virtual users)

```
k6 run \
    -e API_BASE_URL="" \
    -e DATA_PARTITION_ID="" \
    -e LEGAL_TAG="" \
    -e ACL_DOMAIN="" \
    -e TOKEN="" \
    --vus 100 \
    --iterations 100 \
    ./scripts/writeLogMetadata.js
```