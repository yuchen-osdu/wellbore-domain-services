Documentation for model_curated
===============================

This contains documentation that we may not want to put in docstrings (exposed via openapi)

Necessary setup to verify code with doctest:

```
>>> from pprint import pprint
>>> from app.model.model_curated import *

```

Tags
----

DDMSBaseModel
-------------

DDMSBaseModelWithExtra
----------------------

LinkList
--------

Kind
----

MetaItem
--------

DDMSBaseRecord
--------------

Point
-----

Legal
-----

TagDictionary
-------------

ToOneRelationship
-----------------

ValueWithUnit
-------------

Type
----

Polygon
-------

DataType
--------

Format
------

dipsetrelationships
-------------------

DataType_2
----------

Format_2
--------

historyRecord
-------------

ReferenceType
-------------

logRelationships
----------------

basinContext
------------

WellStatus
----------

WellType
--------

ByBoundingBox
-------------

ByDistance
----------

ByGeoPolygon
------------

SimpleElevationReference
------------------------

GeoJsonLineString
-----------------

GeoJsonMultiPoint
-----------------

GeoJsonMultiPolygon
-------------------

namedProperty
-------------

namedProperty Model

value accepts a float

```
>>> from pprint import pprint
>>> named_property = namedProperty(**{
...     "value": 42.0
... })
>>> pprint(named_property.dict())
{'associations': None,
 'description': None,
 'format': None,
 'name': None,
 'unitKey': None,
 'value': 42.0,
 'values': None}
 
```


value accepts an int

```
>>> from pprint import pprint
>>> named_property = namedProperty(**{
...     "value": 42
... })
>>> pprint(named_property.dict())
{'associations': None,
 'description': None,
 'format': None,
 'name': None,
 'unitKey': None,
 'value': 42,
 'values': None}
 
```

value also accepts a string

```
>>> named_property = namedProperty(**{
...     "value": "Lorem Ipsum"
... })
>>> pprint(named_property.dict())
{'associations': None,
 'description': None,
 'format': None,
 'name': None,
 'unitKey': None,
 'value': 'Lorem Ipsum',
 'values': None}
 
```

Note different types of values for other fields are accepted, and coerced to string

```
>>> named_property = namedProperty(**{
...     "associations": [1,2,3],
...     "description": 51,
...     "format": 33,
...     "name": 42,
...     "unitKey": 5
... })
>>> pprint(named_property.dict())
{'associations': ['1', '2', '3'],
 'description': '51',
 'format': '33',
 'name': '42',
 'unitKey': '5',
 'value': None,
 'values': None}
 
```


logchannel
----------

logData
-------

log
---

SpatialFilter
-------------

wellboreData
------------

wellbore
--------

channel
-------

logSetData
----------

dipSetData
----------

logset
------

dipset
------

trajectoryData
--------------

trajectory
----------

markerData
----------

marker
------

wellData
--------

well
----
