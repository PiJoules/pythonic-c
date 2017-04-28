# -----------------------------------------------------------------------------
# cparse.py
#
# Simple parser for ANSI C.  Based on the grammar in K&R, 2nd Ed.
# -----------------------------------------------------------------------------

import sys
import clex
import ply.yacc as yacc
import json

# Get the token map
tokens = clex.tokens

INDENT_SIZE = 4
INDENT = " " * INDENT_SIZE
FAKE_HEADERS = "fake_headers"


class SlotDefinedClass:
    __slots__ = tuple()

    def __init__(self, *args, **kwargs):
        for i, val in enumerate(args):
            setattr(self, self.__slots__[i], val)

        for attr in self.__slots__[len(args):]:
            setattr(self, attr, kwargs[attr])


class Node(SlotDefinedClass):
    def lines(self):
        """
        Yields strings that represent each line in the string representation
        of this node. The newline should not be included with each line.
        """
        raise NotImplementedError("lines() not implemented for {}".format(type(self)))

    def __str__(self):
        return "\n".join(self.lines())


class NodeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Node):
            d = {attr: getattr(obj, attr) for attr in obj.__slots__}
            d["__name__"] = obj.__class__.__name__
            return d

        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


def iter_fields(node):
    for attr in node.__slots__:
        yield attr, getattr(node, attr)


def iter_tracking(iterable):
    """
    Yields:
        Any: The item returned by the iterable
        bool: If the item is the first item in the iterable
        bool: If the item is the last item in the iterable
    """
    iter_ = iter(iterable)
    item = next(iter_)  # Raises Stopiteration if empty

    try:
        next_item = next(iter_)
    except StopIteration:
        # Iterable has only 1 item
        yield item, True, True
        return
    else:
        # Iterable has more than 1 item
        yield item, True, False

    while True:
        item = next_item
        try:
            next_item = next(iter_)
        except StopIteration:
            # Reached end
            yield item, False, True
            return
        else:
            # Has more
            yield item, False, False


def dump(node, indent_size=4):
    indent = indent_size * " "
    def _lines(node, attr=None):
        if isinstance(node, Node):
            if attr:
                yield attr + "=" + node.__class__.__name__ + ":"
            else:
                yield node.__class__.__name__ + ":"

            for attr, val in iter_fields(node):
                for line in _lines(val, attr=attr):
                    yield indent + line
        elif isinstance(node, list):
            if not node:
                if attr:
                    yield attr + "=[]"
                else:
                    yield "[]"
            else:
                if attr:
                    yield attr + "=["
                else:
                    yield "["

                for elem in node:
                    for line in _lines(elem):
                        yield indent + line

                yield "]"
        elif isinstance(node, str):
            line = "" if not attr else (attr + "=")
            yield line + '"{}"'.format(node.replace("\"", "\\\""))
        else:
            line = "" if not attr else (attr + "=")
            yield line + str(node)


    return "\n".join(_lines(node))


# translation-unit:
# Series of declarations


class Module(Node):
    __slots__ = ("body", )

    def lines(self):
        for decl in self.body:
            yield from decl.lines()
            yield ""  # Extra newline


def p_translation_unit_1(t):
    'translation_unit : external_declaration'
    t[0] = Module([t[1]])


def p_translation_unit_2(t):
    'translation_unit : translation_unit external_declaration'
    t[1].body.append(t[2])
    t[0] = t[1]


# external-declaration:
# Either a varuable declaration or definition;


def p_external_declaration_1(t):
    'external_declaration : function_definition'
    t[0] = t[1]


def p_external_declaration_2(t):
    'external_declaration : declaration'
    t[0] = t[1]


# function-definition:


class FuncDef(Node):
    """
int foo(int a, char *p)
{
    return 0;
}

"int" is the declaration specifier, "foo(int a, char*p)" is the declarator,
and the rest is the compound_statement
    """
    __slots__ = ("decl_specs", "declarator", "cmp_stmt")

    def lines(self):
        line1 = str(self.declarator)
        if self.decl_specs:
            line1 = str(self.decl_specs) + " " + line1
        yield line1

        yield from self.cmp_stmt.lines()


