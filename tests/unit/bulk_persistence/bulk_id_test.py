from app.bulk_persistence import BulkId
import uuid


def test_bulk_id_is_an_uuid():
    uuid.UUID(BulkId.new_bulk_id())

