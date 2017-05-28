from file_conversion import to_c_file
from lang_utils import *

import os


INDENT = "    "


class TypeMixin:
    """Mixin to indicate this node represents a type."""


class ValueMixin:
    """Mixin to indicate this node represents a value."""


LANG_TYPES = (str, TypeMixin)


class NodeChecker(SlottedClassChecker):
    def __init__(cls, *args):
        super().__init__(*args)

        #assert "lines" in cls.__dict__
        #assert "c_lines" in cls.__dict__


class Node(SlottedClass, metaclass=NodeChecker):
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


def assert_node(n):
    assert isinstance(n, Node), "Expected Node. Got {}".format(n)


def assert_contains_nodes(seq):
    assert isinstance(seq, (list, tuple)), "Expected list or tuple for sequence. Got {}".format(type(seq))
    for n in seq:
        assert_node(n)


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
    __slots__ = ("body", "filename")
    __types__ = {
        "body": [Node],
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


class VarDecl(Node):
    __slots__ = ("name", "type", "init")
    __types__ = {
        "name": str,
        "type": LANG_TYPES,
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


class Ellipsis(Node):
    def lines(self):
        yield "..."

    def c_lines(self):
        yield "..."


class VarDeclStmt(Node):
    __slots__ = ("decl", )
    __types__ = {"decl": VarDecl}

    def lines(self):
        yield from self.decl.lines()

    def c_lines(self):
        yield self.decl.c_code() + ";"


class FuncDef(Node):
    __slots__ = ("name", "params", "body", "returns")
    __types__ = {
        "name": str,
        "params": [(str, VarDecl)],
        "body": [Node],
        "returns": optional(LANG_TYPES)
    }

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
        for node in self.body:
            for line in node.lines():
                yield INDENT + line

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
        for node in self.body:
            for line in node.c_lines():
                yield INDENT + line

        yield "}"


class FuncDecl(Node):
    __slots__ = ("name", "params", "returns")
    __types__ = {
        "name": str,
        "params": [(VarDecl, Ellipsis)],
        "returns": LANG_TYPES
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

    def type(self):
        return FuncType([p if isinstance(p, Ellipsis) else p.type for p in self.params], self.returns)


class FuncType(Node, TypeMixin):
    __slots__ = ("params", "returns")
    __types__ = {
        "params": [(LANG_TYPES, Ellipsis)],
        "returns": LANG_TYPES
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
    assert isinstance(t, LANG_TYPES)
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
    elif isinstance(t, str):
        return "{} {}".format(t, name)
    else:
        params = t.params
        returns = t.returns
        return "{} (*{})({})".format(
            returns.c_code(),
            name,
            ", ".join(p.c_code() for p in params)
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
    __slots__ = ("contents", "size")

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
    __slots__ = ("contents", )
    __types__ = {"contents": LANG_TYPES}

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
    __slots__ = ("value", )

    def lines(self):
        yield "*{}".format(self.value)

    def c_lines(self):
        yield "*{}".format(self.value.c_code())


class StructPointerDeref(Node, ValueMixin):
    __slots__ = ("value", "member")
    __types__ = {
        "value": ValueMixin,
        "member": str,
    }

    def lines(self):
        yield "{}->{}".format(self.value, self.member)

    def c_lines(self):
        yield "{}->{}".format(self.value.c_code(), self.member)


class ArrayLiteral(Node, ValueMixin):
    __slots__ = ("contents", )

    def lines(self):
        yield "[{}]".format(", ".join(map(str, self.contents)))


class Cast(Node, ValueMixin):
    __slots__ = ("target_type", "expr")
    __types__ = {
        "target_type": LANG_TYPES,
    }

    def lines(self):
        yield "<{}>{}".format(self.target_type, self.expr)

    def c_lines(self):
        yield "({}){}".format(
            self.target_type.c_code(),
            self.expr.c_code()
        )


class ExprStmt(Node):
    __slots__ = ("value", )

    def lines(self):
        yield from self.value.lines()

    def c_lines(self):
        yield "{};".format(self.value.c_code())


class Assign(Node):
    __slots__ = ("left", "right")
    __types__ = {
        "left": ValueMixin,
        "right": ValueMixin,
    }

    def lines(self):
        yield "{} = {}".format(self.left, self.right)

    def c_lines(self):
        yield "{} = {};".format(self.left.c_code(), self.right.c_code())


class Return(Node):
    __slots__ = ("value", )

    def lines(self):
        line_iter = self.value.lines()
        line1 = next(line_iter)
        yield "return {}".format(line1)
        for line in line_iter:
            yield INDENT + line

    def c_lines(self):
        yield "return {};".format(self.value)


class Pass(Node):
    def lines(self):
        yield "pass"

    def c_lines(self):
        return
        yield


class Break(Node):
    def lines(self):
        yield "break"

    def c_lines(self):
        yield "break;"


class DoWhile(Node):
    __slots__ = ("test", "body")
    __types__ = {
        "test": Node,
        "body": [Node],
    }

    def lines(self):
        yield "do:"

        for node in self.body:
            for line in node.lines():
                yield INDENT + line

        yield "while {}".format(self.test)

    def c_lines(self):
        yield "do {"

        for node in self.body:
            for line in node.c_lines():
                yield INDENT + line

        yield "}} while ({});".format(self.test.c_code())


class While(Node):
    __slots__ = ("test", "body", "orelse")
    __types__ = {
        "test": Node,
        "body": [Node],
        "orelse": [Node]
    }
    __defaults__ = {"orelse": []}

    def lines(self):
        yield "while {}:".format(self.test)
        for node in self.body:
            for line in node.lines():
                yield INDENT + line

        orelse = self.orelse
        if orelse:
            yield "else:"
            for node in orelse:
                for line in node.lines():
                    yield INDENT + line

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

            for node in self.body:
                for line in node.c_lines():
                    yield INDENT + line

            yield "}"


class If(Node):
    __slots__ = ("test", "body", "orelse")
    __types__ = {
        "test": ValueMixin,
        "body": [Node],
        "orelse": [Node],
    }

    def lines(self):
        yield "if {}:".format(self.test)
        for node in self.body:
            for line in node.lines():
                yield INDENT + line

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
                for node in orelse:
                    for line in node.lines():
                        yield INDENT + line


    def c_lines(self):
        yield "if ({}) {{".format(self.test.c_code())

        for node in self.body:
            for line in node.c_lines():
                yield INDENT + line

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
                for node in orelse:
                    for line in node.c_lines():
                        yield INDENT + line
                yield "}"


class Switch(Node):
    __slots__ = ("test", "cases")
    __types__ = {
        "test": ValueMixin,
        "cases": [Node],
    }

    def lines(self):
        yield "switch {}:".format(self.test)

        for case in self.cases:
            for line in case.lines():
                yield INDENT + line

    def c_lines(self):
        yield "switch ({}){{".format(self.test.c_code())

        for case in self.cases:
            for line in case.c_lines():
                yield INDENT + line

        yield "}"


class Case(Node):
    """
    Cases will match the syntax proposed in this pep:
    https://www.python.org/dev/peps/pep-3103/#alternative-a
    """
    __slots__ = ("tests", "body")
    __types__ = {
        "tests": [Node],
        "body": [Node],
    }

    def lines(self):
        yield "case {}:".format(", ".join(map(str, self.tests)))

        for node in self.body:
            for line in node.lines():
                yield INDENT + line

    def c_lines(self):
        for case, i, is_last in ext_enumerate(self.tests):
            yield "case {}:".format(case.c_code())
            if is_last:
                for node in self.body:
                    for line in node.c_lines():
                        yield INDENT + line


class Default(Node):
    __slots__ = ("body", )

    def lines(self):
        yield "else:"
        for node in self.body:
            for line in node.lines():
                yield INDENT + line

    def c_lines(self):
        yield "default:"
        for node in self.body:
            for line in node.c_lines():
                yield INDENT + line


class BinOp(Node, ValueMixin):
    __slots__ = ("left", "op", "right")
    __types__ = {
        "left": ValueMixin,
        "op": str,
        "right": ValueMixin
    }

    def lines(self):
        yield "({} {} {})".format(self.left, self.op, self.right)

    def c_lines(self):
        yield "({} {} {})".format(self.left.c_code(), self.op, self.right.c_code())


class Compare(BinOp, ValueMixin):
    pass


class UAdd(Node):
    def lines(self):
        yield "+"


class USub(Node):
    def lines(self):
        yield "-"


class Not(Node):
    def lines(self):
        yield "not"

    def c_lines(self):
        yield "!"


class Invert(Node):
    def lines(self):
        yield "~"


class UnaryOp(Node, ValueMixin):
    __slots__ = ("op", "value")

    def lines(self):
        if isinstance(self.op, Not):
            yield "{} {}".format(self.op, self.value)
        else:
            yield "{}{}".format(self.op, self.value)

    def c_lines(self):
        yield "{}{}".format(self.op.c_code(), self.value.c_code())


class PostInc(Node, ValueMixin):
    __slots__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "{}++".format(self.value)

    def c_lines(self):
        yield "{}++".format(self.value.c_code())


class PostDec(Node, ValueMixin):
    __slots__ = ("value", )
    __types__ = {"value": ValueMixin}

    def lines(self):
        yield "{}--".format(self.value)

    def c_lines(self):
        yield "{}--".format(self.value.c_code())


class Call(Node, ValueMixin):
    __slots__ = ("func", "args")
    __types__ = {
        "func": ValueMixin,
        "args": [ValueMixin]
    }
    __defaults__ = {"args": []}

    def lines(self):
        yield "{}({})".format(self.func, ", ".join(map(str, self.args)))

    def c_lines(self):
        yield "{}({})".format(self.func.c_code(), ", ".join(a.c_code() for a in self.args))


class Name(Node, ValueMixin):
    __slots__ = ("id", )
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
    __slots__ = ("n", )

    def lines(self):
        yield str(self.n)

    def c_lines(self):
        yield str(self.n)


class Float(Node, ValueMixin):
    __slots__ = ("n", )

    def lines(self):
        yield str(self.n)

    def c_lines(self):
        yield str(self.n)


class Str(Node, ValueMixin):
    __slots__ = ("s", )

    def lines(self):
        yield '"{}"'.format(
            self.s.replace('"', r'\"').replace("\n", "\\n")
        )

    def c_lines(self):
        yield '"{}"'.format(
            self.s.replace('"', r'\"').replace("\n", "\\n")
        )


class Tuple(Node, ValueMixin):
    __slots__ = ("elts", )

    def lines(self):
        yield "({})".format(", ".join(map(str, self.elts)))


class Enum(Node):
    __slots__ = ("name", "members", )
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


class EnumDecl(Node):
    __slots__ = ("enum", )
    __types__ = {"enum": Enum}

    def lines(self):
        yield from self.enum.lines()

    def c_lines(self):
        yield "typedef enum {} {};".format(
            self.enum.name,
            self.enum.name
        )
        yield self.enum.c_code() + ";"


class TypeDefStmt(Node):
    __slots__ = ("type", "name")
    __types__ = {
        "type": LANG_TYPES,
        "name": str
    }

    def lines(self):
        yield "typedef {} {}".format(self.type, self.name)

    def c_lines(self):
        if isinstance(self.type, Node):
            yield "typedef {} {};".format(self.type.c_code(), self.name)
        else:
            yield "typedef {} {};".format(self.type, self.name)


class Struct(Node, TypeMixin):
    __slots__ = ("name", "decls", "_members")
    __types__ = {
        "name": str,
        "decls": [VarDecl],
    }
    __defaults__ = {"_members": None}

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

    def members(self):
        if self._members is None:
            self._members = {d.name: d.type for d in self.decls}
        return self._members

    def member_type(self, member):
        return self._members[member]


class StructDecl(Node):
    __slots__ = ("struct", )
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

class Define(Node):
    __slots__ = ("name", "value")
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


class CInclude(Node):
    __slots__ = ("path", )
    __types__ = {"path": str}

    def c_lines(self):
        yield '#include <{}>'.format(self.path)


class Include(Node):
    __slots__ = ("path", )
    __types__ = {"path": Str}

    def lines(self):
        yield 'include {}'.format(self.path)

    def c_lines(self):
        yield '#include "{}"'.format(to_c_file(self.path.s))


class Ifndef(Node):
    __slots__ = ("guard", )

    def lines(self):
        yield "ifndef {}".format(self.guard)

    def c_lines(self):
        yield "#ifndef {}".format(self.guard)


class Endif(Node):
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
            for attr in node.__slots__:
                val = getattr(node, attr)
                if val is not None:
                    self.visit(val)

    def visit_list(self, seq):
        return [self.visit(n) for n in seq]

    def visit_dict(self, d):
        return {k: self.visit(v) for k, v in d.items()}
