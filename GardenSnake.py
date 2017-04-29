# GardenSnake - a parser generator demonstration program
#
# This implements a modified version of a subset of Python:
#  - only 'def', 'return' and 'if' statements
#  - 'if' only has 'then' clause (no elif nor else)
#  - single-quoted strings only, content in raw format
#  - numbers are decimal.Decimal instances (not integers or floats)
#  - no print statment; use the built-in 'print' function
#  - only < > == + - / * implemented (and unary + -)
#  - assignment and tuple assignment work
#  - no generators of any sort
#  - no ... well, no quite a lot

# Why?  I'm thinking about a new indentation-based configuration
# language for a project and wanted to figure out how to do it.  Once
# I got that working I needed a way to test it out.  My original AST
# was dumb so I decided to target Python's AST and compile it into
# Python code.  Plus, it's pretty cool that it only took a day or so
# from sitting down with Ply to having working code.

# This uses David Beazley's Ply from http://www.dabeaz.com/ply/

# This work is hereby released into the Public Domain. To view a copy of
# the public domain dedication, visit
# http://creativecommons.org/licenses/publicdomain/ or send a letter to
# Creative Commons, 543 Howard Street, 5th Floor, San Francisco,
# California, 94105, USA.
#
# Portions of this work are derived from Python's Grammar definition
# and may be covered under the Python copyright and license
#
#          Andrew Dalke / Dalke Scientific Software, LLC
#             30 August 2006 / Cape Town, South Africa

# Changelog:
#  30 August - added link to CC license; removed the "swapcase" encoding

# Modifications for inclusion in PLY distribution
import sys
sys.path.insert(0, "../..")
from ply import *

##### Lexer ######
#import lex
import decimal

tokens = (
    'DEF',
    'IF',
    'NAME',
    'NUMBER',  # Python decimals
    'STRING',  # single quoted strings only; syntax of raw strings
    'LPAR',
    'RPAR',
    'COLON',
    'EQ',
    'ASSIGN',
    'LT',
    'GT',
    'PLUS',
    'MINUS',
    'MULT',
    'DIV',
    'RETURN',
    'WS',
    'NEWLINE',
    'COMMA',
    'INDENT',
    'DEDENT',
)

#t_NUMBER = r'\d+'
# taken from decmial.py but without the leading sign


def t_NUMBER(t):
    r"""(\d+(\.\d*)?)|(\.\d+)"""
    if t.value.isdigit():
        t.value = int(t.value)
    else:
        t.value = float(t.value)
    return t


def t_STRING(t):
    r"'([^\\']+|\\'|\\\\)*'"  # I think this is right ...
    t.value = t.value[1:-1]  # .swapcase() # for fun
    return t

t_COLON = r':'
t_EQ = r'=='
t_ASSIGN = r'='
t_LT = r'<'
t_GT = r'>'
t_PLUS = r'\+'
t_MINUS = r'-'
t_MULT = r'\*'
t_DIV = r'/'
t_COMMA = r','

# Ply nicely documented how to do this.

RESERVED = {
    "def": "DEF",
    "if": "IF",
    "return": "RETURN",
}


def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = RESERVED.get(t.value, "NAME")
    return t

# Putting this before t_WS let it consume lines with only comments in
# them so the latter code never sees the WS part.  Not consuming the
# newline.  Needed for "if 1: #comment"


def t_comment(t):
    r"[ ]*\043[^\n]*"  # \043 is '#'
    pass


# Whitespace
def t_WS(t):
    r'[ ]+'
    if t.lexer.at_line_start and t.lexer.paren_count == 0:
        return t

# Don't generate newline tokens when inside of parenthesis, eg
#   a = (1,
#        2, 3)


def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    t.type = "NEWLINE"
    if t.lexer.paren_count == 0:
        return t


def t_LPAR(t):
    r'\('
    t.lexer.paren_count += 1
    return t


def t_RPAR(t):
    r'\)'
    # check for underflow?  should be the job of the parser
    t.lexer.paren_count -= 1
    return t


def t_error(t):
    raise SyntaxError("Unknown symbol %r" % (t.value[0],))
    print("Skipping", repr(t.value[0]))
    t.lexer.skip(1)

# I implemented INDENT / DEDENT generation as a post-processing filter

