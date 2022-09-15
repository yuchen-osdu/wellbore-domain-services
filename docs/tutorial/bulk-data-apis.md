# Introduction

In this tutorial we will explain: 

- How to [write bulk data](#write-bulk-data---all-at-once) using [Wellbore DDMS chunking APIs](/solutions/osduwellboreddms/apis/wellbore-data-access-v3)
- How to [read and write a given version](#welllog-record-versioning) of a WellLog
- How to [read bulk data](#read-bulk-data) with filtering options as columns, offset and limit
- How is ensured meta (record) and bulk [data consistency for WellLogs](#welllog-consistency-rules)
- How is ensured meta (record) and bulk [data consistency for Wellbore Trajectories](#trajectory-consistency-rules)

Here is the corresponding Jupyter notebook of this tutorial: [Wellbore-DDMS-Bulk-data-API.ipynb](/sites/default/files/solution/wellboreDMS/Wellbore-DDMS-Bulk-data-API.ipynb)

# Prerequisites

## Required Python packages

Before to start to write bulk data through Wellbore DDMS API's, you will need to install the Python packages below:

 - The pandas module and its Pandas.Dataframe json format to structure log bulk data to be written to the Wellbore DDMS.
 - The pyarrow module to transform Pandas.Dataframe to parquet file through the pyarrow engine.
 - The httpx module that allows to post request to the Wellbore DDMS.

```python
# Prerequisite to run this notebook
!python -m pip install pip --upgrade
!pip install pandas numpy httpx pyarrow
``` 

## Authorization

For any call to Wellbore DDMS API's you need to pass into the header of the request a valid bearer token. This token can be obtained from any API catalog on the developer portal. You will need first to request a developer base subscription. Then from the developer base subscription pick any API and execute it. A valid bearer token is returns in the Curl section of the response. Copy this token value and assign it to the TOKEN variable below.

```python
TOKEN = '' # Paste here the token without the bearer prefix
```

## Utility methods

<details> <summary> Helper functions used in the different sample scripts of this tutorial. </summary>

```python
from typing import List
import httpx
import pandas as pd
import numpy as np
import io
from IPython.display import display_html, display, HTML
from itertools import chain, cycle

def generate_df_typed(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('bool'):
            return np.random.choice(a=[False, True], size=size) 
        if col_name.startswith('date'):
            return (np.datetime4('2021-01-01') + days for days in range(size))
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                      for c in columns}, index=index)
    return df

def multi_table(table_list):
    '''Acceps a list of IpyTable objects and returns a table which contains each IpyTable in a cell'''
    return HTML(
        '<table><tr style="background-color:white;">' + 
        ''.join(['<td>' + table._repr_html_() + '</td>' for table in table_list]) +
        '</tr></table>'
    )

def gen_color(color):
    def fct(val=None):
         return f'color: {color}'
    return fct

def display_operation(before, sent, after):
    colors = ['blue', 'green', 'orange', 'red']
    color_fct = [gen_color(c) for c in colors]
    sent_st = [sent[i].style.set_caption(f'chunk {i+1} sent').applymap(color_fct[i]) for i in range(len(sent))]
    def color_output(s):
        res = []
        for r in s.index:
            c = ''
            for i in range(len(sent)):
                if s.name in sent[i] and int(r) in sent[i][s.name]:
                    c = color_fct[i]()#f'color: {colors[i]}'
            res.append(c)
        return res

    margin = '65'
    after_st = after.style.set_table_attributes(f"style='margin-left:{margin}px'").apply(color_output).highlight_null(null_color='lightyellow').set_caption('Final data - After session commit')   
    display(multi_table([before.style.set_table_attributes(f"style='margin-right:{margin}px'").set_caption('Initial data - Before session'), *sent_st, after_st]))
    
def display_side_by_side(dfs:list, captions:list):
    """Display tables side by side to save vertical space
    Input:
        dfs: list of pandas.DataFrame
        captions: list of table captions
    """
    output = ""
    combined = dict(zip(captions, dfs))
    for caption, df in combined.items():
        output += df.style.set_table_attributes("style='display:inline'").set_caption(caption)._repr_html_()
        output += "\xa0\xa0\xa0"
    display(HTML(output))
    
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
    content_type = response.headers.get('content-type')
    
    if content_type == 'application/json':
        return pd.DataFrame.from_dict(response.json())
    
    elif content_type == 'application/x-parquet':
        f = io.BytesIO(response.content)
        f.seek(0)
        return pd.read_parquet(f)
    
    raise ValueError(f"Unknown content-type: '{content_type}'")
    
def display_previous_and_current_well_log_data_versions(record_id):
    """Display the previous and current WellLog data versions for a given record id and highlight differences between them.
    Input:
        record_id: a WellLog record id
    """
    # list record version
    results_response = client.get(f'{welllog_dms_url}/{record_id}/versions')
    wellLog_versions_response = results_response.json()
    versions = wellLog_versions_response['versions']
    
    is_previous_results = False
    is_current_results = False
    if len(versions) >= 2:
        previous_version_id = versions[len(versions)-2]
        curl = f'{welllog_dms_url}/{record_id}/versions/{previous_version_id}/data'
        results_response = client.get(curl)
        if results_response.status_code == 200:
            previous_results = create_df_from_response(results_response)
            is_previous_results = True
    
        current_version_id = versions[len(versions)-1]
        curl = f'{welllog_dms_url}/{record_id}/versions/{current_version_id}/data'
        results_response = client.get(curl)
        if results_response.status_code == 200:
            current_results = create_df_from_response(results_response)
            is_current_results = True
    
    colors = ['blue', 'red']
    color_fct = [gen_color(c) for c in colors]
    def color_output(s):
        res = []        
        for r in s.index:
            c = ''
            if s.name in previous_results and int(r) in previous_results[s.name]:
                c = color_fct[0]()
            else:
                c = color_fct[1]()
            res.append(c)
        return res
    
    margin = '65'
    tables = []
    if is_previous_results:
        previous_results_st = previous_results.style.set_table_attributes(f"style='margin-left:{margin}px'").highlight_null(null_color='lightyellow').set_caption('Previous WellLog data version').applymap(color_fct[0])  
        tables.append(previous_results_st)
        
    if is_current_results:
        if is_previous_results:
            current_results_st = current_results.style.set_table_attributes(f"style='margin-left:{margin}px'").apply(color_output).highlight_null(null_color='lightyellow').set_caption('Current WellLog data version with data chunks added in red')
            tables.append(current_results_st)
        else:
            current_results_st = current_results.style.set_table_attributes(f"style='margin-left:{margin}px'").highlight_null(null_color='lightyellow').set_caption('Current WellLog data version') 
            tables.append(current_results_st)
        
    display(multi_table(tables))
```
</details> 

## Settings

Several settings as the base url end-point and the data partition id to create a WellLog to the Wellbore DDMS. Please change those settings accordingly to the environment settings that you want to target.

```python
base_url = "" # set a base URL value
data_partition_id = "" # set a data partition id
legal_tag = "" # set a valid legal tag in the data partition 
acl_domain = "" # set an Access Control Lists (ACL) domain

welllog_dms_url = f'{base_url}/api/os-wellbore-ddms/ddms/v3/welllogs'

client = httpx.Client(verify=False,
    headers={
        "data-partition-id": f"{data_partition_id}",
        "Authorization": f"Bearer {TOKEN}",
    },
    timeout=120
)

# Create a new WellLog. Here is a fake body just to illustrate the API use
record = {
    "kind": "osdu:wks:work-product-component--WellLog:1.2.0",
    "acl": {
        "viewers": [f"data.default.viewers@{data_partition_id}.{acl_domain}"],
        "owners": [f"data.default.owners@{data_partition_id}.{acl_domain}"]
      },
    "legal": {
        "legaltags": [f"{legal_tag}"],
        "otherRelevantDataCountries": ["US"],
    },
    "data": {
        "ReferenceCurveID": "MD",
        "WellboreID": "namespace:master-data--Wellbore:SomeUniqueWellboreID:",
        "Curves": [
            {
                "CurveID": "MD",
                "NumberOfColumns": 1
            },
            {
                "CurveID": "X",
                "NumberOfColumns": 1
            }
        ]
    },
    "version" : 0
}
```

## Create a WellLog record

The script below is creating a WellLog record that is used in this tutorial to demonstrate how to write WellLog bulk data to the Wellbore DDMS.

```python
response = client.post(welllog_dms_url, json=[record])
print_response(response)
record_id = response.json()["recordIds"][0]
record_id
``` 

# Write bulk data - all at once<a name="write-bulk-data---all-at-once"></a>

Each time that data are written to the WellLog, a new version is created to the Wellbore DDMS. This is true when writting the entire bulk data at once or even by chunks (cover in a next section of this tutorial).
So when writting all bulk data at once, the payload is expected to contain the entire bulk data that replaces the previous bulk version by creating a new version. This new bulk version becomes the latest one and the current version that is returned by the GET WellLog bulk data API for the given record id.

The Wellbore DDMS bulk data API supports both Parquet and JSON formats. In order to target one of this format the 'Content-Type' must be set accordingly in the headers of the HTTP POST request. Wellbore DDMS API supports HTTP chunked encoding as well.

First of all let's generate a Pandas.Dataframe through the code below with 2 columns and 5 rows.

```python
generated_dataframe = generate_df(['COLUMN_MD', 'COLUMN_X'], range(5))
generated_dataframe
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
      <th>COLUMN_MD</th>
      <th>COLUMN_X</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>986</td>
      <td>712</td>
    </tr>
    <tr>
      <th>1</th>
      <td>311</td>
      <td>348</td>
    </tr>
    <tr>
      <th>2</th>
      <td>-27</td>
      <td>339</td>
    </tr>
    <tr>
      <th>3</th>
      <td>230</td>
      <td>191</td>
    </tr>
    <tr>
      <th>4</th>
      <td>162</td>
      <td>740</td>
    </tr>
  </tbody>
</table>
</div>

### All at once - Parquet

Sending the whole dataframe to the WellLog bulk data.

```python
data_to_send_parquet = generated_dataframe.to_parquet(path=None, engine="pyarrow")
headers = { 'content-type': 'application/x-parquet'}

print_response(client.post(f'{welllog_dms_url}/{record_id}/data', data=data_to_send_parquet, headers=headers))
```
    
### All at once - JSON

With the JSON format the orient parameter has to be set accordingly to the Pandas.Dataframe orientation.
This orient value can be passed through the params argument of the HTTP POST request. 
Supported orient values are split and columns. The default orient value is set to split.

Here are examples of the same Pandas.Dataframe (5 rows and 2 columns) with different orientation:

split:
{"columns":["COLUMN_MD","COLUMN_X"],"index":[0,1,2,3,4],"data":[[0.0,1001],[0.5,1002],[1.0,1003],[1.5,1004],[2.0,1005]]}
 
columns:
{"COLUMN_MD":{"0":0.0,"1":0.5,"2":1.0,"3":1.5,"4":2.0},"COLUMN_X":{"0":1001,"1":1002,"2":1003,"3":1004,"4":1005}}
 
```python
data_to_send_json = {
    'index': [0, 1, 2, 3, 4],
    'columns': ['COLUMN_MD', 'COLUMN_X'],
    'data': [[265, 845], [92, 246], [804, 268], [645, 877], [-20, -28]]
}

params = {'orient':'split'}
print_response(client.post(f'{welllog_dms_url}/{record_id}/data', params=params, json=data_to_send_json))
```
    
# Write bulk data - by chunk

In order to write WellLog bulk data by chunks to the Wellbore DDMS you have to follow those 3 steps:

1. Create a WellLog session - POST /alpha/ddms/v3/welllogs/{record_id}/sessions
2. Send data by chunk in the session - POST /alpha/ddms/v3/welllogs/{record_id}/sessions/{session_id}/data  
3. Commit the session once all chunks are sent -  PATCH /alpha/ddms/v3/welllogs/{welllog_id}/sessions/{session_id}

In step 3 you can also update the session or abandon. This is controlled by the state attribute that is passed in the JSON of the PATCH HTTP session API.

{
  "state": "commit", "abandon" or "update"
}

## Flow to send json: 
## Open a new session > Send json chunks > Commit the session

### Session mode: update or overwrite

A session can be created with two different modes:
- update: existing data in previous WellLog version is merged with the data sent during the session when the session is committed.
- overwrite: existing data in previous WellLog version is ignored, the final result only contains data sent during the session when the session is committed. In this case the only way to retrieve the previous data is querying the previous WellLog version.

```python
SESSION_MODE = 'update' # 'update' | 'overwrite'
```

## Add data by rows 

In the sample script below the WellLog data is ingested by chunk of row data.
In the same session it is possible to liberate WellLog data with both JSON and Parquet formats as shown below: 

```python
# Create a session
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})

print_response(create_session_response)
session_data = create_session_response.json()
session_id = session_data['id']
print(f"Session created: {session_data['state']} with id {session_id}\n")
                               
# append first chunk - JSON
chunk_1 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(5,10))
response_chunk_1 = client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_1.to_dict(orient='split'))
print_response(response_chunk_1)

# append second chunk - JSON
chunk_2 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(10,15))
response_chunk_2 = client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_2.to_dict(orient='split'))
print_response(response_chunk_2)


```

Once the whole WellLog data has been sent through the session, then the session needs to be committed using a session PATCH API call with the 'state' attribute sets to 'commit' value.

```python
# Commit session
commit_session_response = client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'})

print_response(commit_session_response)
session = commit_session_response.json()
print('Session after commit =', session['state'])
```
    
Or the session can be abandonned calling the session PATCH API with the 'state' attribute sets to 'abandon' value.

```python
# OR else, ABANDON session
abandon_session_response = client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'abandon'})
print_response(abandon_session_response)
if abandon_session_response.status_code == httpx.codes.OK:
    print('Session after commit =', abandon_session_response.json()['state'])
