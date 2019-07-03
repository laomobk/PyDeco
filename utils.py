def get_side(li):
    '''
    对于一个二维数组，取每个元素的第零个元素
    '''

    return [el[0] for el in li]


def to_pairs(li):
    temp = list()
    for i in range(0, len(li) - 1, 2):
        temp.append((li[i], li[i + 1]))

    return temp