# The original lex token stream contains WS and NEWLINE characters.
# WS will only occur before any other tokens on a line.

# I have three filters.  One tags tokens by adding two attributes.
# "must_indent" is True if the token must be indented from the
# previous code.  The other is "at_line_start" which is True for WS
# and the first non-WS/non-NEWLINE on a line.  It flags the check so
# see if the new line has changed indication level.

# Python's syntax has three INDENT states
#  0) no colon hence no need to indent
#  1) "if 1: go()" - simple statements have a COLON but no need for an indent
#  2) "if 1:\n  go()" - complex statements have a COLON NEWLINE and must indent
NO_INDENT = 0
MAY_INDENT = 1
MUST_INDENT = 2

# only care about whitespace at the start of a line


def track_tokens_filter(lexer, tokens):
    lexer.at_line_start = at_line_start = True
    indent = NO_INDENT
    saw_colon = False
    for token in tokens:
        token.at_line_start = at_line_start

        if token.type == "COLON":
            at_line_start = False
            indent = MAY_INDENT
            token.must_indent = False

        elif token.type == "NEWLINE":
            at_line_start = True
            if indent == MAY_INDENT:
                indent = MUST_INDENT
            token.must_indent = False

        elif token.type == "WS":
            assert token.at_line_start == True
            at_line_start = True
            token.must_indent = False

        else:
            # A real token; only indent after COLON NEWLINE
            if indent == MUST_INDENT:
                token.must_indent = True
            else:
                token.must_indent = False
            at_line_start = False
            indent = NO_INDENT

        yield token
        lexer.at_line_start = at_line_start


def _new_token(type, lineno):
    tok = lex.LexToken()
    tok.type = type
    tok.value = None
    tok.lineno = lineno
    return tok

# Synthesize a DEDENT tag


def DEDENT(lineno):
    return _new_token("DEDENT", lineno)

# Synthesize an INDENT tag


def INDENT(lineno):
    return _new_token("INDENT", lineno)


# Track the indentation level and emit the right INDENT / DEDENT events.
def indentation_filter(tokens):
    # A stack of indentation levels; will never pop item 0
    levels = [0]
    token = None
    depth = 0
    prev_was_ws = False
    for token in tokens:
        # if 1:
        # print "Process", token,
        # if token.at_line_start:
        # print "at_line_start",
        # if token.must_indent:
        # print "must_indent",
        # print

        # WS only occurs at the start of the line
        # There may be WS followed by NEWLINE so
        # only track the depth here.  Don't indent/dedent
        # until there's something real.
        if token.type == "WS":
            assert depth == 0
            depth = len(token.value)
            prev_was_ws = True
            # WS tokens are never passed to the parser
            continue

        if token.type == "NEWLINE":
            depth = 0
            if prev_was_ws or token.at_line_start:
                # ignore blank lines
                continue
            # pass the other cases on through
            yield token
            continue

        # then it must be a real token (not WS, not NEWLINE)
        # which can affect the indentation level

        prev_was_ws = False
        if token.must_indent:
            # The current depth must be larger than the previous level
            if not (depth > levels[-1]):
                raise IndentationError("expected an indented block")

            levels.append(depth)
            yield INDENT(token.lineno)

        elif token.at_line_start:
            # Must be on the same level or one of the previous levels
            if depth == levels[-1]:
                # At the same level
                pass
            elif depth > levels[-1]:
                raise IndentationError(
                    "indentation increase but not in new block")
            else:
                # Back up; but only if it matches a previous level
                try:
                    i = levels.index(depth)
                except ValueError:
                    raise IndentationError("inconsistent indentation")
                for _ in range(i + 1, len(levels)):
                    yield DEDENT(token.lineno)
                    levels.pop()

        yield token

    ### Finished processing ###

    # Must dedent any remaining levels
    if len(levels) > 1:
        assert token is not None
        for _ in range(1, len(levels)):
            yield DEDENT(token.lineno)


# The top-level filter adds an ENDMARKER, if requested.
# Python's grammar uses it.
def filter(lexer):
    token = None
    tokens = iter(lexer.token, None)
    tokens = track_tokens_filter(lexer, tokens)
    for token in indentation_filter(tokens):
        yield token

# Combine Ply and my filters into a new lexer


