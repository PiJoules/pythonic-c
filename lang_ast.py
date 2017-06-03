import inspect
import sys

from file_conversion import to_c_file
from lang_utils import SlottedClass, optional

INDENT = "    "


class TypeMixin(SlottedClass):
    """Mixin to indicate this node represents a type."""


class ValueMixin(SlottedClass):
    """Mixin to indicate this node represents a value."""


class StmtMixin(SlottedClass):
    """Mixin to indicate this node represents a statement."""


class Node(SlottedClass):
    __extra_attrs__ = {"lineno", "colno"}
    __types__ = {
        "lineno": int,
        "colno": int,
    }
    __defaults__ = {
        "lineno": -1,
        "colno": -1,
    }

    def lines(self):
        """
        Yields strings representing each line in the textual representation
        of this node. The tailing newline is excluded.
        """
        raise NotImplementedError("lines() not implemented for node {}".format(type(self)))

    def c_lines(self):
        """
        Same as lines() but each line is the C code equivalent.
        """
        raise NotImplementedError("c_lines() not implemented for node {}".format(type(self)))

    def c_code(self):
        return "\n".join(self.c_lines())

    def __str__(self):
        return "\n".join(self.lines())

    def loc(self):
        return self.lineno, self.colno


def ext_enumerate(iterable):
    """
    Yields:
        Any: the item
        idx: item index
        bool: if the element is last
    """
    it = iter(iterable)
    item = next(it)  # Raises Stopiteration if empty

    idx = 0
    try:
        next_item = next(it)
    except StopIteration:
        # Only 1 item
        yield item, idx, True
        return
    else:
        # Has at least 1 item
        yield item, idx, False

    while True:
        item = next_item
        idx += 1
        try:
            next_item = next(it)
        except StopIteration:
            # End of the iterable
            yield item, idx, True
            return
        else:
            # More items still
            yield item, idx, False


def iter_fields(node):
    for attr in node.__slots__:
        yield attr, getattr(node, attr)


def iter_indent_seq(seq, c_code=False):
    """Iterate through a sequence of nodes and indent each line in the node."""
    for node in seq:
        if c_code:
            for line in node.c_lines():
                yield INDENT + line
        else:
            for line in node.lines():
                yield INDENT + line


def dump_tree(node, indent_size=4):
    indent = " " * indent_size

    def _lines(node, attr=None):
        if attr:
            start = attr + "="
        else:
            start = ""

        if isinstance(node, Node):
            yield start + node.__class__.__name__ + ":"

            for attr, val in iter_fields(node):
                for line in _lines(val, attr=attr):
                    yield indent + line
        elif isinstance(node, (list, tuple)):
            if not node:
                yield start + "[]"
            elif len(node) == 1:
                for line, i, is_last in ext_enumerate(_lines(node[0])):
                    if not i:
                        line = start + "[" + line
                    else:
                        line = indent + line
                    if is_last:
                        line += "]"
                    yield line
            else:
                yield start + "["

                for elem in node:
                    for line in _lines(elem):
                        yield indent + line

                yield "]"
        elif isinstance(node, str):
            yield start + '"{}"'.format(node.replace('"', r'\"').replace("\n", r"\n"))
        else:
            yield start + str(node)

    return "\n".join(_lines(node))


################ Nodes #################


class Module(Node):
    __attrs__ = ("body", "filename")
    __types__ = {
        "body": [StmtMixin],
        "filename": optional(str),
    }
    __defaults__ = {
        "body": [],
        "filename": None,
    }

    def lines(self):
        for node in self.body:
            yield from node.lines()

    def c_lines(self):
        for node in self.body:
            yield from node.c_lines()


class NameType(Node, TypeMixin):
    __attrs__ = ("id", )
    __types__ = {"id": str}

    TYPE_NAME_CONVERSIONS = {
        "long": "long long",
        "uchar": "unsigned char",
        "ushort": "unsigned short",
        "uint": "unsigned int",
        "ulong": "unsigned long",
    }

    def lines(self):
        yield self.id

    def c_lines(self):
        """Different base types will be converted to other types."""
        yield self.TYPE_NAME_CONVERSIONS.get(self.id, self.id)


