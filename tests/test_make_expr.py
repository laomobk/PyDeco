import sys
sys.path.append('..')

import pydecoder as pd

from tests.test_funcs import func_me

import utils

def test():
    fd = pd.FuncDecomplier(func_me)
    co = utils.to_pairs(list(func_me.__code__.co_code))
    return fd.test_make_expr(co)

import dis
#dis.dis(func_me)
print(test())