def p_function_definition_1(t):
    'function_definition : declarator compound_statement'
    t[0] = FuncDef(None, t[1], t[2])


def p_function_definition_2(t):
    'function_definition : declaration_specifiers declarator compound_statement'
    t[0] = FuncDef(t[1], t[2], t[3])


# declaration:


class Declaration(Node):
    __slots__ = ("decl_specs", "init_decl_lst")

    def lines(self):
        if self.init_decl_lst:
            yield "{} {};".format(
                self.decl_specs,
                ", ".join(map(str, self.init_decl_lst))
            )
        else:
            yield "{};".format(self.decl_specs)


def p_declaration_1(t):
    'declaration : declaration_specifiers init_declarator_list SEMI'
    t[0] = Declaration(t[1], t[2])


def p_declaration_2(t):
    'declaration : declaration_specifiers SEMI'
    t[0] = Declaration(t[1], [])

# declaration-list:


def p_declaration_list_1(t):
    'declaration_list : declaration'
    t[0] = [t[1]]


def p_declaration_list_2(t):
    'declaration_list : declaration_list declaration '
    t[0] = t[1] + [t[2]]

# declaration-specifiers

class StorageClassSpec(Node):
    __slots__ = ("storage_cls_spec", "decl_spec")

    def __str__(self):
        if self.decl_spec:
            return "{} {}".format(self.storage_cls_spec, self.decl_spec)
        else:
            return str(self.storage_cls_spec)


class TypeSpec(Node):
    __slots__ = ("type_spec", "decl_spec")

    def __str__(self):
        if self.decl_spec:
            return "{} {}".format(self.type_spec, self.decl_spec)
        else:
            return str(self.type_spec)


class TypeQualifier(Node):
    __slots__ = ("qualifier", "decl_spec")

    def __str__(self):
        if self.decl_spec:
            return "{} {}".format(self.qualifier, self.decl_spec)
        else:
            return str(self.qualifier)


def p_declaration_specifiers_1(t):
    'declaration_specifiers : storage_class_specifier declaration_specifiers'
    t[0] = StorageClassSpec(t[1], t[2])


def p_declaration_specifiers_2(t):
    'declaration_specifiers : type_specifier declaration_specifiers'
    t[0] = TypeSpec(t[1], t[2])


def p_declaration_specifiers_3(t):
    'declaration_specifiers : type_qualifier declaration_specifiers'
    t[0] = TypeQualifier(t[1], t[2])


def p_declaration_specifiers_4(t):
    'declaration_specifiers : storage_class_specifier'
    t[0] = StorageClassSpec(t[1], None)


def p_declaration_specifiers_5(t):
    'declaration_specifiers : type_specifier'
    t[0] = t[1]


def p_declaration_specifiers_6(t):
    'declaration_specifiers : type_qualifier'
    t[0] = TypeQualifier(t[1], None)


# storage-class-specifier


def p_storage_class_specifier(t):
    '''storage_class_specifier : AUTO
                               | REGISTER
                               | STATIC
                               | EXTERN
                               | TYPEDEF
                               '''
    t[0] = str(t[1])

# type-specifier:


def p_type_specifier_1(t):
    '''type_specifier : VOID
                      | CHAR
                      | SHORT
                      | INT
                      | LONG
                      | FLOAT
                      | DOUBLE
                      | SIGNED
                      | UNSIGNED
                      | struct_or_union_specifier
                      | enum_specifier
                      | TYPEID
                      '''
    t[0] = str(t[1])

# type-qualifier:


def p_type_qualifier(t):
    '''type_qualifier : CONST
                      | VOLATILE'''
    t[0] = str(t[1])

# struct-or-union-specifier


def p_struct_or_union_specifier_1(t):
    'struct_or_union_specifier : struct_or_union ID LBRACE struct_declaration_list RBRACE'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_or_union_specifier_2(t):
    'struct_or_union_specifier : struct_or_union LBRACE struct_declaration_list RBRACE'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_or_union_specifier_3(t):
    'struct_or_union_specifier : struct_or_union ID'
    raise NotImplementedError("handling not implemented for current parser rule")