class IndentLexer(object):

    def __init__(self, debug=0, optimize=0, lextab='lextab', reflags=0):
        self.lexer = lex.lex(debug=debug, optimize=optimize,
                             lextab=lextab, reflags=reflags)
        self.token_stream = None

    def input(self, s):
        self.lexer.paren_count = 0
        self.lexer.input(s)
        self.token_stream = filter(self.lexer)

    def token(self):
        try:
            return next(self.token_stream)
        except StopIteration:
            return None

##########   Parser (tokens -> AST) ######


INDENTATION = "    "


class Node:
    __slots__ = tuple()

    def __init__(self, *args, **kwargs):
        for i, val in enumerate(args):
            setattr(self, self.__slots__[i], val)

        for attr in self.__slots__[len(args):]:
            setattr(self, attr, kwargs[attr])

    def lines(self):
        """
        Yields strings representing each line in the textual representation
        of this node. The tailing newline is excluded.
        """
        raise NotImplementedError("lines() not implemented for node {}".format(type(self)))

    def __str__(self):
        return "\n".join(self.lines())


def assert_node(n):
    assert isinstance(n, Node), "Expected Node. Got {}".format(n)


def assert_contains_nodes(seq):
    assert isinstance(seq, (list, tuple)), "Expected list or tuple for sequence. Got {}".format(type(seq))
    for n in seq:
        assert_node(n)


class Module(Node):
    __slots__ = ("body", )

    def lines(self):
        for node in self.body:
            yield from node.lines()


# The grammar comments come from Python's Grammar/Grammar file

# NB: compound_stmt in single_input is followed by extra NEWLINE!
# file_input: (NEWLINE | stmt)* ENDMARKER
def p_module(p):
    """module : stmt_list"""
    assert_contains_nodes(p[1])
    p[0] = Module(p[1])


def p_stmt_list_1(p):
    "stmt_list : stmt_list NEWLINE"
    assert_contains_nodes(p[1])
    p[0] = p[1]


def p_stmt_list_2(p):
    "stmt_list : stmt_list stmt"
    assert_node(p[2])
    assert_contains_nodes(p[1])
    p[0] = p[1] + [p[2]]


def p_stmt_list_3(p):
    "stmt_list : NEWLINE"
    p[0] = []


def p_stmt_list_4(p):
    "stmt_list : stmt"
    assert_node(p[1])
    p[0] = [p[1]]


class FunctionDef(Node):
    __slots__ = ("name", "params", "body")

    def lines(self):
        yield "def {}({}):".format(
            self.name,
            ", ".join(map(str, self.params))
        )
        for node in self.body:
            for line in node.lines():
                yield INDENTATION + line


# funcdef: [decorators] 'def' NAME parameters ':' suite
# ignoring decorators
def p_funcdef(p):
    "funcdef : DEF NAME parameters COLON suite"
    assert_contains_nodes(p[5])
    p[0] = FunctionDef(p[2], tuple(p[3]), p[5])

# parameters: '(' [varargslist] ')'


def p_parameters_empty(p):
    """parameters : LPAR RPAR"""
    p[0] = []


def p_parameters_exist(p):
    """parameters : LPAR varargslist RPAR"""
    p[0] = p[2]


# varargslist: (fpdef ['=' test] ',')* ('*' NAME [',' '**' NAME] | '**' NAME) |
# highly simplified
def p_varargslist_one(p):
    """varargslist : NAME"""
    p[0] = [p[1]]


def p_varargslist_many(p):
    """varargslist : varargslist COMMA NAME"""
    p[0] = p[1] + p[3]


def p_stmt(p):
    """stmt : simple_stmt
            | compound_stmt"""
    assert_node(p[1])
    p[0] = p[1]

# simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE


def p_simple_stmt(p):
    """simple_stmt : small_stmt NEWLINE"""
    assert_node(p[1])
    p[0] = p[1]


# small_stmt: expr_stmt | print_stmt  | del_stmt | pass_stmt | flow_stmt |
#    import_stmt | global_stmt | exec_stmt | assert_stmt


def p_small_stmt(p):
    """small_stmt : flow_stmt
                  | expr_stmt"""
    assert_node(p[1])
    p[0] = p[1]

# expr_stmt: testlist (augassign (yield_expr|testlist) |
#                      ('=' (yield_expr|testlist))*)
# augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' |
#             '<<=' | '>>=' | '**=' | '//=')