class VarDecl(Node, StmtMixin):
    __attrs__ = ("name", "type", "init")
    __types__ = {
        "name": str,
        "type": TypeMixin,
        "init": optional(ValueMixin),
    }
    __defaults__ = {"init": None}

    def lines(self):
        if self.init:
            yield "{}: {} = {}".format(self.name, self.type, self.init)
        else:
            yield "{}: {}".format(self.name, self.type)

    def c_lines(self):
        line = _format_c_decl(self.name, self.type)
        if self.init:
            line += " = {}".format(self.init.c_code())
        yield line


class Ellipsis(Node, TypeMixin):
    def lines(self):
        yield "..."

    def c_lines(self):
        yield "..."


class VarDeclStmt(Node, StmtMixin):
    __attrs__ = ("decl", )
    __types__ = {"decl": VarDecl}

    def lines(self):
        yield from self.decl.lines()

    def c_lines(self):
        yield self.decl.c_code() + ";"


class FuncDef(Node, StmtMixin):
    __attrs__ = ("name", "params", "body", "returns")
    __types__ = {
        "name": str,
        "params": [(str, VarDecl)],
        "body": [StmtMixin],
        "returns": optional(TypeMixin)
    }
    __defaults__ = {"returns": None}

    def lines(self):
        line1 = "def {}({})".format(
            self.name,
            ", ".join(map(str, self.params))
        )

        if self.returns:
            line1 += " -> {}:".format(self.returns)
        else:
            line1 += ":"

        yield line1
        yield from iter_indent_seq(self.body)

    def c_lines(self):
        # Check types
        assert self.returns is not None
        assert all(isinstance(p, VarDecl) for p in self.params)

        if isinstance(self.returns, str):
            return_s = self.returns
        else:
            return_s = self.returns.c_code()

        yield "{} {}({}){{".format(
            return_s,
            self.name,
            ", ".join(p.c_code() for p in self.params)
        )

        # Body
        yield from iter_indent_seq(self.body, c_code=True)

        yield "}"


class FuncDecl(Node, StmtMixin):
    __attrs__ = ("name", "params", "returns")
    __types__ = {
        "name": str,
        "params": [(VarDecl, Ellipsis)],
        "returns": TypeMixin
    }
    __defaults__ = {
        "returns": NameType("int"),
    }

    def lines(self):
        if self.returns:
            yield "def {}({}) -> {}".format(
                self.name,
                ", ".join(map(str, self.params)),
                self.returns
            )
        else:
            yield "def {}({})".format(
                self.name,
                ", ".join(map(str, self.params))
            )

    def c_lines(self):
        assert self.returns, "returns parameter expected for FuncDecl to produce c equivalent code"
        if isinstance(self.returns, str):
            returns = self.returns
        else:
            returns = self.returns.c_code()
        yield "{} {}({});".format(
            returns,
            self.name,
            ", ".join(p.c_code() for p in self.params)
        )

    def as_func_type(self):
        return FuncType([p.type if isinstance(p, VarDecl) else p for p in self.params], self.returns)


class FuncType(Node, TypeMixin):
    __attrs__ = ("params", "returns")
    __types__ = {
        "params": [(TypeMixin, Ellipsis)],
        "returns": TypeMixin
    }

    def lines(self):
        yield "({}) -> {}".format(
            ", ".join(map(str, self.params)),
            self.returns
        )

    def __hash__(self):
        return hash((
            tuple(self.params),
            self.returns
        ))


