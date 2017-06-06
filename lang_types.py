from lang_ast import *
from lang_utils import SlottedClass


class LangType(SlottedClass):
    __attrs__ = ("name", )
    __types__ = {
        "name": str,
    }

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name


"""
Rule of thumb: Try to create a subclass of LangType only if you need to
add more __attrs__. Enums do not need a subclass because you just use the name
of the enum as the type whereas structs have members and pointers point to
stuff.
"""


class PointerType(LangType):
    __attrs__ = ("contents", )
    __types__ = {
        "contents": LangType,
    }

    def __init__(self, *args, **kwargs):
        super().__init__("pointer", *args, **kwargs)

    def __str__(self):
        return "pointer[{}]".format(self.contents)


class ArrayType(LangType):
    __attrs__ = ("contents", "size")
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
    __attrs__ = ("members", )
    __types__ = {
        "members": {str: LangType}
    }
    __defaults__ = {
        "members": {}
    }


class ClassType(LangType):
    __attrs__ = ("properties", "type_params", "parents")
    __types__ = {
        "properties": {str: LangType},
        "type_params": [str],
        "parents": [LangType],
    }
    __defaults__ = {
        "properties": {},
        "type_params": [],
        "parents": []
    }

    def set_prop(self, prop, t):
        if prop in self.properties:
            expected_t = self.properties[prop]
            if expected_t != t:
                raise KeyError("Property '{}' previosuly declared as type {}. Received {}.".format(
                    prop, expected_t, t
                ))
        else:
            self.properties[prop] = t

    #def __hash__(self):
    #    return hash((
    #        self.name, tuple(self.properties), tuple(self.type_params),
    #        tuple(self.parents)
    #    ))


class CallableType(LangType):
    __attrs__ = ("args", "returns")
    __types__ = {
        "args": [LangType],
        "returns": LangType
    }

    def __init__(self, *args, **kwargs):
        super().__init__("callable", *args, **kwargs)

    #def __hash__(self):
    #    return hash((self.name, tuple(self.args), self.returns))

    def __str__(self):
        return "callable({}) -> {}".format(
            ", ".join(map(str, self.args)),
            self.returns
        )


# Initialize some base types since these will pretty much not change at all
CHAR_TYPE = LangType("char")
SHORT_TYPE = LangType("short")
INT_TYPE = LangType("int")
LONG_TYPE = LangType("long")

UCHAR_TYPE = LangType("uchar")
USHORT_TYPE = LangType("ushort")
UINT_TYPE = LangType("uint")
ULONG_TYPE = LangType("ulong")

FLOAT_TYPE = LangType("float")
DOUBLE_TYPE = LangType("double")

SIZE_TYPE = LangType("size_t")
NULL_TYPE = LangType("NULL")
VOID_TYPE = LangType("void")
VARARG_TYPE = LangType("vararg")
FILE_TYPE = LangType("FILE")


# Builtin C types
BUILTIN_TYPES = frozenset((
    # Signed integral
    CHAR_TYPE,
    SHORT_TYPE,
    INT_TYPE,
    LONG_TYPE,

    # Unsigned integral
    UCHAR_TYPE,
    USHORT_TYPE,
    UINT_TYPE,
    ULONG_TYPE,

    # Floating point
    FLOAT_TYPE,
    DOUBLE_TYPE,

    # Misc
    NULL_TYPE,
    VOID_TYPE,
    VARARG_TYPE,
    FILE_TYPE,
))


INTEGRAL_TYPES = frozenset({CHAR_TYPE, SHORT_TYPE, INT_TYPE, LONG_TYPE,
                            UCHAR_TYPE, USHORT_TYPE, UINT_TYPE, ULONG_TYPE})

FLOATING_POINT_TYPES = frozenset({FLOAT_TYPE, DOUBLE_TYPE})

NUMERIC_TYPES = INTEGRAL_TYPES | FLOATING_POINT_TYPES


def is_integral_type(t):
    return t in INTEGRAL_TYPES


def is_floating_point_type(t):
    return t in FLOATING_POINT_TYPES


def is_numeric_type(t):
    return t in NUMERIC_TYPES


def is_container_type(t):
    return isinstance(t, (ArrayType, PointerType))


def can_implicit_assign(target_t, value_t):
    """Check if the value type can be implicitely assigned to the target
    type. This is primarily for the base types and not pointers.

    Example:
    x: int = 'y'

    'y' is a char but holds a numeric value whose possible ranges fit into an
    int type
    """
    assert target_t in BUILTIN_TYPES, "{} not in builtins".format(target_t)
    assert value_t in BUILTIN_TYPES, "{} not in builtins".format(value_t)

    if target_t == value_t:
        return True

    # Integral types can be casted to other integrals
    if value_t in INTEGRAL_TYPES and target_t in INTEGRAL_TYPES:
        return True

    # Floating points can be casted to floating poinrts
    if value_t in FLOATING_POINT_TYPES and target_t in FLOATING_POINT_TYPES:
        return True

    return False
