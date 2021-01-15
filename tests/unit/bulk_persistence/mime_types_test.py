from app.bulk_persistence import MimeTypes
import pytest


def test_list_all_types():
    assert len(list(MimeTypes.types())) > 0


@pytest.mark.parametrize(
    "value,expected", [
        ('application/x-parquet', MimeTypes.PARQUET),
        ('APPLICATION/X-PARQUET', MimeTypes.PARQUET),
        ('application/parquet', MimeTypes.PARQUET),
        ('APPLICATION/PARQUET', MimeTypes.PARQUET),
        ('parquet', MimeTypes.PARQUET),
        ('.parquet', MimeTypes.PARQUET),
        ('PARQUET', MimeTypes.PARQUET),
        ('application/json', MimeTypes.JSON),
        ('application/messagepack', MimeTypes.MSGPACK)
    ])
def test_mime_from_valid_string(value, expected):
    assert MimeTypes.from_str(value) == expected


def test_mime_from_invalid_string():
    with pytest.raises(ValueError) as e:
        MimeTypes.from_str('unknown_type')
    assert 'unknown_type' in str(e.value)

