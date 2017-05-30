import ply.yacc as yacc
from clex import Lexer, find_column
from lang_ast import *


class Parser:
    # Note: High precedence last, low precedence first
    precedence = (
        ("left", "OR"),  # 12
        ("left", "AND"),  # 11
        ("left", "EQ", "NE"),  # 7
        ("left", "GT", "LT", "LE", "GE"),  # 6
        ("left", "PLUS", "MINUS"),  # 4
        ("left", "MULT", "DIV", "MOD"),  # 3
        ("right", "AMP", "NOT", "CAST", "PREINC", "PREDEC"),  # 2
        ("left", "ARROW", "POSTINC", "POSTDEC"),  # 1
    )

    ########### Parser interface #############

    def __init__(self, lexer=Lexer, infer_types=True, source_file=None, **kwargs):
        self.__infer_types = infer_types
        self.__source_file = source_file

        self.__lexer = lexer(**kwargs)
        self.tokens = self.__lexer.tokens
        self.parser = yacc.yacc(
            module=self,
            **kwargs
        )

    def lexer(self):
        return self.__lexer

    def parse(self, code):
        # The parser will not work for strings for some reason if a newline is
        # not at the end of the string. This does not affect files though.
        # For example, passing the string "func()" to this parser without this
        # line will raise a syntax error although a file just containing
        # "func()" works fine. Don't know if this has to do with EOF.
        code += "\n"
        return self.parser.parse(code, lexer=self.__lexer)

    ##########   Parser (tokens -> AST) ######

    # Module will be a list of statements
    def p_module(self, p):
        """module : stmt_list"""
        p[0] = Module(p[1], self.__source_file)

    def p_empty_module(self, p):
        "module : empty"
        p[0] = Module(filename=self.__source_file)

    # Statements are separated by newlines
    def p_stmt_list_1(self, p):
        "stmt_list : stmt_list NEWLINE"
        p[0] = p[1]

    def p_stmt_list_2(self, p):
        "stmt_list : stmt_list stmt"
        p[0] = p[1] + [p[2]]

    def p_stmt_list_3(self, p):
        "stmt_list : NEWLINE"
        p[0] = []

    def p_stmt_list_4(self, p):
        "stmt_list : stmt"
        p[0] = [p[1]]

    # FuncDef is the standard way of defining a python function
    def p_funcdef(self, p):
        "funcdef : DEF NAME parameters COLON suite"
        p[0] = FuncDef(p[2], p[3], p[5], None)

    # Empty parameters
    def p_parameters_empty(self, p):
        """parameters : LPAR RPAR"""
        p[0] = []

    def p_parameters_exist(self, p):
        """parameters : LPAR varargslist RPAR"""
        p[0] = p[2]

    def p_varargslist_one(self, p):
        """varargslist : varaglist_elem"""
        p[0] = [p[1]]

    def p_name_or_var_decl(self, p):
        """varaglist_elem : NAME
                          | var_decl"""
        p[0] = p[1]

    def p_ellipsis(self, p):
        "varaglist_elem : ELLIPSIS"
        p[0] = Ellipsis()

    def p_varargslist_many(self, p):
        """varargslist : varargslist COMMA varaglist_elem"""
        p[0] = p[1] + [p[3]]

    def p_stmt(self, p):
        """stmt : simple_stmt
                | compound_stmt"""
        p[0] = p[1]

    """
    Simple statements always take up 1 line
    """

    def p_simple_stmt(self, p):
        """simple_stmt : small_stmt NEWLINE"""
        p[0] = p[1]

    def p_small_stmt(self, p):
        """small_stmt : return_stmt
                      | include_stmt
                      | define_stmt
                      | ifndef_stmt
                      | endif_stmt
                      | expr_stmt
                      | assign_stmt
                      | func_decl
                      | var_decl_stmt
                      | enum_decl_stmt
                      | struct_decl_stmt
                      | typedef_stmt
                      | break
                      | pass"""
        p[0] = p[1]

    # typdef

    def p_typedef_stmt(self, p):
        "typedef_stmt : TYPEDEF type_declaration NAME"
        p[0] = TypeDefStmt(p[2], p[3])

    # Macros

    def p_define_stmt(self, p):
        "define_stmt : DEFINE NAME expr"
        p[0] = Define(p[2], p[3])

    def p_define_stmt_empty(self, p):
        "define_stmt : DEFINE NAME"
        p[0] = Define(p[2])

    def p_ifndef_stmt(self, p):
        "ifndef_stmt : IFNDEF NAME"
        p[0] = Ifndef(p[2])

    def p_endif_stmt(self, p):
        "endif_stmt : ENDIF"
        p[0] = Endif()

    def p_pass(self, p):
        "pass : PASS"
        p[0] = Pass()

    def p_break(self, p):
        "break : BREAK"
        p[0] = Break()

    # Enums
    def p_enum_decl_stmt(self, p):
        "enum_decl_stmt : enum_decl"
        p[0] = EnumDecl(p[1])

    def p_enum_decl(self, p):
        "enum_decl : ENUM NAME LBRACE enum_name_list RBRACE"
        p[0] = Enum(p[2], p[4])

    def p_enum_name_list(self, p):
        "enum_name_list : NAME"
        p[0] = [p[1]]

    def p_enum_name_list_many(self, p):
        "enum_name_list : enum_name_list COMMA NAME"
        p[0] = p[1] + [p[3]]

    # Structs
    # They must have at least 1 member
    def p_struct_decl_stmt(self, p):
        "struct_decl_stmt : struct_decl"
        p[0] = StructDecl(p[1])

    def p_struct_decl(self, p):
        "struct_decl : STRUCT NAME LBRACE struct_decl_list optional_comma RBRACE"
        p[0] = Struct(p[2], p[4])

    def p_optional_seq_comma(self, p):
        """optional_comma : COMMA
                          | empty"""
        # The extra optional comma in a sequence
        pass

    def p_struct_decl_list(self, p):
        "struct_decl_list : struct_decl_list COMMA var_decl"
        p[0] = p[1] + [p[3]]

    def p_struct_decl_list_one(self, p):
        """struct_decl_list : var_decl"""
        p[0] = [p[1]]

    # def func(a, b:int)
    def p_func_decl(self, p):
        "func_decl : DEF NAME parameters"
        p[0] = FuncDecl(p[2], p[3], NameType("int"))

    # def func(a, b:int) -> ret
    def p_func_declwith_ret(self, p):
        "func_decl : DEF NAME parameters ARROW type_declaration"
        p[0] = FuncDecl(p[2], p[3], p[5])

    def p_var_decl_stmt(self, p):
        "var_decl_stmt : var_decl"
        p[0] = VarDeclStmt(p[1])

    # x: int
    def p_vardecl(self, p):
        "var_decl : NAME COLON type_declaration"
        p[0] = VarDecl(p[1], p[3])

    # x: int = 2
    def p_vardecl_assign(self, p):
        "var_decl : NAME COLON type_declaration ASSIGN expr"
        p[0] = VarDecl(p[1], p[3], p[5])

    def p_declaration_name(self, p):
        "type_declaration : NAME"
        p[0] = NameType(p[1])

    def p_type_declaration_scoped(self, p):
        "type_declaration : LBRACE type_declaration RBRACE"
        p[0] = p[2]


    # Function type declarations

    def p_function_declaration(self, p):
        "type_declaration : inline_func_decl"
        p[0] = p[1]

    def p_inline_func_decl(self, p):
        "inline_func_decl : param_type_list ARROW type_declaration"
        p[0] = FuncType(p[1], p[3])

    def p_param_type_list_empty(self, p):
        "param_type_list : LPAR RPAR"
        p[0] = []

    def p_param_type_list_something(self, p):
        "param_type_list : LPAR param_list_contents RPAR"
        p[0] = p[2]

    def p_param_list_contents(self, p):
        "param_list_contents : type_declaration"
        p[0] = [p[1]]

    def p_param_list_contents_many(self, p):
        "param_list_contents : param_list_contents COMMA type_declaration"
        p[0] = p[1] + [p[3]]

    # Pointer type declarations

    def p_declaration_array(self, p):
        "type_declaration : type_declaration bracket_list"
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

    def p_pointer_or_array(self, p):
        """pointer_or_array : pointer
                            | array"""
        p[0] = p[1]

    def p_bracket_list_one(self, p):
        "bracket_list : pointer_or_array"
        p[0] = [p[1]]

    def p_bracket_list_many(self, p):
        "bracket_list : bracket_list pointer_or_array"
        p[0] = p[1] + [p[2]]

    def p_pointer(self, p):
        "pointer : LBRACKET RBRACKET"
        p[0] = None  # None to indicate to higher rule this has no size

    def p_array(self, p):
        "array : LBRACKET expr RBRACKET"
        p[0] = p[2]

    def p_include_standard(self, p):
        "include_stmt : INCLUDE STRING"
        p[0] = Include(Str(p[2]))

    def p_expr_stmt(self, p):
        """expr_stmt : expr"""
        p[0] = ExprStmt(p[1])

    # LHS is expr b/c nearly anything can be assigned to
    def p_assign(self, p):
        "assign_stmt : expr ASSIGN expr"
        p[0] = Assign(p[1], p[3])

    def p_return_stmt(self, p):
        "return_stmt : RETURN expr"
        p[0] = Return(p[2])

    # compound_stmt is a multiline statement

    def p_compound_stmt(self, p):
        """compound_stmt : if_stmt
                         | while_stmt
                         | dowhile_stmt
                         | switch_stmt
                         | funcdef"""
        p[0] = p[1]


    ###### Control flow ##########

    # Do while stmt
    def p_dowhile(self, p):
        "dowhile_stmt : DO COLON suite WHILE expr"
        p[0] = DoWhile(p[5], p[3])

    # While stmt
    def p_while_stmt(self, p):
        "while_stmt : WHILE expr COLON suite"
        p[0] = While(p[2], p[4], [])

    def p_while_stmt_orelse(self, p):
        "while_stmt : WHILE expr COLON suite while_orelse"
        p[0] = While(p[2], p[4], p[5])

    def p_while_orelse(self, p):
        "while_orelse : ELSE COLON suite"
        p[0] = p[3]


    # If stmt
    def p_if_stmt(self, p):
        'if_stmt : IF expr COLON suite'
        p[0] = If(p[2], p[4], [])

    def p_if_else(self, p):
        'if_stmt : IF expr COLON suite if_orelse'
        p[0] = If(p[2], p[4], p[5])

    def p_orelse_else(self, p):
        "if_orelse : ELSE COLON suite"
        p[0] = p[3]

    def p_orelse_elif_no_orelse(self, p):
        "if_orelse : ELIF expr COLON suite"
        p[0] = [If(p[2], p[4], [])]

    def p_orelse_elif_with_orelse(self, p):
        "if_orelse : ELIF expr COLON suite if_orelse"
        p[0] = [If(p[2], p[4], p[5])]

    # Switch statement
    def p_switch(self, p):
        "switch_stmt : SWITCH expr COLON switch_suite"
        p[0] = Switch(p[2], p[4])

    def p_switch_suite(self, p):
        "switch_suite : NEWLINE INDENT switch_stmts DEDENT"
        p[0] = p[3]

    def p_switch_stmts_case_list(self, p):
        "switch_stmts : case_list"
        p[0] = p[1]

    def p_switch_stmts_cases_with_default(self, p):
        "switch_stmts : case_list default"
        p[0] = p[1] + [p[2]]

    def p_switch_stmts_default(self, p):
        "switch_stmts : default"
        p[0] = [p[1]]

    def p_default(self, p):
        "default : ELSE COLON suite"
        p[0] = Default(p[3])

    def p_case_list_one(self, p):
        "case_list : case"
        p[0] = [p[1]]

    def p_case_list(self, p):
        "case_list : case_list case"
        p[0] = p[1] + [p[2]]

    def p_case(self, p):
        "case : CASE case_expr_list COLON suite"
        p[0] = Case(p[2], p[4])

    def p_case_expr_list_one(self, p):
        "case_expr_list : expr"
        p[0] = [p[1]]

    def p_case_expr_list(self, p):
        "case_expr_list : case_expr_list COMMA expr"
        p[0] = p[1] + [p[3]]

    # Indented suite
    def p_suite(self, p):
        """suite : NEWLINE INDENT stmts DEDENT"""
        p[0] = p[3]

    def p_stmts_1(self, p):
        """stmts : stmt"""
        p[0] = [p[1]]

    def p_stmts_2(self, p):
        """stmts : stmts stmt"""
        p[0] = p[1] + [p[2]]

    """
    Expressions
    """

    def p_add_expr(self, p):
        "expr : expr PLUS expr"
        p[0] = BinOp(p[1], "+", p[3])

    def p_sub_expr(self, p):
        "expr : expr MINUS expr"
        p[0] = BinOp(p[1], "-", p[3])

    def p_mult_expr(self, p):
        "expr : expr MULT expr"
        p[0] = BinOp(p[1], "*", p[3])

    def p_mod_expr(self, p):
        "expr : expr MOD expr"
        p[0] = BinOp(p[1], "%", p[3])

    def p_div_expr(self, p):
        "expr : expr DIV expr"
        p[0] = BinOp(p[1], "/", p[3])

    def p_eq_expr(self, p):
        "expr : expr EQ expr"
        p[0] = Compare(p[1], "==", p[3])

    def p_lt_expr(self, p):
        "expr : expr LT expr"
        p[0] = Compare(p[1], "<", p[3])

    def p_gt_expr(self, p):
        "expr : expr GT expr"
        p[0] = Compare(p[1], ">", p[3])

    def p_le_expr(self, p):
        "expr : expr LE expr"
        p[0] = Compare(p[1], "<=", p[3])

    def p_ge_expr(self, p):
        "expr : expr GE expr"
        p[0] = Compare(p[1], ">=", p[3])

    def p_and_expr(self, p):
        "expr : expr AND expr"
        p[0] = BinOp(p[1], "and", p[3])

    def p_or_expr(self, p):
        "expr : expr OR expr"
        p[0] = BinOp(p[1], "or", p[3])

    def p_comparison_power(self, p):
        "expr : power"
        p[0] = p[1]

    def p_ne(self, p):
        "expr : expr NE expr"
        p[0] = Compare(p[1], "!=", p[3])

    def p_expr_struct_deref(self, p):
        "expr : expr ARROW NAME"
        p[0] = StructPointerDeref(p[1], p[3])

    def p_comparison_scoped(self, p):
        "expr : LPAR expr RPAR"
        p[0] = p[2]

    def p_comparison_cast(self, p):
        "expr : LT type_declaration GT expr %prec CAST"
        p[0] = Cast(p[2], p[4])

    def p_comparison_deref(self, p):
        "expr : MULT expr"
        p[0] = Deref(p[2])

    def p_comparison_uadd(self, p):
        "expr : PLUS expr"
        p[0] = UnaryOp(UAdd(), p[2])

    def p_comparison_usub(self, p):
        "expr : MINUS expr"
        p[0] = UnaryOp(USub(), p[2])

    # Post inc/decrement

    def p_post_inc(self, p):
        "expr : expr INC %prec POSTINC"
        p[0] = PostInc(p[1])

    def p_post_dec(self, p):
        "expr : expr DEC %prec POSTDEC"
        p[0] = PostDec(p[1])

    # Pre inc/decrement

    def p_pre_inc(self, p):
        "expr : INC expr %prec PREINC"
        p[0] = PreInc(p[2])

    def p_pre_dec(self, p):
        "expr : DEC expr %prec PREDEC"
        p[0] = PreDec(p[2])

    def p_comparison_not(self, p):
        "expr : NOT expr"
        p[0] = UnaryOp(Not(), p[2])

    def p_null(self, p):
        "atom : NULL"
        p[0] = Null()

    def p_power_1(self, p):
        "power : atom"
        p[0] = p[1]

    def p_power_2(self, p):
        "power : atom LPAR RPAR"
        p[0] = Call(p[1])

    def p_power_call_args(self, p):
        "power : atom LPAR arglist RPAR"
        p[0] = Call(p[1], p[3])

    # Indexing

    def p_index(self, p):
        "expr : expr LBRACKET expr RBRACKET"
        p[0] = Index(p[1], p[3])

    # Address of

    def p_address_of(self, p):
        "expr : AMP expr"
        p[0] = AddressOf(p[2])

    def p_atom_name(self, p):
        "atom : NAME"
        p[0] = Name(p[1])

    def p_atom_int(self, p):
        "atom : INT"
        p[0] = Int(p[1])

    def p_atom_float(self, p):
        "atom : FLOAT"
        p[0] = Float(p[1])

    def p_atom_str(self, p):
        "atom : STRING"
        p[0] = Str(p[1])

    def p_atom_char(self, p):
        "atom : CHAR"
        p[0] = Char(p[1])

    def p_atom_array_empty(self, p):
        "atom : LBRACKET RBRACKET"
        p[0] = ArrayLiteral([])

    def p_atom_array(self, p):
        "atom : LBRACKET array_contents RBRACKET"
        p[0] = ArrayLiteral(p[2])

    def p_array_litral_contents(self, p):
        "array_contents : expr"
        p[0] = [p[1]]

    def p_array_litral_contents_2(self, p):
        "array_contents : array_contents COMMA expr"
        p[0] = p[1] + [p[3]]

    """
    Arguments when calling a function.

    func(expr1, expr2, expr3)
    """

    def p_arglist(self, p):
        "arglist : arglist COMMA argument"
        p[0] = p[1] + [p[3]]

    def p_arglist_one_arg(self, p):
        "arglist : argument"
        p[0] = [p[1]]

    def p_argument(self, p):
        "argument : expr"
        p[0] = p[1]

    def p_empty(self, p):
        "empty : "

    def p_error(self, p):
        raise SyntaxError("Unexpected symbol '{}' at ({}, {})".format(
            p.value,
            p.lineno, find_column(p)
        ))
