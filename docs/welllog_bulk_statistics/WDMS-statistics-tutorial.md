In this tutorial we will explain:

* How to automatically get bulk statistics on newly created WellLog using Wellbore DDMS chunking API's
* How to trigger manually computation of bulk statistics on WellLogs created before OSDU M12 release.
* How to trigger manually computation of bulk statistics:  
    - for WellLogs created before statistics feature available at OSDU M12 release.
    - in case of error of previous computation

Computable data types are: integer, float and date/datetime.

# Prerequesites

## Required Python packages


```python
!python -m pip install pip --upgrade
!pip install httpx pandas pyarrow
```

    Requirement already satisfied: pip in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (22.1.1)
    

    The system cannot find the path specified.
    

    Requirement already satisfied: httpx in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (0.22.0)
    Requirement already satisfied: pandas in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (1.4.1)
    Requirement already satisfied: pyarrow in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (7.0.0)
    Requirement already satisfied: certifi in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpx) (2021.10.8)
    Requirement already satisfied: charset-normalizer in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpx) (2.0.12)
    Requirement already satisfied: rfc3986[idna2008]<2,>=1.3 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpx) (1.5.0)
    Requirement already satisfied: sniffio in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpx) (1.2.0)
    Requirement already satisfied: httpcore<0.15.0,>=0.14.5 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpx) (0.14.7)
    Requirement already satisfied: python-dateutil>=2.8.1 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from pandas) (2.8.2)
    Requirement already satisfied: pytz>=2020.1 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from pandas) (2021.3)
    Requirement already satisfied: numpy>=1.18.5 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from pandas) (1.22.2)
    Requirement already satisfied: h11<0.13,>=0.11 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpcore<0.15.0,>=0.14.5->httpx) (0.12.0)
    Requirement already satisfied: anyio==3.* in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from httpcore<0.15.0,>=0.14.5->httpx) (3.5.0)
    Requirement already satisfied: idna>=2.8 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from anyio==3.*->httpcore<0.15.0,>=0.14.5->httpx) (3.3)
    Requirement already satisfied: six>=1.5 in c:\repositories\jupyter\.jupy-env-38\lib\site-packages (from python-dateutil>=2.8.1->pandas) (1.16.0)
    

    The system cannot find the path specified.
    

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
data_partition_id = '' # set a data partition id
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

## Create WellLog record


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
            {
                "CurveID": "Curve-1",
            },
            {
                "CurveID": "Curve-2",
            },
            {
                "CurveID": "Curve-3",
            },
            {
                "CurveID": "Curve-4",
            },
            {
                "CurveID": "Curve-5",
            },
            {
                "CurveID": "Curve-6",
            }
        ]
    },
}

response = client.post(welllog_url, json=[record])
print_response(response)
record_id = response.json()["recordIds"][0]
print(record_id)
```

    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs -> 200
    opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d
    

# Trigger statistics computation: chunking APIs
Computation of bulk statistics will be triggered automatically when creating a new WellLog using the chunking APIs.  
Below an example that push bulk for 6 curves with 100k rows:

- Create a session 
- Send data by chunks
- Commit the session
- Wait for statistics to be computation in background...


```python
columns = ["Curve-1", "Curve-2", "Curve-3", "Curve-4", "Curve-5", "Curve-6"]
rows_count = 100_000

print(f"\nRun at {datetime.now()}\n")

create_session_response = client.post(f'{welllog_url}/{record_id}/sessions', json={'mode': 'overwrite'})
print_response(create_session_response)
session_id = create_session_response.json()['id']

start = time.time()
futures = []
print('\n...Preparing async requests...')
for col in columns:
    auto_generated_column_data = generate_df([col], range(rows_count))
    
    f = aclient.post(f'{welllog_url}/{record_id}/sessions/{session_id}/data', 
                     content=auto_generated_column_data.to_parquet(engine="pyarrow"), 
                     headers={'content-type':'application/parquet'})
    futures.append(f)

print('...Waiting for chunks fully sent...')
await asyncio.gather(*futures)
print('Sending chunks finished! Elapsed time:', time.time() - start)

