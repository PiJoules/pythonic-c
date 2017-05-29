from lang_types import *


STDIO_MODULE = Module([
    Ifndef("_STDIO_H"),
    Define("_STDIO_H"),

    # 22
    FuncDecl(
        "printf",
        [
            VarDecl("format", Pointer(NameType("char"))),
            Ellipsis(),
        ],
        NameType("void")
    ),

    # 27
    FuncDecl(
        "fscanf",
        [
            VarDecl("fscanf", Pointer(NameType("FILE"))),
            VarDecl("format", Pointer(NameType("char"))),
        ],
        NameType("void")
    ),

    Endif(),
])


STDIO_VARS = dict.fromkeys(
    {
        "printf",
        "fscanf",
    },
    ("stdio.h", STDIO_MODULE)
)
