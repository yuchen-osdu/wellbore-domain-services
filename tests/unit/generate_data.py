import numpy as np
import pandas as pd


def generate_df(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('bool'):
            return np.random.choice(a=[False, True], size=size)
        if col_name.startswith('date'):
            return pd.date_range(start='1/1/2022', freq='us', periods=size)
        if col_name.startswith('array_'):
            array_size = int(col_name.split('_')[1])
            return [np.array(np.random.random_sample(size=array_size)) for _i in range(size)]

        return np.random.randint(-100, 1000, size=size)

    return pd.DataFrame({c: gen_values(c, len(index)) for c in columns}, index=index)