class Expr(Node):
    __slots__ = ("value", )

    def lines(self):
        yield from self.value.lines()


class Assign(Node):
    __slots__ = ("left", "right")

    def lines(self):
        yield "{} = {}".format(self.left, self.right)


def p_expr_stmt(p):
    """expr_stmt : testlist ASSIGN testlist
                 | testlist """
    if len(p) == 2:
        # a list of expressions
        p[0] = Expr(p[1])
    else:
        p[0] = Assign(p[1], p[3])


def p_flow_stmt(p):
    "flow_stmt : return_stmt"
    p[0] = p[1]

# return_stmt: 'return' [testlist]


class Return(Node):
    __slots__ = ("value", )

    def lines(self):
        line_iter = self.value.lines()
        line1 = next(line_iter)
        yield "return {}".format(line1)
        for line in line_iter:
            yield INDENTATION + line


def p_return_stmt(p):
    "return_stmt : RETURN testlist"
    p[0] = Return(p[2])


# compound_stmt is a multiline statement


def p_compound_stmt(p):
    """compound_stmt : if_stmt
                     | funcdef"""
    p[0] = p[1]


class If(Node):
    __slots__ = ("test", "body")

    def lines(self):
        yield "if {}:".format(self.test)
        for node in self.body:
            for line in node.lines():
                yield INDENTATION + line


def p_if_stmt(p):
    'if_stmt : IF test COLON suite'
    p[0] = If(p[2], p[4])


def p_suite(p):
    """suite : NEWLINE INDENT stmts DEDENT"""
    p[0] = p[3]


def p_stmts_1(p):
    """stmts : stmt"""
    p[0] = [p[1]]


def p_stmts_2(p):
    """stmts : stmts stmt"""
    p[0] = p[1] + [p[2]]

# No using Python's approach because Ply supports precedence

# comparison: expr (comp_op expr)*
# arith_expr: term (('+'|'-') term)*
# term: factor (('*'|'/'|'%'|'//') factor)*
# factor: ('+'|'-'|'~') factor | power
# comp_op: '<'|'>'|'=='|'>='|'<='|'<>'|'!='|'in'|'not' 'in'|'is'|'is' 'not'


class BinOp(Node):
    __slots__ = ("left", "op", "right")

    def lines(self):
        yield "({} {} {})".format(self.left, self.op, self.right)


class Compare(BinOp):
    pass


def make_lt_compare(left, right):
    return Compare(left, '<', right)


def make_gt_compare(left, right):
    return Compare(left, '>', right)


def make_eq_compare(left, right):
    return Compare(left, '==', right)


def make_add(l, r):
    return BinOp(l, "+", r)


def make_sub(l, r):
    return BinOp(l, "-", r)


def make_mult(l, r):
    return BinOp(l, "*", r)


def make_div(l, r):
    return BinOp(l, "/", r)


class UAdd(Node):
    def lines(self):
        yield "+"


class USub(Node):
    def lines(self):
        yield "-"


class Not(Node):
    def lines(self):
        yield "not"


class Invert(Node):
    def lines(self):
        yield "~"


class UnaryOp(Node):
    __slots__ = ("op", "value")

    def lines(self):
        if isinstance(self.op, Not):
            yield "{} {}".format(self.op, self.value)
        else:
            yield "{}{}".format(self.op, self.value)


binary_ops = {
    "+": make_add,
    "-": make_sub,
    "*": make_mult,
    "/": make_div,
    "<": make_lt_compare,
    ">": make_gt_compare,
    "==": make_eq_compare,
}
precedence = (
    ("left", "EQ", "GT", "LT"),
    ("left", "PLUS", "MINUS"),
    ("left", "MULT", "DIV"),
)


def p_comparison(p):
    """comparison : comparison PLUS comparison
                  | comparison MINUS comparison
                  | comparison MULT comparison
                  | comparison DIV comparison
                  | comparison LT comparison
                  | comparison EQ comparison
                  | comparison GT comparison
                  | power"""
    if len(p) == 4:
        p[0] = binary_ops[p[2]](p[1], p[3])
    else:
        p[0] = p[1]


def p_comparison_uadd(p):
    """comparison : PLUS comparison"""
    p[0] = UnaryOp(UAdd(), p[2])