```

## Flow to send parquet: 
## Open a new session > Send parquet chunks > Commit the session

```python
SESSION_MODE = 'update'
```

```python
# Create a session to send parquet
create_session_response = client.post(f'{wellbore_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})

print_response(create_session_response)
session_data = create_session_response.json()
session_id = session_data['id']
print(f"Session created: {session_data['state']} with id {session_id}\n")
```

```python
# append first chunk - PARQUET
chunk_3 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(15,20))
headers = {'content-type': 'application/x-parquet'}
response_chunk_3 = client.post(f'{wellbore_dms_url}/{record_id}/sessions/{session_id}/data', data=chunk_3.to_parquet(engine="pyarrow"), headers=headers)
print_response(response_chunk_3)
```


```python
# append second chunk - PARQUET
chunk_4 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(20,25))
headers = {'content-type': 'application/x-parquet'}
response_chunk_4 = client.post(f'{wellbore_dms_url}/{record_id}/sessions/{session_id}/data', data=chunk_4.to_parquet(engine="pyarrow"), headers=headers)
print_response(response_chunk_4)
```

    

```python
# commit session for parquet
print_response(client.patch(f'{wellbore_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'}))
```

The code below shows initial WellLog data before the session and chunks by rows inserted to the final WellLog data version after the session has been committed.

```python
# Display result
results_response = client.get(f'{welllog_dms_url}/{record_id}/data')
results_cols_md_x = create_df_from_response(results_response) 
display_operation(generated_dataframe, [chunk_1, chunk_2, chunk_3], results_cols_md_x)
```
<div>
<style  type="text/css" >
#T_22a7e_row0_col0,#T_22a7e_row0_col1,#T_22a7e_row1_col0,#T_22a7e_row1_col1,#T_22a7e_row2_col0,#T_22a7e_row2_col1,#T_22a7e_row3_col0,#T_22a7e_row3_col1,#T_22a7e_row4_col0,#T_22a7e_row4_col1{
            color:  blue;
        }
#T_572e1_row0_col0,#T_572e1_row0_col1,#T_572e1_row1_col0,#T_572e1_row1_col1,#T_572e1_row2_col0,#T_572e1_row2_col1,#T_572e1_row3_col0,#T_572e1_row3_col1,#T_572e1_row4_col0,#T_572e1_row4_col1{
            color:  green;
        }
#T_cb70d_row0_col0,#T_cb70d_row0_col1,#T_cb70d_row1_col0,#T_cb70d_row1_col1,#T_cb70d_row2_col0,#T_cb70d_row2_col1,#T_cb70d_row3_col0,#T_cb70d_row3_col1,#T_cb70d_row4_col0,#T_cb70d_row4_col1{
            color:  orange;
        }
#T_d0f3e_row0_col0,#T_d0f3e_row0_col1,#T_d0f3e_row1_col0,#T_d0f3e_row1_col1,#T_d0f3e_row2_col0,#T_d0f3e_row2_col1,#T_d0f3e_row3_col0,#T_d0f3e_row3_col1,#T_d0f3e_row4_col0,#T_d0f3e_row4_col1{
            color:  red;
        }
#T_c63f5_row5_col0,#T_c63f5_row5_col1,#T_c63f5_row6_col0,#T_c63f5_row6_col1,#T_c63f5_row7_col0,#T_c63f5_row7_col1,#T_c63f5_row8_col0,#T_c63f5_row8_col1,#T_c63f5_row9_col0,#T_c63f5_row9_col1{
            color:  blue;
        }
#T_c63f5_row10_col0,#T_c63f5_row10_col1,#T_c63f5_row11_col0,#T_c63f5_row11_col1,#T_c63f5_row12_col0,#T_c63f5_row12_col1,#T_c63f5_row13_col0,#T_c63f5_row13_col1,#T_c63f5_row14_col0,#T_c63f5_row14_col1{
            color:  green;
        }
#T_c63f5_row15_col0,#T_c63f5_row15_col1,#T_c63f5_row16_col0,#T_c63f5_row16_col1,#T_c63f5_row17_col0,#T_c63f5_row17_col1,#T_c63f5_row18_col0,#T_c63f5_row18_col1,#T_c63f5_row19_col0,#T_c63f5_row19_col1{
            color:  orange;
        }
#T_c63f5_row20_col0,#T_c63f5_row20_col1,#T_c63f5_row21_col0,#T_c63f5_row21_col1,#T_c63f5_row22_col0,#T_c63f5_row22_col1,#T_c63f5_row23_col0,#T_c63f5_row23_col1,#T_c63f5_row24_col0,#T_c63f5_row24_col1{
            color:  red;
        }
</style>
<table id="T_4dbb3_" style='display:inline'><caption>Initial data - Before session</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_4dbb3_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_4dbb3_row0_col0" class="data row0 col0" >957</td>
                        <td id="T_4dbb3_row0_col1" class="data row0 col1" >190</td>
            </tr>
            <tr>
                        <th id="T_4dbb3_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_4dbb3_row1_col0" class="data row1 col0" >649</td>
                        <td id="T_4dbb3_row1_col1" class="data row1 col1" >907</td>
            </tr>
            <tr>
                        <th id="T_4dbb3_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_4dbb3_row2_col0" class="data row2 col0" >598</td>
                        <td id="T_4dbb3_row2_col1" class="data row2 col1" >697</td>
            </tr>
            <tr>
                        <th id="T_4dbb3_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_4dbb3_row3_col0" class="data row3 col0" >396</td>
                        <td id="T_4dbb3_row3_col1" class="data row3 col1" >8</td>
            </tr>
            <tr>
                        <th id="T_4dbb3_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_4dbb3_row4_col0" class="data row4 col0" >57</td>
                        <td id="T_4dbb3_row4_col1" class="data row4 col1" >297</td>
            </tr>
    </tbody></table>
<table id="T_22a7e_" style='display:inline'><caption>chunk 1 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_22a7e_level0_row0" class="row_heading level0 row0" >5</th>
                        <td id="T_22a7e_row0_col0" class="data row0 col0" >462</td>
                        <td id="T_22a7e_row0_col1" class="data row0 col1" >95</td>
            </tr>
            <tr>
                        <th id="T_22a7e_level0_row1" class="row_heading level0 row1" >6</th>
                        <td id="T_22a7e_row1_col0" class="data row1 col0" >275</td>
                        <td id="T_22a7e_row1_col1" class="data row1 col1" >946</td>
            </tr>
            <tr>
                        <th id="T_22a7e_level0_row2" class="row_heading level0 row2" >7</th>
                        <td id="T_22a7e_row2_col0" class="data row2 col0" >-79</td>
                        <td id="T_22a7e_row2_col1" class="data row2 col1" >965</td>
            </tr>
            <tr>
                        <th id="T_22a7e_level0_row3" class="row_heading level0 row3" >8</th>
                        <td id="T_22a7e_row3_col0" class="data row3 col0" >174</td>
                        <td id="T_22a7e_row3_col1" class="data row3 col1" >5</td>
            </tr>
            <tr>
                        <th id="T_22a7e_level0_row4" class="row_heading level0 row4" >9</th>
                        <td id="T_22a7e_row4_col0" class="data row4 col0" >848</td>
                        <td id="T_22a7e_row4_col1" class="data row4 col1" >344</td>
            </tr>
    </tbody></table>
<table id="T_572e1_" style='display:inline'><caption>chunk 2 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_572e1_level0_row0" class="row_heading level0 row0" >10</th>
                        <td id="T_572e1_row0_col0" class="data row0 col0" >252</td>
                        <td id="T_572e1_row0_col1" class="data row0 col1" >929</td>
            </tr>
            <tr>
                        <th id="T_572e1_level0_row1" class="row_heading level0 row1" >11</th>
                        <td id="T_572e1_row1_col0" class="data row1 col0" >390</td>
                        <td id="T_572e1_row1_col1" class="data row1 col1" >629</td>
            </tr>
            <tr>
                        <th id="T_572e1_level0_row2" class="row_heading level0 row2" >12</th>
                        <td id="T_572e1_row2_col0" class="data row2 col0" >449</td>
                        <td id="T_572e1_row2_col1" class="data row2 col1" >986</td>
            </tr>
            <tr>
                        <th id="T_572e1_level0_row3" class="row_heading level0 row3" >13</th>
                        <td id="T_572e1_row3_col0" class="data row3 col0" >-34</td>
                        <td id="T_572e1_row3_col1" class="data row3 col1" >400</td>
            </tr>
            <tr>
                        <th id="T_572e1_level0_row4" class="row_heading level0 row4" >14</th>
                        <td id="T_572e1_row4_col0" class="data row4 col0" >607</td>
                        <td id="T_572e1_row4_col1" class="data row4 col1" >272</td>
            </tr>
    </tbody></table>
<table id="T_cb70d_" style='display:inline'><caption>chunk 3 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_cb70d_level0_row0" class="row_heading level0 row0" >15</th>
                        <td id="T_cb70d_row0_col0" class="data row0 col0" >390</td>
                        <td id="T_cb70d_row0_col1" class="data row0 col1" >915</td>
            </tr>
            <tr>
                        <th id="T_cb70d_level0_row1" class="row_heading level0 row1" >16</th>
                        <td id="T_cb70d_row1_col0" class="data row1 col0" >-73</td>
                        <td id="T_cb70d_row1_col1" class="data row1 col1" >368</td>
            </tr>
            <tr>
                        <th id="T_cb70d_level0_row2" class="row_heading level0 row2" >17</th>
                        <td id="T_cb70d_row2_col0" class="data row2 col0" >277</td>
                        <td id="T_cb70d_row2_col1" class="data row2 col1" >-21</td>
            </tr>
            <tr>
                        <th id="T_cb70d_level0_row3" class="row_heading level0 row3" >18</th>
                        <td id="T_cb70d_row3_col0" class="data row3 col0" >543</td>
                        <td id="T_cb70d_row3_col1" class="data row3 col1" >-78</td>
            </tr>
            <tr>
                        <th id="T_cb70d_level0_row4" class="row_heading level0 row4" >19</th>
                        <td id="T_cb70d_row4_col0" class="data row4 col0" >754</td>
                        <td id="T_cb70d_row4_col1" class="data row4 col1" >94</td>
            </tr>
    </tbody></table>
<table id="T_d0f3e_" style='display:inline'><caption>chunk 4 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_d0f3e_level0_row0" class="row_heading level0 row0" >20</th>
                        <td id="T_d0f3e_row0_col0" class="data row0 col0" >-82</td>
                        <td id="T_d0f3e_row0_col1" class="data row0 col1" >27</td>
            </tr>
            <tr>
                        <th id="T_d0f3e_level0_row1" class="row_heading level0 row1" >21</th>
                        <td id="T_d0f3e_row1_col0" class="data row1 col0" >431</td>
                        <td id="T_d0f3e_row1_col1" class="data row1 col1" >933</td>
            </tr>
            <tr>
                        <th id="T_d0f3e_level0_row2" class="row_heading level0 row2" >22</th>
                        <td id="T_d0f3e_row2_col0" class="data row2 col0" >318</td>
                        <td id="T_d0f3e_row2_col1" class="data row2 col1" >465</td>
            </tr>
            <tr>
                        <th id="T_d0f3e_level0_row3" class="row_heading level0 row3" >23</th>
                        <td id="T_d0f3e_row3_col0" class="data row3 col0" >-3</td>
                        <td id="T_d0f3e_row3_col1" class="data row3 col1" >593</td>
            </tr>
            <tr>
                        <th id="T_d0f3e_level0_row4" class="row_heading level0 row4" >24</th>
                        <td id="T_d0f3e_row4_col0" class="data row4 col0" >256</td>
                        <td id="T_d0f3e_row4_col1" class="data row4 col1" >130</td>
            </tr>
    </tbody></table>
<table id="T_c63f5_" style='display:inline'><caption>Final data - After session commit</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_c63f5_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_c63f5_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_c63f5_row0_col1" class="data row0 col1" >845</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_c63f5_row1_col0" class="data row1 col0" >92</td>
                        <td id="T_c63f5_row1_col1" class="data row1 col1" >246</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_c63f5_row2_col0" class="data row2 col0" >804</td>
                        <td id="T_c63f5_row2_col1" class="data row2 col1" >268</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_c63f5_row3_col0" class="data row3 col0" >645</td>
                        <td id="T_c63f5_row3_col1" class="data row3 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_c63f5_row4_col0" class="data row4 col0" >-20</td>
                        <td id="T_c63f5_row4_col1" class="data row4 col1" >-28</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_c63f5_row5_col0" class="data row5 col0" >462</td>
                        <td id="T_c63f5_row5_col1" class="data row5 col1" >95</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_c63f5_row6_col0" class="data row6 col0" >275</td>
                        <td id="T_c63f5_row6_col1" class="data row6 col1" >946</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_c63f5_row7_col0" class="data row7 col0" >-79</td>
                        <td id="T_c63f5_row7_col1" class="data row7 col1" >965</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_c63f5_row8_col0" class="data row8 col0" >174</td>
                        <td id="T_c63f5_row8_col1" class="data row8 col1" >5</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_c63f5_row9_col0" class="data row9 col0" >848</td>
                        <td id="T_c63f5_row9_col1" class="data row9 col1" >344</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_c63f5_row10_col0" class="data row10 col0" >252</td>
                        <td id="T_c63f5_row10_col1" class="data row10 col1" >929</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_c63f5_row11_col0" class="data row11 col0" >390</td>
                        <td id="T_c63f5_row11_col1" class="data row11 col1" >629</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_c63f5_row12_col0" class="data row12 col0" >449</td>
                        <td id="T_c63f5_row12_col1" class="data row12 col1" >986</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_c63f5_row13_col0" class="data row13 col0" >-34</td>
                        <td id="T_c63f5_row13_col1" class="data row13 col1" >400</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_c63f5_row14_col0" class="data row14 col0" >607</td>
                        <td id="T_c63f5_row14_col1" class="data row14 col1" >272</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_c63f5_row15_col0" class="data row15 col0" >390</td>
                        <td id="T_c63f5_row15_col1" class="data row15 col1" >915</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_c63f5_row16_col0" class="data row16 col0" >-73</td>
                        <td id="T_c63f5_row16_col1" class="data row16 col1" >368</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_c63f5_row17_col0" class="data row17 col0" >277</td>
                        <td id="T_c63f5_row17_col1" class="data row17 col1" >-21</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_c63f5_row18_col0" class="data row18 col0" >543</td>
                        <td id="T_c63f5_row18_col1" class="data row18 col1" >-78</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_c63f5_row19_col0" class="data row19 col0" >754</td>
                        <td id="T_c63f5_row19_col1" class="data row19 col1" >94</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_c63f5_row20_col0" class="data row20 col0" >-82</td>
                        <td id="T_c63f5_row20_col1" class="data row20 col1" >27</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_c63f5_row21_col0" class="data row21 col0" >431</td>
                        <td id="T_c63f5_row21_col1" class="data row21 col1" >933</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_c63f5_row22_col0" class="data row22 col0" >318</td>
                        <td id="T_c63f5_row22_col1" class="data row22 col1" >465</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_c63f5_row23_col0" class="data row23 col0" >-3</td>
                        <td id="T_c63f5_row23_col1" class="data row23 col1" >593</td>
            </tr>
            <tr>
                        <th id="T_c63f5_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_c63f5_row24_col0" class="data row24 col0" >256</td>
                        <td id="T_c63f5_row24_col1" class="data row24 col1" >130</td>
            </tr>
    </tbody></table>
</div>

It is possible to get access to the exhaustive list of versions created for a given WellLog id (GET /ddms/v3/welllogs/{welllogid}/versions).
And then access the WellLog data for a given version (GET /ddms/v3/welllogs/{welllogid}/versions/{version}/data).
This is what the function below is doing reading WellLog data of the previous and current version and highlighting differences between them.
Differences when sending WellLog data in a session with update or overwrite mode is clearly illustrated through WellLog data previous and current versions returned by the function.

```python
display_previous_and_current_well_log_data_versions(record_id)
```

<div>
<style  type="text/css" >
#T_f8ed1_row0_col0,#T_f8ed1_row0_col1,#T_f8ed1_row1_col0,#T_f8ed1_row1_col1,#T_f8ed1_row2_col0,#T_f8ed1_row2_col1,#T_f8ed1_row3_col0,#T_f8ed1_row3_col1,#T_f8ed1_row4_col0,#T_f8ed1_row4_col1{
            color:  blue;
        }

#T_360e3_row0_col0,#T_360e3_row0_col1,#T_360e3_row1_col0,#T_360e3_row1_col1,#T_360e3_row2_col0,#T_360e3_row2_col1,#T_360e3_row3_col0,#T_360e3_row3_col1,#T_360e3_row4_col0,#T_360e3_row4_col1{
            color:  blue;
        }
#T_360e3_row5_col0,#T_360e3_row5_col1,#T_360e3_row6_col0,#T_360e3_row6_col1,#T_360e3_row7_col0,#T_360e3_row7_col1,#T_360e3_row8_col0,#T_360e3_row8_col1,#T_360e3_row9_col0,#T_360e3_row9_col1,#T_360e3_row10_col0,#T_360e3_row10_col1,#T_360e3_row11_col0,#T_360e3_row11_col1,#T_360e3_row12_col0,#T_360e3_row12_col1,#T_360e3_row13_col0,#T_360e3_row13_col1,#T_360e3_row14_col0,#T_360e3_row14_col1,#T_360e3_row15_col0,#T_360e3_row15_col1,#T_360e3_row16_col0,#T_360e3_row16_col1,#T_360e3_row17_col0,#T_360e3_row17_col1,#T_360e3_row18_col0,#T_360e3_row18_col1,#T_360e3_row19_col0,#T_360e3_row19_col1{
            color:  red;
        }
</style>
<table id="T_f8ed1_" style='display:inline'><caption>Previous WellLog data version</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_f8ed1_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_f8ed1_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_f8ed1_row0_col1" class="data row0 col1" >845</td>
            </tr>
            <tr>
                        <th id="T_f8ed1_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_f8ed1_row1_col0" class="data row1 col0" >92</td>
                        <td id="T_f8ed1_row1_col1" class="data row1 col1" >246</td>
            </tr>
            <tr>
                        <th id="T_f8ed1_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_f8ed1_row2_col0" class="data row2 col0" >804</td>
                        <td id="T_f8ed1_row2_col1" class="data row2 col1" >268</td>
            </tr>
            <tr>
                        <th id="T_f8ed1_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_f8ed1_row3_col0" class="data row3 col0" >645</td>
                        <td id="T_f8ed1_row3_col1" class="data row3 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_f8ed1_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_f8ed1_row4_col0" class="data row4 col0" >-20</td>
                        <td id="T_f8ed1_row4_col1" class="data row4 col1" >-28</td>
            </tr>
    </tbody></table>
	<table id="T_360e3_" style='display:inline'><caption>Current WellLog data version with data chunks added in red</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_360e3_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_360e3_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_360e3_row0_col1" class="data row0 col1" >845</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_360e3_row1_col0" class="data row1 col0" >92</td>
                        <td id="T_360e3_row1_col1" class="data row1 col1" >246</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_360e3_row2_col0" class="data row2 col0" >804</td>
                        <td id="T_360e3_row2_col1" class="data row2 col1" >268</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_360e3_row3_col0" class="data row3 col0" >645</td>
                        <td id="T_360e3_row3_col1" class="data row3 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_360e3_row4_col0" class="data row4 col0" >-20</td>
                        <td id="T_360e3_row4_col1" class="data row4 col1" >-28</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_360e3_row5_col0" class="data row5 col0" >-29</td>
                        <td id="T_360e3_row5_col1" class="data row5 col1" >832</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_360e3_row6_col0" class="data row6 col0" >-15</td>
                        <td id="T_360e3_row6_col1" class="data row6 col1" >107</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_360e3_row7_col0" class="data row7 col0" >339</td>
                        <td id="T_360e3_row7_col1" class="data row7 col1" >212</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_360e3_row8_col0" class="data row8 col0" >823</td>
                        <td id="T_360e3_row8_col1" class="data row8 col1" >240</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_360e3_row9_col0" class="data row9 col0" >-97</td>
                        <td id="T_360e3_row9_col1" class="data row9 col1" >349</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_360e3_row10_col0" class="data row10 col0" >183</td>
                        <td id="T_360e3_row10_col1" class="data row10 col1" >89</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_360e3_row11_col0" class="data row11 col0" >194</td>
                        <td id="T_360e3_row11_col1" class="data row11 col1" >276</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_360e3_row12_col0" class="data row12 col0" >-7</td>
                        <td id="T_360e3_row12_col1" class="data row12 col1" >-7</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_360e3_row13_col0" class="data row13 col0" >446</td>
                        <td id="T_360e3_row13_col1" class="data row13 col1" >829</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_360e3_row14_col0" class="data row14 col0" >32</td>
                        <td id="T_360e3_row14_col1" class="data row14 col1" >706</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_360e3_row15_col0" class="data row15 col0" >914</td>
                        <td id="T_360e3_row15_col1" class="data row15 col1" >740</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_360e3_row16_col0" class="data row16 col0" >593</td>
                        <td id="T_360e3_row16_col1" class="data row16 col1" >279</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_360e3_row17_col0" class="data row17 col0" >304</td>
                        <td id="T_360e3_row17_col1" class="data row17 col1" >-57</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_360e3_row18_col0" class="data row18 col0" >697</td>
                        <td id="T_360e3_row18_col1" class="data row18 col1" >145</td>
            </tr>
            <tr>
                        <th id="T_360e3_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_360e3_row19_col0" class="data row19 col0" >775</td>
                        <td id="T_360e3_row19_col1" class="data row19 col1" >247</td>
            </tr>
    </tbody></table></div>

## Add data by columns

In the sample script below the WellLog data is ingested column per column. This is a typical action when we create new curves in a WellLog.
If the new columns added by chunks are sent in a session created with update mode then the new columns are appended to the list of columns present in the current version of the WellLog bulk data.
The columns posted in a session created with overwrite mode are only remaining in the latest version of the bulk data and the previous columns aren't preserved.  

```python
SESSION_MODE = 'update' # 'update' | 'overwrite'

# Create a session
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})

print_response(create_session_response)
session_id = create_session_response.json()['id']


# Send data for Y
generated_Y_dataframe = generate_df(['COLUMN_Y'], range(5, 25)) # variable has different indexes
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=generated_Y_dataframe.to_dict(orient='split')))

# Send data for Z
generated_Z_dataframe = generate_df(['COLUMN_Z'], range(10, 15)) # variable has different indexes
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=generated_Z_dataframe.to_dict(orient='split')))


# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'}))
```
    
The code below shows initial WellLog data before the session and chunks by columns inserted to the final WellLog data version after the session has been committed.

```python
# Display result
full_data_response = client.get(f'{welllog_dms_url}/{record_id}/data')
print_response(full_data_response)
with_new_col = create_df_from_response(full_data_response)

