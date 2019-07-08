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

def merge(listA, listB):
    '''
    将listA， listB合并在一起，得到listC，例如：
    listA = [1,2,3]
    listB = [4,5,6]
    listC = [(1, 4), (2, 5), (3, 6)]
    如果listA, listB 的长度不相等，则在两个的长度中取最小值作为listC的长度
    '''
    ml = len(listA)  #listC的默认长度
    if len(listA) != len(listB):
        ml = min((len(listA), len(listB)))

    return [(listA[i], listB[i]) for i in range(ml)]
