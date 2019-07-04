class DecomplierError(Exception):
    '''反编译器异常'''
    def __init__(self, *args):
        super().__init__(str(args[0]) + '''\n  ---This may not be your fault. 
If you think your pyc file is perfect,
you should contact the developer and ask him for BUG,
or show him the error message.
The developer's e-mail address is laomobk@163.com''')


def mayerr(func):
    def wrapper(*args, **kw):
        try:
            rtn = func(*args, **kw)
        
        except Exception as e:
            raise DecomplierError('PythonException:' + str(e))

        return rtn
    return wrapper