display_operation(results_cols_md_x, [generated_Y_dataframe, generated_Z_dataframe], with_new_col)
```

<div>
<style  type="text/css" >
#T_abcf1_row0_col0,#T_abcf1_row1_col0,#T_abcf1_row2_col0,#T_abcf1_row3_col0,#T_abcf1_row4_col0,#T_abcf1_row5_col0,#T_abcf1_row6_col0,#T_abcf1_row7_col0,#T_abcf1_row8_col0,#T_abcf1_row9_col0,#T_abcf1_row10_col0,#T_abcf1_row11_col0,#T_abcf1_row12_col0,#T_abcf1_row13_col0,#T_abcf1_row14_col0,#T_abcf1_row15_col0,#T_abcf1_row16_col0,#T_abcf1_row17_col0,#T_abcf1_row18_col0,#T_abcf1_row19_col0{
            color:  blue;
        }

#T_db462_row0_col0,#T_db462_row1_col0,#T_db462_row2_col0,#T_db462_row3_col0,#T_db462_row4_col0{
            color:  green;
        }
<style  type="text/css" >
#T_b48d9_row0_col2,#T_b48d9_row0_col3,#T_b48d9_row1_col2,#T_b48d9_row1_col3,#T_b48d9_row2_col2,#T_b48d9_row2_col3,#T_b48d9_row3_col2,#T_b48d9_row3_col3,#T_b48d9_row4_col2,#T_b48d9_row4_col3,#T_b48d9_row5_col3,#T_b48d9_row6_col3,#T_b48d9_row7_col3,#T_b48d9_row8_col3,#T_b48d9_row9_col3,#T_b48d9_row15_col3,#T_b48d9_row16_col3,#T_b48d9_row17_col3,#T_b48d9_row18_col3,#T_b48d9_row19_col3,#T_b48d9_row20_col0,#T_b48d9_row20_col1,#T_b48d9_row20_col3,#T_b48d9_row21_col0,#T_b48d9_row21_col1,#T_b48d9_row21_col3,#T_b48d9_row22_col0,#T_b48d9_row22_col1,#T_b48d9_row22_col3,#T_b48d9_row23_col0,#T_b48d9_row23_col1,#T_b48d9_row23_col3,#T_b48d9_row24_col0,#T_b48d9_row24_col1,#T_b48d9_row24_col3{
            background-color:  lightyellow;
        }
#T_b48d9_row5_col2,#T_b48d9_row6_col2,#T_b48d9_row7_col2,#T_b48d9_row8_col2,#T_b48d9_row9_col2,#T_b48d9_row10_col2,#T_b48d9_row11_col2,#T_b48d9_row12_col2,#T_b48d9_row13_col2,#T_b48d9_row14_col2,#T_b48d9_row15_col2,#T_b48d9_row16_col2,#T_b48d9_row17_col2,#T_b48d9_row18_col2,#T_b48d9_row19_col2,#T_b48d9_row20_col2,#T_b48d9_row21_col2,#T_b48d9_row22_col2,#T_b48d9_row23_col2,#T_b48d9_row24_col2{
            color:  blue;
        }
#T_b48d9_row10_col3,#T_b48d9_row11_col3,#T_b48d9_row12_col3,#T_b48d9_row13_col3,#T_b48d9_row14_col3{
            color:  green;
        }
</style>
<table id="T_8a02b_" style='display:inline'><caption>Initial data - Before session</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_8a02b_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_8a02b_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_8a02b_row0_col1" class="data row0 col1" >845</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_8a02b_row1_col0" class="data row1 col0" >92</td>
                        <td id="T_8a02b_row1_col1" class="data row1 col1" >246</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_8a02b_row2_col0" class="data row2 col0" >804</td>
                        <td id="T_8a02b_row2_col1" class="data row2 col1" >268</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_8a02b_row3_col0" class="data row3 col0" >645</td>
                        <td id="T_8a02b_row3_col1" class="data row3 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_8a02b_row4_col0" class="data row4 col0" >-20</td>
                        <td id="T_8a02b_row4_col1" class="data row4 col1" >-28</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_8a02b_row5_col0" class="data row5 col0" >-29</td>
                        <td id="T_8a02b_row5_col1" class="data row5 col1" >832</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_8a02b_row6_col0" class="data row6 col0" >-15</td>
                        <td id="T_8a02b_row6_col1" class="data row6 col1" >107</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_8a02b_row7_col0" class="data row7 col0" >339</td>
                        <td id="T_8a02b_row7_col1" class="data row7 col1" >212</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_8a02b_row8_col0" class="data row8 col0" >823</td>
                        <td id="T_8a02b_row8_col1" class="data row8 col1" >240</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_8a02b_row9_col0" class="data row9 col0" >-97</td>
                        <td id="T_8a02b_row9_col1" class="data row9 col1" >349</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_8a02b_row10_col0" class="data row10 col0" >183</td>
                        <td id="T_8a02b_row10_col1" class="data row10 col1" >89</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_8a02b_row11_col0" class="data row11 col0" >194</td>
                        <td id="T_8a02b_row11_col1" class="data row11 col1" >276</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_8a02b_row12_col0" class="data row12 col0" >-7</td>
                        <td id="T_8a02b_row12_col1" class="data row12 col1" >-7</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_8a02b_row13_col0" class="data row13 col0" >446</td>
                        <td id="T_8a02b_row13_col1" class="data row13 col1" >829</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_8a02b_row14_col0" class="data row14 col0" >32</td>
                        <td id="T_8a02b_row14_col1" class="data row14 col1" >706</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_8a02b_row15_col0" class="data row15 col0" >914</td>
                        <td id="T_8a02b_row15_col1" class="data row15 col1" >740</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_8a02b_row16_col0" class="data row16 col0" >593</td>
                        <td id="T_8a02b_row16_col1" class="data row16 col1" >279</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_8a02b_row17_col0" class="data row17 col0" >304</td>
                        <td id="T_8a02b_row17_col1" class="data row17 col1" >-57</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_8a02b_row18_col0" class="data row18 col0" >697</td>
                        <td id="T_8a02b_row18_col1" class="data row18 col1" >145</td>
            </tr>
            <tr>
                        <th id="T_8a02b_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_8a02b_row19_col0" class="data row19 col0" >775</td>
                        <td id="T_8a02b_row19_col1" class="data row19 col1" >247</td>
            </tr>
    </tbody></table>
	<table id="T_abcf1_" style='display:inline'><caption>chunk 1 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_Y</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_abcf1_level0_row0" class="row_heading level0 row0" >5</th>
                        <td id="T_abcf1_row0_col0" class="data row0 col0" >192</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row1" class="row_heading level0 row1" >6</th>
                        <td id="T_abcf1_row1_col0" class="data row1 col0" >816</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row2" class="row_heading level0 row2" >7</th>
                        <td id="T_abcf1_row2_col0" class="data row2 col0" >61</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row3" class="row_heading level0 row3" >8</th>
                        <td id="T_abcf1_row3_col0" class="data row3 col0" >658</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row4" class="row_heading level0 row4" >9</th>
                        <td id="T_abcf1_row4_col0" class="data row4 col0" >104</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row5" class="row_heading level0 row5" >10</th>
                        <td id="T_abcf1_row5_col0" class="data row5 col0" >704</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row6" class="row_heading level0 row6" >11</th>
                        <td id="T_abcf1_row6_col0" class="data row6 col0" >681</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row7" class="row_heading level0 row7" >12</th>
                        <td id="T_abcf1_row7_col0" class="data row7 col0" >393</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row8" class="row_heading level0 row8" >13</th>
                        <td id="T_abcf1_row8_col0" class="data row8 col0" >329</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row9" class="row_heading level0 row9" >14</th>
                        <td id="T_abcf1_row9_col0" class="data row9 col0" >402</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row10" class="row_heading level0 row10" >15</th>
                        <td id="T_abcf1_row10_col0" class="data row10 col0" >418</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row11" class="row_heading level0 row11" >16</th>
                        <td id="T_abcf1_row11_col0" class="data row11 col0" >-9</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row12" class="row_heading level0 row12" >17</th>
                        <td id="T_abcf1_row12_col0" class="data row12 col0" >857</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row13" class="row_heading level0 row13" >18</th>
                        <td id="T_abcf1_row13_col0" class="data row13 col0" >845</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row14" class="row_heading level0 row14" >19</th>
                        <td id="T_abcf1_row14_col0" class="data row14 col0" >78</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row15" class="row_heading level0 row15" >20</th>
                        <td id="T_abcf1_row15_col0" class="data row15 col0" >484</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row16" class="row_heading level0 row16" >21</th>
                        <td id="T_abcf1_row16_col0" class="data row16 col0" >384</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row17" class="row_heading level0 row17" >22</th>
                        <td id="T_abcf1_row17_col0" class="data row17 col0" >658</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row18" class="row_heading level0 row18" >23</th>
                        <td id="T_abcf1_row18_col0" class="data row18 col0" >622</td>
            </tr>
            <tr>
                        <th id="T_abcf1_level0_row19" class="row_heading level0 row19" >24</th>
                        <td id="T_abcf1_row19_col0" class="data row19 col0" >459</td>
            </tr>
    </tbody></table>
	<table id="T_db462_" style='display:inline'><caption>chunk 2 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_db462_level0_row0" class="row_heading level0 row0" >10</th>
                        <td id="T_db462_row0_col0" class="data row0 col0" >141</td>
            </tr>
            <tr>
                        <th id="T_db462_level0_row1" class="row_heading level0 row1" >11</th>
                        <td id="T_db462_row1_col0" class="data row1 col0" >478</td>
            </tr>
            <tr>
                        <th id="T_db462_level0_row2" class="row_heading level0 row2" >12</th>
                        <td id="T_db462_row2_col0" class="data row2 col0" >72</td>
            </tr>
            <tr>
                        <th id="T_db462_level0_row3" class="row_heading level0 row3" >13</th>
                        <td id="T_db462_row3_col0" class="data row3 col0" >476</td>
            </tr>
            <tr>
                        <th id="T_db462_level0_row4" class="row_heading level0 row4" >14</th>
                        <td id="T_db462_row4_col0" class="data row4 col0" >434</td>
            </tr>
    </tbody></table>
	<table id="T_b48d9_" style='display:inline'><caption>Final data - After session commit</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_b48d9_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_b48d9_row0_col0" class="data row0 col0" >265.000000</td>
                        <td id="T_b48d9_row0_col1" class="data row0 col1" >845.000000</td>
                        <td id="T_b48d9_row0_col2" class="data row0 col2" >nan</td>
                        <td id="T_b48d9_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_b48d9_row1_col0" class="data row1 col0" >92.000000</td>
                        <td id="T_b48d9_row1_col1" class="data row1 col1" >246.000000</td>
                        <td id="T_b48d9_row1_col2" class="data row1 col2" >nan</td>
                        <td id="T_b48d9_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_b48d9_row2_col0" class="data row2 col0" >804.000000</td>
                        <td id="T_b48d9_row2_col1" class="data row2 col1" >268.000000</td>
                        <td id="T_b48d9_row2_col2" class="data row2 col2" >nan</td>
                        <td id="T_b48d9_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_b48d9_row3_col0" class="data row3 col0" >645.000000</td>
                        <td id="T_b48d9_row3_col1" class="data row3 col1" >877.000000</td>
                        <td id="T_b48d9_row3_col2" class="data row3 col2" >nan</td>
                        <td id="T_b48d9_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_b48d9_row4_col0" class="data row4 col0" >-20.000000</td>
                        <td id="T_b48d9_row4_col1" class="data row4 col1" >-28.000000</td>
                        <td id="T_b48d9_row4_col2" class="data row4 col2" >nan</td>
                        <td id="T_b48d9_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_b48d9_row5_col0" class="data row5 col0" >-29.000000</td>
                        <td id="T_b48d9_row5_col1" class="data row5 col1" >832.000000</td>
                        <td id="T_b48d9_row5_col2" class="data row5 col2" >192.000000</td>
                        <td id="T_b48d9_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_b48d9_row6_col0" class="data row6 col0" >-15.000000</td>
                        <td id="T_b48d9_row6_col1" class="data row6 col1" >107.000000</td>
                        <td id="T_b48d9_row6_col2" class="data row6 col2" >816.000000</td>
                        <td id="T_b48d9_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_b48d9_row7_col0" class="data row7 col0" >339.000000</td>
                        <td id="T_b48d9_row7_col1" class="data row7 col1" >212.000000</td>
                        <td id="T_b48d9_row7_col2" class="data row7 col2" >61.000000</td>
                        <td id="T_b48d9_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_b48d9_row8_col0" class="data row8 col0" >823.000000</td>
                        <td id="T_b48d9_row8_col1" class="data row8 col1" >240.000000</td>
                        <td id="T_b48d9_row8_col2" class="data row8 col2" >658.000000</td>
                        <td id="T_b48d9_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_b48d9_row9_col0" class="data row9 col0" >-97.000000</td>
                        <td id="T_b48d9_row9_col1" class="data row9 col1" >349.000000</td>
                        <td id="T_b48d9_row9_col2" class="data row9 col2" >104.000000</td>
                        <td id="T_b48d9_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_b48d9_row10_col0" class="data row10 col0" >183.000000</td>
                        <td id="T_b48d9_row10_col1" class="data row10 col1" >89.000000</td>
                        <td id="T_b48d9_row10_col2" class="data row10 col2" >704.000000</td>
                        <td id="T_b48d9_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_b48d9_row11_col0" class="data row11 col0" >194.000000</td>
                        <td id="T_b48d9_row11_col1" class="data row11 col1" >276.000000</td>
                        <td id="T_b48d9_row11_col2" class="data row11 col2" >681.000000</td>
                        <td id="T_b48d9_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_b48d9_row12_col0" class="data row12 col0" >-7.000000</td>
                        <td id="T_b48d9_row12_col1" class="data row12 col1" >-7.000000</td>
                        <td id="T_b48d9_row12_col2" class="data row12 col2" >393.000000</td>
                        <td id="T_b48d9_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_b48d9_row13_col0" class="data row13 col0" >446.000000</td>
                        <td id="T_b48d9_row13_col1" class="data row13 col1" >829.000000</td>
                        <td id="T_b48d9_row13_col2" class="data row13 col2" >329.000000</td>
                        <td id="T_b48d9_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_b48d9_row14_col0" class="data row14 col0" >32.000000</td>
                        <td id="T_b48d9_row14_col1" class="data row14 col1" >706.000000</td>
                        <td id="T_b48d9_row14_col2" class="data row14 col2" >402.000000</td>
                        <td id="T_b48d9_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_b48d9_row15_col0" class="data row15 col0" >914.000000</td>
                        <td id="T_b48d9_row15_col1" class="data row15 col1" >740.000000</td>
                        <td id="T_b48d9_row15_col2" class="data row15 col2" >418.000000</td>
                        <td id="T_b48d9_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_b48d9_row16_col0" class="data row16 col0" >593.000000</td>
                        <td id="T_b48d9_row16_col1" class="data row16 col1" >279.000000</td>
                        <td id="T_b48d9_row16_col2" class="data row16 col2" >-9.000000</td>
                        <td id="T_b48d9_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_b48d9_row17_col0" class="data row17 col0" >304.000000</td>
                        <td id="T_b48d9_row17_col1" class="data row17 col1" >-57.000000</td>
                        <td id="T_b48d9_row17_col2" class="data row17 col2" >857.000000</td>
                        <td id="T_b48d9_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_b48d9_row18_col0" class="data row18 col0" >697.000000</td>
                        <td id="T_b48d9_row18_col1" class="data row18 col1" >145.000000</td>
                        <td id="T_b48d9_row18_col2" class="data row18 col2" >845.000000</td>
                        <td id="T_b48d9_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_b48d9_row19_col0" class="data row19 col0" >775.000000</td>
                        <td id="T_b48d9_row19_col1" class="data row19 col1" >247.000000</td>
                        <td id="T_b48d9_row19_col2" class="data row19 col2" >78.000000</td>
                        <td id="T_b48d9_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_b48d9_row20_col0" class="data row20 col0" >nan</td>
                        <td id="T_b48d9_row20_col1" class="data row20 col1" >nan</td>
                        <td id="T_b48d9_row20_col2" class="data row20 col2" >484.000000</td>
                        <td id="T_b48d9_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_b48d9_row21_col0" class="data row21 col0" >nan</td>
                        <td id="T_b48d9_row21_col1" class="data row21 col1" >nan</td>
                        <td id="T_b48d9_row21_col2" class="data row21 col2" >384.000000</td>
                        <td id="T_b48d9_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_b48d9_row22_col0" class="data row22 col0" >nan</td>
                        <td id="T_b48d9_row22_col1" class="data row22 col1" >nan</td>
                        <td id="T_b48d9_row22_col2" class="data row22 col2" >658.000000</td>
                        <td id="T_b48d9_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_b48d9_row23_col0" class="data row23 col0" >nan</td>
                        <td id="T_b48d9_row23_col1" class="data row23 col1" >nan</td>
                        <td id="T_b48d9_row23_col2" class="data row23 col2" >622.000000</td>
                        <td id="T_b48d9_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b48d9_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_b48d9_row24_col0" class="data row24 col0" >nan</td>
                        <td id="T_b48d9_row24_col1" class="data row24 col1" >nan</td>
                        <td id="T_b48d9_row24_col2" class="data row24 col2" >459.000000</td>
                        <td id="T_b48d9_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table></div>


The function below shows the differences between the current WellLog data version with new columns added by chunk and the previous version of the WellLog data.

```python
display_previous_and_current_well_log_data_versions(record_id)
```

<div>
<style  type="text/css" >
#T_af85c_row0_col0,#T_af85c_row0_col1,#T_af85c_row1_col0,#T_af85c_row1_col1,#T_af85c_row2_col0,#T_af85c_row2_col1,#T_af85c_row3_col0,#T_af85c_row3_col1,#T_af85c_row4_col0,#T_af85c_row4_col1,#T_af85c_row5_col0,#T_af85c_row5_col1,#T_af85c_row6_col0,#T_af85c_row6_col1,#T_af85c_row7_col0,#T_af85c_row7_col1,#T_af85c_row8_col0,#T_af85c_row8_col1,#T_af85c_row9_col0,#T_af85c_row9_col1,#T_af85c_row10_col0,#T_af85c_row10_col1,#T_af85c_row11_col0,#T_af85c_row11_col1,#T_af85c_row12_col0,#T_af85c_row12_col1,#T_af85c_row13_col0,#T_af85c_row13_col1,#T_af85c_row14_col0,#T_af85c_row14_col1,#T_af85c_row15_col0,#T_af85c_row15_col1,#T_af85c_row16_col0,#T_af85c_row16_col1,#T_af85c_row17_col0,#T_af85c_row17_col1,#T_af85c_row18_col0,#T_af85c_row18_col1,#T_af85c_row19_col0,#T_af85c_row19_col1{
            color:  blue;
        }

#T_7a4c1_row0_col0,#T_7a4c1_row0_col1,#T_7a4c1_row1_col0,#T_7a4c1_row1_col1,#T_7a4c1_row2_col0,#T_7a4c1_row2_col1,#T_7a4c1_row3_col0,#T_7a4c1_row3_col1,#T_7a4c1_row4_col0,#T_7a4c1_row4_col1,#T_7a4c1_row5_col0,#T_7a4c1_row5_col1,#T_7a4c1_row6_col0,#T_7a4c1_row6_col1,#T_7a4c1_row7_col0,#T_7a4c1_row7_col1,#T_7a4c1_row8_col0,#T_7a4c1_row8_col1,#T_7a4c1_row9_col0,#T_7a4c1_row9_col1,#T_7a4c1_row10_col0,#T_7a4c1_row10_col1,#T_7a4c1_row11_col0,#T_7a4c1_row11_col1,#T_7a4c1_row12_col0,#T_7a4c1_row12_col1,#T_7a4c1_row13_col0,#T_7a4c1_row13_col1,#T_7a4c1_row14_col0,#T_7a4c1_row14_col1,#T_7a4c1_row15_col0,#T_7a4c1_row15_col1,#T_7a4c1_row16_col0,#T_7a4c1_row16_col1,#T_7a4c1_row17_col0,#T_7a4c1_row17_col1,#T_7a4c1_row18_col0,#T_7a4c1_row18_col1,#T_7a4c1_row19_col0,#T_7a4c1_row19_col1{
            color:  blue;
        }
#T_7a4c1_row0_col2,#T_7a4c1_row0_col3,#T_7a4c1_row1_col2,#T_7a4c1_row1_col3,#T_7a4c1_row2_col2,#T_7a4c1_row2_col3,#T_7a4c1_row3_col2,#T_7a4c1_row3_col3,#T_7a4c1_row4_col2,#T_7a4c1_row4_col3,#T_7a4c1_row5_col3,#T_7a4c1_row6_col3,#T_7a4c1_row7_col3,#T_7a4c1_row8_col3,#T_7a4c1_row9_col3,#T_7a4c1_row15_col3,#T_7a4c1_row16_col3,#T_7a4c1_row17_col3,#T_7a4c1_row18_col3,#T_7a4c1_row19_col3,#T_7a4c1_row20_col0,#T_7a4c1_row20_col1,#T_7a4c1_row20_col3,#T_7a4c1_row21_col0,#T_7a4c1_row21_col1,#T_7a4c1_row21_col3,#T_7a4c1_row22_col0,#T_7a4c1_row22_col1,#T_7a4c1_row22_col3,#T_7a4c1_row23_col0,#T_7a4c1_row23_col1,#T_7a4c1_row23_col3,#T_7a4c1_row24_col0,#T_7a4c1_row24_col1,#T_7a4c1_row24_col3{
            color:  red;
            background-color:  lightyellow;
        }
#T_7a4c1_row5_col2,#T_7a4c1_row6_col2,#T_7a4c1_row7_col2,#T_7a4c1_row8_col2,#T_7a4c1_row9_col2,#T_7a4c1_row10_col2,#T_7a4c1_row10_col3,#T_7a4c1_row11_col2,#T_7a4c1_row11_col3,#T_7a4c1_row12_col2,#T_7a4c1_row12_col3,#T_7a4c1_row13_col2,#T_7a4c1_row13_col3,#T_7a4c1_row14_col2,#T_7a4c1_row14_col3,#T_7a4c1_row15_col2,#T_7a4c1_row16_col2,#T_7a4c1_row17_col2,#T_7a4c1_row18_col2,#T_7a4c1_row19_col2,#T_7a4c1_row20_col2,#T_7a4c1_row21_col2,#T_7a4c1_row22_col2,#T_7a4c1_row23_col2,#T_7a4c1_row24_col2{
            color:  red;
        }
</style>
<table id="T_af85c_" style='display:inline'><caption>Previous WellLog data version</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_af85c_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_af85c_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_af85c_row0_col1" class="data row0 col1" >845</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_af85c_row1_col0" class="data row1 col0" >92</td>
                        <td id="T_af85c_row1_col1" class="data row1 col1" >246</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_af85c_row2_col0" class="data row2 col0" >804</td>
                        <td id="T_af85c_row2_col1" class="data row2 col1" >268</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_af85c_row3_col0" class="data row3 col0" >645</td>
                        <td id="T_af85c_row3_col1" class="data row3 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_af85c_row4_col0" class="data row4 col0" >-20</td>
                        <td id="T_af85c_row4_col1" class="data row4 col1" >-28</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_af85c_row5_col0" class="data row5 col0" >-29</td>
                        <td id="T_af85c_row5_col1" class="data row5 col1" >832</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_af85c_row6_col0" class="data row6 col0" >-15</td>
                        <td id="T_af85c_row6_col1" class="data row6 col1" >107</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_af85c_row7_col0" class="data row7 col0" >339</td>
                        <td id="T_af85c_row7_col1" class="data row7 col1" >212</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_af85c_row8_col0" class="data row8 col0" >823</td>
                        <td id="T_af85c_row8_col1" class="data row8 col1" >240</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_af85c_row9_col0" class="data row9 col0" >-97</td>
                        <td id="T_af85c_row9_col1" class="data row9 col1" >349</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_af85c_row10_col0" class="data row10 col0" >183</td>
                        <td id="T_af85c_row10_col1" class="data row10 col1" >89</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_af85c_row11_col0" class="data row11 col0" >194</td>
                        <td id="T_af85c_row11_col1" class="data row11 col1" >276</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_af85c_row12_col0" class="data row12 col0" >-7</td>
                        <td id="T_af85c_row12_col1" class="data row12 col1" >-7</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_af85c_row13_col0" class="data row13 col0" >446</td>
                        <td id="T_af85c_row13_col1" class="data row13 col1" >829</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_af85c_row14_col0" class="data row14 col0" >32</td>
                        <td id="T_af85c_row14_col1" class="data row14 col1" >706</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_af85c_row15_col0" class="data row15 col0" >914</td>
                        <td id="T_af85c_row15_col1" class="data row15 col1" >740</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_af85c_row16_col0" class="data row16 col0" >593</td>
                        <td id="T_af85c_row16_col1" class="data row16 col1" >279</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_af85c_row17_col0" class="data row17 col0" >304</td>
                        <td id="T_af85c_row17_col1" class="data row17 col1" >-57</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_af85c_row18_col0" class="data row18 col0" >697</td>
                        <td id="T_af85c_row18_col1" class="data row18 col1" >145</td>
            </tr>
            <tr>
                        <th id="T_af85c_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_af85c_row19_col0" class="data row19 col0" >775</td>
                        <td id="T_af85c_row19_col1" class="data row19 col1" >247</td>
            </tr>
    </tbody></table>
	<table id="T_7a4c1_" style='display:inline'><caption>Current WellLog data version with data chunks added in red</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_7a4c1_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_7a4c1_row0_col0" class="data row0 col0" >265.000000</td>
                        <td id="T_7a4c1_row0_col1" class="data row0 col1" >845.000000</td>
                        <td id="T_7a4c1_row0_col2" class="data row0 col2" >nan</td>
                        <td id="T_7a4c1_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_7a4c1_row1_col0" class="data row1 col0" >92.000000</td>
                        <td id="T_7a4c1_row1_col1" class="data row1 col1" >246.000000</td>
                        <td id="T_7a4c1_row1_col2" class="data row1 col2" >nan</td>
                        <td id="T_7a4c1_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_7a4c1_row2_col0" class="data row2 col0" >804.000000</td>
                        <td id="T_7a4c1_row2_col1" class="data row2 col1" >268.000000</td>
                        <td id="T_7a4c1_row2_col2" class="data row2 col2" >nan</td>
                        <td id="T_7a4c1_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_7a4c1_row3_col0" class="data row3 col0" >645.000000</td>
                        <td id="T_7a4c1_row3_col1" class="data row3 col1" >877.000000</td>
                        <td id="T_7a4c1_row3_col2" class="data row3 col2" >nan</td>
                        <td id="T_7a4c1_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_7a4c1_row4_col0" class="data row4 col0" >-20.000000</td>
                        <td id="T_7a4c1_row4_col1" class="data row4 col1" >-28.000000</td>
                        <td id="T_7a4c1_row4_col2" class="data row4 col2" >nan</td>
                        <td id="T_7a4c1_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_7a4c1_row5_col0" class="data row5 col0" >-29.000000</td>
                        <td id="T_7a4c1_row5_col1" class="data row5 col1" >832.000000</td>
                        <td id="T_7a4c1_row5_col2" class="data row5 col2" >192.000000</td>
                        <td id="T_7a4c1_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_7a4c1_row6_col0" class="data row6 col0" >-15.000000</td>
                        <td id="T_7a4c1_row6_col1" class="data row6 col1" >107.000000</td>
                        <td id="T_7a4c1_row6_col2" class="data row6 col2" >816.000000</td>
                        <td id="T_7a4c1_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_7a4c1_row7_col0" class="data row7 col0" >339.000000</td>
                        <td id="T_7a4c1_row7_col1" class="data row7 col1" >212.000000</td>
                        <td id="T_7a4c1_row7_col2" class="data row7 col2" >61.000000</td>
                        <td id="T_7a4c1_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_7a4c1_row8_col0" class="data row8 col0" >823.000000</td>
                        <td id="T_7a4c1_row8_col1" class="data row8 col1" >240.000000</td>
                        <td id="T_7a4c1_row8_col2" class="data row8 col2" >658.000000</td>
                        <td id="T_7a4c1_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_7a4c1_row9_col0" class="data row9 col0" >-97.000000</td>
                        <td id="T_7a4c1_row9_col1" class="data row9 col1" >349.000000</td>
                        <td id="T_7a4c1_row9_col2" class="data row9 col2" >104.000000</td>
                        <td id="T_7a4c1_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_7a4c1_row10_col0" class="data row10 col0" >183.000000</td>
                        <td id="T_7a4c1_row10_col1" class="data row10 col1" >89.000000</td>
                        <td id="T_7a4c1_row10_col2" class="data row10 col2" >704.000000</td>
                        <td id="T_7a4c1_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_7a4c1_row11_col0" class="data row11 col0" >194.000000</td>
                        <td id="T_7a4c1_row11_col1" class="data row11 col1" >276.000000</td>
                        <td id="T_7a4c1_row11_col2" class="data row11 col2" >681.000000</td>
                        <td id="T_7a4c1_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_7a4c1_row12_col0" class="data row12 col0" >-7.000000</td>
                        <td id="T_7a4c1_row12_col1" class="data row12 col1" >-7.000000</td>
                        <td id="T_7a4c1_row12_col2" class="data row12 col2" >393.000000</td>
                        <td id="T_7a4c1_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_7a4c1_row13_col0" class="data row13 col0" >446.000000</td>
                        <td id="T_7a4c1_row13_col1" class="data row13 col1" >829.000000</td>
                        <td id="T_7a4c1_row13_col2" class="data row13 col2" >329.000000</td>
                        <td id="T_7a4c1_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_7a4c1_row14_col0" class="data row14 col0" >32.000000</td>
                        <td id="T_7a4c1_row14_col1" class="data row14 col1" >706.000000</td>
                        <td id="T_7a4c1_row14_col2" class="data row14 col2" >402.000000</td>
                        <td id="T_7a4c1_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_7a4c1_row15_col0" class="data row15 col0" >914.000000</td>
                        <td id="T_7a4c1_row15_col1" class="data row15 col1" >740.000000</td>
                        <td id="T_7a4c1_row15_col2" class="data row15 col2" >418.000000</td>
                        <td id="T_7a4c1_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_7a4c1_row16_col0" class="data row16 col0" >593.000000</td>
                        <td id="T_7a4c1_row16_col1" class="data row16 col1" >279.000000</td>
                        <td id="T_7a4c1_row16_col2" class="data row16 col2" >-9.000000</td>
                        <td id="T_7a4c1_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_7a4c1_row17_col0" class="data row17 col0" >304.000000</td>
                        <td id="T_7a4c1_row17_col1" class="data row17 col1" >-57.000000</td>
                        <td id="T_7a4c1_row17_col2" class="data row17 col2" >857.000000</td>
                        <td id="T_7a4c1_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_7a4c1_row18_col0" class="data row18 col0" >697.000000</td>
                        <td id="T_7a4c1_row18_col1" class="data row18 col1" >145.000000</td>
                        <td id="T_7a4c1_row18_col2" class="data row18 col2" >845.000000</td>
                        <td id="T_7a4c1_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_7a4c1_row19_col0" class="data row19 col0" >775.000000</td>
                        <td id="T_7a4c1_row19_col1" class="data row19 col1" >247.000000</td>
                        <td id="T_7a4c1_row19_col2" class="data row19 col2" >78.000000</td>
                        <td id="T_7a4c1_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_7a4c1_row20_col0" class="data row20 col0" >nan</td>
                        <td id="T_7a4c1_row20_col1" class="data row20 col1" >nan</td>
                        <td id="T_7a4c1_row20_col2" class="data row20 col2" >484.000000</td>
                        <td id="T_7a4c1_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_7a4c1_row21_col0" class="data row21 col0" >nan</td>
                        <td id="T_7a4c1_row21_col1" class="data row21 col1" >nan</td>
                        <td id="T_7a4c1_row21_col2" class="data row21 col2" >384.000000</td>
                        <td id="T_7a4c1_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_7a4c1_row22_col0" class="data row22 col0" >nan</td>
                        <td id="T_7a4c1_row22_col1" class="data row22 col1" >nan</td>
                        <td id="T_7a4c1_row22_col2" class="data row22 col2" >658.000000</td>
                        <td id="T_7a4c1_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_7a4c1_row23_col0" class="data row23 col0" >nan</td>
                        <td id="T_7a4c1_row23_col1" class="data row23 col1" >nan</td>
                        <td id="T_7a4c1_row23_col2" class="data row23 col2" >622.000000</td>
                        <td id="T_7a4c1_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_7a4c1_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_7a4c1_row24_col0" class="data row24 col0" >nan</td>
                        <td id="T_7a4c1_row24_col1" class="data row24 col1" >nan</td>
                        <td id="T_7a4c1_row24_col2" class="data row24 col2" >459.000000</td>
                        <td id="T_7a4c1_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table></div>

## Add data by columns and by rows

The chunking by columns and rows can be mixed in a same session. This is what the script below is showing:

```python
SESSION_MODE = 'update' # 'update' | 'overwrite'

# Create a session
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})
print_response(create_session_response)
session_id = create_session_response.json()['id']


chunk_md_x_1 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(10))
response_chunk_1 = client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_md_x_1.to_dict(orient='split'))
print_response(response_chunk_1)

chunk_md_x_2 = generate_df(['COLUMN_MD', 'COLUMN_X'], range(10, 25))
response_chunk_2 = client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_md_x_2.to_dict(orient='split'))
print_response(response_chunk_2)