# struct-or-union:


def p_struct_or_union(t):
    '''struct_or_union : STRUCT
                       | UNION
                       '''
    raise NotImplementedError("handling not implemented for current parser rule")

# struct-declaration-list:


def p_struct_declaration_list_1(t):
    'struct_declaration_list : struct_declaration'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_declaration_list_2(t):
    'struct_declaration_list : struct_declaration_list struct_declaration'
    raise NotImplementedError("handling not implemented for current parser rule")

# init-declarator-list:


def p_init_declarator_list_1(t):
    'init_declarator_list : init_declarator'
    t[0] = [t[1]]


def p_init_declarator_list_2(t):
    'init_declarator_list : init_declarator_list COMMA init_declarator'
    t[1].append(t[2])
    t[0] = t[1]

# init-declarator


class InitDeclarator(Node):
    __slots__ = ("declarator", "initializer")

    def lines(self):
        if self.initializer:
            yield "{} = {}".format(self.declarator, self.initializer)
        else:
            yield str(self.declarator)


def p_init_declarator_1(t):
    'init_declarator : declarator'
    t[0] = InitDeclarator(t[1], None)


def p_init_declarator_2(t):
    'init_declarator : declarator EQUALS initializer'
    t[0] = InitDeclarator(t[1], t[3])

# struct-declaration:


def p_struct_declaration(t):
    'struct_declaration : specifier_qualifier_list struct_declarator_list SEMI'
    raise NotImplementedError("handling not implemented for current parser rule")

# specifier-qualifier-list:


def p_specifier_qualifier_list_1(t):
    'specifier_qualifier_list : type_specifier specifier_qualifier_list'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_specifier_qualifier_list_2(t):
    'specifier_qualifier_list : type_specifier'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_specifier_qualifier_list_3(t):
    'specifier_qualifier_list : type_qualifier specifier_qualifier_list'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_specifier_qualifier_list_4(t):
    'specifier_qualifier_list : type_qualifier'
    raise NotImplementedError("handling not implemented for current parser rule")

# struct-declarator-list:


def p_struct_declarator_list_1(t):
    'struct_declarator_list : struct_declarator'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_declarator_list_2(t):
    'struct_declarator_list : struct_declarator_list COMMA struct_declarator'
    raise NotImplementedError("handling not implemented for current parser rule")

# struct-declarator:


def p_struct_declarator_1(t):
    'struct_declarator : declarator'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_declarator_2(t):
    'struct_declarator : declarator COLON constant_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_struct_declarator_3(t):
    'struct_declarator : COLON constant_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# enum-specifier:


def p_enum_specifier_1(t):
    'enum_specifier : ENUM ID LBRACE enumerator_list RBRACE'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_enum_specifier_2(t):
    'enum_specifier : ENUM LBRACE enumerator_list RBRACE'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_enum_specifier_3(t):
    'enum_specifier : ENUM ID'
    raise NotImplementedError("handling not implemented for current parser rule")

# enumerator_list:


def p_enumerator_list_1(t):
    'enumerator_list : enumerator'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_enumerator_list_2(t):
    'enumerator_list : enumerator_list COMMA enumerator'
    raise NotImplementedError("handling not implemented for current parser rule")

# enumerator:


def p_enumerator_1(t):
    'enumerator : ID'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_enumerator_2(t):
    'enumerator : ID EQUALS constant_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# declarator:


class Declarator(Node):
    __slots__ = ("pntr", "direct_declarator")

    def lines(self):
        if self.pntr:
            yield "{}{}".format(self.pntr, self.direct_declarator)
        else:
            yield str(self.direct_declarator)


def p_declarator_1(t):
    'declarator : pointer direct_declarator'
    t[0] = Declarator(t[1], t[2])


def p_declarator_2(t):
    'declarator : direct_declarator'
    t[0] = t[1]


# direct-declarator:


class FuncDeclarator(Node):
    __slots__ = ("direct_declarator", "args")

    def lines(self):
        yield "{}({})".format(
            self.direct_declarator,
            ", ".join(map(str, self.args))
        )


