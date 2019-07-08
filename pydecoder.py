from dis import opname, opmap, cmp_op
import utils
import error

def sth_in(target, *sth):
    '''
    助手函数, 返回target里面是否有sth
    如果sth是个元则target中只要有一个sth中的元素就返回True
    '''
    for obj in sth:
        if obj in target:
            return True
    
    return False

def opall(*opnames):
    cs = []  #用于返回的字节码
    
    for name in opnames:
        cs.append(opmap[name])
    
    return cs

class Source:
    def __init__(self):
        self.__lines = []

    @property
    def line(self):
        return self.line
    
    def add_line(self, line, level = 0):
        print(('\t'*level) + line)
        self.__lines.append(('\t'*level) + line)

    def export(self, fp='Untitled.py'):
        '''
        fp : 文件地址
        生成源码文件
        '''
        with open(fp, 'w') as f:
            for ln in self.__lines:
                f.write(ln + '\n')

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
        
        if (opmap['STORE_NAME'] in codes or opmap['STORE_FAST'] in codes) \
                and opmap['IMPORT_NAME'] not in codes and opmap["SETUP_LOOP"] not in codes:
            return True
        
        return False

    def is_def_attr(self, codes : list):
        '''
        codes: 字节码对
        '''
        scodes = utils.get_side(codes)

        if opmap in opmap['STORE_ATTR'] and opmap["SETUP_LOOP"] not in scodes:
            return True
        return False

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
        !!!暂不支持单行 if 语句
        '''
        #fest = self.__find_jump_fastest(codes) #寻找最远的偏移量

        '''
        python 的 and or 表达式经过了很好的优化，但是，对于反编译来说，这是个噩梦！！！
        我甚至用了2天的时间来找python对于and or语句的规律，例如整个表达式的结束。
        但值得我欣慰的是，它只是一个表达式！！！！
        '''

        scodes = utils.get_side(codes)
        if opname[scodes[-1]] in ('POP_JUMP_IF_FALSE', 'POP_JUMP_IF_TRUE'):
            #如果最后是 POP_JUMP_IF_FALSE 或 POP_JUMP_IF_TRUE，就判断是 if 语句
            return True

        return False

    def is_import_expr(self, code :list):
        '''
        codes: 字节码对
        '''
        scodes = utils.get_side(code)

        if opmap['IMPORT_NAME'] in scodes:
            return True
        return False


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

        self.__level = 0  #代码缩进级别

        self.__source.add_line(self.Head)
        self.__level += 1

    @property
    def Head(self):
        return self.__HEAD

    @property
    def __args(self):
        return self.__code.co_varnames[:self.__code.co_argcount]

    def __deco_init(self):
        lcodes = self.__split_bc_into_lines(self.__codes, self.__code.co_lnotab)
        self.__make_line(lcodes)

    def __add_line(self, line):
        self.__source.add_line(line, self.__level)

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
                self.__add_line(beh.format(expr))  #将结果添加到源码文件
            
            elif self.__reco.is_assert_expr(ln):
                beh = 'assert {0}'
                hsn = False #如果assert后面出现了not
                #开始处理 LOAD_GLOBAL 以上的字节码对
                sc = utils.get_side(ln)[::-1]  #取出一边，并颠倒
                try:
                    ci = sc.index(opmap['POP_JUMP_IF_TRUE'])
                    #如果assert后面出现not，则应该是POP_JUMP_IF_FALSE
                except ValueError:
                    hsn = True
                    ci = ci = sc.index(opmap['POP_JUMP_IF_FALSE'])

                ci += 1  #不包括POP_JUMP_IF_XXXX 指令

                cs = ln[::-1][ci:][::-1] #截取 POP_JUMP_IF_FALSE 以上的字节码对
                cond = self.__make_expr(cs)  #取得表达式

                self.__add_line(
                    beh.format(
                        ('not ' if hsn else '') + cond))  #将结果添加至源码行中,如果hsn，则将'not '加入
                
            elif self.__reco.is_def_var(ln):
                isf = False  #如果是STORE_FAST
                beh = '{0} = {1}'
                #处理STORE_XXX以上的字节码
                
                rc = utils.get_side(ln) #取出一边
                
                try:
                    ci = rc.index(opmap['STORE_NAME'])  #找到STORE_NAME的位置
                except ValueError:
                    #当是STORE_FAST的时候
                    isf = True
                    ci = rc.index(opmap['STORE_FAST'])  #找到STORE_FAST的位置

                exprcs = ln[:ci]  #截取STORE_XXX以上的字节码
                expr = self.__make_expr(exprcs)  #生成表达式
                argv = ln[ci][1] #得到 STORE_XXX 的参数

                if not isf:
                    name = self.__load_name(argv)  #根据参数，得到变量名
                else:
                    name = self.__load_fast(argv)  #根据参数，得到变量名

                self.__add_line(beh.format(name, expr))

            elif self.__reco.is_def_attr(ln):
                pass

            elif self.__reco.is_import_expr(ln):
                behn = 'import {0}'  #简单import
                behf = 'from {0} import {1}' #from import

                has = False #是否拥有as
                hsf = False #是否是from import

                isfast = False #如果是LOAD_FAST

                '''
                as 其实不用省略，因为 import os => import os as os
                但是为了人性化，还是选择省略
                '''
                #处理 STORE_NAME 以上的字节码
                
                sln = utils.get_side(ln)[::-1]
                try:
                    ci = sln.index(opmap['STORE_FAST'])  #如果是在函数/方法里面import
                except ValueError:
                    ci = sln.index(opmap['STORE_NAME'])  #在global域import

                cs = ln[::-1][ci+1:][::-1]  #截取ci以上的字节码，然后回正
                scs = utils.get_side(cs)

                #开始处理ci以上的字节码
                if opmap['IMPORT_STAR'] in scs:  #如果是from xx import *
                    #尽管 from xx import * 不允许出现在函数中
                    imp_ni = scs.index(opmap['IMPORT_NAME'])
                    imp_name = self.__load_name(ln[imp_ni][1])

                    self.__add_line(behf.format(imp_name, '*'))
                elif opmap['IMPORT_FROM'] in scs:  #如果是 from xx import xx的样式
                    #最开头的IMPORT_FROM是from的位置
                    fi = scs.index(opmap['IMPORT_NAME']) 
                    imp_pos = self.__load_name(ln[fi][1]) #from的位置
                    imp_nbr = self.__load_const(ln[fi-1][1]) #再往前就是import的内容，应该是一个元祖
                    imp_nbn = len(imp_nbr) * 2 #元祖的长度*2为下面 IMPORT_NAME STORE_NAME 的数量,用于生成 __ as __
                    imp_nbrl = ln[fi+1:fi+imp_nbn+1]  #得到import的成员和其别名(as xxx)
                    imp_ol = [self.__load_name(op[1]) for op in imp_nbrl if op[0] == 109]  #原成员名字
                    imp_nl = [self.__load_fast(op[1]) for op in imp_nbrl if op[0] in [125, 90]]  #现成员名字

                    if len(imp_ol) != len(imp_nl):
                        raise error.DecomplierError('len(imp_ol) != len(imp_nl)!\nimp_ol:'+str(imp_ol)
                                                +'\nimp_nl:'+str(imp_nl))
                    
                    onp = utils.merge(imp_ol, imp_nl)
                    ons = ['{0}{1}'.format(o, (f' as {n}' if o != n else '')) for o, n in onp]
                    #生成的 xx as xx列表 如果o, n同名，则取o

                    self.__add_line(behf.format(imp_pos, ', '.join(ons)))
                else:
                    ci = scs.index(opmap['IMPORT_NAME'])  #获取最开头的IMPORT_NAME位置
                    imp_n = self.__load_name(ln[ci][1])  #获取import名称
                    imp_as = self.__load_name(ln[ci+1][1])  #import对象的as名称
                    
                    if imp_n != imp_as:  #如果导入对象原名称不等于现名称
                        self.__add_line(behn.format(imp_n + ' as ' + imp_as))  #将as加在后面
                        return
                    self.__add_line(behn.format(imp_n))   #不加as
                
            else:  #单独表达式
                expr = self.__make_expr(ln)
                self.__add_line(expr)

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

    '''
    def __make_cond_expr(self, pairs :list):
        
        pairs:用于生成表达式的字节码对
        
        用于生成条件表达式
        
        cmp = lambda code, name : code == opmap[name]  #匿名函数，方便比较
        cp = 0  #字节码对指针

        for code, arg in pairs:
            if cmp(code, ''):
                pass


            lnp += 1
    '''

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
                beh = '{0}'.format(':'.join([(a if a != 'None' else '') for a in args])) #切片的本质是实例化一个 slice 对象
                #如果a为'None'，就不显示

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

            elif cmp(code, 'COMPARE_OP'):
                self.__make_arit_expr(cmp_op[arg], stack)

            elif cmp(code, 'BUILD_LIST'):
                items = [stack.pop() for _ in range(arg)][::-1]  #根据参数，得到元素数量，依次弹出栈，并反转
                #生成数组表达式，不能使用str()，否则数组嵌套时会出现内部数组是字符串的情况！！
                tl = []
                for item in items:
                    if isinstance(item, str) and \
                        (item[0], item[-1]) in (('[', ']'), ('(', ')'), ('{', '}')):
                        #为了判断对方是否是字符串
                        tl.append(item)
                        continue
                    tl.append(str(item))

                stack.append('[{0}]'.format(', '.join(tl)))
                
            elif cmp(code, 'LOAD_METHOD') or cmp(code, 'LOAD_ATTR'):
                #LOAD_METHOD, LOAD_ATTR的区别是给python虚拟机看的,本质上区别很小
                beh = '{0}.{1}'
                ins = stack.pop()  #对象名称
                attrn = self.__load_name(arg)

                stack.append(beh.format(ins, attrn))

            elif cmp(code, 'CALL_METHOD'):
                beh = '{0}({1})'
                #arg 的值是 参数的数量
                args = ', '.join([str(stack.pop()) for x in range(arg)][::-1])  #逐个出栈，并翻转
                cler = stack.pop()  #方法调用者
                stack.append(beh.format(cler, args))

            elif cmp(code, 'BUILD_TUPLE'):  #代码和 BUILD_LIST 一模一样
                items = [stack.pop() for _ in range(arg)][::-1]  #根据参数，得到元素数量，依次弹出栈，并反转
                #生成数组表达式，不能使用str()，否则数组嵌套时会出现内部数组是字符串的情况！！
                tl = []
                for item in items:
                    if isinstance(item, str) and \
                        (item[0], item[-1]) in (('[', ']'), ('(', ')'), ('{', '}')):
                        #为了判断对方是否是字符串
                        tl.append(item)
                        continue
                    tl.append(str(item))

            elif cmp(code, 'BUILD_CONST_KEY_MAP') or cmp(code, 'BUILD_MAP'):  
                #BUILD_CONST_KEY_MAP 和 BUILD_MAP 差不多的
                keys = stack.pop()  #此时TOS就是键，当map长度为1时，TOS是个const
                
                if not isinstance(keys, tuple): #当TOS不是tuple时
                    keys = (keys, )

                vs = [str(stack.pop()) for x in range(arg)][::-1]  #获取值列表，并反转
                kvs = utils.merge(keys, vs)  #将keys,vs合并
                kvstr = ', '.join(['{0}:{1}'.format(k, v) for k, v in kvs])  #生成键值对

                stack.append('{'+('{0}'.format(kvstr)+'}'))

            cp += 1  #将字节码指针加1

        #理论来说，一路下来，stack的长度应该是1
        if len(stack) != 1:
            raise error.DecomplierError('Expr-stack\'s length is not 1:\nExpr-Stack: '+str(stack))

        return stack.pop()

    def __make_arit_expr(self, operation, stack):
        '''
        构建算数表达式并压入栈
        '''
        a = stack.pop()
        b = stack.pop()

        #TODO : 优化什么时候加括号！
        beh = '({0} {2} {1})'.format(b, a, operation)
        stack.append(beh)

    def __load_const(self, index):
        '''
        co_consts[index]
        '''
        c = self.__consts[index]
        if isinstance(c, str):
            return '"' + c + '"'

        return c

    def __load_fast(self, index):
        '''
        用于 LOAD_FAST  co_varnames[index]
        '''
        return self.__varnames[index]

    def __load_name(self, index):
        '''
        用于 LOAD_NAME & LOAD_GLOBAL  #co_names[index]
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
        self.__make_line(c)
        self.__source.export('TEST_ML.py')

def decode(codeobj):
    pass
