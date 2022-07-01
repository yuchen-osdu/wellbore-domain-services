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

```
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
        "ID": "opendes:osdu:string:00001234",
        "LineageRelationshipType": "opendes:reference-data--LineageRelationshipType:string:"
      }
    ],
    "Artefacts": [
      {
        "RoleID": "opendes:reference-data--ArtefactRole:string:",
        "ResourceKind": "opendes:osdu:string:00001234",
        "ResourceID": "opendes:dataset--string:string:"
      }
    ],
    "IsExtendedLoad": true,
    "IsDiscoverable": true,
    "ResourceHomeRegionID": "opendes:reference-data--OSDURegion:string:",
    "ResourceHostRegionIDs": [
      "opendes:reference-data--OSDURegion:string:"
    ],
    "ResourceCurationStatus": "opendes:reference-data--ResourceCurationStatus:string:",
    "ResourceLifecycleStatus": "opendes:reference-data--ResourceLifecycleStatus:string:",
    "ResourceSecurityClassification": "opendes:reference-data--ResourceSecurityClassification:string:",
    "Source": "string",
    "ExistenceKind": "opendes:reference-data--ExistenceKind:string:",
    "WellboreID": "opendes:master-data--Wellbore:00001234:",
    "VerticalMeasurement": {},
    "AvailableMarkerProperties": [
      {
        "MarkerPropertyTypeID": "opendes:reference-data--MarkerPropertyType:MissingThickness:",
        "MarkerPropertyUnitID": "opendes:reference-data--UnitOfMeasure:ft:",
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
        "MarkerTypeID": "opendes:reference-data--MarkerType:string:",
        "FeatureTypeID": "opendes:reference-data--FeatureType:string:",
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
```
</details>

### Simple Create / Read session<a name="simple-create-read-session"></a>


```python
import requests
import json
```


```python
base_url="https://evd.managed-osdu.cloud.slb-ds.com/api/os-wellbore-ddms"
token = '****'
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
        "data.default.owners@opendes.enterprisedata.cloud.slb-ds.com"
      ],
      "viewers": [
        "data.default.viewers@opendes.enterprisedata.cloud.slb-ds.com"
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
          "ResourceID": "opendes:dataset--string:string:",
          "ResourceKind": "opendes:osdu:string:00001234",
          "RoleID": "opendes:reference-data--ArtefactRole:string:"
        }
      ],
      "AuthorIDs": [
        "string"
      ],
      "AvailableMarkerProperties": [
        {
          "MarkerPropertyTypeID": "opendes:reference-data--MarkerPropertyType:MissingThickness:",
          "MarkerPropertyUnitID": "opendes:reference-data--UnitOfMeasure:ft:",
          "Name": "MissingThickness"
        }
      ],
      "BusinessActivities": [
        "string"
      ],
      "CreationDateTime": "2021-12-02T15:19:19.271Z",
      "Description": "string",
      "ExistenceKind": "opendes:reference-data--ExistenceKind:string:",
      "ExtensionProperties": {},
      "GeoContexts": [
        "string"
      ],
      "IsDiscoverable": True,
      "IsExtendedLoad": True,
      "LineageAssertions": [
        {
          "ID": "opendes:osdu:string:00001234",
          "LineageRelationshipType": "opendes:reference-data--LineageRelationshipType:string:"
        }
      ],
      "Markers": [
        {
          "FeatureName": "string",
          "FeatureTypeID": "opendes:reference-data--FeatureType:string:",
          "GeologicalAge": "string",
          "MarkerDate": "2021-12-02T15:19:19.271Z",
          "MarkerInterpreter": "string",
          "MarkerMeasuredDepth": 0,
          "MarkerName": "string",
          "MarkerObservationNumber": 0,
          "MarkerSubSeaVerticalDepth": 0,
          "MarkerTypeID": "opendes:reference-data--MarkerType:string:",
          "Missing": "string",
          "NegativeVerticalDelta": 0,
          "PositiveVerticalDelta": 0,
          "SurfaceDipAngle": 0,
          "SurfaceDipAzimuth": 0
        }
      ],
      "Name": "string",
      "ResourceCurationStatus": "opendes:reference-data--ResourceCurationStatus:string:",
      "ResourceHomeRegionID": "opendes:reference-data--OSDURegion:string:",
      "ResourceHostRegionIDs": [
        "opendes:reference-data--OSDURegion:string:"
      ],
      "ResourceLifecycleStatus": "opendes:reference-data--ResourceLifecycleStatus:string:",
      "ResourceSecurityClassification": "opendes:reference-data--ResourceSecurityClassification:string:",
      "Source": "string",
      "SpatialArea": {},
      "SpatialPoint": {},
      "SubmitterName": "string",
      "Tags": [
        "string"
      ],
      "VerticalMeasurement": {},
      "WellboreID": "opendes:master-data--Wellbore:00001234:"
    },
    "id": "opendes:work-product-component--WellboreMarkerSet:00001234",
    "kind": "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
    "legal": {
      "legaltags": [
        "opendes-default-legal"
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
  'data-partition-id': 'opendes',
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
        "opendes:work-product-component--WellboreMarkerSet:00001234:1656685178752952"
      ],
      "recordIds": [
        "opendes:work-product-component--WellboreMarkerSet:00001234"
      ],
      "skippedRecordIds": []
    }
    

</details>

<details> 
    <summary> 
        Retrieving a WellboreMarkerSet record
    </summary>


```python
url = f"{base_url}/ddms/v3/wellboremarkersets/opendes:work-product-component--WellboreMarkerSet:00001234"

