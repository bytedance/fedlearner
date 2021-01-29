import string

ALL_CHARS = string.ascii_letters+string.digits+'_'

class BaseFunction(object):
    def __init__(self, arg_size):
        self._arg_size = arg_size

    @property
    def args_size(self):
        return self._arg_size

    def __call__(self, show, conv, args: list[str]):
        raise NotImplementedError

class LTFuncDef(BaseFunction):
    def __init__(self):
        super(LTFuncDef, self).__init__(2)

    def __call__(self, show, conv, args):
        assert all([hasattr(conv, att) for att in args]), "Arg missed"
        assert all([hasattr(show, att) for att in args]), "Arg missed"
        show_event_time = getattr(show, args[0])
        conv_event_time = getattr(conv, args[0])
        return show_event_time < conv_event_time

LINK_MAP = dict({"lt": LTFuncDef()})

class Token(object):
    def __init__(self, tok):
        self._tok = tok
        self._is_numeric = self._tok.isdigit()

    def key(self):
        return self._tok

    def __str__(self):
        return "Token: " + self._tok + ":%s" % (
            "i" if self._is_numeric else "s")

    @property
    def name(self):
        return self._tok

class Tuple(object):
    def __init__(self, tuples):
        self._tokens = []
        for tok in tuples:
            if isinstance(tok, FunctionDecl):
                self._tokens.append(tok)
            else:
                assert isinstance(tok, str), "Unknown type of %s"%tok
                self._tokens.append(Token(tok))

    def __str__(self):
        return "Tuple: " + ", ".join([it.__str__() for it in self._tokens])

    def key(self):
        return [tok.key() for tok in self._tokens \
                if not isinstance(tok, FunctionDecl)]

    def __getitem__(self, index):
        return self._tokens[index]

    def has_func(self):
        return any(isinstance(item, FunctionDecl) for item in self._tokens)

    def run_func(self):
        """
            返回一个函数
        """
        assert self.has_func(), "No func declared"
        def run(show, conv):
            return all([LINK_MAP[f.name](show, conv) \
                        for f in self._tokens if isinstance(f, FunctionDecl)])
        return run

    @property
    def name(self):
        raise NotImplementedError

class FunctionDecl(object):
    def __init__(self, func_name, args):
        self._func_name = func_name
        self._args = [Token(arg) for arg in args]

    def __str__(self):
        return "FunctionDecl: %s(%s)"%(
            self._func_name, ",".join([arg.__str__() for arg in self._args]))

    def key(self):
        raise NotImplementedError

    def arg(self, i):
        return self._args[i]

    @property
    def args(self):
        return self._args

    @property
    def name(self):
        return self._func_name

class JoinExpr(object):
    def __init__(self, key):
        self._expr_str = key
        self._basic_block = []
        self._parse()
        #TODO: syntax validation

    def basic_block(self, i):
        return self._basic_block[i]

    def __str__(self):
        #print(self._basic_block)
        expr_str = "AST of [%s]:\n"%(self._expr_str)
        sep = "\n"
        for tok in self._basic_block:
            if isinstance(tok, list):
                for inner_tok in tok:
                    expr_str += "%s%s"%(inner_tok, sep)
            else:
                expr_str += "%s%s"%(tok, sep)
        return expr_str

    def keys(self):
        return [bb.key() for bb in self._basic_block]

    def run_func(self, tuple_idx):
        return self._basic_block[tuple_idx].run_func()

    def add_ast(self, tuples):
        if len(tuples) == 0:
            return
        if len(tuples) == 1:
            self._basic_block.append(Token(tuples[0]))
        else:
            func = None
            arg_sz = 0
            arg_reader = 0
            cur_tuple = [str]
            result = []
            for tup in tuples:
                if tup in LINK_MAP:
                    result.extend(cur_tuple)
                    cur_tuple = []
                    arg_sz = LINK_MAP[tup].arg_size
                    func = tup
                    arg_reader = 0
                else:
                    assert tup not in LINK_MAP, "Invalid expression"
                    cur_tuple.append(tup)
                if arg_reader >= arg_sz > 0 and func is not None:
                    #pdb.set_trace()
                    result.append(FunctionDecl(func, cur_tuple))
                    func = None
                    cur_tuple = []
                arg_reader += 1

            if len(cur_tuple) > 0:
                result.extend(cur_tuple)
            self._basic_block.append(Tuple(result))

    def _parse(self):
        strip_key = self._expr_str.strip()
        tok_pos = 0
        left_bracket = 0
        cur_tuple = []
        for i, c in enumerate(strip_key):
            if c == '(':
                left_bracket += 1
                if i > tok_pos:
                    tok = strip_key[tok_pos:i]
                    if tok == "or":
                        self.add_ast(cur_tuple)
                        cur_tuple = []
                    else:
                        cur_tuple.append(tok)
                tok_pos = i+1
            elif c in (')', ' ', ','):
                if c == ')':
                    left_bracket -= 1
                    if left_bracket < 0:
                        raise ValueError("( should match )")
                if i > tok_pos:
                    tok = strip_key[tok_pos:i]
                    if tok == "or":
                        self.add_ast(cur_tuple)
                        cur_tuple = []
                    else:
                        cur_tuple.append(tok)
                tok_pos = i+1
            else:
                assert c in ALL_CHARS, "Illegal character [%s]"%c
        assert left_bracket == 0, "( should match )"
        if len(strip_key) > tok_pos:
            cur_tuple.append(strip_key[tok_pos:])
        self.add_ast(cur_tuple)
        assert left_bracket == 0, "( should match )"
