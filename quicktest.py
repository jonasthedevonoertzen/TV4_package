

feature_schema = {'nol': str, 'isl': list} #  'c_new': str, 'd_new': list

def aaa(key, value):
    if ((key in feature_schema.keys() and feature_schema[key] != list) or key.endswith('_new')) and isinstance(value, list):
        if len(value) > 1:
            raise ValueError("Expected at most one item in the list.")
        print(f'ran successfully: {key}')

aaa(key='nol', value='bla')
aaa(key='isl', value=['1', '2'])
aaa(key='isl', value='bla')
aaa(key='nol', value=['1'])
aaa(key='??', value=['blc'])
aaa(key='??_new', value=['blc'])
