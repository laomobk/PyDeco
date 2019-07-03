from dis import opname, opmap
import utils

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

    def args(self):
        return self.__code.co_varnames[:self.__code.co_argcount]

    def split_line(self, codes:tuple):
        pass #TODO:将字节码分割成一行一行

    def __make_expr(self, pairs:tuple):
        '''
        pairs:用于生成表达式的字节码对
        '''
        stack = []  #虚拟栈
        #expr_stack = []  #用于存放临时表达式

        cmp = lambda code, name : code == opmap[name]  #匿名函数，方便比较
        
        for code, arg in pairs:
            if cmp(code, 'LOAD_CONST'):
                stack.append(self.load_const(arg))
            
            elif code in (opmap['LOAD_NAME'], opmap['LOAD_GLOBAL']):
                stack.append(self.load_name(arg))
            
            elif cmp(code, 'LOAD_FAST'):
                stack.append(self.load_fast(arg))
            
            elif cmp(code, 'BINARY_ADD'):
                self.__make_arit_expr('+')

            elif cmp(code, 'BINARY_MULTIPLY'):
                self.__make_arit_expr('*')

            elif cmp(code, 'BINARY_TRUE_DIVIDE'):
                self.__make_arit_expr('/')

            elif cmp(code, 'BINARY_FLOOR_DIVIDE'):
                self.__make_arit_expr('//')
                
            elif cmp(code, 'BINARY_SUBTRACT'):
                self.__make_arit_expr('-')

            elif cmp(code, 'BINARY_RSHIFT'):
                self.__make_arit_expr('>>')
            
            elif cmp(code, 'BINARY_LSHIFT'):
                self.__make_arit_expr('<<')

            elif cmp(code, 'BINARY_AND'):
                self.__make_arit_expr('&')

            elif cmp(code, 'BINARY_XOR'):
                self.__make_arit_expr('^')

            elif cmp(code, 'BINARY_OR'):
                self.__make_arit_expr('|')
            
            elif cmp(code, 'BINARY_MODULO'):
                self.__make_arit_expr('%')

            elif cmp(code, 'BINARY_POWER'):
                self.__make_arit_expr('**')

            elif cmp(code, 'BINARY_MATRIX_MULTIPLY'):
                self.__make_arit_expr('@')


            elif cmp(code, 'CALL_FUNCTION'):
                args  = stack[:arg][-1] 
                fname = stack.pop()
                #根据arg得知参数数量，用切片的方式获取从栈顶开始深arg的元素，再翻转
                beh = '{0}({1})'.format(fname, ','.join(args))
                stack.append(beh)

        #理论来说，一路下来，stack的长度应该是1
        if len(stack) != 1:
            import error
            raise error.DecomplierError('Expr-stack\'s length is not 1:\n\tExpr-Stack:'+str(stack))

        return stack.pop()

    def __make_arit_expr(self, operation, stack):
        a = stack.pop()
        b = stack.pop()

        beh = '{0} {2} {1}'.format(b, a)
        stack.append(beh)

    def load_const(self, index):
        c = self.__consts[index]
        
        if isinstance(c, str):
            return '"' + c + '"'

        return c

    def load_fast(self, index):
        '''
        用于 LOAD_FAST
        '''
        return self.__varnames[index]

    def load_name(self, index):
        '''
        用于 LOAD_NAME & LOAD_GLOBAL
        '''
        return self.__names[index]

def decode(codeobj):
    pass
