from lang_ast import *


class LangType(SlottedClass):
    __slots__ = ("name", )
    __types__ = {
        "name": str,
    }

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name


class PointerType(LangType):
    __slots__ = ("contents", )
    __types__ = {
        "contents": LangType,
    }

    def __init__(self, *args, **kwargs):
        super().__init__("pointer", *args, **kwargs)

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, NullType):
            return True

        return super().__eq__(other)

    def __str__(self):
        return "pointer[{}]".format(self.contents)


class NumericTypeMixin:
    "Indicates this type represents a number."


class WholeNumberMixin(NumericTypeMixin):
    "This type represents a whole number."


class DecimalNumberMixin(NumericTypeMixin):
    "This type respresents a decimal number."


class NullType(LangType, NumericTypeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("NULL", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, (PointerType, NullType))

    def __hash__(self):
        return hash(self.name)


class IntType(LangType, WholeNumberMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("int", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class UIntType(LangType, WholeNumberMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("uint", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class FloatType(LangType, DecimalNumberMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("float", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class VoidType(LangType):
    def __init__(self, *args, **kwargs):
        super().__init__("void", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class CharType(LangType, WholeNumberMixin):
    def __init__(self, *args, **kwargs):
        super().__init__("char", *args, **kwargs)

    def __eq__(self, other):
        return isinstance(other, NumericTypeMixin)

    def __hash__(self):
        return hash(self.name)


class VarargType(LangType):
    def __init__(self, *args, **kwargs):
        super().__init__("vararg", *args, **kwargs)


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
