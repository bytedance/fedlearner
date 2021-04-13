# Copyright 2021 The FedLearner Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# coding: utf-8
import string

ALL_CHARS = string.ascii_letters+string.digits+'_'

class BaseFunction(object):
    def __init__(self, arg_size):
        self._arg_size = arg_size

    @property
    def args_size(self):
        return self._arg_size

    def __call__(self, leader, follower, args):
        raise NotImplementedError

class LTFuncDef(BaseFunction):
    def __init__(self):
        super(LTFuncDef, self).__init__(1)

    def __call__(self, leader, follower, args):
        assert all([hasattr(follower, att) for att in args]), "Arg missed"
        assert all([hasattr(leader, att) for att in args]), "Arg missed"
        leader_event_time = getattr(leader, args[0])
        follower_event_time = getattr(follower, args[0])
        return leader_event_time < follower_event_time

class GTFuncDef(BaseFunction):
    def __init__(self):
        super(GTFuncDef, self).__init__(1)

    def __call__(self, leader, follower, args):
        assert all([hasattr(follower, att) for att in args]), "Arg missed"
        assert all([hasattr(leader, att) for att in args]), "Arg missed"
        leader_event_time = getattr(leader, args[0])
        follower_event_time = getattr(follower, args[0])
        return leader_event_time > follower_event_time

class DateTruncDef(BaseFunction):
    """truncate event time"""
    def __init__(self):
        super(DateTruncDef, self).__init__(2)

    def __call__(self, leader, follower, args):
        assert len(args) == 2, "Args not enough"
        leader_event_time = getattr(leader, args[0])
        follower_event_time = getattr(follower, args[0])
        if isinstance(leader_event_time, int):
            leader_event_time = str(leader_event_time)
            follower_event_time = str(follower_event_time)
        size = int(args[1])
        if len(follower_event_time) > size:
            leader_event_time = int(leader_event_time[0: size])
            follower_event_time = int(follower_event_time[0: size])
        return leader_event_time == follower_event_time

class EqualToDef(BaseFunction):
    def __init__(self):
        super(EqualToDef, self).__init__(2)

    def __call__(self, leader, follower, args):
        assert len(args) == self._arg_size, "Args not enough"
        assert hasattr(leader, args[0]), 'Args miss [%s]'%args[0]
        return str(args[1]) == str(getattr(leader, args[0]))

LINK_MAP = dict({
    "lt": LTFuncDef(),
    "gt": GTFuncDef(),
    "et": EqualToDef(),
    "trunc": DateTruncDef()})

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

    def has_func(self):
        return False

class Tuple(object):
    def __init__(self, tuples):
        self._tokens = []
        for tok in tuples:
            if isinstance(tok, FunctionDecl):
                self._tokens.append(tok)
            else:
                if isinstance(tok, str):
                    self._tokens.append(Token(tok))
                else:
                    assert isinstance(tok, Token), "Unknown type of %s"%tok
                    self._tokens.append(tok)

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
        """ return all the function we have."""
        def run(leader, follower):
            return all([LINK_MAP[f.name](leader, follower, f.args(True)) \
                        for f in self._tokens if isinstance(f, FunctionDecl)])
        return run

    @property
    def name(self):
        raise NotImplementedError

class FunctionDecl(object):
    def __init__(self, func_name, args):
        self._func_name = func_name
        assert all(isinstance(arg, str) for arg in args), \
                "Arguments can only be str"
        self._args = [Token(arg) for arg in args]

    def __str__(self):
        return "FunctionDecl: %s(%s)"%(
            self._func_name, ",".join([arg.__str__() for arg in self._args]))

    def key(self):
        raise NotImplementedError

    def arg(self, i):
        return self._args[i]

    def args(self, by_str=False):
        if by_str:
            return [f.key() for f in self._args]
        return self._args

    @property
    def name(self):
        return self._func_name

class Expr(object):
    def __init__(self, key):
        self._expr_str = key
        self._basic_block = []
        self._parse()
        #TODO: syntax validation

    def basic_block(self, i):
        return self._basic_block[i]

    def __str__(self):
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
        return [bb.key() for bb in self._basic_block if len(bb.key()) > 0]


    def run_func(self, tuple_idx):
        item = self._basic_block[tuple_idx]
        if not item.has_func():
            return lambda x, y: True
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
            cur_tuple = []
            result = []
            for tup in tuples:
                if tup in LINK_MAP:
                    result.extend(cur_tuple)
                    cur_tuple = []
                    arg_sz = LINK_MAP[tup].args_size
                    func = tup
                    arg_reader = 0
                else:
                    assert tup not in LINK_MAP, "Invalid expression"
                    cur_tuple.append(tup)
                if arg_reader >= arg_sz > 0 and func is not None:
                    result.append(FunctionDecl(func, cur_tuple))
                    func = None
                    cur_tuple = []
                arg_reader += 1

            if len(cur_tuple) > 0:
                if func is not None:
                    result.append(FunctionDecl(func, cur_tuple))
                else:
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
