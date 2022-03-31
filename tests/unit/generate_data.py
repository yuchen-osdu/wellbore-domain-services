import numpy as np
import pandas as pd


def generate_df(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('date'):
            return (np.datetime64('2021-01-01') + days for days in range(size))
        if col_name.startswith('array_'):
            array_size = int(col_name.split('_')[1])
            return [np.array(np.random.random_sample(size=array_size)) for _i in range(size)]
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                       for c in columns}, index=index)
    return df

def generate_df_typed(columns, index):
    def gen_values(col_name, size):
        if col_name.startswith('float'):
            return np.random.random_sample(size=size)
        if col_name.startswith('str'):
            return [f'string_value_{i}' for i in range(size)]
        if col_name.startswith('bool'):
            return np.random.choice(a=[False, True], size=size)
        if col_name.startswith('date'):
            return (np.datetime64('2021-01-01') + days for days in range(size))
        return np.random.randint(-100, 1000, size=size)

    df = pd.DataFrame({c: gen_values(c, len(index))
                       for c in columns}, index=index)
    return df
