from ply import *
from clex import IndentLexer, tokens
from lang_ast import *

import logging

LOGGER = logging.getLogger("ply")
LOGGER.setLevel(logging.ERROR)

##########   Parser (tokens -> AST) ######

# Module will be a list of statements
def p_module(p):
    """module : stmt_list"""
    p[0] = Module(p[1])

def p_empty_module(p):
    "module : empty"
    p[0] = Module([])


# Statements are separated by newlines
def p_stmt_list_1(p):
    "stmt_list : stmt_list NEWLINE"
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



# FuncDef is the standard way of defining a python function
def p_funcdef(p):
    "funcdef : DEF NAME parameters COLON suite"
    p[0] = FuncDef(p[2], p[3], p[5])


# Empty parameters
def p_parameters_empty(p):
    """parameters : LPAR RPAR"""
    p[0] = []


def p_parameters_exist(p):
    """parameters : LPAR varargslist RPAR"""
    p[0] = p[2]


# varargslist: (fpdef ['=' expr] ',')* ('*' NAME [',' '**' NAME] | '**' NAME) |
# highly simplified
def p_varargslist_one(p):
    """varargslist : name_or_var_decl"""
    p[0] = [p[1]]

def p_name_or_var_decl(p):
    """name_or_var_decl : NAME
                        | var_decl"""
    p[0] = p[1]

def p_varargslist_many(p):
    """varargslist : varargslist COMMA name_or_var_decl"""
    p[0] = p[1] + [p[3]]


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
    """small_stmt : return_stmt
                  | include_stmt
                  | define_stmt
                  | expr_stmt
                  | assign_stmt
                  | func_decl
                  | var_decl
                  | enum_decl"""
    p[0] = p[1]


def p_enum_decl(p):
    "enum_decl : ENUM NAME LBRACE enum_name_list RBRACE"
    p[0] = Enum(p[2], p[4])

def p_enum_name_list(p):
    "enum_name_list : NAME"
    p[0] = [p[1]]

def p_enum_name_list_many(p):
    "enum_name_list : enum_name_list COMMA NAME"
    p[0] = p[1] + [p[3]]


# def func(a, b:int)
def p_func_decl(p):
    "func_decl : DEF NAME parameters"
    p[0] = FuncDecl(p[2], p[3], None)


# def func(a, b:int) -> ret
def p_func_declwith_ret(p):
    "func_decl : DEF NAME parameters ARROW type_declaration"
    p[0] = FuncDecl(p[2], p[3], p[5])


# x: int
def p_vardecl(p):
    "var_decl : NAME COLON type_declaration"
    p[0] = VarDecl(p[1], p[3], None)

# x: int = 2
def p_vardecl_assign(p):
    "var_decl : NAME COLON type_declaration ASSIGN expr"
    p[0] = VarDecl(p[1], p[3], p[5])


def p_declaration_name(p):
    "type_declaration : NAME"
    p[0] = p[1]

def p_type_declaration_scoped(p):
    "type_declaration : LBRACE type_declaration RBRACE"
    p[0] = p[2]


# Function type declarations

def p_function_declaration(p):
    "type_declaration : inline_func_decl"
    p[0] = p[1]

def p_inline_func_decl(p):
    "inline_func_decl : param_type_list ARROW type_declaration"
    p[0] = FuncType(p[1], p[3])

def p_param_type_list_empty(p):
    "param_type_list : LPAR RPAR"
    p[0] = []

def p_param_type_list_something(p):
    "param_type_list : LPAR param_list_contents RPAR"
    p[0] = p[2]

def p_param_list_contents(p):
    "param_list_contents : type_declaration"
    p[0] = [p[1]]

def p_param_list_contents_many(p):
    "param_list_contents : param_list_contents COMMA type_declaration"
    p[0] = p[1] + [p[3]]

# Pointer type declarations


def p_declaration_array(p):
    "type_declaration : type_declaration bracket_list"
    contents = p[1]

    def _distribute(sizes):
        # Wraps p[1] in either an array or pointer by distributing the bracket
        # sizes
        if not sizes:
            return p[1]
        size = sizes[0]
        if size is None:
            return Pointer(_distribute(sizes[1:]))
        else:
            return Array(_distribute(sizes[1:]), size)
    p[0] = _distribute(p[2])

def p_pointer_or_array(p):
    """pointer_or_array : pointer
                        | array"""
    p[0] = p[1]

def p_bracket_list_one(p):
    "bracket_list : pointer_or_array"
    p[0] = [p[1]]

def p_bracket_list_many(p):
    "bracket_list : bracket_list pointer_or_array"
    p[0] = p[1] + [p[2]]

def p_pointer(p):
    "pointer : LBRACKET RBRACKET"
    p[0] = None  # None to indicate to higher rule this has no size

def p_array(p):
    "array : LBRACKET expr RBRACKET"
    p[0] = p[2]