chunk_y_1 = generate_df(['COLUMN_Y'], range(15))
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_y_1.to_dict(orient='split')))

chunk_y_2 = generate_df(['COLUMN_Y'], range(15, 25))
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=chunk_y_2.to_dict(orient='split')))


# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'}))
```
  
The code below shows initial WellLog data before the session and chunks by columns and rows inserted to the final WellLog data version after the session has been committed.

```python
# Display result
rows_and_cols_response = client.get(f'{welllog_dms_url}/{record_id}/data')
print_response(rows_and_cols_response)
rows_and_cols_response_final = create_df_from_response(rows_and_cols_response)

display_operation(with_new_col, [chunk_md_x_1, chunk_md_x_2, chunk_y_1, chunk_y_2], rows_and_cols_response_final)
```

<div>
<style  type="text/css" >
#T_eab10_row0_col0,#T_eab10_row0_col1,#T_eab10_row1_col0,#T_eab10_row1_col1,#T_eab10_row2_col0,#T_eab10_row2_col1,#T_eab10_row3_col0,#T_eab10_row3_col1,#T_eab10_row4_col0,#T_eab10_row4_col1,#T_eab10_row5_col0,#T_eab10_row5_col1,#T_eab10_row6_col0,#T_eab10_row6_col1,#T_eab10_row7_col0,#T_eab10_row7_col1,#T_eab10_row8_col0,#T_eab10_row8_col1,#T_eab10_row9_col0,#T_eab10_row9_col1{
            color:  blue;
        }
#T_7a927_row0_col0,#T_7a927_row0_col1,#T_7a927_row1_col0,#T_7a927_row1_col1,#T_7a927_row2_col0,#T_7a927_row2_col1,#T_7a927_row3_col0,#T_7a927_row3_col1,#T_7a927_row4_col0,#T_7a927_row4_col1,#T_7a927_row5_col0,#T_7a927_row5_col1,#T_7a927_row6_col0,#T_7a927_row6_col1,#T_7a927_row7_col0,#T_7a927_row7_col1,#T_7a927_row8_col0,#T_7a927_row8_col1,#T_7a927_row9_col0,#T_7a927_row9_col1,#T_7a927_row10_col0,#T_7a927_row10_col1,#T_7a927_row11_col0,#T_7a927_row11_col1,#T_7a927_row12_col0,#T_7a927_row12_col1,#T_7a927_row13_col0,#T_7a927_row13_col1,#T_7a927_row14_col0,#T_7a927_row14_col1{
            color:  green;
        }
#T_5f34c_row0_col0,#T_5f34c_row1_col0,#T_5f34c_row2_col0,#T_5f34c_row3_col0,#T_5f34c_row4_col0,#T_5f34c_row5_col0,#T_5f34c_row6_col0,#T_5f34c_row7_col0,#T_5f34c_row8_col0,#T_5f34c_row9_col0,#T_5f34c_row10_col0,#T_5f34c_row11_col0,#T_5f34c_row12_col0,#T_5f34c_row13_col0,#T_5f34c_row14_col0{
            color:  orange;
        }

#T_15f6a_row0_col0,#T_15f6a_row0_col1,#T_15f6a_row1_col0,#T_15f6a_row1_col1,#T_15f6a_row2_col0,#T_15f6a_row2_col1,#T_15f6a_row3_col0,#T_15f6a_row3_col1,#T_15f6a_row4_col0,#T_15f6a_row4_col1,#T_15f6a_row5_col0,#T_15f6a_row5_col1,#T_15f6a_row6_col0,#T_15f6a_row6_col1,#T_15f6a_row7_col0,#T_15f6a_row7_col1,#T_15f6a_row8_col0,#T_15f6a_row8_col1,#T_15f6a_row9_col0,#T_15f6a_row9_col1{
            color:  blue;
        }
#T_15f6a_row0_col2,#T_15f6a_row1_col2,#T_15f6a_row2_col2,#T_15f6a_row3_col2,#T_15f6a_row4_col2,#T_15f6a_row5_col2,#T_15f6a_row6_col2,#T_15f6a_row7_col2,#T_15f6a_row8_col2,#T_15f6a_row9_col2,#T_15f6a_row10_col2,#T_15f6a_row11_col2,#T_15f6a_row12_col2,#T_15f6a_row13_col2,#T_15f6a_row14_col2{
            color:  orange;
        }
#T_15f6a_row0_col3,#T_15f6a_row1_col3,#T_15f6a_row2_col3,#T_15f6a_row3_col3,#T_15f6a_row4_col3,#T_15f6a_row5_col3,#T_15f6a_row6_col3,#T_15f6a_row7_col3,#T_15f6a_row8_col3,#T_15f6a_row9_col3,#T_15f6a_row15_col3,#T_15f6a_row16_col3,#T_15f6a_row17_col3,#T_15f6a_row18_col3,#T_15f6a_row19_col3,#T_15f6a_row20_col3,#T_15f6a_row21_col3,#T_15f6a_row22_col3,#T_15f6a_row23_col3,#T_15f6a_row24_col3{
            background-color:  lightyellow;
        }
#T_15f6a_row10_col0,#T_15f6a_row10_col1,#T_15f6a_row11_col0,#T_15f6a_row11_col1,#T_15f6a_row12_col0,#T_15f6a_row12_col1,#T_15f6a_row13_col0,#T_15f6a_row13_col1,#T_15f6a_row14_col0,#T_15f6a_row14_col1,#T_15f6a_row15_col0,#T_15f6a_row15_col1,#T_15f6a_row16_col0,#T_15f6a_row16_col1,#T_15f6a_row17_col0,#T_15f6a_row17_col1,#T_15f6a_row18_col0,#T_15f6a_row18_col1,#T_15f6a_row19_col0,#T_15f6a_row19_col1,#T_15f6a_row20_col0,#T_15f6a_row20_col1,#T_15f6a_row21_col0,#T_15f6a_row21_col1,#T_15f6a_row22_col0,#T_15f6a_row22_col1,#T_15f6a_row23_col0,#T_15f6a_row23_col1,#T_15f6a_row24_col0,#T_15f6a_row24_col1{
            color:  green;
        }
#T_15f6a_row15_col2,#T_15f6a_row16_col2,#T_15f6a_row17_col2,#T_15f6a_row18_col2,#T_15f6a_row19_col2,#T_15f6a_row20_col2,#T_15f6a_row21_col2,#T_15f6a_row22_col2,#T_15f6a_row23_col2,#T_15f6a_row24_col2{
            color:  red;
        }
</style>
<table id="T_0dc1e_" style='display:inline'><caption>Initial data - Before session</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_0dc1e_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_0dc1e_row0_col0" class="data row0 col0" >265.000000</td>
                        <td id="T_0dc1e_row0_col1" class="data row0 col1" >845.000000</td>
                        <td id="T_0dc1e_row0_col2" class="data row0 col2" >nan</td>
                        <td id="T_0dc1e_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_0dc1e_row1_col0" class="data row1 col0" >92.000000</td>
                        <td id="T_0dc1e_row1_col1" class="data row1 col1" >246.000000</td>
                        <td id="T_0dc1e_row1_col2" class="data row1 col2" >nan</td>
                        <td id="T_0dc1e_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_0dc1e_row2_col0" class="data row2 col0" >804.000000</td>
                        <td id="T_0dc1e_row2_col1" class="data row2 col1" >268.000000</td>
                        <td id="T_0dc1e_row2_col2" class="data row2 col2" >nan</td>
                        <td id="T_0dc1e_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_0dc1e_row3_col0" class="data row3 col0" >645.000000</td>
                        <td id="T_0dc1e_row3_col1" class="data row3 col1" >877.000000</td>
                        <td id="T_0dc1e_row3_col2" class="data row3 col2" >nan</td>
                        <td id="T_0dc1e_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_0dc1e_row4_col0" class="data row4 col0" >-20.000000</td>
                        <td id="T_0dc1e_row4_col1" class="data row4 col1" >-28.000000</td>
                        <td id="T_0dc1e_row4_col2" class="data row4 col2" >nan</td>
                        <td id="T_0dc1e_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_0dc1e_row5_col0" class="data row5 col0" >-29.000000</td>
                        <td id="T_0dc1e_row5_col1" class="data row5 col1" >832.000000</td>
                        <td id="T_0dc1e_row5_col2" class="data row5 col2" >192.000000</td>
                        <td id="T_0dc1e_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_0dc1e_row6_col0" class="data row6 col0" >-15.000000</td>
                        <td id="T_0dc1e_row6_col1" class="data row6 col1" >107.000000</td>
                        <td id="T_0dc1e_row6_col2" class="data row6 col2" >816.000000</td>
                        <td id="T_0dc1e_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_0dc1e_row7_col0" class="data row7 col0" >339.000000</td>
                        <td id="T_0dc1e_row7_col1" class="data row7 col1" >212.000000</td>
                        <td id="T_0dc1e_row7_col2" class="data row7 col2" >61.000000</td>
                        <td id="T_0dc1e_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_0dc1e_row8_col0" class="data row8 col0" >823.000000</td>
                        <td id="T_0dc1e_row8_col1" class="data row8 col1" >240.000000</td>
                        <td id="T_0dc1e_row8_col2" class="data row8 col2" >658.000000</td>
                        <td id="T_0dc1e_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_0dc1e_row9_col0" class="data row9 col0" >-97.000000</td>
                        <td id="T_0dc1e_row9_col1" class="data row9 col1" >349.000000</td>
                        <td id="T_0dc1e_row9_col2" class="data row9 col2" >104.000000</td>
                        <td id="T_0dc1e_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_0dc1e_row10_col0" class="data row10 col0" >183.000000</td>
                        <td id="T_0dc1e_row10_col1" class="data row10 col1" >89.000000</td>
                        <td id="T_0dc1e_row10_col2" class="data row10 col2" >704.000000</td>
                        <td id="T_0dc1e_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_0dc1e_row11_col0" class="data row11 col0" >194.000000</td>
                        <td id="T_0dc1e_row11_col1" class="data row11 col1" >276.000000</td>
                        <td id="T_0dc1e_row11_col2" class="data row11 col2" >681.000000</td>
                        <td id="T_0dc1e_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_0dc1e_row12_col0" class="data row12 col0" >-7.000000</td>
                        <td id="T_0dc1e_row12_col1" class="data row12 col1" >-7.000000</td>
                        <td id="T_0dc1e_row12_col2" class="data row12 col2" >393.000000</td>
                        <td id="T_0dc1e_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_0dc1e_row13_col0" class="data row13 col0" >446.000000</td>
                        <td id="T_0dc1e_row13_col1" class="data row13 col1" >829.000000</td>
                        <td id="T_0dc1e_row13_col2" class="data row13 col2" >329.000000</td>
                        <td id="T_0dc1e_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_0dc1e_row14_col0" class="data row14 col0" >32.000000</td>
                        <td id="T_0dc1e_row14_col1" class="data row14 col1" >706.000000</td>
                        <td id="T_0dc1e_row14_col2" class="data row14 col2" >402.000000</td>
                        <td id="T_0dc1e_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_0dc1e_row15_col0" class="data row15 col0" >914.000000</td>
                        <td id="T_0dc1e_row15_col1" class="data row15 col1" >740.000000</td>
                        <td id="T_0dc1e_row15_col2" class="data row15 col2" >418.000000</td>
                        <td id="T_0dc1e_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_0dc1e_row16_col0" class="data row16 col0" >593.000000</td>
                        <td id="T_0dc1e_row16_col1" class="data row16 col1" >279.000000</td>
                        <td id="T_0dc1e_row16_col2" class="data row16 col2" >-9.000000</td>
                        <td id="T_0dc1e_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_0dc1e_row17_col0" class="data row17 col0" >304.000000</td>
                        <td id="T_0dc1e_row17_col1" class="data row17 col1" >-57.000000</td>
                        <td id="T_0dc1e_row17_col2" class="data row17 col2" >857.000000</td>
                        <td id="T_0dc1e_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_0dc1e_row18_col0" class="data row18 col0" >697.000000</td>
                        <td id="T_0dc1e_row18_col1" class="data row18 col1" >145.000000</td>
                        <td id="T_0dc1e_row18_col2" class="data row18 col2" >845.000000</td>
                        <td id="T_0dc1e_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_0dc1e_row19_col0" class="data row19 col0" >775.000000</td>
                        <td id="T_0dc1e_row19_col1" class="data row19 col1" >247.000000</td>
                        <td id="T_0dc1e_row19_col2" class="data row19 col2" >78.000000</td>
                        <td id="T_0dc1e_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_0dc1e_row20_col0" class="data row20 col0" >nan</td>
                        <td id="T_0dc1e_row20_col1" class="data row20 col1" >nan</td>
                        <td id="T_0dc1e_row20_col2" class="data row20 col2" >484.000000</td>
                        <td id="T_0dc1e_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_0dc1e_row21_col0" class="data row21 col0" >nan</td>
                        <td id="T_0dc1e_row21_col1" class="data row21 col1" >nan</td>
                        <td id="T_0dc1e_row21_col2" class="data row21 col2" >384.000000</td>
                        <td id="T_0dc1e_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_0dc1e_row22_col0" class="data row22 col0" >nan</td>
                        <td id="T_0dc1e_row22_col1" class="data row22 col1" >nan</td>
                        <td id="T_0dc1e_row22_col2" class="data row22 col2" >658.000000</td>
                        <td id="T_0dc1e_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_0dc1e_row23_col0" class="data row23 col0" >nan</td>
                        <td id="T_0dc1e_row23_col1" class="data row23 col1" >nan</td>
                        <td id="T_0dc1e_row23_col2" class="data row23 col2" >622.000000</td>
                        <td id="T_0dc1e_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_0dc1e_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_0dc1e_row24_col0" class="data row24 col0" >nan</td>
                        <td id="T_0dc1e_row24_col1" class="data row24 col1" >nan</td>
                        <td id="T_0dc1e_row24_col2" class="data row24 col2" >459.000000</td>
                        <td id="T_0dc1e_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table>
	<table id="T_eab10_" style='display:inline'><caption>chunk 1 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_eab10_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_eab10_row0_col0" class="data row0 col0" >614</td>
                        <td id="T_eab10_row0_col1" class="data row0 col1" >964</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_eab10_row1_col0" class="data row1 col0" >887</td>
                        <td id="T_eab10_row1_col1" class="data row1 col1" >155</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_eab10_row2_col0" class="data row2 col0" >865</td>
                        <td id="T_eab10_row2_col1" class="data row2 col1" >179</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_eab10_row3_col0" class="data row3 col0" >343</td>
                        <td id="T_eab10_row3_col1" class="data row3 col1" >167</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_eab10_row4_col0" class="data row4 col0" >212</td>
                        <td id="T_eab10_row4_col1" class="data row4 col1" >100</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_eab10_row5_col0" class="data row5 col0" >-52</td>
                        <td id="T_eab10_row5_col1" class="data row5 col1" >-98</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_eab10_row6_col0" class="data row6 col0" >738</td>
                        <td id="T_eab10_row6_col1" class="data row6 col1" >573</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_eab10_row7_col0" class="data row7 col0" >151</td>
                        <td id="T_eab10_row7_col1" class="data row7 col1" >138</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_eab10_row8_col0" class="data row8 col0" >-21</td>
                        <td id="T_eab10_row8_col1" class="data row8 col1" >378</td>
            </tr>
            <tr>
                        <th id="T_eab10_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_eab10_row9_col0" class="data row9 col0" >178</td>
                        <td id="T_eab10_row9_col1" class="data row9 col1" >266</td>
            </tr>
    </tbody></table>
	<table id="T_7a927_" style='display:inline'><caption>chunk 2 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_7a927_level0_row0" class="row_heading level0 row0" >10</th>
                        <td id="T_7a927_row0_col0" class="data row0 col0" >172</td>
                        <td id="T_7a927_row0_col1" class="data row0 col1" >596</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row1" class="row_heading level0 row1" >11</th>
                        <td id="T_7a927_row1_col0" class="data row1 col0" >521</td>
                        <td id="T_7a927_row1_col1" class="data row1 col1" >618</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row2" class="row_heading level0 row2" >12</th>
                        <td id="T_7a927_row2_col0" class="data row2 col0" >592</td>
                        <td id="T_7a927_row2_col1" class="data row2 col1" >832</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row3" class="row_heading level0 row3" >13</th>
                        <td id="T_7a927_row3_col0" class="data row3 col0" >560</td>
                        <td id="T_7a927_row3_col1" class="data row3 col1" >831</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row4" class="row_heading level0 row4" >14</th>
                        <td id="T_7a927_row4_col0" class="data row4 col0" >926</td>
                        <td id="T_7a927_row4_col1" class="data row4 col1" >179</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row5" class="row_heading level0 row5" >15</th>
                        <td id="T_7a927_row5_col0" class="data row5 col0" >901</td>
                        <td id="T_7a927_row5_col1" class="data row5 col1" >486</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row6" class="row_heading level0 row6" >16</th>
                        <td id="T_7a927_row6_col0" class="data row6 col0" >610</td>
                        <td id="T_7a927_row6_col1" class="data row6 col1" >472</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row7" class="row_heading level0 row7" >17</th>
                        <td id="T_7a927_row7_col0" class="data row7 col0" >587</td>
                        <td id="T_7a927_row7_col1" class="data row7 col1" >325</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row8" class="row_heading level0 row8" >18</th>
                        <td id="T_7a927_row8_col0" class="data row8 col0" >463</td>
                        <td id="T_7a927_row8_col1" class="data row8 col1" >653</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row9" class="row_heading level0 row9" >19</th>
                        <td id="T_7a927_row9_col0" class="data row9 col0" >9</td>
                        <td id="T_7a927_row9_col1" class="data row9 col1" >923</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row10" class="row_heading level0 row10" >20</th>
                        <td id="T_7a927_row10_col0" class="data row10 col0" >138</td>
                        <td id="T_7a927_row10_col1" class="data row10 col1" >460</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row11" class="row_heading level0 row11" >21</th>
                        <td id="T_7a927_row11_col0" class="data row11 col0" >715</td>
                        <td id="T_7a927_row11_col1" class="data row11 col1" >362</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row12" class="row_heading level0 row12" >22</th>
                        <td id="T_7a927_row12_col0" class="data row12 col0" >590</td>
                        <td id="T_7a927_row12_col1" class="data row12 col1" >-91</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row13" class="row_heading level0 row13" >23</th>
                        <td id="T_7a927_row13_col0" class="data row13 col0" >642</td>
                        <td id="T_7a927_row13_col1" class="data row13 col1" >-18</td>
            </tr>
            <tr>
                        <th id="T_7a927_level0_row14" class="row_heading level0 row14" >24</th>
                        <td id="T_7a927_row14_col0" class="data row14 col0" >679</td>
                        <td id="T_7a927_row14_col1" class="data row14 col1" >54</td>
            </tr>
    </tbody></table>
	<table id="T_5f34c_" style='display:inline'><caption>chunk 3 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_Y</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_5f34c_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_5f34c_row0_col0" class="data row0 col0" >108</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_5f34c_row1_col0" class="data row1 col0" >979</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_5f34c_row2_col0" class="data row2 col0" >533</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_5f34c_row3_col0" class="data row3 col0" >235</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_5f34c_row4_col0" class="data row4 col0" >497</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_5f34c_row5_col0" class="data row5 col0" >608</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_5f34c_row6_col0" class="data row6 col0" >781</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_5f34c_row7_col0" class="data row7 col0" >646</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_5f34c_row8_col0" class="data row8 col0" >157</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_5f34c_row9_col0" class="data row9 col0" >895</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_5f34c_row10_col0" class="data row10 col0" >705</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_5f34c_row11_col0" class="data row11 col0" >873</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_5f34c_row12_col0" class="data row12 col0" >298</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_5f34c_row13_col0" class="data row13 col0" >-82</td>
            </tr>
            <tr>
                        <th id="T_5f34c_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_5f34c_row14_col0" class="data row14 col0" >484</td>
            </tr>
    </tbody></table>
	<table id="T_ce4cc_" style='display:inline'><caption>chunk 4 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_Y</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_ce4cc_level0_row0" class="row_heading level0 row0" >15</th>
                        <td id="T_ce4cc_row0_col0" class="data row0 col0" >446</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row1" class="row_heading level0 row1" >16</th>
                        <td id="T_ce4cc_row1_col0" class="data row1 col0" >456</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row2" class="row_heading level0 row2" >17</th>
                        <td id="T_ce4cc_row2_col0" class="data row2 col0" >776</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row3" class="row_heading level0 row3" >18</th>
                        <td id="T_ce4cc_row3_col0" class="data row3 col0" >208</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row4" class="row_heading level0 row4" >19</th>
                        <td id="T_ce4cc_row4_col0" class="data row4 col0" >236</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row5" class="row_heading level0 row5" >20</th>
                        <td id="T_ce4cc_row5_col0" class="data row5 col0" >795</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row6" class="row_heading level0 row6" >21</th>
                        <td id="T_ce4cc_row6_col0" class="data row6 col0" >760</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row7" class="row_heading level0 row7" >22</th>
                        <td id="T_ce4cc_row7_col0" class="data row7 col0" >160</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row8" class="row_heading level0 row8" >23</th>
                        <td id="T_ce4cc_row8_col0" class="data row8 col0" >667</td>
            </tr>
            <tr>
                        <th id="T_ce4cc_level0_row9" class="row_heading level0 row9" >24</th>
                        <td id="T_ce4cc_row9_col0" class="data row9 col0" >447</td>
            </tr>
    </tbody></table>
	<table id="T_15f6a_" style='display:inline'><caption>Final data - After session commit</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_15f6a_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_15f6a_row0_col0" class="data row0 col0" >614</td>
                        <td id="T_15f6a_row0_col1" class="data row0 col1" >964</td>
                        <td id="T_15f6a_row0_col2" class="data row0 col2" >108.000000</td>
                        <td id="T_15f6a_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_15f6a_row1_col0" class="data row1 col0" >887</td>
                        <td id="T_15f6a_row1_col1" class="data row1 col1" >155</td>
                        <td id="T_15f6a_row1_col2" class="data row1 col2" >979.000000</td>
                        <td id="T_15f6a_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_15f6a_row2_col0" class="data row2 col0" >865</td>
                        <td id="T_15f6a_row2_col1" class="data row2 col1" >179</td>
                        <td id="T_15f6a_row2_col2" class="data row2 col2" >533.000000</td>
                        <td id="T_15f6a_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_15f6a_row3_col0" class="data row3 col0" >343</td>
                        <td id="T_15f6a_row3_col1" class="data row3 col1" >167</td>
                        <td id="T_15f6a_row3_col2" class="data row3 col2" >235.000000</td>
                        <td id="T_15f6a_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_15f6a_row4_col0" class="data row4 col0" >212</td>
                        <td id="T_15f6a_row4_col1" class="data row4 col1" >100</td>
                        <td id="T_15f6a_row4_col2" class="data row4 col2" >497.000000</td>
                        <td id="T_15f6a_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_15f6a_row5_col0" class="data row5 col0" >-52</td>
                        <td id="T_15f6a_row5_col1" class="data row5 col1" >-98</td>
                        <td id="T_15f6a_row5_col2" class="data row5 col2" >608.000000</td>
                        <td id="T_15f6a_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_15f6a_row6_col0" class="data row6 col0" >738</td>
                        <td id="T_15f6a_row6_col1" class="data row6 col1" >573</td>
                        <td id="T_15f6a_row6_col2" class="data row6 col2" >781.000000</td>
                        <td id="T_15f6a_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_15f6a_row7_col0" class="data row7 col0" >151</td>
                        <td id="T_15f6a_row7_col1" class="data row7 col1" >138</td>
                        <td id="T_15f6a_row7_col2" class="data row7 col2" >646.000000</td>
                        <td id="T_15f6a_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_15f6a_row8_col0" class="data row8 col0" >-21</td>
                        <td id="T_15f6a_row8_col1" class="data row8 col1" >378</td>
                        <td id="T_15f6a_row8_col2" class="data row8 col2" >157.000000</td>
                        <td id="T_15f6a_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_15f6a_row9_col0" class="data row9 col0" >178</td>
                        <td id="T_15f6a_row9_col1" class="data row9 col1" >266</td>
                        <td id="T_15f6a_row9_col2" class="data row9 col2" >895.000000</td>
                        <td id="T_15f6a_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_15f6a_row10_col0" class="data row10 col0" >172</td>
                        <td id="T_15f6a_row10_col1" class="data row10 col1" >596</td>
                        <td id="T_15f6a_row10_col2" class="data row10 col2" >705.000000</td>
                        <td id="T_15f6a_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_15f6a_row11_col0" class="data row11 col0" >521</td>
                        <td id="T_15f6a_row11_col1" class="data row11 col1" >618</td>
                        <td id="T_15f6a_row11_col2" class="data row11 col2" >873.000000</td>
                        <td id="T_15f6a_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_15f6a_row12_col0" class="data row12 col0" >592</td>
                        <td id="T_15f6a_row12_col1" class="data row12 col1" >832</td>
                        <td id="T_15f6a_row12_col2" class="data row12 col2" >298.000000</td>
                        <td id="T_15f6a_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_15f6a_row13_col0" class="data row13 col0" >560</td>
                        <td id="T_15f6a_row13_col1" class="data row13 col1" >831</td>
                        <td id="T_15f6a_row13_col2" class="data row13 col2" >-82.000000</td>
                        <td id="T_15f6a_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_15f6a_row14_col0" class="data row14 col0" >926</td>
                        <td id="T_15f6a_row14_col1" class="data row14 col1" >179</td>
                        <td id="T_15f6a_row14_col2" class="data row14 col2" >484.000000</td>
                        <td id="T_15f6a_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_15f6a_row15_col0" class="data row15 col0" >901</td>
                        <td id="T_15f6a_row15_col1" class="data row15 col1" >486</td>
                        <td id="T_15f6a_row15_col2" class="data row15 col2" >446.000000</td>
                        <td id="T_15f6a_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_15f6a_row16_col0" class="data row16 col0" >610</td>
                        <td id="T_15f6a_row16_col1" class="data row16 col1" >472</td>
                        <td id="T_15f6a_row16_col2" class="data row16 col2" >456.000000</td>
                        <td id="T_15f6a_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_15f6a_row17_col0" class="data row17 col0" >587</td>
                        <td id="T_15f6a_row17_col1" class="data row17 col1" >325</td>
                        <td id="T_15f6a_row17_col2" class="data row17 col2" >776.000000</td>
                        <td id="T_15f6a_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_15f6a_row18_col0" class="data row18 col0" >463</td>
                        <td id="T_15f6a_row18_col1" class="data row18 col1" >653</td>
                        <td id="T_15f6a_row18_col2" class="data row18 col2" >208.000000</td>
                        <td id="T_15f6a_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_15f6a_row19_col0" class="data row19 col0" >9</td>
                        <td id="T_15f6a_row19_col1" class="data row19 col1" >923</td>
                        <td id="T_15f6a_row19_col2" class="data row19 col2" >236.000000</td>
                        <td id="T_15f6a_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_15f6a_row20_col0" class="data row20 col0" >138</td>
                        <td id="T_15f6a_row20_col1" class="data row20 col1" >460</td>
                        <td id="T_15f6a_row20_col2" class="data row20 col2" >795.000000</td>
                        <td id="T_15f6a_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_15f6a_row21_col0" class="data row21 col0" >715</td>
                        <td id="T_15f6a_row21_col1" class="data row21 col1" >362</td>
                        <td id="T_15f6a_row21_col2" class="data row21 col2" >760.000000</td>
                        <td id="T_15f6a_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_15f6a_row22_col0" class="data row22 col0" >590</td>
                        <td id="T_15f6a_row22_col1" class="data row22 col1" >-91</td>
                        <td id="T_15f6a_row22_col2" class="data row22 col2" >160.000000</td>
                        <td id="T_15f6a_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_15f6a_row23_col0" class="data row23 col0" >642</td>
                        <td id="T_15f6a_row23_col1" class="data row23 col1" >-18</td>
                        <td id="T_15f6a_row23_col2" class="data row23 col2" >667.000000</td>
                        <td id="T_15f6a_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_15f6a_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_15f6a_row24_col0" class="data row24 col0" >679</td>
                        <td id="T_15f6a_row24_col1" class="data row24 col1" >54</td>
                        <td id="T_15f6a_row24_col2" class="data row24 col2" >447.000000</td>
                        <td id="T_15f6a_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table></div>


The function below shows the differences between the current WellLog data version with columns and rows added by chunk and the previous version of the WellLog data.

```python
display_previous_and_current_well_log_data_versions(record_id)
```

<div>
<style  type="text/css" >
#T_d0644_row0_col0,#T_d0644_row0_col1,#T_d0644_row1_col0,#T_d0644_row1_col1,#T_d0644_row2_col0,#T_d0644_row2_col1,#T_d0644_row3_col0,#T_d0644_row3_col1,#T_d0644_row4_col0,#T_d0644_row4_col1,#T_d0644_row5_col0,#T_d0644_row5_col1,#T_d0644_row5_col2,#T_d0644_row6_col0,#T_d0644_row6_col1,#T_d0644_row6_col2,#T_d0644_row7_col0,#T_d0644_row7_col1,#T_d0644_row7_col2,#T_d0644_row8_col0,#T_d0644_row8_col1,#T_d0644_row8_col2,#T_d0644_row9_col0,#T_d0644_row9_col1,#T_d0644_row9_col2,#T_d0644_row10_col0,#T_d0644_row10_col1,#T_d0644_row10_col2,#T_d0644_row10_col3,#T_d0644_row11_col0,#T_d0644_row11_col1,#T_d0644_row11_col2,#T_d0644_row11_col3,#T_d0644_row12_col0,#T_d0644_row12_col1,#T_d0644_row12_col2,#T_d0644_row12_col3,#T_d0644_row13_col0,#T_d0644_row13_col1,#T_d0644_row13_col2,#T_d0644_row13_col3,#T_d0644_row14_col0,#T_d0644_row14_col1,#T_d0644_row14_col2,#T_d0644_row14_col3,#T_d0644_row15_col0,#T_d0644_row15_col1,#T_d0644_row15_col2,#T_d0644_row16_col0,#T_d0644_row16_col1,#T_d0644_row16_col2,#T_d0644_row17_col0,#T_d0644_row17_col1,#T_d0644_row17_col2,#T_d0644_row18_col0,#T_d0644_row18_col1,#T_d0644_row18_col2,#T_d0644_row19_col0,#T_d0644_row19_col1,#T_d0644_row19_col2,#T_d0644_row20_col2,#T_d0644_row21_col2,#T_d0644_row22_col2,#T_d0644_row23_col2,#T_d0644_row24_col2{
            color:  blue;
        }
#T_d0644_row0_col2,#T_d0644_row0_col3,#T_d0644_row1_col2,#T_d0644_row1_col3,#T_d0644_row2_col2,#T_d0644_row2_col3,#T_d0644_row3_col2,#T_d0644_row3_col3,#T_d0644_row4_col2,#T_d0644_row4_col3,#T_d0644_row5_col3,#T_d0644_row6_col3,#T_d0644_row7_col3,#T_d0644_row8_col3,#T_d0644_row9_col3,#T_d0644_row15_col3,#T_d0644_row16_col3,#T_d0644_row17_col3,#T_d0644_row18_col3,#T_d0644_row19_col3,#T_d0644_row20_col0,#T_d0644_row20_col1,#T_d0644_row20_col3,#T_d0644_row21_col0,#T_d0644_row21_col1,#T_d0644_row21_col3,#T_d0644_row22_col0,#T_d0644_row22_col1,#T_d0644_row22_col3,#T_d0644_row23_col0,#T_d0644_row23_col1,#T_d0644_row23_col3,#T_d0644_row24_col0,#T_d0644_row24_col1,#T_d0644_row24_col3{
            background-color:  lightyellow;
            color:  blue;
        }
#T_413e0_row0_col0,#T_413e0_row0_col1,#T_413e0_row0_col2,#T_413e0_row1_col0,#T_413e0_row1_col1,#T_413e0_row1_col2,#T_413e0_row2_col0,#T_413e0_row2_col1,#T_413e0_row2_col2,#T_413e0_row3_col0,#T_413e0_row3_col1,#T_413e0_row3_col2,#T_413e0_row4_col0,#T_413e0_row4_col1,#T_413e0_row4_col2,#T_413e0_row5_col0,#T_413e0_row5_col1,#T_413e0_row5_col2,#T_413e0_row6_col0,#T_413e0_row6_col1,#T_413e0_row6_col2,#T_413e0_row7_col0,#T_413e0_row7_col1,#T_413e0_row7_col2,#T_413e0_row8_col0,#T_413e0_row8_col1,#T_413e0_row8_col2,#T_413e0_row9_col0,#T_413e0_row9_col1,#T_413e0_row9_col2,#T_413e0_row10_col0,#T_413e0_row10_col1,#T_413e0_row10_col2,#T_413e0_row10_col3,#T_413e0_row11_col0,#T_413e0_row11_col1,#T_413e0_row11_col2,#T_413e0_row11_col3,#T_413e0_row12_col0,#T_413e0_row12_col1,#T_413e0_row12_col2,#T_413e0_row12_col3,#T_413e0_row13_col0,#T_413e0_row13_col1,#T_413e0_row13_col2,#T_413e0_row13_col3,#T_413e0_row14_col0,#T_413e0_row14_col1,#T_413e0_row14_col2,#T_413e0_row14_col3,#T_413e0_row15_col0,#T_413e0_row15_col1,#T_413e0_row15_col2,#T_413e0_row16_col0,#T_413e0_row16_col1,#T_413e0_row16_col2,#T_413e0_row17_col0,#T_413e0_row17_col1,#T_413e0_row17_col2,#T_413e0_row18_col0,#T_413e0_row18_col1,#T_413e0_row18_col2,#T_413e0_row19_col0,#T_413e0_row19_col1,#T_413e0_row19_col2,#T_413e0_row20_col0,#T_413e0_row20_col1,#T_413e0_row20_col2,#T_413e0_row21_col0,#T_413e0_row21_col1,#T_413e0_row21_col2,#T_413e0_row22_col0,#T_413e0_row22_col1,#T_413e0_row22_col2,#T_413e0_row23_col0,#T_413e0_row23_col1,#T_413e0_row23_col2,#T_413e0_row24_col0,#T_413e0_row24_col1,#T_413e0_row24_col2{
            color:  blue;
        }
#T_413e0_row0_col3,#T_413e0_row1_col3,#T_413e0_row2_col3,#T_413e0_row3_col3,#T_413e0_row4_col3,#T_413e0_row5_col3,#T_413e0_row6_col3,#T_413e0_row7_col3,#T_413e0_row8_col3,#T_413e0_row9_col3,#T_413e0_row15_col3,#T_413e0_row16_col3,#T_413e0_row17_col3,#T_413e0_row18_col3,#T_413e0_row19_col3,#T_413e0_row20_col3,#T_413e0_row21_col3,#T_413e0_row22_col3,#T_413e0_row23_col3,#T_413e0_row24_col3{
            color:  blue;
            background-color:  lightyellow;
        }
</style>
</style>
<table id="T_d0644_" style='display:inline'><caption>Previous WellLog data version</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_d0644_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_d0644_row0_col0" class="data row0 col0" >265.000000</td>
                        <td id="T_d0644_row0_col1" class="data row0 col1" >845.000000</td>
                        <td id="T_d0644_row0_col2" class="data row0 col2" >nan</td>
                        <td id="T_d0644_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_d0644_row1_col0" class="data row1 col0" >92.000000</td>
                        <td id="T_d0644_row1_col1" class="data row1 col1" >246.000000</td>
                        <td id="T_d0644_row1_col2" class="data row1 col2" >nan</td>
                        <td id="T_d0644_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_d0644_row2_col0" class="data row2 col0" >804.000000</td>
                        <td id="T_d0644_row2_col1" class="data row2 col1" >268.000000</td>
                        <td id="T_d0644_row2_col2" class="data row2 col2" >nan</td>
                        <td id="T_d0644_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_d0644_row3_col0" class="data row3 col0" >645.000000</td>
                        <td id="T_d0644_row3_col1" class="data row3 col1" >877.000000</td>
                        <td id="T_d0644_row3_col2" class="data row3 col2" >nan</td>
                        <td id="T_d0644_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_d0644_row4_col0" class="data row4 col0" >-20.000000</td>
                        <td id="T_d0644_row4_col1" class="data row4 col1" >-28.000000</td>
                        <td id="T_d0644_row4_col2" class="data row4 col2" >nan</td>
                        <td id="T_d0644_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_d0644_row5_col0" class="data row5 col0" >-29.000000</td>
                        <td id="T_d0644_row5_col1" class="data row5 col1" >832.000000</td>
                        <td id="T_d0644_row5_col2" class="data row5 col2" >192.000000</td>
                        <td id="T_d0644_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_d0644_row6_col0" class="data row6 col0" >-15.000000</td>
                        <td id="T_d0644_row6_col1" class="data row6 col1" >107.000000</td>
                        <td id="T_d0644_row6_col2" class="data row6 col2" >816.000000</td>
                        <td id="T_d0644_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_d0644_row7_col0" class="data row7 col0" >339.000000</td>
                        <td id="T_d0644_row7_col1" class="data row7 col1" >212.000000</td>
                        <td id="T_d0644_row7_col2" class="data row7 col2" >61.000000</td>
                        <td id="T_d0644_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_d0644_row8_col0" class="data row8 col0" >823.000000</td>
                        <td id="T_d0644_row8_col1" class="data row8 col1" >240.000000</td>
                        <td id="T_d0644_row8_col2" class="data row8 col2" >658.000000</td>
                        <td id="T_d0644_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_d0644_row9_col0" class="data row9 col0" >-97.000000</td>
                        <td id="T_d0644_row9_col1" class="data row9 col1" >349.000000</td>
                        <td id="T_d0644_row9_col2" class="data row9 col2" >104.000000</td>
                        <td id="T_d0644_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_d0644_row10_col0" class="data row10 col0" >183.000000</td>
                        <td id="T_d0644_row10_col1" class="data row10 col1" >89.000000</td>
                        <td id="T_d0644_row10_col2" class="data row10 col2" >704.000000</td>
                        <td id="T_d0644_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_d0644_row11_col0" class="data row11 col0" >194.000000</td>
                        <td id="T_d0644_row11_col1" class="data row11 col1" >276.000000</td>
                        <td id="T_d0644_row11_col2" class="data row11 col2" >681.000000</td>
                        <td id="T_d0644_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_d0644_row12_col0" class="data row12 col0" >-7.000000</td>
                        <td id="T_d0644_row12_col1" class="data row12 col1" >-7.000000</td>
                        <td id="T_d0644_row12_col2" class="data row12 col2" >393.000000</td>
                        <td id="T_d0644_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_d0644_row13_col0" class="data row13 col0" >446.000000</td>
                        <td id="T_d0644_row13_col1" class="data row13 col1" >829.000000</td>
                        <td id="T_d0644_row13_col2" class="data row13 col2" >329.000000</td>
                        <td id="T_d0644_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_d0644_row14_col0" class="data row14 col0" >32.000000</td>
                        <td id="T_d0644_row14_col1" class="data row14 col1" >706.000000</td>
                        <td id="T_d0644_row14_col2" class="data row14 col2" >402.000000</td>
                        <td id="T_d0644_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_d0644_row15_col0" class="data row15 col0" >914.000000</td>
                        <td id="T_d0644_row15_col1" class="data row15 col1" >740.000000</td>
                        <td id="T_d0644_row15_col2" class="data row15 col2" >418.000000</td>
                        <td id="T_d0644_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_d0644_row16_col0" class="data row16 col0" >593.000000</td>
                        <td id="T_d0644_row16_col1" class="data row16 col1" >279.000000</td>
                        <td id="T_d0644_row16_col2" class="data row16 col2" >-9.000000</td>
                        <td id="T_d0644_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_d0644_row17_col0" class="data row17 col0" >304.000000</td>
                        <td id="T_d0644_row17_col1" class="data row17 col1" >-57.000000</td>
                        <td id="T_d0644_row17_col2" class="data row17 col2" >857.000000</td>
                        <td id="T_d0644_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_d0644_row18_col0" class="data row18 col0" >697.000000</td>
                        <td id="T_d0644_row18_col1" class="data row18 col1" >145.000000</td>
                        <td id="T_d0644_row18_col2" class="data row18 col2" >845.000000</td>
                        <td id="T_d0644_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_d0644_row19_col0" class="data row19 col0" >775.000000</td>
                        <td id="T_d0644_row19_col1" class="data row19 col1" >247.000000</td>
                        <td id="T_d0644_row19_col2" class="data row19 col2" >78.000000</td>
                        <td id="T_d0644_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_d0644_row20_col0" class="data row20 col0" >nan</td>
                        <td id="T_d0644_row20_col1" class="data row20 col1" >nan</td>
                        <td id="T_d0644_row20_col2" class="data row20 col2" >484.000000</td>
                        <td id="T_d0644_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_d0644_row21_col0" class="data row21 col0" >nan</td>
                        <td id="T_d0644_row21_col1" class="data row21 col1" >nan</td>
                        <td id="T_d0644_row21_col2" class="data row21 col2" >384.000000</td>
                        <td id="T_d0644_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_d0644_row22_col0" class="data row22 col0" >nan</td>
                        <td id="T_d0644_row22_col1" class="data row22 col1" >nan</td>
                        <td id="T_d0644_row22_col2" class="data row22 col2" >658.000000</td>
                        <td id="T_d0644_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_d0644_row23_col0" class="data row23 col0" >nan</td>
                        <td id="T_d0644_row23_col1" class="data row23 col1" >nan</td>
                        <td id="T_d0644_row23_col2" class="data row23 col2" >622.000000</td>
                        <td id="T_d0644_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_d0644_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_d0644_row24_col0" class="data row24 col0" >nan</td>
                        <td id="T_d0644_row24_col1" class="data row24 col1" >nan</td>
                        <td id="T_d0644_row24_col2" class="data row24 col2" >459.000000</td>
                        <td id="T_d0644_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table>
	<table id="T_413e0_" style='display:inline'><caption>Current WellLog data version with data chunks added in red</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_413e0_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_413e0_row0_col0" class="data row0 col0" >614</td>
                        <td id="T_413e0_row0_col1" class="data row0 col1" >964</td>
                        <td id="T_413e0_row0_col2" class="data row0 col2" >108.000000</td>
                        <td id="T_413e0_row0_col3" class="data row0 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_413e0_row1_col0" class="data row1 col0" >887</td>
                        <td id="T_413e0_row1_col1" class="data row1 col1" >155</td>
                        <td id="T_413e0_row1_col2" class="data row1 col2" >979.000000</td>
                        <td id="T_413e0_row1_col3" class="data row1 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_413e0_row2_col0" class="data row2 col0" >865</td>
                        <td id="T_413e0_row2_col1" class="data row2 col1" >179</td>
                        <td id="T_413e0_row2_col2" class="data row2 col2" >533.000000</td>
                        <td id="T_413e0_row2_col3" class="data row2 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_413e0_row3_col0" class="data row3 col0" >343</td>
                        <td id="T_413e0_row3_col1" class="data row3 col1" >167</td>
                        <td id="T_413e0_row3_col2" class="data row3 col2" >235.000000</td>
                        <td id="T_413e0_row3_col3" class="data row3 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_413e0_row4_col0" class="data row4 col0" >212</td>
                        <td id="T_413e0_row4_col1" class="data row4 col1" >100</td>
                        <td id="T_413e0_row4_col2" class="data row4 col2" >497.000000</td>
                        <td id="T_413e0_row4_col3" class="data row4 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_413e0_row5_col0" class="data row5 col0" >-52</td>
                        <td id="T_413e0_row5_col1" class="data row5 col1" >-98</td>
                        <td id="T_413e0_row5_col2" class="data row5 col2" >608.000000</td>
                        <td id="T_413e0_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_413e0_row6_col0" class="data row6 col0" >738</td>
                        <td id="T_413e0_row6_col1" class="data row6 col1" >573</td>
                        <td id="T_413e0_row6_col2" class="data row6 col2" >781.000000</td>
                        <td id="T_413e0_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_413e0_row7_col0" class="data row7 col0" >151</td>
                        <td id="T_413e0_row7_col1" class="data row7 col1" >138</td>
                        <td id="T_413e0_row7_col2" class="data row7 col2" >646.000000</td>
                        <td id="T_413e0_row7_col3" class="data row7 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_413e0_row8_col0" class="data row8 col0" >-21</td>
                        <td id="T_413e0_row8_col1" class="data row8 col1" >378</td>
                        <td id="T_413e0_row8_col2" class="data row8 col2" >157.000000</td>
                        <td id="T_413e0_row8_col3" class="data row8 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_413e0_row9_col0" class="data row9 col0" >178</td>
                        <td id="T_413e0_row9_col1" class="data row9 col1" >266</td>
                        <td id="T_413e0_row9_col2" class="data row9 col2" >895.000000</td>
                        <td id="T_413e0_row9_col3" class="data row9 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_413e0_row10_col0" class="data row10 col0" >172</td>
                        <td id="T_413e0_row10_col1" class="data row10 col1" >596</td>
                        <td id="T_413e0_row10_col2" class="data row10 col2" >705.000000</td>
                        <td id="T_413e0_row10_col3" class="data row10 col3" >141.000000</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_413e0_row11_col0" class="data row11 col0" >521</td>
                        <td id="T_413e0_row11_col1" class="data row11 col1" >618</td>
                        <td id="T_413e0_row11_col2" class="data row11 col2" >873.000000</td>
                        <td id="T_413e0_row11_col3" class="data row11 col3" >478.000000</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_413e0_row12_col0" class="data row12 col0" >592</td>
                        <td id="T_413e0_row12_col1" class="data row12 col1" >832</td>
                        <td id="T_413e0_row12_col2" class="data row12 col2" >298.000000</td>
                        <td id="T_413e0_row12_col3" class="data row12 col3" >72.000000</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_413e0_row13_col0" class="data row13 col0" >560</td>
                        <td id="T_413e0_row13_col1" class="data row13 col1" >831</td>
                        <td id="T_413e0_row13_col2" class="data row13 col2" >-82.000000</td>
                        <td id="T_413e0_row13_col3" class="data row13 col3" >476.000000</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_413e0_row14_col0" class="data row14 col0" >926</td>
                        <td id="T_413e0_row14_col1" class="data row14 col1" >179</td>
                        <td id="T_413e0_row14_col2" class="data row14 col2" >484.000000</td>
                        <td id="T_413e0_row14_col3" class="data row14 col3" >434.000000</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row15" class="row_heading level0 row15" >15</th>
                        <td id="T_413e0_row15_col0" class="data row15 col0" >901</td>
                        <td id="T_413e0_row15_col1" class="data row15 col1" >486</td>
                        <td id="T_413e0_row15_col2" class="data row15 col2" >446.000000</td>
                        <td id="T_413e0_row15_col3" class="data row15 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row16" class="row_heading level0 row16" >16</th>
                        <td id="T_413e0_row16_col0" class="data row16 col0" >610</td>
                        <td id="T_413e0_row16_col1" class="data row16 col1" >472</td>
                        <td id="T_413e0_row16_col2" class="data row16 col2" >456.000000</td>
                        <td id="T_413e0_row16_col3" class="data row16 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row17" class="row_heading level0 row17" >17</th>
                        <td id="T_413e0_row17_col0" class="data row17 col0" >587</td>
                        <td id="T_413e0_row17_col1" class="data row17 col1" >325</td>
                        <td id="T_413e0_row17_col2" class="data row17 col2" >776.000000</td>
                        <td id="T_413e0_row17_col3" class="data row17 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row18" class="row_heading level0 row18" >18</th>
                        <td id="T_413e0_row18_col0" class="data row18 col0" >463</td>
                        <td id="T_413e0_row18_col1" class="data row18 col1" >653</td>
                        <td id="T_413e0_row18_col2" class="data row18 col2" >208.000000</td>
                        <td id="T_413e0_row18_col3" class="data row18 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row19" class="row_heading level0 row19" >19</th>
                        <td id="T_413e0_row19_col0" class="data row19 col0" >9</td>
                        <td id="T_413e0_row19_col1" class="data row19 col1" >923</td>
                        <td id="T_413e0_row19_col2" class="data row19 col2" >236.000000</td>
                        <td id="T_413e0_row19_col3" class="data row19 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row20" class="row_heading level0 row20" >20</th>
                        <td id="T_413e0_row20_col0" class="data row20 col0" >138</td>
                        <td id="T_413e0_row20_col1" class="data row20 col1" >460</td>
                        <td id="T_413e0_row20_col2" class="data row20 col2" >795.000000</td>
                        <td id="T_413e0_row20_col3" class="data row20 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row21" class="row_heading level0 row21" >21</th>
                        <td id="T_413e0_row21_col0" class="data row21 col0" >715</td>
                        <td id="T_413e0_row21_col1" class="data row21 col1" >362</td>
                        <td id="T_413e0_row21_col2" class="data row21 col2" >760.000000</td>
                        <td id="T_413e0_row21_col3" class="data row21 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row22" class="row_heading level0 row22" >22</th>
                        <td id="T_413e0_row22_col0" class="data row22 col0" >590</td>
                        <td id="T_413e0_row22_col1" class="data row22 col1" >-91</td>
                        <td id="T_413e0_row22_col2" class="data row22 col2" >160.000000</td>
                        <td id="T_413e0_row22_col3" class="data row22 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row23" class="row_heading level0 row23" >23</th>
                        <td id="T_413e0_row23_col0" class="data row23 col0" >642</td>
                        <td id="T_413e0_row23_col1" class="data row23 col1" >-18</td>
                        <td id="T_413e0_row23_col2" class="data row23 col2" >667.000000</td>
                        <td id="T_413e0_row23_col3" class="data row23 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_413e0_level0_row24" class="row_heading level0 row24" >24</th>
                        <td id="T_413e0_row24_col0" class="data row24 col0" >679</td>
                        <td id="T_413e0_row24_col1" class="data row24 col1" >54</td>
                        <td id="T_413e0_row24_col2" class="data row24 col2" >447.000000</td>
                        <td id="T_413e0_row24_col3" class="data row24 col3" >nan</td>
            </tr>
    </tbody></table></div>


## Add array data by chunk to a WellLog

As prerequisite a new WellLog record is created below to store array data. The WellLog is created with a MD column storing reference values and single WellLog values stored in a column X.

```python
# Create new record for 2D curves
record_2d_response = client.post(welllog_dms_url, json=[record])
print_response(record_2d_response)
record_2d_id = record_2d_response.json()["recordIds"][0]
print(f"2D record created '{record_2d_id}'")

