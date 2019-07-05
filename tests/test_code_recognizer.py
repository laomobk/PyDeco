import sys
sys.path.append('..')

import pydecoder as pd

from tests.test_funcs import func_reco

import utils

import pprint

def test():
    fd = pd.FuncDecomplier(func_reco)
    co = func_reco.__code__.co_code
    co = utils.to_pairs(co)
    
    print(co)

    return fd.test_reco(co)

print(test())