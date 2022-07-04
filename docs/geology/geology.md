# Wellbore DDMS Geology APIs


- [Introduction](#introduction) 
- [Schemas](#schemas) 
- [APIs](#apis)
  + [Sample data](#sample-data)
  + [Simple Create / Read session](#simple-create-read-session)


## Introduction<a name="introduction"></a>

The Wellbore DDMS Geology APIs let the user manage Markers related to a Wellbore, with CRUD APIs for MarkerSets. 


## Schemas<a name="schemas"></a>

The Wellbore DDMS Geology APIs support the OSDU [WellboreMarkerSet schema](https://community.opengroup.org/osdu/data/data-definitions/-/blob/v0.15.0/E-R/work-product-component/WellboreMarkerSet.1.1.0.md)


## APIs<a name="apis"></a>

[Wellbore DDMS Geology APIs specification](/solutions/osduwellboreddms/apis/geology-v3)

Those are generic Create Read Update Delete (CRUD) APIs to manage WellboreMarkerSet objects.

### Sample data<a name="sample-data"></a>

<details> 
    <summary> 
        Among the WellboreMarkerSet data fields are the WellboreID to which is is related, and a Markers array.
    </summary>

  "data": {
    "Name": "string",
    "Description": "string",
    "CreationDateTime": "2021-12-02T15:19:19.271000+00:00",
    "Tags": [
      "string"
    ],
    "SpatialPoint": {},
    "SpatialArea": {},
    "GeoContexts": [
      "string"
    ],
    "SubmitterName": "string",
    "BusinessActivities": [
      "string"
    ],
    "AuthorIDs": [
      "string"
    ],
    "LineageAssertions": [
      {
        "ID": "mydata:osdu:string:00001234",
        "LineageRelationshipType": "mydata:reference-data--LineageRelationshipType:string:"
      }
    ],
    "Artefacts": [
      {
        "RoleID": "mydata:reference-data--ArtefactRole:string:",
        "ResourceKind": "mydata:osdu:string:00001234",
        "ResourceID": "mydata:dataset--string:string:"
      }
    ],
    "IsExtendedLoad": true,
    "IsDiscoverable": true,
    "ResourceHomeRegionID": "mydata:reference-data--OSDURegion:string:",
    "ResourceHostRegionIDs": [
      "mydata:reference-data--OSDURegion:string:"
    ],
    "ResourceCurationStatus": "mydata:reference-data--ResourceCurationStatus:string:",
    "ResourceLifecycleStatus": "mydata:reference-data--ResourceLifecycleStatus:string:",
    "ResourceSecurityClassification": "mydata:reference-data--ResourceSecurityClassification:string:",
    "Source": "string",
    "ExistenceKind": "mydata:reference-data--ExistenceKind:string:",
    "WellboreID": "mydata:master-data--Wellbore:00001234:",
    "VerticalMeasurement": {},
    "AvailableMarkerProperties": [
      {
        "MarkerPropertyTypeID": "mydata:reference-data--MarkerPropertyType:MissingThickness:",
        "MarkerPropertyUnitID": "mydata:reference-data--UnitOfMeasure:ft:",
        "Name": "MissingThickness"
      }
    ],
    "Markers": [
      {
        "MarkerName": "string",
        "MarkerMeasuredDepth": 0.0,
        "MarkerSubSeaVerticalDepth": 0.0,
        "MarkerDate": "2021-12-02T15:19:19.271000+00:00",
        "MarkerObservationNumber": 0.0,
        "MarkerInterpreter": "string",
        "MarkerTypeID": "mydata:reference-data--MarkerType:string:",
        "FeatureTypeID": "mydata:reference-data--FeatureType:string:",
        "FeatureName": "string",
        "PositiveVerticalDelta": 0.0,
        "NegativeVerticalDelta": 0.0,
        "SurfaceDipAngle": 0.0,
        "SurfaceDipAzimuth": 0.0,
        "Missing": "string",
        "GeologicalAge": "string"
      }
    ],
    "ExtensionProperties": {}
  }

</details>

### Simple Create / Read session<a name="simple-create-read-session"></a>


```python
import requests
import json
```


```python
base_url="https://www.example.com/api/os-wellbore-ddms"
token = '****'
datapartitionid = 'mydata'
domain = 'example.com'
```

<details> 
    <summary> 
        Creating a WellboreMarkerSet record
    </summary>


```python
url = f"{base_url}/ddms/v3/wellboremarkersets"

payload = json.dumps([
  {
    "acl": {
      "owners": [
        f"data.default.owners@{datapartitionid}.{domain}"
      ],
      "viewers": [
        f"data.default.viewers@{datapartitionid}.{domain}"
      ]
    },
    "ancestry": {
      "parents": []
    },
    "createTime": "2020-12-16T11:46:20.163Z",
    "createUser": "some-user@some-company-cloud.com",
    "data": {
      "Artefacts": [
        {
          "ResourceID": f"{datapartitionid}:dataset--string:string:",
          "ResourceKind": f"{datapartitionid}:osdu:string:00001234",
          "RoleID": f"{datapartitionid}:reference-data--ArtefactRole:string:"
        }
      ],
      "AuthorIDs": [
        "string"
      ],
      "AvailableMarkerProperties": [
        {
          "MarkerPropertyTypeID": f"{datapartitionid}:reference-data--MarkerPropertyType:MissingThickness:",
          "MarkerPropertyUnitID": f"{datapartitionid}:reference-data--UnitOfMeasure:ft:",
          "Name": "MissingThickness"
        }
      ],
      "BusinessActivities": [
        "string"
      ],
      "CreationDateTime": "2021-12-02T15:19:19.271Z",
      "Description": "string",
      "ExistenceKind": f"{datapartitionid}:reference-data--ExistenceKind:string:",
      "ExtensionProperties": {},
      "GeoContexts": [
        "string"
      ],
      "IsDiscoverable": True,
      "IsExtendedLoad": True,
      "LineageAssertions": [
        {
          "ID": f"{datapartitionid}:osdu:string:00001234",
          "LineageRelationshipType": f"{datapartitionid}:reference-data--LineageRelationshipType:string:"
        }
      ],
      "Markers": [
        {
          "FeatureName": "string",
          "FeatureTypeID": f"{datapartitionid}:reference-data--FeatureType:string:",
          "GeologicalAge": "string",
          "MarkerDate": "2021-12-02T15:19:19.271Z",
          "MarkerInterpreter": "string",
          "MarkerMeasuredDepth": 0,
          "MarkerName": "string",
          "MarkerObservationNumber": 0,
          "MarkerSubSeaVerticalDepth": 0,
          "MarkerTypeID": f"{datapartitionid}:reference-data--MarkerType:string:",
          "Missing": "string",
          "NegativeVerticalDelta": 0,
          "PositiveVerticalDelta": 0,
          "SurfaceDipAngle": 0,
          "SurfaceDipAzimuth": 0
        }
      ],
      "Name": "string",
      "ResourceCurationStatus": f"{datapartitionid}:reference-data--ResourceCurationStatus:string:",
      "ResourceHomeRegionID": f"{datapartitionid}:reference-data--OSDURegion:string:",
      "ResourceHostRegionIDs": [
        f"{datapartitionid}:reference-data--OSDURegion:string:"
      ],
      "ResourceLifecycleStatus": f"{datapartitionid}:reference-data--ResourceLifecycleStatus:string:",
      "ResourceSecurityClassification": f"{datapartitionid}:reference-data--ResourceSecurityClassification:string:",
      "Source": "string",
      "SpatialArea": {},
      "SpatialPoint": {},
      "SubmitterName": "string",
      "Tags": [
        "string"
      ],
      "VerticalMeasurement": {},
      "WellboreID": f"{datapartitionid}:master-data--Wellbore:00001234:"
    },
    "id": f"{datapartitionid}:work-product-component--WellboreMarkerSet:00001234",
    "kind": "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
    "legal": {
      "legaltags": [
        f"{datapartitionid}-default-legal"
      ],
      "otherRelevantDataCountries": [
        "FR",
        "US"
      ]
    },
    "meta": [],
    "modifyTime": "2020-12-16T11:52:24.477Z",
    "modifyUser": "some-user@some-company-cloud.com",
    "tags": {
      "NameOfKey": "String value"
    },
    "version": 1562066009929332
  }
])
headers = {
  'data-partition-id': f'{datapartitionid}',
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {token}'
}

response = requests.request("POST", url, headers=headers, data=payload)

```

</details>

<details><summary>Query results</summary>



```python
print(json.dumps(response.json(), indent=2))

```

    {
      "recordCount": 1,
      "recordIdVersions": [
        "mydata:work-product-component--WellboreMarkerSet:00001234:1656929137041793"
      ],
      "recordIds": [
        "mydata:work-product-component--WellboreMarkerSet:00001234"
      ],
      "skippedRecordIds": []
    }
    

<details> 
    <summary> 
        Retrieving a WellboreMarkerSet record
    </summary>


```python
url = f"{base_url}/ddms/v3/wellboremarkersets/{datapartitionid}:work-product-component--WellboreMarkerSet:00001234"

payload={}
headers = {
  'data-partition-id': f'{datapartitionid}',
  'Authorization': f'Bearer {token}'
}

response = requests.request("GET", url, headers=headers, data=payload)

```

</details>

<details><summary>Query results</summary>


```python
print(json.dumps(response.json(), indent=2))
```

    {
      "id": "mydata:work-product-component--WellboreMarkerSet:00001234",
      "kind": "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
      "version": 1656929137041793,
      "acl": {
        "owners": [
          "data.default.owners@mydata.example.com"
        ],
        "viewers": [
          "data.default.viewers@mydata.example.com"
        ]
      },
      "legal": {
        "legaltags": [
          "mydata-default-legal"
        ],
        "otherRelevantDataCountries": [
          "FR",
          "US"
        ]
      },
      "tags": {
        "NameOfKey": "String value"
      },
      "createTime": "2021-12-16T15:20:59.752000+00:00",
      "createUser": "some-user@some-company-cloud.com",
      "modifyTime": "2022-07-04T10:05:37.050000+00:00",
      "modifyUser": "some-user@some-company-cloud.com",
      "meta": [],
      "data": {
        "Name": "string",
        "Description": "string",
        "CreationDateTime": "2021-12-02T15:19:19.271000+00:00",
        "Tags": [
          "string"
        ],
        "SpatialPoint": {},
        "SpatialArea": {},
        "GeoContexts": [
          "string"
        ],
        "SubmitterName": "string",
        "BusinessActivities": [
          "string"
        ],
        "AuthorIDs": [
          "string"
        ],
        "LineageAssertions": [
          {
            "ID": "mydata:osdu:string:00001234",
            "LineageRelationshipType": "mydata:reference-data--LineageRelationshipType:string:"
          }
        ],
        "Artefacts": [
          {
            "RoleID": "mydata:reference-data--ArtefactRole:string:",
            "ResourceKind": "mydata:osdu:string:00001234",
            "ResourceID": "mydata:dataset--string:string:"
          }
        ],
        "IsExtendedLoad": true,
        "IsDiscoverable": true,
        "ResourceHomeRegionID": "mydata:reference-data--OSDURegion:string:",
        "ResourceHostRegionIDs": [
          "mydata:reference-data--OSDURegion:string:"
        ],
        "ResourceCurationStatus": "mydata:reference-data--ResourceCurationStatus:string:",
        "ResourceLifecycleStatus": "mydata:reference-data--ResourceLifecycleStatus:string:",
        "ResourceSecurityClassification": "mydata:reference-data--ResourceSecurityClassification:string:",
        "Source": "string",
        "ExistenceKind": "mydata:reference-data--ExistenceKind:string:",
        "WellboreID": "mydata:master-data--Wellbore:00001234:",
        "VerticalMeasurement": {},
        "AvailableMarkerProperties": [
          {
            "MarkerPropertyTypeID": "mydata:reference-data--MarkerPropertyType:MissingThickness:",
            "MarkerPropertyUnitID": "mydata:reference-data--UnitOfMeasure:ft:",
            "Name": "MissingThickness"
          }
        ],
        "Markers": [
          {
            "MarkerName": "string",
            "MarkerMeasuredDepth": 0.0,
            "MarkerSubSeaVerticalDepth": 0.0,
            "MarkerDate": "2021-12-02T15:19:19.271000+00:00",
            "MarkerObservationNumber": 0.0,
            "MarkerInterpreter": "string",
            "MarkerTypeID": "mydata:reference-data--MarkerType:string:",
            "FeatureTypeID": "mydata:reference-data--FeatureType:string:",
            "FeatureName": "string",
            "PositiveVerticalDelta": 0.0,
            "NegativeVerticalDelta": 0.0,
            "SurfaceDipAngle": 0.0,
            "SurfaceDipAzimuth": 0.0,
            "Missing": "string",
            "GeologicalAge": "string"
          }
        ],
        "ExtensionProperties": {}
      }
    }
    

</details>