def p_comparison_usub(p):
    """comparison : MINUS comparison"""
    p[0] = UnaryOp(USub(), p[2])

# power: atom trailer* ['**' factor]
# trailers enables function calls.  I only allow one level of calls
# so this is 'trailer'


class Call(Node):
    __slots__ = ("func", "args")

    def lines(self):
        yield "{}({})".format(self.func, ", ".join(map(str, self.args)))


def p_power_1(p):
    """power : atom"""
    p[0] = p[1]


def p_power_2(p):
    """power : atom trailer"""
    p[0] = Call(p[1], p[2])


class Name(Node):
    __slots__ = ("id", )

    def lines(self):
        yield str(self.id)


class Number(Node):
    __slots__ = ("n", )

    def lines(self):
        yield str(self.n )


class Str(Node):
    __slots__ = ("s", )

    def lines(self):
        yield '"{}"'.format(self.s.replace('"', r'\"'))


def p_atom_name(p):
    """atom : NAME"""
    p[0] = Name(p[1])


def p_atom_number(p):
    """atom : NUMBER"""
    p[0] = Number(p[1])


def p_atom_str(p):
    """atom : STRING"""
    p[0] = Str(p[1])


def p_atom_tuple(p):
    """atom : LPAR testlist RPAR"""
    p[0] = p[2]

# trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME


def p_trailer(p):
    "trailer : LPAR arglist RPAR"
    p[0] = p[2]

# testlist: test (',' test)* [',']
# Contains shift/reduce error


class Tuple(Node):
    __slots__ = ("elts", )

    def lines(self):
        yield "({})".format(", ".join(map(str, self.elts)))


def p_testlist(p):
    """testlist : testlist_multi COMMA
                | testlist_multi """
    if len(p) == 2:
        p[0] = p[1]
    else:
        # May need to promote singleton to tuple
        if isinstance(p[1], list):
            p[0] = p[1]
        else:
            p[0] = [p[1]]
    # Convert into a tuple?
    if isinstance(p[0], list):
        p[0] = Tuple(p[0])


def p_testlist_multi(p):
    """testlist_multi : testlist_multi COMMA test
                      | test"""
    if len(p) == 2:
        # singleton
        p[0] = p[1]
    else:
        if isinstance(p[1], list):
            p[0] = p[1] + [p[3]]
        else:
            # singleton -> tuple
            p[0] = [p[1], p[3]]


# test: or_test ['if' or_test 'else' test] | lambdef
#  as I don't support 'and', 'or', and 'not' this works down to 'comparison'
def p_test(p):
    "test : comparison"
    p[0] = p[1]


# arglist: (argument ',')* (argument [',']| '*' test [',' '**' test] | '**' test)
# XXX INCOMPLETE: this doesn't allow the trailing comma
def p_arglist(p):
    """arglist : arglist COMMA argument
               | argument"""
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

# argument: test [gen_for] | test '=' test  # Really [keyword '='] test

def p_argument(p):
    "argument : test"
    p[0] = p[1]


def p_error(p):
    # print "Error!", repr(p)
    raise SyntaxError(p)


class GardenSnakeParser(object):

    def __init__(self, lexer=None):
        if lexer is None:
            lexer = IndentLexer()
        self.lexer = lexer
        self.parser = yacc.yacc()

    def parse(self, code):
        self.lexer.input(code)
        result = self.parser.parse(lexer=self.lexer)
        return result


####### Test code #######

code = r"""

print('LET\'S TRY THIS \\OUT')

#Comment here
def x(a):
    def func(y):
        def func2(z):
            return z
        return func2(y)

    print('called with', a)
    if a == 1:
        return 2
    if a*2 > 10:
        return 999 / 4
        # Another comment here

    return func(a+2*3)

ints = (1, 2,
   3, 4,
5)
print('mutiline-expression', ints)

t = 4+1/3*2+6*(9-5+1)
print('predence test; should be 34+2/3:', t, t==(34+2/3))

print('numbers', 1,2,3,4,5)
if 1:
 8
 a=9
 print(x(a))

print(x(1))
print(x(2))
print(x(8),'3')
print('this is decimal', 1/5)
print('BIG DECIMAL', 1.234567891234567)

"""

import astor
parser = GardenSnakeParser()
#print(astor.dump(parser.parse(code)))
print(parser.parse(code))
