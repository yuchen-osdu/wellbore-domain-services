import pandas as pd
import uuid
from datetime import datetime
from app.bulk_persistence.dask.session_file_meta import generate_chunk_filename, is_chunk_filename


def test_is_chunk_filename():
    assert is_chunk_filename(
        generate_chunk_filename(pd.DataFrame({'A': range(10), 'B': range(10)}, index=range(10)))
    )
    assert is_chunk_filename(
        generate_chunk_filename(pd.DataFrame({'A': range(10), 'B': range(10)}, index=range(10))) + '.parquet'
    )
    assert is_chunk_filename(generate_chunk_filename(pd.DataFrame({'A': [1], 'B': [1]}, index=[datetime.now()])))

    # should not match this case
    assert not is_chunk_filename(f'{uuid.uuid4()}.parquet')