def p_include_standard(p):
    "include_stmt : INCLUDE STRING"
    p[0] = Include(p[2])


def p_include_local(p):
    "include_stmt : INCLUDE_LOCAL STRING"
    p[0] = IncludeLocal(p[2])


def p_expr_stmt(p):
    """expr_stmt : expr"""
    p[0] = ExprStmt(p[1])

# LHS is expr b/c nearly anything can be assigned to
def p_assign(p):
    "assign_stmt : expr ASSIGN expr"
    p[0] = Assign(p[1], p[3])


def p_return_stmt(p):
    "return_stmt : RETURN expr"
    p[0] = Return(p[2])


def p_define_stmt(p):
    "define_stmt : DEFINE NAME expr"
    p[0] = Define(p[2], p[3])


def p_define_stmt_empty(p):
    "define_stmt : DEFINE NAME"
    p[0] = Define(p[2], None)


# compound_stmt is a multiline statement

def p_compound_stmt(p):
    """compound_stmt : if_stmt
                     | funcdef"""
    p[0] = p[1]


def p_if_stmt(p):
    'if_stmt : IF expr COLON suite'
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

# expr: expr (comp_op expr)*
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
    """expr : expr PLUS expr
            | expr MINUS expr
            | expr MULT expr
            | expr DIV expr
            | expr LT expr
            | expr EQ expr
            | expr GT expr
            | power"""
    if len(p) == 4:
        p[0] = binary_ops[p[2]](p[1], p[3])
    else:
        p[0] = p[1]

def p_comparison_scoped(p):
    "expr : LPAR expr RPAR"
    p[0] = p[2]

def p_comparison_cast(p):
    "expr : LPAR type_declaration RPAR expr"
    p[0] = Cast(p[2], p[4])


def p_comparison_uadd(p):
    """expr : PLUS expr"""
    p[0] = UnaryOp(UAdd(), p[2])


def p_comparison_usub(p):
    """expr : MINUS expr"""
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


def p_atom_int(p):
    """atom : INT"""
    p[0] = Int(p[1])

def p_atom_float(p):
    """atom : FLOAT"""
    p[0] = Float(p[1])


def p_atom_str(p):
    """atom : STRING"""
    p[0] = Str(p[1])

def p_atom_array_empty(p):
    "atom : LBRACKET RBRACKET"
    p[0] = ArrayLiteral([])

def p_atom_array(p):
    "atom : LBRACKET array_contents RBRACKET"
    p[0] = ArrayLiteral(p[2])

def p_array_litral_contents(p):
    "array_contents : expr"
    p[0] = [p[1]]

def p_array_litral_contents_2(p):
    "array_contents : array_contents COMMA expr"
    p[0] = p[1] + [p[3]]


#def p_atom_tuple(p):
#    """atom : LPAR testlist RPAR"""
#    p[0] = p[2]

# trailer: '(' [arglist] ')' | '[' subscriptlist ']' | '.' NAME


def p_trailer(p):
    "trailer : LPAR arglist RPAR"
    p[0] = p[2]

def p_trailer_empty(p):
    "trailer : LPAR RPAR"
    p[0] = []

# testlist: expr (',' expr)* [',']
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
    """testlist_multi : testlist_multi COMMA expr
                      | expr"""
    if len(p) == 2:
        # singleton
        p[0] = p[1]
    else:
        if isinstance(p[1], list):
            p[0] = p[1] + [p[3]]
        else:
            # singleton -> tuple
            p[0] = [p[1], p[3]]


# arglist: (argument ',')* (argument [',']| '*' expr [',' '**' expr] | '**' expr)
# XXX INCOMPLETE: this doesn't allow the trailing comma
def p_arglist(p):
    """arglist : arglist COMMA argument
               | argument"""
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    else:
        p[0] = [p[1]]

# argument: expr [gen_for] | expr '=' expr  # Really [keyword '='] expr

def p_argument(p):
    "argument : expr"
    p[0] = p[1]

def p_empty(p):
    "empty : "
    pass


def p_error(p):
    raise SyntaxError(p)


def find_column(input, token):
    last_cr = input.rfind('\n',0,token.lexpos)
    if last_cr < 0:
        last_cr = 0
    column = (token.lexpos - last_cr) + 1
    return column


class Parser(object):

    def __init__(self, lexer=None, **kwargs):
        if lexer is None:
            lexer = IndentLexer()
        self.lexer = lexer
        self.parser = yacc.yacc(errorlog=LOGGER)

    def parse(self, code):
        # The parser will not work for strings for some reason if a newline is
        # not at the end of the string. This does not affect files though.
        # For example, passing the string "func()" to this parser without this
        # line will raise a syntax error although a file just containing
        # "func()" works fine. Don't know if this has to do with EOF.
        code += "\n"

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