initial_df = generate_df(['COLUMN_MD', 'COLUMN_X'], range(10))
headers = { 'content-type': 'application/x-parquet'}
print_response(client.post(f'{welllog_dms_url}/{record_2d_id}/data', data=initial_df.to_parquet(engine="pyarrow"), headers=headers))
```
    
By convention array data are added to the WellLog record through a Panda dataframe with columns that contain the name of the array and the column number between square bracket. The orient value has to be set to columns.

```python
# Create a session
create_2d_session_response = client.post(f'{welllog_dms_url}/{record_2d_id}/sessions', json={'mode': 'update'})

print_response(create_2d_session_response)
session_id_2d = create_2d_session_response.json()['id']

# Send chunk data for 2D
arr_data_dataframe = generate_df(['2D[0]', '2D[1]'], range(15))

print_response(client.post(f'{welllog_dms_url}/{record_2d_id}/sessions/{session_id_2d}/data',
                           params={"orient": 'columns'},
                           headers={ 'content-type': 'application/json'},
                           data=arr_data_dataframe.to_json(orient='columns')))

# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_2d_id}/sessions/{session_id_2d}', json={'state': 'commit'}))
```

The script below shows initial WellLog data before the session and array data added to the final WellLog data version after the session has been committed.

```python
# Display result
bulk_2d_data_response = client.get(f'{welllog_dms_url}/{record_2d_id}/data')
bulk_2d_data = create_df_from_response(bulk_2d_data_response)
display_operation(initial_df, [arr_data_dataframe], bulk_2d_data)
```

<div>
><style  type="text/css" >
#T_0d1d2_row0_col0,#T_0d1d2_row0_col1,#T_0d1d2_row1_col0,#T_0d1d2_row1_col1,#T_0d1d2_row2_col0,#T_0d1d2_row2_col1,#T_0d1d2_row3_col0,#T_0d1d2_row3_col1,#T_0d1d2_row4_col0,#T_0d1d2_row4_col1,#T_0d1d2_row5_col0,#T_0d1d2_row5_col1,#T_0d1d2_row6_col0,#T_0d1d2_row6_col1,#T_0d1d2_row7_col0,#T_0d1d2_row7_col1,#T_0d1d2_row8_col0,#T_0d1d2_row8_col1,#T_0d1d2_row9_col0,#T_0d1d2_row9_col1,#T_0d1d2_row10_col0,#T_0d1d2_row10_col1,#T_0d1d2_row11_col0,#T_0d1d2_row11_col1,#T_0d1d2_row12_col0,#T_0d1d2_row12_col1,#T_0d1d2_row13_col0,#T_0d1d2_row13_col1,#T_0d1d2_row14_col0,#T_0d1d2_row14_col1{
            color:  blue;
        }

#T_b00a6_row0_col0,#T_b00a6_row0_col1,#T_b00a6_row1_col0,#T_b00a6_row1_col1,#T_b00a6_row2_col0,#T_b00a6_row2_col1,#T_b00a6_row3_col0,#T_b00a6_row3_col1,#T_b00a6_row4_col0,#T_b00a6_row4_col1,#T_b00a6_row5_col0,#T_b00a6_row5_col1,#T_b00a6_row6_col0,#T_b00a6_row6_col1,#T_b00a6_row7_col0,#T_b00a6_row7_col1,#T_b00a6_row8_col0,#T_b00a6_row8_col1,#T_b00a6_row9_col0,#T_b00a6_row9_col1,#T_b00a6_row10_col0,#T_b00a6_row10_col1,#T_b00a6_row11_col0,#T_b00a6_row11_col1,#T_b00a6_row12_col0,#T_b00a6_row12_col1,#T_b00a6_row13_col0,#T_b00a6_row13_col1,#T_b00a6_row14_col0,#T_b00a6_row14_col1{
            color:  blue;
        }
#T_b00a6_row10_col2,#T_b00a6_row10_col3,#T_b00a6_row11_col2,#T_b00a6_row11_col3,#T_b00a6_row12_col2,#T_b00a6_row12_col3,#T_b00a6_row13_col2,#T_b00a6_row13_col3,#T_b00a6_row14_col2,#T_b00a6_row14_col3{
            background-color:  lightyellow;
        }
</style>
<table id="T_e85dc_" style='display:inline'><caption>Initial data - Before session</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_e85dc_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_e85dc_row0_col0" class="data row0 col0" >752</td>
                        <td id="T_e85dc_row0_col1" class="data row0 col1" >700</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_e85dc_row1_col0" class="data row1 col0" >-36</td>
                        <td id="T_e85dc_row1_col1" class="data row1 col1" >241</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_e85dc_row2_col0" class="data row2 col0" >883</td>
                        <td id="T_e85dc_row2_col1" class="data row2 col1" >107</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_e85dc_row3_col0" class="data row3 col0" >177</td>
                        <td id="T_e85dc_row3_col1" class="data row3 col1" >159</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_e85dc_row4_col0" class="data row4 col0" >156</td>
                        <td id="T_e85dc_row4_col1" class="data row4 col1" >801</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_e85dc_row5_col0" class="data row5 col0" >277</td>
                        <td id="T_e85dc_row5_col1" class="data row5 col1" >597</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_e85dc_row6_col0" class="data row6 col0" >-1</td>
                        <td id="T_e85dc_row6_col1" class="data row6 col1" >202</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_e85dc_row7_col0" class="data row7 col0" >-21</td>
                        <td id="T_e85dc_row7_col1" class="data row7 col1" >669</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_e85dc_row8_col0" class="data row8 col0" >334</td>
                        <td id="T_e85dc_row8_col1" class="data row8 col1" >291</td>
            </tr>
            <tr>
                        <th id="T_e85dc_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_e85dc_row9_col0" class="data row9 col0" >771</td>
                        <td id="T_e85dc_row9_col1" class="data row9 col1" >-56</td>
            </tr>
    </tbody></table>
	<table id="T_0d1d2_" style='display:inline'><caption>chunk 1 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >2D[0]</th>        <th class="col_heading level0 col1" >2D[1]</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_0d1d2_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_0d1d2_row0_col0" class="data row0 col0" >676</td>
                        <td id="T_0d1d2_row0_col1" class="data row0 col1" >702</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_0d1d2_row1_col0" class="data row1 col0" >983</td>
                        <td id="T_0d1d2_row1_col1" class="data row1 col1" >588</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_0d1d2_row2_col0" class="data row2 col0" >948</td>
                        <td id="T_0d1d2_row2_col1" class="data row2 col1" >422</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_0d1d2_row3_col0" class="data row3 col0" >272</td>
                        <td id="T_0d1d2_row3_col1" class="data row3 col1" >-59</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_0d1d2_row4_col0" class="data row4 col0" >986</td>
                        <td id="T_0d1d2_row4_col1" class="data row4 col1" >869</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_0d1d2_row5_col0" class="data row5 col0" >563</td>
                        <td id="T_0d1d2_row5_col1" class="data row5 col1" >131</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_0d1d2_row6_col0" class="data row6 col0" >703</td>
                        <td id="T_0d1d2_row6_col1" class="data row6 col1" >31</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_0d1d2_row7_col0" class="data row7 col0" >375</td>
                        <td id="T_0d1d2_row7_col1" class="data row7 col1" >538</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_0d1d2_row8_col0" class="data row8 col0" >244</td>
                        <td id="T_0d1d2_row8_col1" class="data row8 col1" >416</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_0d1d2_row9_col0" class="data row9 col0" >761</td>
                        <td id="T_0d1d2_row9_col1" class="data row9 col1" >580</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_0d1d2_row10_col0" class="data row10 col0" >825</td>
                        <td id="T_0d1d2_row10_col1" class="data row10 col1" >222</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_0d1d2_row11_col0" class="data row11 col0" >174</td>
                        <td id="T_0d1d2_row11_col1" class="data row11 col1" >644</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_0d1d2_row12_col0" class="data row12 col0" >871</td>
                        <td id="T_0d1d2_row12_col1" class="data row12 col1" >857</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_0d1d2_row13_col0" class="data row13 col0" >880</td>
                        <td id="T_0d1d2_row13_col1" class="data row13 col1" >780</td>
            </tr>
            <tr>
                        <th id="T_0d1d2_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_0d1d2_row14_col0" class="data row14 col0" >783</td>
                        <td id="T_0d1d2_row14_col1" class="data row14 col1" >883</td>
            </tr>
    </tbody></table>
	<table id="T_b00a6_" style='display:inline'><caption>Final data - After session commit</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >2D[0]</th>        <th class="col_heading level0 col1" >2D[1]</th>        <th class="col_heading level0 col2" >COLUMN_MD</th>        <th class="col_heading level0 col3" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_b00a6_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_b00a6_row0_col0" class="data row0 col0" >676</td>
                        <td id="T_b00a6_row0_col1" class="data row0 col1" >702</td>
                        <td id="T_b00a6_row0_col2" class="data row0 col2" >752.000000</td>
                        <td id="T_b00a6_row0_col3" class="data row0 col3" >700.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_b00a6_row1_col0" class="data row1 col0" >983</td>
                        <td id="T_b00a6_row1_col1" class="data row1 col1" >588</td>
                        <td id="T_b00a6_row1_col2" class="data row1 col2" >-36.000000</td>
                        <td id="T_b00a6_row1_col3" class="data row1 col3" >241.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_b00a6_row2_col0" class="data row2 col0" >948</td>
                        <td id="T_b00a6_row2_col1" class="data row2 col1" >422</td>
                        <td id="T_b00a6_row2_col2" class="data row2 col2" >883.000000</td>
                        <td id="T_b00a6_row2_col3" class="data row2 col3" >107.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_b00a6_row3_col0" class="data row3 col0" >272</td>
                        <td id="T_b00a6_row3_col1" class="data row3 col1" >-59</td>
                        <td id="T_b00a6_row3_col2" class="data row3 col2" >177.000000</td>
                        <td id="T_b00a6_row3_col3" class="data row3 col3" >159.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_b00a6_row4_col0" class="data row4 col0" >986</td>
                        <td id="T_b00a6_row4_col1" class="data row4 col1" >869</td>
                        <td id="T_b00a6_row4_col2" class="data row4 col2" >156.000000</td>
                        <td id="T_b00a6_row4_col3" class="data row4 col3" >801.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_b00a6_row5_col0" class="data row5 col0" >563</td>
                        <td id="T_b00a6_row5_col1" class="data row5 col1" >131</td>
                        <td id="T_b00a6_row5_col2" class="data row5 col2" >277.000000</td>
                        <td id="T_b00a6_row5_col3" class="data row5 col3" >597.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_b00a6_row6_col0" class="data row6 col0" >703</td>
                        <td id="T_b00a6_row6_col1" class="data row6 col1" >31</td>
                        <td id="T_b00a6_row6_col2" class="data row6 col2" >-1.000000</td>
                        <td id="T_b00a6_row6_col3" class="data row6 col3" >202.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_b00a6_row7_col0" class="data row7 col0" >375</td>
                        <td id="T_b00a6_row7_col1" class="data row7 col1" >538</td>
                        <td id="T_b00a6_row7_col2" class="data row7 col2" >-21.000000</td>
                        <td id="T_b00a6_row7_col3" class="data row7 col3" >669.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_b00a6_row8_col0" class="data row8 col0" >244</td>
                        <td id="T_b00a6_row8_col1" class="data row8 col1" >416</td>
                        <td id="T_b00a6_row8_col2" class="data row8 col2" >334.000000</td>
                        <td id="T_b00a6_row8_col3" class="data row8 col3" >291.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_b00a6_row9_col0" class="data row9 col0" >761</td>
                        <td id="T_b00a6_row9_col1" class="data row9 col1" >580</td>
                        <td id="T_b00a6_row9_col2" class="data row9 col2" >771.000000</td>
                        <td id="T_b00a6_row9_col3" class="data row9 col3" >-56.000000</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_b00a6_row10_col0" class="data row10 col0" >825</td>
                        <td id="T_b00a6_row10_col1" class="data row10 col1" >222</td>
                        <td id="T_b00a6_row10_col2" class="data row10 col2" >nan</td>
                        <td id="T_b00a6_row10_col3" class="data row10 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_b00a6_row11_col0" class="data row11 col0" >174</td>
                        <td id="T_b00a6_row11_col1" class="data row11 col1" >644</td>
                        <td id="T_b00a6_row11_col2" class="data row11 col2" >nan</td>
                        <td id="T_b00a6_row11_col3" class="data row11 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_b00a6_row12_col0" class="data row12 col0" >871</td>
                        <td id="T_b00a6_row12_col1" class="data row12 col1" >857</td>
                        <td id="T_b00a6_row12_col2" class="data row12 col2" >nan</td>
                        <td id="T_b00a6_row12_col3" class="data row12 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_b00a6_row13_col0" class="data row13 col0" >880</td>
                        <td id="T_b00a6_row13_col1" class="data row13 col1" >780</td>
                        <td id="T_b00a6_row13_col2" class="data row13 col2" >nan</td>
                        <td id="T_b00a6_row13_col3" class="data row13 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_b00a6_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_b00a6_row14_col0" class="data row14 col0" >783</td>
                        <td id="T_b00a6_row14_col1" class="data row14 col1" >883</td>
                        <td id="T_b00a6_row14_col2" class="data row14 col2" >nan</td>
                        <td id="T_b00a6_row14_col3" class="data row14 col3" >nan</td>
            </tr>
    </tbody></table></div>

The function below shows the differences between the current WellLog data version with array data added by chunk and the previous version of the WellLog data.

```python
display_previous_and_current_well_log_data_versions(record_2d_id)
```

<div>
<style  type="text/css" >
#T_14222_row0_col0,#T_14222_row0_col1,#T_14222_row1_col0,#T_14222_row1_col1,#T_14222_row2_col0,#T_14222_row2_col1,#T_14222_row3_col0,#T_14222_row3_col1,#T_14222_row4_col0,#T_14222_row4_col1,#T_14222_row5_col0,#T_14222_row5_col1,#T_14222_row6_col0,#T_14222_row6_col1,#T_14222_row7_col0,#T_14222_row7_col1,#T_14222_row8_col0,#T_14222_row8_col1,#T_14222_row9_col0,#T_14222_row9_col1{
            color:  blue;
        }
#T_e0d27_row0_col0,#T_e0d27_row0_col1,#T_e0d27_row1_col0,#T_e0d27_row1_col1,#T_e0d27_row2_col0,#T_e0d27_row2_col1,#T_e0d27_row3_col0,#T_e0d27_row3_col1,#T_e0d27_row4_col0,#T_e0d27_row4_col1,#T_e0d27_row5_col0,#T_e0d27_row5_col1,#T_e0d27_row6_col0,#T_e0d27_row6_col1,#T_e0d27_row7_col0,#T_e0d27_row7_col1,#T_e0d27_row8_col0,#T_e0d27_row8_col1,#T_e0d27_row9_col0,#T_e0d27_row9_col1,#T_e0d27_row10_col0,#T_e0d27_row10_col1,#T_e0d27_row11_col0,#T_e0d27_row11_col1,#T_e0d27_row12_col0,#T_e0d27_row12_col1,#T_e0d27_row13_col0,#T_e0d27_row13_col1,#T_e0d27_row14_col0,#T_e0d27_row14_col1{
            color:  red;
        }
#T_e0d27_row0_col2,#T_e0d27_row0_col3,#T_e0d27_row1_col2,#T_e0d27_row1_col3,#T_e0d27_row2_col2,#T_e0d27_row2_col3,#T_e0d27_row3_col2,#T_e0d27_row3_col3,#T_e0d27_row4_col2,#T_e0d27_row4_col3,#T_e0d27_row5_col2,#T_e0d27_row5_col3,#T_e0d27_row6_col2,#T_e0d27_row6_col3,#T_e0d27_row7_col2,#T_e0d27_row7_col3,#T_e0d27_row8_col2,#T_e0d27_row8_col3,#T_e0d27_row9_col2,#T_e0d27_row9_col3{
            color:  blue;
        }
#T_e0d27_row10_col2,#T_e0d27_row10_col3,#T_e0d27_row11_col2,#T_e0d27_row11_col3,#T_e0d27_row12_col2,#T_e0d27_row12_col3,#T_e0d27_row13_col2,#T_e0d27_row13_col3,#T_e0d27_row14_col2,#T_e0d27_row14_col3{
            color:  red;
            background-color:  lightyellow;
        }
</style>
<table id="T_14222_" style='display:inline'><caption>Previous WellLog data version</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_14222_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_14222_row0_col0" class="data row0 col0" >752</td>
                        <td id="T_14222_row0_col1" class="data row0 col1" >700</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_14222_row1_col0" class="data row1 col0" >-36</td>
                        <td id="T_14222_row1_col1" class="data row1 col1" >241</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_14222_row2_col0" class="data row2 col0" >883</td>
                        <td id="T_14222_row2_col1" class="data row2 col1" >107</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_14222_row3_col0" class="data row3 col0" >177</td>
                        <td id="T_14222_row3_col1" class="data row3 col1" >159</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_14222_row4_col0" class="data row4 col0" >156</td>
                        <td id="T_14222_row4_col1" class="data row4 col1" >801</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_14222_row5_col0" class="data row5 col0" >277</td>
                        <td id="T_14222_row5_col1" class="data row5 col1" >597</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_14222_row6_col0" class="data row6 col0" >-1</td>
                        <td id="T_14222_row6_col1" class="data row6 col1" >202</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_14222_row7_col0" class="data row7 col0" >-21</td>
                        <td id="T_14222_row7_col1" class="data row7 col1" >669</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_14222_row8_col0" class="data row8 col0" >334</td>
                        <td id="T_14222_row8_col1" class="data row8 col1" >291</td>
            </tr>
            <tr>
                        <th id="T_14222_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_14222_row9_col0" class="data row9 col0" >771</td>
                        <td id="T_14222_row9_col1" class="data row9 col1" >-56</td>
            </tr>
    </tbody></table>
	<table id="T_e0d27_" style='display:inline'><caption>Current WellLog data version with data chunks added in red</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >2D[0]</th>        <th class="col_heading level0 col1" >2D[1]</th>        <th class="col_heading level0 col2" >COLUMN_MD</th>        <th class="col_heading level0 col3" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_e0d27_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_e0d27_row0_col0" class="data row0 col0" >676</td>
                        <td id="T_e0d27_row0_col1" class="data row0 col1" >702</td>
                        <td id="T_e0d27_row0_col2" class="data row0 col2" >752.000000</td>
                        <td id="T_e0d27_row0_col3" class="data row0 col3" >700.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_e0d27_row1_col0" class="data row1 col0" >983</td>
                        <td id="T_e0d27_row1_col1" class="data row1 col1" >588</td>
                        <td id="T_e0d27_row1_col2" class="data row1 col2" >-36.000000</td>
                        <td id="T_e0d27_row1_col3" class="data row1 col3" >241.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_e0d27_row2_col0" class="data row2 col0" >948</td>
                        <td id="T_e0d27_row2_col1" class="data row2 col1" >422</td>
                        <td id="T_e0d27_row2_col2" class="data row2 col2" >883.000000</td>
                        <td id="T_e0d27_row2_col3" class="data row2 col3" >107.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_e0d27_row3_col0" class="data row3 col0" >272</td>
                        <td id="T_e0d27_row3_col1" class="data row3 col1" >-59</td>
                        <td id="T_e0d27_row3_col2" class="data row3 col2" >177.000000</td>
                        <td id="T_e0d27_row3_col3" class="data row3 col3" >159.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_e0d27_row4_col0" class="data row4 col0" >986</td>
                        <td id="T_e0d27_row4_col1" class="data row4 col1" >869</td>
                        <td id="T_e0d27_row4_col2" class="data row4 col2" >156.000000</td>
                        <td id="T_e0d27_row4_col3" class="data row4 col3" >801.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_e0d27_row5_col0" class="data row5 col0" >563</td>
                        <td id="T_e0d27_row5_col1" class="data row5 col1" >131</td>
                        <td id="T_e0d27_row5_col2" class="data row5 col2" >277.000000</td>
                        <td id="T_e0d27_row5_col3" class="data row5 col3" >597.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_e0d27_row6_col0" class="data row6 col0" >703</td>
                        <td id="T_e0d27_row6_col1" class="data row6 col1" >31</td>
                        <td id="T_e0d27_row6_col2" class="data row6 col2" >-1.000000</td>
                        <td id="T_e0d27_row6_col3" class="data row6 col3" >202.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_e0d27_row7_col0" class="data row7 col0" >375</td>
                        <td id="T_e0d27_row7_col1" class="data row7 col1" >538</td>
                        <td id="T_e0d27_row7_col2" class="data row7 col2" >-21.000000</td>
                        <td id="T_e0d27_row7_col3" class="data row7 col3" >669.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_e0d27_row8_col0" class="data row8 col0" >244</td>
                        <td id="T_e0d27_row8_col1" class="data row8 col1" >416</td>
                        <td id="T_e0d27_row8_col2" class="data row8 col2" >334.000000</td>
                        <td id="T_e0d27_row8_col3" class="data row8 col3" >291.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_e0d27_row9_col0" class="data row9 col0" >761</td>
                        <td id="T_e0d27_row9_col1" class="data row9 col1" >580</td>
                        <td id="T_e0d27_row9_col2" class="data row9 col2" >771.000000</td>
                        <td id="T_e0d27_row9_col3" class="data row9 col3" >-56.000000</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row10" class="row_heading level0 row10" >10</th>
                        <td id="T_e0d27_row10_col0" class="data row10 col0" >825</td>
                        <td id="T_e0d27_row10_col1" class="data row10 col1" >222</td>
                        <td id="T_e0d27_row10_col2" class="data row10 col2" >nan</td>
                        <td id="T_e0d27_row10_col3" class="data row10 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row11" class="row_heading level0 row11" >11</th>
                        <td id="T_e0d27_row11_col0" class="data row11 col0" >174</td>
                        <td id="T_e0d27_row11_col1" class="data row11 col1" >644</td>
                        <td id="T_e0d27_row11_col2" class="data row11 col2" >nan</td>
                        <td id="T_e0d27_row11_col3" class="data row11 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row12" class="row_heading level0 row12" >12</th>
                        <td id="T_e0d27_row12_col0" class="data row12 col0" >871</td>
                        <td id="T_e0d27_row12_col1" class="data row12 col1" >857</td>
                        <td id="T_e0d27_row12_col2" class="data row12 col2" >nan</td>
                        <td id="T_e0d27_row12_col3" class="data row12 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row13" class="row_heading level0 row13" >13</th>
                        <td id="T_e0d27_row13_col0" class="data row13 col0" >880</td>
                        <td id="T_e0d27_row13_col1" class="data row13 col1" >780</td>
                        <td id="T_e0d27_row13_col2" class="data row13 col2" >nan</td>
                        <td id="T_e0d27_row13_col3" class="data row13 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_e0d27_level0_row14" class="row_heading level0 row14" >14</th>
                        <td id="T_e0d27_row14_col0" class="data row14 col0" >783</td>
                        <td id="T_e0d27_row14_col1" class="data row14 col1" >883</td>
                        <td id="T_e0d27_row14_col2" class="data row14 col2" >nan</td>
                        <td id="T_e0d27_row14_col3" class="data row14 col3" >nan</td>
            </tr>
    </tbody></table></div>

## Update existing WellLog data by chunk

This section explains how to replace values for specific curves in a specific range for a given WellLog record id.
First let's create through the sample script below a new WellLog record with some bulk data posted as a JSON dataframe to the WellLog record.


```python
# Create new record
response = client.post(welllog_dms_url, json=[record])
print_response(response)
record_id = response.json()["recordIds"][0]
record_id