print('...Session committing...')
start = time.time()
commit_session_response = client.patch(f'{welllog_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
print_response(commit_session_response)
print('Session state after commit =', commit_session_response.json()['state'])
print(f"\nTotal time elapsed:", time.time() - start, "s")

```

    
    Run at 2022-05-31 14:07:33.973041
    
    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d/sessions -> 200
    
    ...Preparing async requests...
    ...Waiting for chunks fully sent...
    Sending chunks finished! Elapsed time: 1.7203505039215088
    ...Session committing...
    PATCH : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d/sessions/7ec172c7-ad32-452d-a983-2ec14d5cd8f8 -> 200
    Session state after commit = committed
    
    Total time elapsed: 2.364872694015503 s
    

## Fetch and display WellLog data just sent


```python
%time welllog_data_response = client.get(f'{welllog_url}/{record_id}/data', headers={'Accept':'application/parquet'})
print_response(welllog_data_response)
display(create_df_from_response(welllog_data_response))
```

    CPU times: total: 78.1 ms
    Wall time: 3.02 s
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ba49961a652e4109a4aad86818c33a62/data -> 200
    


<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>Curve-1</th>
      <th>Curve-2</th>
      <th>Curve-3</th>
      <th>Curve-4</th>
      <th>Curve-5</th>
      <th>Curve-6</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>51</td>
      <td>469</td>
      <td>352</td>
      <td>760</td>
      <td>335</td>
      <td>484</td>
    </tr>
    <tr>
      <th>1</th>
      <td>408</td>
      <td>-85</td>
      <td>-7</td>
      <td>714</td>
      <td>525</td>
      <td>659</td>
    </tr>
    <tr>
      <th>2</th>
      <td>186</td>
      <td>852</td>
      <td>512</td>
      <td>571</td>
      <td>829</td>
      <td>827</td>
    </tr>
    <tr>
      <th>3</th>
      <td>645</td>
      <td>352</td>
      <td>320</td>
      <td>584</td>
      <td>37</td>
      <td>327</td>
    </tr>
    <tr>
      <th>4</th>
      <td>856</td>
      <td>465</td>
      <td>72</td>
      <td>294</td>
      <td>318</td>
      <td>559</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>99995</th>
      <td>94</td>
      <td>155</td>
      <td>219</td>
      <td>406</td>
      <td>537</td>
      <td>438</td>
    </tr>
    <tr>
      <th>99996</th>
      <td>181</td>
      <td>792</td>
      <td>466</td>
      <td>195</td>
      <td>600</td>
      <td>853</td>
    </tr>
    <tr>
      <th>99997</th>
      <td>36</td>
      <td>391</td>
      <td>-32</td>
      <td>878</td>
      <td>872</td>
      <td>351</td>
    </tr>
    <tr>
      <th>99998</th>
      <td>407</td>
      <td>655</td>
      <td>688</td>
      <td>-94</td>
      <td>200</td>
      <td>687</td>
    </tr>
    <tr>
      <th>99999</th>
      <td>688</td>
      <td>128</td>
      <td>454</td>
      <td>826</td>
      <td>503</td>
      <td>-25</td>
    </tr>
  </tbody>
</table>
<p>100000 rows × 6 columns</p>
</div>


## Display Bulk statistics computed from bulk data previously sent by chunks

### Display statistics data as JSON


```python
# leave the parameter "curves" empty or None, will select all the WellLog's curves available
select_all_curves_param = {}

select_specific_curves_params = {
    # To select only Curve 1, 5 and 6.
    "curves": "Curve-1,Curve-5,Curve-6"
}

%time welllog_stats_response = client.get(f'{welllog_url}/{record_id}/data/statistics', params=select_all_curves_param)
print_response(welllog_stats_response)

display(welllog_stats_response.json())
```

    CPU times: total: 125 ms
    Wall time: 2.34 s
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d/data/statistics -> 200
    


    {'computationStartDatetime': '2022-05-31T12:07:38.440333',
     'recordId': 'opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d',
     'recordVersion': 1653998857641710,
     'computationStatus': 'complete',
     'data': {'Curve-1': {'mean': '450.053',
       'std': '318.66713975315935',
       'min': '-100.0',
       '10%': '8.0',
       '50%': '452.0',
       '90%': '891.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'Curve-3': {'mean': '449.24881',
       'std': '317.49627705288657',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '448.0',
       '90%': '889.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'Curve-4': {'mean': '448.3254',
       'std': '317.50465414997313',
       'min': '-100.0',
       '10%': '8.0',
       '50%': '448.0',
       '90%': '889.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'Curve-2': {'mean': '450.12567',
       'std': '317.2213872221358',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '451.0',
       '90%': '888.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'Curve-6': {'mean': '449.59783',
       'std': '317.8342532443859',
       'min': '-100.0',
       '10%': '9.0',
       '50%': '451.0',
       '90%': '888.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'Curve-5': {'mean': '449.96533',
       'std': '317.9705158980639',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '449.0',
       '90%': '890.1000000000058',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'}}}


### Display statistics data in a Dataframe


```python
json_stats_copy = response_copy_without_data(welllog_stats_response)
display(json_stats_copy)

create_df_from_dict(welllog_stats_response)
```


    {'computationStartDatetime': '2022-05-31T12:07:38.440333',
     'recordId': 'opendes:work-product-component--WellLog:a57b87e2321d45f4a4f74fddeb51cf4d',
     'recordVersion': 1653998857641710,
     'computationStatus': 'complete'}





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>mean</th>
      <th>std</th>
      <th>min</th>
      <th>10%</th>
      <th>50%</th>
      <th>90%</th>
      <th>max</th>
      <th>totalCount</th>
      <th>nonAbsentValuesCount</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Curve-1</th>
      <td>450.053</td>
      <td>318.66713975315935</td>
      <td>-100.0</td>
      <td>8.0</td>
      <td>452.0</td>
      <td>891.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>Curve-3</th>
      <td>449.24881</td>
      <td>317.49627705288657</td>
      <td>-100.0</td>
      <td>10.0</td>
      <td>448.0</td>
      <td>889.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>Curve-4</th>
      <td>448.3254</td>
      <td>317.50465414997313</td>
      <td>-100.0</td>
      <td>8.0</td>
      <td>448.0</td>
      <td>889.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>Curve-2</th>
      <td>450.12567</td>
      <td>317.2213872221358</td>
      <td>-100.0</td>
      <td>10.0</td>
      <td>451.0</td>
      <td>888.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>Curve-6</th>
      <td>449.59783</td>
      <td>317.8342532443859</td>
      <td>-100.0</td>
      <td>9.0</td>
      <td>451.0</td>
      <td>888.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>Curve-5</th>
      <td>449.96533</td>
      <td>317.9705158980639</td>
      <td>-100.0</td>
      <td>10.0</td>
      <td>449.0</td>
      <td>890.1000000000058</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
  </tbody>
</table>
</div>


#
# Trigger statistics computation: POST APIs
Computation of bulk statistics will be triggered automatically when creating a new WellLog using the post data APIs.  
Below an example that push bulk for 8 curves with DIFFERENT types of data with 100k rows:

- Send data
- Wait for statistics to be computation in background...


```python
record = {
    "kind": f"{data_partition}:wks:work-product-component--WellLog:1.0.0",
    "acl": {
        "viewers": [f"data.default.viewers@{data_partition}.{acl_domain}"],
        "owners": [f"data.default.owners@{data_partition}.{acl_domain}"]
      },
    "legal": {
        "legaltags": legaltags,
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
types_col_record_id
```

    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs -> 200
    

## POST WellLog data


```python
columns = ['int-A', 'int-A-with-nan', 'float-B', 'float-B-with-nan', 'bool-D', 'string-E', 'date-C', 'date-C-with-nan']

different_type_df = generate_df_typed(columns, range(100_000))
add_nan_values_to_df(different_type_df)

data_to_send = different_type_df.to_parquet(engine='pyarrow')

write_response = client.post(f'{welllog_url}/{types_col_record_id}/data', data=data_to_send, headers={'content-type': 'application/parquet'})
print_response(write_response)
```


<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>int-A</th>
      <th>int-A-with-nan</th>
      <th>float-B</th>
      <th>float-B-with-nan</th>
      <th>bool-D</th>
      <th>string-E</th>
      <th>date-C</th>
      <th>date-C-with-nan</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>868</td>
      <td>592.0</td>
      <td>0.792575</td>
      <td>0.113692</td>
      <td>False</td>
      <td>string_value_0</td>
      <td>2021-01-01 00:00:00.000</td>
      <td>2021-01-01 00:00:00.000</td>
    </tr>
    <tr>
      <th>1</th>
      <td>222</td>
      <td>624.0</td>
      <td>0.529602</td>
      <td>0.047647</td>
      <td>True</td>
      <td>string_value_1</td>
      <td>2021-01-01 00:00:00.001</td>
      <td>NaT</td>
    </tr>
    <tr>
      <th>2</th>
      <td>842</td>
      <td>359.0</td>
      <td>0.184516</td>
      <td>0.783715</td>
      <td>True</td>
      <td>string_value_2</td>
      <td>2021-01-01 00:00:00.002</td>
      <td>NaT</td>
    </tr>
    <tr>
      <th>3</th>
      <td>879</td>
      <td>280.0</td>
      <td>0.526019</td>
      <td>0.288487</td>
      <td>False</td>
      <td>string_value_3</td>
      <td>2021-01-01 00:00:00.003</td>
      <td>NaT</td>
    </tr>
    <tr>
      <th>4</th>
      <td>456</td>
      <td>619.0</td>
      <td>0.512207</td>
      <td>0.373447</td>
      <td>True</td>
      <td>string_value_4</td>
      <td>2021-01-01 00:00:00.004</td>
      <td>2021-01-01 00:00:00.004</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>99995</th>
      <td>560</td>
      <td>220.0</td>
      <td>0.714021</td>
      <td>0.064975</td>
      <td>False</td>
      <td>string_value_99995</td>
      <td>2021-01-01 00:01:39.995</td>
      <td>2021-01-01 00:01:39.995</td>
    </tr>
    <tr>
      <th>99996</th>
      <td>861</td>
      <td>78.0</td>
      <td>0.663497</td>
      <td>0.560253</td>
      <td>False</td>
      <td>string_value_99996</td>
      <td>2021-01-01 00:01:39.996</td>
      <td>2021-01-01 00:01:39.996</td>
    </tr>
    <tr>
      <th>99997</th>
      <td>916</td>
      <td>100.0</td>
      <td>0.687259</td>
      <td>NaN</td>
      <td>False</td>
      <td>string_value_99997</td>
      <td>2021-01-01 00:01:39.997</td>
      <td>2021-01-01 00:01:39.997</td>
    </tr>
    <tr>
      <th>99998</th>
      <td>354</td>
      <td>933.0</td>
      <td>0.563194</td>
      <td>0.921421</td>
      <td>False</td>
      <td>string_value_99998</td>
      <td>2021-01-01 00:01:39.998</td>
      <td>2021-01-01 00:01:39.998</td>
    </tr>
    <tr>
      <th>99999</th>
      <td>-14</td>
      <td>812.0</td>
      <td>0.976996</td>
      <td>0.644540</td>
      <td>True</td>
      <td>string_value_99999</td>
      <td>2021-01-01 00:01:39.999</td>
      <td>NaT</td>
    </tr>
  </tbody>
</table>
<p>100000 rows × 8 columns</p>
</div>


    POST : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data -> 200
    

## Fetch and display WellLog data just sent


```python
%time welllog_data_typed_response = client.get(f'{welllog_url}/{types_col_record_id}/data', headers={'Accept':'application/parquet'})
print_response(welllog_data_typed_response)

display(create_df_from_response(welllog_data_typed_response))
```

    CPU times: total: 125 ms
    Wall time: 4.7 s
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:ac6ec4b8074941b19c4723b1dbdc0da9/data -> 200
    


<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>bool-D</th>
      <th>date-C</th>
      <th>date-C-with-nan</th>
      <th>float-B</th>
      <th>float-B-with-nan</th>
      <th>int-A</th>
      <th>int-A-with-nan</th>
      <th>string-E</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>False</td>
      <td>2021-01-01 00:00:00.000</td>
      <td>2021-01-01 00:00:00.000</td>
      <td>0.792575</td>
      <td>0.113692</td>
      <td>868</td>
      <td>592.0</td>
      <td>string_value_0</td>
    </tr>
    <tr>
      <th>1</th>
      <td>True</td>
      <td>2021-01-01 00:00:00.001</td>
      <td>NaT</td>
      <td>0.529602</td>
      <td>0.047647</td>
      <td>222</td>
      <td>624.0</td>
      <td>string_value_1</td>
    </tr>
    <tr>
      <th>2</th>
      <td>True</td>
      <td>2021-01-01 00:00:00.002</td>
      <td>NaT</td>
      <td>0.184516</td>
      <td>0.783715</td>
      <td>842</td>
      <td>359.0</td>
      <td>string_value_2</td>
    </tr>
    <tr>
      <th>3</th>
      <td>False</td>
      <td>2021-01-01 00:00:00.003</td>
      <td>NaT</td>
      <td>0.526019</td>
      <td>0.288487</td>
      <td>879</td>
      <td>280.0</td>
      <td>string_value_3</td>
    </tr>
    <tr>
      <th>4</th>
      <td>True</td>
      <td>2021-01-01 00:00:00.004</td>
      <td>2021-01-01 00:00:00.004</td>
      <td>0.512207</td>
      <td>0.373447</td>
      <td>456</td>
      <td>619.0</td>
      <td>string_value_4</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>99995</th>
      <td>False</td>
      <td>2021-01-01 00:01:39.995</td>
      <td>2021-01-01 00:01:39.995</td>
      <td>0.714021</td>
      <td>0.064975</td>
      <td>560</td>
      <td>220.0</td>
      <td>string_value_99995</td>
    </tr>
    <tr>
      <th>99996</th>
      <td>False</td>
      <td>2021-01-01 00:01:39.996</td>
      <td>2021-01-01 00:01:39.996</td>
      <td>0.663497</td>
      <td>0.560253</td>
      <td>861</td>
      <td>78.0</td>
      <td>string_value_99996</td>
    </tr>
    <tr>
      <th>99997</th>
      <td>False</td>
      <td>2021-01-01 00:01:39.997</td>
      <td>2021-01-01 00:01:39.997</td>
      <td>0.687259</td>
      <td>NaN</td>
      <td>916</td>
      <td>100.0</td>
      <td>string_value_99997</td>
    </tr>
    <tr>
      <th>99998</th>
      <td>False</td>
      <td>2021-01-01 00:01:39.998</td>
      <td>2021-01-01 00:01:39.998</td>
      <td>0.563194</td>
      <td>0.921421</td>
      <td>354</td>
      <td>933.0</td>
      <td>string_value_99998</td>
    </tr>
    <tr>
      <th>99999</th>
      <td>True</td>
      <td>2021-01-01 00:01:39.999</td>
      <td>NaT</td>
      <td>0.976996</td>
      <td>0.644540</td>
      <td>-14</td>
      <td>812.0</td>
      <td>string_value_99999</td>
    </tr>
  </tbody>
</table>
<p>100000 rows × 8 columns</p>
</div>


## Display Bulk statistics computed from bulk data previously sent with POST API

Please, note that WellLog's curves with string and boolean data types are not computed

### Display statistics data as JSON


```python
%time post_welllog_stats_response = client.get(f'{welllog_url}/{types_col_record_id}/data/statistics')
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





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>mean</th>
      <th>std</th>
      <th>min</th>
      <th>10%</th>
      <th>50%</th>
      <th>90%</th>
      <th>max</th>
      <th>totalCount</th>
      <th>nonAbsentValuesCount</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>int-A-with-nan</th>
      <td>449.8925764705882</td>
      <td>317.8241340241287</td>
      <td>-100.0</td>
      <td>10.0</td>
      <td>450.0</td>
      <td>890.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>85000.0</td>
    </tr>
    <tr>
      <th>date-C</th>
      <td>2021-01-01 00:00:49.999499776</td>
      <td>NaN</td>
      <td>2021-01-01 00:00:00</td>
      <td>2021-01-01 00:00:09.999899904</td>
      <td>2021-01-01 00:00:49.999500032</td>
      <td>2021-01-01 00:01:29.999100160</td>
      <td>2021-01-01 00:01:39.999000</td>
      <td>100000</td>
      <td>100000</td>
    </tr>
    <tr>
      <th>float-B-with-nan</th>
      <td>0.4981784333593075</td>
      <td>0.2888887958106551</td>
      <td>3.56818820279603e-06</td>
      <td>0.09984358734025209</td>
      <td>0.4974533393916296</td>
      <td>0.8997088186446737</td>
      <td>0.9999888136429178</td>
      <td>100000</td>
      <td>85000.0</td>
    </tr>
    <tr>
      <th>float-B</th>
      <td>0.4980908954221541</td>
      <td>0.2885563043838143</td>
      <td>1.4538739944169876e-06</td>
      <td>0.09894710442338889</td>
      <td>0.4969224934210345</td>
      <td>0.8987151676695218</td>
      <td>0.9999918891377975</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>int-A</th>
      <td>449.63618</td>
      <td>317.49388998642064</td>
      <td>-100.0</td>
      <td>9.0</td>
      <td>451.0</td>
      <td>890.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>date-C-with-nan</th>
      <td>2021-01-01 00:00:49.995083776</td>
      <td>NaN</td>
      <td>2021-01-01 00:00:00</td>
      <td>2021-01-01 00:00:10.055899904</td>
      <td>2021-01-01 00:00:49.966500096</td>
      <td>2021-01-01 00:01:29.970099968</td>
      <td>2021-01-01 00:01:39.998000</td>
      <td>100000</td>
      <td>85000</td>
    </tr>
  </tbody>
</table>
</div>



#
# Manually trigger bulk statistics's computation  

There are two cases when bulk statistics computation needs to be manually triggered:
- for WellLogs created before statistics feature available at OSDU M12 release.
- in case of error of previous computation: 1h delay between computations, 3 attempts maximum.


```python
legacy_record_id = 'opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4'
```

## Manually trigger bulk statistics computation
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
    

## Wait for statistic data to be computed...


```python
def fetch_statistics_for(_url, _record_id, _params, *, attempts=5):
    n = int(attempts)
    if not _params:
        _params = {}
        
    for i in range(n):
        print(f"\nAttempt number {i+1}:")

        _welllog_stats_response = client.get(f'{_url}/{_record_id}/data/statistics', params=_params)
        print_response(_welllog_stats_response)

        if not (_welllog_stats_response.status_code == 404 and _welllog_stats_response.json()['errorType'] == 'COMPUTATION_NOT_COMPLETE'):
            break
        print(f"Wait for {1 + i}s before retrying...")
        time.sleep(1 + i)

    if _welllog_stats_response.status_code != 200:
        raise Exception(f"Unable to get bulk statistics data after {i+1} attempts...", _welllog_stats_response.text)
    return _welllog_stats_response
```

### Display statistics data as JSON


```python
regular_welllog_stats_response = fetch_statistics_for(welllog_url, legacy_record_id, None, attempts=5)

regular_json_stats = regular_welllog_stats_response.json()
display(regular_json_stats)
```

    
    Attempt number 1:
    GET : https://evt.api.enterprisedata.cloud.slb-ds.com/api/os-wellbore-ddms---integration/ddms/v3/welllogs/opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4/data/statistics -> 200
    


    {'computationStartDatetime': '2022-05-31T09:49:51.180443',
     'recordId': 'opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4',
     'recordVersion': 1653990573032433,
     'computationStatus': 'complete',
     'data': {'int-A-with-nan': {'mean': '449.5494705882353',
       'std': '316.5811423464183',
       'min': '-100.0',
       '10%': '10.0',
       '50%': '451.0',
       '90%': '887.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'},
      'date-C': {'mean': '2021-01-01 00:00:49.999499776',
       'std': 'NaN',
       'min': '2021-01-01 00:00:00',
       '10%': '2021-01-01 00:00:09.999899904',
       '50%': '2021-01-01 00:00:49.999500032',
       '90%': '2021-01-01 00:01:29.999100160',
       'max': '2021-01-01 00:01:39.999000',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000'},
      'float-B-with-nan': {'mean': '0.5000246779807201',
       'std': '0.28936434203405226',
       'min': '6.161415082694965e-06',
       '10%': '0.09797749332708527',
       '50%': '0.5008735113317963',
       '90%': '0.9008682937966069',
       'max': '0.9999884908777941',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000.0'},
      'float-B': {'mean': '0.500878465176603',
       'std': '0.2895880011920779',
       'min': '1.1233012248146323e-06',
       '10%': '0.0984692531200841',
       '50%': '0.5016498429112666',
       '90%': '0.9022214518862695',
       'max': '0.9999765254360873',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'int-A': {'mean': '451.67252',
       'std': '316.6790264809271',
       'min': '-100.0',
       '10%': '12.0',
       '50%': '452.0',
       '90%': '889.0',
       'max': '999.0',
       'totalCount': '100000',
       'nonAbsentValuesCount': '100000.0'},
      'date-C-with-nan': {'mean': '2021-01-01 00:00:49.974277632',
       'std': 'NaN',
       'min': '2021-01-01 00:00:00',
       '10%': '2021-01-01 00:00:10.012899840',
       '50%': '2021-01-01 00:00:49.933500160',
       '90%': '2021-01-01 00:01:29.937100032',
       'max': '2021-01-01 00:01:39.999000',
       'totalCount': '100000',
       'nonAbsentValuesCount': '85000'}}}


### Display statistics data in a Dataframe


```python
regular_json_stats_copy = response_copy_without_data(regular_welllog_stats_response)
display(regular_json_stats_copy)

create_df_from_dict(regular_welllog_stats_response)
```


    {'computationStartDatetime': '2022-05-31T09:49:51.180443',
     'recordId': 'opendes:work-product-component--WellLog:89bd0debbcf1411fb240d0a906da7cd4',
     'recordVersion': 1653990573032433,
     'computationStatus': 'complete'}





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>mean</th>
      <th>std</th>
      <th>min</th>
      <th>10%</th>
      <th>50%</th>
      <th>90%</th>
      <th>max</th>
      <th>totalCount</th>
      <th>nonAbsentValuesCount</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>int-A-with-nan</th>
      <td>449.5494705882353</td>
      <td>316.5811423464183</td>
      <td>-100.0</td>
      <td>10.0</td>
      <td>451.0</td>
      <td>887.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>85000.0</td>
    </tr>
    <tr>
      <th>date-C</th>
      <td>2021-01-01 00:00:49.999499776</td>
      <td>NaN</td>
      <td>2021-01-01 00:00:00</td>
      <td>2021-01-01 00:00:09.999899904</td>
      <td>2021-01-01 00:00:49.999500032</td>
      <td>2021-01-01 00:01:29.999100160</td>
      <td>2021-01-01 00:01:39.999000</td>
      <td>100000</td>
      <td>100000</td>
    </tr>
    <tr>
      <th>float-B-with-nan</th>
      <td>0.5000246779807201</td>
      <td>0.28936434203405226</td>
      <td>6.161415082694965e-06</td>
      <td>0.09797749332708527</td>
      <td>0.5008735113317963</td>
      <td>0.9008682937966069</td>
      <td>0.9999884908777941</td>
      <td>100000</td>
      <td>85000.0</td>
    </tr>
    <tr>
      <th>float-B</th>
      <td>0.500878465176603</td>
      <td>0.2895880011920779</td>
      <td>1.1233012248146323e-06</td>
      <td>0.0984692531200841</td>
      <td>0.5016498429112666</td>
      <td>0.9022214518862695</td>
      <td>0.9999765254360873</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>int-A</th>
      <td>451.67252</td>
      <td>316.6790264809271</td>
      <td>-100.0</td>
      <td>12.0</td>
      <td>452.0</td>
      <td>889.0</td>
      <td>999.0</td>
      <td>100000</td>
      <td>100000.0</td>
    </tr>
    <tr>
      <th>date-C-with-nan</th>
      <td>2021-01-01 00:00:49.974277632</td>
      <td>NaN</td>
      <td>2021-01-01 00:00:00</td>
      <td>2021-01-01 00:00:10.012899840</td>
      <td>2021-01-01 00:00:49.933500160</td>
      <td>2021-01-01 00:01:29.937100032</td>
      <td>2021-01-01 00:01:39.999000</td>
      <td>100000</td>
      <td>85000</td>
    </tr>
  </tbody>
</table>
</div>



# Fetch WellLog bulk statistics examples

APIs:
- GET /ddms/v3/welllogs/{record_id}/data/statistics
- GET /ddms/v3/welllogs/{record_id}/versions/{version}/data/statistics

## Select specifics curves statistics
As the GET bulk API, you can fetch statistics only for specifics curves

### Fetch WellLog bulk informations and retrieve columns from it
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



```python

```
