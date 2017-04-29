from ply import *
from clex import IndentLexer, tokens
from lang_ast import *


##########   Parser (tokens -> AST) ######

def p_module(p):
    """module : stmt_list"""
    p[0] = Module(p[1])


def p_stmt_list_1(p):
    "stmt_list : stmt_list NEWLINE"
    # For catching newlines
    p[0] = p[1]


def p_stmt_list_2(p):
    "stmt_list : stmt_list stmt"
    # Appending statements to statement list
    p[0] = p[1] + [p[2]]


def p_stmt_list_3(p):
    "stmt_list : NEWLINE"
    p[0] = []


def p_stmt_list_4(p):
    "stmt_list : stmt"
    p[0] = [p[1]]



# funcdef: [decorators] 'def' NAME parameters ':' suite
# ignoring decorators
def p_funcdef(p):
    "funcdef : DEF NAME parameters COLON suite"
    assert_contains_nodes(p[5])
    p[0] = FunctionDef(p[2], p[3], p[5])

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
    p[0] = p[1]

# simple_stmt: small_stmt (';' small_stmt)* [';'] NEWLINE


def p_simple_stmt(p):
    """simple_stmt : small_stmt NEWLINE"""
    p[0] = p[1]



# small_stmt: expr_stmt | print_stmt  | del_stmt | pass_stmt | flow_stmt |
#    import_stmt | global_stmt | exec_stmt | assert_stmt


def p_small_stmt(p):
    """small_stmt : flow_stmt
                  | expr_stmt
                  | funcdecl"""
    p[0] = p[1]


def p_funcdecl(p):
    "funcdecl : DEF NAME parameters"
    p[0] = FunctionDef(p[2], p[3], [])


# expr_stmt: testlist (augassign (yield_expr|testlist) |
#                      ('=' (yield_expr|testlist))*)
# augassign: ('+=' | '-=' | '*=' | '/=' | '%=' | '&=' | '|=' | '^=' |
#             '<<=' | '>>=' | '**=' | '//=')




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


def p_return_stmt(p):
    "return_stmt : RETURN testlist"
    p[0] = Return(p[2])


# compound_stmt is a multiline statement


def p_compound_stmt(p):
    """compound_stmt : if_stmt
                     | funcdef"""
    p[0] = p[1]


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


precedence = (
    ("left", "EQ", "GT", "LT"),
    ("left", "PLUS", "MINUS"),
    ("left", "MULT", "DIV"),
)


binary_ops = {
    "+": make_add,
    "-": make_sub,
    "*": make_mult,
    "/": make_div,
    "<": make_lt_compare,
    ">": make_gt_compare,
    "==": make_eq_compare,
}

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



def p_power_1(p):
    """power : atom"""
    p[0] = p[1]


def p_power_2(p):
    """power : atom trailer"""
    p[0] = Call(p[1], p[2])


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
    raise SyntaxError(p)


class Parser(object):

    def __init__(self, lexer=None):
        if lexer is None:
            lexer = IndentLexer()
        self.lexer = lexer
        self.parser = yacc.yacc()

    def parse(self, code):
        self.lexer.input(code)
        result = self.parser.parse(lexer=self.lexer)
        return result


def get_args():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument("filename")
    parser.add_argument("-d", "--dump", default=False, action="store_true")

    return parser.parse_args()


def main():
    args = get_args()

    parser = Parser()

    with open(args.filename, "r") as f:
        ast = parser.parse(f.read())

    if args.dump:
        print(dump_tree(ast))
    else:
        print(ast)


if __name__ == "__main__":
    main()