# Add first bulk data to the record
df_cols_md_x_y_z = generate_df(['COLUMN_MD', 'COLUMN_X', 'COLUMN_Y', 'COLUMN_Z'], range(5))
print_response(client.post(f'{welllog_dms_url}/{record_id}/data', json=df_cols_md_x_y_z.to_dict(orient='split')))

check_data_response = client.get(f'{welllog_dms_url}/{record_id}/data')
print_response(check_data_response)
df_cols_md_x_y_z = create_df_from_response(check_data_response)
df_cols_md_x_y_z
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
      <th>COLUMN_MD</th>
      <th>COLUMN_X</th>
      <th>COLUMN_Y</th>
      <th>COLUMN_Z</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>-15</td>
      <td>-21</td>
      <td>283</td>
      <td>768</td>
    </tr>
    <tr>
      <th>1</th>
      <td>643</td>
      <td>659</td>
      <td>-3</td>
      <td>437</td>
    </tr>
    <tr>
      <th>2</th>
      <td>674</td>
      <td>988</td>
      <td>739</td>
      <td>530</td>
    </tr>
    <tr>
      <th>3</th>
      <td>-40</td>
      <td>244</td>
      <td>311</td>
      <td>171</td>
    </tr>
    <tr>
      <th>4</th>
      <td>989</td>
      <td>989</td>
      <td>710</td>
      <td>541</td>
    </tr>
  </tbody>
