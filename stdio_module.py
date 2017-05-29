from lang_types import *


STDIO_MODULE = Module([
    Ifndef("_STDIO_H"),
    Define("_STDIO_H"),

    FuncDecl(
        "printf",
        [
            VarDecl("format", Pointer(NameType("char"))),
            Ellipsis(),
        ],
        NameType("void")
    ),

    Endif(),
])


STDIO_VARS = dict.fromkeys(
    {"printf"},
    ("stdio.h", STDIO_MODULE)
)
