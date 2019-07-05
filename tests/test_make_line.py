import sys
sys.path.append('..')

import pydecoder as pd

from tests.test_funcs import func_ml

import utils

import pprint

def test():
    fd = pd.FuncDecomplier(func_ml)

    co = func_ml.__code__.co_code
    co = utils.to_pairs(co)
    co = fd.test_split_bc_into_lines(co, func_ml.__code__.co_lnotab)

    return fd.test_make_line(co)

print(test())