def _format_c_decl(name, t):
    """
    Format type declaration to C code

    Args:
        name (str): Name of the variable
        t (Node): The type of the variable
    """
    assert isinstance(t, TypeMixin)
    assert isinstance(name, str)

    if isinstance(t, Pointer):
        return _format_c_decl(
            "*" + name,
            t.contents
        )
    elif isinstance(t, Array):
        return _format_c_decl(
            name + "[{}]".format(t.size),
            t.contents
        )
    elif isinstance(t, NameType):
        return "{} {}".format(t.c_code(), name)
    elif isinstance(t, FuncType):
        params = t.params
        returns = t.returns
        return "{} (*{})({})".format(
            returns.c_code(),
            name,
            ", ".join(p.c_code() for p in params)
        )
    else:
        raise NotImplementedError(
            "Logic for _format_c_decl not implemented for TypeMixin '{}'"
            .format(type(t))
        )


def _format_container(node, sizes=None):
    """
    Fromat a heiarchy of arrays or nodes to print the sizes correctly.
    Works only on single line nodes for now.
    """
    sizes = sizes or []
    if isinstance(node, Array):
        sizes.append(node.size)
        return _format_container(node.contents, sizes=sizes)
    elif isinstance(node, Pointer):
        sizes.append(None)
        return _format_container(node.contents, sizes=sizes)
    else:
        s = ""
        for size in sizes:
            s += "[]" if size is None else "[{}]".format(size)
        if isinstance(node, FuncType):
            return "{{{}}}".format(node) + s
        else:
            return str(node) + s


class Array(Node, TypeMixin):
    __attrs__ = ("contents", "size")
    __types__ = {
        "contents": TypeMixin,
        "size": ValueMixin,
    }

    def lines(self):
        yield _format_container(self)

    def c_lines(self):
        size_s = self.size.c_code() if self.size else ""
        if isinstance(self.contents, str):
            yield "{}[{}]".format(
                self.contents,
                size_s
            )
        else:
            yield "{}[{}]".format(
                self.contents.c_code(),
                size_s
            )


class Pointer(Node, TypeMixin):
    __attrs__ = ("contents", )
    __types__ = {"contents": TypeMixin}

    def lines(self):
        yield _format_container(self)

    def c_lines(self):
        if isinstance(self.contents, str):
            yield "{}*".format(self.contents)
        else:
            yield "{}*".format(self.contents.c_code())

    def __hash__(self):
        return hash(self.contents)


