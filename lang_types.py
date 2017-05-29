from lang_ast import *
from lang_utils import SlottedClass


class LangType(SlottedClass):
    __slots__ = ("name", )
    __types__ = {
        "name": str,
    }

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name


"""
Rule of thumb: Try to create a subclass of LangType only if you need to
add more __slots__. Enums do not need a subclass because you just use the name
of the enum as the type whereas structs have members and pointers point to
stuff.
"""


class PointerType(LangType):
    __slots__ = ("contents", )
    __types__ = {
        "contents": LangType,
    }

    def __init__(self, *args, **kwargs):
        super().__init__("pointer", *args, **kwargs)

    def __str__(self):
        return "pointer[{}]".format(self.contents)


class ArrayType(LangType):
    __slots__ = ("contents", "size")
    __types__ = {
        "contents": LangType,
        "size": ValueMixin,
    }

    def __init__(self, *args, **kwargs):
        super().__init__("array", *args, **kwargs)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, ArrayType):
            return self.contents == other.contents

        return super().__eq__(other)

    def __str__(self):
        return "array[{}]".format(self.contents)


class StructType(LangType):
    __slots__ = ("members", )
    __types__ = {
        "members": {str: LangType}
    }
    __defaults__ = {
        "members": {}
    }


class CallableType(LangType):
    __slots__ = ("args", "returns")
    __types__ = {
        "args": [LangType],
        "returns": LangType
    }

    def __init__(self, *args, **kwargs):
        super().__init__("callable", *args, **kwargs)

    def __hash__(self):
        return hash((self.name, tuple(self.args), self.returns))

    def __str__(self):
        return "callable({}) -> {}".format(
            ", ".join(map(str, self.args)),
            self.returns
        )


CHAR_TYPE = LangType("char")
SHORT_TYPE = LangType("short")
INT_TYPE = LangType("int")
LONG_TYPE = LangType("long")

UINT_TYPE = LangType("uint")

FLOAT_TYPE = LangType("float")
DOUBLE_TYPE = LangType("double")

SIZE_TYPE = LangType("size_t")
NULL_TYPE = LangType("NULL")
VOID_TYPE = LangType("void")
VARARG_TYPE = LangType("vararg")
FILE_TYPE = LangType("FILE")


def can_implicit_assign(target_t, value_t):
    """Check if the value type can be implicitely assigned to the target
    type.

    Example:
    x: int = 'y'

    'y' is a char but holds a numeric value whose possible ranges fit into an
    int type
    """
    if target_t == value_t:
        return True

    # Null to pointer
    if isinstance(target_t, PointerType) and value_t == NULL_TYPE:
        return True

    return (target_t, value_t) in {
        # To char
        (CHAR_TYPE, INT_TYPE),

        # To int
        (INT_TYPE, CHAR_TYPE),

        # To uint
        (UINT_TYPE, INT_TYPE),

        # To double
        (DOUBLE_TYPE, FLOAT_TYPE),

        # To size_t
        (SIZE_TYPE, INT_TYPE),
    }