</table>
</div>

The update of the WellLog bulk data is done in a session open with the update mode. The dataframe posted to the session has to contain a list of column names and a range of indexes that exist in the current version of the WellLog bulk data to be updated. If columns and indexes don't exist then they are appended to the WellLog data as explain in the "Add data by columns" section.

```python
# Create a session
resp = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': 'update'})
print_response(resp)
sessions_id_update = resp.json()['id']

# udpating columns MD and Y with new data for rows going from 0 to 4 index numbers
data_md_y = generate_df(['COLUMN_MD', 'COLUMN_Y'], range(5))
resp = client.post(f'{welllog_dms_url}/{record_id}/sessions/{sessions_id_update}/data', json=data_md_y.to_dict(orient='split'))
print_response(resp)

# udpating column Z with new data for rows going from 3 to 4 index numbers
data_z = generate_df(['COLUMN_Z'], range(3, 5))
resp = client.post(f'{welllog_dms_url}/{record_id}/sessions/{sessions_id_update}/data', json=data_z.to_dict(orient='split'))
print_response(resp)

# appending column X with 3 new rows
data_md_x = generate_df(['COLUMN_X'], range(5, 8))
resp = client.post(f'{welllog_dms_url}/{record_id}/sessions/{sessions_id_update}/data', json=data_md_x.to_dict(orient='split'))
print_response(resp)

# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_id}/sessions/{sessions_id_update}', json={'state': 'commit'}))
```
 
The script below shows initial WellLog data before the session and data updated to the final WellLog data version after the session has been committed.

```python
# display result
response = client.get(f'{welllog_dms_url}/{record_id}/data')
data_update = create_df_from_response(response)
display_operation(df_cols_md_x_y_z, [data_md_y, data_z, data_md_x], data_update)
```
<div>
<style  type="text/css" >
#T_9a5ee_row0_col0,#T_9a5ee_row0_col1,#T_9a5ee_row1_col0,#T_9a5ee_row1_col1,#T_9a5ee_row2_col0,#T_9a5ee_row2_col1,#T_9a5ee_row3_col0,#T_9a5ee_row3_col1,#T_9a5ee_row4_col0,#T_9a5ee_row4_col1{
            color:  blue;
        }
#T_f8239_row0_col0,#T_f8239_row1_col0{
            color:  green;
        }
#T_f4408_row0_col0,#T_f4408_row1_col0,#T_f4408_row2_col0{
            color:  orange;
        }
#T_324ce_row0_col0,#T_324ce_row0_col2,#T_324ce_row1_col0,#T_324ce_row1_col2,#T_324ce_row2_col0,#T_324ce_row2_col2,#T_324ce_row3_col0,#T_324ce_row3_col2,#T_324ce_row4_col0,#T_324ce_row4_col2{
            color:  blue;
        }
#T_324ce_row3_col3,#T_324ce_row4_col3{
            color:  green;
        }
#T_324ce_row5_col0,#T_324ce_row5_col2,#T_324ce_row5_col3,#T_324ce_row6_col0,#T_324ce_row6_col2,#T_324ce_row6_col3,#T_324ce_row7_col0,#T_324ce_row7_col2,#T_324ce_row7_col3{
            background-color:  lightyellow;
        }
#T_324ce_row5_col1,#T_324ce_row6_col1,#T_324ce_row7_col1{
            color:  orange;
        }
</style>
<table id="T_5260e_" style='display:inline'><caption>Initial data - Before session</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_5260e_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_5260e_row0_col0" class="data row0 col0" >-15</td>
                        <td id="T_5260e_row0_col1" class="data row0 col1" >-21</td>
                        <td id="T_5260e_row0_col2" class="data row0 col2" >283</td>
                        <td id="T_5260e_row0_col3" class="data row0 col3" >768</td>
            </tr>
            <tr>
                        <th id="T_5260e_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_5260e_row1_col0" class="data row1 col0" >643</td>
                        <td id="T_5260e_row1_col1" class="data row1 col1" >659</td>
                        <td id="T_5260e_row1_col2" class="data row1 col2" >-3</td>
                        <td id="T_5260e_row1_col3" class="data row1 col3" >437</td>
            </tr>
            <tr>
                        <th id="T_5260e_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_5260e_row2_col0" class="data row2 col0" >674</td>
                        <td id="T_5260e_row2_col1" class="data row2 col1" >988</td>
                        <td id="T_5260e_row2_col2" class="data row2 col2" >739</td>
                        <td id="T_5260e_row2_col3" class="data row2 col3" >530</td>
            </tr>
            <tr>
                        <th id="T_5260e_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_5260e_row3_col0" class="data row3 col0" >-40</td>
                        <td id="T_5260e_row3_col1" class="data row3 col1" >244</td>
                        <td id="T_5260e_row3_col2" class="data row3 col2" >311</td>
                        <td id="T_5260e_row3_col3" class="data row3 col3" >171</td>
            </tr>
            <tr>
                        <th id="T_5260e_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_5260e_row4_col0" class="data row4 col0" >989</td>
                        <td id="T_5260e_row4_col1" class="data row4 col1" >989</td>
                        <td id="T_5260e_row4_col2" class="data row4 col2" >710</td>
                        <td id="T_5260e_row4_col3" class="data row4 col3" >541</td>
            </tr>
    </tbody></table><table id="T_9a5ee_" style='display:inline'><caption>chunk 1 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_Y</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_9a5ee_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_9a5ee_row0_col0" class="data row0 col0" >-91</td>
                        <td id="T_9a5ee_row0_col1" class="data row0 col1" >877</td>
            </tr>
            <tr>
                        <th id="T_9a5ee_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_9a5ee_row1_col0" class="data row1 col0" >-28</td>
                        <td id="T_9a5ee_row1_col1" class="data row1 col1" >336</td>
            </tr>
            <tr>
                        <th id="T_9a5ee_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_9a5ee_row2_col0" class="data row2 col0" >971</td>
                        <td id="T_9a5ee_row2_col1" class="data row2 col1" >648</td>
            </tr>
            <tr>
                        <th id="T_9a5ee_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_9a5ee_row3_col0" class="data row3 col0" >458</td>
                        <td id="T_9a5ee_row3_col1" class="data row3 col1" >-50</td>
            </tr>
            <tr>
                        <th id="T_9a5ee_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_9a5ee_row4_col0" class="data row4 col0" >569</td>
                        <td id="T_9a5ee_row4_col1" class="data row4 col1" >89</td>
            </tr>
    </tbody></table><table id="T_f8239_" style='display:inline'><caption>chunk 2 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_f8239_level0_row0" class="row_heading level0 row0" >3</th>
                        <td id="T_f8239_row0_col0" class="data row0 col0" >964</td>
            </tr>
            <tr>
                        <th id="T_f8239_level0_row1" class="row_heading level0 row1" >4</th>
                        <td id="T_f8239_row1_col0" class="data row1 col0" >991</td>
            </tr>
    </tbody></table><table id="T_f4408_" style='display:inline'><caption>chunk 3 sent</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_f4408_level0_row0" class="row_heading level0 row0" >5</th>
                        <td id="T_f4408_row0_col0" class="data row0 col0" >587</td>
            </tr>
            <tr>
                        <th id="T_f4408_level0_row1" class="row_heading level0 row1" >6</th>
                        <td id="T_f4408_row1_col0" class="data row1 col0" >818</td>
            </tr>
            <tr>
                        <th id="T_f4408_level0_row2" class="row_heading level0 row2" >7</th>
                        <td id="T_f4408_row2_col0" class="data row2 col0" >768</td>
            </tr>
    </tbody></table><table id="T_324ce_" style='display:inline'><caption>Final data - After session commit</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>        <th class="col_heading level0 col2" >COLUMN_Y</th>        <th class="col_heading level0 col3" >COLUMN_Z</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_324ce_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_324ce_row0_col0" class="data row0 col0" >-91.000000</td>
                        <td id="T_324ce_row0_col1" class="data row0 col1" >-21</td>
                        <td id="T_324ce_row0_col2" class="data row0 col2" >877.000000</td>
                        <td id="T_324ce_row0_col3" class="data row0 col3" >768.000000</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_324ce_row1_col0" class="data row1 col0" >-28.000000</td>
                        <td id="T_324ce_row1_col1" class="data row1 col1" >659</td>
                        <td id="T_324ce_row1_col2" class="data row1 col2" >336.000000</td>
                        <td id="T_324ce_row1_col3" class="data row1 col3" >437.000000</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_324ce_row2_col0" class="data row2 col0" >971.000000</td>
                        <td id="T_324ce_row2_col1" class="data row2 col1" >988</td>
                        <td id="T_324ce_row2_col2" class="data row2 col2" >648.000000</td>
                        <td id="T_324ce_row2_col3" class="data row2 col3" >530.000000</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_324ce_row3_col0" class="data row3 col0" >458.000000</td>
                        <td id="T_324ce_row3_col1" class="data row3 col1" >244</td>
                        <td id="T_324ce_row3_col2" class="data row3 col2" >-50.000000</td>
                        <td id="T_324ce_row3_col3" class="data row3 col3" >964.000000</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_324ce_row4_col0" class="data row4 col0" >569.000000</td>
                        <td id="T_324ce_row4_col1" class="data row4 col1" >989</td>
                        <td id="T_324ce_row4_col2" class="data row4 col2" >89.000000</td>
                        <td id="T_324ce_row4_col3" class="data row4 col3" >991.000000</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_324ce_row5_col0" class="data row5 col0" >nan</td>
                        <td id="T_324ce_row5_col1" class="data row5 col1" >587</td>
                        <td id="T_324ce_row5_col2" class="data row5 col2" >nan</td>
                        <td id="T_324ce_row5_col3" class="data row5 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_324ce_row6_col0" class="data row6 col0" >nan</td>
                        <td id="T_324ce_row6_col1" class="data row6 col1" >818</td>
                        <td id="T_324ce_row6_col2" class="data row6 col2" >nan</td>
                        <td id="T_324ce_row6_col3" class="data row6 col3" >nan</td>
            </tr>
            <tr>
                        <th id="T_324ce_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_324ce_row7_col0" class="data row7 col0" >nan</td>
                        <td id="T_324ce_row7_col1" class="data row7 col1" >768</td>
                        <td id="T_324ce_row7_col2" class="data row7 col2" >nan</td>
                        <td id="T_324ce_row7_col3" class="data row7 col3" >nan</td>
            </tr>
    </tbody></table>
</div>

# WellLog record versioning<a name="welllog-record-versioning"></a>

Each time that the WellLog record metadata or its associated bulk data are updated a new version of the WellLog record is created.
This rule makes that the first version for a given WellLog record has never a bulk data associated to it as demonstrated by the script below:

```python
# creating a new record
response = client.post(welllog_dms_url, json=[record])
print_response(response)
record_id = response.json()["recordIds"][0]
record_id

# posting bulk data to the WellLog record
initial_df = generate_df(['COLUMN_MD', 'COLUMN_X'], range(10))
headers = { 'content-type': 'application/x-parquet'}
print_response(client.post(f'{welllog_dms_url}/{record_id}/data', data=initial_df.to_parquet(engine="pyarrow"), headers=headers))

# checking for versions = 2 versions of the WellLog record with only the last one with associated bulk data
results_response = client.get(f'{welllog_dms_url}/{record_id}/versions')
wellLog_versions_response = results_response.json()
versions = wellLog_versions_response['versions']
for index, version in enumerate(versions):
    print(f'{index}. version number: {version}')
    version_data_response = client.get(f'{welllog_dms_url}/{record_id}/versions/{version}/data')
    #print_response(version_data_response)
    if version_data_response.status_code == 200:
        version_df = create_df_from_response(version_data_response)
        version_df_st = version_df.style.set_table_attributes(f"style='margin-left:65px'").highlight_null(null_color='lightyellow').set_caption(f'WellLog data version {version}')   
        display(multi_table([version_df_st]))
    else:
        print(f'\tNo bulk data associated to version {version}')
```

    0. version number: 1627640423310341
    	No bulk data associated to version 1627640423310341
    1. version number: 1627640424041113
  
<table id="T_e5d05_" style='display:inline'><caption>WellLog data version 1627640424041113</caption><thead>    <tr>        <th class="blank level0" ></th>        <th class="col_heading level0 col0" >COLUMN_MD</th>        <th class="col_heading level0 col1" >COLUMN_X</th>    </tr></thead><tbody>
                <tr>
                        <th id="T_e5d05_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_e5d05_row0_col0" class="data row0 col0" >265</td>
                        <td id="T_e5d05_row0_col1" class="data row0 col1" >970</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_e5d05_row1_col0" class="data row1 col0" >643</td>
                        <td id="T_e5d05_row1_col1" class="data row1 col1" >-22</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_e5d05_row2_col0" class="data row2 col0" >-87</td>
                        <td id="T_e5d05_row2_col1" class="data row2 col1" >926</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_e5d05_row3_col0" class="data row3 col0" >710</td>
                        <td id="T_e5d05_row3_col1" class="data row3 col1" >432</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_e5d05_row4_col0" class="data row4 col0" >977</td>
                        <td id="T_e5d05_row4_col1" class="data row4 col1" >225</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_e5d05_row5_col0" class="data row5 col0" >997</td>
                        <td id="T_e5d05_row5_col1" class="data row5 col1" >880</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_e5d05_row6_col0" class="data row6 col0" >997</td>
                        <td id="T_e5d05_row6_col1" class="data row6 col1" >806</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_e5d05_row7_col0" class="data row7 col0" >33</td>
                        <td id="T_e5d05_row7_col1" class="data row7 col1" >80</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_e5d05_row8_col0" class="data row8 col0" >517</td>
                        <td id="T_e5d05_row8_col1" class="data row8 col1" >650</td>
            </tr>
            <tr>
                        <th id="T_e5d05_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_e5d05_row9_col0" class="data row9 col0" >514</td>
                        <td id="T_e5d05_row9_col1" class="data row9 col1" >792</td>
            </tr>
    </tbody></table>

## Write bulk data from a given WellLog record version

Through the wellbore DDMS API it is possible to write bulk data from a given version of the WellLog record.
The example below shows a WellLog record with two different versions of the bulk data.
1. First version contains only a column X
2. Second version contains columns X and Y

If a column Z is written from the first version, only columns X and Z remains in the final version of the WellLog bulk data.

```python
# creating a new record
response = client.post(welllog_dms_url, json=[record])
print_response(response)
record_id = response.json()["recordIds"][0]
record_id

# sending data for column A 
generated_A_dataframe = generate_df(['COLUMN_MD','COLUMN_X'], range(10))
headers = { 'content-type': 'application/x-parquet'}
print_response(client.post(f'{welllog_dms_url}/{record_id}/data', data=generated_A_dataframe.to_parquet(engine="pyarrow"), headers=headers))


SESSION_MODE = 'update' # 'update' | 'overwrite'

# adding column B to the WellLog by chunk through a session
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json={'mode': SESSION_MODE})
print_response(create_session_response)
session_id = create_session_response.json()['id']

generated_B_dataframe = generate_df(['COLUMN_Y'], range(10))
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=generated_B_dataframe.to_dict(orient='split')))

# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'}))

results_response = client.get(f'{welllog_dms_url}/{record_id}/versions')
wellLog_versions_response = results_response.json()
version = wellLog_versions_response['versions'][1]

# Create a session from previous version that contains only column A
session_json = {
    'mode': SESSION_MODE,
    'fromVersion': version
}
create_session_response = client.post(f'{welllog_dms_url}/{record_id}/sessions', json=session_json)
print_response(create_session_response)
session_id = create_session_response.json()['id']


# adding column C to the WellLog by chunk through a session and from the previous version
generated_C_dataframe = generate_df(['COLUMN_Z'], range(10))
print_response(client.post(f'{welllog_dms_url}/{record_id}/sessions/{session_id}/data', json=generated_C_dataframe.to_dict(orient='split')))


# Commit session
print_response(client.patch(f'{welllog_dms_url}/{record_id}/sessions/{session_id}', json={'state': 'commit'}))


# Display result
results_response = client.get(f'{welllog_dms_url}/{record_id}/versions')
wellLog_versions_response = results_response.json()
versions = wellLog_versions_response['versions']
titles = []
dataframes = []
for index, version in enumerate(versions):
    version_data_response = client.get(f'{welllog_dms_url}/{record_id}/versions/{version}/data')
    if version_data_response.status_code == 200:
        if index == 3:
            titles.append(f'{index}. version number {version} created from version {versions[1]}')
        else:
            titles.append(f'{index}. version number {version}')
        version_df = create_df_from_response(version_data_response)
        dataframes.append(version_df)
        

display_side_by_side(dataframes, titles)

```
    
<table id="T_697ec_" style='display:inline'>
  <caption>1. version number 1627640429377696</caption>
  <thead>    
	<tr>        
		<th class="blank level0" ></th>        
		<th class="col_heading level0 col0" >COLUMN_MD</th>        
		<th class="col_heading level0 col1" >COLUMN_X</th>    
	</tr>
  </thead>
  <tbody>
            <tr>
                        <th id="T_697ec_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_697ec_row0_col0" class="data row0 col0" >345</td>
                        <td id="T_697ec_row0_col1" class="data row0 col1" >18</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_697ec_row1_col0" class="data row1 col0" >845</td>
                        <td id="T_697ec_row1_col1" class="data row1 col1" >863</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_697ec_row2_col0" class="data row2 col0" >290</td>
                        <td id="T_697ec_row2_col1" class="data row2 col1" >-62</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_697ec_row3_col0" class="data row3 col0" >947</td>
                        <td id="T_697ec_row3_col1" class="data row3 col1" >698</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_697ec_row4_col0" class="data row4 col0" >562</td>
                        <td id="T_697ec_row4_col1" class="data row4 col1" >825</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_697ec_row5_col0" class="data row5 col0" >79</td>
                        <td id="T_697ec_row5_col1" class="data row5 col1" >450</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_697ec_row6_col0" class="data row6 col0" >809</td>
                        <td id="T_697ec_row6_col1" class="data row6 col1" >153</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_697ec_row7_col0" class="data row7 col0" >53</td>
                        <td id="T_697ec_row7_col1" class="data row7 col1" >450</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_697ec_row8_col0" class="data row8 col0" >121</td>
                        <td id="T_697ec_row8_col1" class="data row8 col1" >793</td>
            </tr>
            <tr>
                        <th id="T_697ec_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_697ec_row9_col0" class="data row9 col0" >352</td>
                        <td id="T_697ec_row9_col1" class="data row9 col1" >-97</td>
            </tr>
    </tbody>
