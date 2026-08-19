import pytest
from app.model.osdu_record_id import split_record_id_version


@pytest.mark.parametrize("input_str_id, expected_id, expected_version", [

    ('namespace:master-data--custom-type:c7c421a7:1', 'namespace:master-data--custom-type:c7c421a7', 1),
    ('namespace:master-data--custom-type:c7c421a7', 'namespace:master-data--custom-type:c7c421a7', None),

    # from previous tests cases
    ('opendes:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e:1234',
     'opendes:work-product-component--WellLog:713b4988cca14719867ae3b1004edf4e', 1234),

    ('opendes:work-product-component--WellboreTrajectory:713b4988cca14719867ae3:465',
     'opendes:work-product-component--WellboreTrajectory:713b4988cca14719867ae3', 465),

    ('data-partition:work-product-component--WellLog:713b4988cca14719867ae3b1004:16',
     'data-partition:work-product-component--WellLog:713b4988cca14719867ae3b1004', 16),

    ('9nlnBplxN:master-data--Well:g657DSIO',
     '9nlnBplxN:master-data--Well:g657DSIO', None),
    ('9nlnBplxN:master-data--Well:g657DSIO:',
     '9nlnBplxN:master-data--Well:g657DSIO', None),
    ('9nlnBplxN:master-data--Well:g657DSIO:1234',
     '9nlnBplxN:master-data--Well:g657DSIO', 1234),

    ('9nlnBplxN:master-data--Wellbore:g657DSIO',
     '9nlnBplxN:master-data--Wellbore:g657DSIO', None),
    ('9nlnBplxN:master-data--Wellbore:g657DSIO:',
     '9nlnBplxN:master-data--Wellbore:g657DSIO', None),
    ('9nlnBplxN:master-data--Wellbore:g657DSIO:1234',
     '9nlnBplxN:master-data--Wellbore:g657DSIO', 1234),

    ('9nlnBplxN:work-product-component--WellLog:g657DSIO',
     '9nlnBplxN:work-product-component--WellLog:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellLog:g657DSIO:',
     '9nlnBplxN:work-product-component--WellLog:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellLog:g657DSIO:1234',
     '9nlnBplxN:work-product-component--WellLog:g657DSIO', 1234),

    ('9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO',
     '9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO:',
     '9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO:1234',
     '9nlnBplxN:work-product-component--WellboreTrajectory:g657DSIO', 1234),

    ('9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO',
     '9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO:',
     '9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO', None),
    ('9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO:1234',
     '9nlnBplxN:work-product-component--WellboreMarkerSet:g657DSIO', 1234),
])
def test_split_record_id_version(input_str_id, expected_id, expected_version):
    assert split_record_id_version(input_str_id) == (expected_id, expected_version)


def test_split_record_id_version_straightly_return_invalid():
    assert split_record_id_version('') == (None, None)
    assert split_record_id_version(':::1324') == (None, None)
    assert split_record_id_version('invalid-record') == (None, None)
    assert split_record_id_version('invalid-record:123456') == (None, None)
