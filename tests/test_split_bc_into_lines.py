import sys
sys.path.append('..')

import pydecoder as pd

from tests.test_funcs import func_me

import utils

def test():
    fd = pd.FuncDecomplier(func_me)

    c = func_me.__code__
    
    co = c.co_code
    co = utils.to_pairs(co)

    res = fd.test_split_bc_into_lines(co, c.co_lnotab)

    return res
    #return (res, utils.to_pairs(list(func_sbil.__code__.co_code)))

import pprint
import dis

res = test()
print('Total lines: ', len(res))
pprint.pprint(res)
dis.dis(func_me)