</table>
<table id="T_cf3b3_" style='display:inline'>
  <caption>2. version number 1627640431304081</caption>
  <thead>    
	<tr>        
		<th class="blank level0" ></th>
		<th class="col_heading level0 col0" >COLUMN_MD</th>        
		<th class="col_heading level0 col1" >COLUMN_X</th>        
		<th class="col_heading level0 col2" >COLUMN_Y</th>    
	</tr>
  </thead>
  <tbody>
            <tr>
                        <th id="T_cf3b3_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_cf3b3_row0_col0" class="data row0 col0" >345</td>
                        <td id="T_cf3b3_row0_col1" class="data row0 col1" >18</td>
                        <td id="T_cf3b3_row0_col2" class="data row0 col2" >750</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_cf3b3_row1_col0" class="data row1 col0" >845</td>
                        <td id="T_cf3b3_row1_col1" class="data row1 col1" >863</td>
                        <td id="T_cf3b3_row1_col2" class="data row1 col2" >499</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_cf3b3_row2_col0" class="data row2 col0" >290</td>
                        <td id="T_cf3b3_row2_col1" class="data row2 col1" >-62</td>
                        <td id="T_cf3b3_row2_col2" class="data row2 col2" >114</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_cf3b3_row3_col0" class="data row3 col0" >947</td>
                        <td id="T_cf3b3_row3_col1" class="data row3 col1" >698</td>
                        <td id="T_cf3b3_row3_col2" class="data row3 col2" >637</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_cf3b3_row4_col0" class="data row4 col0" >562</td>
                        <td id="T_cf3b3_row4_col1" class="data row4 col1" >825</td>
                        <td id="T_cf3b3_row4_col2" class="data row4 col2" >368</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_cf3b3_row5_col0" class="data row5 col0" >79</td>
                        <td id="T_cf3b3_row5_col1" class="data row5 col1" >450</td>
                        <td id="T_cf3b3_row5_col2" class="data row5 col2" >219</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_cf3b3_row6_col0" class="data row6 col0" >809</td>
                        <td id="T_cf3b3_row6_col1" class="data row6 col1" >153</td>
                        <td id="T_cf3b3_row6_col2" class="data row6 col2" >46</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_cf3b3_row7_col0" class="data row7 col0" >53</td>
                        <td id="T_cf3b3_row7_col1" class="data row7 col1" >450</td>
                        <td id="T_cf3b3_row7_col2" class="data row7 col2" >628</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_cf3b3_row8_col0" class="data row8 col0" >121</td>
                        <td id="T_cf3b3_row8_col1" class="data row8 col1" >793</td>
                        <td id="T_cf3b3_row8_col2" class="data row8 col2" >267</td>
            </tr>
            <tr>
                        <th id="T_cf3b3_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_cf3b3_row9_col0" class="data row9 col0" >352</td>
                        <td id="T_cf3b3_row9_col1" class="data row9 col1" >-97</td>
                        <td id="T_cf3b3_row9_col2" class="data row9 col2" >990</td>
            </tr>
    </tbody>
</table>
<table id="T_6cd4b_" style='display:inline'>
 <caption>3. version number 1627640433479387 created from version 1627640429377696</caption>
 <thead>    
	<tr>        
		<th class="blank level0" ></th>        
		<th class="col_heading level0 col0" >COLUMN_MD</th>        
		<th class="col_heading level0 col1" >COLUMN_X</th>        
		<th class="col_heading level0 col2" >COLUMN_Z</th>    
	</tr>
 </thead>
 <tbody>
            <tr>
                        <th id="T_6cd4b_level0_row0" class="row_heading level0 row0" >0</th>
                        <td id="T_6cd4b_row0_col0" class="data row0 col0" >345</td>
                        <td id="T_6cd4b_row0_col1" class="data row0 col1" >18</td>
                        <td id="T_6cd4b_row0_col2" class="data row0 col2" >-31</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row1" class="row_heading level0 row1" >1</th>
                        <td id="T_6cd4b_row1_col0" class="data row1 col0" >845</td>
                        <td id="T_6cd4b_row1_col1" class="data row1 col1" >863</td>
                        <td id="T_6cd4b_row1_col2" class="data row1 col2" >431</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row2" class="row_heading level0 row2" >2</th>
                        <td id="T_6cd4b_row2_col0" class="data row2 col0" >290</td>
                        <td id="T_6cd4b_row2_col1" class="data row2 col1" >-62</td>
                        <td id="T_6cd4b_row2_col2" class="data row2 col2" >322</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row3" class="row_heading level0 row3" >3</th>
                        <td id="T_6cd4b_row3_col0" class="data row3 col0" >947</td>
                        <td id="T_6cd4b_row3_col1" class="data row3 col1" >698</td>
                        <td id="T_6cd4b_row3_col2" class="data row3 col2" >5</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row4" class="row_heading level0 row4" >4</th>
                        <td id="T_6cd4b_row4_col0" class="data row4 col0" >562</td>
                        <td id="T_6cd4b_row4_col1" class="data row4 col1" >825</td>
                        <td id="T_6cd4b_row4_col2" class="data row4 col2" >-53</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row5" class="row_heading level0 row5" >5</th>
                        <td id="T_6cd4b_row5_col0" class="data row5 col0" >79</td>
                        <td id="T_6cd4b_row5_col1" class="data row5 col1" >450</td>
                        <td id="T_6cd4b_row5_col2" class="data row5 col2" >949</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row6" class="row_heading level0 row6" >6</th>
                        <td id="T_6cd4b_row6_col0" class="data row6 col0" >809</td>
                        <td id="T_6cd4b_row6_col1" class="data row6 col1" >153</td>
                        <td id="T_6cd4b_row6_col2" class="data row6 col2" >-47</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row7" class="row_heading level0 row7" >7</th>
                        <td id="T_6cd4b_row7_col0" class="data row7 col0" >53</td>
                        <td id="T_6cd4b_row7_col1" class="data row7 col1" >450</td>
                        <td id="T_6cd4b_row7_col2" class="data row7 col2" >195</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row8" class="row_heading level0 row8" >8</th>
                        <td id="T_6cd4b_row8_col0" class="data row8 col0" >121</td>
                        <td id="T_6cd4b_row8_col1" class="data row8 col1" >793</td>
                        <td id="T_6cd4b_row8_col2" class="data row8 col2" >291</td>
            </tr>
            <tr>
                        <th id="T_6cd4b_level0_row9" class="row_heading level0 row9" >9</th>
                        <td id="T_6cd4b_row9_col0" class="data row9 col0" >352</td>
                        <td id="T_6cd4b_row9_col1" class="data row9 col1" >-97</td>
                        <td id="T_6cd4b_row9_col2" class="data row9 col2" >-95</td>
            </tr>
    </tbody>
</table>   

## List sessions for a record id

The wellbore DDMS provides an API that allows to list the sessions used to write data for a given WellLog record id.
The response returned by the API contains for each session some information as from which version the WellLog data have been written in the session.

```python
sessions_response = client.get(f'{welllog_dms_url}/{record_id}/sessions')
sessions_response.json()
```

    [{'id': '23854a8c-9051-48c2-b3f0-2a3c632f85fc',
      'recordId': 'data-partition-id:work-product-component--WellLog:30f8f5173cc444cca28582ee7814cc0d',
      'fromVersion': 1627640429377696,
      'mode': 'update',
      'expiry': '2021-07-31T10:20:32.187305',
      'createdTime': '2021-07-30T10:20:32.187305',
      'updatedTime': '2021-07-30T10:20:34.001277',
      'state': 'committed',
      'meta': None},
     {'id': 'd28ad3ff-30e2-40e1-ac96-a4efedd6b15e',
      'recordId': 'data-partition-id:work-product-component--WellLog:30f8f5173cc444cca28582ee7814cc0d',
      'fromVersion': 1627640429377696,
      'mode': 'update',
      'expiry': '2021-07-31T10:20:29.915170',
      'createdTime': '2021-07-30T10:20:29.915170',
      'updatedTime': '2021-07-30T10:20:31.832840',
      'state': 'committed',
      'meta': None}]

# Read bulk data<a name="read-bulk-data"></a>

As for writing it is possible to specify the format to be returned when reading WellLog bulk data.
This is done through the header passed to the GET http client request.

```python
headers = {
    'Accept': 'application/parquet' # 'application/parquet' | 'application/json'
}
```

## Read all data at once

The whole WellLog bulk data can be read in one API call as below:

```python
response = client.get(f'{welllog_dms_url}/{record_id}/data', headers=headers)
print_response(response)
create_df_from_response(response)
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
      <th>COLUMN_MD</th>
      <th>COLUMN_X</th>
      <th>COLUMN_Z</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>345</td>
      <td>18</td>
      <td>-31</td>
    </tr>
    <tr>
      <th>1</th>
      <td>845</td>
      <td>863</td>
      <td>431</td>
    </tr>
    <tr>
      <th>2</th>
      <td>290</td>
      <td>-62</td>
      <td>322</td>
    </tr>
    <tr>
      <th>3</th>
      <td>947</td>
      <td>698</td>
      <td>5</td>
    </tr>
    <tr>
      <th>4</th>
      <td>562</td>
      <td>825</td>
      <td>-53</td>
    </tr>
    <tr>
      <th>5</th>
      <td>79</td>
      <td>450</td>
      <td>949</td>
    </tr>
    <tr>
      <th>6</th>
      <td>809</td>
      <td>153</td>
      <td>-47</td>
    </tr>
    <tr>
      <th>7</th>
      <td>53</td>
      <td>450</td>
      <td>195</td>
    </tr>
    <tr>
      <th>8</th>
      <td>121</td>
      <td>793</td>
      <td>291</td>
    </tr>
    <tr>
      <th>9</th>
      <td>352</td>
      <td>-97</td>
      <td>-95</td>
    </tr>
  </tbody>
</table>
</div>



## Read single curves from the bulk

The GET WellLog data API allows you to pass the list of curves (WellLog data column names) to be returned into the response as follow:


```python
response = client.get(f'{welllog_dms_url}/{record_id}/data', params={'curves': 'COLUMN_MD,COLUMN_Z'}, headers=headers)
print_response(response)
create_df_from_response(response)
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
      <th>COLUMN_MD</th>
      <th>COLUMN_Z</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>345</td>
      <td>-31</td>
    </tr>
    <tr>
      <th>1</th>
      <td>845</td>
      <td>431</td>
    </tr>
    <tr>
      <th>2</th>
      <td>290</td>
      <td>322</td>
    </tr>
    <tr>
      <th>3</th>
      <td>947</td>
      <td>5</td>
    </tr>
    <tr>
      <th>4</th>
      <td>562</td>
      <td>-53</td>
    </tr>
    <tr>
      <th>5</th>
      <td>79</td>
      <td>949</td>
    </tr>
    <tr>
      <th>6</th>
      <td>809</td>
      <td>-47</td>
    </tr>
    <tr>
      <th>7</th>
      <td>53</td>
      <td>195</td>
    </tr>
    <tr>
      <th>8</th>
      <td>121</td>
      <td>291</td>
    </tr>
    <tr>
      <th>9</th>
      <td>352</td>
      <td>-95</td>
    </tr>
  </tbody>
</table>
</div>

## Read array columns from the bulk

For array data you can pass to the GET WellLog data API the name of the array and the column number between square bracket to specify which array columns you want to get returned into the response.

```python
response = client.get(f'{welllog_dms_url}/{record_2d_id}/data', params={'curves': '2D[0],2D[1]'}, headers=headers)
print_response(response)
create_df_from_response(response)
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
      <th>2D[0]</th>
      <th>2D[1]</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>676</td>
      <td>702</td>
    </tr>
    <tr>
      <th>1</th>
      <td>983</td>
      <td>588</td>
    </tr>
    <tr>
      <th>2</th>
      <td>948</td>
      <td>422</td>
    </tr>
    <tr>
      <th>3</th>
      <td>272</td>
      <td>-59</td>
    </tr>
    <tr>
      <th>4</th>
      <td>986</td>
      <td>869</td>
    </tr>
    <tr>
      <th>5</th>
      <td>563</td>
      <td>131</td>
    </tr>
    <tr>
      <th>6</th>
      <td>703</td>
      <td>31</td>
    </tr>
    <tr>
      <th>7</th>
      <td>375</td>
      <td>538</td>
    </tr>
    <tr>
      <th>8</th>
      <td>244</td>
      <td>416</td>
    </tr>
    <tr>
      <th>9</th>
      <td>761</td>
      <td>580</td>
    </tr>
    <tr>
      <th>10</th>
      <td>825</td>
      <td>222</td>
    </tr>
    <tr>
      <th>11</th>
      <td>174</td>
      <td>644</td>
    </tr>
    <tr>
      <th>12</th>
      <td>871</td>
      <td>857</td>
    </tr>
    <tr>
      <th>13</th>
      <td>880</td>
      <td>780</td>
    </tr>
    <tr>
      <th>14</th>
      <td>783</td>
      <td>883</td>
    </tr>
  </tbody>
</table>
</div>

## Additional filtering options to read bulk data

Some additional filtering options are available when reading WellLog bulk data as:
- offset: starting index from which the data have to be read from the WellLog bulk data
- limit: the maximum number of rows to be returned.

```python
response = client.get(f'{welllog_dms_url}/{record_id}/data', 
                      params={'limit': 4, 'offset': 4, 'curves': 'COLUMN_MD,COLUMN_Z'}, 
                      headers=headers)

print_response(response)
create_df_from_response(response)
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
      <th>COLUMN_MD</th>
      <th>COLUMN_Z</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>4</th>
      <td>562</td>
      <td>-53</td>
    </tr>
    <tr>
      <th>5</th>
      <td>79</td>
      <td>949</td>
    </tr>
    <tr>
      <th>6</th>
      <td>809</td>
      <td>-47</td>
    </tr>
    <tr>
      <th>7</th>
      <td>53</td>
      <td>195</td>
    </tr>
  </tbody>
</table>
</div>



# WellLog consistency rules<a name="welllog-consistency-rules"></a> 

## WellLog entity : Meta only (record) consistency

### Rules
see [WellLog schema](https://community.opengroup.org/osdu/data/data-definitions/-/blob/v0.14.0/E-R/work-product-component/WellLog.1.2.0.md).

- _rule 1_: Each `CurveID` listed in `data.Curves.CurveID` must be unique.

- _rule 2_: Ensure `data.ReferenceCurveID` exists in `data.Curves.CurveID` list.  


<details>
<summary>Example</summary>

wellog record:  
````json
{
"id": "...",
"data": {
  "ReferenceCurveID": "MD",
  "SamplingStart": 7627.0,
  "SamplingStopt": 7627.6,
  "Curves": [​
      {​
        "CurveID": "CSHG",​
        "Mnemonic": "CSHG",​
        "LogCurveFamilyID": "data-partition-id:reference-data--LogCurveFamily:Core%20Mercury%20Saturation:",​
        "NumberOfColumns": 4
      },​
      {​
        "CurveID": "MD",​
        "CurveUnit": "data-partition-id:reference-data--UnitOfMeasure:ft:",​
        "Mnemonic": "MD",​
        "LogCurveFamilyID": "data-partition-id:reference-data--LogCurveFamily:Measured%20Depth:",​
        "NumberOfColumns": 1​
      }​
  ],​
       
}
````


- _rule 1_: Each `Curves.CurveID` is unique, here `MD` and `CSHG`. 

- _rule 2_: `ReferenceCurveID` is set to `MD` and `MD` exists `Curves.CurveID` list.  

</details>

## WellLog entity : Meta data (record) & Bulk data consistency

WellLog record can exist without bulk data​.

### Rules

When bulk is added\edited following checks to be done :​

- _rule 3_:  Ensure `Curves.CurveID` listed in the record **match** the `column names` in the bulk​.

- _rule 4_:  For each curve, ensure that `NumberOfColumns` **matches** the `column` count in the bulk​ for this curve.

<details>
<summary>Example</summary>

WellLog bulk data:  

| DEPTH  | CSHG[0] | CSHG[1] | CSHG[2] | CSHG[3] |
|--------|---------|---------|---------|---------|
| **7627.0** | 0.573   | 0.573   | 0.573   | 0.573   |
| 7627.1 | 0.531   | 0.531   | 0.531   | 0.531   |
| 7627.2 | 0.653   | 0.653   | 0.653   | 0.653   |
| 7627.3 | 0.788   | 0.788   | 0.788   | 0.788   |
| 7627.4 | 0.034   | 0.034   | 0.034   | 0.034   |
| 7627.5 | 0.035   | 0.035   | 0.035   | 0.035   |
| **7627.6** | 0.607   | 0.607   | 0.607   | 0.607   |


using previous section well log record.
- _rule 3_:  `Curves.CurveID` list, `DEPTH` and `CSHG` matches the `column names` in the bulk​. Here `CSHG` is an array with 4 columns: CSHG[0], CSHG[1], CSHG[2], CSHG[3].

- _rule 4_:  `DEPTH.NumberOfColumns` **matches** the `column` count in the bulk​ ==> **1**.   `CSHG.NumberOfColumns` **matches** the `column` count in the bulk​ ==> **4**, CSHG[0], CSHG[1], CSHG[2], CSHG[3].
</details>

## Additional rules when the reference is type **"Measured Depth"**.

The following rules are only applied if the reference is type **"Measured Depth"**.

### Rules

- _rule 5_:  The values associated to the `ReferenceCurveID` in the record are monotonic​.

- _rule 6_:  The top and bottom bulk values associated to the `ReferenceCurveID` should match values `data.SamplingStart` and `data.SamplingStop` in the record.


<details>
<summary>Example</summary>

from previous record and bulk data: 

record:
````json
{
"id": "...",
"data": {
  "ReferenceCurveID": "MD",
  "SamplingStart": 7627.0,
  "SamplingStopt": 7627.6,
````

bulk:
| DEPTH  | ...     |
|--------|---------|
| **7627.0** |  ...    |
| 7627.1 |  ...    |
| 7627.2 |  ...    |
| 7627.3 |  ...    |
| 7627.4 |  ...    |
| 7627.5 |  ...    |
| **7627.6** |  ...    |


- _rule 5_:  The values associated to the `ReferenceCurveID`,`DEPTH`, are monotonic​: no duplicates, strictly increasing, no missing values.
- 
- _rule 6_:  `data.SamplingStart` matches bulk `DEPTH` top value ==> **7627.0**. `data.SamplingStop` matches bulk `DEPTH` bottom value ==> **7627.6**.

</details>



# WellboreTrajectory  consistency rules<a name="trajectory-consistency-rules"></a> 


## Wellbore trajectory entity : Meta only (record) consistency

### Rules
see [Wellbore trajectory schema](https://community.opengroup.org/osdu/data/data-definitions/-/blob/v0.14.0/E-R/work-product-component/WellboreTrajectory.1.1.0.md)
- _rule 1_: Each `Name` listed in `data.AvailableTrajectoryStationProperties.Name` must be unique.


<details>
<summary>Example</summary>

Wellbore trajectory record:  
````json
{
  "id": "...",
  "data": {
    "Name": "Index",
    "WellboreID": "data-partition-id:master-data--Wellbore:71612d776:",
    "TopDepthMeasuredDepth": 0.0,
    "AzimuthReferenceType": "data-partition-id:reference-data--AzimuthReferenceType:truenorth:",
    "BaseDepthMeasuredDepth": 7628.0,
    "AvailableTrajectoryStationProperties": [
      {
        "TrajectoryStationPropertyTypeID": "data-partition-id:reference-data--TrajectoryStationPropertyType:BOREHOLE_AZIMUTH:",
        "StationPropertyUnitID": "data-partition-id:reference-data--UnitOfMeasure:dega:",
        "Name": "BOREHOLE_AZIMUTH"
      },
      {
        "TrajectoryStationPropertyTypeID": "data-partition-id:reference-data--TrajectoryStationPropertyType:BOREHOLE_DEVIATION:",
        "StationPropertyUnitID": "qa-weu-des-prod-testing-eu:reference-data--UnitOfMeasure:dega:",
        "Name": "BOREHOLE_DEVIATION"
      },
      {
        "TrajectoryStationPropertyTypeID": "data-partition-id:reference-data--TrajectoryStationPropertyType:MD:",
        "StationPropertyUnitID": "data-partition-id:reference-data--UnitOfMeasure:ft:",
        "Name": "MD"
      }
    ]
  }
}
````


- _rule 1_: `AvailableTrajectoryStationProperties.Name` is unique, here `BOREHOLE_AZIMUTH`, `BOREHOLE_DEVIATION` and `MD`.

</details>

## Wellbore trajectory entity : Meta data (record) & Bulk data consistency

Wellbore trajectory record can exist without bulk data.

### Rules

When bulk is added\edited following checks to be done :

- _rule 2_:  Ensure `AvailableTrajectoryStationProperties.Name` listed in the record **match** the `column names` in the bulk.

<details>
<summary>Example</summary>

Wellbore trajectory bulk data:  

| MD  | BOREHOLE_AZIMUTH | BOREHOLE_DEVIATION |
|--------|---------|---------|
| **0.0**     | 360.573   | 0.573   |
| 0.5         | 360.531   | 0.531   |
| 1.0         | 360.653   | 0.653   |
| ...         | ...   | ...   |
| 7627.5      | 360.035   | 0.035   |
| **7628.0**  | 360.607   | 0.607   |


using previous section well log record.
- _rule 2_:  `AvailableTrajectoryStationProperties.Name` listed in the record **match** the `column names` in the bulk, 
here `BOREHOLE_AZIMUTH`, `BOREHOLE_DEVIATION` and `MD`.

</details>

## Additional rules in case of TrajectoryStationPropertyType:**MD**.

The following rules are only applied for TrajectoryStationPropertyType:**MD**.

### Rules

- _rule 3_:  The values associated to the reference in the record must be monotonic.

- _rule 4_:  The top and bottom bulk values associated to the reference should match values `data.TopDepthMeasuredDepth` and `data.BaseDepthMeasuredDepth` in the record.


<details>
<summary>Example</summary>

from previous record and bulk data: 

record:
````json
{
  "id": "...",
  "data": {
    "WellboreID": "data-partition-id:master-data--Wellbore:71612d776:",
    "TopDepthMeasuredDepth": 0.0,
    "BaseDepthMeasuredDepth": 7628.0,
````

bulk:
| MD  | ... |
|--------|---------|
| **0.0**     | ...   |
| 0.5         | ...   |
| ...         | ...   |
| 7627.5      | ...   |
| **7628.0**  | ...   |


- _rule 3_:  The values of `MD` are monotonic: no duplicates, strictly increasing, no missing values.

- _rule 4_:  `data.TopDepthMeasuredDepth` matches bulk `MD` top value ==> **0.0**. `data.BaseDepthMeasuredDepth`
matches bulk `MD` bottom value ==> **7628.0**.

</details>