class Deref(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "(*{})".format(self.value)

    def c_lines(self):
        yield "(*{})".format(self.value.c_code())


class StructPointerDeref(Node, ValueMixin):
    __attrs__ = ("value", "member")
    __types__ = {
        "value": ValueMixin,
        "member": str,
    }

    def lines(self):
        yield "{}->{}".format(self.value, self.member)

    def c_lines(self):
        yield "{}->{}".format(self.value.c_code(), self.member)


class StructMemberAccess(Node, ValueMixin):
    __attrs__ = ("value", "member")
    __types__ = {
        "value": ValueMixin,
        "member": str,
    }

    def lines(self):
        yield "{}.{}".format(self.value, self.member)

    def c_lines(self):
        yield "{}.{}".format(self.value.c_code(), self.member)


class ArrayLiteral(Node, ValueMixin):
    __attrs__ = ("contents", )
    __types__ = {"contents": [ValueMixin]}

    def lines(self):
        yield "[{}]".format(", ".join(map(str, self.contents)))

    def c_lines(self):
        yield "{{{}}}".format(", ".join(c.c_code() for c in self.contents))


# I did not make casting a ValueMixin b/c gcc kept throwing warnings saying
# "initialization makes {type} from pointer without a cast" and that that
# program will abort if that code is reached.
class Cast(Node, ValueMixin):
    __attrs__ = ("target_type", "expr")
    __types__ = {
        "target_type": TypeMixin,
        "expr": ValueMixin,
    }

    def lines(self):
        yield "(<{}>{})".format(self.target_type, self.expr)

    def c_lines(self):
        yield "(({}){})".format(
            self.target_type.c_code(),
            self.expr.c_code()
        )


class ExprStmt(Node, StmtMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield from self.value.lines()

    def c_lines(self):
        yield "{};".format(self.value.c_code())


class Assign(Node, StmtMixin):
    __attrs__ = ("left", "right")
    __types__ = {
        "left": ValueMixin,
        "right": ValueMixin,
    }

    def lines(self):
        yield "{} = {}".format(self.left, self.right)

    def c_lines(self):
        yield "{} = {};".format(self.left.c_code(), self.right.c_code())


class Return(Node, StmtMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        line_iter = self.value.lines()
        line1 = next(line_iter)
        yield "return {}".format(line1)
        for line in line_iter:
            yield INDENT + line

    def c_lines(self):
        yield "return {};".format(self.value)


class Pass(Node, StmtMixin):
    def lines(self):
        yield "pass"

    def c_lines(self):
        return
        yield


class Break(Node, StmtMixin):
    def lines(self):
        yield "break"

    def c_lines(self):
        yield "break;"


# TODO: Maybe add orelse to DoWhile???
class DoWhile(Node, StmtMixin):
    __attrs__ = ("test", "body")
    __types__ = {
        "test": ValueMixin,
        "body": [StmtMixin],
    }

    def lines(self):
        yield "dowhile {}:".format(self.test)
        yield from iter_indent_seq(self.body)

    def c_lines(self):
        yield "do {"
        yield from iter_indent_seq(self.body, c_code=True)
        yield "}} while ({});".format(self.test.c_code())


class While(Node, StmtMixin):
    __attrs__ = ("test", "body", "orelse")
    __types__ = {
        "test": ValueMixin,
        "body": [StmtMixin],
        "orelse": [StmtMixin]
    }
    __defaults__ = {"orelse": []}

    def lines(self):
        yield "while {}:".format(self.test)
        yield from iter_indent_seq(self.body)

        orelse = self.orelse
        if orelse:
            yield "else:"
            yield from iter_indent_seq(orelse)

    def c_lines(self):
        orelse = self.orelse

        if orelse:
            # Execute the else block if the test becomes false
            # This logic should be equivalent to executing the block if we do
            # not break out of the body
            """
while (1){
    if (test){
        // body
    }
    else {
        // orelse
        break;
    }
}
            """
            yield "while (1) {"

            if_stmt = If(self.test, self.body, orelse + [Break()])
            for line in if_stmt.c_lines():
                yield INDENT + line

            yield "}"
        else:
            # Regular while loop
            yield "while ({}) {{".format(self.test.c_code())
            yield from iter_indent_seq(self.body, c_code=True)
            yield "}"


class If(Node, StmtMixin):
    __attrs__ = ("test", "body", "orelse")
    __types__ = {
        "test": ValueMixin,
        "body": [StmtMixin],
        "orelse": [StmtMixin],
    }
    __defaults__ = {
        "orelse": [],
    }

    def lines(self):
        yield "if {}:".format(self.test)
        yield from iter_indent_seq(self.body)

        orelse = self.orelse
        if orelse:
            if len(orelse) == 1 and isinstance(orelse[0], If):
                # elif block
                for i, line in enumerate(orelse[0].lines()):
                    if not i:
                        yield "el" + line  # the elif part
                    else:
                        yield line
            else:
                # else block
                yield "else:"
                yield from iter_indent_seq(orelse)

    def c_lines(self):
        yield "if ({}) {{".format(self.test.c_code())
        yield from iter_indent_seq(self.body, c_code=True)
        yield "}"

        orelse = self.orelse
        if orelse:
            if len(orelse) == 1 and isinstance(orelse[0], If):
                # elif block
                for i, line in enumerate(orelse[0].c_lines()):
                    if not i:
                        yield "else " + line  # the elif part
                    else:
                        yield line
            else:
                # else block
                yield "else {"
                yield from iter_indent_seq(orelse, c_code=True)
                yield "}"


class Case(Node):
    """
    Cases will match the syntax proposed in this pep:
    https://www.python.org/dev/peps/pep-3103/#alternative-a
    """
    __attrs__ = ("tests", "body")
    __types__ = {
        "tests": [ValueMixin],
        "body": [StmtMixin],
    }

    def lines(self):
        yield "case {}:".format(", ".join(map(str, self.tests)))
        yield from iter_indent_seq(self.body)

    def c_lines(self):
        for case, i, is_last in ext_enumerate(self.tests):
            yield "case {}:".format(case.c_code())
            if is_last:
                yield from iter_indent_seq(self.body, c_code=True)


class Default(Node):
    __attrs__ = ("body", )
    __types__ = {"body": [StmtMixin]}

    def lines(self):
        yield "else:"
        yield from iter_indent_seq(self.body)

    def c_lines(self):
        yield "default:"
        yield from iter_indent_seq(self.body, c_code=True)


class Switch(Node, StmtMixin):
    __attrs__ = ("test", "cases")
    __types__ = {
        "test": ValueMixin,
        "cases": [(Case, Default)],
    }

    def lines(self):
        yield "switch {}:".format(self.test)
        yield from iter_indent_seq(self.cases)

    def c_lines(self):
        yield "switch ({}){{".format(self.test.c_code())
        yield from iter_indent_seq(self.cases, c_code=True)
        yield "}"


class BinaryOperator(Node):
    pass


class Add(BinaryOperator):
    def lines(self):
        yield "+"

    def c_lines(self):
        yield "+"


class Sub(BinaryOperator):
    def lines(self):
        yield "-"

    def c_lines(self):
        yield "-"


class Mult(BinaryOperator):
    def lines(self):
        yield "*"

    def c_lines(self):
        yield "*"


class Mod(BinaryOperator):
    def lines(self):
        yield "%"

    def c_lines(self):
        yield "%"


class Div(BinaryOperator):
    def lines(self):
        yield "/"

    def c_lines(self):
        yield "/"


class Eq(BinaryOperator):
    def lines(self):
        yield "=="

    def c_lines(self):
        yield "=="


class Ne(BinaryOperator):
    def lines(self):
        yield "!="

    def c_lines(self):
        yield "!="


class Lt(BinaryOperator):
    def lines(self):
        yield "<"

    def c_lines(self):
        yield "<"


class Gt(BinaryOperator):
    def lines(self):
        yield ">"

    def c_lines(self):
        yield ">"


class Le(BinaryOperator):
    def lines(self):
        yield "<="

    def c_lines(self):
        yield "<="


class Ge(BinaryOperator):
    def lines(self):
        yield ">="

    def c_lines(self):
        yield ">="


class And(BinaryOperator):
    def lines(self):
        yield "and"

    def c_lines(self):
        yield "&&"


class Or(BinaryOperator):
    def lines(self):
        yield "or"

    def c_lines(self):
        yield "||"


class BitAnd(BinaryOperator):
    def lines(self):
        yield "&"

    def c_lines(self):
        yield "&"


class BitOr(BinaryOperator):
    def lines(self):
        yield "|"

    def c_lines(self):
        yield "|"


class Xor(BinaryOperator):
    def lines(self):
        yield "^"

    def c_lines(self):
        yield "^"


class LShift(BinaryOperator):
    def lines(self):
        yield "<<"

    def c_lines(self):
        yield "<<"


class RShift(BinaryOperator):
    def lines(self):
        yield ">>"

    def c_lines(self):
        yield ">>"


# TODO: Make the operators Nodes instead of strings
class BinOp(Node, ValueMixin):
    __attrs__ = ("left", "op", "right")
    __types__ = {
        "left": ValueMixin,
        "op": BinaryOperator,
        "right": ValueMixin
    }

    def lines(self):
        yield "({} {} {})".format(self.left, self.op, self.right)

    def c_lines(self):
        yield "({} {} {})".format(self.left.c_code(),
                                  self.op.c_code(),
                                  self.right.c_code())


class IntegralOp(BinOp):
    """This operation only takes integral types and returns an integral type."""


class BitwiseOp(IntegralOp):
    pass


class LogicalOp(BinOp):
    """This node always infers to a boolean/int."""


class UnaryOperator(Node):
    pass


class UAdd(UnaryOperator):
    def lines(self):
        yield "+"

    def ic_lines(self):
        yield "+"


class USub(UnaryOperator):
    def lines(self):
        yield "-"

    def c_lines(self):
        yield "-"


class Not(UnaryOperator):
    def lines(self):
        yield "not"

    def c_lines(self):
        yield "!"


class Invert(UnaryOperator):
    def lines(self):
        yield "~"

    def c_lines(self):
        yield "~"


class UnaryOp(Node, ValueMixin):
    __attrs__ = ("op", "value")
    __types__ = {
        "value": ValueMixin,
        "op": UnaryOperator,
    }

    def lines(self):
        if isinstance(self.op, Not):
            yield "{} {}".format(self.op, self.value)
        else:
            yield "{}{}".format(self.op, self.value)

    def c_lines(self):
        yield "{}{}".format(self.op.c_code(), self.value.c_code())


class PostInc(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "{}++".format(self.value)

    def c_lines(self):
        yield "{}++".format(self.value.c_code())


class PostDec(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "{}--".format(self.value)

    def c_lines(self):
        yield "{}--".format(self.value.c_code())


class PreInc(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "(++{})".format(self.value)

    def c_lines(self):
        yield "(++{})".format(self.value.c_code())


class PreDec(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "(--{})".format(self.value)

    def c_lines(self):
        yield "(--{})".format(self.value.c_code())


class Call(Node, ValueMixin):
    __attrs__ = ("func", "args")
    __types__ = {
        "func": ValueMixin,
        "args": [ValueMixin]
    }
    __defaults__ = {"args": []}

    def lines(self):
        yield "{}({})".format(self.func, ", ".join(map(str, self.args)))

    def c_lines(self):
        yield "{}({})".format(self.func.c_code(), ", ".join(a.c_code() for a in self.args))


class Index(Node, ValueMixin):
    __attrs__ = ("value", "index")
    __types__ = {
        "value": ValueMixin,
        "index": ValueMixin,
    }

    def lines(self):
        yield "{}[{}]".format(self.value, self.index)

    def c_lines(self):
        yield "{}[{}]".format(self.value.c_code(), self.index.c_code())


class AddressOf(Node, ValueMixin):
    __attrs__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "&({})".format(self.value)

    def c_lines(self):
        yield "&({})".format(self.value.c_code())


class Name(Node, ValueMixin):
    __attrs__ = ("id", )
    __types__ = {
        "id": str,
    }

    def lines(self):
        yield str(self.id)

    def c_lines(self):
        yield str(self.id)


class Null(Node, ValueMixin):
    def lines(self):
        yield "NULL"

    def c_lines(self):
        yield "NULL"


class Int(Node, ValueMixin):
    __attrs__ = ("n", )
    __types__ = {"n": int}

    def lines(self):
        yield str(self.n)

    def c_lines(self):
        yield str(self.n)


class Float(Node, ValueMixin):
    __attrs__ = ("n", )
    __types__ = {"n": float}

    def lines(self):
        yield str(self.n)

    def c_lines(self):
        yield str(self.n)


class Str(Node, ValueMixin):
    __attrs__ = ("s", )
    __types__ = {"s": str}

    def lines(self):
        yield '"{}"'.format(
            self.s.replace('"', r'\"').replace("\n", "\\n")
        )

    def c_lines(self):
        yield '"{}"'.format(
            self.s.replace('"', r'\"').replace("\n", "\\n")
        )


class Char(Node, ValueMixin):
    __attrs__ = ("c", )
    __types__ = {"c": str}

    def lines(self):
        yield "'{}'".format(self.c)

    def c_lines(self):
        yield "'{}'".format(self.c)


class Enum(Node):
    __attrs__ = ("name", "members", )
    __types__ = {
        "name": str,
        "members": [str]
    }

    def lines(self):
        yield "enum {} {{{}}}".format(
            self.name,
            ", ".join(map(str, self.members))
        )

    def c_lines(self):
        yield "enum {} {{{}}}".format(
            self.name,
            ", ".join(map(str, self.members))
        )


class EnumDecl(Node, StmtMixin):
    __attrs__ = ("enum", )
    __types__ = {"enum": Enum}

    def lines(self):
        yield from self.enum.lines()

    def c_lines(self):
        yield "typedef enum {} {};".format(
            self.enum.name,
            self.enum.name
        )
        yield self.enum.c_code() + ";"


class TypeDefStmt(Node, StmtMixin):
    __attrs__ = ("type", "name")
    __types__ = {
        "type": TypeMixin,
        "name": str
    }

    def lines(self):
        yield "typedef {} {}".format(self.type, self.name)

    def c_lines(self):
        if isinstance(self.type, FuncType):
            yield "typedef {};".format(_format_c_decl(self.name, self.type))
        else:
            yield "typedef {} {};".format(self.type.c_code(), self.name)


class Struct(Node):
    __attrs__ = ("name", "decls")
    __types__ = {
        "name": str,
        "decls": [VarDecl],
    }

    def lines(self):
        yield "struct {} {{{}}}".format(
            self.name,
            ", ".join(map(str, self.decls))
        )

    def c_lines(self):
        yield "struct {} {{{}}}".format(
            self.name,
            "; ".join(n.c_code() for n in self.decls) + ";"
        )


class StructDecl(Node, StmtMixin):
    __attrs__ = ("struct", )
    __types__ = {"struct": Struct}

    def lines(self):
        yield from self.struct.lines()

    def c_lines(self):
        yield "typedef struct {} {};".format(
            self.struct.name,
            self.struct.name
        )
        yield self.struct.c_code() + ";"


##### Macros ######


class Macro(Node, StmtMixin):
    pass


class Define(Macro):
    __attrs__ = ("name", "value")
    __types__ = {
        "name": str,
        "value": optional(ValueMixin)
    }
    __defaults__ = {"value": None}

    def lines(self):
        if self.value:
            yield "define {} {}".format(self.name, self.value)
        else:
            yield "define {}".format(self.name)

    def c_lines(self):
        if self.value:
            yield "#define {} {}".format(self.name, self.value)
        else:
            yield "#define {}".format(self.name)


class CInclude(Macro):
    __attrs__ = ("path", )
    __types__ = {"path": str}

    def c_lines(self):
        yield '#include <{}>'.format(self.path)


class Include(Macro):
    __attrs__ = ("path", )
    __types__ = {"path": Str}

    def lines(self):
        yield 'include {}'.format(self.path)

    def c_lines(self):
        yield '#include "{}"'.format(to_c_file(self.path.s))


class Ifndef(Macro):
    __attrs__ = ("guard", )
    __types__ = {"guard": str}

    def lines(self):
        yield "ifndef {}".format(self.guard)

    def c_lines(self):
        yield "#ifndef {}".format(self.guard)


class Endif(Macro):
    def lines(self):
        yield "endif"

    def c_lines(self):
        yield "#endif"


######### Node Manipulators ###########

class NodeVisitor:
    def __init__(self, *, require_all=False):
        """
        Args:
            require_all (bool): If True, a RuntimeError is thrown when there is an
                attempt to visit a node for which there is no proper visit method.
                Otherwise, any child nodes of the node are visited and None is returned.
        """
        self.__require_all = require_all

    def visit(self, node):
        name = node.__class__.__name__
        method_name = "visit_" + name
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(node)
        elif self.__require_all:
            raise RuntimeError("No {} method implemented for type '{}'. Implement {}(self, node) to check this type of node".format(
                prefix,
                name,
                method_name
            ))
        else:
            self.visit_children(node)

    def visit_children(self, node):
        if isinstance(node, Node):
            for attr in node.__attrs__:
                val = getattr(node, attr)
                if val is not None:
                    self.visit(val)

    def visit_list(self, seq):
        return [self.visit(n) for n in seq]

    def visit_dict(self, d):
        return {k: self.visit(v) for k, v in d.items()}


# Get all nodes of specific mixins
def is_typemixin(obj):
    return (inspect.isclass(obj) and issubclass(obj, TypeMixin) and
            obj != TypeMixin)

TYPE_MIXINS = inspect.getmembers(sys.modules[__name__], is_typemixin)
