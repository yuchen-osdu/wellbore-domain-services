# Log statistics


- [Introduction](#introduction)
- [Methodology](#methodology)


## Introduction <a name="introduction"></a>

[API specification](/solutions/wellboreddms/apis/osdu-wellbore-service#/Log/get_log_data_statistics_ddms_v2_logs__logid__statistics_get)

**Goal:** Provide statistical information for Bulk log data

**Use case 1:** Data consumers interested in specific statistics for specific log.

**Use case 2:** Data ingestors can use statistics as a method to ensure bulk data is transferred correctly to Wellbore DMS.

When transferring bulk data to Wellbore DMS it might happened that due to various reasons (human, system) 
the data is not transferred correctly and might not be discovered until the data is actually used. 
By launching the calculation on the application side and comparing the results from this service, 
you will be able to compare results quickly.

The method calculate the following statistics:
-   Count : Number of values (we exclude the missing value NaN)

-   Min & Max : smallest and largest values in this channel

-   Arithmetic Mean value & Standard deviation

-   Percentiles : 25%, 50% , 75%


## Methodology <a name="methodology"></a>

To calculate the statistics, the service use the method `describe` from the "Pandas" library.

Link: <https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.describe.html>

Example:

DataFrame Panda:

::   | **Ref** |  **col_1** |  **col_2** |  **col_3**
--- | --------- | ----------- | ----------- | -----------
  0  |  1.0  |     10        |  NaN        | 11
  1  |  1.5  |     58        |  20.0       | 21
  2  |  2    |     2         |  30.0       | 31

after using `describe` method:

::  |  **Ref**   |  **col_1**   |  **col_2**   |  **col_3**
--- | --------- | ----------- | ----------- | -----------
  count  |  3         |  3           |  2           |  3
  mean   |  1.5       |  23.333333   |  25          |  21
  std    |  0.5       |  30.287511   |  7.071068    |  10
  min    |  1         |  2           |  10          |  11
  25%    | 1.25       | 6            | 22.5         | 16
  50%    |  1.5       |  10          |  25          |  21
  75%    |  1.75      |  34          |  27.5        |  26
  max    |  2         |  58          |  30          |  31

Descriptive statistics include those that summarize the central
tendency, dispersion and shape of a dataset's distribution,
**excluding NaN values.**

For numeric data, the result's index will include **count, mean, std,
min, max** as well as lower, 50 and upper **percentiles**. By default
the lower percentile is 25 and the upper percentile is 75. The 50
percentile is the same as the median.

<https://www.w3resource.com/pandas/dataframe/dataframe-to_json.php>

Example with Curl:

**Curl** 

``` bash
curl -X GET "http://${host}/osdu/wdms/wellbore/v2/log/${logid}/statistics" -H  "accept: application/json" -H  "data-partition-id: ${data-partition-id}" -H  "Authorization: Bearer $TOKEN"
```
```json
{"Ref":{"count":3.0,"mean":1.5,"std":0.5,"min":1.0,"25%":1.25,"50%":1.5,"75%":1.75,"max":2.0},
"col_1":{"count":3.0,"mean":23.3333333333,"std":30.2875111776,"min":2.0,"25%":6.0,"50%":10.0,"75%":34.0,"max":58.0},
"col_2":{"count":2.0,"mean":25.0,"std":7.0710678119,"min":20.0,"25%":22.5,"50%":25.0,"75%":27.5,"max":30.0},
"col_3":{"count":3.0,"mean":21.0,"std":10.0,"min":11.0,"25%":16.0,"50%":21.0,"75%":26.0,"max":31.0}}
```

API response from the swagger :

**Stat API response** 
```json
{
  "Ref": {
    "count": 3,
    "mean": 1.5,
    "std": 0.5,
    "min": 1,
    "25%": 1.25,
    "50%": 1.5,
    "75%": 1.75,
    "max": 2
  },
  "col_1": {
    "count": 3,
    "mean": 23.3333333333,
    "std": 30.2875111776,
    "min": 2,
    "25%": 6,
    "50%": 10,
    "75%": 34,
    "max": 58
  },
  "col_2": {
    "count": 2,
    "mean": 25,
    "std": 7.0710678119,
    "min": 20,
    "25%": 22.5,
    "50%": 25,
    "75%": 27.5,
    "max": 30
  },
  "col_3": {
    "count": 3,
    "mean": 21,
    "std": 10,
    "min": 11,
    "25%": 16,
    "50%": 21,
    "75%": 26,
    "max": 31
  }
}
```