class MainFuncDeclarator(FuncDeclarator):
    def __init__(self, decltor, args):
        if not args:
            # Empty args
            pass
        elif len(args) == 2:
            # argc, argv
            argc = self.__check_argc(args[0])
            argv = self.__check_argv(args[1])
            args = [argc, argv]
        else:
            raise RuntimeError("program entry point expects either 0 or 2 arguments")

        super().__init__(decltor, args)

    def __check_argc(self, node):
        if isinstance(node, str):
            return ParamDecl("int", node)
        elif isinstance(node, ParamDecl):
            assert node.decl_specs == "int"
            return node
        else:
            raise RuntimeError("Expected ParamDecl for FuncDeclarator arguments. Got {}".format(node))

    def __check_argv(self, node):
        return node

        if isinstance(node, str):
            return ParamDecl("int", node)
        elif isinstance(node, ParamDecl):
            assert node.decl_specs == "int"
            return node
        else:
            raise RuntimeError("Expected ParamDecl for FuncDeclarator arguments. Got {}".format(node))


def create_func_declarator(decltor, args):
    if decltor == "main":
        # Program entry point
        return MainFuncDeclarator(decltor, args)

    return FuncDeclarator(decltor, args)


class ArrayDeclarator(Node):
    __slots__ = ("direct_declarator", "size")

    def __str__(self):
        return "{}[{}]".format(self.direct_declarator, self.size)


def p_direct_declarator_1(t):
    'direct_declarator : ID'
    t[0] = t[1]


def p_direct_declarator_2(t):
    'direct_declarator : LPAREN declarator RPAREN'
    t[0] = t[2]


def p_direct_declarator_3(t):
    'direct_declarator : direct_declarator LBRACKET constant_expression_opt RBRACKET'
    t[0] = ArrayDeclarator(t[1], t[3])


def p_direct_declarator_4(t):
    'direct_declarator : direct_declarator LPAREN parameter_type_list RPAREN '
    t[0] = create_func_declarator(t[1], t[3])


def p_direct_declarator_5(t):
    'direct_declarator : direct_declarator LPAREN RPAREN '
    t[0] = create_func_declarator(t[1], [])

# pointer:


class Pointer(Node):
    __slots__ = ("type_qualifiers", "val")

    def lines(self):
        line = "*"
        if self.type_qualifiers:
            line += " " + " ".join(map(str, self.type_qualifiers)) + " "
        if self.val:
            line += str(self.val)
        yield line


def p_pointer_1(t):
    'pointer : TIMES type_qualifier_list'
    t[0] = Pointer(t[2], None)


def p_pointer_2(t):
    'pointer : TIMES'
    t[0] = Pointer([], None)


def p_pointer_3(t):
    'pointer : TIMES type_qualifier_list pointer'
    t[0] = Pointer(t[2], t[3])


def p_pointer_4(t):
    'pointer : TIMES pointer'
    t[0] = Pointer([], t[2])

# type-qualifier-list:


def p_type_qualifier_list_1(t):
    'type_qualifier_list : type_qualifier'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_type_qualifier_list_2(t):
    'type_qualifier_list : type_qualifier_list type_qualifier'
    raise NotImplementedError("handling not implemented for current parser rule")

# parameter-type-list:


class Ellipsis(Node):
    def lines(self):
        yield "..."


def p_parameter_type_list_1(t):
    'parameter_type_list : parameter_list'
    t[0] = t[1]


def p_parameter_type_list_2(t):
    'parameter_type_list : parameter_list COMMA ELLIPSIS'
    t[0] = t[1] + [Ellipsis()]

# parameter-list:


def p_parameter_list_1(t):
    'parameter_list : parameter_declaration'
    t[0] = [t[1]]


def p_parameter_list_2(t):
    'parameter_list : parameter_list COMMA parameter_declaration'
    t[0] = t[1] + [t[3]]

# parameter-declaration:


class ParamDecl(Node):
    __slots__ = ("decl_specs", "declarator")

    def lines(self):
        yield "{} {}".format(self.decl_specs, self.declarator)


