..  _model_curated:

Documentation for model_curated
===============================

Models Documentation

This contains documentation that we may not want to put in docstrings (exposed via openapi)

.. testsetup:: *
    :hide:
    >>> from pprint import pprint
    >>> from app.model.model_curated import *

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

Type_1
------

Type_2
------

Type_3
------

Type_4
------

GeoJsonMultiLineString
----------------------

Type_5
------

Type_6
------

Type_7
------

GeoJsonPoint
------------

Point3dNonGeoJson
-----------------

Type_8
------

Polygon
-------

valueArrayWithUnit
------------------

core_dl_geopoint
----------------

geographicPosition
------------------

PlssLocation
------------

projectedPosition
-----------------

wellborerelationships
---------------------

Shape
-----

WellborePurpose
---------------

WellboreStatus
--------------

WellboreType
------------

DataType
--------

Format
------

logsetrelationships
-------------------

dipsetrelationships
-------------------

DataType_1
----------

Format_1
--------

trajectorychannel
-----------------

trajectoryrelationships
-----------------------

wgs84Position
-------------

markerrelationships
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

wellrelationships
-----------------

DirectionWell
-------------

FluidWell
---------

WellLocationType
----------------

WellPurpose
-----------

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

.. doctest::

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

value also accepts a string

.. doctest::

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


logchannel
----------

logData
-------

log
---

SpatialFilter
-------------

geometryItem
------------

geometries field accepts various geojson geometries

.. doctest::

    >>> geometry_item = geometryItem(**{
    ...    "geometries": [{
    ...        "coordinates": [23.6, 34.65],
    ...        "type": 'Point'
    ...    }, {
    ...        "coordinates": [[1.0, 2.3], [23.6, 34.65]],
    ...        "type": 'MultiPoint'
    ...    }, {
    ...        "coordinates": [[1.0, 2.3], [23.6, 34.65]],
    ...        "type": 'LineString'
    ...    }, {
    ...        "coordinates": [
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],
    ...        "type": 'MultiLineString'
    ...    }, {
    ...        "coordinates": [
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],
    ...        "type": 'Polygon'
    ...    }, {
    ...        "coordinates": [[
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],[
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ]],
    ...        "type": 'MultiPolygon'
    ...    }],
    ...    "type": 'GeometryCollection',
    ... })
    >>> pprint(geometry_item.dict())
    {'bbox': None,
     'geometries': [{'bbox': None,
                     'coordinates': [23.6, 34.65],
                     'type': <Type_7.Point: 'Point'>},
                    {'bbox': None,
                     'coordinates': [[1.0, 2.3], [23.6, 34.65]],
                     'type': <Type_5.MultiPoint: 'MultiPoint'>},
                    {'bbox': None,
                     'coordinates': [[1.0, 2.3], [23.6, 34.65]],
                     'type': <Type_3.LineString: 'LineString'>},
                    {'bbox': None,
                     'coordinates': [[[1.0, 2.3], [23.6, 34.65]],
                                     [[5.678, 12.3], [223.4, 34.2]]],
                     'type': <Type_4.MultiLineString: 'MultiLineString'>},
                    {'bbox': None,
                     'coordinates': [[[1.0, 2.3], [23.6, 34.65]],
                                     [[5.678, 12.3], [223.4, 34.2]]],
                     'type': <Type_8.Polygon: 'Polygon'>},
                    {'bbox': None,
                     'coordinates': [[[[1.0, 2.3], [23.6, 34.65]],
                                      [[5.678, 12.3], [223.4, 34.2]]],
                                     [[[1.0, 2.3], [23.6, 34.65]],
                                      [[5.678, 12.3], [223.4, 34.2]]]],
                     'type': <Type_6.MultiPolygon: 'MultiPolygon'>}],
     'type': <Type.GeometryCollection: 'GeometryCollection'>}



GeoJsonFeature
--------------

geometry field accepts various geojson geometries

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [23.6, 34.65],
    ...        "type": 'Point'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [23.6, 34.65],
                  'type': <Type_7.Point: 'Point'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [[1.0, 2.3], [23.6, 34.65]],
    ...        "type": 'MultiPoint'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [[1.0, 2.3], [23.6, 34.65]],
                  'type': <Type_5.MultiPoint: 'MultiPoint'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [[1.0, 2.3], [23.6, 34.65]],
    ...        "type": 'LineString'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [[1.0, 2.3], [23.6, 34.65]],
                  'type': <Type_3.LineString: 'LineString'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],
    ...        "type": 'MultiLineString'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [[[1.0, 2.3], [23.6, 34.65]],
                                  [[5.678, 12.3], [223.4, 34.2]]],
                  'type': <Type_4.MultiLineString: 'MultiLineString'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],
    ...        "type": 'Polygon'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [[[1.0, 2.3], [23.6, 34.65]],
                                  [[5.678, 12.3], [223.4, 34.2]]],
                  'type': <Type_8.Polygon: 'Polygon'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry":  {
    ...        "coordinates": [[
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ],[
    ...             [[1.0, 2.3], [23.6, 34.65]],
    ...             [[5.678, 12.3], [223.4, 34.2]]
    ...        ]],
    ...        "type": 'MultiPolygon'
    ...    },
    ...    "properties": {},
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [[[[1.0, 2.3], [23.6, 34.65]],
                                   [[5.678, 12.3], [223.4, 34.2]]],
                                  [[[1.0, 2.3], [23.6, 34.65]],
                                   [[5.678, 12.3], [223.4, 34.2]]]],
                  'type': <Type_6.MultiPolygon: 'MultiPolygon'>},
     'properties': {},
     'type': <Type_1.Feature: 'Feature'>}

properties accepts a dict with string keys and any kind of value

.. doctest::

    >>> geojson_feature = GeoJsonFeature(**{
    ...    "geometry": {
    ...        "coordinates": [23.6, 34.65],
    ...        "type": 'Point'
    ...    },
    ...    "properties": {
    ...        "prop_key_1": [1, "toto", 3, 4, {"some_dict_key": "some_dict_value"}]
    ...    },
    ...    "type": 'Feature',
    ... })
    >>> pprint(geojson_feature.dict())
    {'bbox': None,
     'geometry': {'bbox': None,
                  'coordinates': [23.6, 34.65],
                  'type': <Type_7.Point: 'Point'>},
     'properties': {'prop_key_1': [1,
                                   'toto',
                                   3,
                                   4,
                                   {'some_dict_key': 'some_dict_value'}]},
     'type': <Type_1.Feature: 'Feature'>}

GeoJsonFeatureCollection
------------------------

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
