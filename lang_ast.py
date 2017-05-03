INDENT = "    "


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

    def c_lines(self):
        """
        Same as lines() but each line is the C code equivalent.
        """
        raise NotImplementedError("c_lines() not implemented for node {}".format(type(self)))

    def c_code(self):
        return "\n".join(self.c_lines())

    def __str__(self):
        return "\n".join(self.lines())

    def __eq__(self, other):
        if self.__slots__ != other.__slots__:
            return False

        for attr in self.__slots__:
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True

    def __ne__(self, other):
        return not (self == other)


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
    __slots__ = ("body", )

    def lines(self):
        for node in self.body:
            yield from node.lines()

    def c_lines(self):
        for node in self.body:
            yield from node.c_lines()


class FuncDef(Node):
    __slots__ = ("name", "params", "body", "returns")

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
            returns_s = self.returns.c_code()

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


class FuncType(Node):
    __slots__ = ("params", "returns")

    def lines(self):
        if isinstance(self.returns, FuncType):
            yield "({}) -> {{{}}}".format(
                ", ".join(map(str, self.params)),
                self.returns
            )
        else:
            yield "({}) -> {}".format(
                ", ".join(map(str, self.params)),
                self.returns
            )


def _format_c_decl(name, t):
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
        raise RuntimeError("Unable to handle type {}".format(type(t)))


class VarDecl(Node):
    __slots__ = ("name", "type", "init")

    def lines(self):
        if self.init:
            yield "{}: {} = {}".format(self.name, self.type, self.init)
        else:
            yield "{}: {}".format(self.name, self.type)

    def c_lines(self):
        line = _format_c_decl(self.name, self.type)
        if self.init:
            line += " = {}".format(self.init)
        yield line


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


class Array(Node):
    __slots__ = ("contents", "size")

    def lines(self):
        yield _format_container(self)


class Pointer(Node):
    __slots__ = ("contents", )

    def lines(self):
        yield _format_container(self)


class ArrayLiteral(Node):
    __slots__ = ("contents", )

    def lines(self):
        yield "[{}]".format(", ".join(map(str, self.contents)))


class Cast(Node):
    __slots__ = ("target_type", "expr")

    def lines(self):
        yield "({}){}".format(self.target_type, self.expr)


class ExprStmt(Node):
    __slots__ = ("value", )

    def lines(self):
        yield from self.value.lines()

    def c_lines(self):
        yield "{};".format(self.value)


class Assign(Node):
    __slots__ = ("left", "right")

    def lines(self):
        yield "{} = {}".format(self.left, self.right)


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


class If(Node):
    __slots__ = ("test", "body")

    def lines(self):
        yield "if {}:".format(self.test)
        for node in self.body:
            for line in node.lines():
                yield INDENT + line


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


class Call(Node):
    __slots__ = ("func", "args")

    def lines(self):
        yield "{}({})".format(self.func, ", ".join(map(str, self.args)))


class Name(Node):
    __slots__ = ("id", "type")

    def lines(self):
        yield str(self.id)


class Int(Node):
    __slots__ = ("n", )

    def lines(self):
        yield str(self.n)


class Float(Node):
    __slots__ = ("n", )

    def lines(self):
        yield str(self.n)


class Str(Node):
    __slots__ = ("s", )

    def lines(self):
        yield '"{}"'.format(
            self.s.replace('"', r'\"').replace("\n", "\\n")
        )


class Tuple(Node):
    __slots__ = ("elts", )

    def lines(self):
        yield "({})".format(", ".join(map(str, self.elts)))


class Enum(Node):
    __slots__ = ("name", "members", )

    def lines(self):
        yield "enum {} {{{}}}".format(
            self.name,
            ", ".join(map(str, self.members))
        )


##### Macros ######

class Define(Node):
    __slots__ = ("name", "value")

    def lines(self):
        if self.value:
            yield "define {} {}".format(self.name, self.value)
        else:
            yield "define {}".format(self.name)


class Include(Node):
    __slots__ = ("path", )

    def lines(self):
        yield 'include {}'.format(self.path)

    def c_lines(self):
        yield '#include <{}>'.format(self.path.s)


class IncludeLocal(Node):
    __slots__ = ("path", )

    def lines(self):
        yield 'includel {}'.format(self.path)

    def c_lines(self):
        yield '#include {}'.format(self.path)
