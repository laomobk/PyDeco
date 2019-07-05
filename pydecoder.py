from dis import opname, opmap
import utils
import error

#识别码
DEF_VAR = 1


class Source:
    def __init__(self):
        self.__lines = []
    
    def add_line(self, line):
        self.__lines.append(line)

    @property
    def line(self):
        return self.line

#识别给出的字节码的类型
class __CodeRecognizer:
    def __init__(self, codes, codeobj):
        '''
        codeobj : 目标函数的code object
        codes : 一个二维元祖，一组codes代表一行原始代码，每个元素代表一个字节码对 ((21, 0), (43, 1))
        
        '''
        self.__codes = codes
        self.__names = codeobj.co_names
        self.__consts = codeobj.co_consts
        self.__varnames = codeobj.co_varnames

    def __def_var(self):
        behavior = '{0} = {1}'
        codes = utils.get_side(self.__codes)
        
        if opmap['STORE_NAME'] not in codes and opmap['SETUP_LOOP'] in codes: #后者为了排除for循环
            return False

    #TODO:识别更多类型

class FuncDecomplier:
    def __init__(self, funcobj):
        self.__fobj = funcobj
        self.__code = funcobj.__code__
        self.__codes = utils.to_pairs(self.__code.co_code)
        self.__names = self.__code.co_names
        self.__consts = self.__code.co_consts
        self.__varnames = self.__code.co_varnames
        
        self.__HEAD = 'def {0}({1}):'.format(self.__fobj.__name__, ','.join(self.args))

    @property
    def args(self):
        return self.__code.co_varnames[:self.__code.co_argcount]

    def __split_bc_into_lines(self, codes :list, lnotab :list):  #PASS  2019/7/4
        '''
        code :　字节码对
        lnotab : co_lnotab 字段
        
        !!! 暂不支持出现单增量大于 255 的行号表
        '''
        tab = list(lnotab[2:])  #去除第一个偏移增量对(起始行)
        tab = utils.get_side(utils.to_pairs(tab)) #将行号表结成对取一边
        tab.append(len(codes) * 2 - sum(tab))  #增加最后一行的偏移增量

        tl = [] #总字节码序列
        ttl = [] #总序列中的子序列
        ofsi = tp = 0 #ofsi : 偏移增量  tp : 增量表的指针


        for cp in codes + [None]:  #加一个None, 防止越界
            if ofsi == tab[tp]:
                tl.append(ttl.copy())
                ttl = []
                tp += 1 #得到一行， 指针右移
                ofsi = 0 #将偏移增量设置为0
            ttl.append(cp)
            ofsi += 2 #将偏移增量增加 2 个 '字节' (一个PyByteCode占一个字节)
        
        return tl

    #@error.mayerr
    def __make_expr(self, pairs :tuple):
        '''
        pairs:用于生成表达式的字节码对
        '''
        stack = []  #虚拟栈
        #expr_stack = []  #用于存放临时表达式

        cmp = lambda code, name : code == opmap[name]  #匿名函数，方便比较
        
        for code, arg in pairs:
            #print(opname[code], '\t', arg)  #DEBUG :输出字节码
            if cmp(code, 'LOAD_CONST'):
                stack.append(self.__load_const(arg))
            
            elif code in (opmap['LOAD_NAME'], opmap['LOAD_GLOBAL']):
                stack.append(self.__load_name(arg))
            
            elif cmp(code, 'LOAD_FAST'):
                stack.append(self.__load_fast(arg))
            
            elif cmp(code, 'BINARY_ADD'):
                self.__make_arit_expr('+', stack)

            elif cmp(code, 'BINARY_MULTIPLY'):
                self.__make_arit_expr('*', stack)

            elif cmp(code, 'BINARY_TRUE_DIVIDE'):
                self.__make_arit_expr('/', stack)

            elif cmp(code, 'BINARY_FLOOR_DIVIDE'):
                self.__make_arit_expr('//', stack)
                
            elif cmp(code, 'BINARY_SUBTRACT'):
                self.__make_arit_expr('-', stack)

            elif cmp(code, 'BINARY_RSHIFT'):
                self.__make_arit_expr('>>', stack)
            
            elif cmp(code, 'BINARY_LSHIFT'):
                self.__make_arit_expr('<<', stack)

            elif cmp(code, 'BINARY_AND'):
                self.__make_arit_expr('&', stack)

            elif cmp(code, 'BINARY_XOR'):
                self.__make_arit_expr('^', stack)

            elif cmp(code, 'BINARY_OR'):
                self.__make_arit_expr('|', stack)
            
            elif cmp(code, 'BINARY_MODULO'):
                self.__make_arit_expr('%', stack)

            elif cmp(code, 'BINARY_POWER'):
                self.__make_arit_expr('**', stack)

            elif cmp(code, 'BINARY_MATRIX_MULTIPLY'):
                self.__make_arit_expr('@', stack)

            elif cmp(code, 'RETURN_VALUE'):
                #假装返回一波(滑稽)
                if len(stack) == 2:  #将 None 出栈，防止表达式是常数时候反编译出现异常
                    stack.pop()

            elif cmp(code, 'CALL_FUNCTION'):
                args = [str(stack.pop()) for i in range(arg)][::-1]  #逐个出栈，并翻转
                fname = stack.pop()
                #根据arg得知参数数量，用切片的方式获取从栈顶开始深arg的元素，再翻转
                beh = '{0}({1})'.format(fname, ', '.join(args))
                
                stack.append(beh)

            elif cmp(code, 'BUILD_SLICE'):
                if not arg:
                    return  #当arg是0时，是单纯索引

                args = [str(stack.pop()) for i in range(arg)][::-1]
                print(args)
                beh = 'slice({0})'.format(':'.join(args)) #切片的本质是实例化一个 slice 对象
                
                stack.append(beh)

            elif cmp(code, 'BINARY_SUBSCR'):
                argv = stack.pop()
                lname = stack.pop()
                beh = '{0}[{1}]'.format(lname, argv)

                stack.append(beh)

            elif cmp(code, 'POP_TOP'):
                pass  #这个就不管了，可能会pop掉一些很重要的东西

        #理论来说，一路下来，stack的长度应该是1
        if len(stack) != 1:
            raise error.DecomplierError('Expr-stack\'s length is not 1:\nExpr-Stack: '+str(stack))

        return stack.pop()

    def __make_arit_expr(self, operation, stack):
        a = stack.pop()
        b = stack.pop()

        #TODO : 优化什么时候加括号！
        beh = '({0} {2} {1})'.format(b, a, operation)
        stack.append(beh)

    def __load_const(self, index):
        c = self.__consts[index]
        if isinstance(c, str):
            return '"' + c + '"'

        return c

    def __load_fast(self, index):
        '''
        用于 LOAD_FAST
        '''
        return self.__varnames[index]

    def __load_name(self, index):
        '''
        用于 LOAD_NAME & LOAD_GLOBAL
        '''
        return self.__names[index]

    def test_split_bc_into_lines(self, c :list, tab :list):
        #测试接口
        return self.__split_bc_into_lines(c, tab)

    def test_make_expr(self, c :list):
        #测试接口
        return self.__make_expr(c)

def decode(codeobj):
    pass
