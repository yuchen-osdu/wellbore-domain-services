# Copyright 2021 Schlumberger
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import app.model.model_curated as model
import pytest


def test_removing_root_value_as_number():
    json = '{"associations": null, ' \
           '"description": null, ' \
           '"format": null, ' \
           '"name": "testfloatvalue", ' \
           '"unitKey": null, ' \
           '"value": 456.0, ' \
           '"values": [123.0, 456.0]' \
           '}'
    my_model = model.namedProperty.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_value_as_string():
    json = '{"associations": null, ' \
           '"description": null, ' \
           '"format": null, ' \
           '"name": "teststringvalue", ' \
           '"unitKey": null, ' \
           '"value": "stringiam", ' \
           '"values": null' \
           '}'
    my_model = model.namedProperty.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_linestring():
    json = '{"bbox": null, ' \
           '"coordinates": [[1.1, 1.2], [2.1, 2.2]], ' \
           '"type": "LineString"' \
           '}'
    my_model = model.GeoJsonLineString.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_multilinestring():
    json = '{"bbox": null, ' \
           '"coordinates": [[[1.1, 1.2], [2.1, 2.2]], [[3.1, 3.2], [4.1, 4.2]]], ' \
           '"type": "MultiLineString"' \
           '}'
    my_model = model.GeoJsonMultiLineString.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_polygon_coords():
    json = '{"bbox": null, ' \
           '"coordinates": [[1.1, 1.2], [2.1, 2.2]], ' \
           '"type": "MultiPoint"' \
           '}'
    my_model = model.GeoJsonMultiPoint.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_polygon_points():
    json = '{"bbox": null, ' \
           '"coordinates": [[[1.1, 1.2], [2.1, 2.2]], [[3.1, 3.2], [4.1, 4.2]]], ' \
           '"type": "Polygon"' \
           '}'
    my_model = model.Polygon.parse_raw(json)
    result = my_model.json()
    assert (result == json)


def test_removing_root_polygon_array():
    json = '{"bbox": null, ' \
           '"coordinates": [[[[1.1, 1.2], [2.1, 2.2]], [[3.1, 3.2], [4.1, 4.2]]]], ' \
           '"type": "MultiPolygon"' \
           '}'
    my_model = model.GeoJsonMultiPolygon.parse_raw(json)
    result = my_model.json()
    assert (result == json)


@pytest.mark.parametrize("sub_type", [
    '{"bbox": null, "coordinates": [1.0, 2.1], "type": "Point"}',
    '{"bbox": null, "coordinates": [[1.0, 2.1]], "type": "MultiPoint"}',
    '{"bbox": null, "coordinates": [[1.0, 2.1]], "type": "LineString"}',
    '{"bbox": null, "coordinates": [[[1.0, 2.1]]], "type": "MultiLineString"}',
    '{"bbox": null, "coordinates": [[[1.0, 2.1]]], "type": "Polygon"}',
    '{"bbox": null, "coordinates": [[[[1.0, 2.1]]]], "type": "MultiPolygon"}',
])
def test_removing_root_GeoJsonFeatureGeometryItem(sub_type):
    json = '{"bbox": null, ' \
           f'"geometries": [{sub_type}], ' \
           '"type": "GeometryCollection"' \
           '}'
    my_model = model.geometryItem.parse_raw(json)
    result = my_model.json()
    assert (result == json)