def p_parameter_declaration_1(t):
    "parameter_declaration : ID"
    t[0] = t[1]

def p_parameter_declaration_2(t):
    'parameter_declaration : declaration_specifiers declarator'
    t[0] = ParamDecl(t[1], t[2])


def p_parameter_declaration_3(t):
    'parameter_declaration : declaration_specifiers abstract_declarator_opt'
    t[0] = ParamDecl(t[1], t[2])



# identifier-list:


#def p_identifier_list_1(t):
#    'identifier_list : ID'
#    t[0] = [t[1]]
#
#
#def p_identifier_list_2(t):
#    'identifier_list : identifier_list COMMA ID'
#    t[0] = t[1] + [t[3]]

# initializer:


class ArrayLiteral(Node):
    __slots__ = ("elts", )

    def lines(self):
        yield "{" + ", ".join(map(str, self.elts)) + "}"


def p_initializer_1(t):
    'initializer : assignment_expression'
    t[0] = t[1]


def p_initializer_2(t):
    '''initializer : LBRACE initializer_list RBRACE
                   | LBRACE initializer_list COMMA RBRACE'''
    t[0] = ArrayLiteral(t[1])

# initializer-list:


def p_initializer_list_1(t):
    'initializer_list : initializer'
    t[0] = [t[1]]


def p_initializer_list_2(t):
    'initializer_list : initializer_list COMMA initializer'
    t[1].append(t[2])
    t[0] = t[1]

# type-name:


def p_type_name(t):
    'type_name : specifier_qualifier_list abstract_declarator_opt'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_abstract_declarator_opt_1(t):
    'abstract_declarator_opt : empty'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_abstract_declarator_opt_2(t):
    'abstract_declarator_opt : abstract_declarator'
    raise NotImplementedError("handling not implemented for current parser rule")

# abstract-declarator:


def p_abstract_declarator_1(t):
    'abstract_declarator : pointer '
    raise NotImplementedError("handling not implemented for current parser rule")


def p_abstract_declarator_2(t):
    'abstract_declarator : pointer direct_abstract_declarator'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_abstract_declarator_3(t):
    'abstract_declarator : direct_abstract_declarator'
    raise NotImplementedError("handling not implemented for current parser rule")

# direct-abstract-declarator:


def p_direct_abstract_declarator_1(t):
    'direct_abstract_declarator : LPAREN abstract_declarator RPAREN'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_direct_abstract_declarator_2(t):
    'direct_abstract_declarator : direct_abstract_declarator LBRACKET constant_expression_opt RBRACKET'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_direct_abstract_declarator_3(t):
    'direct_abstract_declarator : LBRACKET constant_expression_opt RBRACKET'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_direct_abstract_declarator_4(t):
    'direct_abstract_declarator : direct_abstract_declarator LPAREN parameter_type_list_opt RPAREN'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_direct_abstract_declarator_5(t):
    'direct_abstract_declarator : LPAREN parameter_type_list_opt RPAREN'
    raise NotImplementedError("handling not implemented for current parser rule")

# Optional fields in abstract declarators


def p_constant_expression_opt_1(t):
    'constant_expression_opt : empty'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_constant_expression_opt_2(t):
    'constant_expression_opt : constant_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_parameter_type_list_opt_1(t):
    'parameter_type_list_opt : empty'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_parameter_type_list_opt_2(t):
    'parameter_type_list_opt : parameter_type_list'
    raise NotImplementedError("handling not implemented for current parser rule")

# statement:


def p_statement(t):
    '''
    statement : labeled_statement
              | expression_statement
              | compound_statement
              | selection_statement
              | iteration_statement
              | jump_statement
              '''
    t[0] = t[1]

# labeled-statement:


def p_labeled_statement_1(t):
    'labeled_statement : ID COLON statement'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_labeled_statement_2(t):
    'labeled_statement : CASE constant_expression COLON statement'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_labeled_statement_3(t):
    'labeled_statement : DEFAULT COLON statement'
    raise NotImplementedError("handling not implemented for current parser rule")

# expression-statement:


class ExprStmt(Node):
    __slots__ = ("expr", )

    def lines(self):
        yield "{};".format(self.expr)