payload={}
headers = {
  'data-partition-id': 'opendes',
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
      "id": "opendes:work-product-component--WellboreMarkerSet:00001234",
      "kind": "osdu:wks:work-product-component--WellboreMarkerSet:1.1.0",
      "version": 1656685178752952,
      "acl": {
        "owners": [
          "data.default.owners@opendes.enterprisedata.cloud.slb-ds.com"
        ],
        "viewers": [
          "data.default.viewers@opendes.enterprisedata.cloud.slb-ds.com"
        ]
      },
      "legal": {
        "legaltags": [
          "opendes-default-legal"
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
      "createUser": "lyriarte@slb.com",
      "modifyTime": "2022-07-01T14:19:48.151000+00:00",
      "modifyUser": "lyriarte@slb.com",
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
            "ID": "opendes:osdu:string:00001234",
            "LineageRelationshipType": "opendes:reference-data--LineageRelationshipType:string:"
          }
        ],
        "Artefacts": [
          {
            "RoleID": "opendes:reference-data--ArtefactRole:string:",
            "ResourceKind": "opendes:osdu:string:00001234",
            "ResourceID": "opendes:dataset--string:string:"
          }
        ],
        "IsExtendedLoad": true,
        "IsDiscoverable": true,
        "ResourceHomeRegionID": "opendes:reference-data--OSDURegion:string:",
        "ResourceHostRegionIDs": [
          "opendes:reference-data--OSDURegion:string:"
        ],
        "ResourceCurationStatus": "opendes:reference-data--ResourceCurationStatus:string:",
        "ResourceLifecycleStatus": "opendes:reference-data--ResourceLifecycleStatus:string:",
        "ResourceSecurityClassification": "opendes:reference-data--ResourceSecurityClassification:string:",
        "Source": "string",
        "ExistenceKind": "opendes:reference-data--ExistenceKind:string:",
        "WellboreID": "opendes:master-data--Wellbore:00001234:",
        "VerticalMeasurement": {},
        "AvailableMarkerProperties": [
          {
            "MarkerPropertyTypeID": "opendes:reference-data--MarkerPropertyType:MissingThickness:",
            "MarkerPropertyUnitID": "opendes:reference-data--UnitOfMeasure:ft:",
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
            "MarkerTypeID": "opendes:reference-data--MarkerType:string:",
            "FeatureTypeID": "opendes:reference-data--FeatureType:string:",
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
