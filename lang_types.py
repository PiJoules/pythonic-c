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
        if other.name == "NULL":
            return True

        return super().__eq__(other)

    def __str__(self):
        return "pointer[{}]".format(self.contents)


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