def p_expression_statement(t):
    'expression_statement : expression_opt SEMI'
    t[0] = ExprStmt(t[1])

# compound-statement:


class CompoundStmt(Node):
    __slots__ = ("decl_lst", "stmt_lst")

    def lines(self):
        yield "{"

        for decl in self.decl_lst:
            for line in decl.lines():
                yield INDENT + line

        for stmt in self.stmt_lst:
            yield INDENT + str(stmt)

        yield "}"


def p_compound_statement_1(t):
    'compound_statement : LBRACE declaration_list statement_list RBRACE'
    t[0] = CompoundStmt(t[1], t[2])


def p_compound_statement_2(t):
    'compound_statement : LBRACE statement_list RBRACE'
    t[0] = CompoundStmt([], t[2])


def p_compound_statement_3(t):
    'compound_statement : LBRACE declaration_list RBRACE'
    t[0] = CompoundStmt(t[1], [])


def p_compound_statement_4(t):
    'compound_statement : LBRACE RBRACE'
    t[0] = CompoundStmt([], [])


# statement-list:


def p_statement_list_1(t):
    'statement_list : statement'
    t[0] = [t[1]]


def p_statement_list_2(t):
    'statement_list : statement_list statement'
    t[0] = t[1] + [t[2]]

# selection-statement


def p_selection_statement_1(t):
    'selection_statement : IF LPAREN expression RPAREN statement'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_selection_statement_2(t):
    'selection_statement : IF LPAREN expression RPAREN statement ELSE statement '
    raise NotImplementedError("handling not implemented for current parser rule")


def p_selection_statement_3(t):
    'selection_statement : SWITCH LPAREN expression RPAREN statement '
    raise NotImplementedError("handling not implemented for current parser rule")

# iteration_statement:


def p_iteration_statement_1(t):
    'iteration_statement : WHILE LPAREN expression RPAREN statement'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_iteration_statement_2(t):
    'iteration_statement : FOR LPAREN expression_opt SEMI expression_opt SEMI expression_opt RPAREN statement '
    raise NotImplementedError("handling not implemented for current parser rule")


def p_iteration_statement_3(t):
    'iteration_statement : DO statement WHILE LPAREN expression RPAREN SEMI'
    raise NotImplementedError("handling not implemented for current parser rule")

# jump_statement:


class Return(Node):
    __slots__ = ("expr", )

    def lines(self):
        yield "return {};".format(self.expr)


def p_jump_statement_1(t):
    'jump_statement : GOTO ID SEMI'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_jump_statement_2(t):
    'jump_statement : CONTINUE SEMI'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_jump_statement_3(t):
    'jump_statement : BREAK SEMI'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_jump_statement_4(t):
    'jump_statement : RETURN expression_opt SEMI'
    t[0] = Return(t[2])


def p_expression_opt_1(t):
    'expression_opt : empty'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_expression_opt_2(t):
    'expression_opt : expression'
    t[0] = t[1]

# expression:


def p_expression_1(t):
    'expression : assignment_expression'
    t[0] = t[1]


def p_expression_2(t):
    'expression : expression COMMA assignment_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# assigment_expression:


def p_assignment_expression_1(t):
    'assignment_expression : conditional_expression'
    t[0] = t[1]


def p_assignment_expression_2(t):
    'assignment_expression : unary_expression assignment_operator assignment_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# assignment_operator:


def p_assignment_operator(t):
    '''
    assignment_operator : EQUALS
                        | TIMESEQUAL
                        | DIVEQUAL
                        | MODEQUAL
                        | PLUSEQUAL
                        | MINUSEQUAL
                        | LSHIFTEQUAL
                        | RSHIFTEQUAL
                        | ANDEQUAL
                        | OREQUAL
                        | XOREQUAL
                        '''
    raise NotImplementedError("handling not implemented for current parser rule")

# conditional-expression


def p_conditional_expression_1(t):
    'conditional_expression : logical_or_expression'
    t[0] = t[1]


def p_conditional_expression_2(t):
    'conditional_expression : logical_or_expression CONDOP expression COLON conditional_expression '
    raise NotImplementedError("handling not implemented for current parser rule")

