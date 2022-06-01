In this tutorial we will explain:

* How to get bulk statistics on WellLog data created
  * after OSDU M12 release: statistics computation is automatic
  * before OSDU M12 release: statistics computation is manual
  
* Fetch WellLog bulk statistics code examples


Computable WellLog's curves data types are: integer, float and date/datetime.

# 1. Prerequisites

## Required Python packages


```bash
!python -m pip install pip --upgrade
!pip install httpx pandas pyarrow
```
   

## Authorization
For any call to Wellbore DDMS API's you need to pass into the header of the request a valid bearer token. This token can be obtained from any API catalog on the developer portal. You will need first to request a developer base subscription. Then from the developer base subscription pick any API and execute it. A valid bearer token is returns in the Curl section of the response. Copy this token value and assign it to the TOKEN variable below.


```python
TOKEN = '' # Paste here the token without the bearer prefix
```

## Utility methods
Below is a list of helper functions used in the different sample scripts of this tutorial.


```python
from typing import List
import time
from datetime import datetime
import io
import asyncio
from itertools import chain
import itertools
import psutil
import copy
from IPython.display import JSON

import httpx

import pandas as pd 
import pyarrow.parquet as pq
import pyarrow as pa
import numpy as np


def generate_df(columns: List[str], index):
    nbrows = len(index)
    df = pd.DataFrame(
        np.random.randint(-100, 1000, size=(nbrows, len(columns))), index=index)
    df.columns = columns
    return df

def generate_df_typed(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('bool'):
            return np.random.choice(a=[False, True], size=size) 
        if col_name.startswith('date'):
            return pd.date_range(start='2021-01-01', freq='ms', periods=size)
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                      for c in columns}, index=index)
    return df

def add_nan_values_to_df(_df):
    cols_with_nan = [c for c in _df.columns if c.endswith('nan')]
    for col_with_nan in cols_with_nan:
        _df.loc[_df.sample(frac=0.15).index, col_with_nan] = np.nan
            
def print_response(resp):
    print(f'{resp.request.method} : {resp.url} -> {resp.status_code}')
    if resp.status_code != httpx.codes.OK:
        display(resp.content)
    
def create_df_from_response(response):
    f = io.BytesIO(response.content)
    f.seek(0)

    content_type = response.headers.get('content-type')
    if content_type == 'application/x-parquet':
        return pd.read_parquet(f)
    elif content_type == 'text/csv; charset=utf-8':
        return pd.read_csv(f, index_col=0)
    elif content_type == 'application/json':
        return pd.read_json(f, dtype=True, orient='split', convert_axes=False)
    else:
        raise ValueError(f"Unknown content-type: '{content_type}'")

def create_df_from_dict(response):
    assert response.headers.get('content-type') == 'application/json'
    
    dict_data = response.json()['data']
    return pd.DataFrame.from_dict(dict_data, orient='index')

def response_copy_without_data(welllog_stats_response):
    json_stats_copy = copy.copy(welllog_stats_response.json())
    if 'data' in json_stats_copy:
        del json_stats_copy['data']
    return json_stats_copy

```

## Settings

Several settings as the base url end-point and the data partition id to create a WellLog to the Wellbore DDMS. Please change those settings accordingly to the environment settings that you want to target.


```python
base_url = '' # set a base URL value
data_partition = '' # set a data partition id
legal_tag = '' # set a valid legal tag in the data partition 
acl_domain = '' # set an Access Control Lists (ACL) domain

welllog_url = f'{base_url}/api/os-wellbore-ddms/ddms/v3/welllogs'

headers = {
        "data-partition-id": data_partition,
        "Authorization": f"Bearer {TOKEN}"
}

client = httpx.Client(verify=False,
    headers=headers,
    timeout=300
)

aclient = httpx.AsyncClient(verify=False,
    headers=headers,
    timeout=300
)
```

# 2. How to trigger WellLog bulk data statistics computation



## 2.1. For WellLogs created or updated AFTER the OSDU M12 release 
Computation of WellLog bulk statistics will be triggered automatically when updating WellLog bulk data using: Chunking or POST data APIs.  

1. Send data: all at once or by chunks
2. Wait for statistics to be computed in background...

Below an example, using POST data API, that push WellLog data: 8 curves with DIFFERENT data type of 100k rows each:

### Create WellLog record
```python
record = {
    "kind": f"{data_partition}:wks:work-product-component--WellLog:1.0.0",
    "acl": {
        "viewers": [f"data.default.viewers@{data_partition}.{acl_domain}"],
        "owners": [f"data.default.owners@{data_partition}.{acl_domain}"]
      },
    "legal": {
        "legaltags": [legal_tag],
        "otherRelevantDataCountries": ["US"],
    },
    "data": {
        "Curves": [
            {"CurveID": 'int-A'},
            {"CurveID": 'int-A-with-nan'},
            {"CurveID": 'float-B'},
            {"CurveID": 'float-B-with-nan'}, 
            {"CurveID": 'date-C'}, 
            {"CurveID": 'date-C-with-nan'},
            {"CurveID": 'bool-D'},
            {"CurveID": 'string-E'},
        ]
    },
}

response_typed = client.post(welllog_url, json=[record])
print_response(response_typed)
types_col_record_id = response_typed.json()["recordIds"][0]
print(types_col_record_id)
```

    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs -> 200
    

### POST WellLog data


```python
columns = ['int-A', 'int-A-with-nan', 'float-B', 'float-B-with-nan', 'bool-D', 'string-E', 'date-C', 'date-C-with-nan']

different_type_df = generate_df_typed(columns, range(100_000))
add_nan_values_to_df(different_type_df)
display(different_type_df)

data_to_send = different_type_df.to_parquet(engine='pyarrow')

write_response = client.post(f'{welllog_url}/{types_col_record_id}/data', data=data_to_send, headers={'content-type': 'application/parquet'})
print_response(write_response)
```

| 	         | int-A | int-A-with-nan | float-B  | float-B-with-nan | 	bool-D | string-E            | date-C                   | date-C-with-nan         |
|-----------|-------|----------------|----------|------------------|---------|---------------------|--------------------------|-------------------------|
| **0**     | 	868  | 592.0          | 0.792575 | 0.113692         | False   | string_value_0      | 2021-01-01 00:00:00.000	 | 2021-01-01 00:00:00.000 |
| **1**     | 	222  | 624.0          | 0.529602 | 0.047647         | True    | string_value_1      | 2021-01-01 00:00:00.001  | NaT                     |
| **2**     | 	842  | 359.0          | 0.184516 | 0.783715         | True    | string_value_2      | 2021-01-01 00:00:00.002  | NaT                     |
| **3**     | 	879  | 280.0          | 0.526019 | 0.288487         | False   | string_value_3      | 2021-01-01 00:00:00.003  | NaT                     |
| **4**     | 	456  | 619.0          | 0.512207 | 0.373447         | True    | string_value_4      | 2021-01-01 00:00:00.004	 | 2021-01-01 00:00:00.004 |
| **...**   | ...   | ...            | ...      | ...              | ...     | 	...                | 	...                     | 	...                    |
| **99995** | 	560  | 	220.0         | 0.714021 | 0.064975	        | False   | string_value_99995  | 2021-01-01 00:01:39.995  | 2021-01-01 00:01:39.995 |
| **99996** | 	861  | 	78.0          | 0.663497 | 0.560253	        | False   | string_value_99996  | 2021-01-01 00:01:39.996  | 2021-01-01 00:01:39.996 |
| **99997** | 	916  | 	100.0         | 0.687259 | NaN              | False   | string_value_99997	 | 2021-01-01 00:01:39.997  | 2021-01-01 00:01:39.997 |
| **99998** | 	354  | 	933.0         | 0.563194 | 0.921421         | False   | string_value_99998	 | 2021-01-01 00:01:39.998	 | 2021-01-01 00:01:39.998 | 
| **99999** | 	-14  | 	812.0         | 0.976996 | 0.644540         | True    | string_value_99999	 | 2021-01-01 00:01:39.999	 | NaT                     |  


    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data -> 200

### Wait for statistic data to be computed...
In case, the computation of statistics of WellLog bulk data is just triggered, below a code snippet to wait until the computation is ready 

