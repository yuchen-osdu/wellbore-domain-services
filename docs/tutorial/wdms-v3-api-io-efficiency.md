# Wellbore DDMS V3 - bulk IO efficiency 

In this tutorial we will explain how to read and write bulk data efficiently.



## 1. Introduction

Firstly, before adressing how to send or read efficiently the bulk data, ensure to:
- Use parquet format for sending and fetching bulk data is much faster
- Use asynchronous requests in case of multiple calls
- Use a deployment with WDDMS worker service enabled, it improves a lot performances for:
    - reading from OSDU M16 release
    - writing from OSDU M20 release
    
Note: It is possible to check the version of WDDMS and whether the WDDMS workers are available with this API:  
**GET** *OSDU_BASE_URL/api/os-wellbore-ddms/version*  
``` json
// Response
{
  "service": "Wellbore DDMS OSDU",
  .. other properties before  ...
  "release": "M20",                    <======== OSDU release version of WDDMS deployment available
  "details": {
    ... Other properties before  ...
    "enable_wdms_bulk_worker": "True"  <======== If True, WDDMS worker deployment is avaialble
  }
}
```
    
### What are chunking APIs ?
All the APIs that help to sent bulk data by chunk instead of all bulk data at once, they are enabled to write bulk data for **WellLogs** and **WellboreTrajectories**.
Most important APIs for chunking:
1. Open a new session **POST**            */ddms/v3/welllogs/MY_RECORD_ID/sessions*
2. Send chunks in json/parquet:  **POST** */ddms/v3/welllogs/MY_RECORD_ID/sessions/MY_SESSION_ID/data*
3. Commit the session:  **PATCH**         */ddms/v3/welllogs/MY_RECORD_ID/sessions/MY_SESSION_ID*

Note: "welllogs" must be replaced by "wellboretrajectories" to manage bulk data for a WellboreTrajectories.
    
## 2. Chunking or not chunking?
Chunk APIs have been created to handle large amount of bulk data (GB) or when network is not stable enough and requires to split up data into smaller pieces.  
When writting, using the **chunking feature has a ressource and timing cost**: it requires to manage a session, verify that chunks can be assembled all together and resolving conflicts if any.

It implies, you should not use chunking APIs if your bulk data has a:
- Total number of values below **5 millions**
- Total size is below **50MB**

## 3. WDMS bulk data limits 
Each read or writing call using chunking APIs must request below **10 millions values** or **500 columns**, otherwise an HTTP 400 or HTTP 413 error will be returned


## 4. Enhance writing performances
In order to minimize writing time, it's necessary to:
- Double check whether bulk data is big enough to be sent with chunking APIs: meaning > 10 millions values or > 500 columns
  - If no, use instead **POST** */ddms/v3/welllogs/MY_RECORD_ID/data API* 
- Ensure all curve's values are in the same chunk to be sent
- Each chunk should contain as many as columns it is possible until upper limits are reached