# constant-expression


def p_constant_expression(t):
    'constant_expression : conditional_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# logical-or-expression


def p_logical_or_expression_1(t):
    'logical_or_expression : logical_and_expression'
    t[0] = t[1]


def p_logical_or_expression_2(t):
    'logical_or_expression : logical_or_expression LOR logical_and_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# logical-and-expression


def p_logical_and_expression_1(t):
    'logical_and_expression : inclusive_or_expression'
    t[0] = t[1]


def p_logical_and_expression_2(t):
    'logical_and_expression : logical_and_expression LAND inclusive_or_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# inclusive-or-expression:


def p_inclusive_or_expression_1(t):
    'inclusive_or_expression : exclusive_or_expression'
    t[0] = t[1]


def p_inclusive_or_expression_2(t):
    'inclusive_or_expression : inclusive_or_expression OR exclusive_or_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# exclusive-or-expression:


def p_exclusive_or_expression_1(t):
    'exclusive_or_expression :  and_expression'
    t[0] = t[1]


def p_exclusive_or_expression_2(t):
    'exclusive_or_expression :  exclusive_or_expression XOR and_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# AND-expression


def p_and_expression_1(t):
    'and_expression : equality_expression'
    t[0] = t[1]


def p_and_expression_2(t):
    'and_expression : and_expression AND equality_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


# equality-expression:
def p_equality_expression_1(t):
    'equality_expression : relational_expression'
    t[0] = t[1]


def p_equality_expression_2(t):
    'equality_expression : equality_expression EQ relational_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_equality_expression_3(t):
    'equality_expression : equality_expression NE relational_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


# relational-expression:
def p_relational_expression_1(t):
    'relational_expression : shift_expression'
    t[0] = t[1]


def p_relational_expression_2(t):
    'relational_expression : relational_expression LT shift_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_relational_expression_3(t):
    'relational_expression : relational_expression GT shift_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_relational_expression_4(t):
    'relational_expression : relational_expression LE shift_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_relational_expression_5(t):
    'relational_expression : relational_expression GE shift_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# shift-expression


def p_shift_expression_1(t):
    'shift_expression : additive_expression'
    t[0] = t[1]


def p_shift_expression_2(t):
    'shift_expression : shift_expression LSHIFT additive_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_shift_expression_3(t):
    'shift_expression : shift_expression RSHIFT additive_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# additive-expression


def p_additive_expression_1(t):
    'additive_expression : multiplicative_expression'
    t[0] = t[1]


def p_additive_expression_2(t):
    'additive_expression : additive_expression PLUS multiplicative_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_additive_expression_3(t):
    'additive_expression : additive_expression MINUS multiplicative_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# multiplicative-expression


def p_multiplicative_expression_1(t):
    'multiplicative_expression : cast_expression'
    t[0] = t[1]


def p_multiplicative_expression_2(t):
    'multiplicative_expression : multiplicative_expression TIMES cast_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_multiplicative_expression_3(t):
    'multiplicative_expression : multiplicative_expression DIVIDE cast_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_multiplicative_expression_4(t):
    'multiplicative_expression : multiplicative_expression MOD cast_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# cast-expression:


def p_cast_expression_1(t):
    'cast_expression : unary_expression'
    t[0] = t[1]


def p_cast_expression_2(t):
    'cast_expression : LPAREN type_name RPAREN cast_expression'
    raise NotImplementedError("handling not implemented for current parser rule")

# unary-expression:


def p_unary_expression_1(t):
    'unary_expression : postfix_expression'
    t[0] = t[1]


def p_unary_expression_2(t):
    'unary_expression : PLUSPLUS unary_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_unary_expression_3(t):
    'unary_expression : MINUSMINUS unary_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_unary_expression_4(t):
    'unary_expression : unary_operator cast_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_unary_expression_5(t):
    'unary_expression : SIZEOF unary_expression'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_unary_expression_6(t):
    'unary_expression : SIZEOF LPAREN type_name RPAREN'
    raise NotImplementedError("handling not implemented for current parser rule")