```python
def wait_for_statistics(_url, _record_id, _params, *, attempts=5):
    n = int(attempts)
    if not _params:
        _params = {}
        
    for i in range(n):
        print(f"\nAttempt number {i+1}:")

        _welllog_stats_response = client.get(f'{_url}/{_record_id}/data/statistics', params=_params)
        print_response(_welllog_stats_response)

        if not (_welllog_stats_response.status_code == 404 and _welllog_stats_response.json()['errorType'] == 'COMPUTATION_NOT_COMPLETE'):
            break
        waiting_time = i + 2 ** i
        print(f"Wait for {waiting_time}s before retrying...")
        time.sleep(waiting_time)

    if _welllog_stats_response.status_code != 200:
        raise Exception(f"Unable to get bulk statistics data after {i+1} attempts...", _welllog_stats_response.text)
    return _welllog_stats_response

example_json_stats_response = fetch_statistics_for(welllog_url, types_col_record_id, param={'curves': 'int-A-with-nan'}, attempts=5)
example_json_stats = example_json_stats_response.json()
display(example_json_stats)
```
    
    Attempt number 1:
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data/statistics -> 404
    b'{"errorType":"COMPUTATION_NOT_COMPLETE","message":"Statistics computation not finished yet"}'
    
    
    Attempt number 2:
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data/statistics -> 200

    {'computationStartDatetime': '2022-05-31T09:17:08.431223',
     'recordId': 'opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9',
     'recordVersion': 1653988624188709,
     'computationStatus': 'complete',
     'data': {'int-A-with-nan': {'mean': '449.8925764705882',
       'std': '317.8241340241287',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '450.0',
       '90%': '890.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'}}}

### Automatics WellLog data statistics computation finished with error
In case `GET /ddms/v3/welllogs/{record_id}/data/statistics` or `GET /ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics`  
returns `HTTP 200` with body like so:

    {
      "computationStartDatetime": "2022-05-18T16:22:16.010582",
      "recordId": "osdu:work-product-component--WellLog:6d9c95c972254bbbaeaecbfa67fd1cf3",
      "recordVersion": "1998222529528913770053504387865218642",
      "computationStatus": "error",
      "data": {}
    }

