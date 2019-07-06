from dis import opname, opmap
import utils
import error

#识别码
DEF_VAR = 1


class Source:
    def __init__(self):
        self.__lines = []

    @property
    def line(self):
        return self.line
    
    def add_line(self, line):
        print(line)
        self.__lines.append(line)

    def export(self, fp='Untitled.py'):
        '''
        fp : 文件地址
        生成源码文件
        '''
        with open(fp, 'w') as f:
            for ln in self.__lines:
                f.write(ln)

#识别给出的字节码的类型
class CodeRecognizer:
    def __init__(self, codeobj):
        '''
        codeobj : 目标函数的code object
        '''
        self.__names = codeobj.co_names
        self.__consts = codeobj.co_consts
        self.__varnames = codeobj.co_varnames

    def __find_jump_fastest(self, codes :list):
        '''
        寻找在 POP_JUMP 中跳得最远的偏移量
        codes : 需要用来判断的字节码对
        '''
        scodes = utils.get_side(codes)
        cp = 0 #字节码对指针
        fest = 0 #最远的偏移量

        for c in scodes:
            if opname[c] in ('POP_JUMP_IF_TRUE', 'POP_JUMP_IF_FALSE',
                             'JUMP_IF_TRUE_OR_POP', 'JUMP_IF_FALSE_OR_POP'):
                if codes[cp][1] > fest:  #如果现偏移量大于原偏移量
                    fest = codes[cp][1]
            cp += 1

        if fest <= 0:
            raise error.DecomplierError('The jump target can not be 0')
        
        return fest

    def is_def_var(self, codes :list):
        '''
        codes: 字节码对
        '''
        codes = utils.get_side(codes)
        beh = '{0} = {1}'
        
        if opmap['STORE_NAME'] not in codes and opmap['SETUP_LOOP'] in codes: #后者为了排除for循环
            return False

        return True

    def is_return_expr(self, codes :list):
        '''
        codes: 字节码对
        '''
        scodes = utils.get_side(codes)

        if codes[-2:] == [(100, 0), (83, 0)] and len(codes) > 2:
            #为了排除隐式 return
            return False 

        if scodes[-1] != opmap['RETURN_VALUE']:
            #return 语句的 RETURN_VALUE 在最后
            return False

        return True

    def is_assert_expr(self, codes :list):
        '''
        codes: 字节码对
        '''
        #accert 无论如何都会压入一个AssertionError对象
        scodes = utils.get_side(codes)
        
        if opmap['LOAD_GLOBAL'] in scodes:
            tc = scodes[::-1]  #翻转，寻找最靠后的LOAD_GLOBAL
            ei = tc.index(opmap['LOAD_GLOBAL'])  #寻找最靠后的LOAD_GLOBAL的地址
            ti = codes[::-1][ei][1]  #颠倒字节码对数组，寻找目标字节码对，取出参数
            
            if self.__load_name(ti) == 'AssertionError':
                return True
            
            return False

    def is_if_expr(self, codes :list):
        '''
        codes: 字节码对
        '''
        pass


    #TODO:识别更多类型

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


class FuncDecomplier:
    def __init__(self, funcobj):
        self.__fobj = funcobj #函数对象
        self.__code = funcobj.__code__ #代码对象
        self.__codes = utils.to_pairs(self.__code.co_code) #字节码对
        self.__names = self.__code.co_names
        self.__consts = self.__code.co_consts
        self.__varnames = self.__code.co_varnames
        
        self.__HEAD = 'def {0}({1}):'.format(self.__fobj.__name__, ','.join(self.__args)) #函数头

        self.__reco = CodeRecognizer(self.__code)
        self.__source = Source()  #生成的源码文件

    @property
    def Head(self):
        return self.__HEAD

    @property
    def __args(self):
        return self.__code.co_varnames[:self.__code.co_argcount]

    def __deco_init(self):
        lcodes = self.__split_bc_into_lines(self.__codes, self.__code.co_lnotab)
        self.__make_like(locals)

    def __make_line(self, codes :list):
        '''
        codes : 所有已经分行的字节码对
        将反编译出来的行写入文件
        '''
        ln_index = 0  #行号索引
        

        for ln in codes:  #codes: 整个已分行co_code, ln : 每行
            if self.__reco.is_return_expr(ln): #如果是 return expr
                beh = 'return {0}'
                #开始处理 POP_TOP 以下， RETURN_VALUE 以上的字节码
                
                if opmap['POP_TOP'] in utils.get_side(ln):  #寻找行里是否有POP_TOP
                    lln = ln[::-1]  #将该字节码颠倒，开始寻找最靠后的POP_TOP
                    pti = lln.index(opmap['POP_TOP'])  #寻找最靠后的一个 POP_TOP
                    lln = lln[1:pti-1][::-1]  #得到RETURN_VALUE ~ POP_TOP之间的字节码，并翻转
                else:
                    #一般来说，如果没有POP_TOP， 那么这个return表达式就是独立的
                    lln = ln[:-1]

                expr = self.__make_expr(lln)  #生成return之后的表达式
                self.__source.add_line(beh.format(expr))  #将结果添加到源码文件
            
            elif self.__reco.is_assert_expr(ln):
                beh = 'assert {0}'
                #开始处理 LOAD_GLOBAL 以上的字节码对
                sc = utils.get_side(codes)[::-1]  #取出一边，并颠倒
                ci = sc.index(opmap['LOAD_GLOBAL'])
                cs = sc[ci:][::-1] #截取 LOAD_GLOBAL 以上的字节码对，并回正

                cond = self.__make_cond_expr(cs)  #取得条件表达式

                self.__source.add_line(beh.format(cond))  #将结果添加至源码行中

            ln_index += 1

    def __split_bc_into_lines(self, codes :list, lnotab :list):  #PASS  2019/7/4
        '''
        code :　字节码对
        lnotab : co_lnotab 字段
        
        !!! 暂不支持出现单行增量大于 255 的行号表
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

    def __make_cond_expr(self, pairs :list):
        '''
        pairs:用于生成表达式的字节码对
        
        用于生成条件表达式
        '''

        cmp = lambda code, name : code == opmap[name]  #匿名函数，方便比较
        cp = 0  #字节码对指针

        for code, arg in pairs:
            if cmp(code, ''):
                pass


            lnp += 1

    #@error.mayerr
    def __make_expr(self, pairs :list):  # PASS 2019/7/5
        '''
        pairs:用于生成表达式的字节码对
        '''
        stack = []  #虚拟栈
        #expr_stack = []  #用于存放临时表达式

        cp = 0  #字节码对指针

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
                if arg != 0:
                    #表达式的return一般为0，否则就奇了怪了
                    raise error.DecomplierError("Single expr's return argv must be 0.\nExpr-Stack: "+str(stack))

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

            elif cmp(code, 'UNARY_NOT'):
                tos = stack.pop()
                beh = 'not {0}'.format(tos)

                stack.append(beh)

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

    def test_reco(self, c: list):
        #测试接口
        return self.__reco.is_return_expr(c)

    def test_make_line(self, c: list):
        #测试接口
        return self.__make_line(c)

def decode(codeobj):
    pass