# unary-operator


def p_unary_operator(t):
    '''unary_operator : AND
                    | TIMES
                    | PLUS
                    | MINUS
                    | NOT
                    | LNOT '''
    raise NotImplementedError("handling not implemented for current parser rule")

# postfix-expression:


class FuncCall(Node):
    __slots__ = ("func", "args")

    def lines(self):
        yield "{}({})".format(self.func, ", ".join(map(str, self.args)))


def p_postfix_expression_1(t):
    'postfix_expression : primary_expression'
    t[0] = t[1]


def p_postfix_expression_2(t):
    'postfix_expression : postfix_expression LBRACKET expression RBRACKET'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_postfix_expression_3(t):
    'postfix_expression : postfix_expression LPAREN argument_expression_list RPAREN'
    t[0] = FuncCall(t[1], t[3])


def p_postfix_expression_4(t):
    'postfix_expression : postfix_expression LPAREN RPAREN'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_postfix_expression_5(t):
    'postfix_expression : postfix_expression PERIOD ID'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_postfix_expression_6(t):
    'postfix_expression : postfix_expression ARROW ID'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_postfix_expression_7(t):
    'postfix_expression : postfix_expression PLUSPLUS'
    raise NotImplementedError("handling not implemented for current parser rule")


def p_postfix_expression_8(t):
    'postfix_expression : postfix_expression MINUSMINUS'
    raise NotImplementedError("handling not implemented for current parser rule")

# primary-expression:


def p_primary_expression_1(t):
    '''primary_expression :  ID
                        |  constant
                        |  SCONST '''
    t[0] = t[1]


def p_primary_expression_2(t):
    '''primary_expression : LPAREN expression RPAREN'''
    raise NotImplementedError("handling not implemented for current parser rule")


# argument-expression-list:


def p_argument_expression_list_1(t):
    '''argument_expression_list : assignment_expression'''
    t[0] = [t[1]]


def p_argument_expression_list_2(t):
    '''argument_expression_list : argument_expression_list COMMA assignment_expression'''
    t[0] = t[1] + [t[2]]


# constant:


def p_constant(t):
    '''constant : ICONST
               | FCONST
               | CCONST'''
    s = t[1]
    if s.isdigit():
        t[0] = int(s)
    else:
        raise NotImplementedError("handling not implemented for current parser rule")


def p_empty(t):
    'empty : '
    raise NotImplementedError("handling not implemented for current parser rule")


def p_error(t):
    raise RuntimeError("Unable to parse: {}".format(t))


def change_to_c_file(filename):
    import shutil
    if filename.endswith(".c"):
        return filename

    #newname = ".".join(filename.split(".")[:-1]) + ".c"
    newname = filename + ".c"

    shutil.copyfile(filename, newname)

    return newname


def preprocess_file(filename, compiler="gcc", output=None, extra_flags=""):
    import subprocess, os.path

    filename = change_to_c_file(filename)

    if not output:
        parts = filename.split(".")
        output = ".".join(parts[:-1]) + "_pp.c"

    subprocess.run(
        "{compiler} -Werror -E {filename} -o {output} -nostdinc {extra_flags} -I {fake_headers}".format(
            fake_headers=FAKE_HEADERS,
            **locals()
        ).split(),
        check=True
    )

    if not os.path.isfile(output):
        raise RuntimeError("Could not create {}".format(output))

    return output


def get_args():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-d", "--dump", default=False,
                        action="store_true")
    parser.add_argument("-j", "--json", default=False,
                        action="store_true")
    parser.add_argument("-t", "--text", default=False,
                        action="store_true")

    return parser.parse_args()


def main():
    args = get_args()

    parser = yacc.yacc()

    if args.text:
        c_ast = parser.parse(args.input)
    else:
        out_filename = preprocess_file(args.input)
        with open(out_filename) as f:
            c_ast = parser.parse(f.read())

    if args.json:
        print(json.dumps(c_ast, indent=INDENT_SIZE, cls=NodeEncoder))
    elif args.dump:
        print(dump(c_ast))
    else:
        print(c_ast)


if __name__ == "__main__":
    main()