Code snippet [here](#Prepare-bulk-data-and-chunks-to-be-sent).

## 5. Enhance reading performances
In order to minimize reading time.

1. [Partial reading](#Partial-reading)
    - Select only needed columns
    
**Important**: using curves filtering has a cost, use it only if it reduces significally the amount of retrieved bulk data.

2. [Full reading](#Full-reading)
    - Try to read everything, if those errors are returned go to next steps:
        - HTTP 400 "Too many columns requested"
        - HTTP 400 "Too many values requested"
        - HTTP 413 "the resource requested exceeds the limitthe resource requested exceeds the limit" (When WDMS is enabled)
    - Get curve names and number of rows per curve by using describe parameter
       - Each request should fetch as many as columns it is possible until upper limits are reached

**NOTE**: reading exact same chunks that written chunks wihout any modifications (no filtering and ask for all the columns contained in the chunk) will speed up a lot the reading

# Code snippets

## Prerequisites

### Required Python packages
Before to start to write bulk data through Wellbore DDMS API's, you will need to install the Python packages below:

- The **pandas** library and its Pandas.Dataframe json format to structure log bulk data to be written to the Wellbore DDMS.
- The **pyarrow** library to transform Pandas.Dataframe to parquet file through the pyarrow engine.
- The **httpx** library that allows to post request to the Wellbore DDMS.


```python
# Prerequisite to run code snippet
!pip install pandas numpy httpx pyarrow natsort
```

### Settings

For any call to Wellbore DDMS API's you need to pass into the header of the request a valid bearer token. Copy this token value and assign it to the TOKEN variable below.

Several settings as the **osdu_base_urlosdu_base_url** end-point and the **data-partition-id** are needed to create a WellLog to the Wellbore DDMS. Please, change those settings accordingly to your environment that you want to target.



```python
# Paste here the token without the bearer prefix
TOKEN = ""

# Set the OSDU base URL value
osdu_base_url = ""

# Set a data partition id
data_partition_id = ""

## Only necessary to create dummy record ##
record_acl_domain = ""
record_legal_tags = list()
###########################################
```


```python
# WDMS upper limits
COLUMNS_LIMIT = 3_000
VALUES_LIMIT = 10_000_000

# url to target welllogs records
welllog_dms_url = f"{osdu_base_url}/api/os-wellbore-ddms/ddms/v3/welllogs"

httpx_clients_config = {
    "headers" : {
        "data-partition-id": f"{data_partition_id}",
        "Authorization": f"Bearer {TOKEN}",
        },
    "timeout": 60
}

# http clients configured to target WDMS deployement
client = httpx.Client(**httpx_clients_config)
async_client = httpx.AsyncClient(**httpx_clients_config)
```

### Utility methods


```python
from typing import List
import httpx
import pandas as pd
import numpy as np
import io
from itertools import chain, cycle
from natsort import natsorted
from statistics import mean
import asyncio

def generate_df_typed(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('bool'):
            return np.random.choice(a=[False, True], size=size) 
        if col_name.startswith('date'):
            return (np.datetime64('2021-01-01') + days for days in range(size))
        
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                      for c in columns}, index=index)
    return df
    
def generate_df(columns: List[str], index):
    nbrows = len(index)
    df = pd.DataFrame(
        np.random.randint(-100, 1000, size=(nbrows, len(columns))), index=index)
    df.columns= columns
    return df


def print_response(resp):
    print(f'{resp.request.method} : {resp.url} -> {resp.status_code}')
    if resp.status_code != httpx.codes.OK:
        display(resp.content)

        
def create_df_from_response(response):
    """Returns a dataframe created from the WellLog bulk data response
    Input:
        response: a httpx.response object
    Output:
        dataframe: a pandas.dataframe object
    """
    if response.status_code != httpx.codes.OK:
        raise Exception("Unable to create df from response", response.text)
        
    content_type = response.headers.get('content-type')
    
    if "json" in content_type:
        return pd.DataFrame.from_dict(response.json())
    
    elif 'parquet' in content_type:
        f = io.BytesIO(response.content)
        f.seek(0)
        return pd.read_parquet(f)
    
    raise ValueError(f"Unknown content-type: '{content_type}'")
    
    
def split_df_into_chunks(
    df: pd.DataFrame,
    *,
    max_values_per_chunk: int,
    max_columns_per_chunk: int,
) -> List[pd.DataFrame]:
    """
    breakdown a dataframe into several chunks given the limits of total number of values and columns provided. Split is
    down column first. It applies horizontal slicing (by row) only if single column contains more values then the limit
    requested.
    :param df: dataframe to chunk
    :param max_values_per_chunk: maximum number of values in each chunk
    :param max_columns_per_chunk: maximum number of column in each chunk
    :return: list of dataframe/chunk
    """
    if df.empty:
        return [df]

    nb_rows = len(df)
    columns = natsorted(df.columns.tolist())
    chunks: List[pd.DataFrame] = []

    # split column first
    if nb_rows > max_values_per_chunk:
        for c in columns:
            single_column_df = df[[c]]
            for i in range(0, nb_rows, max_values_per_chunk):
                chunks.append(single_column_df.iloc[i : i + max_values_per_chunk])
    else:
        column_per_chunk = min(max_columns_per_chunk, int(max_values_per_chunk / nb_rows))
        for i in range(0, len(columns), column_per_chunk):
            chunks.append(df[columns[i : i + column_per_chunk]])
    return chunks


def format_bytes(n: int) -> str:
    """
    Copy from library dask/utils.py module.
    
    Format bytes as text:    
    >>> format_bytes(1234)
    '1.21 kiB'
    >>> format_bytes(12345678)
    '11.77 MiB'
    >>> format_bytes(1234567890)
    '1.15 GiB'
    
    For all values < 2**60, the output is always <= 10 characters.
    """
    for prefix, k in (
        ("Pi", 2**50),
        ("Ti", 2**40),
        ("Gi", 2**30),
        ("Mi", 2**20),
        ("ki", 2**10),
    ):
        if n >= k * 0.9:
            return f"{n / k:.2f} {prefix}B"
    return f"{n} B"


def create_dummy_welllog_record_with_curves(_curves_name: List[str], _data_partition_id : str, _acl_domain: str, _legal_tags: str) -> str:
    """ Create a new wellLog. Here is a fake body just to illustrate the the API """
    
    _curves = [{"CurveID": col, "NumberOfColumns": 1} for col in _curves_name]
    
    welllog_record = {
        "kind": "osdu:wks:work-product-component--WellLog:1.2.0",
        "acl": {
            "viewers": [f"data.default.viewers@{_data_partition_id}.{_acl_domain}"],
            "owners": [f"data.default.owners@{_data_partition_id}.{_acl_domain}"]
          },
        "legal": {
            "legaltags": _legal_tags,
            "otherRelevantDataCountries": ["US"],
        },
        "data": {
            "Curves": _curves
        },
    }
    print("Dummy record to be saved:", welllog_record)
    create_record_response = client.post(welllog_dms_url, json=[welllog_record])
    print_response(create_record_response)
    if create_record_response.status_code != httpx.codes.OK:
        raise Exception("Unable to create record", create_record_response.text)
    
    return create_record_response.json()["recordIds"][0]
```

## 4. Enhance writing performances

To speed up writing time, it's necessary to:
1. Double check that bulk data is big enough to be sent with chunking APIs: meaning > 10 millions values or > 500 curves
1. Ensure all curve's values are in the same chunk to be sent
1. Each chunk should contain as many as curves it is possible until upper limits are reached

### Prepare bulk data and chunks to be sent


```python
writing_cols_1 = [f'float-curve-{i}' for i in range(83)]
writing_row_count_1 = 1_000_000

# Generate data
writing_welllog_data_df = generate_df_typed(columns=writing_cols_1, index=range(writing_row_count_1))
print(f"Created a dataframe with {len(writing_cols_1)} columns and {len(writing_cols_1) * writing_row_count_1:,} values.")

# Splitting up whole bulk data into chunks
writting_chunk_dfs = split_df_into_chunks(writing_welllog_data_df, max_values_per_chunk=VALUES_LIMIT, max_columns_per_chunk=COLUMNS_LIMIT)

# Display some info
chunks_size = [_chunk.memory_usage(deep=True).sum() for _chunk in writting_chunk_dfs]
print(f"Dataframe is split up into {len(writting_chunk_dfs)} chunks. Each chunk are about {format_bytes(mean(chunks_size))}.")
```

    Created a dataframe with 83 columns and 83,000,000 values.
    Dataframe is split up into 9 chunks. Each chunk are about 70.36 MiB.
    


```python
record_id = "my-record-id"
```

### Sent chunks to WDMS asynchronously


```python
SESSION_MODE = 'overwrite' # 'update' | 'overwrite'

# Create a session #
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})
print_response(create_session_response)
session_id = create_session_response.json()['id']
print(f"Session created with id '{session_id}'\n")

parquet_headers = {'content-type': 'application/parquet'}
# Create asynchronous coroutines to send chunk data #
writting_routines = [
    async_client.post(url=f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', 
                data=_chunk.to_parquet(engine="pyarrow"), 
                headers=parquet_headers)
    for _chunk in writting_chunk_dfs]

print(f"Bulk data will be sent via chunking APIs throught {len(writting_routines)} asynchronous requests.")

print("Sending chunks asynchronously...")
write_chunks_responses = await asyncio.gather(*writting_routines)
print("All chunks have been sent!\n")

# Commit session
commit_session_response = client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})
print_response(commit_session_response)
print('Session after commit =', commit_session_response.json()['state'])
```

    POST : https://OSDU_BASE_URL/api/os-wellbore-ddms/ddms/v3/welllogs/MY_RECORD_ID/sessions -> 200
    Session created with id f0c9a52d-43c3-4e61-8bd4-391131f34e52
    
    Bulk data will be sent via chunking APIs throught 9 asynchronous requests
    Sending chunks...
    All chunks have been sent!
    PATCH : https://OSDU_BASE_URL/api/os-wellbore-ddms/ddms/v3/welllogs/MY_RECORD_ID/sessions/f0c9a52d-43c3-4e61-8bd4-391131f34e52 -> 200
    Session after commit = committed
    

## 5. Enhance reading performances

### Partial reading
- Select only needed curves

**Important**: keep in mind, using filtering on curves will increase the request time.


```python
ten_first_columns = writing_cols_1[:6]
parquet_headers = {'Accept': 'application/parquet'}

print("Reading 6 first curves:", ten_first_columns)
partial_read_response = client.get(f'{welllog_dms_url}/{record_id}/data', params={'curves': ','.join(ten_first_columns)}, headers=parquet_headers)
print_response(partial_read_response)

create_df_from_response(partial_read_response)
```

    Reading 6 first curves: ['float-curve-0', 'float-curve-1', 'float-curve-2', 'float-curve-3', 'float-curve-4', 'float-curve-5']
    GET : https://OSDU_BASE_URL/api/os-wellbore-ddms/ddms/v3/welllogs/MY_RECORD_ID/data?curves=float-curve-0%2Cfloat-curve-1%2Cfloat-curve-2%2Cfloat-curve-3%2Cfloat-curve-4%2Cfloat-curve-5 -> 200
    




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
      <th>float-curve-0</th>
      <th>float-curve-1</th>
      <th>float-curve-2</th>
      <th>float-curve-3</th>
      <th>float-curve-4</th>
      <th>float-curve-5</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0.561653</td>
      <td>0.357109</td>
      <td>0.561343</td>
      <td>0.957882</td>
      <td>0.848126</td>
      <td>0.384168</td>
    </tr>
    <tr>
      <th>1</th>
      <td>0.860161</td>
      <td>0.404813</td>
      <td>0.999685</td>
      <td>0.403734</td>
      <td>0.330359</td>
      <td>0.473276</td>
    </tr>
    <tr>
      <th>2</th>
      <td>0.230994</td>
      <td>0.701664</td>
      <td>0.059868</td>
      <td>0.866748</td>
      <td>0.587617</td>
      <td>0.904564</td>
    </tr>
    <tr>
      <th>3</th>
      <td>0.039214</td>
      <td>0.015107</td>
      <td>0.572603</td>
      <td>0.757716</td>
      <td>0.702208</td>
      <td>0.999775</td>
    </tr>
    <tr>
      <th>4</th>
      <td>0.421962</td>
      <td>0.060224</td>
      <td>0.771250</td>
      <td>0.391762</td>
      <td>0.298185</td>
      <td>0.509154</td>
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
      <th>999995</th>
      <td>0.178788</td>
      <td>0.411284</td>
      <td>0.225754</td>
      <td>0.426515</td>
      <td>0.149432</td>
      <td>0.543071</td>
    </tr>
    <tr>
      <th>999996</th>
      <td>0.289828</td>
      <td>0.930861</td>
      <td>0.675247</td>
      <td>0.793975</td>
      <td>0.128721</td>
      <td>0.528824</td>
    </tr>
    <tr>
      <th>999997</th>
      <td>0.463705</td>
      <td>0.444714</td>
      <td>0.724229</td>
      <td>0.160315</td>
      <td>0.883222</td>
      <td>0.444145</td>
    </tr>
    <tr>
      <th>999998</th>
      <td>0.775479</td>
      <td>0.573866</td>
      <td>0.946070</td>
      <td>0.786278</td>
      <td>0.430194</td>
      <td>0.659571</td>
    </tr>
    <tr>
      <th>999999</th>
      <td>0.787469</td>
      <td>0.497432</td>
      <td>0.555824</td>
      <td>0.004622</td>
      <td>0.746023</td>
      <td>0.268821</td>
    </tr>
  </tbody>
</table>
<p>1000000 rows × 6 columns</p>
</div>



### Full reading
- Try to read everything, if error "HTTP 413: Content too large" is returned go to next steps
- Get curves name and number of rows per curve by using describe parameter
   - Each request should fetch as many as curves it is possible until upper limits are reached


```python
total_read_response = client.get(f'{welllog_dms_url}/{record_id}/data', headers=parquet_headers)
print_response(total_read_response)

if total_read_response.status_code == 200:
    print("\nGreat! Bulk data can be read all at once.")
    total_read_df = create_df_from_response(total_read_response)
    
elif total_read_response.status_code == 413:
    print("\nBulk data is too big to be read in one go.")
    describe_read_response = client.get(f'{welllog_dms_url}/{record_id}/data', params={"describe":True})
    print_response(describe_read_response)
    
    describe_read_data = describe_read_response.json()
    columns = describe_read_data["columns"]
    rows_count = describe_read_data["numberOfRows"]
    print(f"Bulk data contains {len(columns)} curves of {rows_count:,} rows. It represent {len(describe_read_data['columns']) * describe_read_data['numberOfRows']:,} values.")
    
    columns_per_chunk = min(COLUMNS_LIMIT, int(VALUES_LIMIT / rows_count))
    print(f"Each read request will ask for {columns_per_chunk} curves.")
    curves_selection = [columns[i : i + columns_per_chunk] 
                       for i in range(0, len(columns), columns_per_chunk)]
    print(f"\nGroup of curves to be requested:\n{curves_selection}\n")
    
    read_chunks_routines = [async_client.get(f'{welllog_dms_url}/{record_id}/data', params={"curves" : ','.join(_curves)}, headers=parquet_headers)
                           for _curves in curves_selection]
    
    print("Reading bulk data by chunks asynchronously...")
    total_read_responses = await asyncio.gather(*read_chunks_routines)
    print("All chunks have been received!\n")
    
    # Create pandas dataframe from responses' body
    total_read_dfs = [create_df_from_response(_read_response) for _read_response in total_read_responses]
    
    # Merge all together retrieved chunks' dataframe into one dataframe
    total_read_df = pd.concat(total_read_dfs, axis=1)
    
total_read_df
```

    GET : https://OSDU_BASE_URL/api/os-wellbore-ddms/ddms/v3/welllogs/MY_RECORD_ID/data -> 413

    b'{"detail":"{\\"message\\": \\"Too many values requested: 83000000. The maximum allowed is 10000000.\\", \\"requested\\": 83000000, \\"limit\\": 10000000}"}'
    
    Bulk data is too big to be read in one go.
    GET : https://OSDU_BASE_URL/api/os-wellbore-ddms/ddms/v3/welllogs/MY_RECORD_ID/data?describe=true -> 200
    Bulk data contains 83 curves of 1,000,000 rows. It represent 83,000,000 values.
    Each read requests will ask for 10 curves
    
    Group of curves to be requested:
     [['float-curve-0', 'float-curve-1', 'float-curve-2', 'float-curve-3', 'float-curve-4', 'float-curve-5', 'float-curve-6', 'float-curve-7', 'float-curve-8', 'float-curve-9'], ['float-curve-10', 'float-curve-11', 'float-curve-12', 'float-curve-13', 'float-curve-14', 'float-curve-15', 'float-curve-16', 'float-curve-17', 'float-curve-18', 'float-curve-19'], ['float-curve-20', 'float-curve-21', 'float-curve-22', 'float-curve-23', 'float-curve-24', 'float-curve-25', 'float-curve-26', 'float-curve-27', 'float-curve-28', 'float-curve-29'], ['float-curve-30', 'float-curve-31', 'float-curve-32', 'float-curve-33', 'float-curve-34', 'float-curve-35', 'float-curve-36', 'float-curve-37', 'float-curve-38', 'float-curve-39'], ['float-curve-40', 'float-curve-41', 'float-curve-42', 'float-curve-43', 'float-curve-44', 'float-curve-45', 'float-curve-46', 'float-curve-47', 'float-curve-48', 'float-curve-49'], ['float-curve-50', 'float-curve-51', 'float-curve-52', 'float-curve-53', 'float-curve-54', 'float-curve-55', 'float-curve-56', 'float-curve-57', 'float-curve-58', 'float-curve-59'], ['float-curve-60', 'float-curve-61', 'float-curve-62', 'float-curve-63', 'float-curve-64', 'float-curve-65', 'float-curve-66', 'float-curve-67', 'float-curve-68', 'float-curve-69'], ['float-curve-70', 'float-curve-71', 'float-curve-72', 'float-curve-73', 'float-curve-74', 'float-curve-75', 'float-curve-76', 'float-curve-77', 'float-curve-78', 'float-curve-79'], ['float-curve-80', 'float-curve-81', 'float-curve-82']]
    
    Reading bulk data by chunks asynchronously...
    All chunks have been received!
    
    




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
      <th>float-curve-0</th>
      <th>float-curve-1</th>
      <th>float-curve-2</th>
      <th>float-curve-3</th>
      <th>float-curve-4</th>
      <th>float-curve-5</th>
      <th>float-curve-6</th>
      <th>float-curve-7</th>
      <th>float-curve-8</th>
      <th>float-curve-9</th>
      <th>...</th>
      <th>float-curve-73</th>
      <th>float-curve-74</th>
      <th>float-curve-75</th>
      <th>float-curve-76</th>
      <th>float-curve-77</th>
      <th>float-curve-78</th>
      <th>float-curve-79</th>
      <th>float-curve-80</th>
      <th>float-curve-81</th>
      <th>float-curve-82</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>0.561653</td>
      <td>0.357109</td>
      <td>0.561343</td>
      <td>0.957882</td>
      <td>0.848126</td>
      <td>0.384168</td>
      <td>0.203289</td>
      <td>0.375742</td>
      <td>0.302330</td>
      <td>0.845720</td>
      <td>...</td>
      <td>0.974872</td>
      <td>0.823158</td>
      <td>0.744154</td>
      <td>0.894489</td>
      <td>0.048051</td>
      <td>0.191020</td>
      <td>0.667232</td>
      <td>0.944684</td>
      <td>0.205424</td>
      <td>0.614031</td>
    </tr>
    <tr>
      <th>1</th>
      <td>0.860161</td>
      <td>0.404813</td>
      <td>0.999685</td>
      <td>0.403734</td>
      <td>0.330359</td>
      <td>0.473276</td>
      <td>0.079577</td>
      <td>0.883874</td>
      <td>0.248177</td>
      <td>0.520031</td>
      <td>...</td>
      <td>0.921179</td>
      <td>0.408297</td>
      <td>0.615726</td>
      <td>0.357840</td>
      <td>0.437411</td>
      <td>0.484429</td>
      <td>0.549779</td>
      <td>0.446323</td>
      <td>0.123743</td>
      <td>0.424978</td>
    </tr>
    <tr>
      <th>2</th>
      <td>0.230994</td>
      <td>0.701664</td>
      <td>0.059868</td>
      <td>0.866748</td>
      <td>0.587617</td>
      <td>0.904564</td>
      <td>0.488008</td>
      <td>0.681888</td>
      <td>0.961089</td>
      <td>0.410333</td>
      <td>...</td>
      <td>0.626242</td>
      <td>0.368079</td>
      <td>0.627273</td>
      <td>0.866717</td>
      <td>0.811112</td>
      <td>0.892841</td>
      <td>0.377545</td>
      <td>0.510975</td>
      <td>0.255662</td>
      <td>0.043609</td>
    </tr>
    <tr>
      <th>3</th>
      <td>0.039214</td>
      <td>0.015107</td>
      <td>0.572603</td>
      <td>0.757716</td>
      <td>0.702208</td>
      <td>0.999775</td>
      <td>0.045320</td>
      <td>0.981300</td>
      <td>0.928267</td>
      <td>0.848884</td>
      <td>...</td>
      <td>0.138135</td>
      <td>0.025714</td>
      <td>0.394036</td>
      <td>0.903475</td>
      <td>0.755836</td>
      <td>0.269777</td>
      <td>0.163004</td>
      <td>0.357546</td>
      <td>0.975143</td>
      <td>0.739757</td>
    </tr>
    <tr>
      <th>4</th>
      <td>0.421962</td>
      <td>0.060224</td>
      <td>0.771250</td>
      <td>0.391762</td>
      <td>0.298185</td>
      <td>0.509154</td>
      <td>0.570597</td>
      <td>0.085882</td>
      <td>0.458086</td>
      <td>0.499488</td>
      <td>...</td>
      <td>0.569084</td>
      <td>0.464860</td>
      <td>0.843537</td>
      <td>0.080980</td>
      <td>0.708808</td>
      <td>0.215453</td>
      <td>0.634032</td>
      <td>0.378934</td>
      <td>0.658440</td>
      <td>0.630914</td>
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
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
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
      <th>999995</th>
      <td>0.178788</td>
      <td>0.411284</td>
      <td>0.225754</td>
      <td>0.426515</td>
      <td>0.149432</td>
      <td>0.543071</td>
      <td>0.016034</td>
      <td>0.912921</td>
      <td>0.786004</td>
      <td>0.772934</td>
      <td>...</td>
      <td>0.932847</td>
      <td>0.885079</td>
      <td>0.534289</td>
      <td>0.952742</td>
      <td>0.681911</td>
      <td>0.551813</td>
      <td>0.121215</td>
      <td>0.154066</td>
      <td>0.255789</td>
      <td>0.408960</td>
    </tr>
    <tr>
      <th>999996</th>
      <td>0.289828</td>
      <td>0.930861</td>
      <td>0.675247</td>
      <td>0.793975</td>
      <td>0.128721</td>
      <td>0.528824</td>
      <td>0.098364</td>
      <td>0.411375</td>
      <td>0.961170</td>
      <td>0.650969</td>
      <td>...</td>
      <td>0.729353</td>
      <td>0.680816</td>
      <td>0.661337</td>
      <td>0.418669</td>
      <td>0.831224</td>
      <td>0.856098</td>
      <td>0.467002</td>
      <td>0.326681</td>
      <td>0.366456</td>
      <td>0.911664</td>
    </tr>
    <tr>
      <th>999997</th>
      <td>0.463705</td>
      <td>0.444714</td>
      <td>0.724229</td>
      <td>0.160315</td>
      <td>0.883222</td>
      <td>0.444145</td>
      <td>0.907256</td>
      <td>0.498612</td>
      <td>0.828349</td>
      <td>0.950625</td>
      <td>...</td>
      <td>0.034442</td>
      <td>0.987607</td>
      <td>0.766548</td>
      <td>0.093291</td>
      <td>0.920685</td>
      <td>0.736951</td>
      <td>0.433659</td>
      <td>0.038032</td>
      <td>0.659308</td>
      <td>0.929024</td>
    </tr>
    <tr>
      <th>999998</th>
      <td>0.775479</td>
      <td>0.573866</td>
      <td>0.946070</td>
      <td>0.786278</td>
      <td>0.430194</td>
      <td>0.659571</td>
      <td>0.073379</td>
      <td>0.794796</td>
      <td>0.178272</td>
      <td>0.819471</td>
      <td>...</td>
      <td>0.506286</td>
      <td>0.536543</td>
      <td>0.087606</td>
      <td>0.728651</td>
      <td>0.944643</td>
      <td>0.971663</td>
      <td>0.850513</td>
      <td>0.393359</td>
      <td>0.920398</td>
      <td>0.055620</td>
    </tr>
    <tr>
      <th>999999</th>
      <td>0.787469</td>
      <td>0.497432</td>
      <td>0.555824</td>
      <td>0.004622</td>
      <td>0.746023</td>
      <td>0.268821</td>
      <td>0.944797</td>
      <td>0.561048</td>
      <td>0.871234</td>
      <td>0.898111</td>
      <td>...</td>
      <td>0.566569</td>
      <td>0.040034</td>
      <td>0.742755</td>
      <td>0.240439</td>
      <td>0.371686</td>
      <td>0.813523</td>
      <td>0.459830</td>
      <td>0.936860</td>
      <td>0.844398</td>
      <td>0.249257</td>
    </tr>
  </tbody>
</table>
<p>1000000 rows × 83 columns</p>
</div>


