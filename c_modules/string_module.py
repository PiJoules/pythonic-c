from lang_types import *


STRING_MODULE = Module([
    FuncDecl(
        "strlen",
        [
            VarDecl("str", Pointer(NameType("char")))
        ],
        NameType("size_t")
    ),

    FuncDecl(
        "strncpy",
        [
            VarDecl("dest", Pointer(NameType("char"))),
            VarDecl("src", Pointer(NameType("char"))),
            VarDecl("n", NameType("size_t")),
        ],
        NameType("void")
    ),
])


STRING_VARS = dict.fromkeys(
    {
        "strlen",
        "strncpy",
    },
    ("string.h", STRING_MODULE)
)

STRING_TYPES = dict.fromkeys(
    {
    },
    ("string.h", STRING_MODULE)
)