It is necessary to trigger manually the WellLog data statistics computation. Move to [Manually trigger bulk statistics computation](#manually-trigger-bulk-statistics-computation).


## 2.2 For WellLogs created or updated BEFORE the OSDU M12 release  

Bulk data statistics computation needs to be manually triggered whenever:
- WellLogs data are posted before OSDU M12 release
- The automatic bulk data statistics computation has failed


Current limitations to manually trigger the WellLog bulk data statistics computation are:
- A delay of 1h before triggering the computation again for the same WellLog data.
- A maximum of 3 attempts to compute statistics for a given WellLog data.


```python
legacy_record_id = '' # pick one WellLog record id created before M12 release.
```

### Manually trigger bulk statistics computation
Computation can be manually triggered if WellLog was create before M12 release or in case of computation error.

API to use:
`POST /ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics`

NOTE: record id and record version are required.


```python
welllog_meta_response = client.get(f'{welllog_url}/{legacy_record_id}')
print_response(welllog_meta_response)
record_version = welllog_meta_response.json()['version']

post_welllog_stats_response = client.post(f'{welllog_url}/{legacy_record_id}/versions/{record_version}/data/statistics', headers={'content-type': 'application/parquet'})
print_response(post_welllog_stats_response)
```

    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4 -> 200
    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4/versions/1653990573032433/data/statistics -> 200


# 3. How to fetch WellLog bulk data statistics already computed

Please, note that WellLog's curves with string and boolean data types are not computed

### Display statistics data as JSON


```python
# Leave the parameter "curves" empty will select all the WellLog's curves statistics available
select_all_curves_param = {}

 # To select only curves: 'int-A', 'float-B' and 'date-C' from computed statistics
select_specific_curves_params = {"curves": "int-A,float-B,date-C"}

%time post_welllog_stats_response = client.get(f'{welllog_url}/{types_col_record_id}/data/statistics', param=select_all_curves_param)
print_response(post_welllog_stats_response)

json_posted_stats = post_welllog_stats_response.json()
display(json_posted_stats)
```

    CPU times: total: 141 ms
    Wall time: 2.01 s
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data/statistics -> 200
    
    {'computationStartDatetime': '2022-05-31T09:17:08.431223',
     'recordId': 'opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9',
     'recordVersion': 1653988624188709,
     'computationStatus': 'complete',
     'data': {'int-A-with-nan': {'mean': '449.8925764705882',
       'std': '317.8241340241287',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '450.0',
       '90%': '890.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'},
      'int-A': {'mean': '449.63618',
       'std': '317.49388998642064',
       'min': '-100.0',
       '10%': '9.0',
       '50%': '451.0',
       '90%': '890.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'date-C': {'mean': '2021-01-01 00:00:49.999499776',
       'std': 'NaN',
       'min': '2021-01-01 00:00:00',
       '10%': '2021-01-01 00:00:09.999899904',
       '50%': '2021-01-01 00:00:49.999500032',
       '90%': '2021-01-01 00:01:29.999100160',
       'max': '2021-01-01 00:01:39.999000',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000'},
      'date-C-with-nan': {'mean': '2021-01-01 00:00:49.995083776',
       'std': 'NaN',
       'min': '2021-01-01 00:00:00',
       '10%': '2021-01-01 00:00:10.055899904',
       '50%': '2021-01-01 00:00:49.966500096',
       '90%': '2021-01-01 00:01:29.970099968',
       'max': '2021-01-01 00:01:39.998000',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000'},
      'float-B-with-nan': {'mean': '0.4981784333593075',
       'std': '0.2888887958106551',
       'min': '3.56818820279603e-06',
       '10%': '0.09984358734025209',
       '50%': '0.4974533393916296',
       '90%': '0.8997088186446737',
       'max': '0.9999888136429178',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'},
      'float-B': {'mean': '0.4980908954221541',
       'std': '0.2885563043838143',
       'min': '1.4538739944169876e-06',
       '10%': '0.09894710442338889',
       '50%': '0.4969224934210345',
       '90%': '0.8987151676695218',
       'max': '0.9999918891377975',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'}}}


### Display statistics data in a Dataframe


```python
json_posted_stats_copy = response_copy_without_data(post_welllog_stats_response)
display(json_posted_stats_copy)

create_df_from_dict(post_welllog_stats_response)
```


    {'computationStartDatetime': '2022-05-31T09:17:08.431223',
     'recordId': 'opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9',
     'recordVersion': 1653988624188709,
     'computationStatus': 'complete'}


|                       | mean                          | std                | min                    | 10%                           | 50%                           | 90%                            | max                        | totalCount | nonAbsentValuesCount |
|-----------------------|-------------------------------|--------------------|------------------------|-------------------------------|-------------------------------|--------------------------------|----------------------------|------------|----------------------|
| **int-A-with-nan**	   | 449.8925764705882             | 317.8241340241287  | -100.0                 | 10.0                          | 450.0                         | 890.0                          | 999.0                      | 100000     | 85000.0              |
| **date-C**	           | 2021-01-01 00:00:49.999499776 | NaN                | 2021-01-01 00:00:00    | 2021-01-01 00:00:09.999899904 | 2021-01-01 00:00:49.999500032 | 2021-01-01 00:01:29.999100160	 | 2021-01-01 00:01:39.999000 | 100000     | 	100000              |
| **float-B-with-nan**	 | 0.4981784333593075            | 0.2888887958106551 | 3.56818820279603e-06   | 0.09984358734025209           | 0.4974533393916296            | 0.8997088186446737             | 0.9999888136429178         | 100000     | 85000.0              |
| **float-B**       	   | 0.4980908954221541            | 0.2885563043838143 | 1.4538739944169876e-06 | 0.09894710442338889           | 0.4969224934210345            | 0.8987151676695218             | 0.9999918891377975         | 100000     | 100000.0             |
| **int-A**             | 449.63618                     | 317.49388998642064 | -100.0                 | 9.0                           | 451.0                         | 890.0                          | 999.0                      | 100000     | 100000.0             |
| **date-C-with-nan**   | 2021-01-01 00:00:49.995083776 | NaN                | 2021-01-01 00:00:00    | 2021-01-01 00:00:10.055899904 | 2021-01-01 00:00:49.966500096 | 2021-01-01 00:01:29.970099968	 | 2021-01-01 00:01:39.998000 | 100000     | 	85000               |


# 4. Fetch WellLog bulk statistics code examples

APIs:
- GET /ddms/v3/welllogs/{record_id}/data/statistics
- GET /ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics

## Select specifics curves statistics
As the GET bulk API, you can fetch statistics only for specifics curves

### Fetch WellLog bulk information and retrieve columns from it
- GET /ddms/v3/welllogs/{record_id}/data?describe=True


```python
welllog_bulk_response_example_1 = client.get(f'{welllog_url}/{types_col_record_id}/data', params={'describe':True})
record_columns = welllog_bulk_response_example_1.json().get('columns', [])
display(welllog_bulk_response_example_1.json())

wanted_curves = [c for c in record_columns if c.startswith('float')]
print("\nWanted WellLog's curves", wanted_curves)
```


    {'numberOfRows': 100000,
     'columns': ['bool-D',
      'date-C',
      'date-C-with-nan',
      'float-B',
      'float-B-with-nan',
      'int-A',
      'int-A-with-nan',
      'string-E']}

    Wanted WellLog's curves ['float-B', 'float-B-with-nan']
    

### Fetch WellLog bulk statistics of selected WellLog's curves
- GET /ddms/v3/welllogs/{record_id}/data/statistics


```python
# Generate list of wanted curves from previous describe=True API.
wanted_curves_params = {
    'curves': ','.join(wanted_curves)
}

welllog_stats_response_example_1 = client.get(f'{welllog_url}/{types_col_record_id}/data/statistics', params=wanted_curves_params)
print_response(welllog_stats_response_example_1)

json_posted_stats_example_1 = welllog_stats_response_example_1.json()
display(json_posted_stats_example_1)
```

    {'curves': 'float-B,float-B-with-nan'}
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data/statistics?curves=float-B%2Cfloat-B-with-nan -> 200


    {'computationStartDatetime': '2022-05-31T09:17:08.431223',
     'recordId': 'opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9',
     'recordVersion': 1653988624188709,
     'computationStatus': 'complete',
     'data': {'float-B': {'mean': '0.4980908954221541',
       'std': '0.2885563043838143',
       'min': '1.4538739944169876e-06',
       '10%': '0.09894710442338889',
       '50%': '0.4969224934210345',
       '90%': '0.8987151676695218',
       'max': '0.9999918891377975',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'float-B-with-nan': {'mean': '0.4981784333593075',
       'std': '0.2888887958106551',
       'min': '3.56818820279603e-06',
       '10%': '0.09984358734025209',
       '50%': '0.4974533393916296',
       '90%': '0.8997088186446737',
       'max': '0.9999888136429178',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'}}}


### Fetch WellLog bulk statistics of anterior WellLog bulk version

#### List WellLog anterior versions
- GET /ddms/v3/welllogs/{welllogId}/versions


```python
welllog_record_response_example_2 = client.get(f'{welllog_url}/{types_col_record_id}/versions')
record_versions = welllog_record_response_example_2.json().get('versions', [])

print("record_versions:", record_versions)
last_record_version = record_versions[-1]
```

    record_versions: [1653988602340449, 1653988624188709]
    

#### Then, fetch WellLog bulk statistics at specified version
- GET /ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics


```python
wanted_curves_params = {
    'curves': ','.join(wanted_curves)
}

record_version = last_record_version

welllog_stats_response_example_2 = client.get(f'{welllog_url}/{types_col_record_id}/versions/{record_version}/data/statistics', params=wanted_curves_params)
print_response(welllog_stats_response_example_2)

json_posted_stats_example_2 = welllog_stats_response_example_2.json()
display(json_posted_stats_example_2)
```

    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/versions/1653988624188709/data/statistics?curves=float-B%2Cfloat-B-with-nan -> 200
    

    {'computationStartDatetime': '2022-05-31T09:17:08.431223',
     'recordId': 'opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9',
     'recordVersion': 1653988624188709,
     'computationStatus': 'complete',
     'data': {'float-B': {'mean': '0.4980908954221541',
       'std': '0.2885563043838143',
       'min': '1.4538739944169876e-06',
       '10%': '0.09894710442338889',
       '50%': '0.4969224934210345',
       '90%': '0.8987151676695218',
       'max': '0.9999918891377975',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'float-B-with-nan': {'mean': '0.4981784333593075',
       'std': '0.2888887958106551',
       'min': '3.56818820279603e-06',
       '10%': '0.09984358734025209',
       '50%': '0.4974533393916296',
       '90%': '0.8997088186446737',
       'max': '0.9999888136429178',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'}}}
